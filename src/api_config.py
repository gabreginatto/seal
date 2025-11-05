"""
Shared API configuration for PNCP API Client
Used by both medical and lacre modules
"""

class APIConfig:
    """PNCP API configuration"""

    # Base URLs
    BASE_URL = "https://pncp.gov.br/api"
    CONSULTATION_BASE_URL = "https://pncp.gov.br/api/consulta"

    # Endpoints
    LOGIN_ENDPOINT = "/v1/usuarios/login"
    TENDERS_ENDPOINT = "/v1/contratacoes/publicacao"
    TENDER_ITEMS_ENDPOINT = "/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"
    ITEM_RESULTS_ENDPOINT = "/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados"

    # Request settings
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    # Response pagination
    MIN_PAGE_SIZE = 10  # API minimum requirement
    DEFAULT_PAGE_SIZE = 10  # Use conservative page size
    MAX_PAGE_SIZE = 50  # PNCP API maximum supported


class RateLimitConfig:
    """API rate limiting configuration"""

    # API rate limiting
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000


__all__ = ['APIConfig', 'RateLimitConfig']
