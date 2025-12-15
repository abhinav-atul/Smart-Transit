from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import asyncpg
import json
import asyncio


# --- APP CONFIGURATION ---
app = FastAPI(title="Smart-Transit API Gateway")

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your frontend (likely running on port 5500 or 8080) 
# to talk to this backend (running on port 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Connection String (Matches docker-compose.yml)
DB_DSN = "postgresql://user@localhost:5433/transit_db"


# --- DATA MODELS ---

class GPSPing(BaseModel):
    vehicle_id: str
    route_id: str
    lat: float
    lng: float
    speed: float = 0.0
    timestamp: Optional[datetime] = None

# --- LIFESPAN EVENTS (Startup/Shutdown) ---

@app.on_event("startup")
async def startup_db():
    retries = 10
    delay = 2

    for i in range(retries):
        try:
            app.state.pool = await asyncpg.create_pool(DB_DSN)
            print("✅ Database connection established.")
            return
        except Exception as e:
            print(f"❌ DB connection failed (attempt {i+1}/{retries}): {e}")
            await asyncio.sleep(delay)

    print("🚨 Could not connect to database after retries.")


@app.on_event("shutdown")
async def shutdown_db():
    if hasattr(app.state, "pool"):
        await app.state.pool.close()
    print("zzZ Database connection closed.")

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    """Simple check to see if API is online."""
    return {"status": "online", "system": "Smart-Transit Backend"}

# 1. RECEIVE DATA (From Bus Simulator)
@app.post("/location")
async def receive_location_ping(ping: GPSPing):
    """
    Receives raw GPS pings from the bus simulator or driver app.
    Stores them in the time-series database.
    """
    ts = ping.timestamp if ping.timestamp else datetime.now()
    
    query = """
        INSERT INTO vehicle_logs (time, vehicle_id, route_id, latitude, longitude, speed)
        VALUES ($1, $2, $3, $4, $5, $6)
    """
    
    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute(query, ts, ping.vehicle_id, ping.route_id, ping.lat, ping.lng, ping.speed)
        return {"status": "success", "vehicle": ping.vehicle_id}
    except Exception as e:
        print(f"Error saving ping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. SERVE LIVE POSITIONS (To Frontend Map)
@app.get("/buses/live")
async def get_live_buses():
    """
    Returns the *latest* known position for every active bus.
    Uses 'DISTINCT ON' for high performance.
    """
    query = """
        SELECT DISTINCT ON (vehicle_id) 
            vehicle_id, route_id, latitude, longitude, speed, time
        FROM vehicle_logs
        ORDER BY vehicle_id, time DESC
    """
    
    try:
        async with app.state.pool.acquire() as conn:
            rows = await conn.fetch(query)
            
        return [
            {
                "vehicle_id": row["vehicle_id"],
                "route_id": row["route_id"],
                "lat": row["latitude"],
                "lng": row["longitude"],
                "speed": row["speed"],
                "last_update": row["time"].isoformat()
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. SERVE STATIC ROUTES (To Frontend Init)
@app.get("/routes")
async def get_static_routes():
    """
    Fetches Routes and Stops from SQL and structures them 
    into the nested JSON format required by app.js.
    """
    # Join routes and stops, ordered by sequence
    query = """
        SELECT r.route_id, r.route_name, s.stop_name, s.latitude, s.longitude
        FROM routes r
        JOIN stops s ON r.route_id = s.route_id
        ORDER BY r.route_id, s.stop_sequence
    """
    
    try:
        async with app.state.pool.acquire() as conn:
            rows = await conn.fetch(query)

        # Transformation Logic: SQL Flat Rows -> Nested JSON
        routes_data = {}
        
        for row in rows:
            rid = row['route_id']
            
            if rid not in routes_data:
                routes_data[rid] = {
                    "routeName": row['route_name'],
                    "stops": []
                }
            
            routes_data[rid]["stops"].append({
                "name": row['stop_name'],
                "lat": row['latitude'],
                "lng": row['longitude']
            })

        return {"routes": routes_data}

    except Exception as e:
        print(f"Route Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 4. ETA PREDICTION (Placeholder for ML integration)
@app.get("/eta/{route_id}")
async def get_eta(route_id: str):
    """
    Future home of the ML model inference.
    Currently returns a rule-based placeholder.
    """
    return {
        "route_id": route_id,
        "prediction": "5 mins",
        "confidence": 0.85,
        "source": "rule_based_fallback"
    }


