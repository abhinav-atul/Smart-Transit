from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from services.tracking import ingest_gps
from services.eta_engine import eta_service
from services.crowd_detect import crowd_service
from models.schemas import GPSLog, ETARequest, ETAResponse, CrowdResponse

app = FastAPI(title="Smart-Transit Gateway")

# Enable CORS so the frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY STATE (Acts as a temporary database for the UI) ---
TRIP_STATE = {
    "BUS-101": {
        "location": {"lat": 28.7041, "lng": 77.1025},
        "eta": {"minutes": 0, "status": "Waiting"},
        "crowd": {"count": 0, "level": "Unknown"},
        "route": "Route 1 (Red Line)"
    }
}

@app.get("/")
def home():
    return {"message": "Smart Transit API is Running"}

# 1. Vehicle Tracking (Called by Simulator)
@app.post("/api/v1/location")
async def update_location(data: GPSLog):
    # Update global state
    if data.vehicle_id in TRIP_STATE:
        TRIP_STATE[data.vehicle_id]["location"] = {"lat": data.latitude, "lng": data.longitude}
    return await ingest_gps(data)

# 2. Smart ETA (Called by Simulator)
@app.post("/api/v1/eta", response_model=ETAResponse)
async def get_eta(req: ETARequest):
    minutes, status, delay = eta_service.calculate(
        req.current_stop_id, req.next_stop_id, req.progress_percent, req.current_speed
    )
    
    # Update global state for UI
    # We assume the simulator sends this for 'BUS-101'
    TRIP_STATE["BUS-101"]["eta"] = {
        "minutes": minutes,
        "status": status,
        "next_stop": req.next_stop_id
    }
    
    return ETAResponse(eta_minutes=minutes, status=status, delay_minutes=delay)

# 3. Crowd Analysis (Called by Bus Camera)
@app.post("/api/v1/crowd", response_model=CrowdResponse)
async def analyze_crowd(file: UploadFile = File(...)):
    contents = await file.read()
    count, level, conf = await crowd_service.analyze(contents)
    
    # Update global state for UI
    TRIP_STATE["BUS-101"]["crowd"] = {"count": count, "level": level}
    
    return CrowdResponse(people_count=count, crowd_level=level, confidence=conf)

# 4. NEW: Frontend Polling Endpoint
@app.get("/api/v1/status")
def get_fleet_status():
    """Frontend calls this every 1 second to get positions."""
    return TRIP_STATE