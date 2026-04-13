"""Test if database tables exist"""
import asyncio
import sys
sys.path.insert(0, '/Users/taara/OneDrive/DATA/Desktop/Assignment/async-doc-processor/backend')

from app.db.session import engine
from app.models.base import Base
from app.models.job_model import Job
from app.models.document_model import Document
from app.models.result_model import Result
from app.models.user_model import User
from sqlalchemy import inspect, text

async def check_tables():
    """Check what tables exist in the database"""
    async with engine.begin() as conn:
        # Check what tables exist
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        existing_tables = [row[0] for row in result]
        print("Existing tables in PostgreSQL:")
        for table in existing_tables:
            print(f"  - {table}")
        
        if not existing_tables:
            print("  (no tables found)")
            print("\nNeed to create tables...")
            # Create all tables
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ Tables created successfully!")
            
            # Verify
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            new_tables = [row[0] for row in result]
            print("\nNew tables created:")
            for table in new_tables:
                print(f"  - {table}")

if __name__ == "__main__":
    asyncio.run(check_tables())
