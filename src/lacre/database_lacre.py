"""
GCP Cloud SQL (PostgreSQL) database module for PNCP lacre data processing
Wrapper around base database module to point to lacre-specific database
"""

import os
import logging
from typing import Dict, List, Optional, Any
from database import CloudSQLManager, DatabaseOperations, DATABASE_SCHEMA
from .config_lacre import LacreDatabaseConfig

logger = logging.getLogger(__name__)

def create_lacre_db_manager_from_env() -> CloudSQLManager:
    """Create database manager for lacre database from environment variables"""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    region = os.getenv('CLOUD_SQL_REGION', 'us-central1')
    instance_name = os.getenv('CLOUD_SQL_INSTANCE')

    # Use lacre-specific database name
    database_name = os.getenv('LACRE_DATABASE_NAME', LacreDatabaseConfig.DATABASE_NAME)

    if not all([project_id, instance_name]):
        raise ValueError("Missing required environment variables: GOOGLE_CLOUD_PROJECT, CLOUD_SQL_INSTANCE")

    logger.info(f"Creating lacre database manager for: {project_id}:{region}:{instance_name}/{database_name}")

    return CloudSQLManager(project_id, region, instance_name, database_name)

class LacreDatabaseOperations(DatabaseOperations):
    """
    Database operations for PNCP lacre data
    Extends base DatabaseOperations with lacre-specific functionality
    """

    def __init__(self, db_manager: CloudSQLManager):
        super().__init__(db_manager)
        logger.info(f"Initialized LacreDatabaseOperations for database: {db_manager.database_name}")

    async def get_lacre_statistics(self) -> Dict[str, Any]:
        """Get statistics about lacre tenders in database"""
        conn = await self.db_manager.get_connection()
        try:
            stats = {}

            # Total tenders
            total_tenders = await conn.fetchval("SELECT COUNT(*) FROM tenders")
            stats['total_tenders'] = total_tenders

            # Total items
            total_items = await conn.fetchval("SELECT COUNT(*) FROM tender_items")
            stats['total_items'] = total_items

            # Total matched products
            total_matches = await conn.fetchval("SELECT COUNT(*) FROM matched_products")
            stats['total_matches'] = total_matches

            # Total value
            total_value = await conn.fetchval(
                "SELECT COALESCE(SUM(total_estimated_value), 0) FROM tenders"
            )
            stats['total_value_brl'] = float(total_value) if total_value else 0.0

            # By state
            state_distribution = await conn.fetch("""
                SELECT state_code, COUNT(*) as count,
                       SUM(total_estimated_value) as total_value
                FROM tenders
                WHERE state_code IS NOT NULL
                GROUP BY state_code
                ORDER BY count DESC
            """)
            stats['by_state'] = [
                {
                    'state_code': row['state_code'],
                    'count': row['count'],
                    'total_value': float(row['total_value']) if row['total_value'] else 0.0
                }
                for row in state_distribution
            ]

            # By government level
            gov_distribution = await conn.fetch("""
                SELECT government_level, COUNT(*) as count
                FROM tenders
                GROUP BY government_level
                ORDER BY count DESC
            """)
            stats['by_government_level'] = {
                row['government_level']: row['count']
                for row in gov_distribution
            }

            # Recent activity (last 30 days)
            recent_count = await conn.fetchval("""
                SELECT COUNT(*) FROM tenders
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            """)
            stats['recent_tenders_30days'] = recent_count

            return stats

        finally:
            await conn.close()

    async def get_ongoing_tenders_count(self) -> int:
        """Get count of ongoing tenders"""
        conn = await self.db_manager.get_connection()
        try:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM tenders
                WHERE status IN ('Em andamento', 'Aberta', 'Publicada', 'open', 'ongoing')
            """)
            return count or 0
        finally:
            await conn.close()

    async def get_tenders_by_application(self, application: str) -> List[Dict]:
        """Get tenders filtered by lacre application (e.g., 'water_meter')"""
        conn = await self.db_manager.get_connection()
        try:
            # This assumes we store application info in description or metadata
            # Could be enhanced with a dedicated column
            query = """
                SELECT t.*, o.name as organization_name
                FROM tenders t
                JOIN organizations o ON t.organization_id = o.id
                WHERE t.description ILIKE $1
                ORDER BY t.total_estimated_value DESC
                LIMIT 100
            """

            # Map application to search terms
            search_terms = {
                'water_meter': '%hidrômetro%',
                'energy_meter': '%energia%',
                'gas_meter': '%gás%',
                'envelope': '%envelope%',
                'wristband': '%pulseira%'
            }

            search_pattern = search_terms.get(application, f'%{application}%')
            rows = await conn.fetch(query, search_pattern)

            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def search_tenders_by_keyword(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search tenders by keyword in title or description"""
        conn = await self.db_manager.get_connection()
        try:
            query = """
                SELECT t.*, o.name as organization_name
                FROM tenders t
                JOIN organizations o ON t.organization_id = o.id
                WHERE t.title ILIKE $1 OR t.description ILIKE $1
                ORDER BY t.created_at DESC
                LIMIT $2
            """

            search_pattern = f'%{keyword}%'
            rows = await conn.fetch(query, search_pattern, limit)

            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def get_high_value_tenders(self, min_value: float = 100000.0, limit: int = 50) -> List[Dict]:
        """Get high-value lacre tenders"""
        conn = await self.db_manager.get_connection()
        try:
            query = """
                SELECT t.*, o.name as organization_name
                FROM tenders t
                JOIN organizations o ON t.organization_id = o.id
                WHERE t.total_estimated_value >= $1
                ORDER BY t.total_estimated_value DESC
                LIMIT $2
            """

            rows = await conn.fetch(query, min_value, limit)
            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def export_tenders_for_analysis(self, state_code: str = None) -> List[Dict]:
        """Export tender data for analysis/reporting"""
        conn = await self.db_manager.get_connection()
        try:
            query = """
                SELECT
                    t.id,
                    t.cnpj,
                    t.ano,
                    t.sequencial,
                    t.title,
                    t.description,
                    t.government_level,
                    t.tender_size,
                    t.modality_name,
                    t.total_estimated_value,
                    t.state_code,
                    t.municipality_code,
                    t.status,
                    t.publication_date,
                    o.name as organization_name,
                    COUNT(DISTINCT ti.id) as items_count,
                    COUNT(DISTINCT mp.id) as matches_count
                FROM tenders t
                JOIN organizations o ON t.organization_id = o.id
                LEFT JOIN tender_items ti ON t.id = ti.tender_id
                LEFT JOIN matched_products mp ON ti.id = mp.tender_item_id
            """

            if state_code:
                query += " WHERE t.state_code = $1"
                query += " GROUP BY t.id, o.name ORDER BY t.total_estimated_value DESC"
                rows = await conn.fetch(query, state_code)
            else:
                query += " GROUP BY t.id, o.name ORDER BY t.total_estimated_value DESC"
                rows = await conn.fetch(query)

            return [dict(row) for row in rows]

        finally:
            await conn.close()

