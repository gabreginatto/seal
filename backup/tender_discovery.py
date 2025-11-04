"""
Tender Discovery Module for PNCP Medical Data Processing
Discovers and filters tenders across Brazilian states with medical relevance classification
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import json

from config import (
    BRAZILIAN_STATES, ProcessingConfig, GovernmentLevel,
    TenderSize, get_state_codes, classify_tender_size
)
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier, ClassificationResult
from database import DatabaseOperations, CloudSQLManager

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryStats:
    """Statistics for tender discovery process"""
    total_found: int = 0
    medical_relevant: int = 0
    by_state: Dict[str, int] = None
    by_government_level: Dict[str, int] = None
    by_size: Dict[str, int] = None
    by_modality: Dict[str, int] = None
    processing_time_seconds: float = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.by_state is None:
            self.by_state = {}
        if self.by_government_level is None:
            self.by_government_level = {}
        if self.by_size is None:
            self.by_size = {}
        if self.by_modality is None:
            self.by_modality = {}
        if self.errors is None:
            self.errors = []

class TenderDiscoveryEngine:
    """Discovers and classifies tenders for medical supplies across Brazilian states"""

    def __init__(self, api_client: PNCPAPIClient, classifier: TenderClassifier,
                 db_operations: DatabaseOperations, config: ProcessingConfig = None):
        self.api_client = api_client
        self.classifier = classifier
        self.db_ops = db_operations
        self.config = config or ProcessingConfig()

    async def discover_tenders_for_date_range(self, start_date: str, end_date: str,
                                            states: List[str] = None) -> DiscoveryStats:
        """Discover tenders across states for a specific date range"""

        start_time = datetime.now()
        stats = DiscoveryStats()

        if states is None:
            states = self.config.enabled_states

        logger.info(f"Starting tender discovery for {len(states)} states from {start_date} to {end_date}")

        # Start processing log
        log_id = await self.db_ops.log_processing_start(
            'tender_discovery',
            metadata={
                'start_date': start_date,
                'end_date': end_date,
                'states': states,
                'modalities': self.config.allowed_modalities
            }
        )

        try:
            # Process each state
            for state_code in states:
                try:
                    state_stats = await self._discover_state_tenders(
                        state_code, start_date, end_date
                    )

                    # Update overall stats
                    stats.total_found += state_stats.total_found
                    stats.medical_relevant += state_stats.medical_relevant
                    stats.by_state[state_code] = state_stats.total_found

                    # Merge other statistics
                    self._merge_stats_dicts(stats.by_government_level, state_stats.by_government_level)
                    self._merge_stats_dicts(stats.by_size, state_stats.by_size)
                    self._merge_stats_dicts(stats.by_modality, state_stats.by_modality)

                    logger.info(f"Completed {state_code}: {state_stats.total_found} tenders, "
                              f"{state_stats.medical_relevant} medical relevant")

                except Exception as e:
                    error_msg = f"Error processing state {state_code}: {str(e)}"
                    logger.error(error_msg)
                    stats.errors.append(error_msg)

            # Calculate processing time
            stats.processing_time_seconds = (datetime.now() - start_time).total_seconds()

            # Log completion
            await self.db_ops.log_processing_end(
                log_id, 'completed', stats.total_found, stats.medical_relevant
            )

            logger.info(f"Discovery completed: {stats.total_found} total tenders, "
                       f"{stats.medical_relevant} medical relevant in {stats.processing_time_seconds:.1f}s")

        except Exception as e:
            error_msg = f"Discovery process failed: {str(e)}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
            await self.db_ops.log_processing_end(log_id, 'failed', error_message=error_msg)

        return stats

    async def _discover_state_tenders(self, state_code: str, start_date: str, end_date: str) -> DiscoveryStats:
        """Discover tenders for a specific state"""

        state_stats = DiscoveryStats()
        state_name = BRAZILIAN_STATES.get(state_code, state_code)

        logger.info(f"Discovering tenders for {state_name} ({state_code})")

        try:
            # Discover raw tenders
            raw_tenders = await self.api_client.discover_tenders_for_state(
                state_code, start_date, end_date, self.config.allowed_modalities
            )

            state_stats.total_found = len(raw_tenders)

            if not raw_tenders:
                logger.info(f"No tenders found for {state_code}")
                return state_stats

            # Process and classify tenders
            processed_tenders = await self._process_raw_tenders(raw_tenders, state_code)

            # Filter relevant tenders
            relevant_tenders = self.classifier.filter_relevant_tenders(
                processed_tenders,
                min_medical_score=self.config.min_match_score,
                allowed_gov_levels=self.config.government_levels,
                min_value=self.config.min_tender_value
            )

            state_stats.medical_relevant = len(relevant_tenders)

            # Store relevant tenders in database
            await self._store_tenders(relevant_tenders, state_code)

            # Update statistics
            self._update_state_stats(state_stats, relevant_tenders)

        except Exception as e:
            error_msg = f"Error discovering tenders for {state_code}: {str(e)}"
            logger.error(error_msg)
            state_stats.errors.append(error_msg)

        return state_stats

    async def _process_raw_tenders(self, raw_tenders: List[Dict], state_code: str) -> List[Dict]:
        """Process raw tender data and add metadata"""

        processed_tenders = []

        for tender in raw_tenders:
            try:
                # Extract key fields
                processed_tender = {
                    'cnpj': tender.get('cnpj', ''),
                    'ano': tender.get('ano') or tender.get('anoCompra'),
                    'sequencial': tender.get('sequencial') or tender.get('sequencialCompra'),
                    'control_number': tender.get('numeroControlePNCPCompra'),
                    'title': tender.get('objetoCompra', ''),
                    'description': tender.get('descricao', ''),
                    'organization_name': tender.get('orgaoEntidade', {}).get('razaoSocial', ''),
                    'total_estimated_value': self._safe_float(tender.get('valorTotalEstimado')),
                    'total_homologated_value': self._safe_float(tender.get('valorTotalHomologado')),
                    'publication_date': self._parse_date(tender.get('dataPublicacaoPncp')),
                    'contracting_modality': tender.get('modalidadeId'),
                    'modality_name': tender.get('modalidadeNome', ''),
                    'state_code': state_code,
                    'municipality_code': tender.get('codigoIbgeMunicipio'),
                    'raw_data': tender  # Keep original for reference
                }

                # Only process tenders with homologated value (completed tenders)
                if processed_tender['total_homologated_value'] and processed_tender['total_homologated_value'] > 0:
                    processed_tenders.append(processed_tender)

            except Exception as e:
                logger.warning(f"Error processing tender {tender.get('numeroControlePNCPCompra', 'unknown')}: {e}")

        logger.info(f"Processed {len(processed_tenders)} completed tenders from {len(raw_tenders)} raw tenders")
        return processed_tenders

    async def _store_tenders(self, tenders: List[Dict], state_code: str):
        """Store tenders and organizations in database"""

        for tender in tenders:
            try:
                classification = tender.get('classification')
                if not classification:
                    continue

                # Store organization
                org_data = {
                    'cnpj': tender['cnpj'],
                    'name': tender['organization_name'],
                    'government_level': classification.government_level.value,
                    'organization_type': classification.organization_type.value,
                    'state_code': state_code
                }

                org_id = await self.db_ops.insert_organization(org_data)

                # Store tender
                tender_data = {
                    'organization_id': org_id,
                    'cnpj': tender['cnpj'],
                    'ano': tender['ano'],
                    'sequencial': tender['sequencial'],
                    'control_number': tender.get('control_number'),
                    'title': tender.get('title'),
                    'description': tender.get('description'),
                    'government_level': classification.government_level.value,
                    'tender_size': classification.tender_size.value,
                    'contracting_modality': tender.get('contracting_modality'),
                    'modality_name': tender.get('modality_name'),
                    'total_estimated_value': tender.get('total_estimated_value'),
                    'total_homologated_value': tender.get('total_homologated_value'),
                    'publication_date': tender.get('publication_date'),
                    'state_code': state_code,
                    'municipality_code': tender.get('municipality_code'),
                    'status': 'discovered'
                }

                await self.db_ops.insert_tender(tender_data)

            except Exception as e:
                logger.error(f"Error storing tender {tender.get('control_number', 'unknown')}: {e}")

    def _update_state_stats(self, stats: DiscoveryStats, tenders: List[Dict]):
        """Update statistics with tender data"""

        for tender in tenders:
            classification = tender.get('classification')
            if classification:
                # Government level
                gov_level = classification.government_level.value
                stats.by_government_level[gov_level] = stats.by_government_level.get(gov_level, 0) + 1

                # Tender size
                size = classification.tender_size.value
                stats.by_size[size] = stats.by_size.get(size, 0) + 1

            # Modality
            modality = tender.get('contracting_modality')
            if modality:
                stats.by_modality[str(modality)] = stats.by_modality.get(str(modality), 0) + 1

    def _merge_stats_dicts(self, target: Dict[str, int], source: Dict[str, int]):
        """Merge statistics dictionaries"""
        for key, value in source.items():
            target[key] = target.get(key, 0) + value

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str:
            return None

        # Handle different date formats
        try:
            # Try YYYY-MM-DD format
            if len(date_str) >= 10:
                return date_str[:10]

            # Try YYYYMMDD format
            if len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        except Exception:
            pass

        return None

    async def get_unprocessed_tenders_for_items(self, state_code: str = None,
                                              limit: int = 100) -> List[Dict]:
        """Get tenders that need item extraction"""
        return await self.db_ops.get_unprocessed_tenders(state_code, limit)

    async def discover_recent_tenders(self, days_back: int = 30,
                                    states: List[str] = None) -> DiscoveryStats:
        """Discover tenders from recent days"""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        return await self.discover_tenders_for_date_range(start_date_str, end_date_str, states)

    async def discover_by_date_chunks(self, start_date: str, end_date: str,
                                    chunk_days: int = 7, states: List[str] = None) -> List[DiscoveryStats]:
        """Discover tenders by breaking date range into chunks to avoid API limits"""

        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')

        chunk_results = []
        current_date = start_dt

        while current_date < end_dt:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_dt)

            chunk_start_str = current_date.strftime('%Y%m%d')
            chunk_end_str = chunk_end.strftime('%Y%m%d')

            logger.info(f"Processing chunk: {chunk_start_str} to {chunk_end_str}")

            try:
                chunk_stats = await self.discover_tenders_for_date_range(
                    chunk_start_str, chunk_end_str, states
                )
                chunk_results.append(chunk_stats)

                # Small delay between chunks
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing chunk {chunk_start_str}-{chunk_end_str}: {e}")

            current_date = chunk_end

        return chunk_results


# Utility functions for discovery management
async def create_discovery_engine(db_manager: CloudSQLManager, username: str = None,
                                password: str = None, config: ProcessingConfig = None) -> TenderDiscoveryEngine:
    """Create configured discovery engine"""

    api_client = PNCPAPIClient(username, password)
    classifier = TenderClassifier()
    db_ops = DatabaseOperations(db_manager)

    return TenderDiscoveryEngine(api_client, classifier, db_ops, config)

async def run_full_state_discovery(states: List[str], start_date: str, end_date: str,
                                 db_manager: CloudSQLManager, username: str = None,
                                 password: str = None) -> DiscoveryStats:
    """Run complete discovery for specified states"""

    async with PNCPAPIClient(username, password) as api_client:
        classifier = TenderClassifier()
        db_ops = DatabaseOperations(db_manager)

        engine = TenderDiscoveryEngine(api_client, classifier, db_ops)

        return await engine.discover_tenders_for_date_range(start_date, end_date, states)

def print_discovery_stats(stats: DiscoveryStats):
    """Print formatted discovery statistics"""

    print("=== TENDER DISCOVERY STATISTICS ===")
    print(f"Total Tenders Found: {stats.total_found:,}")
    print(f"Medical Relevant: {stats.medical_relevant:,}")
    print(f"Processing Time: {stats.processing_time_seconds:.1f} seconds")

    if stats.by_state:
        print("\n--- By State ---")
        for state, count in sorted(stats.by_state.items()):
            state_name = BRAZILIAN_STATES.get(state, state)
            print(f"{state_name} ({state}): {count:,}")

    if stats.by_government_level:
        print("\n--- By Government Level ---")
        for level, count in stats.by_government_level.items():
            print(f"{level.title()}: {count:,}")

    if stats.by_size:
        print("\n--- By Tender Size ---")
        for size, count in stats.by_size.items():
            print(f"{size.title()}: {count:,}")

    if stats.errors:
        print(f"\n--- Errors ({len(stats.errors)}) ---")
        for error in stats.errors[:5]:  # Show first 5 errors
            print(f"- {error}")


# Example usage and testing
async def test_discovery():
    """Test discovery functionality"""

    # This would need actual database connection and API credentials
    print("Discovery module test - would need actual DB and API credentials")

    # Example configuration
    config = ProcessingConfig(
        enabled_states=['DF', 'SP'],  # Just test with Federal District and São Paulo
        min_tender_value=10000.0,
        min_match_score=20.0
    )

    print(f"Test configuration: {len(config.enabled_states)} states, "
          f"min value: R${config.min_tender_value:,.2f}")

if __name__ == "__main__":
    asyncio.run(test_discovery())