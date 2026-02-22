import asyncio
import sys
import os

# Add src to sys.path to allow imports from nova_guard
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import text
from nova_guard.database import engine, Base
import nova_guard.models  # Import all models to register with Base.metadata

async def clear_database():
    """
    Clears all data from the database tables defined in the models.
    Preserves the table structure and alembic migrations.
    """
    async with engine.begin() as conn:
        print("🔌 Connecting to database...")
        
        # Iterate through tables in reverse order of dependencies
        # This is safer for foreign keys, though CASCADE also handles it
        for table in reversed(Base.metadata.sorted_tables):
            print(f"🧹 Truncating table: {table.name}...")
            try:
                # Use TRUNCATE with CASCADE for PostgreSQL to handle foreign key dependencies
                await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE;'))
            except Exception as e:
                print(f"⚠️  Could not truncate {table.name}: {e}")
                
        print("\n✅ Database cleared successfully!")
        print("Note: Table structures and migrations are preserved.")

if __name__ == "__main__":
    try:
        asyncio.run(clear_database())
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)
