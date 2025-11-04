"""
Item Processing Module for PNCP Medical Data
Retrieves tender items, extracts homologated prices, and matches with Fernandes products
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import pandas as pd

from config import ProcessingConfig
from pncp_api import PNCPAPIClient
from product_matcher import ProductMatcher
from database import DatabaseOperations

logger = logging.getLogger(__name__)

@dataclass
class ItemProcessingResult:
    """Result of processing items for a tender"""
    tender_id: int
    cnpj: str
    year: int
    sequential: int
    total_items_found: int
    items_with_results: int
    matched_products: int
    total_homologated_value: float
    processing_time_seconds: float
    errors: List[str]

@dataclass
class MatchedProduct:
    """Matched Fernandes product with pricing information"""
    tender_item_id: int
    fernandes_code: str
    fernandes_description: str
    match_score: float
    fob_price_usd: float
    moq: int
    homologated_price_brl: float
    homologated_price_usd: float  # Converted
    exchange_rate: float
    price_difference_percent: float
    is_competitive: bool

class ItemProcessor:
    """Processes tender items and matches with Fernandes products"""

    def __init__(self, api_client: PNCPAPIClient, product_matcher: ProductMatcher,
                 db_operations: DatabaseOperations, fernandes_products: List[Dict],
                 usd_to_brl_rate: float = 5.0):
        self.api_client = api_client
        self.product_matcher = product_matcher
        self.db_ops = db_operations
        self.fernandes_products = fernandes_products
        self.usd_to_brl_rate = usd_to_brl_rate

    async def process_tender_items(self, tender_id: int, cnpj: str, year: int,
                                 sequential: int) -> ItemProcessingResult:
        """Process all items for a specific tender"""

        start_time = datetime.now()
        result = ItemProcessingResult(
            tender_id=tender_id,
            cnpj=cnpj,
            year=year,
            sequential=sequential,
            total_items_found=0,
            items_with_results=0,
            matched_products=0,
            total_homologated_value=0,
            processing_time_seconds=0,
            errors=[]
        )

        try:
            # Get tender items from API
            status, items_response = await self.api_client.get_tender_items(cnpj, year, sequential)

            if status != 200:
                error_msg = f"Failed to get items: {status} - {items_response}"
                result.errors.append(error_msg)
                logger.error(f"Error getting items for {cnpj}/{year}/{sequential}: {error_msg}")
                return result

            items = items_response.get('data', [])
            result.total_items_found = len(items)

            if not items:
                logger.info(f"No items found for tender {cnpj}/{year}/{sequential}")
                return result

            # Process each item
            processed_items = []
            matched_products = []

            for item in items:
                try:
                    processed_item, item_matches = await self._process_single_item(
                        tender_id, item, cnpj, year, sequential
                    )

                    if processed_item:
                        processed_items.append(processed_item)
                        result.total_homologated_value += processed_item.get('homologated_total_value', 0) or 0

                        if processed_item.get('homologated_unit_value'):
                            result.items_with_results += 1

                    if item_matches:
                        matched_products.extend(item_matches)
                        result.matched_products += len(item_matches)

                    # Small delay between items to be respectful
                    await asyncio.sleep(0.1)

                except Exception as e:
                    error_msg = f"Error processing item {item.get('numeroItem', 'unknown')}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

            # Store processed items in database
            if processed_items:
                await self.db_ops.insert_tender_items_batch(processed_items)

            # Store matched products
            if matched_products:
                await self._store_matched_products(matched_products)

            result.processing_time_seconds = (datetime.now() - start_time).total_seconds()

            logger.info(f"Processed {result.total_items_found} items for {cnpj}/{year}/{sequential}: "
                       f"{result.matched_products} matches, R${result.total_homologated_value:,.2f} total value")

        except Exception as e:
            error_msg = f"Error processing tender {cnpj}/{year}/{sequential}: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        return result

    async def _process_single_item(self, tender_id: int, item: Dict, cnpj: str,
                                 year: int, sequential: int) -> Tuple[Optional[Dict], List[MatchedProduct]]:
        """Process a single tender item"""

        item_number = item.get('numeroItem')
        if not item_number:
            return None, []

        # Extract item data
        processed_item = {
            'tender_id': tender_id,
            'item_number': item_number,
            'description': item.get('descricao', ''),
            'unit': item.get('unidadeMedida'),
            'quantity': self._safe_float(item.get('quantidade')),
            'estimated_unit_value': self._safe_float(item.get('valorUnitarioEstimado')),
            'estimated_total_value': self._safe_float(item.get('valorTotalEstimado')),
            'homologated_unit_value': None,
            'homologated_total_value': None,
            'winner_name': None,
            'winner_cnpj': None
        }

        matched_products = []

        try:
            # Get item results (winning bids)
            results_status, results_response = await self.api_client.get_item_results(
                cnpj, year, sequential, item_number
            )

            if results_status == 200:
                results = results_response.get('data', [])

                # Find winning result (highest ranking or marked as winner)
                winning_result = self._find_winning_result(results)

                if winning_result:
                    processed_item.update({
                        'homologated_unit_value': self._safe_float(winning_result.get('valorUnitario')),
                        'homologated_total_value': self._safe_float(winning_result.get('valorTotal')),
                        'winner_name': winning_result.get('nomeProponente'),
                        'winner_cnpj': winning_result.get('cnpjProponente')
                    })

                    # Try to match with Fernandes products
                    if processed_item['description']:
                        matches = await self._match_item_with_products(processed_item)
                        matched_products.extend(matches)

        except Exception as e:
            logger.warning(f"Error getting results for item {item_number}: {e}")

        return processed_item, matched_products

    def _find_winning_result(self, results: List[Dict]) -> Optional[Dict]:
        """Find the winning result from a list of bid results"""

        if not results:
            return None

        # Look for explicitly marked winner
        for result in results:
            if result.get('situacao') == 'Vencedor' or result.get('classificacao') == 1:
                return result

        # If no explicit winner, take the one with lowest price
        valid_results = [r for r in results if self._safe_float(r.get('valorUnitario')) is not None]
        if valid_results:
            return min(valid_results, key=lambda x: self._safe_float(x.get('valorUnitario', float('inf'))))

        return None

    async def _match_item_with_products(self, item: Dict) -> List[MatchedProduct]:
        """Match item with Fernandes products and calculate pricing"""

        if not item['description'] or not item.get('homologated_unit_value'):
            return []

        # Use product matcher to find matches
        match_result = self.product_matcher.find_best_match(
            item['description'], self.fernandes_products
        )

        if not match_result:
            return []

        product, match_score = match_result

        # Calculate pricing comparison
        homologated_price_brl = item['homologated_unit_value']
        homologated_price_usd = homologated_price_brl / self.usd_to_brl_rate
        fob_price_usd = float(product.get('FOB NINGBO USD/unit', 0))

        if fob_price_usd <= 0:
            return []  # Can't compare without FOB price

        price_difference_percent = ((homologated_price_usd - fob_price_usd) / fob_price_usd) * 100
        is_competitive = price_difference_percent <= 200  # Less than 200% markup is competitive

        matched_product = MatchedProduct(
            tender_item_id=0,  # Will be set when storing
            fernandes_code=product.get('CÓDIGO', ''),
            fernandes_description=product.get('DESCRIÇÃO', ''),
            match_score=match_score,
            fob_price_usd=fob_price_usd,
            moq=int(product.get('MOQ/unit', 0)),
            homologated_price_brl=homologated_price_brl,
            homologated_price_usd=homologated_price_usd,
            exchange_rate=self.usd_to_brl_rate,
            price_difference_percent=price_difference_percent,
            is_competitive=is_competitive
        )

        return [matched_product]

    async def _store_matched_products(self, matched_products: List[MatchedProduct]):
        """Store matched products in database"""

        # This would need to be implemented in DatabaseOperations
        # For now, log the matches
        for match in matched_products:
            logger.info(f"Matched product: {match.fernandes_code} with score {match.match_score:.1f}%, "
                       f"price difference: {match.price_difference_percent:+.1f}%")

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def process_multiple_tenders(self, tender_list: List[Dict],
                                     max_concurrent: int = 5) -> List[ItemProcessingResult]:
        """Process multiple tenders concurrently with rate limiting"""

        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_with_semaphore(tender):
            async with semaphore:
                return await self.process_tender_items(
                    tender['id'], tender['cnpj'], tender['ano'], tender['sequencial']
                )

        tasks = [process_with_semaphore(tender) for tender in tender_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing tender {tender_list[i].get('cnpj', 'unknown')}: {result}")
            else:
                processed_results.append(result)

        return processed_results

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed items and matches"""

        # This would query the database for statistics
        # For now, return placeholder
        return {
            'total_tenders_processed': 0,
            'total_items_processed': 0,
            'total_matches_found': 0,
            'average_match_score': 0,
            'competitive_matches': 0
        }


