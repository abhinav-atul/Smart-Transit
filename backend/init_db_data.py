import json
import asyncio
import asyncpg
import os

# --- CONFIGURATION ---
DB_DSN = "postgresql://user:password@localhost:5432/transit_db"
CONFIG_FILE = "config.json"

async def populate_database():
    print(f"📂 Loading data from {CONFIG_FILE}...")
    
    # 1. Load JSON Data
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: {CONFIG_FILE} not found!")
        return

    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    print("🔌 Connecting to Database...")
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   (Make sure 'docker-compose up' is running)")
        return

    print("🚀 Inserting Routes and Stops...")
    
    try:
        # Start a transaction to ensure all or nothing
        async with conn.transaction():
            
            # Loop through each route in config.json
            for route_id, route_data in config['routes'].items():
                route_name = route_data['routeName']
                
                # A. Insert Route
                # ON CONFLICT DO NOTHING prevents errors if you run this script twice
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
                    
                    # We treat (route_id, stop_sequence) as a unique constraint logically
                    # but for simplicity, we just insert. 
                    # Note: Ideally, clear old stops for this route first if updating.
                    await conn.execute("""
                        INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence)
                        VALUES ($1, $2, $3, $4, $5)
                    """, route_id, stop_name, lat, lng, idx)
                    
        print("\n✅ Success! Database populated successfully.")

    except Exception as e:
        print(f"\n❌ Database Error: {e}")
    
    finally:
        await conn.close()

if __name__ == "__main__":
    # Python 3.7+ approach to running async main
    try:
        asyncio.run(populate_database())
    except KeyboardInterrupt:
        print("\nOperation cancelled.")