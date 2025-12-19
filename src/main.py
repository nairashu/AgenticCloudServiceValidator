"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import configs, validations
from src.config import settings
from src.storage.repository import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup
    print(f"Starting {settings.app_name}...")
    
    # Initialize database
    await db_manager.create_tables()
    print("Database initialized")
    
    # Start scheduler if enabled
    if settings.scheduler_enabled:
        from src.scheduler import scheduler
        scheduler.start()
        print("Scheduler started")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    
    # Stop scheduler
    if settings.scheduler_enabled:
        from src.scheduler import scheduler
        scheduler.shutdown()
    
    # Close database
    await db_manager.close()
    print("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Agentic Cloud Service Validator",
    description="AI-powered multi-agent system for validating cloud service dependencies",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(configs.router)
app.include_router(validations.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.prometheus_enabled:
        return JSONResponse(
            status_code=404,
            content={"detail": "Metrics not enabled"},
        )
    
    # In production, return Prometheus-formatted metrics
    return {
        "validations_total": 0,
        "validations_success": 0,
        "validations_failed": 0,
        "anomalies_detected": 0,
        "alerts_sent": 0,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
