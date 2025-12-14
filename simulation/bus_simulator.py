import time
import json
import requests
from datetime import datetime
from geopy.distance import geodesic

API_URL = "http://localhost:8000/location"

# --- Load Configuration ---
CONFIG_PATH = "simulation/data/config.json"

try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    print("✅ Successfully loaded route and bus configuration.")
except Exception as e:
    print(f"❌ Error loading config.json: {e}")
    exit(1)


def simulate_buses():
    """
    Sends simulated GPS pings for buses to the FastAPI backend.
    """
    bus_data = {}

    # Prepare routes from config.json
    for route_id, route_data in config["routes"].items():
        stops = route_data["stops"]

        # Convert stops to (lat, lng) tuples
        path = [tuple(stop["coords"]) for stop in stops]

        if len(path) < 2:
            continue

        # Assign buses to this route
        bus_ids = config.get("bus_assignments", {}).get(route_id, [])
        for bus_id in bus_ids:
            bus_data[bus_id] = {
                "route_id": route_id,
                "path": path,
                "index": 0,
            }

    if not bus_data:
        print("❌ No buses found to simulate.")
        return

    print("🚌 Starting bus GPS simulation...")

    while True:
        for bus_id, data in bus_data.items():
            path = data["path"]

            # Move to next point
            data["index"] = (data["index"] + 1) % len(path)
            lat, lng = path[data["index"]]

            payload = {
                "vehicle_id": bus_id,
                "route_id": data["route_id"],
                "lat": lat,
                "lng": lng,
                "speed": 40.0,
                "timestamp": datetime.utcnow().isoformat()
            }

            try:
                response = requests.post(API_URL, json=payload, timeout=3)
                print(f"📡 Sent ping → {bus_id} ({response.status_code})")
            except Exception as e:
                print(f"❌ API Error for {bus_id}: {e}")

        time.sleep(2)


if __name__ == "__main__":
    simulate_buses()
