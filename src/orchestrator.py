"""Orchestrator for coordinating multi-agent validation workflow."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from agent_framework import ChatAgent, ChatMessage, WorkflowBuilder
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

from agents import (
    AlertAgent,
    AnomalyDetectionAgent,
    CrossVerificationAgent,
    DataFetcherAgent,
    create_alert_agent,
    create_anomaly_detection_agent,
    create_cross_verification_agent,
    create_data_fetcher_agent,
)
from src.config import settings
from src.models import AlertConfig, ServiceConfig, ValidationResult, ValidationStatus


class ValidationOrchestrator:
    """
    Orchestrates the multi-agent validation workflow.
    
    Workflow:
    1. DataFetcherAgent → Fetches data from all services
    2. CrossVerificationAgent → Validates data consistency
    3. AnomalyDetectionAgent → Detects anomalies and generates reports
    4. AlertAgent → Sends alerts if thresholds are exceeded
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        model_name: str = "openai/gpt-4.1-mini",
    ):
        """
        Initialize the orchestrator.

        Args:
            github_token: GitHub token for API access
            model_name: Model to use for agents
        """
        self.github_token = github_token or settings.github_token
        self.model_name = model_name
        self._chat_clients: Dict[str, Any] = {}

    async def create_workflow(
        self,
        config: ServiceConfig,
        alert_config: Optional[AlertConfig] = None,
    ) -> Any:
        """
        Create the multi-agent validation workflow.

        Args:
            config: Service configuration
            alert_config: Alert configuration

        Returns:
            Configured workflow
        """
        # Create chat agents for each executor
        # Using GitHub Models (free tier) for development
        from agent_framework.integrations.github import GitHubChatClient

        # Create individual chat clients for each agent with specific instructions
        data_fetcher_client = GitHubChatClient(
            token=self.github_token,
            model_name=self.model_name,
        )
        data_fetcher_chat_agent = ChatAgent(
            chat_client=data_fetcher_client,
            instructions=(
                "You are a data extraction specialist. "
                "Extract and structure data from various service APIs. "
                "Identify key fields, relationships, and data types. "
                "Return well-structured JSON that preserves important information."
            ),
        )

        verification_client = GitHubChatClient(
            token=self.github_token,
            model_name=self.model_name,
        )
        verification_chat_agent = ChatAgent(
            chat_client=verification_client,
            instructions=(
                "You are a data consistency validator. "
                "Compare data across services to find inconsistencies, missing records, and mismatches. "
                "Be thorough but concise. Return structured JSON with clear pass/fail indicators."
            ),
        )

        anomaly_client = GitHubChatClient(
            token=self.github_token,
            model_name=self.model_name,
        )
        anomaly_chat_agent = ChatAgent(
            chat_client=anomaly_client,
            instructions=(
                "You are an anomaly detection specialist. "
                "Identify data anomalies, assess severity (critical/high/medium/low), "
                "and provide actionable recommendations. Be specific about impact and remediation."
            ),
        )

        alert_client = GitHubChatClient(
            token=self.github_token,
            model_name=self.model_name,
        )
        alert_chat_agent = ChatAgent(
            chat_client=alert_client,
            instructions=(
                "You are an alert message composer. "
                "Create clear, urgent, actionable alert messages for technical teams. "
                "Prioritize critical information and immediate action items."
            ),
        )

        # Create agent executors
        data_fetcher = await create_data_fetcher_agent(data_fetcher_chat_agent)
        verifier = await create_cross_verification_agent(verification_chat_agent)
        anomaly_detector = await create_anomaly_detection_agent(
            anomaly_chat_agent, settings.anomaly_threshold_percentage
        )
        alerter = await create_alert_agent(alert_chat_agent, alert_config)

        # Build workflow using Agent Framework
        workflow = (
            WorkflowBuilder()
            .set_start_executor(data_fetcher)
            .add_edge(data_fetcher, verifier)
            .add_edge(verifier, anomaly_detector)
            .add_edge(anomaly_detector, alerter)
            .build()
        )

        return workflow

    async def run_validation(
        self,
        config: ServiceConfig,
        validation_id: UUID,
        alert_config: Optional[AlertConfig] = None,
    ) -> ValidationResult:
        """
        Run a complete validation workflow.

        Args:
            config: Service configuration
            validation_id: Validation run ID
            alert_config: Alert configuration

        Returns:
            ValidationResult with complete results
        """
        started_at = datetime.utcnow()

        try:
            # Create workflow
            workflow = await self.create_workflow(config, alert_config)

            # Prepare initial input for data fetcher
            all_services = [config.primary_service] + config.dependent_services

            # Run workflow with streaming
            final_output = None
            async for event in workflow.run_stream(all_services):
                # You could log events here for debugging
                # print(f"Event: {event.__class__.__name__}")
                
                # Capture final output
                from agent_framework import WorkflowOutputEvent
                if isinstance(event, WorkflowOutputEvent):
                    final_output = event.data

            # Process results
            if final_output:
                completed_at = datetime.utcnow()
                duration = (completed_at - started_at).total_seconds()

                # Extract verification results
                verification_results = final_output.get("verification_results", [])
                anomaly_report = final_output.get("anomaly_report")

                result = ValidationResult(
                    validation_id=validation_id,
                    config_id=config.config_id,
                    status=ValidationStatus.COMPLETED,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=duration,
                    data_snapshots=final_output.get("snapshots", []),
                    rules_checked=len(config.validation_rules),
                    rules_passed=sum(1 for r in verification_results if r.passed),
                    rules_failed=sum(1 for r in verification_results if not r.passed),
                    anomalies_detected=anomaly_report.total_anomalies if anomaly_report else 0,
                    details={
                        "verification_summary": {
                            "total_rules": len(verification_results),
                            "passed": sum(1 for r in verification_results if r.passed),
                            "failed": sum(1 for r in verification_results if not r.passed),
                        },
                        "alert_sent": final_output.get("alerts_sent", False),
                        "alert_message": final_output.get("alert_message"),
                    },
                )

                return result

            else:
                # No output received
                return ValidationResult(
                    validation_id=validation_id,
                    config_id=config.config_id,
                    status=ValidationStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error_message="Workflow completed but no output received",
                )

        except Exception as e:
            # Handle errors
            return ValidationResult(
                validation_id=validation_id,
                config_id=config.config_id,
                status=ValidationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_message=f"Validation error: {str(e)}",
            )


