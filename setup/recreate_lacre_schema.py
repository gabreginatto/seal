#!/usr/bin/env python3
"""
Recreate lacre schema to EXACTLY match medical schema
"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

# EXACT schema from medical database
TABLES = {
    'organizations': """
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
    'tenders': """
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
            status VARCHAR(50),
            process_category INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cnpj, ano, sequencial)
        )
    """,
    'tender_items': """
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
    'matched_products': """
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
    'processing_log': """
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
    'homologated_results': """
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
}

async def recreate_schema():
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('LACRE_DATABASE_NAME', 'pncp_lacre_data')
    
    connection_name = f"{project_id}:{region}:{instance_name}"
    
    print("=" * 70)
    print("Recreating Lacre Schema to Match Medical Schema EXACTLY")
    print("=" * 70)
    
    connector = Connector()
    
    try:
        conn = await connector.connect_async(
            instance_connection_string=connection_name,
            driver="asyncpg",
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=database_name,
            ip_type="public"
        )
        
        print("\n1️⃣  Dropping existing tables (in correct order)...")
        drop_order = ['homologated_results', 'matched_products', 'tender_items', 'tenders', 'organizations', 'processing_log']
        for table in drop_order:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"   ✅ Dropped {table}")
            except Exception as e:
                print(f"   ⚠️  {table}: {e}")
        
        print("\n2️⃣  Creating tables (EXACT medical schema)...")
        for table_name, create_stmt in TABLES.items():
            try:
                await conn.execute(create_stmt)
                print(f"   ✅ {table_name}")
            except Exception as e:
                print(f"   ❌ {table_name}: {e}")
                raise
        
        print("\n3️⃣  Verifying tables...")
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
        print("✅ Lacre Schema Now EXACTLY Matches Medical Schema!")
        print("=" * 70)
        
    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(recreate_schema())
