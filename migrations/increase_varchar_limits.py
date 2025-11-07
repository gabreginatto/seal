#!/usr/bin/env python3
"""
Database Migration: Increase VARCHAR limits for text fields

This migration increases VARCHAR limits for tender title fields that may exceed 1000 characters.
Some tender titles from PNCP API can be very long and were causing save failures.
"""

import asyncio
import asyncpg
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.cloud.sql.connector import Connector


async def run_migration():
    """Increase VARCHAR limits for text fields"""

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

        # Check current column type
        check_query = """
        SELECT column_name, character_maximum_length, data_type
        FROM information_schema.columns
        WHERE table_name = 'tenders'
        AND column_name = 'title';
        """

        result = await conn.fetch(check_query)
        if result:
            row = result[0]
            print(f"\nCurrent schema for 'title' column:")
            print(f"  Column: {row['column_name']}")
            print(f"  Type: {row['data_type']}")
            print(f"  Max Length: {row['character_maximum_length']}")

        print("\nIncreasing VARCHAR limit for 'title' column to 5000 characters...")

        # Increase the title column from VARCHAR(1000) to VARCHAR(5000)
        alter_query = """
        ALTER TABLE tenders
        ALTER COLUMN title TYPE VARCHAR(5000);
        """

        await conn.execute(alter_query)
        print("✓ Column 'title' VARCHAR limit increased to 5000!")

        # Verify the change
        verify_query = """
        SELECT column_name, character_maximum_length, data_type
        FROM information_schema.columns
        WHERE table_name = 'tenders'
        AND column_name = 'title';
        """

        result = await conn.fetch(verify_query)
        if result:
            row = result[0]
            print(f"\n✓ Migration successful!")
            print(f"  Column: {row['column_name']}")
            print(f"  Type: {row['data_type']}")
            print(f"  New Max Length: {row['character_maximum_length']}")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise

    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("="*70)
    print("DATABASE MIGRATION: Increase VARCHAR limits for text fields")
    print("="*70)
    print()

    asyncio.run(run_migration())

    print()
    print("="*70)
    print("Migration complete!")
    print("="*70)
