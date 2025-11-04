"""
Processed Tenders Tracker
Keeps track of which tenders have been processed to avoid duplicates
"""

import json
import os
import logging
from typing import Set, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TenderIdentifier:
    """Unique identifier for a tender"""
    cnpj: str
    ano: int
    sequencial: int
    state_code: str = ""

    def __post_init__(self):
        # Normalize CNPJ (remove dots, slashes, dashes)
        self.cnpj = self.cnpj.replace(".", "").replace("/", "").replace("-", "")

    @property
    def unique_key(self) -> str:
        """Generate unique key for this tender"""
        return f"{self.cnpj}_{self.ano}_{self.sequencial}"

    def __hash__(self):
        return hash(self.unique_key)

    def __eq__(self, other):
        if isinstance(other, TenderIdentifier):
            return self.unique_key == other.unique_key
        return False

@dataclass
class ProcessedTenderRecord:
    """Record of a processed tender with metadata"""
    tender_id: TenderIdentifier
    processed_date: str
    homologated_value: float
    items_count: int
    matches_found: int
    processing_status: str = "completed"  # completed, failed, partial

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedTenderRecord':
        """Create from dictionary (for JSON loading)"""
        tender_id_data = data['tender_id']
        tender_id = TenderIdentifier(
            cnpj=tender_id_data['cnpj'],
            ano=tender_id_data['ano'],
            sequencial=tender_id_data['sequencial'],
            state_code=tender_id_data.get('state_code', '')
        )

        return cls(
            tender_id=tender_id,
            processed_date=data['processed_date'],
            homologated_value=data['homologated_value'],
            items_count=data['items_count'],
            matches_found=data['matches_found'],
            processing_status=data.get('processing_status', 'completed')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'tender_id': asdict(self.tender_id),
            'processed_date': self.processed_date,
            'homologated_value': self.homologated_value,
            'items_count': self.items_count,
            'matches_found': self.matches_found,
            'processing_status': self.processing_status
        }

