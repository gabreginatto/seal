"""
GCP Cloud SQL (PostgreSQL) database module for PNCP medical data processing
Handles database connections, schema creation, and data operations
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import asyncpg
from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DatabaseConfig, GovernmentLevel, TenderSize, OrganizationType

logger = logging.getLogger(__name__)

class CloudSQLManager:
    """Manages connections and operations for GCP Cloud SQL PostgreSQL"""

    def __init__(self, project_id: str, region: str, instance_name: str, database_name: str = None):
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.database_name = database_name or DatabaseConfig.DATABASE_NAME
        self.connection_name = f"{project_id}:{region}:{instance_name}"

        self.connector = Connector()
        self.engine = None
        self.async_engine = None

    def get_connection_string(self, use_async: bool = False) -> str:
        """Generate connection string for Cloud SQL"""
        if DatabaseConfig.USE_IAM_AUTH:
            # Use IAM authentication
            if use_async:
                return f"postgresql+asyncpg://{self.database_name}"
            else:
                return f"postgresql+pg8000://{self.database_name}"
        else:
            # Use username/password (for development/testing)
            user = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', '')
            if use_async:
                return f"postgresql+asyncpg://{user}:{password}@/{self.database_name}"
            else:
                return f"postgresql+pg8000://{user}:{password}@/{self.database_name}"

    async def get_connection(self):
        """Get async database connection using Cloud SQL connector"""
        # Check if password is provided - if so, use password auth
        db_password = os.getenv('DB_PASSWORD', '')
        use_password_auth = bool(db_password)

        # Check USE_PRIVATE_IP from env first, then config
        use_private_ip = os.getenv('USE_PRIVATE_IP', 'false').lower() == 'true'

        return await self.connector.connect_async(
            instance_connection_string=self.connection_name,
            driver="asyncpg",
            user=os.getenv('DB_USER', 'postgres'),
            password=db_password if use_password_auth else None,
            db=self.database_name,
            enable_iam_auth=not use_password_auth,
            ip_type="private" if use_private_ip else "public"
        )

    def create_sync_engine(self):
        """Create synchronous SQLAlchemy engine"""
        if self.engine is None:
            self.engine = create_engine(
                self.get_connection_string(use_async=False),
                creator=self._get_sync_connection,
                pool_size=DatabaseConfig.MAX_CONNECTIONS,
                pool_timeout=DatabaseConfig.CONNECTION_TIMEOUT,
                echo=False  # Set to True for SQL debugging
            )
        return self.engine

    def create_async_engine(self):
        """Create asynchronous SQLAlchemy engine"""
        if self.async_engine is None:
            self.async_engine = create_async_engine(
                self.get_connection_string(use_async=True),
                creator=self._get_async_connection,
                pool_size=DatabaseConfig.MAX_CONNECTIONS,
                pool_timeout=DatabaseConfig.CONNECTION_TIMEOUT,
                echo=False  # Set to True for SQL debugging
            )
        return self.async_engine

    def _get_sync_connection(self):
        """Get synchronous connection for SQLAlchemy"""
        # This would need to be implemented based on your specific Cloud SQL setup
        # For now, using standard asyncpg connection
        pass

    async def _get_async_connection(self):
        """Get asynchronous connection for SQLAlchemy"""
        return await self.get_connection()

    async def close(self):
        """Close connector and engines"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        await self.connector.close_async()