class ProductCatalogManager:
    """Manages Fernandes product catalog"""

    def __init__(self, catalog_file_path: str = None):
        self.catalog_file_path = catalog_file_path
        self.products = []

    def load_catalog_from_pdf_data(self, pdf_data: List[Dict]):
        """Load catalog from extracted PDF data"""
        self.products = pdf_data
        logger.info(f"Loaded {len(self.products)} products from catalog")

    def load_catalog_from_csv(self, csv_path: str):
        """Load catalog from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            self.products = df.to_dict('records')
            logger.info(f"Loaded {len(self.products)} products from {csv_path}")
        except Exception as e:
            logger.error(f"Error loading catalog from {csv_path}: {e}")
            self.products = []

    def get_products(self) -> List[Dict]:
        """Get all products"""
        return self.products

    def get_products_by_category(self, category: str) -> List[Dict]:
        """Get products filtered by category/type"""
        return [p for p in self.products if category.lower() in p.get('DESCRIÇÃO', '').lower()]

    def export_to_csv(self, output_path: str):
        """Export catalog to CSV"""
        if self.products:
            df = pd.DataFrame(self.products)
            df.to_csv(output_path, index=False)
            logger.info(f"Exported {len(self.products)} products to {output_path}")


# Utility functions
def create_sample_fernandes_catalog() -> List[Dict]:
    """Create sample Fernandes catalog for testing"""
    return [
        {
            'CÓDIGO': 'IVFS.5057',
            'DESCRIÇÃO': 'CURATIVO IV TRANSP. FENESTRADO COM BORDA E DUAS FITAS DE ESTABILIZAÇÃO - 5X5-7CM',
            'FOB NINGBO USD/unit': 0.0741,
            'MOQ/unit': 40000
        },
        {
            'CÓDIGO': 'IVFS.67',
            'DESCRIÇÃO': 'CURATIVO IV TRANSP. FENESTRADO COM BORDA E UMA FITA DE IDENTIFICAÇÃO - 6X7CM',
            'FOB NINGBO USD/unit': 0.0541,
            'MOQ/unit': 50000
        },
        {
            'CÓDIGO': 'PRFS67',
            'DESCRIÇÃO': 'CURATIVO TRANSP. 6X7 FRAME STYLE BORDA PROTECT',
            'FOB NINGBO USD/unit': 0.0454,
            'MOQ/unit': 100000
        },
        {
            'CÓDIGO': 'PRFS1012',
            'DESCRIÇÃO': 'CURATIVO TRANSP. 10X12 FRAME STYLE BORDA PROTECT',
            'FOB NINGBO USD/unit': 0.0963,
            'MOQ/unit': 50000
        }
    ]

async def process_unprocessed_tenders(db_operations: DatabaseOperations,
                                    api_client: PNCPAPIClient,
                                    fernandes_products: List[Dict],
                                    state_code: str = None,
                                    limit: int = 50) -> List[ItemProcessingResult]:
    """Process tenders that haven't had their items extracted yet"""

    # Get unprocessed tenders
    unprocessed = await db_operations.get_unprocessed_tenders(state_code, limit)

    if not unprocessed:
        logger.info("No unprocessed tenders found")
        return []

    # Create processor
    product_matcher = ProductMatcher()
    processor = ItemProcessor(api_client, product_matcher, db_operations, fernandes_products)

    # Process tenders
    results = await processor.process_multiple_tenders(unprocessed)

    logger.info(f"Processed {len(results)} tenders")
    return results

