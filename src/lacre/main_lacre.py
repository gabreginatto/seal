"""
PNCP Lacre (Security Seals) Data Processing - Main Orchestration Module
Coordinates the complete workflow from ongoing tender discovery to analysis
"""

import asyncio
import logging
import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .config_lacre import (
    LacreProcessingConfig, LacreDatabaseConfig, get_state_codes,
    BRAZILIAN_STATES, DEFAULT_LACRE_CONFIG
)
from .database_lacre import create_lacre_db_manager_from_env, LacreDatabaseOperations
from .pncp_api import PNCPAPIClient, test_api_connection
from .classifier_lacre import LacreTenderClassifier
from .optimized_lacre_discovery import OptimizedLacreDiscovery, print_metrics_summary
from .processed_lacre_tenders_tracker import (
    ProcessedLacreTendersTracker, LacreTenderIdentifier, get_processed_lacre_tenders_tracker
)

# Configure logging with timestamped log file in logs directory
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_filename = f"pncp_lacre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_filepath = os.path.join(log_dir, log_filename)

# Store log filepath globally for run.sh script to access
os.environ['PNCP_CURRENT_LOG'] = log_filepath

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"📝 Log file: {log_filepath}")

class PNCPLacreProcessor:
    """Main orchestration class for PNCP lacre data processing"""

    def __init__(self, config: LacreProcessingConfig = None):
        self.config = config or DEFAULT_LACRE_CONFIG
        self.db_manager = None
        self.db_ops = None
        self.api_client = None
        self.classifier = None
        self.discovery_engine = None
        self.tracker = None

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing PNCP Lacre Processor...")

        try:
            # Initialize database
            await self._initialize_database()

            # Initialize API client
            await self._initialize_api_client()

            # Initialize processing components
            self._initialize_processors()

            # Initialize processed tenders tracker
            self.tracker = get_processed_lacre_tenders_tracker()
            logger.info(f"Loaded tracker with {len(self.tracker.processed_tenders)} processed tenders")

            logger.info("Initialization completed successfully")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def _initialize_database(self):
        """Initialize Cloud SQL database connection"""
        logger.info("Initializing lacre database connection...")

        try:
            self.db_manager = create_lacre_db_manager_from_env()
            self.db_ops = LacreDatabaseOperations(self.db_manager)

            logger.info(f"✓ Connected to lacre database: {self.db_manager.database_name}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _initialize_api_client(self):
        """Initialize PNCP API client and test connection"""
        logger.info("Initializing API client...")

        username = os.getenv('PNCP_USERNAME', '')
        password = os.getenv('PNCP_PASSWORD', '')

        # PNCP is a public API - credentials are optional
        self.api_client = PNCPAPIClient(username, password)

        logger.info("API client initialized (using public PNCP API access)")

    def _initialize_processors(self):
        """Initialize processing components"""
        logger.info("Initializing processing components...")

        self.classifier = LacreTenderClassifier()

        self.discovery_engine = OptimizedLacreDiscovery(
            self.api_client, self.classifier, self.db_ops, self.config
        )

        logger.info("Processing components initialized (optimized multi-stage)")

    async def discover_ongoing_tenders(self, start_date: str, end_date: str,
                                     states: List[str] = None, chunk_days: int = 7):
        """Discover ongoing lacre tenders for specified date range and states"""

        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not initialized")

        states = states or self.config.enabled_states
        logger.info(f"Starting optimized ongoing lacre tender discovery for {len(states)} states: {start_date} to {end_date}")

        all_tenders = []
        all_metrics = []

        # Process each state
        for state in states:
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing state: {state}")
            logger.info(f"{'='*70}")

            try:
                tenders, metrics = await self.discovery_engine.discover_lacre_tenders_optimized(
                    state, start_date, end_date
                )
                all_tenders.extend(tenders)
                all_metrics.append(metrics)

                # Print metrics for this state
                print_metrics_summary(metrics)

            except Exception as e:
                logger.error(f"Error processing state {state}: {e}")

        logger.info(f"\n{'='*70}")
        logger.info(f"DISCOVERY COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Total tenders found: {len(all_tenders)}")
        logger.info(f"States processed: {len(all_metrics)}")

        return all_tenders, all_metrics

    async def run_complete_workflow(self, start_date: str, end_date: str,
                                  states: List[str] = None, chunk_days: int = 7):
        """Run complete workflow: discovery -> analysis"""

        logger.info("Starting complete PNCP lacre data workflow (optimized)")

        workflow_start = datetime.now()

        try:
            # Phase 1: Optimized Ongoing Tender Discovery
            logger.info("=== Phase 1: Optimized Ongoing Lacre Tender Discovery ===")
            all_tenders, all_metrics = await self.discover_ongoing_tenders(start_date, end_date, states, chunk_days)

            if not all_tenders:
                logger.warning("No lacre relevant tenders found")
                return

            # Phase 2: Generate Reports
            logger.info("=== Phase 2: Generating Reports ===")
            await self.generate_reports(all_tenders, all_metrics)

            total_time = (datetime.now() - workflow_start).total_seconds()
            logger.info(f"Complete workflow finished in {total_time:.1f} seconds")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

    async def generate_reports(self, all_tenders, all_metrics):
        """Generate analysis reports"""

        logger.info("Generating analysis reports...")

        # Aggregate metrics
        total_api_calls = sum(m.total_api_calls for m in all_metrics)
        total_duration = sum(m.total_duration for m in all_metrics)

        reports = {
            'discovery_summary': {
                'total_tenders_found': len(all_tenders),
                'ongoing_tenders': sum(1 for t in all_tenders if t.get('is_ongoing', False)),
                'processing_time': total_duration,
                'total_api_calls': total_api_calls,
                'api_efficiency': all_metrics[0].api_efficiency if all_metrics else 0
            },
            'timestamp': datetime.now().isoformat()
        }

        # Save report to file
        report_filename = f"pncp_lacre_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(reports, f, indent=2, default=str)

        logger.info(f"Report saved to {report_filename}")

        # Print summary
        print("\n=== LACRE WORKFLOW SUMMARY ===")
        print(f"Tenders Found: {reports['discovery_summary']['total_tenders_found']:,}")
        print(f"Ongoing Tenders: {reports['discovery_summary']['ongoing_tenders']:,}")
        print(f"API Calls: {reports['discovery_summary']['total_api_calls']:,}")
        print(f"Processing Time: {reports['discovery_summary']['processing_time']:.1f}s")

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")

        if self.api_client:
            await self.api_client.close_session()

        if self.db_manager:
            await self.db_manager.close()

        if self.tracker:
            self.tracker.save_to_file()
            self.tracker.print_stats()

        logger.info("Cleanup completed")

async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description='PNCP Lacre (Security Seals) Data Processor')
    parser.add_argument('--start-date', required=True, help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYYMMDD)')
    parser.add_argument('--states', nargs='*', help='State codes to process (default: all)')
    parser.add_argument('--chunk-days', type=int, default=7, help='Days per processing chunk')
    parser.add_argument('--discovery-only', action='store_true', help='Only run discovery phase')
    parser.add_argument('--config-file', help='Configuration file path')

    args = parser.parse_args()

    # Load configuration
    config = DEFAULT_LACRE_CONFIG
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
            logger.info(f"Loaded configuration from {args.config_file}")

    # Validate states
    if args.states:
        invalid_states = [s for s in args.states if s not in get_state_codes()]
        if invalid_states:
            logger.error(f"Invalid state codes: {invalid_states}")
            return

    processor = PNCPLacreProcessor(config)

    try:
        await processor.initialize()

        if args.discovery_only:
            logger.info("Running discovery only...")
            tenders, metrics_list = await processor.discover_ongoing_tenders(
                args.start_date, args.end_date, args.states, args.chunk_days
            )
            logger.info(f"\nDiscovery complete: {len(tenders)} lacre tenders found")
            if metrics_list:
                logger.info(f"States processed: {len(metrics_list)}")

        else:
            logger.info("Running complete workflow...")
            await processor.run_complete_workflow(
                args.start_date, args.end_date, args.states, args.chunk_days
            )

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")

    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise

    finally:
        await processor.cleanup()

