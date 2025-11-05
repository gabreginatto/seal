"""
Optimized Multi-Stage Lacre Tender Discovery System
Implements progressive filtering to minimize API calls and maximize efficiency

Stage 1: Bulk Fetch (1 API call) → 1000 tenders
Stage 2: Quick Filter (0 API calls) → 300 tenders (70% reduction)
Stage 3: Smart Sampling (300 API calls) → 100 tenders (sample first 3 items only)
Stage 4: Full Processing (1000+ API calls) → 100 tenders (complete processing)

Expected Performance: 95% reduction in API calls, 89% faster processing
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from .config_lacre import LacreProcessingConfig, LACRE_KEYWORDS
from .pncp_api import PNCPAPIClient
from .classifier_lacre import LacreTenderClassifier
from .database_lacre import LacreDatabaseOperations

logger = logging.getLogger(__name__)

@dataclass
class StageMetrics:
    """Metrics for a single processing stage"""
    stage_name: str
    tenders_in: int = 0
    tenders_out: int = 0
    api_calls: int = 0
    duration_seconds: float = 0.0
    errors: int = 0

    @property
    def reduction_percent(self) -> float:
        """Calculate reduction percentage"""
        if self.tenders_in == 0:
            return 0.0
        return ((self.tenders_in - self.tenders_out) / self.tenders_in) * 100

    @property
    def throughput(self) -> float:
        """Tenders processed per second"""
        if self.duration_seconds == 0:
            return 0.0
        return self.tenders_in / self.duration_seconds


@dataclass
class LacreDiscoveryMetrics:
    """Complete metrics for multi-stage lacre discovery"""
    stage1_bulk_fetch: StageMetrics = field(default_factory=lambda: StageMetrics("Stage 1: Bulk Fetch"))
    stage2_quick_filter: StageMetrics = field(default_factory=lambda: StageMetrics("Stage 2: Quick Filter"))
    stage3_smart_sampling: StageMetrics = field(default_factory=lambda: StageMetrics("Stage 3: Smart Sampling"))
    stage4_full_processing: StageMetrics = field(default_factory=lambda: StageMetrics("Stage 4: Full Processing"))

    @property
    def total_api_calls(self) -> int:
        """Total API calls across all stages"""
        return (self.stage1_bulk_fetch.api_calls +
                self.stage2_quick_filter.api_calls +
                self.stage3_smart_sampling.api_calls +
                self.stage4_full_processing.api_calls)

    @property
    def total_duration(self) -> float:
        """Total processing duration"""
        return (self.stage1_bulk_fetch.duration_seconds +
                self.stage2_quick_filter.duration_seconds +
                self.stage3_smart_sampling.duration_seconds +
                self.stage4_full_processing.duration_seconds)

    @property
    def api_efficiency(self) -> float:
        """Ratio of final results to total API calls"""
        if self.total_api_calls == 0:
            return 0.0
        return self.stage4_full_processing.tenders_out / self.total_api_calls


class OptimizedLacreDiscovery:
    """
    Multi-stage lacre tender discovery with progressive filtering
    Minimizes API calls by filtering aggressively at each stage
    """

    def __init__(self, api_client: PNCPAPIClient, classifier: LacreTenderClassifier,
                 db_operations: LacreDatabaseOperations, config: LacreProcessingConfig = None):
        self.api_client = api_client
        self.classifier = classifier
        self.db_ops = db_operations
        self.config = config or LacreProcessingConfig()

        # Caching system
        self.lacre_orgs_cache: Set[str] = set()
        self.non_lacre_orgs_cache: Set[str] = set()
        self.tender_cache: Dict[str, Dict] = {}
        self.item_cache: Dict[str, List[Dict]] = {}

        # Metrics tracking
        self.metrics = LacreDiscoveryMetrics()

    async def discover_lacre_tenders_optimized(
        self, state: str, start_date: str, end_date: str
    ) -> Tuple[List[Dict], LacreDiscoveryMetrics]:
        """
        Main entry point for optimized multi-stage lacre discovery
        Returns: (lacre_tenders, metrics)
        """
        logger.info(f"🚀 Starting optimized lacre discovery for {state} ({start_date} to {end_date})")

        # STAGE 1: Bulk fetch
        raw_tenders = await self._stage1_bulk_fetch(state, start_date, end_date)
        logger.info(f"📥 Stage 1 complete: {len(raw_tenders)} tenders fetched")

        # DEDUPLICATION: Filter out tenders already in database
        new_tenders = await self._filter_new_tenders(raw_tenders)
        duplicates_filtered = len(raw_tenders) - len(new_tenders)
        if duplicates_filtered > 0:
            logger.info(f"🔄 Deduplication: {duplicates_filtered} tenders already in DB, "
                       f"{len(new_tenders)} new tenders to process")

        # STAGE 2: Quick filter (zero API calls)
        quick_filtered = await self._stage2_quick_filter(new_tenders)
        logger.info(f"🔍 Stage 2 complete: {len(quick_filtered)} tenders retained "
                   f"({self.metrics.stage2_quick_filter.reduction_percent:.1f}% filtered out)")

        # STAGE 3: Smart sampling (minimal API calls)
        sampled = await self._stage3_smart_sampling(quick_filtered)
        logger.info(f"🎯 Stage 3 complete: {len(sampled)} tenders confirmed via sampling "
                   f"({self.metrics.stage3_smart_sampling.reduction_percent:.1f}% filtered out)")

        # STAGE 4: Full processing
        processed = await self._stage4_full_processing(sampled)
        logger.info(f"⚡ Stage 4 complete: {len(processed)} tenders fully processed")

        # STAGE 5: Save tenders to database
        saved_count = await self._save_tenders_to_db(processed, state)
        logger.info(f"💾 Stage 5 complete: {saved_count} tenders saved to database")

        # Summary
        logger.info(f"✅ Discovery complete: {self.metrics.total_api_calls} API calls, "
                   f"{self.metrics.total_duration:.1f}s total, "
                   f"{self.metrics.api_efficiency:.2f} efficiency ratio")

        return processed, self.metrics

    async def _filter_new_tenders(self, tenders: List[Dict]) -> List[Dict]:
        """Filter out tenders that already exist in database"""
        return await self.db_ops.filter_new_tenders(tenders)

    async def _stage1_bulk_fetch(self, state: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Stage 1: Bulk fetch tenders from API
        Strategy: Fetch all ONGOING tenders for the date range with basic filters
        """
        start_time = datetime.now()

        try:
            # Fetch using configured modalities and ONGOING filter
            raw_tenders = await self.api_client.discover_tenders_for_state(
                state, start_date, end_date,
                modalities=self.config.allowed_modalities,
                only_ongoing=self.config.only_ongoing_tenders
            )

            # Update metrics
            self.metrics.stage1_bulk_fetch.tenders_in = 0  # Initial fetch
            self.metrics.stage1_bulk_fetch.tenders_out = len(raw_tenders)
            self.metrics.stage1_bulk_fetch.api_calls = len(self.config.allowed_modalities)  # One call per modality
            self.metrics.stage1_bulk_fetch.duration_seconds = (datetime.now() - start_time).total_seconds()

            return raw_tenders

        except Exception as e:
            logger.error(f"Stage 1 error: {e}")
            self.metrics.stage1_bulk_fetch.errors += 1
            return []

    async def _stage2_quick_filter(self, tenders: List[Dict]) -> List[Dict]:
        """
        Stage 2: Quick filter using lacre keywords and value filters (ZERO API calls)
        Strategy: Use keyword matching, value filters, ongoing status check
        """
        start_time = datetime.now()
        self.metrics.stage2_quick_filter.tenders_in = len(tenders)

        filtered = []

        for tender in tenders:
            try:
                # Quick lacre relevance check
                title = tender.get('objetoCompra', '')
                description = tender.get('descricao', '')

                score = self._count_lacre_keywords(title, description)

                # Apply value filters (use homologated value like Medical system)
                homologated_value = tender.get('valorTotalHomologado') or 0

                # Skip if value is below minimum
                if homologated_value < self.config.min_tender_value:
                    continue

                if self.config.max_tender_value and homologated_value > self.config.max_tender_value:
                    continue

                # Note: Removed ongoing status filter - we process all tenders now
                # The config.only_ongoing_tenders controls Stage 1 API calls, not Stage 2 filtering

                # Threshold for proceeding to next stage
                if score >= 1:  # At least 1 lacre keyword
                    tender['quick_filter_score'] = score
                    filtered.append(tender)

            except Exception as e:
                logger.warning(f"Error in quick filter for tender {tender.get('numeroControlePNCPCompra')}: {e}")
                self.metrics.stage2_quick_filter.errors += 1

        # Sort by score for prioritized processing
        filtered.sort(key=lambda x: x.get('quick_filter_score', 0), reverse=True)

        # Update metrics
        self.metrics.stage2_quick_filter.tenders_out = len(filtered)
        self.metrics.stage2_quick_filter.api_calls = 0  # No API calls!
        self.metrics.stage2_quick_filter.duration_seconds = (datetime.now() - start_time).total_seconds()

        return filtered

    def _count_lacre_keywords(self, title: str, description: str) -> int:
        """Count lacre keywords in tender title and description"""
        if not title and not description:
            return 0

        text = f"{title} {description}".lower()
        count = sum(1 for keyword in LACRE_KEYWORDS if keyword in text)
        return count

    def _count_lacre_keywords_in_object(self, objeto: str) -> int:
        """Count strong lacre keywords in tender object description"""
        if not objeto:
            return 0

        objeto_lower = objeto.lower()

        # Strong lacre keywords that are highly indicative
        strong_keywords = [
            'lacre', 'lacres',
            'lacre de segurança', 'lacre inviolável', 'lacre antifraude',
            'lacre numerado', 'lacre sequencial',
            'seal', 'seals', 'security seal', 'tamper evident',
            'selo-lacre', 'etiqueta void', 'void label',
            'lacre plástico', 'lacre metálico',
            'lacre para hidrômetro', 'lacre medidor',
            'pulseira inviolável', 'pulseira com lacre',
            'envelope de segurança', 'envelope lacrado',
            'dispositivo de segurança', 'dispositivo inviolável'
        ]

        return sum(1 for keyword in strong_keywords if keyword in objeto_lower)

    async def _stage3_smart_sampling(self, tenders: List[Dict]) -> List[Dict]:
        """
        Stage 3: FULL ITEM ANALYSIS (NO SAMPLING - Critical for lacres!)

        ⚠️  CRITICAL DIFFERENCE FROM MEDICAL PROJECT:
        - Medical items: Homogeneous (if 3 items are medical, all 97 are likely medical)
        - Lacre items: Heterogeneous (99 office supplies + 1 lacre = we MUST check all 100)

        Strategy: Fetch ALL items for ALL tenders and analyze each one for lacres
        This is slower but necessary because lacres can be bundled with unrelated items.
        """
        start_time = datetime.now()
        self.metrics.stage3_smart_sampling.tenders_in = len(tenders)

        logger.info(f"📋 Stage 3: Full item analysis for {len(tenders)} tenders")
        logger.info("⚠️  NO SAMPLING - Analyzing EVERY item to find lacres")

        verified_tenders = []
        items_analyzed = 0
        tenders_with_lacres = 0
        api_calls = 0
        api_calls_lock = asyncio.Lock()

        # Process in batches to manage rate limits
        batch_size = 5  # Process 5 tenders at a time
        semaphore = asyncio.Semaphore(batch_size)

        async def analyze_tender_items(tender):
            """Analyze all items for a single tender"""
            nonlocal api_calls

            async with semaphore:
                try:
                    result = await self._analyze_all_tender_items(tender)

                    async with api_calls_lock:
                        api_calls += 1  # One API call per tender (with pagination)

                    return result

                except Exception as e:
                    logger.error(f"Error analyzing tender {tender.get('numeroControlePNCPCompra')}: {e}")
                    self.metrics.stage3_smart_sampling.errors += 1
                    return None

        # Process all tenders in batches
        for i in range(0, len(tenders), batch_size):
            batch = tenders[i:i + batch_size]

            # Fetch ALL items for each tender in batch (with pagination)
            tasks = [analyze_tender_items(tender) for tender in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for tender, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing tender {tender.get('numeroControlePNCPCompra')}: {result}")
                    continue

                if result is None:
                    continue

                if result['has_lacres']:
                    verified_tenders.append({
                        **tender,
                        'verification_method': 'full_item_analysis',
                        'items_analyzed': result['total_items'],
                        'lacre_items_found': result['lacre_items_count'],
                        'lacre_items': result['lacre_items'],  # List of matching items
                        'all_items': result.get('all_items', [])  # Store all items for saving later
                    })
                    tenders_with_lacres += 1
                    logger.info(
                        f"✅ Found {result['lacre_items_count']} lacre items in "
                        f"{result['total_items']} total items - {tender.get('numeroControlePNCPCompra')}"
                    )

                items_analyzed += result['total_items']

            # Respect rate limits
            await asyncio.sleep(1)

        logger.info(f"✅ Stage 3 complete: {tenders_with_lacres}/{len(tenders)} tenders have lacres")
        logger.info(f"📊 Analyzed {items_analyzed} total items")

        # Update metrics
        self.metrics.stage3_smart_sampling.tenders_out = len(verified_tenders)
        self.metrics.stage3_smart_sampling.api_calls = api_calls
        self.metrics.stage3_smart_sampling.duration_seconds = (datetime.now() - start_time).total_seconds()

        return verified_tenders

    async def _analyze_all_tender_items(self, tender: Dict) -> Dict:
        """
        Fetch ALL items for a tender (with pagination) and check each for lacre keywords

        Returns:
            {
                'has_lacres': bool,
                'total_items': int,
                'lacre_items_count': int,
                'lacre_items': List[Dict],  # Items that contain lacre keywords
                'all_items': List[Dict]  # ALL items (for saving to database later)
            }
        """
        # Extract CNPJ from nested structure
        cnpj = tender.get('orgaoEntidade', {}).get('cnpj', '') or tender.get('cnpj', '')
        year = tender.get('ano') or tender.get('anoCompra')
        sequential = tender.get('sequencial') or tender.get('sequencialCompra')

        if not all([cnpj, year, sequential]):
            return {
                'has_lacres': False,
                'total_items': 0,
                'lacre_items_count': 0,
                'lacre_items': [],
                'all_items': []
            }

        # Fetch ALL items with pagination (uses get_tender_items which has pagination)
        status, response = await self.api_client.get_tender_items(cnpj, year, sequential)

        if status != 200:
            logger.warning(f"Failed to fetch items for {cnpj}/{year}/{sequential}: status {status}")
            return {
                'has_lacres': False,
                'total_items': 0,
                'lacre_items_count': 0,
                'lacre_items': [],
                'all_items': []
            }

        # Extract items from response
        all_items = response.get('data', []) if isinstance(response, dict) else response

        if not all_items:
            return {
                'has_lacres': False,
                'total_items': 0,
                'lacre_items_count': 0,
                'lacre_items': [],
                'all_items': []
            }

        # Analyze EVERY item for lacre keywords
        lacre_items = []

        for item in all_items:
            if self._item_contains_lacre(item):
                lacre_items.append({
                    'numero': item.get('numeroItem'),
                    'descricao': item.get('descricao', ''),
                    'quantidade': item.get('quantidade'),
                    'valorUnitario': item.get('valorUnitarioEstimado'),
                    'valorTotal': item.get('valorTotalEstimado')
                })

        return {
            'has_lacres': len(lacre_items) > 0,
            'total_items': len(all_items),
            'lacre_items_count': len(lacre_items),
            'lacre_items': lacre_items,
            'all_items': all_items  # Store ALL items for database saving
        }

    def _item_contains_lacre(self, item: Dict) -> bool:
        """
        Check if an item description contains lacre-related keywords

        Returns True if ANY lacre keyword is found in the item description
        """
        description = item.get('descricao', '').lower()

        if not description:
            return False

        # Check if any lacre keyword is present
        return any(keyword in description for keyword in LACRE_KEYWORDS)

    def _analyze_sample_items(self, items: List[Dict]) -> float:
        """
        Analyze sample items for lacre relevance
        Returns confidence score (0-100)

        NOTE: This method is kept for backward compatibility but is NOT used
        in the new full item analysis approach for lacre detection.
        """
        if not items:
            return 0.0

        lacre_indicators = 0
        total_items = len(items)

        for item in items:
            description = (item.get('descricao', '') or item.get('descricaoItem', '')).lower()

            # Check for lacre keywords in item description
            if any(keyword in description for keyword in LACRE_KEYWORDS):
                lacre_indicators += 1

        confidence = (lacre_indicators / total_items) * 100 if total_items > 0 else 0
        return confidence

    async def _stage4_full_processing(self, tenders: List[Dict]) -> List[Dict]:
        """
        Stage 4: Full processing with item fetching and classification
        Strategy: Priority-based (high value first), adaptive concurrency
        """
        start_time = datetime.now()
        self.metrics.stage4_full_processing.tenders_in = len(tenders)

        # Group by value priority
        high_value = [t for t in tenders if (t.get('valorTotalEstimado', 0) or t.get('valorTotalHomologado', 0)) > 100_000]
        medium_value = [t for t in tenders if 10_000 <= (t.get('valorTotalEstimado', 0) or t.get('valorTotalHomologado', 0)) <= 100_000]
        low_value = [t for t in tenders if (t.get('valorTotalEstimado', 0) or t.get('valorTotalHomologado', 0)) < 10_000]

        logger.info(f"Stage 4 priority groups: {len(high_value)} high, {len(medium_value)} medium, {len(low_value)} low value")

        processed = []
        api_calls = 0

        # Process each priority group
        for priority_group, group_name in [(high_value, "high"), (medium_value, "medium"), (low_value, "low")]:
            if not priority_group:
                continue

            # Adaptive concurrency
            max_concurrent = 10 if group_name == "high" else (5 if group_name == "medium" else 3)
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_tender(tender):
                nonlocal api_calls

                async with semaphore:
                    try:
                        # Use cached sample items if available
                        if 'sample_items' in tender:
                            items = tender['sample_items']
                            api_calls += 0  # Using cached data
                        else:
                            # Note: Full item fetching would happen here if needed
                            api_calls += 0

                        # Classify tender using lacre classifier (for metadata, not filtering)
                        title = tender.get('objetoCompra', '')
                        description = tender.get('descricao', '')
                        is_relevant, score, keywords, reasoning = self.classifier.assess_lacre_relevance(title, description)

                        # Always keep the tender (don't reject here like Medical system)
                        tender['lacre_classification'] = {
                            'is_relevant': is_relevant,
                            'score': score,
                            'keywords': keywords,
                            'reasoning': reasoning
                        }
                        return tender

                    except Exception as e:
                        logger.error(f"Processing error for {tender.get('numeroControlePNCPCompra')}: {e}")
                        self.metrics.stage4_full_processing.errors += 1
                        return None

            tasks = [process_tender(t) for t in priority_group]
            results = await asyncio.gather(*tasks)
            processed.extend([r for r in results if r is not None])

        # Update metrics
        self.metrics.stage4_full_processing.tenders_out = len(processed)
        self.metrics.stage4_full_processing.api_calls = api_calls
        self.metrics.stage4_full_processing.duration_seconds = (datetime.now() - start_time).total_seconds()

        return processed

    async def _save_tenders_to_db(self, tenders: List[Dict], state: str) -> int:
        """Save processed tenders to database"""
        saved_count = 0

        for tender in tenders:
            try:
                # First, ensure organization exists
                org_data = tender.get('orgaoEntidade', {})
                cnpj = self._normalize_cnpj(org_data.get('cnpj', ''))

                if not cnpj:
                    logger.warning(f"Tender {tender.get('numeroControlePNCP')} has no CNPJ, skipping")
                    continue

                # Determine government level
                gov_level = 'municipal'  # Default
                org_name = org_data.get('razaoSocial', '').lower()
                if 'estado' in org_name or 'secretaria de estado' in org_name:
                    gov_level = 'state'
                elif 'federal' in org_name or 'ministério' in org_name or 'ministerio' in org_name:
                    gov_level = 'federal'

                org_id = await self.db_ops.insert_organization({
                    'cnpj': cnpj,
                    'name': org_data.get('razaoSocial', 'Unknown'),
                    'government_level': gov_level,
                    'organization_type': 'public',
                    'state_code': state
                })

                # Get year and sequential
                year = tender.get('ano') or tender.get('anoCompra')
                sequential = tender.get('sequencial') or tender.get('sequencialCompra')

                # Determine tender size
                estimated_value = tender.get('valorTotalEstimado', 0) or 0
                homologated_value = tender.get('valorTotalHomologado', 0) or 0
                tender_value = max(estimated_value, homologated_value)

                if tender_value < 50_000:
                    tender_size = 'small'
                elif tender_value < 500_000:
                    tender_size = 'medium'
                elif tender_value < 5_000_000:
                    tender_size = 'large'
                else:
                    tender_size = 'mega'

                # Prepare tender data
                tender_data = {
                    'organization_id': org_id,
                    'cnpj': cnpj,
                    'ano': year,
                    'sequencial': sequential,
                    'control_number': tender.get('numeroControlePNCP'),
                    'title': tender.get('objetoCompra', ''),
                    'description': tender.get('descricao', ''),
                    'government_level': gov_level,
                    'tender_size': tender_size,
                    'contracting_modality': tender.get('modalidadeId'),
                    'modality_name': tender.get('modalidadeNome', ''),
                    'total_estimated_value': estimated_value,
                    'total_homologated_value': homologated_value,
                    'publication_date': tender.get('dataPublicacaoPncp', '')[:10] if tender.get('dataPublicacaoPncp') else None,
                    'state_code': state,
                    'municipality_code': tender.get('codigoIbgeMunicipio'),
                    'status': tender.get('situacaoCompra') or tender.get('situacao') or 'discovered'
                }

                # Insert tender
                tender_id = await self.db_ops.insert_tender(tender_data)
                saved_count += 1

                logger.debug(f"Saved tender {tender.get('numeroControlePNCP')} to database (ID: {tender_id})")

                # ✅ NEW: Save ALL items with is_lacre flag
                all_items = tender.get('all_items', [])
                if all_items:
                    items_to_save = []
                    for item in all_items:
                        # Check if this item is a lacre item
                        is_lacre = self._item_contains_lacre(item)

                        items_to_save.append({
                            'tender_id': tender_id,
                            'item_number': item.get('numeroItem'),
                            'description': item.get('descricao', ''),
                            'unit': item.get('unidadeMedida'),
                            'quantity': item.get('quantidade'),
                            'estimated_unit_value': item.get('valorUnitarioEstimado'),
                            'estimated_total_value': item.get('valorTotalEstimado'),
                            'homologated_unit_value': None,  # Will be updated later if available
                            'homologated_total_value': None,
                            'winner_name': None,
                            'winner_cnpj': None,
                            'is_lacre': is_lacre  # ✅ CRITICAL: Mark lacre items
                        })

                    # Save items in batch
                    if items_to_save:
                        await self.db_ops.insert_tender_items_batch(items_to_save)
                        lacre_count = sum(1 for item in items_to_save if item['is_lacre'])
                        logger.debug(f"Saved {len(items_to_save)} items ({lacre_count} lacre items) for tender {tender_id}")

            except Exception as e:
                logger.error(f"Error saving tender {tender.get('numeroControlePNCP')}: {e}")
                continue

        return saved_count

    def _normalize_cnpj(self, cnpj: str) -> str:
        """Normalize CNPJ to digits only"""
        if not cnpj:
            return ""
        return ''.join(filter(str.isdigit, cnpj))

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            'total_api_calls': self.metrics.total_api_calls,
            'total_duration_seconds': self.metrics.total_duration,
            'api_efficiency_ratio': self.metrics.api_efficiency,
            'stages': {
                'stage1': {
                    'name': self.metrics.stage1_bulk_fetch.stage_name,
                    'tenders_out': self.metrics.stage1_bulk_fetch.tenders_out,
                    'api_calls': self.metrics.stage1_bulk_fetch.api_calls,
                    'duration': self.metrics.stage1_bulk_fetch.duration_seconds,
                },
                'stage2': {
                    'name': self.metrics.stage2_quick_filter.stage_name,
                    'tenders_in': self.metrics.stage2_quick_filter.tenders_in,
                    'tenders_out': self.metrics.stage2_quick_filter.tenders_out,
                    'reduction_percent': self.metrics.stage2_quick_filter.reduction_percent,
                    'api_calls': self.metrics.stage2_quick_filter.api_calls,
                    'duration': self.metrics.stage2_quick_filter.duration_seconds,
                },
                'stage3': {
                    'name': self.metrics.stage3_smart_sampling.stage_name,
                    'tenders_in': self.metrics.stage3_smart_sampling.tenders_in,
                    'tenders_out': self.metrics.stage3_smart_sampling.tenders_out,
                    'reduction_percent': self.metrics.stage3_smart_sampling.reduction_percent,
                    'api_calls': self.metrics.stage3_smart_sampling.api_calls,
                    'duration': self.metrics.stage3_smart_sampling.duration_seconds,
                },
                'stage4': {
                    'name': self.metrics.stage4_full_processing.stage_name,
                    'tenders_in': self.metrics.stage4_full_processing.tenders_in,
                    'tenders_out': self.metrics.stage4_full_processing.tenders_out,
                    'api_calls': self.metrics.stage4_full_processing.api_calls,
                    'duration': self.metrics.stage4_full_processing.duration_seconds,
                }
            }
        }


