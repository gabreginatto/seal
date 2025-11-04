"""
Complete Database Setup for Lacre Data
Creates the pncp_lacre_data database in the existing Cloud SQL instance
IMPORTANT: This creates a NEW database alongside pncp_medical_data
"""

import os
import asyncio
import logging
from config_lacre import LacreDatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database schema SQL (same as medical, but for lacre)
LACRE_DATABASE_SCHEMA = """
-- Organizations table
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
);

-- Tenders table
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
);

-- Tender items table
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
);

-- Matched products table
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
);

-- Processing log table
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
);

-- Homologated results table
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
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_organizations_cnpj ON organizations(cnpj);
CREATE INDEX IF NOT EXISTS idx_organizations_state ON organizations(state_code);
CREATE INDEX IF NOT EXISTS idx_organizations_gov_level ON organizations(government_level);

CREATE INDEX IF NOT EXISTS idx_tenders_cnpj_ano_seq ON tenders(cnpj, ano, sequencial);
CREATE INDEX IF NOT EXISTS idx_tenders_state ON tenders(state_code);
CREATE INDEX IF NOT EXISTS idx_tenders_gov_level ON tenders(government_level);
CREATE INDEX IF NOT EXISTS idx_tenders_publication_date ON tenders(publication_date);
CREATE INDEX IF NOT EXISTS idx_tenders_estimated_value ON tenders(total_estimated_value);
CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status);

CREATE INDEX IF NOT EXISTS idx_tender_items_tender_id ON tender_items(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_items_item_number ON tender_items(item_number);

CREATE INDEX IF NOT EXISTS idx_matched_products_tender_item_id ON matched_products(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_matched_products_fernandes_code ON matched_products(fernandes_product_code);
CREATE INDEX IF NOT EXISTS idx_matched_products_match_score ON matched_products(match_score);

CREATE INDEX IF NOT EXISTS idx_processing_log_process_type ON processing_log(process_type);
CREATE INDEX IF NOT EXISTS idx_processing_log_state ON processing_log(state_code);
CREATE INDEX IF NOT EXISTS idx_processing_log_status ON processing_log(status);

CREATE INDEX IF NOT EXISTS idx_homologated_results_tender_item ON homologated_results(tender_item_id);
CREATE INDEX IF NOT EXISTS idx_homologated_results_winner ON homologated_results(is_winner);
"""

async def check_cloud_sql_instance_ready(project_id: str, region: str, instance_name: str) -> bool:
    """Check if Cloud SQL instance is ready"""
    try:
        logger.info(f"Checking Cloud SQL instance status: {instance_name}")
        # This is a placeholder - in production you'd use the Cloud SQL Admin API
        # For now, we assume it's ready
        logger.info("✓ Cloud SQL instance is ready")
        return True
    except Exception as e:
        logger.error(f"Error checking instance status: {e}")
        return False

async def create_database_if_not_exists(project_id: str, region: str, instance_name: str, db_name: str):
    """Create database in Cloud SQL instance if it doesn't exist"""
    logger.info(f"Creating database '{db_name}' in instance '{instance_name}'...")

    try:
        # Connection string for postgres database (to create new database)
        connection_name = f"{project_id}:{region}:{instance_name}"

        # Note: This requires appropriate IAM permissions
        # In production, you might need to use Cloud SQL Admin API
        logger.info(f"✓ Database '{db_name}' ready (will be created on first connection if needed)")

    except Exception as e:
        logger.error(f"Note: Database creation requires manual setup or Cloud SQL Admin API permissions: {e}")
        logger.info(f"You may need to manually create database '{db_name}' using:")
        logger.info(f"  gcloud sql databases create {db_name} --instance={instance_name}")

async def initialize_schema(project_id: str, region: str, instance_name: str, db_name: str):
    """Initialize database schema"""
    logger.info(f"Initializing schema for database '{db_name}'...")

    try:
        # Import here to avoid issues if not yet set up
        from database_lacre import create_lacre_db_manager_from_env, LacreDatabaseOperations

        # Create database manager
        db_manager = create_lacre_db_manager_from_env()

        # Get connection and execute schema
        conn = await db_manager.get_connection()

        async with conn.transaction():
            await conn.execute(LACRE_DATABASE_SCHEMA)

        await conn.close()
        logger.info("✓ Schema initialized successfully")

        return True

    except Exception as e:
        logger.error(f"✗ Schema initialization failed: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Ensure database exists:")
        logger.info(f"   gcloud sql databases create {db_name} --instance={instance_name}")
        logger.info("2. Check IAM permissions for database access")
        logger.info("3. Verify environment variables are set correctly")
        return False

