import requests
import time
import random

API_URL = "http://localhost:8000/api/v1"

def simulate():
    print("Starting Bus Simulator...")
    
    # Starting State
    lat, lon = 28.7041, 77.1025 # Example coords
    current_stop = "STOP_A"
    next_stop = "STOP_B"
    progress = 0.0
    
    while True:
        # 1. Simulate Motion
        lat += 0.0001
        lon += 0.0001
        speed = random.uniform(15, 55) # Variable speed
        progress += 0.05 # Move 5% closer to next stop
        
        if progress >= 1.0:
            progress = 0.0
            current_stop = next_stop
            next_stop = "STOP_C" if next_stop == "STOP_B" else "STOP_D"
            print(f"--- ARRIVED AT {current_stop} ---")

        # 2. Payload for Location
        gps_payload = {
            "vehicle_id": "BUS-101",
            "latitude": lat,
            "longitude": lon,
            "speed": speed,
            "timestamp": time.time(),
            "route_id": "ROUTE_1"
        }

        # 3. Payload for ETA Request
        eta_payload = {
            "current_stop_id": current_stop,
            "next_stop_id": next_stop,
            "progress_percent": progress,
            "current_speed": speed
        }

        try:
            # Send GPS
            requests.post(f"{API_URL}/location", json=gps_payload)
            
            # Get ETA
            resp = requests.post(f"{API_URL}/eta", json=eta_payload)
            if resp.status_code == 200:
                data = resp.json()
                print(f"Bus: {current_stop}->{next_stop} | Speed: {int(speed)}km/h | ETA: {data['eta_minutes']} min | Status: {data['status']}")
        
        except Exception as e:
            print(f"Connection Error: {e}")

        time.sleep(2)

if __name__ == "__main__":
    simulate()