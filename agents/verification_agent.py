"""Cross-Verification Agent - Validates data consistency across services."""

import json
from typing import Any, Dict, List

from agent_framework import ChatAgent, ChatMessage, Executor, WorkflowContext, handler

from src.models import DataSnapshot, ValidationRule


class VerificationResult:
    """Result of a single verification check."""

    def __init__(
        self,
        rule_id: str,
        passed: bool,
        message: str,
        details: Dict[str, Any] = None,
    ):
        self.rule_id = rule_id
        self.passed = passed
        self.message = message
        self.details = details or {}


class CrossVerificationAgent(Executor):
    """
    Agent responsible for cross-verifying data consistency across services.
    
    This agent:
    1. Applies validation rules to data snapshots
    2. Checks for data consistency across services
    3. Identifies missing or mismatched data
    4. Uses AI to understand complex relationships
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        id: str = "cross_verification",
    ):
        """
        Initialize the Cross-Verification Agent.

        Args:
            chat_agent: AI agent for intelligent data verification
            id: Unique identifier for this executor
        """
        self.agent = chat_agent
        super().__init__(id=id)

    @handler
    async def verify_data_consistency(
        self,
        context: Dict[str, Any],
        ctx: WorkflowContext[Dict[str, Any]],
    ) -> None:
        """
        Verify data consistency across all services.

        Args:
            context: Dictionary containing snapshots and rules
            ctx: Workflow context to send results downstream
        """
        snapshots: List[DataSnapshot] = context.get("snapshots", [])
        rules: List[ValidationRule] = context.get("rules", [])

        verification_results: List[VerificationResult] = []

        # Verify each rule
        for rule in rules:
            result = await self._verify_rule(rule, snapshots)
            verification_results.append(result)

        # Prepare results summary
        results = {
            "snapshots": snapshots,
            "rules": rules,
            "verification_results": verification_results,
            "rules_checked": len(rules),
            "rules_passed": sum(1 for r in verification_results if r.passed),
            "rules_failed": sum(1 for r in verification_results if not r.passed),
        }

        await ctx.send_message(results)

    async def _verify_rule(
        self, rule: ValidationRule, snapshots: List[DataSnapshot]
    ) -> VerificationResult:
        """
        Verify a single validation rule against data snapshots.

        Args:
            rule: Validation rule to check
            snapshots: List of data snapshots to verify against

        Returns:
            VerificationResult with pass/fail and details
        """
        try:
            # Find relevant snapshots
            source_snapshot = next(
                (s for s in snapshots if s.service_id == rule.source_service), None
            )

            if not source_snapshot or not source_snapshot.success:
                return VerificationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message=f"Source service '{rule.source_service}' data not available",
                )

            # If there's a target service for comparison
            if rule.target_service:
                target_snapshot = next(
                    (s for s in snapshots if s.service_id == rule.target_service), None
                )

                if not target_snapshot or not target_snapshot.success:
                    return VerificationResult(
                        rule_id=rule.rule_id,
                        passed=False,
                        message=f"Target service '{rule.target_service}' data not available",
                    )

                # Use AI to perform cross-service verification
                return await self._ai_cross_verify(rule, source_snapshot, target_snapshot)

            else:
                # Single service validation
                return await self._ai_single_verify(rule, source_snapshot)

        except Exception as e:
            return VerificationResult(
                rule_id=rule.rule_id,
                passed=False,
                message=f"Verification error: {str(e)}",
            )

    async def _ai_cross_verify(
        self,
        rule: ValidationRule,
        source: DataSnapshot,
        target: DataSnapshot,
    ) -> VerificationResult:
        """
        Use AI to verify data consistency between two services.

        Args:
            rule: Validation rule
            source: Source service data
            target: Target service data

        Returns:
            VerificationResult
        """
        prompt = f"""Verify data consistency between two services according to this rule:

Rule: {rule.rule_name}
Description: {rule.description}
Comparison Logic: {rule.comparison_logic or 'Check that all records in source have matching records in target'}

Source Service Data ({source.service_id}):
{json.dumps(source.data, indent=2)[:3000]}

Target Service Data ({target.service_id}):
{json.dumps(target.data, indent=2)[:3000]}

Expected Fields: {', '.join(rule.expected_fields)}

Analyze the data and respond with a JSON object:
{{
    "passed": true/false,
    "message": "Brief description of the verification result",
    "inconsistencies_found": number,
    "missing_records": number,
    "mismatched_records": number,
    "details": {{"any": "relevant details"}}
}}

Return ONLY valid JSON, no additional text."""

        try:
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)

            # Parse AI response
            response_text = response.text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result_data = json.loads(response_text)

            return VerificationResult(
                rule_id=rule.rule_id,
                passed=result_data.get("passed", False),
                message=result_data.get("message", "Verification completed"),
                details=result_data,
            )

        except Exception as e:
            return VerificationResult(
                rule_id=rule.rule_id,
                passed=False,
                message=f"AI verification failed: {str(e)}",
            )

    async def _ai_single_verify(
        self, rule: ValidationRule, source: DataSnapshot
    ) -> VerificationResult:
        """
        Use AI to verify data from a single service.

        Args:
            rule: Validation rule
            source: Source service data

        Returns:
            VerificationResult
        """
        prompt = f"""Verify data from a single service according to this rule:

Rule: {rule.rule_name}
Description: {rule.description}

Service Data ({source.service_id}):
{json.dumps(source.data, indent=2)[:3000]}

Expected Fields: {', '.join(rule.expected_fields)}
Query/Filter: {rule.validation_query or 'None'}

Check that:
1. All expected fields are present
2. Data follows expected format
3. No obvious data quality issues

Respond with a JSON object:
{{
    "passed": true/false,
    "message": "Brief description of findings",
    "missing_fields": [],
    "data_quality_issues": [],
    "details": {{"any": "relevant details"}}
}}

Return ONLY valid JSON, no additional text."""

        try:
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)

            # Parse AI response
            response_text = response.text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result_data = json.loads(response_text)

            return VerificationResult(
                rule_id=rule.rule_id,
                passed=result_data.get("passed", False),
                message=result_data.get("message", "Verification completed"),
                details=result_data,
            )

        except Exception as e:
            return VerificationResult(
                rule_id=rule.rule_id,
                passed=False,
                message=f"AI verification failed: {str(e)}",
            )


async def create_cross_verification_agent(chat_agent: ChatAgent) -> CrossVerificationAgent:
    """
    Factory function to create a configured Cross-Verification Agent.

    Args:
        chat_agent: Configured chat agent with appropriate model

    Returns:
        Configured CrossVerificationAgent instance
    """
    return CrossVerificationAgent(chat_agent=chat_agent)
