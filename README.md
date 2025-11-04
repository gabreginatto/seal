# Seal - PNCP Tender Monitoring System

> Automated monitoring and analysis system for Brazilian government procurement tenders (PNCP - Portal Nacional de Contratações Públicas)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192.svg)](https://www.postgresql.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-SQL-4285F4.svg)](https://cloud.google.com/sql)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Overview

Seal is a comprehensive tender monitoring system that tracks and analyzes government procurement opportunities in Brazil. The system supports two product categories:

- 🏥 **Medical Supplies** - Surgical materials, medical equipment, and healthcare products
- 🔐 **Security Seals (Lacre)** - Tamper-evident seals, security devices, and identification systems

## ✨ Features

### Multi-Stage Discovery Pipeline
- **Stage 1: Bulk Fetch** - Retrieves tenders from PNCP API with intelligent pagination
- **Stage 2: Quick Filter** - Rapid keyword-based filtering using product-specific dictionaries
- **Stage 3: Smart Sampling** - Efficient item sampling with confidence-based processing
- **Stage 4: Full Processing** - Complete tender analysis with priority grouping
- **Stage 5: Database Storage** - PostgreSQL storage with deduplication

### Intelligent Processing
- ✅ Database deduplication to prevent reprocessing
- ✅ API rate limiting (60 req/min, 1000 req/hour)
- ✅ Multi-modality support (Pregão, Credenciamento, etc.)
- ✅ Ongoing tender detection and filtering
- ✅ Geographic filtering by state/municipality
- ✅ Value-based prioritization
- ✅ Notion dashboard integration

### Performance Optimizations
- 🚀 Smart sampling reduces API calls by ~90%
- 🚀 Keyword-based pre-filtering reduces processing time
- 🚀 Asynchronous database operations
- 🚀 Connection pooling for Cloud SQL
- 🚀 Configurable batch processing

## 📋 Table of Contents

- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Database Schema](#️-database-schema)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 13+ (or Google Cloud SQL)
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

### Database Setup

#### Option 1: Complete Setup (Recommended)

```bash
# For Lacre (Security Seals) system
python setup/complete_db_setup_lacre.py

# For Medical system
python setup/complete_db_setup.py
```

#### Option 2: Manual Setup

```bash
# Create database schema
python setup/recreate_lacre_schema.py

# Add constraints
python setup/add_constraints_lacre.py

# Verify setup
python setup/verify_setup.py
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Google Cloud SQL Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_INSTANCE_NAME=your-instance-name
GCP_DATABASE_NAME=pncp_lacre_data

# Notion Integration (Optional)
NOTION_API_KEY=your-notion-api-key
NOTION_DATABASE_ID=your-database-id

# PNCP API (Optional - Public access available)
PNCP_USERNAME=your-username
PNCP_PASSWORD=your-password
```

## ⚙️ Configuration

### System Configuration

Edit configuration files in `src/lacre/` or `src/medical/`:

**Lacre System** (`src/lacre/config_lacre.py`):
```python
class LacreProcessingConfig:
    enabled_states: List[str] = ['SP', 'RJ', 'MG']  # States to monitor
    min_tender_value: float = 1_000.0  # Minimum tender value (BRL)
    allowed_modalities: List[int] = [6, 12]  # Pregão, Credenciamento
    only_ongoing_tenders: bool = True  # Filter ongoing only
```

**Medical System** (`src/medical/config.py`):
```python
class ProcessingConfig:
    enabled_states: List[str] = ['SP', 'RJ', 'MG']
    min_tender_value: float = 5_000.0
    allowed_modalities: List[int] = [6, 12, 1, 9]
```

### Keywords Configuration

Add or modify product keywords in configuration files:

```python
# Lacre keywords (config_lacre.py)
LACRE_KEYWORDS = {
    'lacre', 'lacre de segurança', 'lacre inviolável',
    'tamper evident seal', 'security seal', ...
}

# Medical keywords (config.py)
MEDICAL_KEYWORDS = {
    'luva cirúrgica', 'bisturi', 'seringa',
    'surgical glove', 'scalpel', 'syringe', ...
}
```

## 🎯 Usage

### Basic Usage

#### Lacre (Security Seals) System

```bash
# Discovery mode - Find new tenders
python src/lacre/main_lacre.py \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP RJ MG \
  --discovery-only

# Full processing - Discovery + Item analysis
python src/lacre/main_lacre.py \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP
```

#### Medical System

```bash
# Discovery mode
python src/medical/main.py \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP \
  --discovery-only

# Full processing
python src/medical/main.py \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP RJ MG
```

### Advanced Options

```bash
# Process specific states with custom date range
python src/lacre/main_lacre.py \
  --start-date 20241001 \
  --end-date 20241231 \
  --states SP RJ MG ES \
  --min-value 5000

# Run with increased logging
LOGLEVEL=DEBUG python src/lacre/main_lacre.py \
  --start-date 20241001 \
  --end-date 20241031 \
  --states SP
```

### Command-Line Arguments

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `--start-date` | Start date (YYYYMMDD) | Required | `20241001` |
| `--end-date` | End date (YYYYMMDD) | Required | `20241031` |
| `--states` | State codes to process | All | `SP RJ MG` |
| `--discovery-only` | Run discovery only (no item processing) | False | - |
| `--min-value` | Minimum tender value (BRL) | Config | `5000` |

### Output

The system generates:
- **Console output**: Real-time progress and statistics
- **Log files**: Detailed logs in `logs/` directory
- **JSON files**: Processed tender data in root directory
- **Database records**: Full tender data in PostgreSQL
- **Notion dashboard**: (Optional) Visual dashboard integration

## 📁 Project Structure

```
seal/
├── src/
│   ├── lacre/                    # Lacre (Security Seals) system
│   │   ├── main_lacre.py        # Main entry point
│   │   ├── config_lacre.py      # Configuration
│   │   ├── database_lacre.py    # Database operations
│   │   ├── classifier_lacre.py  # Product classification
│   │   └── optimized_lacre_discovery.py  # Discovery engine
│   │
│   ├── medical/                  # Medical supplies system
│   │   ├── main.py              # Main entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database operations
│   │   ├── classifier.py        # Product classification
│   │   └── item_processor.py   # Item processing
│   │
│   └── notion_integration.py    # Shared Notion integration
│
├── setup/                        # Database setup scripts
│   ├── complete_db_setup_lacre.py
│   ├── recreate_lacre_schema.py
│   └── verify_setup.py
│
├── backup/                       # Archived scripts
├── docs/                         # Documentation
├── logs/                         # Log files
├── pncp_api.py                  # Shared PNCP API client
└── requirements.txt             # Python dependencies
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed documentation.

## 🏗️ Architecture

### Multi-Stage Discovery Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Bulk Fetch                                           │
│  • Fetch tenders from PNCP API by state/modality              │
│  • Handle pagination (50 tenders per page)                     │
│  • Apply date range filters                                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Quick Filter                                         │
│  • Keyword-based filtering (HIGH_RELEVANCE keywords)           │
│  • Database deduplication check                                │
│  • Filter ~95% of irrelevant tenders                          │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Smart Sampling                                       │
│  • Phase 1: Auto-approve high-confidence matches               │
│  • Phase 2: Sample first 3 items for edge cases               │
│  • Saves ~90% of API calls                                     │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: Full Processing                                      │
│  • Priority grouping (high/medium/low value)                   │
│  • Complete item fetch and analysis                            │
│  • Product matching and classification                         │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5: Database Storage                                     │
│  • Store tenders, items, organizations                         │
│  • Track processing history                                    │
│  • Export to Notion (optional)                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: Python 3.8+ with asyncio
- **Database**: PostgreSQL 13+ (Google Cloud SQL)
- **API Client**: aiohttp for async HTTP
- **Cloud**: Google Cloud Platform
- **Integration**: Notion API
- **Data Processing**: Pandas, asyncpg

## 📚 API Documentation

### PNCP API

The system uses the PNCP (Portal Nacional de Contratações Públicas) public consultation API:

**Base URL**: `https://pncp.gov.br/api/consulta`

**Key Endpoints**:
- `GET /v1/contratacoes/publicacao` - Get tenders by publication date
- `GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens` - Get tender items
- `GET /v1/orgaos/{cnpj}/compras/{year}/{sequential}/itens/{item}/resultados` - Get item results

**Rate Limits**:
- 60 requests per minute
- 1,000 requests per hour

**Parameters**:
- `dataInicial` / `dataFinal`: Date range (YYYYMMDD)
- `codigoModalidadeContratacao`: Modality code (1-12)
- `uf`: State code (e.g., 'SP', 'RJ')
- `pagina`: Page number
- `tamanhoPagina`: Page size (10-50)

See [docs/ManualPNCPAPIConsultasVerso1.0.pdf](docs/ManualPNCPAPIConsultasVerso1.0.pdf) for complete API documentation.

## 🗄️ Database Schema

### Core Tables

**tenders**
- `id` (PK)
- `control_number` (Unique)
- `cnpj`, `year`, `sequential`
- `publication_date`, `object_description`
- `estimated_value`, `modality_code`
- `status`, `government_level`

**tender_items**
- `id` (PK)
- `tender_id` (FK → tenders)
- `item_number`, `description`
- `quantity`, `unit`, `unit_value`
- `catalog_item_code`

**organizations**
- `id` (PK)
- `cnpj` (Unique)
- `name`, `government_level`
- `state`, `municipality`
- `organization_type`

**matched_products**
- `id` (PK)
- `item_id` (FK → tender_items)
- `product_type`, `match_score`
- `keywords_matched`

**processing_log**
- `id` (PK)
- `tender_id` (FK → tenders)
- `stage`, `status`
- `timestamp`, `details`

See database schema files in `setup/` for complete DDL.

## 👩‍💻 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/gabreginatto/seal.git
cd seal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy
```

### Code Style

This project follows PEP 8 style guidelines:

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_classifier.py

# Run with coverage
pytest --cov=src tests/
```

### Adding New Product Categories

1. Create new configuration file: `src/your_category/config_your_category.py`
2. Define keywords and classifications
3. Create database operations: `database_your_category.py`
4. Implement discovery logic: `optimized_your_category_discovery.py`
5. Create main entry point: `main_your_category.py`
6. Update setup scripts in `setup/`

## 📊 Performance Metrics

Typical performance for São Paulo state (October 2024):

| Metric | Value |
|--------|-------|
| **Tenders Fetched** | 706 |
| **Stage 1 Duration** | ~30s |
| **Stage 2 Filter Rate** | ~95% |
| **Stage 3 API Savings** | ~90% |
| **Total API Calls** | ~20 |
| **Processing Time** | ~45s |
| **Memory Usage** | < 500MB |

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows PEP 8 style guidelines
- Tests are included for new features
- Documentation is updated
- Commit messages are clear and descriptive

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PNCP](https://pncp.gov.br/) - Portal Nacional de Contratações Públicas
- Google Cloud Platform for Cloud SQL infrastructure
- Notion for dashboard integration

## 📧 Contact

Gabriel Reginatto - [@gabreginatto](https://github.com/gabreginatto)

Project Link: [https://github.com/gabreginatto/seal](https://github.com/gabreginatto/seal)

---

**Built with ❤️ for transparent government procurement monitoring**
