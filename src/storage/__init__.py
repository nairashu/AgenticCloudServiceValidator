"""Repository layer for database operations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Anomaly,
    AnomalyReport,
    ServiceConfig,
    ValidationResult,
    ValidationStatus,
)
from src.storage.database import (
    AnomalyDB,
    AnomalyReportDB,
    ServiceConfigDB,
    ValidationResultDB,
)


class ServiceConfigRepository:
    """Repository for service configuration operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, config: ServiceConfig) -> ServiceConfigDB:
        """Create a new service configuration."""
        db_config = ServiceConfigDB(
            id=config.config_id,
            config_name=config.config_name,
            config_data=config.model_dump(mode="json"),
            enabled=config.enabled,
        )
        self.session.add(db_config)
        await self.session.flush()
        return db_config

    async def get_by_id(self, config_id: UUID) -> Optional[ServiceConfigDB]:
        """Get configuration by ID."""
        result = await self.session.execute(select(ServiceConfigDB).where(ServiceConfigDB.id == config_id))
        return result.scalar_one_or_none()

    async def get_all_enabled(self) -> List[ServiceConfigDB]:
        """Get all enabled configurations."""
        result = await self.session.execute(select(ServiceConfigDB).where(ServiceConfigDB.enabled == True))
        return list(result.scalars().all())

    async def update(self, config_id: UUID, config: ServiceConfig) -> Optional[ServiceConfigDB]:
        """Update an existing configuration."""
        db_config = await self.get_by_id(config_id)
        if db_config:
            db_config.config_name = config.config_name
            db_config.config_data = config.model_dump(mode="json")
            db_config.enabled = config.enabled
            db_config.updated_at = datetime.utcnow()
            await self.session.flush()
        return db_config

    async def delete(self, config_id: UUID) -> bool:
        """Delete a configuration."""
        db_config = await self.get_by_id(config_id)
        if db_config:
            await self.session.delete(db_config)
            await self.session.flush()
            return True
        return False


class ValidationResultRepository:
    """Repository for validation result operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: ValidationResult) -> ValidationResultDB:
        """Create a new validation result."""
        db_result = ValidationResultDB(
            id=result.validation_id,
            config_id=result.config_id,
            status=result.status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            rules_checked=result.rules_checked,
            rules_passed=result.rules_passed,
            rules_failed=result.rules_failed,
            anomalies_detected=result.anomalies_detected,
            data_snapshots=[snapshot.model_dump(mode="json") for snapshot in result.data_snapshots],
            details=result.details,
            error_message=result.error_message,
        )
        self.session.add(db_result)
        await self.session.flush()
        return db_result

    async def get_by_id(self, validation_id: UUID) -> Optional[ValidationResultDB]:
        """Get validation result by ID."""
        result = await self.session.execute(select(ValidationResultDB).where(ValidationResultDB.id == validation_id))
        return result.scalar_one_or_none()

    async def get_by_config(
        self, config_id: UUID, limit: int = 10, offset: int = 0
    ) -> List[ValidationResultDB]:
        """Get validation results for a specific configuration."""
        result = await self.session.execute(
            select(ValidationResultDB)
            .where(ValidationResultDB.config_id == config_id)
            .order_by(desc(ValidationResultDB.started_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self, validation_id: UUID, status: ValidationStatus, completed_at: Optional[datetime] = None
    ) -> Optional[ValidationResultDB]:
        """Update validation status."""
        db_result = await self.get_by_id(validation_id)
        if db_result:
            db_result.status = status.value
            if completed_at:
                db_result.completed_at = completed_at
                db_result.duration_seconds = (completed_at - db_result.started_at).total_seconds()
            await self.session.flush()
        return db_result


class AnomalyRepository:
    """Repository for anomaly operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, anomaly: Anomaly) -> AnomalyDB:
        """Create a new anomaly record."""
        db_anomaly = AnomalyDB(
            id=anomaly.anomaly_id,
            validation_id=anomaly.validation_id,
            rule_id=anomaly.rule_id,
            severity=anomaly.severity.value,
            detected_at=anomaly.detected_at,
            service_id=anomaly.service_id,
            anomaly_type=anomaly.anomaly_type,
            description=anomaly.description,
            affected_records=anomaly.affected_records,
            sample_data=anomaly.sample_data,
            expected_value=anomaly.expected_value,
            actual_value=anomaly.actual_value,
            deviation_percentage=anomaly.deviation_percentage,
        )
        self.session.add(db_anomaly)
        await self.session.flush()
        return db_anomaly

    async def get_by_validation(self, validation_id: UUID) -> List[AnomalyDB]:
        """Get all anomalies for a validation."""
        result = await self.session.execute(
            select(AnomalyDB)
            .where(AnomalyDB.validation_id == validation_id)
            .order_by(desc(AnomalyDB.detected_at))
        )
        return list(result.scalars().all())

    async def get_by_severity(self, validation_id: UUID, severity: str) -> List[AnomalyDB]:
        """Get anomalies by severity level."""
        result = await self.session.execute(
            select(AnomalyDB)
            .where(AnomalyDB.validation_id == validation_id, AnomalyDB.severity == severity)
            .order_by(desc(AnomalyDB.detected_at))
        )
        return list(result.scalars().all())


class AnomalyReportRepository:
    """Repository for anomaly report operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report: AnomalyReport) -> AnomalyReportDB:
        """Create a new anomaly report."""
        db_report = AnomalyReportDB(
            id=report.report_id,
            validation_id=report.validation_id,
            generated_at=report.generated_at,
            total_anomalies=report.total_anomalies,
            critical_count=report.critical_count,
            high_count=report.high_count,
            medium_count=report.medium_count,
            low_count=report.low_count,
            recommendations=report.recommendations,
            alert_triggered=report.alert_triggered,
            alert_sent_at=report.alert_sent_at,
        )
        self.session.add(db_report)
        await self.session.flush()
        return db_report

    async def get_by_validation(self, validation_id: UUID) -> Optional[AnomalyReportDB]:
        """Get report for a validation."""
        result = await self.session.execute(
            select(AnomalyReportDB).where(AnomalyReportDB.validation_id == validation_id)
        )
        return result.scalar_one_or_none()
