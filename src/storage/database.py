"""Database models using SQLAlchemy."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


class ServiceConfigDB(Base):
    """Database model for service configurations."""

    __tablename__ = "service_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_name = Column(String(255), nullable=False, index=True)
    config_data = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    validation_results = relationship("ValidationResultDB", back_populates="config", cascade="all, delete-orphan")
    alert_configs = relationship("AlertConfigDB", back_populates="config", cascade="all, delete-orphan")


class ValidationResultDB(Base):
    """Database model for validation results."""

    __tablename__ = "validation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("service_configs.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Metrics
    rules_checked = Column(Integer, default=0)
    rules_passed = Column(Integer, default=0)
    rules_failed = Column(Integer, default=0)
    anomalies_detected = Column(Integer, default=0)

    # Data
    data_snapshots = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    config = relationship("ServiceConfigDB", back_populates="validation_results")
    anomalies = relationship("AnomalyDB", back_populates="validation", cascade="all, delete-orphan")
    reports = relationship("AnomalyReportDB", back_populates="validation", cascade="all, delete-orphan")


class AnomalyDB(Base):
    """Database model for detected anomalies."""

    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    validation_id = Column(UUID(as_uuid=True), ForeignKey("validation_results.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String(255), nullable=False, index=True)
    severity = Column(String(50), nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Details
    service_id = Column(String(255), nullable=False, index=True)
    anomaly_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    affected_records = Column(Integer, default=0)

    # Data
    sample_data = Column(JSON, nullable=True)
    expected_value = Column(JSON, nullable=True)
    actual_value = Column(JSON, nullable=True)
    deviation_percentage = Column(Float, nullable=True)

    # Relationships
    validation = relationship("ValidationResultDB", back_populates="anomalies")


class AnomalyReportDB(Base):
    """Database model for anomaly reports."""

    __tablename__ = "anomaly_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    validation_id = Column(UUID(as_uuid=True), ForeignKey("validation_results.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Summary
    total_anomalies = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)

    # Data
    recommendations = Column(JSON, nullable=True)

    # Alert status
    alert_triggered = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime, nullable=True)

    # Relationships
    validation = relationship("ValidationResultDB", back_populates="reports")


class AlertConfigDB(Base):
    """Database model for alert configurations."""

    __tablename__ = "alert_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("service_configs.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, default=True)

    # Thresholds
    anomaly_count_threshold = Column(Integer, default=3)
    critical_severity_threshold = Column(Integer, default=1)
    high_severity_threshold = Column(Integer, default=3)

    # Channels
    alert_channels = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    config = relationship("ServiceConfigDB", back_populates="alert_configs")
