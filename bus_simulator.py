import time
import json
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from geopy.distance import geodesic
import googlemaps

# --- Configuration ---
APP_ID = 'transitnow-prototype'
# IMPORTANT: Make sure to replace this with your actual Google Maps API key
GOOGLE_MAPS_API_KEY = "AIzaSyDec5RO1JPrJdX0X5ntqupEU8RQ8rxDiwM" 

# --- Load Configuration from JSON File ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    print("Successfully loaded route and bus configuration.")
except Exception as e:
    print(f"Error loading config.json: {e}")
    exit()

# --- Firebase Admin SDK Setup ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Error connecting to Firebase: {e}")
    exit()

def initialize_routes_and_stops():
    """
    Sets up the routes in Firestore based on the config file. 
    You only need to run this once or when your routes change.
    """
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    print("Initializing routes and stops from config.json...")
    
    for route_id, route_data in config['routes'].items():
        print(f"Processing route: {route_id}...")
        stop_list = route_data['stops']
        full_path_coords = []
        if len(stop_list) > 1:
            for i in range(len(stop_list) - 1):
                start_coords = tuple(stop_list[i]["coords"])
                end_coords = tuple(stop_list[i+1]["coords"])
                try:
                    directions = gmaps.directions(start_coords, end_coords, mode="driving")
                    if directions:
                        polyline = directions[0]['overview_polyline']['points']
                        path_segment = googlemaps.convert.decode_polyline(polyline)
                        full_path_coords.extend([(p['lat'], p['lng']) for p in path_segment[:-1]])
                except Exception as e:
                    print(f"  Could not fetch segment for {route_id}: {e}")
            if full_path_coords:
                 full_path_coords.append(tuple(stop_list[-1]["coords"]))

        route_doc_ref = db.collection(f'artifacts/{APP_ID}/routes').document(route_id)
        route_doc = { "routeName": route_data['routeName'], "path": [firestore.GeoPoint(lat, lng) for lat, lng in full_path_coords] }
        route_doc_ref.set(route_doc)

        stops_col_ref = route_doc_ref.collection('stops')
        for i, stop in enumerate(stop_list):
            stop_doc = { "name": stop["name"], "position": firestore.GeoPoint(stop["coords"][0], stop["coords"][1]), "order": i }
            stops_col_ref.document(f"stop_{i:02}").set(stop_doc)
        print(f"  Successfully saved route {route_id} with {len(stop_list)} stops.")
        time.sleep(1) # To avoid hitting API rate limits
    print("All routes and stops initialized.")

def simulate_buses():
    """
    Main simulation loop that continuously updates bus locations in Firestore.
    """
    bus_data = {}
    
    # Fetch the route path data from Firestore to guide the buses
    all_routes_from_db = {}
    routes_snapshot = db.collection(f'artifacts/{APP_ID}/routes').stream()
    for route in routes_snapshot:
        route_data = route.to_dict()
        path_tuples = [(gp.latitude, gp.longitude) for gp in route_data.get('path', [])]
        stops_snapshot = route.reference.collection('stops').order_by("order").stream()
        stops_list = [(s.to_dict()['position'].latitude, s.to_dict()['position'].longitude) for s in stops_snapshot]
        
        if len(stops_list) >= 2:
            all_routes_from_db[route.id] = {"path": path_tuples, "stops": stops_list}

    if not all_routes_from_db:
        print("No valid routes found in Firestore. Cannot start simulation.")
        return

    # Assign buses to routes based on the config file
    bus_assignments = config.get('bus_assignments', {})
    for route_id, bus_ids in bus_assignments.items():
        if route_id not in all_routes_from_db:
            continue
        for bus_id in bus_ids:
            bus_data[bus_id] = {
                "routeId": route_id,
                "path": all_routes_from_db[route_id]["path"],
                "stops": all_routes_from_db[route_id]["stops"],
                "segment_index": 0, # Current position on the path
                "next_stop_index": 1, # The upcoming stop
            }

    print("Starting simplified GPS simulation...")
    buses_col_ref = db.collection(f'artifacts/{APP_ID}/buses')

    while True:
        for bus_id, data in bus_data.items():
            path = data.get("path", [])
            if not path:
                continue

            # --- SIMPLIFIED MOVEMENT LOGIC ---
            # Move to the next point on the path array
            data["segment_index"] += 1
            
            # If the bus reaches the end of the path, loop back to the start
            if data["segment_index"] >= len(path):
                data["segment_index"] = 0
                data["next_stop_index"] = 1 # Reset next stop as well

            # Update the next stop index if the bus is near it
            if data["next_stop_index"] < len(data["stops"]):
                current_pos = path[data["segment_index"]]
                next_stop_pos = data["stops"][data["next_stop_index"]]
                # If bus is within 100 meters of the next stop, update its target
                if geodesic(current_pos, next_stop_pos).m < 100:
                    data["next_stop_index"] += 1

            final_pos = path[data["segment_index"]]

            # --- SIMPLIFIED FIRESTORE PAYLOAD ---
            # This is the pure GPS data sent to the frontend
            bus_doc_ref = buses_col_ref.document(bus_id)
            bus_doc_ref.set({
                "routeId": data["routeId"],
                "lat": final_pos[0],
                "lng": final_pos[1],
                "timestamp": firestore.SERVER_TIMESTAMP,
                "next_stop_index": data["next_stop_index"]
            })
            print(f"Updating GPS for bus: {bus_id} on Route: {data['routeId']}")

        # Controls the speed of the simulation
        time.sleep(2) 

if __name__ == "__main__":
    # Note: You can comment out initialize_routes_and_stops() after running it once
    # to avoid re-fetching route directions from Google Maps every time you start.
    # initialize_routes_and_stops()
    simulate_buses()

