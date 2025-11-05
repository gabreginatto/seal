#!/usr/bin/env python3
"""
Test to get ALL items from Cosmópolis tender (with pagination if needed)
"""

import asyncio
import sys
import os
import json

# Add parent directory and src directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'src'))

from src.pncp_api import PNCPAPIClient

async def test_all_items():
    """Get ALL items with pagination"""

    cnpj = '44730331000152'
    year = 2025
    seq = 105

    print("="*70)
    print(f"Fetching ALL items for Cosmópolis tender {cnpj}/{year}/{seq}")
    print("="*70)

    api = PNCPAPIClient()
    await api.start_session()

    try:
        # Try with pagination
        all_items = []
        page = 1

        while True:
            print(f"\nPage {page}:")
            url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{seq}/itens"

            # Try with page param
            status, resp = await api._make_request('GET', url, params={'pagina': page, 'tamanhoPagina': 100})
            print(f"  Status: {status}")

            if status == 200:
                if isinstance(resp, list):
                    items = resp
                else:
                    items = resp.get('data', [])

                if not items:
                    print(f"  No items on this page - stopping")
                    break

                print(f"  Found {len(items)} items")
                all_items.extend(items)

                # Check if there's pagination info
                if isinstance(resp, dict):
                    has_more = resp.get('paginasRestantes', 0) > 0
                    if not has_more:
                        break

                page += 1

                # Safety limit
                if page > 10:
                    print("  Reached page limit (10)")
                    break
            else:
                print(f"  Error: {resp}")
                break

        print(f"\n{'='*70}")
        print(f"Total items across all pages: {len(all_items)}")
        print(f"{'='*70}")

        # Show all item descriptions
        print("\nAll item descriptions:")
        for item in all_items:
            num = item.get('numeroItem')
            desc = item.get('descricao', 'N/A')
            qty = item.get('quantidade', 0)
            print(f"  {num:3d}. {desc} (Qty: {qty})")

        # Find lacre items
        print(f"\n{'='*70}")
        lacre_items = [item for item in all_items if 'lacre' in item.get('descricao', '').lower()]
        print(f"Lacre items: {len(lacre_items)}")
        print(f"{'='*70}")

        if lacre_items:
            print("\nLACRE ITEMS FOUND:")
            for item in lacre_items:
                num = item.get('numeroItem')
                desc = item.get('descricao')
                qty = item.get('quantidade')
                unit_val = item.get('valorUnitarioEstimado')
                total_val = item.get('valorTotal')
                print(f"\nItem {num}:")
                print(f"  Description: {desc}")
                print(f"  Quantity: {qty}")
                print(f"  Unit Value: R$ {unit_val:,.2f}")
                print(f"  Total Value: R$ {total_val:,.2f}")
        else:
            print("\n⚠️  NO LACRE ITEMS FOUND!")
            print("This is unexpected based on the screenshot showing items 26 and 27 with lacre.")
            print("Possible reasons:")
            print("  1. Items might be on a page we're not reaching")
            print("  2. API might not return all items (only first 10?)")
            print("  3. Different endpoint needed for complete item list")

    finally:
        await api.close_session()

if __name__ == "__main__":
    asyncio.run(test_all_items())
