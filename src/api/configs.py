"""FastAPI routes for service configuration management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ServiceConfig
from src.storage.repository import ServiceConfigRepository, get_db_session

router = APIRouter(prefix="/api/v1/configs", tags=["Service Configurations"])


@router.post("/", response_model=ServiceConfig, status_code=status.HTTP_201_CREATED)
async def create_config(
    config: ServiceConfig,
    session: AsyncSession = Depends(get_db_session),
) -> ServiceConfig:
    """Create a new service configuration."""
    repo = ServiceConfigRepository(session)
    await repo.create(config)
    return config


@router.get("/", response_model=List[ServiceConfig])
async def list_configs(
    enabled_only: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> List[ServiceConfig]:
    """List all service configurations."""
    repo = ServiceConfigRepository(session)
    
    if enabled_only:
        db_configs = await repo.get_all_enabled()
    else:
        # For now, just get enabled ones
        # In production, add a method to get all
        db_configs = await repo.get_all_enabled()
    
    configs = []
    for db_config in db_configs:
        config_data = db_config.config_data
        configs.append(ServiceConfig(**config_data))
    
    return configs


@router.get("/{config_id}", response_model=ServiceConfig)
async def get_config(
    config_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ServiceConfig:
    """Get a specific service configuration."""
    repo = ServiceConfigRepository(session)
    db_config = await repo.get_by_id(config_id)
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
    
    return ServiceConfig(**db_config.config_data)


@router.put("/{config_id}", response_model=ServiceConfig)
async def update_config(
    config_id: UUID,
    config: ServiceConfig,
    session: AsyncSession = Depends(get_db_session),
) -> ServiceConfig:
    """Update a service configuration."""
    repo = ServiceConfigRepository(session)
    db_config = await repo.update(config_id, config)
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
    
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a service configuration."""
    repo = ServiceConfigRepository(session)
    deleted = await repo.delete(config_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found",
        )