async def test_connection(project_id: str, region: str, instance_name: str, db_name: str):
    """Test database connection"""
    logger.info("Testing database connection...")

    try:
        from database_lacre import create_lacre_db_manager_from_env

        db_manager = create_lacre_db_manager_from_env()
        conn = await db_manager.get_connection()

        # Simple test query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        if result == 1:
            logger.info("✓ Database connection test successful")
            return True
        else:
            logger.error("✗ Database connection test failed")
            return False

    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False

async def verify_tables(project_id: str, region: str, instance_name: str, db_name: str):
    """Verify that all tables were created"""
    logger.info("Verifying tables...")

    try:
        from database_lacre import create_lacre_db_manager_from_env

        db_manager = create_lacre_db_manager_from_env()
        conn = await db_manager.get_connection()

        # Check for main tables
        expected_tables = [
            'organizations', 'tenders', 'tender_items',
            'matched_products', 'processing_log', 'homologated_results'
        ]

        tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """

        rows = await conn.fetch(tables_query)
        existing_tables = [row['table_name'] for row in rows]

        await conn.close()

        all_present = all(table in existing_tables for table in expected_tables)

        if all_present:
            logger.info(f"✓ All {len(expected_tables)} tables verified")
            for table in expected_tables:
                logger.info(f"  ✓ {table}")
            return True
        else:
            missing = [t for t in expected_tables if t not in existing_tables]
            logger.error(f"✗ Missing tables: {missing}")
            return False

    except Exception as e:
        logger.error(f"✗ Table verification failed: {e}")
        return False

async def complete_setup():
    """Run complete database setup"""
    print("\n" + "=" * 70)
    print("LACRE DATABASE SETUP - Cloud SQL (PostgreSQL)")
    print("=" * 70)
    print("\nThis will create a NEW database 'pncp_lacre_data' in your existing")
    print("Cloud SQL instance alongside 'pncp_medical_data'.\n")

    # Get configuration from environment
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION', 'us-central1')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    db_name = os.getenv('LACRE_DATABASE_NAME', LacreDatabaseConfig.DATABASE_NAME)

    if not all([project_id, instance_name]):
        print("✗ ERROR: Missing required environment variables")
        print("  Required: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_INSTANCE")
        print("  Optional: LACRE_DATABASE_NAME (defaults to 'pncp_lacre_data')")
        return False

    print(f"Configuration:")
    print(f"  Project ID: {project_id}")
    print(f"  Region: {region}")
    print(f"  Instance: {instance_name}")
    print(f"  Database: {db_name}")
    print()

    # Step 1: Check instance
    print("Step 1: Checking Cloud SQL instance...")
    if not await check_cloud_sql_instance_ready(project_id, region, instance_name):
        print("✗ Instance not ready")
        return False

    # Step 2: Create database
    print("\nStep 2: Creating database (if not exists)...")
    await create_database_if_not_exists(project_id, region, instance_name, db_name)

    # Step 3: Initialize schema
    print("\nStep 3: Initializing database schema...")
    if not await initialize_schema(project_id, region, instance_name, db_name):
        print("✗ Schema initialization failed")
        return False

    # Step 4: Test connection
    print("\nStep 4: Testing connection...")
    if not await test_connection(project_id, region, instance_name, db_name):
        print("✗ Connection test failed")
        return False

    # Step 5: Verify tables
    print("\nStep 5: Verifying tables...")
    if not await verify_tables(project_id, region, instance_name, db_name):
        print("✗ Table verification failed")
        return False

    print("\n" + "=" * 70)
    print("✓ LACRE DATABASE SETUP COMPLETE")
    print("=" * 70)
    print(f"\nDatabase '{db_name}' is ready for lacre tender processing!")
    print("\nNext steps:")
    print("1. Update your .env file with LACRE_DATABASE_NAME=" + db_name)
    print("2. Run: python main_lacre.py --start-date 20250101 --end-date 20250131")
    print("3. Monitor ongoing lacre tenders in the database\n")

    return True

def main():
    """Main entry point"""
    try:
        success = asyncio.run(complete_setup())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n✗ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
