"""
Admin CRUD endpoints for route and stop management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List
from backend.app.auth import verify_token
from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.admin")
router = APIRouter(prefix="/admin", tags=["Admin"])


class StopInput(BaseModel):
    stop_name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteInput(BaseModel):
    route_id: str = Field(..., min_length=1)
    route_name: str = Field(..., min_length=1)
    stops: List[StopInput]


def _require_db():
    pool = get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return pool


@router.get("/routes")
async def list_all_routes(_token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT route_id, route_name FROM routes ORDER BY route_id")
    return [dict(r) for r in rows]


@router.post("/routes", status_code=201)
async def create_route(route: RouteInput, _token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO routes (route_id, route_name) VALUES ($1, $2) ON CONFLICT (route_id) DO UPDATE SET route_name = EXCLUDED.route_name",
                route.route_id, route.route_name,
            )
            await conn.execute("DELETE FROM stops WHERE route_id = $1", route.route_id)
            for idx, stop in enumerate(route.stops):
                await conn.execute(
                    "INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence) VALUES ($1, $2, $3, $4, $5)",
                    route.route_id, stop.stop_name, stop.latitude, stop.longitude, idx,
                )
    return {"status": "created", "route_id": route.route_id}


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, _token: dict = Depends(verify_token)):
    pool = _require_db()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM routes WHERE route_id = $1", route_id)
    return {"status": "deleted", "route_id": route_id}


# ── GTFS Ingestion Endpoints ────────────────────────────────────────────────

@router.post("/gtfs/demo")
async def ingest_gtfs_demo(_token: dict = Depends(verify_token)):
    """
    Trigger the built-in GTFS demo ingestion pipeline from the Admin UI.
    Loads a sample Lahore transit network to demonstrate GTFS compatibility.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent.parent))
    from scripts.gtfs_ingest import generate_demo_gtfs, transform_gtfs

    pool = _require_db()
    gtfs = generate_demo_gtfs()
    routes = transform_gtfs(gtfs)

    written = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for route in routes:
                await conn.execute(
                    "INSERT INTO routes (route_id, route_name) VALUES ($1, $2) ON CONFLICT (route_id) DO UPDATE SET route_name = EXCLUDED.route_name",
                    route["route_id"], route["route_name"],
                )
                await conn.execute("DELETE FROM stops WHERE route_id = $1", route["route_id"])
                for stop in route["stops"]:
                    await conn.execute(
                        "INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence) VALUES ($1, $2, $3, $4, $5)",
                        route["route_id"], stop["stop_name"], stop["lat"], stop["lng"], stop["sequence"],
                    )
                written += 1

    logger.info("GTFS demo ingestion complete: %d routes written", written)
    return {"status": "success", "routes_ingested": written, "source": "demo"}


@router.get("/gtfs/status")
async def gtfs_status(_token: dict = Depends(verify_token)):
    """Returns a count of GTFS-sourced routes currently in the database."""
    pool = _require_db()
    async with pool.acquire() as conn:
        route_count = await conn.fetchval("SELECT COUNT(*) FROM routes WHERE route_id LIKE 'GTFS-%'")
        stop_count = await conn.fetchval(
            "SELECT COUNT(*) FROM stops WHERE route_id IN (SELECT route_id FROM routes WHERE route_id LIKE 'GTFS-%')"
        )
    return {"gtfs_routes": route_count, "gtfs_stops": stop_count}
