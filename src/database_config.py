"""
Shared database configuration for PNCP data processing
Used by both medical and lacre modules
"""

class DatabaseConfig:
    """GCP Cloud SQL (PostgreSQL) database configuration"""

    # Table names
    TENDERS_TABLE = "tenders"
    TENDER_ITEMS_TABLE = "tender_items"
    ORGANIZATIONS_TABLE = "organizations"
    MATCHED_PRODUCTS_TABLE = "matched_products"
    HOMOLOGATED_RESULTS_TABLE = "homologated_results"
    PROCESSING_LOG_TABLE = "processing_log"

    # Batch sizes for processing
    TENDER_BATCH_SIZE = 100
    ITEM_BATCH_SIZE = 50

    # Cloud SQL connection settings
    MAX_CONNECTIONS = 20
    CONNECTION_TIMEOUT = 30

    # GCP Cloud SQL specific settings
    CLOUD_SQL_CONNECTION_NAME = None  # Format: project:region:instance
    DATABASE_NAME = "pncp_medical_data"  # Default database name (can be overridden)

    # Connection options
    USE_IAM_AUTH = True  # Use IAM database authentication
    USE_PRIVATE_IP = True  # Connect via private IP

    # SSL settings
    SSL_MODE = "require"
    SSL_CERT_PATH = None  # Path to client cert if needed
    SSL_KEY_PATH = None   # Path to client key if needed
    SSL_ROOT_CERT_PATH = None  # Path to server CA cert if needed


__all__ = ['DatabaseConfig']
