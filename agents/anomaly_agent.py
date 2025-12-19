"""Anomaly Detection Agent - Detects and reports data anomalies."""

import json
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from agent_framework import ChatAgent, ChatMessage, Executor, WorkflowContext, handler

from src.models import Anomaly, AnomalyReport, AnomalySeverity, DataSnapshot


class AnomalyDetectionAgent(Executor):
    """
    Agent responsible for detecting anomalies and generating reports.
    
    This agent:
    1. Analyzes verification results for anomalies
    2. Assigns severity levels
    3. Generates detailed anomaly reports
    4. Provides recommendations
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        anomaly_threshold: float = 10.0,
        id: str = "anomaly_detection",
    ):
        """
        Initialize the Anomaly Detection Agent.

        Args:
            chat_agent: AI agent for intelligent anomaly detection
            anomaly_threshold: Threshold percentage for anomaly detection
            id: Unique identifier for this executor
        """
        self.agent = chat_agent
        self.anomaly_threshold = anomaly_threshold
        super().__init__(id=id)

    @handler
    async def detect_anomalies(
        self,
        verification_data: Dict[str, Any],
        ctx: WorkflowContext[Dict[str, Any]],
    ) -> None:
        """
        Detect anomalies from verification results.

        Args:
            verification_data: Results from cross-verification agent
            ctx: Workflow context to send results downstream
        """
        validation_id = verification_data.get("validation_id")
        verification_results = verification_data.get("verification_results", [])
        snapshots = verification_data.get("snapshots", [])

        # Detect anomalies using AI
        anomalies = await self._detect_anomalies_with_ai(
            validation_id, verification_results, snapshots
        )

        # Generate comprehensive report
        report = await self._generate_report(validation_id, anomalies, verification_results)

        # Prepare output
        output = {
            **verification_data,
            "anomalies": anomalies,
            "anomaly_report": report,
        }

        await ctx.send_message(output)

    async def _detect_anomalies_with_ai(
        self,
        validation_id: UUID,
        verification_results: List[Any],
        snapshots: List[DataSnapshot],
    ) -> List[Anomaly]:
        """
        Use AI to detect and classify anomalies.

        Args:
            validation_id: ID of the validation run
            verification_results: Results from verification
            snapshots: Data snapshots

        Returns:
            List of detected anomalies
        """
        # Prepare failed verifications
        failed_results = [r for r in verification_results if not r.passed]

        if not failed_results:
            return []

        prompt = f"""Analyze the following failed verification results and detect anomalies:

Failed Verifications:
{json.dumps([{'rule_id': r.rule_id, 'message': r.message, 'details': r.details} for r in failed_results], indent=2)[:3000]}

Data Snapshots Summary:
{json.dumps([{'service_id': s.service_id, 'success': s.success, 'record_count': s.record_count} for s in snapshots], indent=2)}

For each anomaly found, provide:
1. Severity (critical/high/medium/low):
   - CRITICAL: Data loss, security issues, complete failures
   - HIGH: Significant inconsistencies affecting many records
   - MEDIUM: Moderate inconsistencies or data quality issues
   - LOW: Minor issues, edge cases

2. Anomaly type (e.g., data_mismatch, missing_data, data_quality, consistency_error)
3. Affected records count (estimate)
4. Description
5. Deviation percentage (if applicable)

Respond with a JSON array of anomalies:
[
  {{
    "rule_id": "rule_id",
    "severity": "high",
    "service_id": "service_id",
    "anomaly_type": "data_mismatch",
    "description": "Clear description",
    "affected_records": 10,
    "deviation_percentage": 15.5,
    "expected_value": "what was expected",
    "actual_value": "what was found"
  }}
]

