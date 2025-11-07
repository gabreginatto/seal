#!/usr/bin/env python3
"""
Database Migration: Add is_lacre column to tender_items table

This migration adds a boolean column to mark which items in a tender are lacre items.
This is critical for V3 heterogeneous item detection.
"""

import asyncio
import asyncpg
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.cloud.sql.connector import Connector


async def run_migration():
    """Add is_lacre column to tender_items table"""

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

        # Check if column already exists
        check_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'tender_items'
        AND column_name = 'is_lacre';
        """

        result = await conn.fetch(check_query)

        if result:
            print("✓ Column 'is_lacre' already exists in tender_items table")
            return

        print("Adding 'is_lacre' column to tender_items table...")

        # Add the column
        add_column_query = """
        ALTER TABLE tender_items
        ADD COLUMN is_lacre BOOLEAN DEFAULT FALSE NOT NULL;
        """

        await conn.execute(add_column_query)
        print("✓ Column 'is_lacre' added successfully!")

        # Create index for better query performance
        print("Creating index on is_lacre column...")
        create_index_query = """
        CREATE INDEX idx_tender_items_is_lacre
        ON tender_items(is_lacre)
        WHERE is_lacre = TRUE;
        """

        await conn.execute(create_index_query)
        print("✓ Index created successfully!")

        # Verify the column was added
        verify_query = """
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'tender_items'
        AND column_name = 'is_lacre';
        """

        result = await conn.fetch(verify_query)
        if result:
            row = result[0]
            print(f"\n✓ Migration successful!")
            print(f"  Column: {row['column_name']}")
            print(f"  Type: {row['data_type']}")
            print(f"  Default: {row['column_default']}")
            print(f"  Nullable: {row['is_nullable']}")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise

    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("="*70)
    print("DATABASE MIGRATION: Add is_lacre column to tender_items")
    print("="*70)
    print()

    asyncio.run(run_migration())

    print()
    print("="*70)
    print("Migration complete!")
    print("="*70)
