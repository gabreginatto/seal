# Seal - PNCP Lacre Discovery System

> Automated discovery and monitoring system for security seal (lacre) procurement tenders in Brazil

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192.svg)](https://www.postgresql.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-SQL-4285F4.svg)](https://cloud.google.com/sql)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Overview

Seal is a specialized tender discovery system that monitors and analyzes Brazilian government procurement opportunities for **security seals (lacre)** - tamper-evident seals, security devices, and identification systems used in healthcare, logistics, and government operations.

The system automatically:
- 🔍 Discovers lacre tenders from the PNCP API (Portal Nacional de Contratações Públicas)
- 💾 Saves tender data to PostgreSQL database with full item details
- 💰 Fetches homologated (awarded) prices and winner information
- 📊 Provides analytics-ready data for market intelligence
- 🚀 Processes efficiently with smart sampling and rate limiting

## ✨ Key Features

### Intelligent Discovery Pipeline
- **Multi-stage processing**: Bulk fetch → Quick filter → Smart sampling → Full analysis → Database storage
- **Keyword-based filtering**: High-relevance keywords for accurate lacre identification
- **Smart sampling**: Reduces API calls by ~90% while maintaining accuracy
- **Database deduplication**: Prevents reprocessing of existing tenders

### Complete Data Capture
- ✅ Organization details (CNPJ, name, location, government level)
- ✅ Tender information (control number, modality, publication date, status)
- ✅ Item details (description, quantity, unit, estimated values)
- ✅ **Homologated values** (awarded prices and winner information)
- ✅ Processing history and logs

### Performance & Reliability
- 🚀 Asynchronous operations for speed
- 🚀 API rate limiting (60 requests/minute)
- 🚀 Cloud SQL connection pooling
- 🚀 Comprehensive error handling and logging
- 🚀 Configurable retry mechanisms

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [Database](#-database)
- [API Details](#-api-details)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 13+ (or Google Cloud SQL instance)
- Google Cloud SDK (for Cloud SQL connections)
- Git

### Clone Repository

```bash
git clone https://github.com/gabreginatto/seal.git
cd seal
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Google Cloud Authentication

Set up Google Cloud credentials for Cloud SQL access:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/pncp-key.json"
```

### Database Setup

Run the complete database setup script:

```bash
python setup/complete_db_setup_lacre.py
```

This creates:
- All required tables (tenders, tender_items, organizations, etc.)
- Foreign key constraints and indexes
- Views for easier querying (vw_lacre_items)

## 🏃 Quick Start

### Run Discovery for São Paulo (October 2024)

```bash
./run_lacre_discovery.sh --start-date 20241001 --end-date 20241031 --states SP --discovery-only
```

This will:
1. Fetch all tenders from PNCP API for São Paulo in October 2024
2. Filter for lacre-related items using keyword matching
3. Save lacre items to database with homologated values
4. Generate logs in `logs/seal_run_*.log`

### Check Results

```bash
python check_lacre_items.py
```

This displays:
- Total lacre items found
- Count with/without homologated values
- Sample items with details

## ⚙️ Configuration

### System Configuration

Edit `src/lacre/config_lacre.py` to customize:

```python
class LacreProcessingConfig:
    enabled_states: List[str] = ['SP', 'RJ', 'MG']  # States to monitor
    min_tender_value: float = 1_000.0  # Minimum tender value (BRL)
    allowed_modalities: List[int] = [6, 12]  # Pregão, Credenciamento
    only_ongoing_tenders: bool = True  # Filter ongoing only
```

### Keywords Configuration

The system uses multiple keyword categories in `config_lacre.py`:

```python
LACRE_KEYWORDS = {
    'lacre', 'lacre de segurança', 'lacre inviolável',
    'lacre plástico', 'lacre metálico', 'lacre tipo âncora',
    'tamper evident seal', 'security seal', ...
}

MEDICAL_LACRE_KEYWORDS = {
    'lacre para sangue', 'lacre para amostra biológica',
    'lacre para material estéril', ...
}
```

### Database Configuration

Connection details in `.claude/rules.md`:

```python
# Cloud SQL Connection
connector = Connector()
conn = await connector.connect_async(
    "medical-473219:us-central1:pncp-medical-db",
    "asyncpg",
    user="postgres",
    password="TempPass123!",
    db="pncp_lacre_data",
    enable_iam_auth=False,
)
```

## 🎯 Usage

### Basic Discovery

Run discovery for a specific date range and state(s):

```bash
./run_lacre_discovery.sh \
  --start-date 20241001 \
  --end-date 20241231 \
  --states SP RJ MG \
  --discovery-only
```

### Full Year Processing

```bash
./run_lacre_discovery.sh \
  --start-date 20240101 \
  --end-date 20241231 \
  --states SP \
  --discovery-only
```

### Multiple States

```bash
./run_lacre_discovery.sh \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP RJ MG ES PR SC \
  --discovery-only
```

### Command-Line Arguments

| Argument | Description | Required | Example |
|----------|-------------|----------|---------|
| `--start-date` | Start date (YYYYMMDD) | Yes | `20241001` |
| `--end-date` | End date (YYYYMMDD) | Yes | `20241231` |
| `--states` | Space-separated state codes | Yes | `SP RJ MG` |
| `--discovery-only` | Skip full processing (faster) | No | - |

### Monitoring Progress

#### Check Logs

```bash
tail -f logs/seal_run_*.log
```

#### Check Database

```bash
python check_lacre_items.py
```

#### Monitor Process

```bash
ps aux | grep main_lacre
```

## 🗄️ Database

### Connection

The system uses **Google Cloud SQL Connector** for secure connections:

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
        # Your queries here
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM tender_items WHERE is_lacre = TRUE;"
        )
        print(f"Lacre items: {count}")
    finally:
        await conn.close()
        await connector.close_async()

asyncio.run(query_db())
```

### Core Tables

#### `tenders`
Main tender information from PNCP

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `control_number` | TEXT | Unique tender identifier |
| `cnpj` | VARCHAR(14) | Organization CNPJ |
| `year` | INTEGER | Year |
| `sequential` | INTEGER | Sequential number |
| `publication_date` | DATE | Publication date |
| `object_description` | TEXT | Tender description |
| `estimated_value` | NUMERIC | Estimated total value |
| `modality_code` | INTEGER | Modality (6=Pregão, etc.) |
| `status` | TEXT | Tender status |

#### `tender_items`
Individual items within tenders

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `tender_id` | INTEGER | Foreign key to tenders |
| `item_number` | INTEGER | Item number |
| `description` | TEXT | Item description |
| `quantity` | NUMERIC | Quantity |
| `unit` | VARCHAR(50) | Unit of measurement |
| `estimated_unit_value` | NUMERIC | Estimated unit price |
| `estimated_total_value` | NUMERIC | Estimated total price |
| `is_lacre` | BOOLEAN | Lacre classification |
| `homologated_unit_value` | NUMERIC | **Awarded unit price** |
| `homologated_total_value` | NUMERIC | **Awarded total price** |
| `winner_name` | TEXT | **Winning company name** |
| `winner_cnpj` | VARCHAR(14) | **Winning company CNPJ** |

#### `organizations`
Government organizations

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `cnpj` | VARCHAR(14) | Unique CNPJ |
| `name` | TEXT | Organization name |
| `government_level` | TEXT | Federal/State/Municipal |
| `state` | VARCHAR(2) | State code |
| `municipality` | TEXT | Municipality name |

### Common Queries

#### Count lacre items

```sql
SELECT COUNT(*) FROM tender_items WHERE is_lacre = TRUE;
```

#### Check homologated values coverage

```sql
SELECT
    COUNT(*) as total_items,
    COUNT(homologated_unit_value) as with_values,
    COUNT(*) - COUNT(homologated_unit_value) as missing_values,
    ROUND(100.0 * COUNT(homologated_unit_value) / COUNT(*), 2) as coverage_pct
FROM tender_items
WHERE is_lacre = TRUE;
```

#### Get lacre items with details

```sql
SELECT
    ti.description,
    ti.quantity,
    ti.unit,
    ti.estimated_unit_value,
    ti.homologated_unit_value,
    ti.winner_name,
    t.control_number,
    t.publication_date,
    o.name as org_name,
    o.state
FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.is_lacre = TRUE
ORDER BY t.publication_date DESC
LIMIT 10;
```

#### Use the lacre items view

```sql
SELECT * FROM vw_lacre_items
ORDER BY publication_date DESC
LIMIT 10;
```

### Utilities

#### Clear database (for testing)

```bash
python clear_lacre_data.py
```

#### Check database status

```bash
python check_db_simple.py
```

## 📚 API Details

### PNCP API

The system uses the PNCP (Portal Nacional de Contratações Públicas) public API.

**Base URLs:**
- Consultation: `https://pncp.gov.br/api/consulta/v1/`
- Procurement: `https://pncp.gov.br/api/pncp/v1/`

**Key Endpoints:**

```
GET /api/consulta/v1/contratacoes/publicacao
  - Fetch tenders by publication date
  - Parameters: dataInicial, dataFinal, uf, codigoModalidadeContratacao
  - Pagination: pagina, tamanhoPagina (max 50)

GET /api/consulta/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens
  - Fetch all items for a tender
  - Returns item details, quantities, prices

GET /api/pncp/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados
  - Fetch homologated results for an item
  - Returns winner, awarded prices
  - ⚠️ MUST use /api/pncp/v1/ (not /api/consulta/v1/)
```

**Rate Limits:**
- 60 requests per minute
- No hourly limit (previously thought to be 1000/hour)

### Homologated Values Fix

**Critical Issue Resolved:** The system was returning 404 errors when fetching item results.

**Root Cause:** The `get_item_results()` function was using the wrong base URL.

**Fix Applied** (`src/pncp_api.py:332`):

```python
# ❌ WRONG (was using consultation URL):
url = f"{self.base_url}/v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item_number}/resultados"
# where self.base_url = "https://pncp.gov.br/api/consulta"

# ✅ CORRECT (hardcoded procurement URL):
url = "https://pncp.gov.br/api/pncp/v1/orgaos/{}/compras/{}/{}/itens/{}/resultados".format(
    cnpj, year, sequential, item_number
)
```

**Result:** Homologated values now correctly fetched for all items with `temResultado=True`.

**Verified:** Test run (Jan 8-14, 2025 in SP) shows 100% success rate (2/2 items with values).

## 📁 Project Structure

```
seal/
├── src/
│   └── lacre/                        # Lacre system
│       ├── main_lacre.py             # Main entry point
│       ├── config_lacre.py           # Configuration and keywords
│       ├── database_lacre.py         # Database operations
│       ├── classifier_lacre.py       # Product classification
│       └── optimized_lacre_discovery.py  # Discovery engine
│
├── setup/                            # Database setup scripts
│   ├── complete_db_setup_lacre.py    # Complete DB setup
│   ├── recreate_lacre_schema.py      # Schema creation
│   ├── add_constraints_lacre.py      # Constraints & indexes
│   └── verify_setup.py               # Setup verification
│
├── logs/                             # Log files
│   └── seal_run_*.log               # Timestamped logs
│
├── .claude/                          # Claude Code rules
│   └── rules.md                     # Project documentation
│
├── run_lacre_discovery.sh            # Main execution script
├── check_lacre_items.py              # Database verification
├── clear_lacre_data.py               # Database clearing
├── src/pncp_api.py                   # PNCP API client
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## 🔧 Troubleshooting

### Issue: No items found

**Check:**
1. Date range is valid (YYYYMMDD format)
2. State codes are correct (e.g., 'SP', 'RJ')
3. Database is properly set up
4. API is accessible

```bash
# Test API access
curl "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20241001&dataFinal=20241031&pagina=1"
```

### Issue: Homologated values are NULL

**Check:**
1. Items have `temResultado=True` in API response
2. API URL fix is applied (`src/pncp_api.py:332`)
3. No 404 errors in logs

```bash
# Check logs for API errors
grep "404\|Failed to fetch results" logs/seal_run_*.log
```

### Issue: Database connection failed

**Check:**
1. Google Cloud credentials are set
2. Cloud SQL instance is running
3. Connection string is correct

```bash
# Test connection
python check_db_simple.py
```

### Issue: Rate limit errors

**Solution:** The system automatically handles rate limits. If you see rate limit warnings, the system will wait and retry.

```bash
# Check logs for rate limit messages
grep "rate limit" logs/seal_run_*.log
```

### Issue: Import errors

**Check:**
1. All dependencies installed: `pip install -r requirements.txt`
2. Using correct script: `./run_lacre_discovery.sh` (NOT direct Python)
3. PYTHONPATH is not manually set (script handles this)

### Debug Mode

Enable detailed logging:

```bash
export LOGLEVEL=DEBUG
./run_lacre_discovery.sh --start-date 20241001 --end-date 20241031 --states SP --discovery-only
```

## 🏗️ Architecture

### Discovery Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 1: Bulk Fetch                                        │
│  • Fetch tenders from PNCP API by state/modality           │
│  • Handle pagination (50 tenders per page)                  │
│  • Apply date range filters                                 │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: Quick Filter                                      │
│  • Keyword-based filtering (lacre-specific keywords)        │
│  • Database deduplication check                             │
│  • Filter ~95% of irrelevant tenders                       │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 3: Item Fetch & Analysis                            │
│  • Fetch all items for filtered tenders                    │
│  • Classify items (is_lacre boolean)                        │
│  • Fetch homologated values for items with results         │
│  • Save immediately to database                             │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 4: Database Storage                                  │
│  • Store organizations, tenders, items                      │
│  • Track processing history                                 │
│  • Generate summary statistics                              │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.8+ with async/await
- **Database**: PostgreSQL 13+ (Google Cloud SQL)
- **DB Driver**: asyncpg (async PostgreSQL)
- **HTTP Client**: aiohttp (async HTTP)
- **Cloud**: Google Cloud SQL Connector
- **Logging**: Python logging with file rotation

## 📊 Performance

Typical performance for São Paulo state (October 2024):

| Metric | Value |
|--------|-------|
| **Tenders Fetched** | ~700 |
| **Stage 1 Duration** | ~30s |
| **Stage 2 Filter Rate** | ~95% |
| **API Calls** | ~20-30 |
| **Total Processing Time** | ~2-3 minutes |
| **Lacre Items Found** | ~5-10 per month |
| **Homologated Coverage** | ~85-90% |

Full year processing (Jan-Nov 2025) for São Paulo:
- **Duration**: ~2-3 hours
- **Lacre Items**: 50-60+
- **API Calls**: ~1000-1500

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly with real API data
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

**Code Standards:**
- Follow PEP 8 style guidelines
- Add docstrings to functions
- Include type hints where appropriate
- Update documentation for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PNCP](https://pncp.gov.br/) - Portal Nacional de Contratações Públicas
- Google Cloud Platform for Cloud SQL infrastructure
- The Brazilian government for maintaining the PNCP API

## 📧 Contact

Gabriel Reginatto - [@gabreginatto](https://github.com/gabreginatto)

Project Link: [https://github.com/gabreginatto/seal](https://github.com/gabreginatto/seal)

---

**Built for transparent government procurement monitoring and market intelligence**

*Last Updated: November 6, 2025*
