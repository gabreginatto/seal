#!/usr/bin/env python3
"""
Test fetching Cosmópolis tender directly from PNCP API
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'medical'))
sys.path.insert(0, os.path.dirname(__file__))

from pncp_api import PNCPAPIClient

async def test():
    api = PNCPAPIClient()
    await api.start_session()

    try:
        # Search for Cosmópolis tender with pagination
        print("Searching for Cosmópolis tender (CNPJ: 44730331000152, Year: 2025, Sequential: 105)...")
        print("Date: 2025-08-12, Modality: 6 (Pregão Eletrônico)\n")

        # We know the exact date, so search Aug 12 with pagination
        start_date = "20250812"
        end_date = "20250812"
        page = 1
        found = False
        total_checked = 0

        while not found and page <= 20:  # Safety limit: check up to 20 pages (1000 tenders)
            print(f"Checking page {page}...")
            status, response = await api.get_tenders_by_publication_date(
                start_date=start_date,
                end_date=end_date,
                modality_code=6,
                state="SP",
                page=page,
                page_size=50
            )

            if status != 200:
                print(f"  Error: Status {status}")
                break

            tenders = response.get('data', [])
            if not tenders:
                print(f"  No more tenders (empty page)")
                break

            total_checked += len(tenders)
            print(f"  Checking {len(tenders)} tenders (total checked: {total_checked})")

            # Look for Cosmópolis
            for t in tenders:
                org = t.get('orgaoEntidade', {})
                org_name = org.get('razaoSocial', '').upper()
                tender_cnpj = org.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
                tender_seq = t.get('sequencialCompra')
                tender_year = t.get('anoCompra')

                # Check by CNPJ and Sequential (most reliable)
                if tender_cnpj == '44730331000152' and tender_seq == 105 and tender_year == 2025:
                    print(f"\n✅ FOUND BY CNPJ/SEQ: {org_name}")
                    print(f"  Title: {t.get('objetoCompra', 'N/A')}")
                    print(f"  CNPJ: {org.get('cnpj')}")
                    print(f"  Sequential: {tender_seq}")
                    print(f"  Year: {tender_year}")
                    print(f"  Control: {t.get('numeroControlePNCP')}")

                    # Fetch ALL items
                    cnpj = '44730331000152'
                    print(f"\n  Fetching ALL items for {cnpj}/{tender_year}/{tender_seq}...")
                    item_status, item_response = await api.get_tender_items(cnpj, tender_year, tender_seq)
                    print(f"  Items status: {item_status}")

                    if item_status == 200:
                        items = item_response.get('data', [])
                        print(f"  ✅ Found {len(items)} total items\n")

                        # Find lacre items
                        lacre_items = []
                        for i in items:
                            desc = (i.get('descricao', '') or i.get('descricaoItem', '')).lower()
                            if 'lacre' in desc:
                                lacre_items.append(i)

                        print(f"  Lacre items: {len(lacre_items)}")
                        if lacre_items:
                            print(f"\n  Lacre items found:")
                            for li in lacre_items:
                                desc = li.get('descricao', li.get('descricaoItem', 'N/A'))
                                qty = li.get('quantidade', 'N/A')
                                print(f"    • {desc}")
                                print(f"      Qty: {qty}\n")
                    else:
                        print(f"  ❌ Failed to fetch items: {item_response}")

                    found = True
                    break

                # Also check by name
                if 'COSMOPOLIS' in org_name or 'COSMÓPOLIS' in org_name:
                    print(f"\n  Found Cosmópolis org: {org_name}")
                    print(f"    CNPJ: {org.get('cnpj')} (normalized: {tender_cnpj})")
                    print(f"    Sequential: {tender_seq}, Year: {tender_year}")

            page += 1
            await asyncio.sleep(0.5)  # Rate limiting

        if not found:
            print(f"\n❌ Tender not found after checking {total_checked} tenders across {page-1} pages")

    finally:
        await api.close_session()

if __name__ == "__main__":
    asyncio.run(test())
