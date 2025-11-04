"""
Processed Lacre Tenders Tracker
Tracks which lacre tenders have been processed to avoid duplicates
Separate from medical tender tracker to maintain data integrity
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class LacreTenderIdentifier:
    """Unique identifier for a lacre tender"""
    cnpj: str
    ano: int
    sequencial: int
    state_code: str

    def to_key(self) -> str:
        """Generate unique key for this tender"""
        return f"{self.cnpj}_{self.ano}_{self.sequencial}_{self.state_code}"

    @classmethod
    def from_tender(cls, tender: Dict) -> 'LacreTenderIdentifier':
        """Create identifier from tender data"""
        return cls(
            cnpj=tender.get('cnpj', ''),
            ano=tender.get('ano', 0),
            sequencial=tender.get('sequencial', 0),
            state_code=tender.get('state_code', '')
        )

@dataclass
class ProcessedLacreTenderRecord:
    """Record of a processed lacre tender"""
    tender_id: LacreTenderIdentifier
    processed_date: str
    homologated_value: float
    estimated_value: float
    items_count: int
    matches_found: int
    status: str  # 'completed', 'no_items', 'error', 'ongoing'
    is_ongoing: bool  # Whether tender was ongoing at time of processing

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            'cnpj': self.tender_id.cnpj,
            'ano': self.tender_id.ano,
            'sequencial': self.tender_id.sequencial,
            'state_code': self.tender_id.state_code,
            'processed_date': self.processed_date,
            'homologated_value': self.homologated_value,
            'estimated_value': self.estimated_value,
            'items_count': self.items_count,
            'matches_found': self.matches_found,
            'status': self.status,
            'is_ongoing': self.is_ongoing
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProcessedLacreTenderRecord':
        """Create from dictionary"""
        tender_id = LacreTenderIdentifier(
            cnpj=data['cnpj'],
            ano=data['ano'],
            sequencial=data['sequencial'],
            state_code=data['state_code']
        )
        return cls(
            tender_id=tender_id,
            processed_date=data['processed_date'],
            homologated_value=data.get('homologated_value', 0.0),
            estimated_value=data.get('estimated_value', 0.0),
            items_count=data.get('items_count', 0),
            matches_found=data.get('matches_found', 0),
            status=data.get('status', 'completed'),
            is_ongoing=data.get('is_ongoing', False)
        )

class ProcessedLacreTendersTracker:
    """Tracks processed lacre tenders to prevent duplicate processing"""

    def __init__(self, filepath: str = 'processed_lacre_tenders.json'):
        self.filepath = filepath
        self.processed_tenders: Dict[str, ProcessedLacreTenderRecord] = {}
        self.load_from_file()

    def load_from_file(self):
        """Load processed tenders from JSON file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)

                self.processed_tenders = {
                    record['cnpj'] + '_' + str(record['ano']) + '_' + str(record['sequencial']) + '_' + record['state_code']:
                    ProcessedLacreTenderRecord.from_dict(record)
                    for record in data.get('tenders', [])
                }

                logger.info(f"Loaded {len(self.processed_tenders)} processed lacre tender records from {self.filepath}")

            except Exception as e:
                logger.error(f"Error loading processed lacre tenders: {e}")
                self.processed_tenders = {}
        else:
            logger.info(f"No existing processed lacre tenders file found at {self.filepath}")
            self.processed_tenders = {}

    def save_to_file(self):
        """Save processed tenders to JSON file"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.processed_tenders),
                'tenders': [record.to_dict() for record in self.processed_tenders.values()]
            }

            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.processed_tenders)} processed lacre tender records to {self.filepath}")

        except Exception as e:
            logger.error(f"Error saving processed lacre tenders: {e}")

    def is_processed(self, tender_id: LacreTenderIdentifier) -> bool:
        """Check if tender has already been processed"""
        key = tender_id.to_key()
        return key in self.processed_tenders

    def mark_as_processed(self, tender_id: LacreTenderIdentifier,
                         homologated_value: float = 0.0,
                         estimated_value: float = 0.0,
                         items_count: int = 0,
                         matches_found: int = 0,
                         status: str = 'completed',
                         is_ongoing: bool = False):
        """Mark a tender as processed"""
        record = ProcessedLacreTenderRecord(
            tender_id=tender_id,
            processed_date=datetime.now().isoformat(),
            homologated_value=homologated_value,
            estimated_value=estimated_value,
            items_count=items_count,
            matches_found=matches_found,
            status=status,
            is_ongoing=is_ongoing
        )

        key = tender_id.to_key()
        self.processed_tenders[key] = record

        logger.debug(f"Marked lacre tender as processed: {key}")

    def filter_unprocessed_tenders(self, tenders: List[Dict]) -> List[Dict]:
        """Filter list to include only unprocessed tenders"""
        unprocessed = []

        for tender in tenders:
            try:
                tender_id = LacreTenderIdentifier.from_tender(tender)
                if not self.is_processed(tender_id):
                    unprocessed.append(tender)
                else:
                    logger.debug(f"Skipping already processed tender: {tender_id.to_key()}")
            except Exception as e:
                logger.warning(f"Error checking tender: {e}")
                # Include tender if we can't determine status
                unprocessed.append(tender)

        logger.info(f"Filtered {len(unprocessed)} unprocessed tenders from {len(tenders)} total")
        return unprocessed

    def get_processed_count(self) -> int:
        """Get total number of processed tenders"""
        return len(self.processed_tenders)

    def get_stats(self) -> Dict:
        """Get statistics about processed tenders"""
        stats = {
            'total_processed': len(self.processed_tenders),
            'total_value_homologated': 0.0,
            'total_value_estimated': 0.0,
            'total_items': 0,
            'total_matches': 0,
            'by_state': {},
            'by_status': {},
            'ongoing_count': 0
        }

        for record in self.processed_tenders.values():
            stats['total_value_homologated'] += record.homologated_value
            stats['total_value_estimated'] += record.estimated_value
            stats['total_items'] += record.items_count
            stats['total_matches'] += record.matches_found

            # By state
            state = record.tender_id.state_code
            if state not in stats['by_state']:
                stats['by_state'][state] = 0
            stats['by_state'][state] += 1

            # By status
            status = record.status
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += 1

            # Ongoing count
            if record.is_ongoing:
                stats['ongoing_count'] += 1

        return stats

    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_stats()

        print("\n=== PROCESSED LACRE TENDERS STATISTICS ===")
        print(f"Total Processed: {stats['total_processed']:,}")
        print(f"Estimated Value: R${stats['total_value_estimated']:,.2f}")
        print(f"Homologated Value: R${stats['total_value_homologated']:,.2f}")
        print(f"Total Items: {stats['total_items']:,}")
        print(f"Total Matches: {stats['total_matches']:,}")
        print(f"Ongoing Tenders: {stats['ongoing_count']:,}")

        if stats['by_state']:
            print("\n--- By State ---")
            for state, count in sorted(stats['by_state'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {state}: {count:,}")

        if stats['by_status']:
            print("\n--- By Status ---")
            for status, count in sorted(stats['by_status'].items()):
                print(f"  {status}: {count:,}")

    def clear_all(self):
        """Clear all processed tender records (use with caution!)"""
        self.processed_tenders = {}
        logger.warning("Cleared all processed lacre tender records")

    def remove_tender(self, tender_id: LacreTenderIdentifier):
        """Remove a specific tender from processed list"""
        key = tender_id.to_key()
        if key in self.processed_tenders:
            del self.processed_tenders[key]
            logger.info(f"Removed tender from processed list: {key}")
        else:
            logger.warning(f"Tender not found in processed list: {key}")

# Global instance
_lacre_tracker_instance = None

def get_processed_lacre_tenders_tracker(filepath: str = 'processed_lacre_tenders.json') -> ProcessedLacreTendersTracker:
    """Get global tracker instance"""
    global _lacre_tracker_instance
    if _lacre_tracker_instance is None:
        _lacre_tracker_instance = ProcessedLacreTendersTracker(filepath)
    return _lacre_tracker_instance

# Test/demo function
def demo_tracker():
    """Demonstrate tracker functionality"""
    print("=== Lacre Tender Tracker Demo ===\n")

    tracker = ProcessedLacreTendersTracker('test_processed_lacre_tenders.json')

    # Add some sample processed tenders
    sample_tenders = [
        LacreTenderIdentifier('12.345.678/0001-90', 2024, 1, 'SP'),
        LacreTenderIdentifier('98.765.432/0001-10', 2024, 5, 'RJ'),
        LacreTenderIdentifier('11.222.333/0001-44', 2024, 10, 'MG'),
    ]

    for tender_id in sample_tenders:
        tracker.mark_as_processed(
            tender_id,
            estimated_value=50000.0,
            items_count=10,
            matches_found=5,
            status='completed',
            is_ongoing=True
        )

    # Save and print stats
    tracker.save_to_file()
    tracker.print_stats()

    # Test filtering
    print("\n--- Testing Filter ---")
    test_tenders = [
        {'cnpj': '12.345.678/0001-90', 'ano': 2024, 'sequencial': 1, 'state_code': 'SP'},  # Already processed
        {'cnpj': '99.888.777/0001-66', 'ano': 2024, 'sequencial': 20, 'state_code': 'BA'},  # New
    ]

    unprocessed = tracker.filter_unprocessed_tenders(test_tenders)
    print(f"Filtered to {len(unprocessed)} unprocessed tenders from {len(test_tenders)} total")

    # Cleanup test file
    if os.path.exists('test_processed_lacre_tenders.json'):
        os.remove('test_processed_lacre_tenders.json')
        print("\nTest file cleaned up")

if __name__ == "__main__":
    demo_tracker()