# Utility function for easy access
def get_lacre_db_operations() -> LacreDatabaseOperations:
    """Get lacre database operations instance with automatic setup"""
    db_manager = create_lacre_db_manager_from_env()
    return LacreDatabaseOperations(db_manager)

# Test function
async def test_lacre_database_connection():
    """Test lacre database connection"""
    try:
        db_manager = create_lacre_db_manager_from_env()
        conn = await db_manager.get_connection()

        # Test simple query
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        if result == 1:
            logger.info("✓ Lacre database connection successful!")
            return True
        else:
            logger.error("✗ Lacre database connection failed")
            return False

    except Exception as e:
        logger.error(f"✗ Lacre database connection error: {e}")
        return False

if __name__ == "__main__":
    import asyncio

    async def main():
        print("Testing lacre database connection...")
        success = await test_lacre_database_connection()
        if success:
            print("✓ Connection test passed!")

            # Test database operations
            db_ops = get_lacre_db_operations()
            print("\nTesting database operations...")

            try:
                stats = await db_ops.get_lacre_statistics()
                print(f"Database statistics: {stats}")
            except Exception as e:
                print(f"Note: Statistics query failed (expected if tables don't exist yet): {e}")

        else:
            print("✗ Connection test failed!")

    asyncio.run(main())
