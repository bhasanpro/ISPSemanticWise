"""
Health Check Routes
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from isp_semantic_wise.config import get_settings, Settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: dict


class DetailedHealthResponse(HealthResponse):
    vector_db: Optional[dict] = None
    graph_db: Optional[dict] = None
    relational_db: Optional[dict] = None
    models: Optional[dict] = None


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """Basic health check"""
    return HealthResponse(
        status="healthy",
        version=settings.version,
        environment=settings.environment,
        services={
            "api": "up",
        },
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(settings: Settings = Depends(get_settings)):
    """Detailed health check with service status"""
    # TODO: Add actual service checks
    return DetailedHealthResponse(
        status="healthy",
        version=settings.version,
        environment=settings.environment,
        services={
            "api": "up",
        },
        vector_db={"status": "unknown"},
        graph_db={"status": "unknown"},
        relational_db={"status": "unknown"},
        models={"status": "unknown"},
    )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}