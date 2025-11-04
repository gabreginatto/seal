# Lacre (Security Seals) Tender Monitoring System

## Overview
A parallel system to monitor **ongoing lacre (security seal) tenders** from Brazil's PNCP, using the same GCP Cloud SQL instance but with a separate database (`pncp_lacre_data`) alongside the medical database.

## Key Differences from Medical System
- **Data Source**: Queries for **ongoing tenders** (status = "Em andamento", "Aberta", etc.) instead of completed tenders
- **Classification**: Filters for lacre products instead of medical supplies
- **Database**: Uses `pncp_lacre_data` database in the same Cloud SQL instance
- **Keywords**: Comprehensive lacre-specific keyword matching

## Lacre Keywords Covered
### Types
- lacre de segurança
- lacre inviolável
- lacre antifraude
- lacre numerado
- lacre sequencial
- etiqueta void

### Materials
- Plástico, metálico, aço
- Nylon, polipropileno (PP), PEAD

### Applications
- Hidrômetro / Medidor de água
- Medidor de energia
- Medidor de gás
- Pulseira com lacre inviolável
- Envelope com lacre de segurança

## Files Created

### Core Configuration
1. **config_lacre.py** - Lacre-specific configuration with all keywords and enums
2. **classifier_lacre.py** - Lacre tender classification with ongoing status detection
3. **database_lacre.py** - Database wrapper pointing to `pncp_lacre_data`

### API & Discovery
4. **pncp_api.py** (modified) - Added `get_ongoing_tenders_by_status()` and `filter_ongoing_tenders()` methods
5. **tender_discovery_lacre.py** - Discovery engine for ongoing lacre tenders

### Processing & Tracking
6. **processed_lacre_tenders_tracker.py** - Separate tracker for lacre tenders (saves to `processed_lacre_tenders.json`)
7. **main_lacre.py** - Main orchestration module for lacre processing

### Setup
8. **complete_db_setup_lacre.py** - Database initialization script
9. **.env.example** (updated) - Added lacre configuration variables

## Setup Instructions

### 1. Environment Configuration
Update your `.env` file with lacre configuration:
```bash
# Existing variables (shared)
GOOGLE_CLOUD_PROJECT=medical-473219
CLOUD_SQL_REGION=us-central1
CLOUD_SQL_INSTANCE=pncp-medical-db
PNCP_USERNAME=your_username
PNCP_PASSWORD=your_password

# Lacre-specific (new)
LACRE_DATABASE_NAME=pncp_lacre_data
LACRE_CATALOG_CSV=/path/to/lacre_catalog.csv
```

### 2. Create Lacre Database
**IMPORTANT**: This creates a NEW database in your existing Cloud SQL instance

#### Option A: Manual Creation (Recommended)
```bash
# Connect to your Cloud SQL instance
gcloud sql connect pncp-medical-db --user=postgres --database=postgres

# In psql, create the database
CREATE DATABASE pncp_lacre_data;
\q
```

#### Option B: Using Setup Script
```bash
# Run the automated setup
python complete_db_setup_lacre.py
```

This will:
- Create `pncp_lacre_data` database in your existing instance
- Initialize the schema (identical structure to medical)
- Create all necessary tables and indexes
- Test the connection

### 3. Verify Database Setup
```bash
# List databases in your Cloud SQL instance
gcloud sql databases list --instance=pncp-medical-db

# You should see both:
# - pncp_medical_data (existing)
# - pncp_lacre_data (new)
```

### 4. Run Lacre Discovery
```bash
# Discover ongoing lacre tenders for the last 30 days
python main_lacre.py --start-date 20250101 --end-date 20250131 --states SP RJ

# Discovery only (no item processing)
python main_lacre.py --start-date 20250101 --end-date 20250131 --discovery-only

# Specific states
python main_lacre.py --start-date 20250101 --end-date 20250131 --states SP MG BA
```

## Architecture

```
Same GCP Project & Cloud SQL Instance
├── pncp_medical_data (existing)
│   ├── Completed medical tenders
│   └── Fernandes product matching
│
└── pncp_lacre_data (new)
    ├── Ongoing lacre tenders
    └── Lacre product matching

Shared Resources:
- PNCP API client
- Cloud SQL instance
- IAM authentication
- Base database schema
```

## Key Features

### 1. Ongoing Tender Detection
The system filters for ongoing tenders using:
- Status keywords: "aberta", "em andamento", "publicada", "vigente"
- Excludes completed: "homologada", "concluída", "cancelada", "deserta"
- Date-based inference (has publication date but no homologation date)

