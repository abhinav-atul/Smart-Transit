"""
Static route and stop data endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.routes")
router = APIRouter(tags=["Routes"])


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable. Ensure Docker is running.")
    return pool


@router.get("/routes")
async def get_static_routes():
    """
    Fetches routes and stops from SQL and structures them
    into nested JSON format required by the frontend.
    """
    pool = _require_db()

    query = """
        SELECT r.route_id, r.route_name, s.stop_name, s.latitude, s.longitude
        FROM routes r
        JOIN stops s ON r.route_id = s.route_id
        ORDER BY r.route_id, s.stop_sequence
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

        routes_data = {}
        for row in rows:
            rid = row["route_id"]
            if rid not in routes_data:
                routes_data[rid] = {"routeName": row["route_name"], "stops": []}
            routes_data[rid]["stops"].append({
                "name": row["stop_name"],
                "lat": row["latitude"],
                "lng": row["longitude"],
            })

        return {"routes": routes_data}

    except Exception as e:
        logger.error("Route fetch error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