# Database schema SQL
DATABASE_SCHEMA = """
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
    price_comparison_brl DECIMAL(10,4), -- Homologated price in BRL
    price_comparison_usd DECIMAL(10,4), -- Converted price in USD
    exchange_rate DECIMAL(8,4), -- USD/BRL rate used
    price_difference_percent DECIMAL(6,2), -- % difference from FOB
    is_competitive BOOLEAN, -- Whether homologated price is competitive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_item_id, fernandes_product_code)
);

-- Processing log table
CREATE TABLE IF NOT EXISTS processing_log (
    id SERIAL PRIMARY KEY,
    process_type VARCHAR(50) NOT NULL, -- 'tender_discovery', 'item_extraction', 'price_analysis'
    state_code VARCHAR(2),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    records_matched INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB, -- Additional process metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Homologated results table (detailed results storage)
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
    additional_data JSONB, -- Store any additional result data
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
CREATE INDEX IF NOT EXISTS idx_tenders_homologated_value ON tenders(total_homologated_value);

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

class DatabaseOperations:
    """Database operations for PNCP medical data"""

    def __init__(self, db_manager: CloudSQLManager):
        self.db_manager = db_manager

    async def initialize_database(self):
        """Create database schema"""
        try:
            conn = await self.db_manager.get_connection()
            async with conn.transaction():
                await conn.execute(DATABASE_SCHEMA)
            await conn.close()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def insert_organization(self, org_data: Dict[str, Any]) -> int:
        """Insert or update organization and return ID"""
        conn = await self.db_manager.get_connection()
        try:
            # Try to get existing organization
            existing = await conn.fetchrow(
                "SELECT id FROM organizations WHERE cnpj = $1",
                org_data['cnpj']
            )

            if existing:
                # Update existing
                await conn.execute("""
                    UPDATE organizations
                    SET name = $2, government_level = $3, organization_type = $4,
                        state_code = $5, municipality_name = $6, updated_at = CURRENT_TIMESTAMP
                    WHERE cnpj = $1
                """, org_data['cnpj'], org_data['name'], org_data['government_level'],
                    org_data.get('organization_type'), org_data.get('state_code'),
                    org_data.get('municipality_name'))
                return existing['id']
            else:
                # Insert new
                org_id = await conn.fetchval("""
                    INSERT INTO organizations (cnpj, name, government_level, organization_type, state_code, municipality_name)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, org_data['cnpj'], org_data['name'], org_data['government_level'],
                    org_data.get('organization_type'), org_data.get('state_code'),
                    org_data.get('municipality_name'))
                return org_id
        finally:
            await conn.close()

    async def insert_tender(self, tender_data: Dict[str, Any]) -> int:
        """Insert tender and return ID"""
        conn = await self.db_manager.get_connection()
        try:
            tender_id = await conn.fetchval("""
                INSERT INTO tenders (
                    organization_id, cnpj, ano, sequencial, control_number, title, description,
                    government_level, tender_size, contracting_modality, modality_name,
                    total_estimated_value, total_homologated_value, publication_date,
                    state_code, municipality_code, status, process_category
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (cnpj, ano, sequencial) DO UPDATE SET
                    total_homologated_value = EXCLUDED.total_homologated_value,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, tender_data['organization_id'], tender_data['cnpj'], tender_data['ano'],
                tender_data['sequencial'], tender_data.get('control_number'),
                tender_data.get('title'), tender_data.get('description'),
                tender_data['government_level'], tender_data['tender_size'],
                tender_data.get('contracting_modality'), tender_data.get('modality_name'),
                tender_data.get('total_estimated_value'), tender_data.get('total_homologated_value'),
                tender_data.get('publication_date'), tender_data.get('state_code'),
                tender_data.get('municipality_code'), tender_data.get('status'),
                tender_data.get('process_category'))
            return tender_id
        finally:
            await conn.close()

    async def insert_tender_items_batch(self, items_data: List[Dict[str, Any]]):
        """Insert multiple tender items efficiently"""
        if not items_data:
            return

        conn = await self.db_manager.get_connection()
        try:
            await conn.executemany("""
                INSERT INTO tender_items (
                    tender_id, item_number, description, unit, quantity,
                    estimated_unit_value, estimated_total_value,
                    homologated_unit_value, homologated_total_value,
                    winner_name, winner_cnpj
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (tender_id, item_number) DO UPDATE SET
                    homologated_unit_value = EXCLUDED.homologated_unit_value,
                    homologated_total_value = EXCLUDED.homologated_total_value,
                    winner_name = EXCLUDED.winner_name,
                    winner_cnpj = EXCLUDED.winner_cnpj,
                    updated_at = CURRENT_TIMESTAMP
            """, [
                (item['tender_id'], item['item_number'], item['description'],
                 item.get('unit'), item.get('quantity'),
                 item.get('estimated_unit_value'), item.get('estimated_total_value'),
                 item.get('homologated_unit_value'), item.get('homologated_total_value'),
                 item.get('winner_name'), item.get('winner_cnpj'))
                for item in items_data
            ])
        finally:
            await conn.close()

    async def filter_new_tenders(self, tenders: List[Dict]) -> List[Dict]:
        """Filter out tenders already in database (by control_number)"""
        if not tenders:
            return []

        conn = await self.db_manager.get_connection()
        try:
            # Extract all control numbers from tenders
            control_numbers = [
                t.get('numeroControlePNCP') or t.get('numeroControlePNCPCompra') or t.get('control_number')
                for t in tenders
            ]
            # Filter out None values
            control_numbers = [cn for cn in control_numbers if cn]

            if not control_numbers:
                return tenders

            # Query database for existing control numbers
            query = """
                SELECT control_number
                FROM tenders
                WHERE control_number = ANY($1::varchar[])
            """
            existing_rows = await conn.fetch(query, control_numbers)
            existing_control_numbers = {row['control_number'] for row in existing_rows}

            # Filter out tenders that already exist
            new_tenders = []
            for tender in tenders:
                control_num = (
                    tender.get('numeroControlePNCP') or
                    tender.get('numeroControlePNCPCompra') or
                    tender.get('control_number')
                )
                if control_num not in existing_control_numbers:
                    new_tenders.append(tender)

            return new_tenders

        finally:
            await conn.close()

    async def get_unprocessed_tenders(self, state_code: str = None, limit: int = 100) -> List[Dict]:
        """Get tenders that haven't been processed for item extraction"""
        conn = await self.db_manager.get_connection()
        try:
            query = """
                SELECT t.id, t.cnpj, t.ano, t.sequencial, t.government_level,
                       t.total_homologated_value, t.state_code
                FROM tenders t
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                WHERE t.total_homologated_value > 0
                  AND ti.tender_id IS NULL
            """
            params = []

            if state_code:
                query += " AND t.state_code = $1"
                params.append(state_code)

            query += " ORDER BY t.total_homologated_value DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def log_processing_start(self, process_type: str, state_code: str = None,
                                  metadata: Dict = None) -> int:
        """Log start of processing operation"""
        conn = await self.db_manager.get_connection()
        try:
            # Convert metadata dict to JSON string for JSONB column
            metadata_json = json.dumps(metadata) if metadata else None

            log_id = await conn.fetchval("""
                INSERT INTO processing_log (process_type, state_code, start_time, status, metadata)
                VALUES ($1, $2, CURRENT_TIMESTAMP, 'running', $3::jsonb)
                RETURNING id
            """, process_type, state_code, metadata_json)
            return log_id
        finally:
            await conn.close()

    async def log_processing_end(self, log_id: int, status: str, records_processed: int = 0,
                               records_matched: int = 0, error_message: str = None):
        """Log end of processing operation"""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                UPDATE processing_log
                SET end_time = CURRENT_TIMESTAMP, status = $2, records_processed = $3,
                    records_matched = $4, error_message = $5
                WHERE id = $1
            """, log_id, status, records_processed, records_matched, error_message)
        finally:
            await conn.close()

# Utility function to create database manager from environment variables
def create_db_manager_from_env() -> CloudSQLManager:
    """Create database manager from environment variables"""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION', 'us-central1')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')
    database_name = os.getenv('DATABASE_NAME', DatabaseConfig.DATABASE_NAME)

    if not all([project_id, instance_name]):
        raise ValueError("Missing required environment variables: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_INSTANCE")

    return CloudSQLManager(project_id, region, instance_name, database_name)