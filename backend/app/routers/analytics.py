"""
Historical fleet analytics endpoints using TimescaleDB aggregate queries.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.auth import verify_token
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.analytics")
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return pool


@router.get("/fleet/summary")
async def fleet_summary(_token: dict = Depends(verify_token)):
    """Overall fleet statistics for the last 24 hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        data = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT vehicle_id) AS unique_buses,
                COUNT(*) AS total_pings,
                ROUND(AVG(speed)::numeric, 2) AS avg_speed_kmh,
                ROUND(MAX(speed)::numeric, 2) AS max_speed_kmh,
                MIN(time) AS earliest_ping,
                MAX(time) AS latest_ping
            FROM vehicle_logs
            WHERE time > NOW() - INTERVAL '24 hours'
        """)
    return dict(data) if data else {}


@router.get("/fleet/hourly")
async def fleet_hourly_activity(_token: dict = Depends(verify_token)):
    """Hourly ping counts and average speed for the last 24h."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                date_trunc('hour', time) AS hour,
                COUNT(DISTINCT vehicle_id) AS active_buses,
                COUNT(*) AS total_pings,
                ROUND(AVG(speed)::numeric, 2) AS avg_speed
            FROM vehicle_logs
            WHERE time > NOW() - INTERVAL '24 hours'
            GROUP BY date_trunc('hour', time)
            ORDER BY hour
        """)
    return [dict(r) for r in rows]


@router.get("/bus/{vehicle_id}/history")
async def bus_history(
    vehicle_id: str,
    hours: int = Query(default=1, ge=1, le=24),
    _token: dict = Depends(verify_token),
):
    """GPS trail for a specific bus over the last N hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT latitude, longitude, speed, time
            FROM vehicle_logs
            WHERE vehicle_id = $1 AND time > NOW() - INTERVAL '1 hour' * $2
            ORDER BY time ASC
        """, vehicle_id, hours)
    return [
        {"lat": r["latitude"], "lng": r["longitude"], "speed": r["speed"], "time": r["time"].isoformat()}
        for r in rows
    ]


@router.get("/routes/performance")
async def route_performance(_token: dict = Depends(verify_token)):
    """Average speed per route for the last 24 hours."""
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                vl.route_id,
                r.route_name,
                COUNT(DISTINCT vl.vehicle_id) AS buses_operated,
                ROUND(AVG(vl.speed)::numeric, 2) AS avg_speed,
                COUNT(*) AS total_pings
            FROM vehicle_logs vl
            LEFT JOIN routes r ON vl.route_id = r.route_id
            WHERE vl.time > NOW() - INTERVAL '24 hours'
            GROUP BY vl.route_id, r.route_name
            ORDER BY avg_speed DESC
        """)
    return [dict(r) for r in rows]
