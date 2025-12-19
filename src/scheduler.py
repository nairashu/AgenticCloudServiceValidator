"""Scheduler for periodic validation runs."""

import logging
from datetime import datetime
from typing import Dict
from uuid import UUID, uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.models import ServiceConfig
from src.orchestrator import orchestration_service
from src.storage.repository import ServiceConfigRepository, ValidationResultRepository, db_manager

logger = logging.getLogger(__name__)


class ValidationScheduler:
    """Manages scheduled validation runs."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self._scheduled_jobs: Dict[UUID, str] = {}  # config_id -> job_id

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Validation scheduler started")

            # Load and schedule all enabled configurations
            self.scheduler.add_job(
                self._load_configurations,
                trigger="interval",
                seconds=60,  # Check for new configs every minute
                id="config_loader",
                replace_existing=True,
            )

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Validation scheduler shutdown")

    async def _load_configurations(self) -> None:
        """Load enabled configurations and schedule them."""
        try:
            async with db_manager.get_session() as session:
                repo = ServiceConfigRepository(session)
                db_configs = await repo.get_all_enabled()

                for db_config in db_configs:
                    config = ServiceConfig(**db_config.config_data)
                    
                    # Check if already scheduled
                    if config.config_id not in self._scheduled_jobs:
                        await self.schedule_validation(config)

        except Exception as e:
            logger.error(f"Error loading configurations: {e}")

    async def schedule_validation(self, config: ServiceConfig) -> None:
        """
        Schedule a validation for a configuration.

        Args:
            config: Service configuration
        """
        if not config.enabled:
            logger.info(f"Skipping disabled configuration: {config.config_name}")
            return

        job_id = f"validation_{config.config_id}"

        # Remove existing job if any
        if job_id in [job.id for job in self.scheduler.get_jobs()]:
            self.scheduler.remove_job(job_id)

        # Determine trigger
        if config.schedule_cron:
            # Use cron expression
            trigger = CronTrigger.from_crontab(config.schedule_cron)
        else:
            # Use interval in minutes
            trigger = IntervalTrigger(minutes=config.validation_interval_minutes)

        # Schedule the job
        self.scheduler.add_job(
            self._run_scheduled_validation,
            trigger=trigger,
            args=[config],
            id=job_id,
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs
        )

        self._scheduled_jobs[config.config_id] = job_id
        logger.info(
            f"Scheduled validation for '{config.config_name}' "
            f"(interval: {config.validation_interval_minutes} minutes)"
        )

    async def unschedule_validation(self, config_id: UUID) -> None:
        """
        Unschedule a validation.

        Args:
            config_id: Configuration ID
        """
        job_id = self._scheduled_jobs.get(config_id)
        if job_id and job_id in [job.id for job in self.scheduler.get_jobs()]:
            self.scheduler.remove_job(job_id)
            del self._scheduled_jobs[config_id]
            logger.info(f"Unscheduled validation for config {config_id}")

    async def _run_scheduled_validation(self, config: ServiceConfig) -> None:
        """
        Run a scheduled validation.

        Args:
            config: Service configuration
        """
        validation_id = uuid4()
        
        logger.info(
            f"Starting scheduled validation for '{config.config_name}' "
            f"(validation_id: {validation_id})"
        )

        try:
            # Create validation result in database
            async with db_manager.get_session() as session:
                from src.models import ValidationResult
                
                validation_repo = ValidationResultRepository(session)
                result = ValidationResult(
                    validation_id=validation_id,
                    config_id=config.config_id,
                )
                await validation_repo.create(result)

            # Run validation
            result = await orchestration_service.start_validation(config, validation_id)

            # Update database
            async with db_manager.get_session() as session:
                validation_repo = ValidationResultRepository(session)
                await validation_repo.update_status(
                    validation_id,
                    result.status,
                    result.completed_at,
                )

            logger.info(
                f"Completed scheduled validation for '{config.config_name}' "
                f"(validation_id: {validation_id}, status: {result.status.value})"
            )

        except Exception as e:
            logger.error(
                f"Error in scheduled validation for '{config.config_name}': {e}",
                exc_info=True,
            )

            # Update status to failed
            try:
                async with db_manager.get_session() as session:
                    from src.models import ValidationStatus
                    
                    validation_repo = ValidationResultRepository(session)
                    await validation_repo.update_status(
                        validation_id,
                        ValidationStatus.FAILED,
                        datetime.utcnow(),
                    )
            except Exception as update_error:
                logger.error(f"Error updating validation status: {update_error}")


# Global scheduler instance
scheduler = ValidationScheduler()
