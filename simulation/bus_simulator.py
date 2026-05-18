"""
Bus GPS Simulator — sends simulated bus position pings to the backend API.

Uses OSRM for realistic road-following paths and variable speed simulation.
Run from project root: python simulation/bus_simulator.py
"""

import time
import json
import requests
import random
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration
API_PORT = os.getenv("API_PORT", "8000")
API_URL = f"http://localhost:{API_PORT}/location"
CONFIG_PATH = PROJECT_ROOT / "simulation" / "data" / "config.json"
OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("simulator")


def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception as e:
        logger.error("Error loading config: %s", e)
        exit(1)


def fetch_osrm_path(stops):
    """Fetch detailed road path between stops using OSRM."""
    if len(stops) < 2:
        return [tuple(s["coords"]) for s in stops]

    coords_str = ";".join([f"{s['coords'][1]},{s['coords'][0]}" for s in stops])
    url = OSRM_ROUTE_URL.format(coords=coords_str)

    try:
        logger.info("Fetching road path for %d stops...", len(stops))
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and len(data["routes"]) > 0:
                path = [(p[1], p[0]) for p in data["routes"][0]["geometry"]["coordinates"]]
                logger.info("Path found: %d points", len(path))
                return path
    except Exception as e:
        logger.warning("OSRM fetch failed: %s. Using straight lines.", e)

    return [tuple(stop["coords"]) for stop in stops]


def simulate_buses():
    config = load_config()
    bus_state = {}

    logger.info("Initializing bus simulation...")

    # Pre-calculate paths for all routes
    routes_cache = {}
    for route_id, route_data in config["routes"].items():
        logger.info("Processing route: %s", route_data["routeName"])
        routes_cache[route_id] = fetch_osrm_path(route_data["stops"])

    # Assign buses to routes
    for route_id, bus_ids in config.get("bus_assignments", {}).items():
        path = routes_cache.get(route_id, [])
        if not path:
            continue

        for i, bus_id in enumerate(bus_ids):
            start_index = (i * 15) % len(path)
            bus_state[bus_id] = {
                "route_id": route_id,
                "path": path,
                "index": start_index,
                "speed": random.uniform(30.0, 50.0),
            }

    if not bus_state:
        logger.error("No buses configured.")
        return

    logger.info("Simulation started with %d buses. Press Ctrl+C to stop.", len(bus_state))

    # Main loop
    while True:
        for bus_id, state in bus_state.items():
            path = state["path"]
            idx = state["index"]

            # Variable speed: accelerate/decelerate randomly
            fluctuation = random.uniform(-5, 5)
            state["speed"] = max(0.0, min(80.0, state["speed"] + fluctuation))

            lat, lng = path[idx]

            # Only move if speed > 5 km/h (simulates traffic stops)
            if state["speed"] > 5.0:
                state["index"] = (idx + 1) % len(path)

            payload = {
                "vehicle_id": bus_id,
                "route_id": state["route_id"],
                "lat": lat,
                "lng": lng,
                "speed": state["speed"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            try:
                requests.post(API_URL, json=payload, timeout=0.5)
            except requests.exceptions.RequestException:
                pass  # Silent fail if API is down

        time.sleep(1)


if __name__ == "__main__":
    try:
        simulate_buses()
    except KeyboardInterrupt:
        logger.info("Simulation stopped.")