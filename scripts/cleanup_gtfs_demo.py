"""
Cleanup script — removes GTFS demo routes (Lahore) from the database.
Only the original Amritsar routes (RT-101, RT-202, RT-303) are kept.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DB = os.getenv("DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db")

async def clean():
    conn = await asyncpg.connect(DB)
    await conn.execute("DELETE FROM stops WHERE route_id LIKE 'GTFS-%'")
    await conn.execute("DELETE FROM routes WHERE route_id LIKE 'GTFS-%'")
    remaining = await conn.fetch("SELECT route_id, route_name FROM routes ORDER BY route_id")
    print("Remaining routes after cleanup:")
    for r in remaining:
        print(f"  {r['route_id']}: {r['route_name']}")
    await conn.close()

asyncio.run(clean())
