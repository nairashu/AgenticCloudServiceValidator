"""FastAPI routes for validation management."""

from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ServiceConfig, ValidationResult
from src.orchestrator import orchestration_service
from src.storage.repository import (
    ServiceConfigRepository,
    ValidationResultRepository,
    get_db_session,
)

router = APIRouter(prefix="/api/v1/validations", tags=["Validations"])


class ValidationStartRequest(BaseModel):
    """Request to start a validation."""

    config_id: UUID
    

class ValidationStartResponse(BaseModel):
    """Response when starting a validation."""

    validation_id: UUID
    status: str
    message: str


@router.post("/start", response_model=ValidationStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_validation(
    request: ValidationStartRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> ValidationStartResponse:
    """Start a new validation run."""
    # Get configuration
    config_repo = ServiceConfigRepository(session)
    db_config = await config_repo.get_by_id(request.config_id)
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {request.config_id} not found",
        )
    
    if not db_config.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration is disabled",
        )
    
    config = ServiceConfig(**db_config.config_data)
    validation_id = uuid4()
    
    # Create initial validation result
    validation_repo = ValidationResultRepository(session)
    result = ValidationResult(
        validation_id=validation_id,
        config_id=config.config_id,
    )
    await validation_repo.create(result)
    
    # Start validation in background
    background_tasks.add_task(
        run_validation_background,
        validation_id,
        config,
        session,
    )
    
    return ValidationStartResponse(
        validation_id=validation_id,
        status="started",
        message=f"Validation {validation_id} started",
    )


async def run_validation_background(
    validation_id: UUID,
    config: ServiceConfig,
    session: AsyncSession,
) -> None:
    """Run validation in background."""
    try:
        # Run validation
        result = await orchestration_service.start_validation(config, validation_id)
        
        # Update database
        validation_repo = ValidationResultRepository(session)
        await validation_repo.update_status(
            validation_id,
            result.status,
            result.completed_at,
        )
        
    except Exception as e:
        # Update status to failed
        from src.models import ValidationStatus
        validation_repo = ValidationResultRepository(session)
        await validation_repo.update_status(
            validation_id,
            ValidationStatus.FAILED,
        )


@router.get("/{validation_id}", response_model=ValidationResult)
async def get_validation(
    validation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ValidationResult:
    """Get validation result by ID."""
    # First check in-memory
    result = await orchestration_service.get_validation_status(validation_id)
    
    if result:
        return result
    
    # Check database
    validation_repo = ValidationResultRepository(session)
    db_result = await validation_repo.get_by_id(validation_id)
    
    if not db_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation {validation_id} not found",
        )
    
    # Reconstruct ValidationResult from database
    from src.models import ValidationStatus, DataSnapshot
    
    result = ValidationResult(
        validation_id=db_result.id,
        config_id=db_result.config_id,
        status=ValidationStatus(db_result.status),
        started_at=db_result.started_at,
        completed_at=db_result.completed_at,
        duration_seconds=db_result.duration_seconds,
        rules_checked=db_result.rules_checked,
        rules_passed=db_result.rules_passed,
        rules_failed=db_result.rules_failed,
        anomalies_detected=db_result.anomalies_detected,
        data_snapshots=[DataSnapshot(**snapshot) for snapshot in (db_result.data_snapshots or [])],
        details=db_result.details or {},
        error_message=db_result.error_message,
    )
    
    return result


@router.get("/config/{config_id}", response_model=List[ValidationResult])
async def list_validations_for_config(
    config_id: UUID,
    limit: int = 10,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[ValidationResult]:
    """List validation results for a specific configuration."""
    validation_repo = ValidationResultRepository(session)
    db_results = await validation_repo.get_by_config(config_id, limit, offset)
    
    from src.models import ValidationStatus, DataSnapshot
    
    results = []
    for db_result in db_results:
        result = ValidationResult(
            validation_id=db_result.id,
            config_id=db_result.config_id,
            status=ValidationStatus(db_result.status),
            started_at=db_result.started_at,
            completed_at=db_result.completed_at,
            duration_seconds=db_result.duration_seconds,
            rules_checked=db_result.rules_checked,
            rules_passed=db_result.rules_passed,
            rules_failed=db_result.rules_failed,
            anomalies_detected=db_result.anomalies_detected,
            data_snapshots=[DataSnapshot(**snapshot) for snapshot in (db_result.data_snapshots or [])],
            details=db_result.details or {},
            error_message=db_result.error_message,
        )
        results.append(result)
    
    return results


@router.post("/{validation_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_validation(
    validation_id: UUID,
) -> dict:
    """Cancel a running validation."""
    cancelled = await orchestration_service.cancel_validation(validation_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation {validation_id} not found or already completed",
        )
    
    return {"message": f"Validation {validation_id} cancelled"}
