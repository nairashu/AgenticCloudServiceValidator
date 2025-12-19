"""Example usage script demonstrating the API."""

import asyncio
import json
from uuid import uuid4

import httpx


BASE_URL = "http://localhost:8000"


async def create_service_config():
    """Create a new service configuration."""
    config = {
        "config_name": "Demo E-Commerce Validation",
        "primary_service": {
            "service_id": "order-service",
            "service_name": "Order Management",
            "service_type": "REST_API",
            "endpoint": "https://jsonplaceholder.typicode.com/posts",  # Demo API
            "auth_config": {
                "auth_type": "bearer_token",
                "credentials": {"token": "demo_token"},
            },
            "health_check_path": None,
            "timeout_seconds": 30,
        },
        "dependent_services": [
            {
                "service_id": "user-service",
                "service_name": "User Service",
                "service_type": "REST_API",
                "endpoint": "https://jsonplaceholder.typicode.com/users",  # Demo API
                "auth_config": {
                    "auth_type": "api_key",
                    "credentials": {"api_key": "demo_key"},
                },
                "timeout_seconds": 30,
            }
        ],
        "validation_rules": [
            {
                "rule_id": "check-user-references",
                "rule_name": "User Reference Check",
                "description": "Verify all posts have valid user references",
                "source_service": "order-service",
                "target_service": "user-service",
                "expected_fields": ["userId", "id", "title"],
            }
        ],
        "validation_interval_minutes": 60,
        "enabled": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/v1/configs/", json=config)
        response.raise_for_status()
        created_config = response.json()
        print(f"✅ Created configuration: {created_config['config_id']}")
        return created_config


async def list_configurations():
    """List all configurations."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/configs/")
        response.raise_for_status()
        configs = response.json()
        print(f"\n📋 Found {len(configs)} configuration(s):")
        for config in configs:
            print(f"  - {config['config_name']} (ID: {config['config_id']})")
        return configs


async def start_validation(config_id: str):
    """Start a validation run."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/validations/start",
            json={"config_id": config_id},
        )
        response.raise_for_status()
        result = response.json()
        print(f"\n🚀 Started validation: {result['validation_id']}")
        return result["validation_id"]


async def get_validation_status(validation_id: str):
    """Get validation status."""
    async with httpx.AsyncClient() as client:
        # Poll for completion
        for i in range(30):  # Wait up to 5 minutes
            response = await client.get(
                f"{BASE_URL}/api/v1/validations/{validation_id}"
            )
            response.raise_for_status()
            result = response.json()

            status = result["status"]
            print(f"  Status: {status} (attempt {i+1})")

            if status in ["completed", "failed", "cancelled"]:
                print("\n✅ Validation completed!")
                print(f"  Rules checked: {result.get('rules_checked', 0)}")
                print(f"  Rules passed: {result.get('rules_passed', 0)}")
                print(f"  Rules failed: {result.get('rules_failed', 0)}")
                print(f"  Anomalies detected: {result.get('anomalies_detected', 0)}")
                return result

            await asyncio.sleep(10)  # Wait 10 seconds

        print("\n⏱️  Validation still in progress...")
        return None


async def main():
    """Run demo."""
    print("=" * 60)
    print("Agentic Cloud Service Validator - Demo")
    print("=" * 60)

    # Check health
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("\n✅ API is healthy")
        else:
            print("\n❌ API is not responding")
            return

    # Create configuration
    print("\n1️⃣  Creating service configuration...")
    config = await create_service_config()

    # List configurations
    print("\n2️⃣  Listing configurations...")
    await list_configurations()

    # Start validation
    print("\n3️⃣  Starting validation...")
    validation_id = await start_validation(config["config_id"])

    # Wait for completion
    print("\n4️⃣  Waiting for validation to complete...")
    await get_validation_status(validation_id)

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
