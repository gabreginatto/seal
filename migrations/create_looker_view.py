#!/usr/bin/env python3
"""
Database Migration: Create Looker Studio View

This migration creates the vw_lacre_items view for Looker Studio dashboards.
"""

import asyncio
import asyncpg
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.cloud.sql.connector import Connector


async def run_migration():
    """Create Looker Studio view"""

    # Database configuration from .env
    PROJECT_ID = "medical-473219"
    REGION = "us-central1"
    INSTANCE_NAME = "pncp-medical-db"
    DATABASE_NAME = "pncp_lacre_data"
    DB_USER = "postgres"
    DB_PASSWORD = "TempPass123!"
    CONNECTION_NAME = f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}"

    # Initialize Cloud SQL Python Connector
    connector = Connector()

    print(f"Connecting to database: {DATABASE_NAME}...")

    async def getconn():
        conn = await connector.connect_async(
            CONNECTION_NAME,
            "asyncpg",
            user=DB_USER,
            password=DB_PASSWORD,
            db=DATABASE_NAME,
            enable_iam_auth=False,  # Use password auth
        )
        return conn

    # Create connection
    conn = await getconn()

    try:
        print("Connected successfully!")

        # Read the SQL file from migrations directory
        sql_file_path = os.path.join(os.path.dirname(__file__), 'lacre_looker_view.sql')
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()

        print("\nCreating Looker Studio view 'vw_lacre_items'...")

        # Execute the SQL (create view)
        await conn.execute(sql_content)
        print("✓ View 'vw_lacre_items' created successfully!")

        # Test the view
        print("\nTesting view...")
        test_query = "SELECT COUNT(*) as total_lacre_items FROM vw_lacre_items;"
        result = await conn.fetchrow(test_query)

        if result:
            print(f"✓ View is working! Found {result['total_lacre_items']} lacre items")

        # Get sample data
        print("\nSample data from view:")
        sample_query = """
        SELECT
            item_description,
            organization_name,
            state_code,
            homologated_total_value,
            tender_type
        FROM vw_lacre_items
        LIMIT 5;
        """

        samples = await conn.fetch(sample_query)
        for i, row in enumerate(samples, 1):
            print(f"\n{i}. {row['item_description'][:50]}...")
            print(f"   Organization: {row['organization_name']}")
            print(f"   State: {row['state_code']}")
            print(f"   Value: R$ {row['homologated_total_value']:,.2f}")
            print(f"   Type: {row['tender_type']}")

        print(f"\n✓ Migration successful!")
        print(f"\n📊 Next Steps:")
        print(f"   1. Open Looker Studio: https://lookerstudio.google.com")
        print(f"   2. Create a new data source")
        print(f"   3. Connect to Cloud SQL: {CONNECTION_NAME}")
        print(f"   4. Select database: {DATABASE_NAME}")
        print(f"   5. Choose view: vw_lacre_items")
        print(f"   6. Start building your dashboard!")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("="*70)
    print("DATABASE MIGRATION: Create Looker Studio View")
    print("="*70)
    print()

    asyncio.run(run_migration())

    print()
    print("="*70)
    print("Migration complete!")
    print("="*70)
