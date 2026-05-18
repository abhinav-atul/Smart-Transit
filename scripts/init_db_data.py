"""
Database seed script — loads route and stop data from config.json.
Idempotent: safe to run multiple times.

Run from project root: python scripts/init_db_data.py
"""

import json
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_DSN = os.getenv("DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db")
CONFIG_FILE = PROJECT_ROOT / "simulation" / "data" / "config.json"


async def populate_database():
    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found!")
        return

    config = json.loads(CONFIG_FILE.read_text())

    print("Connecting to database...")
    conn = None
    max_retries = 10
    retry_delay = 3

    for i in range(max_retries):
        try:
            conn = await asyncpg.connect(DB_DSN)
            print("Connected.")
            break
        except Exception as e:
            if i < max_retries - 1:
                print(f"Attempt {i+1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                print("Make sure Docker is running: docker compose up -d")
                return

    if conn is None:
        return

    print("Inserting routes and stops...")

    try:
        async with conn.transaction():
            for route_id, route_data in config["routes"].items():
                route_name = route_data["routeName"]

                await conn.execute("""
                    INSERT INTO routes (route_id, route_name)
                    VALUES ($1, $2)
                    ON CONFLICT (route_id) DO UPDATE
                    SET route_name = EXCLUDED.route_name
                """, route_id, route_name)

                print(f"  -> Route: {route_name} ({route_id})")

                await conn.execute("DELETE FROM stops WHERE route_id = $1", route_id)

                for idx, stop in enumerate(route_data.get("stops", [])):
                    await conn.execute("""
                        INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_sequence)
                        VALUES ($1, $2, $3, $4, $5)
                    """, route_id, stop["name"], stop["coords"][0], stop["coords"][1], idx)

        print("Database populated successfully!")

    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(populate_database())
    except KeyboardInterrupt:
        print("\nOperation cancelled.")