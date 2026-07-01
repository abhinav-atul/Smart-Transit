"""
GPS tracking endpoints — receive pings and serve live positions.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.auth import verify_api_key
from backend.app.models import GPSPing, BusPosition, TelemetryPing
from backend.app.db.pool import get_pool
from backend.app.rate_limit import limiter

logger = logging.getLogger("smart_transit.tracking")
router = APIRouter(tags=["Tracking"])


def _require_db():
    """Raise 503 if database is unavailable."""
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable. Ensure Docker is running.")
    return pool


@router.post("/location")
@limiter.limit("60/minute")
async def receive_location_ping(
    request: Request,
    ping: GPSPing,
    _api_key: str = Depends(verify_api_key),
):
    """
    Receives raw GPS pings from the bus simulator or driver app.
    Stores them in the time-series database.
    """
    pool = _require_db()
    ts = ping.timestamp if ping.timestamp else datetime.now(timezone.utc)

    insert_log_query = """
        INSERT INTO vehicle_logs (time, vehicle_id, route_id, latitude, longitude, speed, passenger_count)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    """
    upsert_latest_query = """
        INSERT INTO vehicle_latest_positions (vehicle_id, route_id, latitude, longitude, speed, passenger_count, last_update)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (vehicle_id) DO UPDATE SET
            route_id = EXCLUDED.route_id,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            speed = EXCLUDED.speed,
            passenger_count = EXCLUDED.passenger_count,
            last_update = EXCLUDED.last_update
    """

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                insert_log_query,
                ts,
                ping.vehicle_id,
                ping.route_id,
                ping.lat,
                ping.lng,
                ping.speed,
                ping.passenger_count,
            )
            await conn.execute(
                upsert_latest_query,
                ping.vehicle_id,
                ping.route_id,
                ping.lat,
                ping.lng,
                ping.speed,
                ping.passenger_count,
                ts,
            )
        return {"status": "success", "vehicle": ping.vehicle_id}
    except Exception as e:
        logger.error("Error saving GPS ping for %s: %s", ping.vehicle_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/location/telemetry")
async def receive_telemetry_ping(
    ping: TelemetryPing,
    _api_key: str = Depends(verify_api_key),
):
    """Receive IoT edge passenger counting telemetry."""
    pool = _require_db()
    ts = ping.timestamp if ping.timestamp else datetime.now(timezone.utc)
    
    query = """
        UPDATE vehicle_latest_positions
        SET passenger_count = $1, last_update = $2
        WHERE vehicle_id = $3
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(query, ping.passenger_count, ts, ping.vehicle_id)
        
        # Also broadcast via websocket
        from backend.app.routers.websocket import broadcast_location
        await broadcast_location({
            "vehicle_id": ping.vehicle_id,
            "passenger_count": ping.passenger_count,
            "type": "telemetry"
        })
        
        return {"status": "success", "vehicle": ping.vehicle_id}
    except Exception as e:
        logger.error("Error saving telemetry for %s: %s", ping.vehicle_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buses/live", response_model=List[BusPosition])
async def get_live_buses():
    """
    Returns the latest known position for every active bus.
    Filters to only buses seen in the last 5 minutes for performance.
    """
    pool = _require_db()

    query = """
        SELECT vehicle_id, route_id, latitude, longitude, speed, passenger_count, last_update
        FROM vehicle_latest_positions
        WHERE last_update > NOW() - INTERVAL '5 minutes'
        ORDER BY vehicle_id
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
                passenger_count=row["passenger_count"],
                last_update=row["last_update"].isoformat(),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error("Error fetching live buses: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
