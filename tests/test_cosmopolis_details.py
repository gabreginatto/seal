#!/usr/bin/env python3
"""
Test to get more details about the Cosmópolis tender
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'lacre'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'medical'))
sys.path.insert(0, os.path.dirname(__file__))

from pncp_api import PNCPAPIClient

async def test_tender_details():
    """Get all details about the Cosmópolis tender"""

    api = PNCPAPIClient()
    await api.start_session()

    try:
        # Search for the exact tender
        print("="*70)
        print("Finding Cosmópolis tender...")
        print("="*70)

        page = 4  # We know it's on page 4
        status, response = await api.get_tenders_by_publication_date(
            start_date="20250812",
            end_date="20250812",
            modality_code=6,
            state="SP",
            page=page,
            page_size=50
        )

        if status != 200:
            print(f"Failed to fetch page: {status}")
            return

        tenders = response.get('data', [])
        print(f"Found {len(tenders)} tenders on page {page}\n")

        # Find Cosmópolis
        target_tender = None
        for t in tenders:
            org = t.get('orgaoEntidade', {})
            tender_cnpj = org.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
            if tender_cnpj == '44730331000152':
                target_tender = t
                break

        if not target_tender:
            print("❌ Tender not found on page 4")
            return

        print("✅ Found tender! Full JSON details:\n")
        print(json.dumps(target_tender, indent=2, ensure_ascii=False))

        # Now try different item endpoints
        cnpj = '44730331000152'
        year = 2025
        seq = 105

        print("\n" + "="*70)
        print("Testing different API endpoints for items...")
        print("="*70)

        # Test 1: Standard items endpoint
        print(f"\n1. Standard items endpoint:")
        url1 = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{year}/{seq}/itens"
        print(f"   URL: {url1}")
        status, resp = await api._make_request('GET', url1)
        print(f"   Status: {status}")
        if status == 200:
            print(f"   Items: {len(resp.get('data', []))}")

        # Test 2: Pncp-compra prefix (sometimes used)
        print(f"\n2. PNCP compra endpoint:")
        url2 = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{seq}/itens"
        print(f"   URL: {url2}")
        status, resp = await api._make_request('GET', url2)
        print(f"   Status: {status}")
        if status == 200:
            if isinstance(resp, list):
                items = resp
            else:
                items = resp.get('data', [])
            print(f"   ✅ SUCCESS! Found {len(items)} items\n")

            # Show ALL item structures (first 2 items)
            print(f"\n   Sample item structures (first 2 items):")
            for i, item in enumerate(items[:2]):
                print(f"\n   Item {i+1}:")
                print(json.dumps(item, indent=4, ensure_ascii=False))

            # Search for lacre in ALL fields
            print(f"\n   Searching for 'lacre' keyword in all fields...")
            lacre_items = []
            for item in items:
                # Convert entire item to string and search
                item_str = json.dumps(item, ensure_ascii=False).lower()
                if 'lacre' in item_str:
                    lacre_items.append(item)

            print(f"   Lacre items found: {len(lacre_items)}")
            if lacre_items:
                print(f"\n   Lacre items details:")
                for li in lacre_items:
                    print(json.dumps(li, indent=4, ensure_ascii=False))

        # Test 3: Try getting from the control number directly
        control_num = target_tender.get('numeroControlePNCP') or target_tender.get('numeroControlePNCPCompra')
        if control_num:
            print(f"\n3. Control number: {control_num}")
            print(f"   (Note: No standard endpoint uses control number for items)")

        # Test 4: Check if this is a Pricing Registration (Registro de Preço)
        print(f"\n4. Checking tender type...")
        title = target_tender.get('objetoCompra', '')
        if 'registro' in title.lower() and 'preço' in title.lower():
            print(f"   ⚠️  This is a Pricing Registration (Registro de Preço)")
            print(f"   Items might be stored differently or not published yet")

        # Print relevant status fields
        print(f"\n5. Tender Status Information:")
        print(f"   situacaoCompra: {target_tender.get('situacaoCompra')}")
        print(f"   dataPublicacaoPncp: {target_tender.get('dataPublicacaoPncp')}")
        print(f"   dataAtualizacao: {target_tender.get('dataAtualizacao')}")
        print(f"   valorTotalEstimado: {target_tender.get('valorTotalEstimado')}")
        print(f"   valorTotalHomologado: {target_tender.get('valorTotalHomologado')}")

    finally:
        await api.close_session()

if __name__ == "__main__":
    asyncio.run(test_tender_details())
