#!/usr/bin/env python3
"""
View Processed Tenders Statistics
Shows what tenders have been processed and statistics
"""

import argparse
from processed_tenders_tracker import get_processed_tenders_tracker
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='View processed tenders statistics')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old records (1+ year)')
    parser.add_argument('--reset', action='store_true', help='Reset all processed records (DANGER!)')

    args = parser.parse_args()

    print("📊 PNCP Processed Tenders Tracker")
    print("=" * 50)

    tracker = get_processed_tenders_tracker()

    if args.reset:
        confirm = input("⚠️  Are you sure you want to reset ALL processed records? (type 'yes'): ")
        if confirm.lower() == 'yes':
            tracker.processed_tenders.clear()
            tracker.save_to_file()
            print("✅ All processed records have been reset")
            return
        else:
            print("❌ Reset cancelled")
            return

    if args.cleanup:
        print("🧹 Cleaning up old records...")
        tracker.cleanup_old_records(days_to_keep=365)
        print("✅ Cleanup completed")

    # Show current statistics
    tracker.print_stats()

    # Show recent processing activity
    stats = tracker.get_processing_stats()
    if stats['processing_dates']:
        # Sort dates and show recent activity
        recent_dates = sorted(stats['processing_dates'])[-10:]
        if recent_dates:
            print("🕒 Recent Processing Activity:")
            for date_str in recent_dates:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    print(f"  {date_obj.strftime('%Y-%m-%d %H:%M')}")
                except:
                    print(f"  {date_str}")
            print()

    # Show sample processed tenders
    if tracker.processed_tenders:
        print("📋 Sample Processed Tenders:")
        sample_size = min(5, len(tracker.processed_tenders))
        for i, (key, record) in enumerate(list(tracker.processed_tenders.items())[:sample_size]):
            print(f"  {i+1}. {key}")
            print(f"     Value: R${record.homologated_value:,.2f}")
            print(f"     Items: {record.items_count}, Matches: {record.matches_found}")
            print(f"     Status: {record.processing_status}")
            print()

    print(f"💾 Storage: processed_tenders.json")
    print(f"🎯 Next run will skip {len(tracker.processed_tenders)} already processed tenders")

if __name__ == "__main__":
    main()