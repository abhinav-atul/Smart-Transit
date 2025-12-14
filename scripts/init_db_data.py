import json
import asyncio
import asyncpg
import os

# --- CONFIGURATION ---
# DB_DSN updated to use 127.0.0.1 for better Docker compatibility
DB_DSN = "postgresql://user@localhost:5433/transit_db"
# CONFIG_FILE path corrected to relative location
CONFIG_FILE = "simulation/data/config.json"

async def populate_database():
    print(f"📂 Loading data from {CONFIG_FILE}...")
    
    # 1. Load JSON Data
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: {CONFIG_FILE} not found!")
        return

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    # 2. Connection Logic with Asynchronous Retry (FIX for "Connection refused")
    print("🔌 Connecting to Database...")
    conn = None
    max_retries = 10
    retry_delay = 3

    for i in range(max_retries):
        try:
            print(f"   Attempt {i + 1}/{max_retries}...")
            # Connect to PostgreSQL
            conn = await asyncpg.connect(DB_DSN)
            print("   Connection established!")
            break  # Connection successful, exit the retry loop
        except Exception as e:
            if i < max_retries - 1:
                print(f"❌ Connection failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ Connection failed after {max_retries} attempts: {e}")
                print("   (Make sure 'docker-compose up' is running and Docker is running)")
                return # Exit the function if all retries fail

    if conn is None:
        return # Could not establish connection

    print("🚀 Inserting Routes and Stops...")
    
    # 3. Insertion Logic
    try:
        # Start a transaction to ensure all or nothing
        async with conn.transaction():
            
            # Loop through each route in config.json
            for route_id, route_data in config['routes'].items():
                route_name = route_data['routeName']
                
                # A. Insert Route
                await conn.execute("""
                    INSERT INTO routes (route_id, route_name) 
                    VALUES ($1, $2)
                    ON CONFLICT (route_id) DO UPDATE 
                    SET route_name = EXCLUDED.route_name
                """, route_id, route_name)
                
                print(f"   -> Added Route: {route_name} ({route_id})")

                # B. Insert Stops for this Route
                stops = route_data.get('stops', [])
                for idx, stop in enumerate(stops):
                    stop_name = stop['name']
                    lat = stop['coords'][0]
                    lng = stop['coords'][1]
                    
                    await conn.execute("""
                        INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence)
                        VALUES ($1, $2, $3, $4, $5)
                    """, route_id, stop_name, lat, lng, idx)
                    
        print("\n✅ Success! Database populated successfully.")

    except Exception as e:
        print(f"\n❌ Database Error: {e}")
    
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    # Python 3.7+ approach to running async main
    try:
        asyncio.run(populate_database())
    except KeyboardInterrupt:
        print("\nOperation cancelled.")