# Quick test functions
async def test_setup():
    """Test basic setup and configuration"""

    print("=== PNCP Lacre Processor Test ===")

    # Test configuration
    print(f"Default config states: {len(DEFAULT_LACRE_CONFIG.enabled_states)}")
    print(f"Modalities: {DEFAULT_LACRE_CONFIG.allowed_modalities}")
    print(f"Only ongoing: {DEFAULT_LACRE_CONFIG.only_ongoing_tenders}")

    # Test classifier
    classifier = LacreTenderClassifier()

    test_item = "LACRE DE SEGURANÇA PARA HIDRÔMETRO"
    sample_tender = {
        'title': test_item,
        'description': 'Lacre inviolável numerado em polipropileno',
        'items_summary': ''
    }

    is_relevant, score, keywords, reasoning = classifier.assess_lacre_relevance(
        sample_tender['title'], sample_tender['description']
    )

    print(f"\nClassification test: '{test_item}'")
    print(f"Relevant: {is_relevant} (score: {score:.1f}%)")
    print(f"Keywords: {keywords[:5]}")

    print("\nTest completed")

async def run_demo():
    """Run a demonstration with recent data"""

    print("=== PNCP Lacre Demo Mode ===")

    # Use recent dates for ongoing tenders
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Last 30 days for ongoing

    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Test with just SP (São Paulo)
    demo_states = ['SP']

    config = LacreProcessingConfig(
        enabled_states=demo_states,
        min_tender_value=5000.0,
        min_match_score=20.0,
        only_ongoing_tenders=True
    )

    processor = PNCPLacreProcessor(config)

    try:
        print(f"Demo would process {len(demo_states)} states from {start_date_str} to {end_date_str}")
        print("Requires proper PNCP credentials and Cloud SQL setup")

    except Exception as e:
        print(f"Demo setup failed (expected): {e}")

if __name__ == "__main__":
    # Check if running in demo mode
    if len(os.sys.argv) == 1 or '--demo' in os.sys.argv:
        asyncio.run(run_demo())
    elif '--test' in os.sys.argv:
        asyncio.run(test_setup())
    else:
        asyncio.run(main())
