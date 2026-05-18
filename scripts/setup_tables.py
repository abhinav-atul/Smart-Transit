"""
Database schema creation script.
Run from project root: python scripts/setup_tables.py
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_DSN = os.getenv("DATABASE_URL", "postgresql://user:secretpass123@localhost:5433/transit_db")
SCHEMA_FILE = PROJECT_ROOT / "backend" / "app" / "db" / "schema.sql"


async def create_tables():
    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure Docker is running: docker compose up -d")
        return

    if not SCHEMA_FILE.exists():
        print(f"Error: Schema file not found at {SCHEMA_FILE}")
        return

    schema_sql = SCHEMA_FILE.read_text()

    print("Creating tables...")
    try:
        await conn.execute(schema_sql)
        print("Tables created successfully!")
    except Exception as e:
        print(f"SQL execution error: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_tables())