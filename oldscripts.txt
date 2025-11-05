#!/usr/bin/env python3
"""
PNCP Medical Data Processing - Main Orchestration Script
Coordinates the complete workflow from tender discovery to product matching
"""

import asyncio
import logging
import argparse
import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from config import ProcessingConfig, BRAZILIAN_STATES
from database import CloudSQLManager, DatabaseOperations, create_db_manager_from_env
from pncp_api import PNCPAPIClient
from classifier import TenderClassifier
from optimized_discovery import OptimizedTenderDiscovery, DiscoveryMetrics
from fetch_and_save_items import fetch_and_save_items
from match_tender_items import match_tender_items

# Configure logging (will be set up properly in main())
logger = logging.getLogger(__name__)


def setup_logging(run_mode: str = "full"):
    """Setup logging with timestamped file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'logs/pncp_run_{run_mode}_{timestamp}.log'

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ],
        force=True  # Override any existing config
    )

    logger.info("=" * 70)
    logger.info(f"📝 Log file: {log_filename}")
    logger.info("=" * 70)

    return log_filename


class PNCPMedicalProcessor:
    """Main orchestration class for PNCP medical data processing"""

    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.db_manager: Optional[CloudSQLManager] = None
        self.db_ops: Optional[DatabaseOperations] = None
        self.api_client: Optional[PNCPAPIClient] = None
        self.classifier: Optional[TenderClassifier] = None
        self.discovery_engine: Optional[OptimizedTenderDiscovery] = None

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing PNCP Medical Processor...")

        try:
            # Initialize database
            self.db_manager = create_db_manager_from_env()
            self.db_ops = DatabaseOperations(self.db_manager)
            logger.info("✅ Database initialized")

            # Initialize API client
            self.api_client = PNCPAPIClient()
            await self.api_client.start_session()
            logger.info("✅ API client initialized")

            # Initialize classifier
            self.classifier = TenderClassifier()
            logger.info("✅ Classifier initialized")

            # Initialize discovery engine
            self.discovery_engine = OptimizedTenderDiscovery(
                self.api_client,
                self.classifier,
                self.db_ops,
                self.config
            )
            logger.info("✅ Discovery engine initialized")

            logger.info("Initialization completed successfully\n")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def discover_tenders(self, start_date: str, end_date: str, states: List[str] = None):
        """Phase 1: Discover tenders"""
        if not self.discovery_engine:
            raise RuntimeError("Discovery engine not initialized")

        states = states or self.config.enabled_states
        logger.info(f"🔍 Phase 1: Tender Discovery")
        logger.info(f"   Date Range: {start_date} to {end_date}")
        logger.info(f"   States: {', '.join(states)}")

        # Process each state individually
        total_tenders = 0
        all_metrics = []

        for state in states:
            logger.info(f"\n   Processing state: {state}")
            tenders, metrics = await self.discovery_engine.discover_medical_tenders_optimized(
                state=state,
                start_date=start_date,
                end_date=end_date
            )
            total_tenders += metrics.stage4_full_processing.tenders_out
            all_metrics.append(metrics)

        logger.info(f"\n✅ Discovery Complete: {total_tenders} medical tenders saved across {len(states)} state(s)")
        return all_metrics[0] if all_metrics else None

    async def fetch_items(self):
        """Phase 2: Fetch items for discovered tenders"""
        logger.info(f"\n📦 Phase 2: Fetching Tender Items")

        # Close current API client session since fetch_and_save_items creates its own
        if self.api_client:
            await self.api_client.close_session()
            self.api_client = None

        # Call the standalone function
        await fetch_and_save_items()

        logger.info(f"✅ Item fetching complete")

    async def match_products(self):
        """Phase 3: Match tender items with Fernandes products"""
        logger.info(f"\n🔍 Phase 3: Product Matching")

        # Call the standalone function
        await match_tender_items()

        logger.info(f"✅ Product matching complete")

    async def run_complete_workflow(self, start_date: str, end_date: str, states: List[str] = None, enable_matching: bool = False):
        """Run complete workflow: discovery → items → (optional) matching

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            states: List of state codes to process
            enable_matching: If True, run Phase 3 (product matching). Default False.
        """

        logger.info("\n" + "=" * 70)
        logger.info("🚀 PNCP MEDICAL DATA PROCESSING - COMPLETE WORKFLOW")
        logger.info("=" * 70)
        logger.info(f"📅 Date Range: {start_date} to {end_date}")
        logger.info(f"🗺️  States: {', '.join(states) if states else 'ALL'}")
        if enable_matching:
            logger.info("🔍 Product Matching: ENABLED")
        else:
            logger.info("🔍 Product Matching: SKIPPED (use --match to enable)")
        logger.info("=" * 70)

        workflow_start = datetime.now()

        try:
            # Initialize
            await self.initialize()

            # Phase 1: Discovery
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 1: TENDER DISCOVERY")
            logger.info("=" * 70)
            phase1_start = datetime.now()

            discovery_metrics = await self.discover_tenders(start_date, end_date, states)

            phase1_time = (datetime.now() - phase1_start).total_seconds()
            logger.info(f"⏱️  Phase 1 completed in {phase1_time:.1f}s")

            if not discovery_metrics or discovery_metrics.stage4_full_processing.tenders_out == 0:
                logger.warning("\n⚠️  No medical tenders found. Workflow stopped.")
                return

            # Phase 2: Fetch Items
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 2: FETCHING TENDER ITEMS")
            logger.info("=" * 70)
            phase2_start = datetime.now()

            await self.fetch_items()

            phase2_time = (datetime.now() - phase2_start).total_seconds()
            logger.info(f"⏱️  Phase 2 completed in {phase2_time:.1f}s")

            # Phase 3: Match Products (Optional)
            phase3_time = 0
            if enable_matching:
                logger.info("\n" + "=" * 70)
                logger.info("PHASE 3: PRODUCT MATCHING")
                logger.info("=" * 70)
                phase3_start = datetime.now()

                await self.match_products()

                phase3_time = (datetime.now() - phase3_start).total_seconds()
                logger.info(f"⏱️  Phase 3 completed in {phase3_time:.1f}s")
            else:
                logger.info("\n" + "=" * 70)
                logger.info("PHASE 3: PRODUCT MATCHING - SKIPPED")
                logger.info("=" * 70)
                logger.info("💡 Tip: Use Looker Studio to explore items, then run ai_matching/ for targeted matches")

            # Summary
            total_time = (datetime.now() - workflow_start).total_seconds()
            logger.info("\n" + "=" * 70)
            logger.info("✅ WORKFLOW COMPLETE - SUMMARY")
            logger.info("=" * 70)
            logger.info(f"Phase 1 (Discovery): {phase1_time:.1f}s")
            logger.info(f"Phase 2 (Items):     {phase2_time:.1f}s")
            if enable_matching:
                logger.info(f"Phase 3 (Matching):  {phase3_time:.1f}s")
            else:
                logger.info(f"Phase 3 (Matching):  SKIPPED")
            logger.info(f"Total Time:          {total_time:.1f}s")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"\n❌ Workflow failed: {e}", exc_info=True)
            raise

    async def cleanup(self):
        """Clean up resources"""
        logger.info("\nCleaning up resources...")

        if self.api_client:
            await self.api_client.close_session()

        if self.db_manager:
            await self.db_manager.close()

        logger.info("✅ Cleanup completed")


def get_interactive_input():
    """Get user input interactively"""

    print("\n" + "=" * 70)
    print("🚀 PNCP MEDICAL DATA PROCESSOR - Interactive Mode")
    print("=" * 70)

    # Get start date
    while True:
        start_date = input("\n📅 Enter START DATE (YYYYMMDD, e.g., 20240101): ").strip()
        if len(start_date) == 8 and start_date.isdigit():
            try:
                datetime.strptime(start_date, '%Y%m%d')
                break
            except ValueError:
                print("❌ Invalid date. Please use format YYYYMMDD")
        else:
            print("❌ Invalid format. Please enter 8 digits (YYYYMMDD)")

    # Get end date
    while True:
        end_date = input("📅 Enter END DATE (YYYYMMDD, e.g., 20240131): ").strip()
        if len(end_date) == 8 and end_date.isdigit():
            try:
                datetime.strptime(end_date, '%Y%m%d')
                if end_date >= start_date:
                    break
                else:
                    print("❌ End date must be after or equal to start date")
            except ValueError:
                print("❌ Invalid date. Please use format YYYYMMDD")
        else:
            print("❌ Invalid format. Please enter 8 digits (YYYYMMDD)")

    # Show available states
    print("\n🗺️  Available Brazilian States:")
    print("-" * 70)
    states_list = list(BRAZILIAN_STATES.items())
    for i in range(0, len(states_list), 3):
        row = states_list[i:i+3]
        print("  " + " | ".join([f"{code}: {name:20}" for code, name in row]))
    print("-" * 70)

    # Get states
    while True:
        states_input = input("\n🌎 Enter STATE CODES (space-separated, e.g., SP RJ MG) or 'ALL': ").strip().upper()

        if states_input == 'ALL':
            states = list(BRAZILIAN_STATES.keys())
            print(f"✅ Selected ALL states ({len(states)} total)")
            break

        states = states_input.split()
        invalid_states = [s for s in states if s not in BRAZILIAN_STATES]

        if invalid_states:
            print(f"❌ Invalid state codes: {', '.join(invalid_states)}")
            print("   Please use valid 2-letter codes (e.g., SP, RJ, MG)")
        elif len(states) == 0:
            print("❌ Please enter at least one state code")
        else:
            state_names = [BRAZILIAN_STATES[s] for s in states]
            print(f"✅ Selected {len(states)} state(s): {', '.join(state_names)}")
            break

    # Confirm
    print("\n" + "=" * 70)
    print("📋 CONFIGURATION SUMMARY")
    print("=" * 70)
    print(f"Start Date: {start_date}")
    print(f"End Date:   {end_date}")
    print(f"States:     {', '.join(states)} ({len(states)} total)")
    print("=" * 70)

    confirm = input("\n▶️  Proceed with this configuration? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("❌ Operation cancelled by user")
        return None, None, None

    return start_date, end_date, states


async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description='PNCP Medical Data Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow
  python main.py --start-date 20240101 --end-date 20240131 --states SP RJ

  # Discovery only
  python main.py --start-date 20240101 --end-date 20240131 --discovery-only

  # Process items for existing tenders
  python main.py --items-only

  # Match products only
  python main.py --matching-only

  # Export to Notion only
  python main.py --export-only
        """
    )

    parser.add_argument('--start-date', help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', help='End date (YYYYMMDD)')
    parser.add_argument('--states', nargs='*', help='State codes (e.g., SP RJ MG)')
    parser.add_argument('--match', action='store_true', help='Enable Phase 3 product matching (default: skip)')
    parser.add_argument('--discovery-only', action='store_true', help='Only run discovery phase')
    parser.add_argument('--items-only', action='store_true', help='Only fetch items (skip discovery)')
    parser.add_argument('--matching-only', action='store_true', help='Only match products (skip discovery/items)')
    parser.add_argument('--export-only', action='store_true', help='Only export to Notion')

    args = parser.parse_args()

    # Check if running in interactive mode (no arguments provided)
    phases = [args.discovery_only, args.items_only, args.matching_only, args.export_only]
    interactive_mode = not any(phases) and not args.start_date and not args.end_date

    # Validate phase arguments
    if sum(phases) > 1:
        logger.error("❌ Please specify only one phase flag")
        return

    # Interactive mode for full workflow
    if interactive_mode:
        start_date, end_date, states = get_interactive_input()
        if not start_date:  # User cancelled
            return
        args.start_date = start_date
        args.end_date = end_date
        args.states = states

    # Validate required arguments for specific modes
    if not any(phases) and (not args.start_date or not args.end_date):
        logger.error("❌ Full workflow requires --start-date and --end-date")
        return

    if args.discovery_only and (not args.start_date or not args.end_date):
        logger.error("❌ Discovery requires --start-date and --end-date")
        return

    # Determine run mode for logging
    if args.discovery_only:
        run_mode = "discovery"
    elif args.items_only:
        run_mode = "items"
    elif args.matching_only:
        run_mode = "matching"
    elif args.export_only:
        run_mode = "export"
    else:
        run_mode = "full"

    # Setup logging
    log_file = setup_logging(run_mode)

    # Create processor
    config = ProcessingConfig()
    processor = PNCPMedicalProcessor(config)

    try:
        if args.discovery_only:
            await processor.initialize()
            await processor.discover_tenders(args.start_date, args.end_date, args.states)

        elif args.items_only:
            await processor.initialize()
            await processor.fetch_items()

        elif args.matching_only:
            await processor.initialize()
            await processor.match_products()

        elif args.export_only:
            await processor.initialize()
            await processor.export_to_notion_db()

        else:
            # Full workflow
            await processor.run_complete_workflow(args.start_date, args.end_date, args.states, enable_matching=args.match)

        logger.info(f"\n📝 Full log saved to: {log_file}")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Process interrupted by user")

    except Exception as e:
        logger.error(f"❌ Process failed: {e}", exc_info=True)
        raise

    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