### 2. Comprehensive Lacre Classification
Classifies tenders by:
- **Lacre Type**: security, tamper_evident, anti_fraud, numbered, personalized, void_label
- **Material**: plastic, metal, steel, nylon, polypropylene, HDPE
- **Application**: water_meter, energy_meter, gas_meter, envelope, wristband

### 3. Separate Tracking
- Uses `processed_lacre_tenders.json` (separate from medical)
- Prevents duplicate processing
- Tracks ongoing vs completed status

### 4. Same Schema Structure
Both databases use identical schemas for easy comparison and reporting:
- organizations
- tenders
- tender_items
- matched_products
- homologated_results
- processing_log

## Testing

### Test Configuration
```bash
# Test the lacre classifier
python classifier_lacre.py

# Test database connection
python database_lacre.py

# Test tender discovery
python tender_discovery_lacre.py
```

### Test Main Workflow
```bash
# Run in test mode
python main_lacre.py --test

# Run demo mode
python main_lacre.py --demo
```

## Example Usage

### Discover Ongoing Lacre Tenders in São Paulo
```bash
python main_lacre.py \
  --start-date 20250101 \
  --end-date 20250131 \
  --states SP \
  --chunk-days 7
```

### Output Example
```
=== LACRE TENDER DISCOVERY STATISTICS ===
Total Tenders Found: 145
Lacre Relevant: 87
Ongoing Tenders: 65
Processing Time: 45.3 seconds

--- By State ---
São Paulo (SP): 145

--- By Government Level ---
Municipal: 52
State: 25
Federal: 10

--- By Lacre Type ---
Security: 35
Tamper_evident: 28
Numbered: 15

--- By Application ---
Water_meter: 45
Energy_meter: 30
General: 12
```

## Database Queries

### Check Lacre Database
```sql
-- Connect to lacre database
\c pncp_lacre_data

-- Count ongoing tenders
SELECT COUNT(*) FROM tenders WHERE status IN ('Em andamento', 'Aberta');

-- Tenders by application (from description)
SELECT state_code, COUNT(*)
FROM tenders
WHERE description ILIKE '%hidrômetro%'
GROUP BY state_code;

-- High-value ongoing lacre tenders
SELECT title, total_estimated_value, state_code, status
FROM tenders
WHERE total_estimated_value > 50000
ORDER BY total_estimated_value DESC
LIMIT 10;
```

## Maintenance

### View Processed Tenders
```python
from processed_lacre_tenders_tracker import get_processed_lacre_tenders_tracker

tracker = get_processed_lacre_tenders_tracker()
tracker.print_stats()
```

### Clear Tracker (Use with Caution)
```python
tracker = get_processed_lacre_tenders_tracker()
tracker.clear_all()
tracker.save_to_file()
```

## Important Notes

⚠️ **Database Safety**
- The lacre system creates a **NEW database** (`pncp_lacre_data`)
- Your existing medical database (`pncp_medical_data`) is **NOT touched**
- Both databases coexist in the same Cloud SQL instance
- No risk of data contamination

⚠️ **Ongoing vs Completed**
- Lacre system focuses on **ongoing tenders** (not yet completed)
- Medical system processes **completed tenders** (with homologated prices)
- Different use cases, different data targets

⚠️ **Manual Approval Required**
- Database creation requires manual confirmation
- Schema initialization is automatic but can be re-run safely
- Always verify before running in production

## Troubleshooting

### Database Not Found
```bash
# Manually create the database
gcloud sql databases create pncp_lacre_data --instance=pncp-medical-db
```

### Connection Failed
```bash
# Check if database exists
gcloud sql databases list --instance=pncp-medical-db

# Verify IAM permissions
gcloud projects get-iam-policy medical-473219
```

### No Ongoing Tenders Found
- Check date range (use recent dates for ongoing tenders)
- Verify state codes
- Lower `min_match_score` threshold in config
- Check PNCP API status

## Logs
- Main log: `pncp_lacre_processing.log`
- Tracker file: `processed_lacre_tenders.json`
- Reports: `pncp_lacre_report_YYYYMMDD_HHMMSS.json`

## Support
For issues:
1. Check logs in `pncp_lacre_processing.log`
2. Verify database exists in Cloud SQL
3. Test API connection
4. Review environment variables

---

**Built for ongoing lacre tender monitoring in Brazilian government procurement** 🔐🇧🇷

Last updated: January 2025
