#!/usr/bin/env python3
"""
Test database connection script
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

async def test_database_connection():
    """Test database connection with detailed error reporting"""
    
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL environment variable is not set")
        return False
    
    print(f"🔍 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'Unknown host'}")
    
    try:
        # Test connection
        print("🔄 Attempting to connect...")
        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=5,
            command_timeout=30
        )
        
        # Test a simple query
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            print(f"✅ Database connection successful! Test query result: {result}")
        
        await pool.close()
        return True
        
    except asyncpg.InvalidPasswordError:
        print("❌ Invalid database password")
        print("💡 Check your DATABASE_URL password")
        return False
        
    except asyncpg.InvalidAuthorizationSpecificationError:
        print("❌ Invalid database credentials")
        print("💡 Check your DATABASE_URL username and password")
        return False
        
    except asyncpg.ConnectionDoesNotExistError:
        print("❌ Database does not exist")
        print("💡 Check your DATABASE_URL database name")
        return False
        
    except OSError as e:
        if "Network is unreachable" in str(e):
            print("❌ Network is unreachable")
            print("💡 Possible issues:")
            print("   - DATABASE_URL host is incorrect")
            print("   - Database server is down")
            print("   - Network connectivity issues")
            print("   - Firewall blocking connection")
        else:
            print(f"❌ Network error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Check your DATABASE_URL format")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    if success:
        print("\n🎉 Database connection test passed!")
    else:
        print("\n💥 Database connection test failed!")
        print("\n📋 Next steps:")
        print("1. Check your DATABASE_URL environment variable")
        print("2. Verify database credentials")
        print("3. Ensure database server is running")
        print("4. Check network connectivity")
