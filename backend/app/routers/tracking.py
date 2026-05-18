"""
GPS tracking endpoints — receive pings and serve live positions.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException

from backend.app.models import GPSPing, BusPosition
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.tracking")
router = APIRouter(tags=["Tracking"])


def _require_db():
    """Raise 503 if database is unavailable."""
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable. Ensure Docker is running.")
    return pool


@router.post("/location")
async def receive_location_ping(ping: GPSPing):
    """
    Receives raw GPS pings from the bus simulator or driver app.
    Stores them in the time-series database.
    """
    pool = _require_db()
    ts = ping.timestamp if ping.timestamp else datetime.now(timezone.utc)

    query = """
        INSERT INTO vehicle_logs (time, vehicle_id, route_id, latitude, longitude, speed)
        VALUES ($1, $2, $3, $4, $5, $6)
    """

    try:
        async with pool.acquire() as conn:
            await conn.execute(query, ts, ping.vehicle_id, ping.route_id, ping.lat, ping.lng, ping.speed)
        return {"status": "success", "vehicle": ping.vehicle_id}
    except Exception as e:
        logger.error("Error saving GPS ping for %s: %s", ping.vehicle_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buses/live", response_model=List[BusPosition])
async def get_live_buses():
    """
    Returns the latest known position for every active bus.
    Filters to only buses seen in the last 5 minutes for performance.
    """
    pool = _require_db()

    query = """
        SELECT DISTINCT ON (vehicle_id)
            vehicle_id, route_id, latitude, longitude, speed, time
        FROM vehicle_logs
        WHERE time > NOW() - INTERVAL '5 minutes'
        ORDER BY vehicle_id, time DESC
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

        return [
            BusPosition(
                vehicle_id=row["vehicle_id"],
                route_id=row["route_id"],
                lat=row["latitude"],
                lng=row["longitude"],
                speed=row["speed"],
                last_update=row["time"].isoformat(),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error("Error fetching live buses: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
