"""
Health check endpoint.
"""

from fastapi import APIRouter
from backend.app.models import HealthResponse
from backend.app.db.pool import get_pool

router = APIRouter(tags=["System"])


@router.get("/", response_model=HealthResponse)
def health_check():
    """System health check with component status."""
    from backend.app.main import app

    pool = get_pool()
    db_status = "connected" if pool is not None else "disconnected"

    predictor = getattr(app.state, "eta_predictor", None)
    ml_status = "loaded" if (predictor and predictor.ready) else "fallback"

    return HealthResponse(
        status="online",
        system="Smart-Transit Backend",
        version="2.1.0",
        database=db_status,
        ml_model=ml_status,
    )
