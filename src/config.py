"""Configuration management for the application."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "AgenticCloudServiceValidator"
    app_env: str = "development"
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # GitHub Models
    github_token: Optional[str] = None
    github_model_endpoint: str = "https://models.github.ai/inference/"
    model_name: str = "openai/gpt-4.1-mini"

    # Database
    database_url: str = "sqlite+aiosqlite:///./validator.db"

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"

    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    # Grafana
    grafana_url: str = "http://localhost:3000"
    grafana_api_key: Optional[str] = None

    # Alerts
    alert_email_enabled: bool = False
    alert_email_smtp_host: str = "smtp.gmail.com"
    alert_email_smtp_port: int = 587
    alert_email_from: str = ""
    alert_email_to: str = ""

    alert_slack_enabled: bool = False
    alert_slack_webhook_url: Optional[str] = None

    # Validation
    default_validation_interval_minutes: int = 60
    max_concurrent_validations: int = 5
    validation_timeout_seconds: int = 300

    # Anomaly Detection
    anomaly_threshold_percentage: float = 10.0
    anomaly_alert_threshold: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"


# Global settings instance
settings = Settings()
