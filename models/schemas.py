from pydantic import BaseModel
from typing import Optional, List
from pydantic import BaseModel

# GPS Data from Bus
class GPSLog(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    speed: float
    timestamp: float
    route_id: str

# Request for ETA Calculation
class ETARequest(BaseModel):
    current_stop_id: str
    next_stop_id: str
    progress_percent: float 
    current_speed: float

# Response for ETA
class ETAResponse(BaseModel):
    eta_minutes: float
    status: str
    delay_minutes: int

# Response for Crowd Analysis
class CrowdResponse(BaseModel):
    people_count: int
    crowd_level: str
    confidence: str

# GPS Data from Bus
class GPSLog(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    speed: float
    timestamp: float
    route_id: str

# Request for ETA Calculation
class ETARequest(BaseModel):
    current_stop_id: str
    next_stop_id: str
    progress_percent: float # 0.0 to 1.0 (e.g. 0.5 is halfway between stops)
    current_speed: float

# Response for ETA
class ETAResponse(BaseModel):
    eta_minutes: float
    status: str
    delay_minutes: int

# Response for Crowd Analysis
class CrowdResponse(BaseModel):
    people_count: int
    crowd_level: str
    confidence: str