# PNCP Lacre (Seal) Discovery Project - Claude Rules

## CRITICAL: How to Run Discovery

**ALWAYS use the existing shell script:**
```bash
./run_lacre_discovery.sh --start-date YYYYMMDD --end-date YYYYMMDD --states SP --discovery-only
```

**NEVER:**
- Try to run `python src/lacre/main_lacre.py` directly
- Try to run with `python -m src.lacre.main_lacre`
- Try to set PYTHONPATH manually
- Overcomplicate the execution

**The script handles everything correctly - just use it!**

## Database Connection

### Connection Details
- **Host**: 34.134.110.78 (direct connection) OR use Cloud SQL Connector
- **Port**: 5432
- **Database**: `pncp_lacre_data`
- **User**: `postgres`
- **Password**: `TempPass123!`
- **Connection String (Cloud SQL)**: `medical-473219:us-central1:pncp-medical-db`

### How to Query the Database (CORRECT WAY)

```python
import asyncio
import asyncpg
from google.cloud.sql.connector import Connector

async def query_db():
    connector = Connector()

    async def getconn():
        conn = await connector.connect_async(
            "medical-473219:us-central1:pncp-medical-db",
            "asyncpg",
            user="postgres",
            password="TempPass123!",
            db="pncp_lacre_data",
            enable_iam_auth=False,
        )
        return conn

    conn = await getconn()

    try:
        # Query here
        count = await conn.fetchval("SELECT COUNT(*) FROM tender_items WHERE is_lacre = TRUE;")
        print(f"Lacre items: {count}")
    finally:
        await conn.close()
        await connector.close_async()

asyncio.run(query_db())
```

### Key Tables
- `tenders` - Tender/procurement data
- `tender_items` - Individual items in tenders
- `organizations` - Government organizations
- `vw_lacre_items` - View combining tender and item data for lacre items

### Important Columns
- `is_lacre` - Boolean flag indicating if item is a security seal
- `homologated_unit_value` - Final awarded unit price
- `homologated_total_value` - Final awarded total price
- `winner_name` - Name of winning company
- `winner_cnpj` - CNPJ of winning company
- `estimated_unit_value` - Estimated unit price
- `estimated_total_value` - Estimated total price

## Homologated Values Fix

The code now correctly fetches homologated values from the PNCP API:

**Location 1**: `src/lacre/optimized_lacre_discovery.py` lines 706-745 (`_save_single_tender_to_db`)
**Location 2**: `src/lacre/optimized_lacre_discovery.py` lines 883-921 (`_save_tenders_to_db`)

**Logic**:
1. Check if `item.get('temResultado', False)` is True
2. Call `await api_client.get_item_results(cnpj, year, sequential, item_number)`
3. **✅ CRITICAL FIX 1 - Response Format Handling**: Handle both response formats:
   - If response is a list: use directly
   - If response is a dict: extract from `result_response.get('data', [])`
4. **✅ CRITICAL FIX 2 - API URL**: `src/lacre/pncp_api.py` line 332
   - **MUST** use: `https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados`
   - **NOT**: `{self.base_url}/v1/...` which expands to wrong URL `https://pncp.gov.br/api/consulta/v1/...`
   - The results endpoint is in `/api/pncp/v1/`, NOT `/api/consulta/v1/`
5. Extract from first result:
   - `valorUnitarioHomologado` → `homologated_unit_value`
   - `valorTotalHomologado` → `homologated_total_value`
   - `nomeRazaoSocialFornecedor` → `winner_name`
   - `niFornecedor` → `winner_cnpj`

## Project Structure

```
/Users/gabrielreginatto/Desktop/Code/Seal/
├── src/lacre/              # Lacre-specific code
│   ├── main_lacre.py       # Main entry point
│   ├── optimized_lacre_discovery.py  # Discovery logic
│   ├── pncp_api.py         # API client
│   └── database_lacre.py   # Database operations
├── run_lacre_discovery.sh  # USE THIS SCRIPT
├── logs/                   # Log files
└── setup/                  # Setup scripts
```

## Common Queries

### Check lacre items count
```sql
SELECT COUNT(*) FROM tender_items WHERE is_lacre = TRUE;
```

### Check items missing homologated values
```sql
SELECT COUNT(*)
FROM tender_items
WHERE is_lacre = TRUE
  AND homologated_unit_value IS NULL;
```

### Get sample lacre items
```sql
SELECT
    ti.description,
    ti.estimated_unit_value,
    ti.homologated_unit_value,
    ti.winner_name,
    t.control_number
FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
WHERE ti.is_lacre = TRUE
LIMIT 10;
```

### Use the view for easier queries
```sql
SELECT * FROM vw_lacre_items LIMIT 10;
```

## Testing Protocol

1. **Always** use `./run_lacre_discovery.sh` to run tests
2. **Always** use Cloud SQL Connector to query the database
3. **Never** try to be clever with imports or execution - the script works!
4. **Check** logs at `/Users/gabrielreginatto/Desktop/Code/Seal/logs/seal_run_*.log`

## Sister Project

This project is based on the Medical supplies project. When in doubt:
- Medical project: `pncp_medical_data` database
- Lacre project: `pncp_lacre_data` database
- Same Cloud SQL instance, different databases
- Same table structure and logic patterns

## Debugging

### Check if process is running
```bash
ps aux | grep main_lacre
```

### Monitor logs in real-time
```bash
tail -f logs/seal_run_*.log
```

### Check database connection
```bash
python check_db_simple.py
```

## DO NOT

❌ Try to run Python modules directly without the script
❌ Query the database without using Cloud SQL Connector
❌ Make assumptions about data being there - always verify first
❌ Forget that the database might be empty if tests were cleared
