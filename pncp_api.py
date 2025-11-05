"""
PNCP API Client with Authentication and Rate Limiting
Handles all interactions with the PNCP API including login, token management, and data retrieval
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time
import os
from config import APIConfig, ProcessingConfig

logger = logging.getLogger(__name__)

@dataclass
class AuthToken:
    """Authentication token with expiration tracking"""
    token: str
    expires_at: datetime
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None

    def is_expired(self, buffer_minutes: int = 5) -> bool:
        """Check if token is expired (with buffer for refresh)"""
        return datetime.now() + timedelta(minutes=buffer_minutes) >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'token': self.token,
            'expires_at': self.expires_at.isoformat(),
            'refresh_token': self.refresh_token,
            'user_id': self.user_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthToken':
        """Create from dictionary"""
        return cls(
            token=data['token'],
            expires_at=datetime.fromisoformat(data['expires_at']),
            refresh_token=data.get('refresh_token'),
            user_id=data.get('user_id')
        )

class RateLimiter:
    """Simple rate limiter for API requests"""

    def __init__(self, max_requests_per_minute: int = 60, max_requests_per_hour: int = 1000):
        self.max_per_minute = max_requests_per_minute
        self.max_per_hour = max_requests_per_hour
        self.minute_requests = []
        self.hour_requests = []

    async def wait_if_needed(self):
        """Wait if rate limits would be exceeded"""
        now = time.time()

        # Clean old requests
        self.minute_requests = [req_time for req_time in self.minute_requests if now - req_time < 60]
        self.hour_requests = [req_time for req_time in self.hour_requests if now - req_time < 3600]

        # Check minute limit
        if len(self.minute_requests) >= self.max_per_minute:
            sleep_time = 60 - (now - self.minute_requests[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.wait_if_needed()

        # Check hour limit
        if len(self.hour_requests) >= self.max_per_hour:
            sleep_time = 3600 - (now - self.hour_requests[0])
            if sleep_time > 0:
                logger.warning(f"Hourly rate limit reached, sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.wait_if_needed()

        # Record this request
        self.minute_requests.append(now)
        self.hour_requests.append(now)

class PNCPAPIClient:
    """PNCP API client with authentication and rate limiting"""

    def __init__(self, username: str = None, password: str = None,
                 rate_limiter: RateLimiter = None):
        self.username = username or os.getenv('PNCP_USERNAME')
        self.password = password or os.getenv('PNCP_PASSWORD')
        self.base_url = APIConfig.BASE_URL
        self.consultation_url = APIConfig.CONSULTATION_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[AuthToken] = None
        self.rate_limiter = rate_limiter or RateLimiter(
            ProcessingConfig().max_requests_per_minute,
            ProcessingConfig().max_requests_per_hour
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=APIConfig.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': 'PNCP-Medical-Data-Client/1.0'}
            )

    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _make_request(self, method: str, url: str, **kwargs) -> Tuple[int, Dict[str, Any]]:
        """Make HTTP request with rate limiting and error handling"""
        await self.rate_limiter.wait_if_needed()

        if not self.session:
            await self.start_session()

        retries = 0
        while retries < APIConfig.MAX_RETRIES:
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 401 and self.auth_token:
                        # Token expired, try to refresh
                        logger.info("Token expired, attempting to refresh")
                        await self.authenticate()
                        # Update headers with new token
                        if 'headers' not in kwargs:
                            kwargs['headers'] = {}
                        kwargs['headers']['Authorization'] = f'Bearer {self.auth_token.token}'
                        # Retry the request
                        continue

                    if response.status == 429:  # Rate limited
                        wait_time = min(2 ** retries * APIConfig.RETRY_DELAY, 60)
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        retries += 1
                        continue

                    # Try to parse JSON response
                    try:
                        data = await response.json()
                    except:
                        data = {'error': 'Invalid JSON response', 'text': await response.text()}

                    return response.status, data

            except Exception as e:
                retries += 1
                if retries >= APIConfig.MAX_RETRIES:
                    logger.error(f"Request failed after {retries} retries: {e}")
                    return 500, {'error': str(e)}

                wait_time = 2 ** retries * APIConfig.RETRY_DELAY
                logger.warning(f"Request failed, retrying in {wait_time} seconds: {e}")
                await asyncio.sleep(wait_time)

        return 500, {'error': 'Max retries exceeded'}

    async def authenticate(self) -> bool:
        """Authenticate with PNCP API and get bearer token"""
        # PNCP public API may not require authentication for consultation endpoints
        if not self.username or not self.password:
            logger.info("No credentials provided - using public API access")
            return True  # Allow public access

        login_url = f"{self.base_url}{APIConfig.LOGIN_ENDPOINT}"
        login_data = {
            "login": self.username,
            "senha": self.password
        }

        status, response = await self._make_request(
            'POST',
            login_url,
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )

        if status == 200:
            # Successful login - extract token
            token = response.get('token') or response.get('access_token')
            if token:
                # Estimate token expiration (typically 1 hour for PNCP)
                expires_at = datetime.now() + timedelta(hours=1)
                self.auth_token = AuthToken(
                    token=token,
                    expires_at=expires_at,
                    user_id=response.get('id') or response.get('user_id')
                )
                logger.info("Successfully authenticated with PNCP API")
                return True
            else:
                logger.error("Login successful but no token in response")
                return False
        else:
            error_msg = response.get('message', 'Unknown error')
            logger.error(f"Authentication failed: {status} - {error_msg}")
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = {'Accept': 'application/json'}
        if self.auth_token and not self.auth_token.is_expired():
            headers['Authorization'] = f'Bearer {self.auth_token.token}'
        return headers

    async def get_tenders_by_publication_date(self, start_date: str, end_date: str,
                                            modality_code: int, state: str = None,
                                            municipality_code: str = None,
                                            cnpj: str = None, page: int = 1,
                                            page_size: int = 10) -> Tuple[int, Dict[str, Any]]:
        """Get tenders by publication date using consultation API"""

        url = f"{self.consultation_url}/v1/contratacoes/publicacao"

        # Validate page size (PNCP requires 10-500)
        validated_page_size = max(APIConfig.MIN_PAGE_SIZE, min(page_size, APIConfig.MAX_PAGE_SIZE))

        logger.debug(f"API call - page_size input: {page_size}, validated: {validated_page_size}")

        params = {
            'dataInicial': start_date,
            'dataFinal': end_date,
            'codigoModalidadeContratacao': modality_code,
            'pagina': page,
            'tamanhoPagina': validated_page_size
        }

        logger.debug(f"API params: {params}")

        if state:
            params['uf'] = state
        if municipality_code:
            params['codigoMunicipioIbge'] = municipality_code
        if cnpj:
            params['cnpj'] = cnpj

        return await self._make_request('GET', url, params=params)

    async def get_tender_items(self, cnpj: str, year: int, sequential: int) -> Tuple[int, Dict[str, Any]]:
        """Get all items for a specific tender (with pagination support)"""
        # Try to authenticate if credentials provided, otherwise use public access
        if self.username and self.password:
            if not self.auth_token or self.auth_token.is_expired():
                authenticated = await self.authenticate()
                if not authenticated:
                    return 401, {'error': 'Authentication failed'}

        # Use /api/pncp/v1/ endpoint which supports pagination
        url = "https://pncp.gov.br/api/pncp/v1/orgaos/{}/compras/{}/{}/itens".format(cnpj, year, sequential)
        headers = self._get_auth_headers()

        # Fetch all pages
        all_items = []
        page = 1

        while True:
            params = {'pagina': page, 'tamanhoPagina': 100}
            status, response = await self._make_request('GET', url, headers=headers, params=params)

            if status != 200:
                if page == 1:
                    return status, response
                else:
                    # Already got some items, return what we have
                    break

            # Handle both list and dict responses
            if isinstance(response, list):
                items = response
            else:
                items = response.get('data', [])

            if not items:
                break

            all_items.extend(items)

            # Check for more pages
            if isinstance(response, dict):
                has_more = response.get('paginasRestantes', 0) > 0
                if not has_more:
                    break

            page += 1

            # Safety limit: max 20 pages (2000 items)
            if page > 20:
                logger.warning(f"Reached pagination limit for {cnpj}/{year}/{sequential}")
                break

        return 200, {'data': all_items}

    async def fetch_sample_items(self, cnpj: str, year: int, sequential: int, max_items: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch only first N items from a tender (for sampling in Stage 3)
        This saves API calls by not fetching all items
        """
        try:
            status, response = await self.get_tender_items(cnpj, year, sequential)

            if status == 200:
                items = response.get('data', [])
                # Return only first max_items
                return items[:max_items]
            else:
                logger.warning(f"Failed to fetch items for {cnpj}/{year}/{sequential}: {status}")
                return []

        except Exception as e:
            logger.error(f"Error fetching sample items: {e}")
            return []

    async def get_item_results(self, cnpj: str, year: int, sequential: int,
                             item_number: int) -> Tuple[int, Dict[str, Any]]:
        """Get results (bids) for a specific item"""
        # Try to authenticate if credentials provided, otherwise use public access
        if self.username and self.password:
            if not self.auth_token or self.auth_token.is_expired():
                authenticated = await self.authenticate()
                if not authenticated:
                    return 401, {'error': 'Authentication failed'}

        url = f"{self.base_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados"
        headers = self._get_auth_headers()

        return await self._make_request('GET', url, headers=headers)

    async def get_specific_item_result(self, cnpj: str, year: int, sequential: int,
                                     item_number: int, result_sequential: int) -> Tuple[int, Dict[str, Any]]:
        """Get specific result details for an item"""
        # Try to authenticate if credentials provided, otherwise use public access
        if self.username and self.password:
            if not self.auth_token or self.auth_token.is_expired():
                authenticated = await self.authenticate()
                if not authenticated:
                    return 401, {'error': 'Authentication failed'}

        url = f"{self.base_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados/{result_sequential}"
        headers = self._get_auth_headers()

        return await self._make_request('GET', url, headers=headers)

    async def get_ongoing_tenders_by_status(self, start_date: str, end_date: str,
                                          modality_code: int, state: str = None,
                                          page: int = 1, page_size: int = 10) -> Tuple[int, Dict[str, Any]]:
        """
        Get ongoing tenders (not completed) by checking status and dates
        Focuses on tenders that are currently open for bidding
        """
        url = f"{self.consultation_url}/v1/contratacoes/publicacao"

        # Validate page size (PNCP requires 10-500)
        validated_page_size = max(APIConfig.MIN_PAGE_SIZE, min(page_size, APIConfig.MAX_PAGE_SIZE))

        logger.debug(f"API call (ongoing) - page_size input: {page_size}, validated: {validated_page_size}")

        params = {
            'dataInicial': start_date,
            'dataFinal': end_date,
            'codigoModalidadeContratacao': modality_code,
            'pagina': page,
            'tamanhoPagina': validated_page_size
        }

        logger.debug(f"API params (ongoing): {params}")

        if state:
            params['uf'] = state

        # Note: PNCP API may not have a direct status filter, so we'll need to filter results
        # after retrieving them to check for ongoing status
        return await self._make_request('GET', url, params=params)

    def filter_ongoing_tenders(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter tenders to keep only ongoing ones (not completed/homologated)
        """
        ongoing_status_keywords = [
            'aberta', 'open', 'em andamento', 'in progress',
            'publicada', 'published', 'vigente', 'active',
            'aguardando propostas', 'recebendo propostas'
        ]

        completed_status_keywords = [
            'homologada', 'homologado', 'homologated',
            'concluída', 'concluido', 'concluded', 'completed',
            'adjudicada', 'adjudicado', 'finalizada', 'finalizado',
            'cancelada', 'cancelado', 'deserta', 'fracassada'
        ]

        filtered_tenders = []

        for tender in tenders:
            # Check status field
            status = (
                tender.get('situacaoCompra', '') or
                tender.get('situacao', '') or
                tender.get('statusCompra', '') or
                tender.get('status', '')
            ).lower()

            # Check if completed (exclude these)
            is_completed = any(keyword in status for keyword in completed_status_keywords)
            if is_completed:
                continue

            # Check if ongoing (or unknown status with recent date)
            is_ongoing = any(keyword in status for keyword in ongoing_status_keywords)

            # If no clear status, check dates
            if not is_ongoing and not status:
                # If has publication date but no homologation date, likely ongoing
                has_pub_date = tender.get('dataPublicacao') or tender.get('dataPublicacaoPncp')
                has_homolog_date = tender.get('dataHomologacao') or tender.get('dataResultado')

                if has_pub_date and not has_homolog_date:
                    is_ongoing = True

            if is_ongoing:
                filtered_tenders.append(tender)

        return filtered_tenders

    async def discover_tenders_for_state(self, state_code: str, start_date: str, end_date: str,
                                       modalities: List[int] = None, only_ongoing: bool = False) -> List[Dict[str, Any]]:
        """
        Discover all tenders for a specific state within date range

        Args:
            state_code: State code (e.g., 'SP', 'RJ')
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            modalities: List of modality codes (default: [4, 6, 8])
            only_ongoing: If True, filter for ongoing tenders only
        """
        if modalities is None:
            modalities = [4, 6, 8]  # Electronic tenders, Pregão, Dispensa

        all_tenders = []

        for modality in modalities:
            page = 1
            has_more = True

            while has_more:
                try:
                    if only_ongoing:
                        status, response = await self.get_ongoing_tenders_by_status(
                            start_date, end_date, modality, state_code, page=page, page_size=50
                        )
                    else:
                        status, response = await self.get_tenders_by_publication_date(
                            start_date, end_date, modality, state_code, page=page, page_size=50
                        )

                    if status == 200:
                        data = response.get('data', [])
                        if data:
                            # Filter for ongoing if requested
                            if only_ongoing:
                                data = self.filter_ongoing_tenders(data)

                            all_tenders.extend(data)

                            # Check if there are more pages
                            pages_remaining = response.get('paginasRestantes', 0)
                            has_more = pages_remaining > 0
                            page += 1

                            logger.info(f"Retrieved page {page-1} for {state_code}, modality {modality}: {len(data)} tenders")
                        else:
                            has_more = False
                    else:
                        logger.error(f"Failed to get tenders for {state_code}, modality {modality}: {status} - {response}")
                        has_more = False

                    # Small delay between pages to be respectful
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error getting tenders for {state_code}: {e}")
                    has_more = False

        logger.info(f"Discovered {len(all_tenders)} tenders for {state_code} (ongoing_only={only_ongoing})")
        return all_tenders

    async def get_complete_tender_data(self, cnpj: str, year: int, sequential: int) -> Dict[str, Any]:
        """Get complete tender data including items and results"""
        tender_data = {
            'cnpj': cnpj,
            'year': year,
            'sequential': sequential,
            'items': [],
            'error': None
        }

        try:
            # Get tender items
            status, items_response = await self.get_tender_items(cnpj, year, sequential)

            if status == 200:
                items = items_response.get('data', [])

                for item in items:
                    item_number = item.get('numeroItem')
                    if item_number:
                        # Get item results
                        results_status, results_response = await self.get_item_results(
                            cnpj, year, sequential, item_number
                        )

                        if results_status == 200:
                            item['results'] = results_response.get('data', [])
                        else:
                            item['results'] = []
                            item['results_error'] = f"Status {results_status}: {results_response}"

                    tender_data['items'].append(item)

                    # Small delay between item requests
                    await asyncio.sleep(0.05)

            else:
                tender_data['error'] = f"Failed to get items: {status} - {items_response}"

        except Exception as e:
            tender_data['error'] = f"Exception getting tender data: {str(e)}"
            logger.error(f"Error getting complete tender data for {cnpj}/{year}/{sequential}: {e}")

        return tender_data

    def save_token(self, filepath: str):
        """Save authentication token to file"""
        if self.auth_token:
            with open(filepath, 'w') as f:
                json.dump(self.auth_token.to_dict(), f)

    def load_token(self, filepath: str) -> bool:
        """Load authentication token from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    token_data = json.load(f)
                    self.auth_token = AuthToken.from_dict(token_data)

                    if not self.auth_token.is_expired():
                        logger.info("Loaded valid authentication token")
                        return True
                    else:
                        logger.info("Loaded token is expired")
                        self.auth_token = None
        except Exception as e:
            logger.error(f"Error loading token: {e}")

        return False


# Utility functions
async def test_api_connection(username: str = None, password: str = None) -> bool:
    """Test API connection and authentication"""
    async with PNCPAPIClient(username, password) as client:
        success = await client.authenticate()
        if success:
            # Test a simple consultation API call
            status, response = await client.get_tenders_by_publication_date(
                start_date='20240101',
                end_date='20240102',
                modality_code=8,  # Dispensa
                state='DF',
                page=1
            )

            if status == 200:
                logger.info(f"API test successful, found {response.get('totalRegistros', 0)} tenders")
                return True
            else:
                logger.error(f"API test failed: {status} - {response}")
                return False
        else:
            logger.error("Authentication failed")
            return False

async def discover_tenders_for_multiple_states(states: List[str], start_date: str, end_date: str,
                                             username: str = None, password: str = None) -> Dict[str, List[Dict]]:
    """Discover tenders for multiple states concurrently"""

    async with PNCPAPIClient(username, password) as client:
        await client.authenticate()

        tasks = []
        for state in states:
            task = client.discover_tenders_for_state(state, start_date, end_date)
            tasks.append((state, task))

        results = {}
        for state, task in tasks:
            try:
                tenders = await task
                results[state] = tenders
                logger.info(f"Completed tender discovery for {state}: {len(tenders)} tenders")
            except Exception as e:
                logger.error(f"Failed to discover tenders for {state}: {e}")
                results[state] = []

        return results

if __name__ == "__main__":
    # Test the API client
    async def main():
        success = await test_api_connection()
        if success:
            print("API connection test passed!")
        else:
            print("API connection test failed!")

    asyncio.run(main())