def print_metrics_summary(metrics: LacreDiscoveryMetrics):
    """Print formatted metrics summary"""
    print("\n" + "="*70)
    print("📊 MULTI-STAGE LACRE DISCOVERY PERFORMANCE METRICS")
    print("="*70)

    # Stage 1
    print(f"\n📥 {metrics.stage1_bulk_fetch.stage_name}")
    print(f"   Fetched: {metrics.stage1_bulk_fetch.tenders_out:,} tenders")
    print(f"   API Calls: {metrics.stage1_bulk_fetch.api_calls}")
    print(f"   Duration: {metrics.stage1_bulk_fetch.duration_seconds:.2f}s")

    # Stage 2
    print(f"\n🔍 {metrics.stage2_quick_filter.stage_name}")
    print(f"   Input: {metrics.stage2_quick_filter.tenders_in:,} tenders")
    print(f"   Output: {metrics.stage2_quick_filter.tenders_out:,} tenders")
    print(f"   Filtered: {metrics.stage2_quick_filter.reduction_percent:.1f}%")
    print(f"   API Calls: {metrics.stage2_quick_filter.api_calls} (ZERO!)")
    print(f"   Duration: {metrics.stage2_quick_filter.duration_seconds:.2f}s")

    # Stage 3
    print(f"\n🎯 {metrics.stage3_smart_sampling.stage_name}")
    print(f"   Input: {metrics.stage3_smart_sampling.tenders_in:,} tenders")
    print(f"   Output: {metrics.stage3_smart_sampling.tenders_out:,} tenders")
    print(f"   Filtered: {metrics.stage3_smart_sampling.reduction_percent:.1f}%")
    print(f"   API Calls: {metrics.stage3_smart_sampling.api_calls}")
    print(f"   Duration: {metrics.stage3_smart_sampling.duration_seconds:.2f}s")

    # Stage 4
    print(f"\n⚡ {metrics.stage4_full_processing.stage_name}")
    print(f"   Input: {metrics.stage4_full_processing.tenders_in:,} tenders")
    print(f"   Output: {metrics.stage4_full_processing.tenders_out:,} tenders")
    print(f"   API Calls: {metrics.stage4_full_processing.api_calls}")
    print(f"   Duration: {metrics.stage4_full_processing.duration_seconds:.2f}s")

    # Overall
    print(f"\n{'='*70}")
    print(f"✅ OVERALL PERFORMANCE")
    print(f"{'='*70}")
    print(f"Total API Calls: {metrics.total_api_calls:,}")
    print(f"Total Duration: {metrics.total_duration:.2f}s")
    print(f"API Efficiency: {metrics.api_efficiency:.4f} (final results / API calls)")
    if metrics.total_duration > 0:
        print(f"Throughput: {metrics.stage1_bulk_fetch.tenders_out / metrics.total_duration:.1f} tenders/second")
    print("="*70 + "\n")
