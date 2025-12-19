"""Simple test to verify project setup."""

import pytest


def test_imports():
    """Test that main modules can be imported."""
    from src import config, models
    from agents import data_fetcher_agent, verification_agent

    assert config is not None
    assert models is not None
    assert data_fetcher_agent is not None
    assert verification_agent is not None


def test_models():
    """Test basic model creation."""
    from src.models import AuthConfig, AuthType, DependentService

    auth_config = AuthConfig(
        auth_type=AuthType.API_KEY,
        credentials={"api_key": "test_key"},
    )

    assert auth_config.auth_type == AuthType.API_KEY
    assert auth_config.credentials["api_key"] == "test_key"

    service = DependentService(
        service_id="test-service",
        service_name="Test Service",
        service_type="REST_API",
        endpoint="https://api.example.com",
        auth_config=auth_config,
    )

    assert service.service_id == "test-service"
    assert service.service_name == "Test Service"


def test_config_loading():
    """Test configuration loading."""
    from src.config import settings

    assert settings.app_name == "AgenticCloudServiceValidator"
    assert settings.api_port == 8000
    assert settings.model_name == "openai/gpt-4.1-mini"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
