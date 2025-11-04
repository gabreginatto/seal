#!/usr/bin/env python3
"""
Simple Lacre Database Schema Setup
Based on working medical database setup scripts
"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

# Lacre schema statements (same as medical)
SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        cnpj VARCHAR(18) UNIQUE NOT NULL,
        name VARCHAR(500) NOT NULL,
        government_level VARCHAR(50) NOT NULL,
        organization_type VARCHAR(50),
        state_code VARCHAR(2),
        municipality_name VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenders (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER REFERENCES organizations(id),
        cnpj VARCHAR(18) NOT NULL,
        ano INTEGER NOT NULL,
        sequencial INTEGER NOT NULL,
        control_number VARCHAR(50) UNIQUE,
        title VARCHAR(1000),
        description TEXT,
        government_level VARCHAR(50) NOT NULL,
        tender_size VARCHAR(20) NOT NULL,
        contracting_modality INTEGER,
        modality_name VARCHAR(100),
        total_estimated_value DECIMAL(15,2),
        total_homologated_value DECIMAL(15,2),
        publication_date DATE,
        state_code VARCHAR(2),
        municipality_code VARCHAR(10),
        status VARCHAR(50) DEFAULT 'discovered',
        process_category INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(cnpj, ano, sequencial)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tender_items (
        id SERIAL PRIMARY KEY,
        tender_id INTEGER REFERENCES tenders(id),
        item_number INTEGER NOT NULL,
        description TEXT NOT NULL,
        unit VARCHAR(20),
        quantity DECIMAL(12,3),
        estimated_unit_value DECIMAL(12,4),
        estimated_total_value DECIMAL(15,2),
        homologated_unit_value DECIMAL(12,4),
        homologated_total_value DECIMAL(15,2),
        winner_name VARCHAR(500),
        winner_cnpj VARCHAR(18),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tender_id, item_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS matched_products (
        id SERIAL PRIMARY KEY,
        tender_item_id INTEGER REFERENCES tender_items(id),
        fernandes_product_code VARCHAR(50) NOT NULL,
        fernandes_product_description VARCHAR(500) NOT NULL,
        match_score DECIMAL(5,2) NOT NULL,
        fob_price_usd DECIMAL(10,4),
        moq INTEGER,
        price_comparison_brl DECIMAL(10,4),
        price_comparison_usd DECIMAL(10,4),
        exchange_rate DECIMAL(8,4),
        price_difference_percent DECIMAL(6,2),
        is_competitive BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tender_item_id, fernandes_product_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS processing_log (
        id SERIAL PRIMARY KEY,
        process_type VARCHAR(50) NOT NULL,
        state_code VARCHAR(2),
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        status VARCHAR(20) NOT NULL,
        records_processed INTEGER DEFAULT 0,
        records_matched INTEGER DEFAULT 0,
        error_message TEXT,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS homologated_results (
        id SERIAL PRIMARY KEY,
        tender_item_id INTEGER REFERENCES tender_items(id),
        result_sequential INTEGER NOT NULL,
        supplier_name VARCHAR(500),
        supplier_cnpj VARCHAR(18),
        bid_value DECIMAL(15,2),
        is_winner BOOLEAN DEFAULT FALSE,
        ranking_position INTEGER,
        bid_date TIMESTAMP,
        additional_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tender_item_id, result_sequential)
    )
    """
]

async def create_lacre_schema():
    """Create lacre database schema"""

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('LACRE_DATABASE_NAME', 'pncp_lacre_data')

    connection_name = f"{project_id}:{region}:{instance_name}"

    print("=" * 70)
    print("Creating Lacre Database Schema")
    print("=" * 70)
    print(f"\nConnection: {connection_name}")
    print(f"Database: {database_name}")

    connector = Connector()

    try:
        print("\n1️⃣  Connecting to Cloud SQL...")

        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD', '')

        # Connect with password if provided, otherwise use IAM
        if db_password:
            conn = await connector.connect_async(
                instance_connection_string=connection_name,
                driver="asyncpg",
                user=db_user,
                password=db_password,
                db=database_name,
                ip_type="public"
            )
        else:
            conn = await connector.connect_async(
                instance_connection_string=connection_name,
                driver="asyncpg",
                user=db_user,
                db=database_name,
                enable_iam_auth=True,
                ip_type="public"
            )
        print("   ✅ Connected successfully")

        print("\n2️⃣  Creating tables...")
        table_names = ['organizations', 'tenders', 'tender_items', 'matched_products', 'processing_log', 'homologated_results']

        for i, (stmt, table_name) in enumerate(zip(SCHEMA_STATEMENTS, table_names), 1):
            try:
                await conn.execute(stmt)
                print(f"   ✅ {i}. {table_name}")
            except Exception as e:
                print(f"   ⚠️  {i}. {table_name}: {e}")

        print("\n3️⃣  Creating indexes...")
        # Add indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status)",
            "CREATE INDEX IF NOT EXISTS idx_tenders_state ON tenders(state_code)",
            "CREATE INDEX IF NOT EXISTS idx_tenders_publication_date ON tenders(publication_date)",
            "CREATE INDEX IF NOT EXISTS idx_tender_items_tender_id ON tender_items(tender_id)"
        ]

        for idx_stmt in indexes:
            try:
                await conn.execute(idx_stmt)
            except:
                pass
        print("   ✅ Indexes created")

        print("\n4️⃣  Verifying tables...")
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table['table_name']}")

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ Lacre Schema Creation Complete!")
        print("=" * 70)
        print(f"\nDatabase '{database_name}' is ready to use!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(create_lacre_schema())
