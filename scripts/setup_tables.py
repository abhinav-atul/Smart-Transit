import asyncio
import asyncpg
import os

# Database Connection String
DB_DSN = "postgresql://user@localhost:5433/transit_db"
# Path to your schema file
SCHEMA_FILE = "backend/app/db/schema.sql"

async def create_tables():
    print(f"🔌 Connecting to Database at {DB_DSN}...")
    try:
        conn = await asyncpg.connect(DB_DSN)
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    print(f"📂 Reading schema from {SCHEMA_FILE}...")
    if not os.path.exists(SCHEMA_FILE):
        print(f"❌ Error: Schema file not found at {SCHEMA_FILE}")
        print("   Make sure you are running this script from the project root folder.")
        return

    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()

    print("🚀 Creating Tables...")
    try:
        # asyncpg allows executing a script with multiple statements
        await conn.execute(schema_sql)
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ SQL Execution Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())