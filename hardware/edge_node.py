"""
IoT Edge Node Simulator for Passenger Counting.
In a real environment, this runs on a Raspberry Pi or Nvidia Jetson nano
inside each bus, connected to an IP camera, running an OpenCV Haar Cascade
or YOLOv8 model for head/face detection.
Here, we simulate the inference loop by connecting to the backend,
finding active buses, and sending telemetry.
"""

import time
import random
import logging
import requests
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("edge_ai")

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

API_URL = "http://localhost:8000"
API_KEY = os.getenv("SIMULATOR_API_KEY", "sim-key-change-me")

# Maintain state of passenger counts to simulate realistic changes (random walk)
passenger_counts = {}

def get_active_buses():
    try:
        response = requests.get(f"{API_URL}/buses/live", timeout=5)
        response.raise_for_status()
        return [bus["vehicle_id"] for bus in response.json()]
    except Exception as e:
        logger.error(f"Failed to fetch active buses: {e}")
        return []

def send_telemetry(vehicle_id: str, count: int):
    url = f"{API_URL}/location/telemetry"
    headers = {"X-API-Key": API_KEY}
    payload = {
        "vehicle_id": vehicle_id,
        "passenger_count": count
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=2)
        res.raise_for_status()
        logger.info(f"Bus {vehicle_id} | Passenger Count: {count} | Uploaded")
    except Exception as e:
        logger.error(f"Failed to upload telemetry for {vehicle_id}: {e}")

def run_inference_loop():
    logger.info("Initializing Edge AI Passenger Counting Module...")
    logger.info("Loading OpenCV CascadeClassifier... (simulated)")
    time.sleep(2)
    logger.info("Model loaded. Starting telemetry loop.")
    
    while True:
        active_buses = get_active_buses()
        
        for bus_id in active_buses:
            if bus_id not in passenger_counts:
                # Initialize random count between 5 and 30
                passenger_counts[bus_id] = random.randint(5, 30)
            else:
                # Simulate people getting on/off (random walk bounded 0 to 50)
                change = random.randint(-3, 3)
                passenger_counts[bus_id] = max(0, min(50, passenger_counts[bus_id] + change))
            
            # Simulate inference processing time
            time.sleep(0.5)
            send_telemetry(bus_id, passenger_counts[bus_id])
            
        # Wait before next telemetry cycle
        time.sleep(5)

if __name__ == "__main__":
    run_inference_loop()
