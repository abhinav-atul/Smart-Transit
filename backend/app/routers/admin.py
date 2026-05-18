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
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Route not found")
    return {"status": "deleted", "route_id": route_id}
