"""Alert Agent - Monitors thresholds and sends alerts."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from agent_framework import ChatAgent, ChatMessage, Executor, WorkflowContext, handler
from typing_extensions import Never

from src.models import AlertConfig, AnomalyReport, AnomalySeverity


class AlertAgent(Executor):
    """
    Agent responsible for monitoring thresholds and sending alerts.
    
    This agent:
    1. Monitors anomaly thresholds
    2. Sends alerts via multiple channels (email, Slack, webhooks)
    3. Formats alert messages intelligently
    4. Tracks alert history
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        alert_config: Optional[AlertConfig] = None,
        id: str = "alert",
    ):
        """
        Initialize the Alert Agent.

        Args:
            chat_agent: AI agent for intelligent alert formatting
            alert_config: Alert configuration
            id: Unique identifier for this executor
        """
        self.agent = chat_agent
        self.alert_config = alert_config
        super().__init__(id=id)

    @handler
    async def process_alerts(
        self,
        validation_data: Dict[str, Any],
        ctx: WorkflowContext[Never, Dict[str, Any]],
    ) -> None:
        """
        Process alerts based on anomaly report.

        Args:
            validation_data: Complete validation data with anomaly report
            ctx: Workflow context to yield final output
        """
        anomaly_report: AnomalyReport = validation_data.get("anomaly_report")

        if not anomaly_report:
            await ctx.yield_output({
                **validation_data,
                "alerts_sent": False,
                "alert_message": "No anomaly report generated",
            })
            return

        # Check if alerts should be triggered
        should_alert = await self._should_trigger_alert(anomaly_report)

        if not should_alert or not self.alert_config or not self.alert_config.enabled:
            await ctx.yield_output({
                **validation_data,
                "alerts_sent": False,
                "alert_message": "Alert threshold not met or alerts disabled",
            })
            return

        # Generate alert message using AI
        alert_message = await self._generate_alert_message(anomaly_report, validation_data)

        # Send alerts via configured channels
        alert_results = await self._send_alerts(alert_message, anomaly_report)

        # Yield final output
        await ctx.yield_output({
            **validation_data,
            "alerts_sent": True,
            "alert_results": alert_results,
            "alert_message": alert_message,
        })

    async def _should_trigger_alert(self, report: AnomalyReport) -> bool:
        """
        Determine if alerts should be triggered based on thresholds.

        Args:
            report: Anomaly report

        Returns:
            True if alert should be sent
        """
        if not self.alert_config:
            return report.alert_triggered

        # Check thresholds
        if report.critical_count >= self.alert_config.critical_severity_threshold:
            return True

        if report.high_count >= self.alert_config.high_severity_threshold:
            return True

        if report.total_anomalies >= self.alert_config.anomaly_count_threshold:
            return True

        return False

    async def _generate_alert_message(
        self, report: AnomalyReport, validation_data: Dict[str, Any]
    ) -> str:
        """
        Generate a well-formatted alert message using AI.

        Args:
            report: Anomaly report
            validation_data: Complete validation data

        Returns:
            Formatted alert message
        """
        config_name = validation_data.get("config_name", "Unknown Configuration")
        validation_id = validation_data.get("validation_id", "unknown")

        prompt = f"""Generate a concise, actionable alert message for the following situation:

Configuration: {config_name}
Validation ID: {validation_id}
Timestamp: {datetime.utcnow().isoformat()}

Anomaly Summary:
- Total Anomalies: {report.total_anomalies}
- Critical: {report.critical_count}
- High: {report.high_count}
- Medium: {report.medium_count}
- Low: {report.low_count}

Top Anomalies:
{json.dumps([{
    'severity': a.severity.value,
    'type': a.anomaly_type,
    'description': a.description,
    'service': a.service_id,
    'affected_records': a.affected_records
} for a in report.anomalies[:5]], indent=2)}

Recommendations:
{json.dumps(report.recommendations[:3], indent=2)}

Create an alert message that:
1. Clearly states the severity and urgency
2. Summarizes key issues
3. Provides immediate action items
4. Is suitable for technical team members

Format as plain text (not JSON), max 500 words."""

        try:
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)
            return response.text.strip()

        except Exception:
            # Fallback message
            return self._generate_fallback_message(report, config_name, validation_id)

    def _generate_fallback_message(
        self, report: AnomalyReport, config_name: str, validation_id: str
    ) -> str:
        """Generate a basic alert message if AI generation fails."""
        severity = "🔴 CRITICAL" if report.critical_count > 0 else "⚠️ HIGH PRIORITY"

        message = f"""{severity} - Cloud Service Validation Alert

Configuration: {config_name}
Validation ID: {validation_id}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Anomalies Detected: {report.total_anomalies}
├─ Critical: {report.critical_count}
├─ High: {report.high_count}
├─ Medium: {report.medium_count}
└─ Low: {report.low_count}

Top Issues:
{self._format_top_anomalies(report.anomalies[:3])}

Immediate Actions Required:
{chr(10).join(f'{i+1}. {rec}' for i, rec in enumerate(report.recommendations[:3]))}

Please investigate immediately and take corrective action.
"""
        return message

    def _format_top_anomalies(self, anomalies: List[Any]) -> str:
        """Format top anomalies for display."""
        if not anomalies:
            return "  None"

        lines = []
        for i, anomaly in enumerate(anomalies, 1):
            severity_emoji = {
                AnomalySeverity.CRITICAL: "🔴",
                AnomalySeverity.HIGH: "🟠",
                AnomalySeverity.MEDIUM: "🟡",
                AnomalySeverity.LOW: "🔵",
            }.get(anomaly.severity, "⚪")

            lines.append(
                f"{i}. {severity_emoji} [{anomaly.service_id}] {anomaly.description[:80]}"
            )

        return "\n".join(lines)

    async def _send_alerts(
        self, message: str, report: AnomalyReport
    ) -> Dict[str, Any]:
        """
        Send alerts via all configured channels.

        Args:
            message: Alert message to send
            report: Anomaly report

        Returns:
            Dictionary with results from each channel
        """
        results = {}

        if not self.alert_config:
            return {"error": "No alert configuration provided"}

        # Send via different channels in parallel
        tasks = []

        if self.alert_config.email_enabled and self.alert_config.email_recipients:
            tasks.append(self._send_email_alert(message, report))

        if self.alert_config.slack_enabled and self.alert_config.slack_webhook:
            tasks.append(self._send_slack_alert(message, report))

        if self.alert_config.webhook_enabled and self.alert_config.webhook_url:
            tasks.append(self._send_webhook_alert(message, report))

        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            results["email"] = task_results[0] if self.alert_config.email_enabled else None
            if len(task_results) > 1:
                results["slack"] = task_results[1] if self.alert_config.slack_enabled else None
            if len(task_results) > 2:
                results["webhook"] = task_results[2] if self.alert_config.webhook_enabled else None

        return results

    async def _send_email_alert(self, message: str, report: AnomalyReport) -> Dict[str, Any]:
        """Send alert via email (placeholder implementation)."""
        # In production, integrate with actual email service (SendGrid, AWS SES, etc.)
        return {
            "channel": "email",
            "success": True,
            "message": "Email alert would be sent (not implemented in this demo)",
            "recipients": self.alert_config.email_recipients,
        }

    async def _send_slack_alert(self, message: str, report: AnomalyReport) -> Dict[str, Any]:
        """Send alert via Slack webhook."""
        try:
            # Format for Slack
            slack_payload = {
                "text": f"🚨 Cloud Service Validation Alert",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚨 Cloud Service Validation Alert",
                        },
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message[:3000]},
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Anomalies: *{report.total_anomalies}* | Critical: *{report.critical_count}* | High: *{report.high_count}*",
                            }
                        ],
                    },
                ],
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    str(self.alert_config.slack_webhook), json=slack_payload
                )

                return {
                    "channel": "slack",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                }

        except Exception as e:
            return {"channel": "slack", "success": False, "error": str(e)}

    async def _send_webhook_alert(self, message: str, report: AnomalyReport) -> Dict[str, Any]:
        """Send alert via custom webhook."""
        try:
            payload = {
                "alert_type": "cloud_service_validation",
                "timestamp": datetime.utcnow().isoformat(),
                "message": message,
                "anomaly_count": report.total_anomalies,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "report_id": str(report.report_id),
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    str(self.alert_config.webhook_url),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                return {
                    "channel": "webhook",
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                }

        except Exception as e:
            return {"channel": "webhook", "success": False, "error": str(e)}


async def create_alert_agent(
    chat_agent: ChatAgent, alert_config: Optional[AlertConfig] = None
) -> AlertAgent:
    """
    Factory function to create a configured Alert Agent.

    Args:
        chat_agent: Configured chat agent with appropriate model
        alert_config: Alert configuration

    Returns:
        Configured AlertAgent instance
    """
    return AlertAgent(chat_agent=chat_agent, alert_config=alert_config)
