import time
import json
import requests
import random
from datetime import datetime

# API Configuration
API_URL = "http://localhost:8000/location"
CONFIG_PATH = "simulation/data/config.json"

# OSRM API for road geometry
OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        exit(1)

def fetch_osrm_path(stops):
    """
    Fetches the detailed road path between stops using OSRM.
    Returns a list of (lat, lng) tuples.
    """
    if len(stops) < 2:
        return [tuple(s["coords"]) for s in stops]

    # OSRM requires "lng,lat" formatted coordinates separated by semicolons
    coords_str = ";".join([f"{s['coords'][1]},{s['coords'][0]}" for s in stops])
    
    url = OSRM_ROUTE_URL.format(coords=coords_str)
    
    try:
        print(f"   ↳ Fetching road path for {len(stops)} stops...")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and len(data["routes"]) > 0:
                # OSRM returns [lng, lat], we convert back to [lat, lng]
                path = [(p[1], p[0]) for p in data["routes"][0]["geometry"]["coordinates"]]
                print(f"     ✅ Path found: {len(path)} points")
                return path
    except Exception as e:
        print(f"     ⚠️ OSRM fetch failed ({e}). Using straight lines.")
    
    # Fallback to straight lines if OSRM fails
    return [tuple(stop["coords"]) for stop in stops]

def simulate_buses():
    config = load_config()
    bus_state = {}

    print("🚌 Initializing Bus Simulation with Variable Speeds...")

    # 1. Pre-calculate paths for all routes
    routes_cache = {}
    for route_id, route_data in config["routes"].items():
        print(f"📍 Processing Route: {route_data['routeName']}...")
        routes_cache[route_id] = fetch_osrm_path(route_data["stops"])

    # 2. Assign Buses to Routes
    for route_id, bus_ids in config.get("bus_assignments", {}).items():
        path = routes_cache.get(route_id, [])
        if not path: continue

        for i, bus_id in enumerate(bus_ids):
            # Spacing buses out: Start second bus at different index
            start_index = (i * 15) % len(path)
            
            # Initialize with a random base speed
            bus_state[bus_id] = {
                "route_id": route_id,
                "path": path,
                "index": start_index,
                "speed": random.uniform(30.0, 50.0)  # Initial speed
            }

    if not bus_state:
        print("❌ No buses configured.")
        return

    print("\n🚀 Simulation Started! Press Ctrl+C to stop.\n")

    # 3. Main Loop
    while True:
        for bus_id, state in bus_state.items():
            path = state["path"]
            idx = state["index"]
            
            # --- VARIABLE SPEED LOGIC ---
            # Randomly accelerate or decelerate (-5 to +5 km/h)
            fluctuation = random.uniform(-5, 5)
            new_speed = state["speed"] + fluctuation
            
            # Clamp speed: Min 0 km/h (stopped), Max 80 km/h
            state["speed"] = max(0.0, min(80.0, new_speed))
            
            # --- MOVEMENT LOGIC ---
            # Only move the bus if it has enough speed (> 5 km/h)
            # This simulates stopping at traffic lights or stops
            lat, lng = path[idx]
            
            if state["speed"] > 5.0:
                # Move to next point
                state["index"] = (idx + 1) % len(path)
                # If we are using dense OSRM points, we might want to skip points 
                # to simulate faster movement, but 1 point/sec is fine for smoothness.

            payload = {
                "vehicle_id": bus_id,
                "route_id": state["route_id"],
                "lat": lat,
                "lng": lng,
                "speed": state["speed"],
                "timestamp": datetime.utcnow().isoformat()
            }

            try:
                # Send data to backend (timeout set to avoid lag)
                requests.post(API_URL, json=payload, timeout=0.5)
            except requests.exceptions.RequestException:
                pass # Silent fail if API is down

        # Wait 1 second before next update
        time.sleep(1)

if __name__ == "__main__":
    try:
        simulate_buses()
    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped.")