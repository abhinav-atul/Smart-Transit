from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import asyncpg
import json
import asyncio
import os
from ml_engine.predictor import ETAPredictor # <--- ADDED

# --- APP CONFIGURATION ---
app = FastAPI(title="Smart-Transit API Gateway")

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Connection String (Matches docker-compose.yml)
DB_DSN = "postgresql://user@localhost:5433/transit_db"

# Model Path (Using the final production model file)
MODEL_PATH = "ml_engine/eta_model.pkl" # <--- UPDATED to use the final saved model

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
            # 1. Database Connection
            app.state.pool = await asyncpg.create_pool(DB_DSN)
            print("✅ Database connection established.")
            
            # 2. ML Model Startup
            if os.path.exists(MODEL_PATH):
                app.state.eta_predictor = ETAPredictor(model_path=MODEL_PATH)
                print(f"✅ ML Model loaded from {MODEL_PATH}.")
            else:
                # Use a non-existent path to force the fallback logic
                app.state.eta_predictor = ETAPredictor(model_path="NON_EXISTENT")
                print("⚠️ ML Model not found. ETA prediction will use rule-based fallback.")
            
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

# 4. ETA PREDICTION (ML integration) <--- NEW/MODIFIED ENDPOINT
@app.get("/eta") 
async def get_eta_ml(
    distance_meters: float = Query(..., description="Distance remaining to destination stop in meters"),
    current_speed_kmh: float = Query(..., description="Vehicle speed in km/h")
):
    """
    Predicts ETA using the loaded ML model or a fallback rule.
    """
    try:
        # Convert speed from km/h to m/s, as required by your ETAPredictor's internal logic
        current_speed_m_s = current_speed_kmh / 3.6
        
        # Determine the current hour (for the traffic feature)
        hour_of_day = datetime.now().hour
        
        # Call the predictor
        prediction_minutes = app.state.eta_predictor.predict(
            distance_meters=distance_meters, 
            current_speed=current_speed_m_s, 
            hour_of_day=hour_of_day
        )
        
        source = "ML_model" if app.state.eta_predictor.ready else "rule_based_fallback"
        
        return {
            "prediction": f"{prediction_minutes:.2f} mins",
            "seconds": prediction_minutes * 60,
            "source": source
        }

    except Exception as e:
        print(f"ML Prediction Error: {e}")
        # Note: If ML fails, the frontend will automatically use the Google Maps fallback
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")