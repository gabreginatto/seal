#!/usr/bin/env python3
"""
Automatic Notion Database Setup for PNCP Medical Data
Creates the 3 required databases with proper schemas
"""

import os
import asyncio
import aiohttp
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NotionDatabaseCreator:
    """Creates Notion databases automatically via API"""

    def __init__(self):
        self.api_token = os.getenv('NOTION_API_TOKEN')
        self.parent_page_id = os.getenv('NOTION_PARENT_PAGE_ID', '')
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    def get_tenders_database_schema(self) -> Dict[str, Any]:
        """Define schema for Tenders database"""
        # For now, we'll need the user to create a parent page first
        if not self.parent_page_id or self.parent_page_id == 'your_parent_page_id_optional':
            raise Exception("Please create a parent page in Notion and add its ID to NOTION_PARENT_PAGE_ID in .env")

        parent = {"page_id": self.parent_page_id}

        return {
            "title": [{"text": {"content": "PNCP Tenders Database"}}],
            "parent": parent,
            "properties": {
                "Title": {"title": {}},
                "Organization": {"rich_text": {}},
                "CNPJ": {"rich_text": {}},
                "State": {
                    "select": {
                        "options": [
                            {"name": "SP", "color": "blue"},
                            {"name": "RJ", "color": "green"},
                            {"name": "MG", "color": "yellow"},
                            {"name": "DF", "color": "red"},
                            {"name": "RS", "color": "purple"},
                            {"name": "PR", "color": "pink"},
                            {"name": "BA", "color": "brown"},
                            {"name": "SC", "color": "orange"},
                            {"name": "GO", "color": "gray"},
                            {"name": "PE", "color": "default"},
                        ]
                    }
                },
                "Government Level": {
                    "select": {
                        "options": [
                            {"name": "Federal", "color": "red"},
                            {"name": "State", "color": "yellow"},
                            {"name": "Municipal", "color": "blue"}
                        ]
                    }
                },
                "Total Value (R$)": {
                    "number": {"format": "real"}
                },
                "Publication Date": {"date": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Homologated", "color": "green"},
                            {"name": "In Progress", "color": "yellow"},
                            {"name": "Cancelled", "color": "red"}
                        ]
                    }
                },
                "Items Count": {"number": {}},
                "Matches Found": {"number": {}},
                "Processed Date": {"date": {}}
            }
        }

    def get_items_database_schema(self) -> Dict[str, Any]:
        """Define schema for Items database"""
        if not self.parent_page_id or self.parent_page_id == 'your_parent_page_id_optional':
            raise Exception("Please create a parent page in Notion and add its ID to NOTION_PARENT_PAGE_ID in .env")

        parent = {"page_id": self.parent_page_id}

        return {
            "title": [{"text": {"content": "PNCP Items Database"}}],
            "parent": parent,
            "properties": {
                "Description": {"title": {}},
                "Tender ID": {"rich_text": {}},
                "Organization": {"rich_text": {}},
                "Item Number": {"number": {}},
                "Unit": {"rich_text": {}},
                "Quantity": {"number": {}},
                "Unit Price (R$)": {
                    "number": {"format": "real"}
                },
                "Total Price (R$)": {
                    "number": {"format": "real"}
                },
                "Winner": {"rich_text": {}},
                "State": {
                    "select": {
                        "options": [
                            {"name": "SP", "color": "blue"},
                            {"name": "RJ", "color": "green"},
                            {"name": "MG", "color": "yellow"},
                            {"name": "DF", "color": "red"},
                            {"name": "N/A", "color": "gray"},
                        ]
                    }
                },
                "Has Match": {"checkbox": {}}
            }
        }

    def get_opportunities_database_schema(self) -> Dict[str, Any]:
        """Define schema for Opportunities database"""
        if not self.parent_page_id or self.parent_page_id == 'your_parent_page_id_optional':
            raise Exception("Please create a parent page in Notion and add its ID to NOTION_PARENT_PAGE_ID in .env")

        parent = {"page_id": self.parent_page_id}

        return {
            "title": [{"text": {"content": "PNCP Competitive Opportunities"}}],
            "parent": parent,
            "properties": {
                "Product": {"title": {}},
                "Fernandes Code": {"rich_text": {}},
                "Tender Description": {"rich_text": {}},
                "Organization": {"rich_text": {}},
                "Match Score": {"number": {"format": "percent"}},
                "FOB Price (USD)": {
                    "number": {"format": "dollar"}
                },
                "Market Price (R$)": {
                    "number": {"format": "real"}
                },
                "Our Price (R$)": {
                    "number": {"format": "real"}
                },
                "Price Difference (%)": {
                    "number": {"format": "percent"}
                },
                "Competitive": {"checkbox": {}},
                "State": {
                    "select": {
                        "options": [
                            {"name": "SP", "color": "blue"},
                            {"name": "RJ", "color": "green"},
                            {"name": "MG", "color": "yellow"},
                            {"name": "DF", "color": "red"},
                            {"name": "N/A", "color": "gray"},
                        ]
                    }
                },
                "Opportunity Score": {
                    "select": {
                        "options": [
                            {"name": "🟢 High", "color": "green"},
                            {"name": "🟡 Medium", "color": "yellow"},
                            {"name": "🟠 Low", "color": "orange"},
                            {"name": "🔴 Poor", "color": "red"}
                        ]
                    }
                },
                "Quantity": {"number": {}},
                "Potential Revenue (R$)": {
                    "number": {"format": "real"}
                }
            }
        }

    async def create_database(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create a database using Notion API"""
        url = f"{self.base_url}/databases"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=schema) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create database: {response.status} - {error_text}")

    async def setup_all_databases(self):
        """Create all three databases"""

        if not self.api_token or self.api_token == 'your_notion_integration_token':
            print("❌ NOTION_API_TOKEN not configured in .env file")
            print("Please follow these steps:")
            print("1. Go to https://www.notion.so/my-integrations")
            print("2. Create a new integration called 'PNCP Medical Processor'")
            print("3. Copy the integration token to your .env file")
            return False

        print("🚀 Creating Notion databases for PNCP Medical Processing...")
        print()

        databases_created = []

        try:
            # Create Tenders Database
            print("📋 Creating Tenders Database...")
            tenders_schema = self.get_tenders_database_schema()
            tenders_db = await self.create_database(tenders_schema)
            tenders_id = tenders_db['id']
            databases_created.append(('Tenders', tenders_id, tenders_db['url']))
            print(f"✅ Tenders Database created: {tenders_id}")

            await asyncio.sleep(1)  # Rate limiting

            # Create Items Database
            print("📦 Creating Items Database...")
            items_schema = self.get_items_database_schema()
            items_db = await self.create_database(items_schema)
            items_id = items_db['id']
            databases_created.append(('Items', items_id, items_db['url']))
            print(f"✅ Items Database created: {items_id}")

            await asyncio.sleep(1)  # Rate limiting

            # Create Opportunities Database
            print("💰 Creating Opportunities Database...")
            opportunities_schema = self.get_opportunities_database_schema()
            opportunities_db = await self.create_database(opportunities_schema)
            opportunities_id = opportunities_db['id']
            databases_created.append(('Opportunities', opportunities_id, opportunities_db['url']))
            print(f"✅ Opportunities Database created: {opportunities_id}")

            print()
            print("🎉 All databases created successfully!")
            print()
            print("📋 Database Information:")
            print("=" * 60)

            for name, db_id, url in databases_created:
                print(f"{name} Database:")
                print(f"  ID: {db_id}")
                print(f"  URL: {url}")
                print()

            print("🔧 Add these to your .env file:")
            print("=" * 40)
            print(f"NOTION_TENDERS_DB_ID={databases_created[0][1]}")
            print(f"NOTION_ITEMS_DB_ID={databases_created[1][1]}")
            print(f"NOTION_OPPORTUNITIES_DB_ID={databases_created[2][1]}")
            print()

            print("✅ Setup complete! Your Notion databases are ready.")
            print("🚀 You can now run: python main.py --start-date 20240101 --end-date 20240131")

            return True

        except Exception as e:
            print(f"❌ Error creating databases: {e}")
            print()
            print("Common issues:")
            print("1. Invalid API token - check your integration token")
            print("2. No parent page specified - the databases will be created in your workspace root")
            print("3. Rate limiting - try again in a few seconds")

            if databases_created:
                print()
                print("⚠️  Some databases were created successfully:")
                for name, db_id, url in databases_created:
                    print(f"  {name}: {db_id}")

            return False

async def main():
    """Main setup function"""
    print("🔧 PNCP Medical Data - Notion Database Setup")
    print("=" * 50)

    creator = NotionDatabaseCreator()
    success = await creator.setup_all_databases()

    if success:
        print()
        print("🎯 Next Steps:")
        print("1. Update your .env file with the database IDs above")
        print("2. Add your PNCP credentials to .env")
        print("3. Run the medical processor!")
        print()
        print("📚 For more info, check NOTION_SETUP.md")
    else:
        print()
        print("❌ Setup failed. Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())