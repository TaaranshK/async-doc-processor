"""Initialize database tables"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    from app.core.config import get_settings
    
    settings = get_settings()
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"POSTGRES_HOST: {settings.POSTGRES_HOST}")
    print(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
    print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
    
    from app.db.session import engine
    from app.models.base import Base
    from sqlalchemy import text
    
    try:
        # First test with raw asyncpg
        print("\n--- Testing raw asyncpg connection ---")
        import asyncpg
        try:
            conn = await asyncpg.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database='postgres',
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD
            )
            print("✓ Raw asyncpg connection successful")
            await conn.close()
        except Exception as e:
            print(f"✗ Raw asyncpg failed: {e}")
        
        # Now try with SQLAlchemy
        print("\n--- Testing SQLAlchemy async engine ---")
        print(f"Connecting to: {settings.DATABASE_URL}")
        
        async with engine.begin() as conn:
            # Check what tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            existing_tables = [row[0] for row in result]
            print(f"Existing tables: {existing_tables}")
            
            if not existing_tables:
                print("\nCreating tables...")
                await conn.run_sync(Base.metadata.create_all)
                print("✓ Tables created successfully!")
            else:
                print("✓ Tables already exist")
        
        print("\n✓ Database initialization complete!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
