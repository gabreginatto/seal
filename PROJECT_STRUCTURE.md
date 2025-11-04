# Seal Project - Directory Structure

This document describes the organized structure of the Seal project (PNCP Tender Monitoring System).

## 📁 Directory Overview

```
Seal/
├── src/                          # Source code modules
│   ├── lacre/                    # Lacre (security seals) tender system
│   ├── medical/                  # Medical tender system
│   └── notion_integration.py    # Shared Notion API integration
├── setup/                        # Database and system setup scripts
├── backup/                       # Deprecated/unused scripts (archived)
├── docs/                         # Documentation and API references
├── logs/                         # Application log files
├── pncp_api.py                  # Shared PNCP API client (root level)
└── *.json                       # Data and configuration files

```

## 📂 Detailed Structure

### `/src/` - Source Code

**Core Application Modules**

#### `/src/lacre/` - Lacre Tender System
- `main_lacre.py` - Main entry point for lacre processing
- `config_lacre.py` - Lacre-specific configuration
- `database_lacre.py` - Lacre database operations
- `classifier_lacre.py` - Lacre product classification logic
- `optimized_lacre_discovery.py` - Multi-stage tender discovery
- `processed_lacre_tenders_tracker.py` - Tender tracking and JSON export
- `pncp_api.py` → symlink to root `pncp_api.py`
- `notion_integration.py` → symlink to `/src/notion_integration.py`

#### `/src/medical/` - Medical Tender System
- `main.py` - Main entry point for medical processing
- `config.py` - Medical-specific configuration
- `database.py` - Medical database operations
- `classifier.py` - Medical product classification logic
- `item_processor.py` - Item processing and matching
- `product_matcher.py` - Product matching algorithms
- `processed_tenders_tracker.py` - Tender tracking
- `pncp_api.py` → symlink to root `pncp_api.py`
- `notion_integration.py` → symlink to `/src/notion_integration.py`

**Shared Components** (located in `/src/`)
- `notion_integration.py` - Notion API client for dashboard integration

**Shared Components** (located in root)
- `pncp_api.py` - PNCP API client with authentication and rate limiting

### `/setup/` - Setup Scripts

Database initialization and configuration scripts:
- `complete_db_setup.py` - Complete medical database setup
- `complete_db_setup_lacre.py` - Complete lacre database setup
- `recreate_lacre_schema.py` - Recreate lacre database schema
- `add_constraints_lacre.py` - Add database constraints
- `setup_notion_databases.py` - Initialize Notion databases
- `simple_lacre_setup.py` - Simple lacre setup wizard
- `verify_setup.py` - Verify system configuration

### `/backup/` - Archived Scripts

Deprecated or unused scripts (kept for reference):
- `tender_discovery.py` - Old tender discovery (replaced by optimized version)
- `tender_discovery_lacre.py` - Old lacre discovery (replaced by optimized version)
- `view_processed_tenders.py` - Old tender viewer utility

### `/docs/` - Documentation

Project documentation and references:
- `README.md` - Main project README
- `LACRE_SYSTEM_README.md` - Lacre system documentation
- `NOTION_SETUP.md` - Notion integration setup guide
- `API Docs/` - PNCP API documentation
- `ManualPNCPAPIConsultasVerso1.0.pdf` - Official PNCP API manual
- `Fernandes-price-20250805 (1).pdf` - Price reference document

### `/logs/` - Log Files

Application log files (gitignored):
- `pncp_processing.log` - Medical system logs
- `pncp_lacre_processing.log` - Lacre system logs

### Root Level Files

**Main Entry Points:**
- `pncp_api.py` - Shared PNCP API client library

**Data Files:**
- `processed_lacre_tenders.json` - Processed lacre tenders tracker
- Other JSON configuration/data files

## 🚀 Usage

### Running the Lacre System
```bash
cd /Users/gabrielreginatto/Desktop/Code/Seal
python src/lacre/main_lacre.py --start-date 20241001 --end-date 20241031 --states SP
```

### Running the Medical System
```bash
cd /Users/gabrielreginatto/Desktop/Code/Seal
python src/medical/main.py --start-date 20241001 --end-date 20241031 --states SP
```

### Setup New Database
```bash
python setup/complete_db_setup_lacre.py
```

## 📝 Notes

### Symlinks
- Both `lacre` and `medical` modules use symlinks to shared components (`pncp_api.py` and `notion_integration.py`)
- This avoids code duplication while keeping modules organized
- Symlinks work on Unix-like systems (macOS, Linux)

### Module Organization
- Each system (`lacre`/`medical`) is self-contained with its own config and logic
- Shared utilities are in root or `/src/` and linked via symlinks
- Setup scripts are separated for cleaner project structure
- Logs are automatically created in `/logs/` directory

### Future Improvements
- Consider moving `pncp_api.py` to `/src/shared/` or `/src/common/`
- Add `.gitignore` for `logs/`, `*.pyc`, `__pycache__/`, etc.
- Consider adding a `requirements.txt` or `pyproject.toml` in root

## 🔧 Development

When adding new scripts:
- **Core application code** → `/src/lacre/` or `/src/medical/`
- **Setup/migration scripts** → `/setup/`
- **Documentation** → `/docs/`
- **Shared utilities** → `/src/` or root level
- **Deprecated code** → `/backup/`

---

**Last Updated:** November 4, 2024
**Project:** PNCP Tender Monitoring System (Seal)
