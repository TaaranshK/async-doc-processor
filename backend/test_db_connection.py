import asyncio
import asyncpg
import sys

async def test_connection():
    user = 'postgres'
    password = 'Guddiguddi13@'
    host = 'localhost'
    port = 5432
    
    try:
        print(f"Attempting to connect to Postgres at {host}:{port} as user '{user}'...")
        conn = await asyncpg.connect(user=user, password=password, database='postgres', host=host, port=port)
        print("✓ Connection successful!")
        
        # Check if database exists
        dbname = 'docprocessor'
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", dbname)
        
        if exists:
            print(f"✓ Database '{dbname}' already exists.")
        else:
            print(f"✗ Database '{dbname}' does not exist. Creating...")
            await conn.execute(f'CREATE DATABASE {dbname}')
            print(f"✓ Database '{dbname}' created successfully.")
        
        await conn.close()
        return True
        
    except Exception as exc:
        print(f"✗ Error: {exc}")
        print(f"  Make sure Postgres is running on {host}:{port}")
        return False

if __name__ == '__main__':
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