class ProcessedTendersTracker:
    """Manages tracking of processed tenders"""

    def __init__(self, storage_file: str = "processed_tenders.json"):
        self.storage_file = storage_file
        self.processed_tenders: Dict[str, ProcessedTenderRecord] = {}
        self.load_from_file()

    def load_from_file(self) -> bool:
        """Load processed tenders from JSON file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)

                # Convert from old format if needed
                if isinstance(data, list):
                    # Old format was just a list of unique keys
                    logger.info("Converting old format processed tenders file...")
                    for key in data:
                        # Create minimal record for old entries
                        parts = key.split('_')
                        if len(parts) >= 3:
                            tender_id = TenderIdentifier(
                                cnpj=parts[0],
                                ano=int(parts[1]),
                                sequencial=int(parts[2])
                            )
                            record = ProcessedTenderRecord(
                                tender_id=tender_id,
                                processed_date="unknown",
                                homologated_value=0.0,
                                items_count=0,
                                matches_found=0,
                                processing_status="legacy"
                            )
                            self.processed_tenders[key] = record
                else:
                    # New format with full records
                    for key, record_data in data.items():
                        try:
                            record = ProcessedTenderRecord.from_dict(record_data)
                            self.processed_tenders[key] = record
                        except Exception as e:
                            logger.warning(f"Skipping invalid record {key}: {e}")

                logger.info(f"Loaded {len(self.processed_tenders)} processed tenders from {self.storage_file}")
                return True
            else:
                logger.info(f"No existing processed tenders file found. Starting fresh.")
                return False

        except Exception as e:
            logger.error(f"Failed to load processed tenders: {e}")
            logger.info("Starting with empty processed tenders list")
            self.processed_tenders = {}
            return False

    def save_to_file(self) -> bool:
        """Save processed tenders to JSON file"""
        try:
            # Convert to serializable format
            data = {}
            for key, record in self.processed_tenders.items():
                data[key] = record.to_dict()

            # Create backup of existing file
            if os.path.exists(self.storage_file):
                backup_file = f"{self.storage_file}.backup"
                os.rename(self.storage_file, backup_file)

            # Save new data
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(self.processed_tenders)} processed tenders to {self.storage_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save processed tenders: {e}")
            return False

    def is_processed(self, tender_id: TenderIdentifier) -> bool:
        """Check if tender has been processed"""
        return tender_id.unique_key in self.processed_tenders

    def mark_as_processed(self, tender_id: TenderIdentifier,
                         homologated_value: float = 0.0,
                         items_count: int = 0,
                         matches_found: int = 0,
                         status: str = "completed") -> None:
        """Mark tender as processed"""
        record = ProcessedTenderRecord(
            tender_id=tender_id,
            processed_date=datetime.now().isoformat(),
            homologated_value=homologated_value,
            items_count=items_count,
            matches_found=matches_found,
            processing_status=status
        )

        self.processed_tenders[tender_id.unique_key] = record
        logger.info(f"Marked tender as processed: {tender_id.unique_key}")

    def filter_unprocessed_tenders(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out already processed tenders from a list"""
        unprocessed = []
        processed_count = 0

        for tender in tenders:
            try:
                tender_id = TenderIdentifier(
                    cnpj=tender.get('cnpj', ''),
                    ano=tender.get('ano', 0),
                    sequencial=tender.get('sequencial', 0),
                    state_code=tender.get('state_code', '')
                )

                if not self.is_processed(tender_id):
                    unprocessed.append(tender)
                else:
                    processed_count += 1

            except Exception as e:
                logger.warning(f"Could not create tender ID for tender: {e}")
                # Include in unprocessed if we can't identify it
                unprocessed.append(tender)

        if processed_count > 0:
            logger.info(f"Filtered out {processed_count} already processed tenders")
            logger.info(f"Found {len(unprocessed)} unprocessed tenders")

        return unprocessed

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed tenders"""
        if not self.processed_tenders:
            return {
                "total_processed": 0,
                "by_status": {},
                "total_value": 0.0,
                "total_items": 0,
                "total_matches": 0
            }

        stats = {
            "total_processed": len(self.processed_tenders),
            "by_status": {},
            "total_value": 0.0,
            "total_items": 0,
            "total_matches": 0,
            "by_state": {},
            "processing_dates": []
        }

        for record in self.processed_tenders.values():
            # Status counts
            status = record.processing_status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Totals
            stats["total_value"] += record.homologated_value
            stats["total_items"] += record.items_count
            stats["total_matches"] += record.matches_found

            # By state
            state = record.tender_id.state_code or "unknown"
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1

            # Dates
            if record.processed_date != "unknown":
                stats["processing_dates"].append(record.processed_date)

        return stats

    def print_stats(self):
        """Print processing statistics"""
        stats = self.get_processing_stats()

        print("\n📊 PROCESSED TENDERS STATISTICS")
        print("=" * 50)
        print(f"Total Processed: {stats['total_processed']:,}")

        if stats['by_status']:
            print("\nBy Status:")
            for status, count in stats['by_status'].items():
                print(f"  {status}: {count:,}")

        if stats['by_state']:
            print(f"\nTotal Value: R${stats['total_value']:,.2f}")
            print(f"Total Items: {stats['total_items']:,}")
            print(f"Total Matches: {stats['total_matches']:,}")

            print("\nBy State:")
            sorted_states = sorted(stats['by_state'].items(), key=lambda x: x[1], reverse=True)
            for state, count in sorted_states[:10]:  # Top 10 states
                print(f"  {state}: {count:,}")

        print()

    def cleanup_old_records(self, days_to_keep: int = 365):
        """Remove old processed records to keep file size manageable"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        original_count = len(self.processed_tenders)

        # Keep records that are recent or have unknown dates (legacy)
        filtered_records = {}
        for key, record in self.processed_tenders.items():
            if record.processed_date == "unknown" or record.processing_status == "legacy":
                # Keep legacy records
                filtered_records[key] = record
            else:
                try:
                    processed_date = datetime.fromisoformat(record.processed_date.replace('Z', '+00:00'))
                    if processed_date >= cutoff_date:
                        filtered_records[key] = record
                except:
                    # Keep if we can't parse date
                    filtered_records[key] = record

        self.processed_tenders = filtered_records
        removed_count = original_count - len(self.processed_tenders)

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old processed tender records")
            self.save_to_file()

# Global instance for easy access
_tracker_instance = None

def get_processed_tenders_tracker() -> ProcessedTendersTracker:
    """Get global processed tenders tracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProcessedTendersTracker()
    return _tracker_instance

def test_tracker():
    """Test the tracker functionality"""
    print("🧪 Testing Processed Tenders Tracker...")

    tracker = ProcessedTendersTracker("test_processed_tenders.json")

    # Test tender IDs
    tender1 = TenderIdentifier("12345678000190", 2024, 1, "SP")
    tender2 = TenderIdentifier("98765432000180", 2024, 2, "RJ")
    tender3 = TenderIdentifier("12.345.678/0001-90", 2024, 3, "MG")  # Same as tender1 (normalized)

    # Test processing
    print(f"Tender 1 processed: {tracker.is_processed(tender1)}")

    tracker.mark_as_processed(tender1, 100000.0, 25, 8)
    tracker.mark_as_processed(tender2, 50000.0, 12, 3)

    print(f"Tender 1 processed: {tracker.is_processed(tender1)}")
    print(f"Tender 2 processed: {tracker.is_processed(tender2)}")
    print(f"Tender 3 processed (normalized): {tracker.is_processed(tender3)}")

    # Test stats
    tracker.print_stats()

    # Clean up test file
    if os.path.exists("test_processed_tenders.json"):
        os.remove("test_processed_tenders.json")

    print("✅ Tracker test completed!")

if __name__ == "__main__":
    test_tracker()