def summarize_processing_results(results: List[ItemProcessingResult]) -> Dict[str, Any]:
    """Summarize item processing results"""

    if not results:
        return {}

    total_tenders = len(results)
    total_items = sum(r.total_items_found for r in results)
    total_items_with_results = sum(r.items_with_results for r in results)
    total_matches = sum(r.matched_products for r in results)
    total_value = sum(r.total_homologated_value for r in results)
    total_time = sum(r.processing_time_seconds for r in results)
    total_errors = sum(len(r.errors) for r in results)

    return {
        'total_tenders_processed': total_tenders,
        'total_items_found': total_items,
        'total_items_with_homologated_prices': total_items_with_results,
        'total_product_matches': total_matches,
        'total_homologated_value_brl': total_value,
        'total_processing_time_seconds': total_time,
        'average_items_per_tender': total_items / total_tenders if total_tenders > 0 else 0,
        'match_rate_percent': (total_matches / total_items * 100) if total_items > 0 else 0,
        'total_errors': total_errors,
        'success_rate_percent': ((total_tenders - len([r for r in results if r.errors])) / total_tenders * 100) if total_tenders > 0 else 0
    }

# Testing function
async def test_item_processor():
    """Test item processor with sample data"""

    print("Item Processor test - would need actual API credentials and database")

    # Create sample catalog
    sample_catalog = create_sample_fernandes_catalog()
    print(f"Sample catalog: {len(sample_catalog)} products")

    # Test product matcher
    matcher = ProductMatcher()
    test_descriptions = [
        "CURATIVO TRANSPARENTE FENESTRADO 5X7CM COM BORDA ADESIVA",
        "BANDAGEM IV 6X7CM TRANSPARENTE FRAME STYLE"
    ]

    print("\n--- Product Matching Test ---")
    for desc in test_descriptions:
        result = matcher.find_best_match(desc, sample_catalog)
        if result:
            product, score = result
            print(f"'{desc}' -> {product['CÓDIGO']} (score: {score:.1f}%)")
        else:
            print(f"'{desc}' -> No match found")

if __name__ == "__main__":
    asyncio.run(test_item_processor())