class ValidationOrchestrationService:
    """Service for managing validation orchestration."""

    def __init__(self):
        """Initialize the orchestration service."""
        self.orchestrator = ValidationOrchestrator()
        self._active_validations: Dict[UUID, ValidationResult] = {}

    async def start_validation(
        self,
        config: ServiceConfig,
        validation_id: UUID,
        alert_config: Optional[AlertConfig] = None,
    ) -> ValidationResult:
        """
        Start a new validation run.

        Args:
            config: Service configuration
            validation_id: Validation run ID
            alert_config: Alert configuration

        Returns:
            ValidationResult
        """
        # Store in active validations
        result = ValidationResult(
            validation_id=validation_id,
            config_id=config.config_id,
            status=ValidationStatus.IN_PROGRESS,
        )
        self._active_validations[validation_id] = result

        # Run validation
        result = await self.orchestrator.run_validation(config, validation_id, alert_config)

        # Update active validations
        self._active_validations[validation_id] = result

        return result

    async def get_validation_status(self, validation_id: UUID) -> Optional[ValidationResult]:
        """Get status of a validation run."""
        return self._active_validations.get(validation_id)

    async def cancel_validation(self, validation_id: UUID) -> bool:
        """Cancel a running validation."""
        if validation_id in self._active_validations:
            result = self._active_validations[validation_id]
            if result.status == ValidationStatus.IN_PROGRESS:
                result.status = ValidationStatus.CANCELLED
                result.completed_at = datetime.utcnow()
                return True
        return False


# Global orchestration service instance
orchestration_service = ValidationOrchestrationService()
