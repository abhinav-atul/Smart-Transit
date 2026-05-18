"""
WebSocket endpoint for real-time bus position streaming.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.db.pool import get_pool

logger = logging.getLogger("smart_transit.websocket")
router = APIRouter(tags=["Tracking"])

connected_clients: set[WebSocket] = set()


@router.websocket("/ws/buses")
async def bus_positions_ws(websocket: WebSocket):
    """Push active bus positions to connected clients every second."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(connected_clients))

    query = """
        SELECT vehicle_id, route_id, latitude, longitude, speed, last_update
        FROM vehicle_latest_positions
        WHERE last_update > NOW() - INTERVAL '5 minutes'
        ORDER BY vehicle_id
    """

    try:
        while True:
            buses = []
            pool = get_pool()
            if pool is not None:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(query)
                    buses = [
                        {
                            "vehicle_id": row["vehicle_id"],
                            "route_id": row["route_id"],
                            "lat": float(row["latitude"]),
                            "lng": float(row["longitude"]),
                            "speed": float(row["speed"]),
                            "last_update": row["last_update"].isoformat(),
                        }
                        for row in rows
                    ]

            await websocket.send_json({"type": "bus_update", "buses": buses})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket streaming error: %s", exc)
    finally:
        connected_clients.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(connected_clients))
