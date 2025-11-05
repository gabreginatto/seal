#!/usr/bin/env python3
"""
Quick test to find specific lacre tender from Cosmópolis
CNPJ: 44730331000152-1-000105/2025
"""

import asyncio
import sys
import os

# Add both lacre and medical to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'lacre'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'medical'))
sys.path.insert(0, os.path.dirname(__file__))

from pncp_api import PNCPAPIClient

async def test_specific_tender():
    """Test fetching specific tender and its items"""

    # Tender details
    cnpj = "44730331000152"
    year = 2025
    sequential = 105

    print("="*70)
    print("Testing Specific Lacre Tender from Cosmópolis")
    print("="*70)
    print(f"CNPJ: {cnpj}")
    print(f"Year: {year}")
    print(f"Sequential: {sequential}")
    print()

    api_client = PNCPAPIClient()
    await api_client.start_session()

    try:
        # First, try to get tender details
        print("1. Fetching tender details...")
        # We'll search by date range when it was published
        status, response = await api_client.get_tenders_by_publication_date(
            start_date="20250812",
            end_date="20250812",
            modality_code=6,  # Pregão Eletrônico
            state="SP",
            page=1,
            page_size=50
        )

        print(f"   Status: {status}")
        if status == 200:
            tenders = response.get('data', [])
            print(f"   Found {len(tenders)} tenders on 2025-08-12")

            # Find our specific tender
            target_tender = None
            for tender in tenders:
                tender_cnpj = tender.get('orgaoEntidade', {}).get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
                tender_seq = tender.get('sequencialCompra')
                if tender_cnpj == cnpj and tender_seq == sequential:
                    target_tender = tender
                    break

            if target_tender:
                print(f"   ✅ Found target tender!")
                print(f"   Title: {target_tender.get('objetoCompra', 'N/A')}")
                print(f"   Status: {target_tender.get('situacaoCompra', 'N/A')}")
                print(f"   Value: R$ {target_tender.get('valorTotalEstimado', 0):,.2f}")
                print()
            else:
                print(f"   ❌ Target tender NOT found in results")
                print()

        # Now fetch items directly
        print("2. Fetching ALL items for this tender...")
        status, response = await api_client.get_tender_items(cnpj, year, sequential)

        print(f"   Status: {status}")
        if status == 200:
            items = response.get('data', [])
            print(f"   ✅ Found {len(items)} items")
            print()

            # Show lacre items
            print("3. Analyzing items for 'lacre' keyword:")
            print("-"*70)
            lacre_count = 0
            for item in items:
                item_num = item.get('numeroItem', 'N/A')
                description = item.get('descricao', '') or item.get('descricaoItem', '')
                quantity = item.get('quantidade', 0)
                unit_value = item.get('valorUnitario', 0)
                total_value = item.get('valorTotal', quantity * unit_value)

                if 'lacre' in description.lower():
                    lacre_count += 1
                    print(f"   Item {item_num}: {description[:60]}")
                    print(f"            Qty: {quantity}, Unit: R$ {unit_value:.2f}, Total: R$ {total_value:,.2f}")
                    print()

            print(f"   Found {lacre_count} items with 'lacre' out of {len(items)} total items")
            print()

            # Test keyword matching
            print("4. Testing keyword detection:")
            from config_lacre import LACRE_KEYWORDS

            matched_items = 0
            for item in items:
                description = (item.get('descricao', '') or item.get('descricaoItem', '')).lower()
                if any(keyword in description for keyword in LACRE_KEYWORDS):
                    matched_items += 1

            print(f"   Items matching LACRE_KEYWORDS: {matched_items}/{len(items)}")
            print()

        elif status == 404:
            print(f"   ❌ Items not found (404) - tender may not have published items yet")
            print()
        else:
            print(f"   ❌ Error: {response}")
            print()

    finally:
        await api_client.close_session()

    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_specific_tender())
