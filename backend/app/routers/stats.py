"""
Fleet statistics endpoint.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.app.auth import verify_token
from backend.app.models import FleetStats
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.stats")
router = APIRouter(tags=["Fleet"])


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable. Ensure Docker is running.")
    return pool


@router.get("/stats", response_model=FleetStats)
async def get_fleet_stats(_token_payload: dict = Depends(verify_token)):
    """Fleet statistics for the dashboard."""
    pool = _require_db()

    try:
        async with pool.acquire() as conn:
            active = await conn.fetchval("""
                SELECT COUNT(DISTINCT vehicle_id) FROM vehicle_logs
                WHERE time > NOW() - INTERVAL '2 minutes'
            """)
            total_routes = await conn.fetchval("SELECT COUNT(*) FROM routes")
            total_stops = await conn.fetchval("SELECT COUNT(*) FROM stops")

        return FleetStats(
            active_buses=active or 0,
            total_routes=total_routes or 0,
            total_stops=total_stops or 0,
        )
    except Exception as e:
        logger.error("Fleet stats error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
