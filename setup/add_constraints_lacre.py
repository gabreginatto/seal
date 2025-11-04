#!/usr/bin/env python3
"""Add missing constraints to lacre database"""

import asyncio
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

load_dotenv()

async def add_constraints():
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('LACRE_DATABASE_NAME', 'pncp_lacre_data')
    
    connection_name = f"{project_id}:{region}:{instance_name}"
    
    print("Adding missing constraints to lacre database...")
    
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
        
        # Add unique constraint on tenders
        try:
            await conn.execute("""
                ALTER TABLE tenders 
                ADD CONSTRAINT tenders_cnpj_ano_seq_unique 
                UNIQUE (cnpj, ano, sequencial)
            """)
            print("✅ Added UNIQUE constraint on tenders(cnpj, ano, sequencial)")
        except Exception as e:
            print(f"⚠️  Tenders constraint: {e}")
        
        # Add unique constraint on tender_items  
        try:
            await conn.execute("""
                ALTER TABLE tender_items
                ADD CONSTRAINT tender_items_tender_item_unique
                UNIQUE (tender_id, item_number)
            """)
            print("✅ Added UNIQUE constraint on tender_items(tender_id, item_number)")
        except Exception as e:
            print(f"⚠️  Tender items constraint: {e}")
        
        await conn.close()
        print("\n✅ Constraints added successfully!")
        
    finally:
        await connector.close_async()

if __name__ == "__main__":
    asyncio.run(add_constraints())