Return ONLY valid JSON array, no additional text."""

        try:
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)

            # Parse AI response
            response_text = response.text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            anomaly_data_list = json.loads(response_text)

            # Convert to Anomaly objects
            anomalies = []
            for anomaly_data in anomaly_data_list:
                anomaly = Anomaly(
                    validation_id=validation_id,
                    rule_id=anomaly_data.get("rule_id", "unknown"),
                    severity=AnomalySeverity(anomaly_data.get("severity", "medium").lower()),
                    service_id=anomaly_data.get("service_id", "unknown"),
                    anomaly_type=anomaly_data.get("anomaly_type", "unknown"),
                    description=anomaly_data.get("description", "Anomaly detected"),
                    affected_records=anomaly_data.get("affected_records", 0),
                    deviation_percentage=anomaly_data.get("deviation_percentage"),
                    expected_value=anomaly_data.get("expected_value"),
                    actual_value=anomaly_data.get("actual_value"),
                    sample_data=anomaly_data.get("sample_data"),
                )
                anomalies.append(anomaly)

            return anomalies

        except Exception as e:
            # Fallback: Create basic anomalies from failed verifications
            anomalies = []
            for result in failed_results:
                anomaly = Anomaly(
                    validation_id=validation_id,
                    rule_id=result.rule_id,
                    severity=AnomalySeverity.MEDIUM,
                    service_id="unknown",
                    anomaly_type="verification_failure",
                    description=result.message,
                    affected_records=0,
                )
                anomalies.append(anomaly)

            return anomalies

    async def _generate_report(
        self,
        validation_id: UUID,
        anomalies: List[Anomaly],
        verification_results: List[Any],
    ) -> AnomalyReport:
        """
        Generate comprehensive anomaly report with recommendations.

        Args:
            validation_id: ID of the validation run
            anomalies: List of detected anomalies
            verification_results: Verification results

        Returns:
            AnomalyReport with summary and recommendations
        """
        # Count by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for anomaly in anomalies:
            severity_counts[anomaly.severity.value] += 1

        # Generate recommendations using AI
        recommendations = await self._generate_recommendations(anomalies, verification_results)

        # Determine if alert should be triggered
        alert_triggered = (
            severity_counts["critical"] > 0
            or severity_counts["high"] >= 3
            or len(anomalies) >= 5
        )

        report = AnomalyReport(
            validation_id=validation_id,
            total_anomalies=len(anomalies),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            anomalies=anomalies,
            recommendations=recommendations,
            alert_triggered=alert_triggered,
            alert_sent_at=datetime.utcnow() if alert_triggered else None,
        )

        return report

    async def _generate_recommendations(
        self,
        anomalies: List[Anomaly],
        verification_results: List[Any],
    ) -> List[str]:
        """
        Generate actionable recommendations using AI.

        Args:
            anomalies: List of detected anomalies
            verification_results: Verification results

        Returns:
            List of recommendation strings
        """
        if not anomalies:
            return ["No anomalies detected. All services are operating normally."]

        prompt = f"""Based on the following anomalies, provide actionable recommendations:

Anomalies:
{json.dumps([{
    'severity': a.severity.value,
    'type': a.anomaly_type,
    'description': a.description,
    'affected_records': a.affected_records,
    'service': a.service_id
} for a in anomalies[:10]], indent=2)}

Total Anomalies: {len(anomalies)}

Provide 3-7 specific, actionable recommendations to:
1. Fix immediate issues
2. Prevent recurrence
3. Improve data quality
4. Optimize service interactions

Format as a JSON array of strings:
["Recommendation 1", "Recommendation 2", ...]

Return ONLY valid JSON array, no additional text."""

        try:
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)

            # Parse AI response
            response_text = response.text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            recommendations = json.loads(response_text)
            return recommendations if isinstance(recommendations, list) else [str(recommendations)]

        except Exception:
            # Fallback recommendations
            return [
                f"Investigate {len(anomalies)} detected anomalies",
                "Review service logs for error patterns",
                "Check network connectivity between services",
                "Verify authentication credentials are valid",
                "Consider implementing data reconciliation jobs",
            ]


async def create_anomaly_detection_agent(
    chat_agent: ChatAgent, anomaly_threshold: float = 10.0
) -> AnomalyDetectionAgent:
    """
    Factory function to create a configured Anomaly Detection Agent.

    Args:
        chat_agent: Configured chat agent with appropriate model
        anomaly_threshold: Threshold percentage for anomaly detection

    Returns:
        Configured AnomalyDetectionAgent instance
    """
    return AnomalyDetectionAgent(
        chat_agent=chat_agent, anomaly_threshold=anomaly_threshold
    )
