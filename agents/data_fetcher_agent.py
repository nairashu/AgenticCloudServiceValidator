"""Data Fetcher Agent - Fetches data from dependent services."""

import json
from datetime import datetime
from typing import Any, Dict, List

import httpx
from agent_framework import ChatAgent, ChatMessage, Executor, WorkflowContext, handler

from src.auth import ServiceAuthenticator
from src.models import DataSnapshot, DependentService


class DataFetcherAgent(Executor):
    """
    Agent responsible for fetching data from dependent services.
    
    This agent:
    1. Authenticates with each service
    2. Fetches data according to configuration
    3. Creates data snapshots for validation
    4. Handles errors and timeouts gracefully
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        authenticator: ServiceAuthenticator,
        id: str = "data_fetcher",
    ):
        """
        Initialize the Data Fetcher Agent.

        Args:
            chat_agent: AI agent for intelligent data extraction and error handling
            authenticator: Service authenticator for handling various auth types
            id: Unique identifier for this executor
        """
        self.agent = chat_agent
        self.authenticator = authenticator
        super().__init__(id=id)

    @handler
    async def fetch_service_data(
        self,
        services: List[DependentService],
        ctx: WorkflowContext[List[DataSnapshot]],
    ) -> None:
        """
        Fetch data from all configured dependent services.

        Args:
            services: List of services to fetch data from
            ctx: Workflow context to send results downstream
        """
        snapshots: List[DataSnapshot] = []

        for service in services:
            snapshot = await self._fetch_from_service(service)
            snapshots.append(snapshot)

        # Send snapshots to next agent in workflow
        await ctx.send_message(snapshots)

    async def _fetch_from_service(self, service: DependentService) -> DataSnapshot:
        """
        Fetch data from a single service.

        Args:
            service: Service configuration

        Returns:
            DataSnapshot containing fetched data or error information
        """
        start_time = datetime.utcnow()

        try:
            # Get authenticated headers
            headers = await self.authenticator.get_authenticated_headers(
                service.service_id, service.endpoint, service.auth_config
            )

            # Fetch data from service
            async with httpx.AsyncClient(timeout=service.timeout_seconds) as client:
                # First check health if configured
                if service.health_check_path:
                    health_url = f"{service.endpoint.rstrip('/')}{service.health_check_path}"
                    try:
                        health_response = await client.get(health_url, headers=headers)
                        if health_response.status_code >= 400:
                            return self._create_error_snapshot(
                                service,
                                start_time,
                                f"Health check failed with status {health_response.status_code}",
                            )
                    except Exception as e:
                        return self._create_error_snapshot(
                            service, start_time, f"Health check failed: {str(e)}"
                        )

                # Fetch actual data
                response = await client.get(str(service.endpoint), headers=headers)
                response.raise_for_status()

                # Parse response
                data = response.json() if "application/json" in response.headers.get("content-type", "") else {
                    "raw_response": response.text
                }

                # Use AI agent to extract and structure the data
                structured_data = await self._structure_data_with_ai(service, data)

                fetch_duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                return DataSnapshot(
                    service_id=service.service_id,
                    fetched_at=datetime.utcnow(),
                    data=structured_data,
                    record_count=self._count_records(structured_data),
                    fetch_duration_ms=fetch_duration,
                    success=True,
                )

        except httpx.HTTPError as e:
            return self._create_error_snapshot(service, start_time, f"HTTP error: {str(e)}")
        except Exception as e:
            return self._create_error_snapshot(service, start_time, f"Unexpected error: {str(e)}")

    async def _structure_data_with_ai(self, service: DependentService, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI agent to intelligently structure and extract relevant data.

        Args:
            service: Service configuration
            raw_data: Raw data from service

        Returns:
            Structured data ready for validation
        """
        try:
            # Prepare prompt for AI agent
            prompt = f"""Analyze and structure the following data from service '{service.service_name}' ({service.service_type}):

Data:
{json.dumps(raw_data, indent=2)[:2000]}  # Limit to first 2000 chars

Extract and return a JSON object with:
1. "records": Array of individual records/entities
2. "metadata": Metadata about the dataset (count, timestamps, etc.)
3. "identifiers": Key fields that uniquely identify records
4. "summary": Brief summary of the data

Return ONLY valid JSON, no additional text."""

            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)

            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            structured_data = json.loads(response_text)
            return structured_data

        except Exception as e:
            # Fallback to raw data if AI processing fails
            return {
                "records": [raw_data] if isinstance(raw_data, dict) else raw_data,
                "metadata": {"processing_error": str(e)},
                "raw_data": raw_data,
            }

    def _create_error_snapshot(
        self, service: DependentService, start_time: datetime, error_message: str
    ) -> DataSnapshot:
        """Create a snapshot for failed data fetch."""
        fetch_duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        return DataSnapshot(
            service_id=service.service_id,
            fetched_at=datetime.utcnow(),
            data={},
            record_count=0,
            fetch_duration_ms=fetch_duration,
            success=False,
            error_message=error_message,
        )

    @staticmethod
    def _count_records(data: Dict[str, Any]) -> int:
        """Count the number of records in structured data."""
        if "records" in data and isinstance(data["records"], list):
            return len(data["records"])
        elif isinstance(data, list):
            return len(data)
        elif isinstance(data, dict) and len(data) > 0:
            return 1
        return 0


async def create_data_fetcher_agent(chat_agent: ChatAgent) -> DataFetcherAgent:
    """
    Factory function to create a configured Data Fetcher Agent.

    Args:
        chat_agent: Configured chat agent with appropriate model

    Returns:
        Configured DataFetcherAgent instance
    """
    authenticator = ServiceAuthenticator()
    return DataFetcherAgent(chat_agent=chat_agent, authenticator=authenticator)
