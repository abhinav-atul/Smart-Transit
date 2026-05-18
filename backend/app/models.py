"""
Pydantic request/response models for the Smart-Transit API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# --- Request Models ---

class GPSPing(BaseModel):
    """Incoming GPS data from the bus simulator or driver app."""
    vehicle_id: str = Field(..., min_length=1, description="Unique bus identifier")
    route_id: str = Field(..., min_length=1, description="Route the bus is operating on")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    speed: float = Field(default=0.0, ge=0, description="Speed in km/h")
    timestamp: Optional[datetime] = None


# --- Response Models ---

class HealthResponse(BaseModel):
    status: str
    system: str
    version: str
    database: str
    ml_model: str


class BusPosition(BaseModel):
    vehicle_id: str
    route_id: str
    lat: float
    lng: float
    speed: float
    last_update: str


class ETAResponse(BaseModel):
    prediction: str
    seconds: float
    source: str


class FleetStats(BaseModel):
    active_buses: int
    total_routes: int
    total_stops: int
