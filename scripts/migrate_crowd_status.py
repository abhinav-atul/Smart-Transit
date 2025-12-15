#!/usr/bin/env python3
"""
Database migration script to add crowd_status column to vehicle_logs table.
This is for existing installations that need to be updated.
"""

import asyncio
import asyncpg
import sys

DB_DSN = "postgresql://user@localhost:5433/transit_db"

async def migrate_database():
    """Add crowd_status column if it doesn't exist."""
    print("🔄 Starting database migration...")
    
    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = await asyncpg.connect(DB_DSN)
        print("✓ Connected successfully")
        
        # Check if column exists
        print("\n🔍 Checking if crowd_status column exists...")
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='vehicle_logs' 
            AND column_name='crowd_status'
        """
        result = await conn.fetch(check_query)
        
        if result:
            print("ℹ️  Column 'crowd_status' already exists. No migration needed.")
        else:
            print("📝 Adding crowd_status column...")
            alter_query = """
                ALTER TABLE vehicle_logs 
                ADD COLUMN crowd_status VARCHAR(20) DEFAULT 'unknown'
            """
            await conn.execute(alter_query)
            print("✓ Column added successfully")
            
            # Update existing records
            print("\n🔄 Updating existing records to set default value...")
            update_query = """
                UPDATE vehicle_logs 
                SET crowd_status = 'unknown' 
                WHERE crowd_status IS NULL
            """
            result = await conn.execute(update_query)
            print(f"✓ Updated records: {result}")
        
        # Verify the column
        print("\n✅ Verifying schema...")
        verify_query = """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name='vehicle_logs'
            ORDER BY ordinal_position
        """
        columns = await conn.fetch(verify_query)
        
        print("\nCurrent vehicle_logs schema:")
        print("-" * 60)
        for col in columns:
            default = col['column_default'] if col['column_default'] else 'NULL'
            print(f"  {col['column_name']:<20} {col['data_type']:<15} {default}")
        print("-" * 60)
        
        await conn.close()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Smart Transit - Database Migration")
    print("Adding crowd_status column to vehicle_logs table")
    print("=" * 60)
    print()
    
    try:
        success = asyncio.run(migrate_database())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
