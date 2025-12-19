"""Core data models for the Cloud Service Validator."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class AuthType(str, Enum):
    """Supported authentication types."""

    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    SERVICE_PRINCIPAL = "service_principal"
    CUSTOM = "custom"


class ValidationStatus(str, Enum):
    """Status of a validation run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthConfig(BaseModel):
    """Authentication configuration for a service."""

    auth_type: AuthType
    credentials: Dict[str, str] = Field(default_factory=dict)
    headers: Optional[Dict[str, str]] = Field(default=None)
    token_endpoint: Optional[HttpUrl] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "auth_type": "bearer_token",
                "credentials": {"token": "your_bearer_token_here"},
                "headers": {"Authorization": "Bearer {token}"}
            }
        }


class DependentService(BaseModel):
    """Configuration for a dependent service to validate."""

    service_id: str = Field(description="Unique identifier for the service")
    service_name: str = Field(description="Human-readable name")
    service_type: str = Field(description="Type of service (e.g., API, Database, Storage)")
    endpoint: HttpUrl = Field(description="Service endpoint URL")
    auth_config: AuthConfig = Field(description="Authentication configuration")
    health_check_path: Optional[str] = Field(default="/health", description="Health check endpoint path")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_id": "payment-service",
                "service_name": "Payment Processing Service",
                "service_type": "REST_API",
                "endpoint": "https://api.payment.example.com",
                "auth_config": {
                    "auth_type": "api_key",
                    "credentials": {"api_key": "secret_key"}
                },
                "health_check_path": "/v1/health",
                "timeout_seconds": 30
            }
        }


class ValidationRule(BaseModel):
    """Rule to validate data consistency."""

    rule_id: str = Field(description="Unique identifier for the rule")
    rule_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this rule validates")
    source_service: str = Field(description="Service ID to fetch data from")
    target_service: Optional[str] = Field(default=None, description="Service to compare against")
    validation_query: Optional[str] = Field(default=None, description="Query or filter to apply")
    expected_fields: List[str] = Field(default_factory=list, description="Fields that must be present")
    comparison_logic: Optional[str] = Field(default=None, description="Custom comparison logic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "check-payment-order-consistency",
                "rule_name": "Payment-Order Consistency Check",
                "description": "Verify all payments have corresponding orders",
                "source_service": "payment-service",
                "target_service": "order-service",
                "expected_fields": ["order_id", "amount", "status"],
                "comparison_logic": "payment.order_id == order.id AND payment.amount == order.total"
            }
        }


class ServiceConfig(BaseModel):
    """Main configuration for service validation."""

    config_id: UUID = Field(default_factory=uuid4)
    config_name: str = Field(description="Name of this configuration")
    primary_service: DependentService = Field(description="Primary service being validated")
    dependent_services: List[DependentService] = Field(description="List of dependent services")
    validation_rules: List[ValidationRule] = Field(description="Rules to apply during validation")
    schedule_cron: Optional[str] = Field(default=None, description="Cron expression for scheduling")
    validation_interval_minutes: int = Field(default=60, ge=1)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "config_name": "E-Commerce Validation",
                "primary_service": {
                    "service_id": "order-service",
                    "service_name": "Order Management",
                    "service_type": "REST_API",
                    "endpoint": "https://api.orders.example.com",
                    "auth_config": {"auth_type": "api_key", "credentials": {"api_key": "key"}}
                },
                "dependent_services": [],
                "validation_rules": [],
                "validation_interval_minutes": 60,
                "enabled": True
            }
        }


class DataSnapshot(BaseModel):
    """Snapshot of data fetched from a service."""

    service_id: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(description="Actual data retrieved")
    record_count: int = Field(ge=0)
    fetch_duration_ms: float = Field(ge=0)
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)


class ValidationResult(BaseModel):
    """Result of a validation run."""

    validation_id: UUID = Field(default_factory=uuid4)
    config_id: UUID = Field(description="Reference to ServiceConfig")
    status: ValidationStatus = Field(default=ValidationStatus.PENDING)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None, ge=0)
    
    # Data snapshots
    data_snapshots: List[DataSnapshot] = Field(default_factory=list)
    
    # Results
    rules_checked: int = Field(default=0, ge=0)
    rules_passed: int = Field(default=0, ge=0)
    rules_failed: int = Field(default=0, ge=0)
    anomalies_detected: int = Field(default=0, ge=0)
    
    # Details
    error_message: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "config_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "rules_checked": 10,
                "rules_passed": 8,
                "rules_failed": 2,
                "anomalies_detected": 2
            }
        }


class Anomaly(BaseModel):
    """Detected anomaly in the data."""

    anomaly_id: UUID = Field(default_factory=uuid4)
    validation_id: UUID = Field(description="Reference to ValidationResult")
    rule_id: str = Field(description="Rule that detected the anomaly")
    severity: AnomalySeverity
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Details
    service_id: str = Field(description="Service where anomaly was found")
    anomaly_type: str = Field(description="Type of anomaly (e.g., missing_data, mismatch)")
    description: str = Field(description="Human-readable description")
    affected_records: int = Field(default=0, ge=0)
    sample_data: Optional[Dict[str, Any]] = Field(default=None)
    
    # Thresholds
    expected_value: Optional[Any] = Field(default=None)
    actual_value: Optional[Any] = Field(default=None)
    deviation_percentage: Optional[float] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "validation_id": "123e4567-e89b-12d3-a456-426614174000",
                "rule_id": "check-payment-order-consistency",
                "severity": "high",
                "service_id": "payment-service",
                "anomaly_type": "data_mismatch",
                "description": "Found 15 payments without corresponding orders",
                "affected_records": 15,
                "deviation_percentage": 12.5
            }
        }


class AnomalyReport(BaseModel):
    """Aggregated report of anomalies."""

    report_id: UUID = Field(default_factory=uuid4)
    validation_id: UUID
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Summary
    total_anomalies: int = Field(ge=0)
    critical_count: int = Field(default=0, ge=0)
    high_count: int = Field(default=0, ge=0)
    medium_count: int = Field(default=0, ge=0)
    low_count: int = Field(default=0, ge=0)
    
    # Details
    anomalies: List[Anomaly] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Alert status
    alert_triggered: bool = Field(default=False)
    alert_sent_at: Optional[datetime] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "validation_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_anomalies": 5,
                "critical_count": 1,
                "high_count": 2,
                "medium_count": 2,
                "low_count": 0,
                "alert_triggered": True
            }
        }


class AlertConfig(BaseModel):
    """Configuration for alerting."""

    alert_id: UUID = Field(default_factory=uuid4)
    config_id: UUID = Field(description="Reference to ServiceConfig")
    enabled: bool = Field(default=True)
    
    # Thresholds
    anomaly_count_threshold: int = Field(default=3, ge=1)
    critical_severity_threshold: int = Field(default=1, ge=1)
    high_severity_threshold: int = Field(default=3, ge=1)
    
    # Channels
    email_enabled: bool = Field(default=False)
    email_recipients: List[str] = Field(default_factory=list)
    slack_enabled: bool = Field(default=False)
    slack_webhook: Optional[HttpUrl] = Field(default=None)
    webhook_enabled: bool = Field(default=False)
    webhook_url: Optional[HttpUrl] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "config_id": "123e4567-e89b-12d3-a456-426614174000",
                "enabled": True,
                "anomaly_count_threshold": 5,
                "email_enabled": True,
                "email_recipients": ["admin@example.com"],
                "slack_enabled": True,
                "slack_webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
            }
        }
