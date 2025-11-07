# Mercado Eletronico Integration Plan

> Step-by-step plan to integrate ME API with existing Seal discovery system

## Executive Summary

Mercado Eletronico (ME) is a B2B procurement marketplace focused on **private companies**, complementing our existing PNCP system which covers **public sector** tenders. This integration will enable comprehensive market intelligence across both sectors.

## Current State: PNCP System

### What We Have
- ✅ Fully functional PNCP API client (`src/pncp_api.py`)
- ✅ Complete discovery pipeline for lacre tenders
- ✅ PostgreSQL database with Cloud SQL
- ✅ Keyword-based classification system
- ✅ Multi-stage processing (fetch → filter → analyze → store)
- ✅ Homologated values extraction
- ✅ Rate limiting and error handling

### Data Flow
```
PNCP API → Tenders → Items → Database (pncp_lacre_data)
```

## Target State: Unified System

### What We'll Build
```
┌─────────────────────────────────────────────────────┐
│                  Seal Platform                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐          ┌──────────────┐       │
│  │  PNCP API    │          │   ME API     │       │
│  │  (Public)    │          │  (Private)   │       │
│  └──────┬───────┘          └──────┬───────┘       │
│         │                         │                │
│         │  Tenders                │  Pre-Orders    │
│         │                         │                │
│         └────────┬────────────────┘                │
│                  │                                  │
│         ┌────────▼────────┐                        │
│         │  Unified DB     │                        │
│         │  - Tenders      │                        │
│         │  - Pre-Orders   │                        │
│         │  - Items        │                        │
│         │  - Companies    │                        │
│         └─────────────────┘                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Phase 1: Research & Setup (CURRENT)

### ✅ Completed
- [x] Explored ME API SDK (C#)
- [x] Identified key endpoints
- [x] Mapped data structure
- [x] Created documentation (README, API_ENDPOINTS)
- [x] Created folder structure

### 🎯 Immediate Next Steps
1. **Obtain ME API Credentials**
   - Register at https://developer.me.com.br/
   - Request ClientId and ClientSecret
   - Get sandbox/test environment access

2. **Test ME API**
   - Authenticate with OAuth 2.0
   - Fetch sample pre-orders
   - Verify response structure
   - Test rate limits

## Phase 2: Python API Client (Week 1-2)

### Create `me_api.py`

Similar to `pncp_api.py` structure:

```python
class MEApiClient:
    """ME API client with OAuth 2.0 and rate limiting"""

    def __init__(self, client_id: str, client_secret: str):
        self.base_url = "https://api.mercadoe.com"
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None
        self.rate_limiter = RateLimiter(max_per_minute=60)

    async def authenticate(self) -> bool:
        """OAuth 2.0 authentication"""
        # POST /api/meweb-auth-api/v1/auth/tokens
        pass

    async def get_pre_orders(self, **filters) -> Tuple[int, Dict]:
        """List pre-orders with pagination"""
        pass

    async def get_pre_order_details(self, pre_order_id: str) -> Tuple[int, Dict]:
        """Get full pre-order with items"""
        pass
```

### Key Features
- OAuth 2.0 token management (refresh before expiry)
- Rate limiting (start with 60/min, adjust based on testing)
- Async operations (aiohttp)
- Error handling (401, 429, 404)
- Retry logic with exponential backoff

### Testing
```python
# Test authentication
client = MEApiClient(client_id, client_secret)
authenticated = await client.authenticate()

# Test pre-order listing
status, response = await client.get_pre_orders(status="open", page_size=10)

# Test pre-order details
status, pre_order = await client.get_pre_order_details("pre_order_123")
```

## Phase 3: Database Schema (Week 2-3)

### New Tables for ME Data

#### `me_organizations`
```sql
CREATE TABLE me_organizations (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) UNIQUE NOT NULL,
    cnpj VARCHAR(14) UNIQUE,
    name TEXT NOT NULL,
    sector TEXT,
    state VARCHAR(2),
    city TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    verified BOOLEAN DEFAULT FALSE,
    registration_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `me_pre_orders`
```sql
CREATE TABLE me_pre_orders (
    id SERIAL PRIMARY KEY,
    pre_order_id VARCHAR(255) UNIQUE NOT NULL,
    organization_id INTEGER REFERENCES me_organizations(id),
    title TEXT,
    description TEXT,
    status TEXT,  -- open, closed, awarded
    created_date TIMESTAMPTZ,
    deadline TIMESTAMPTZ,
    estimated_total_value NUMERIC(15,2),
    awarded_value NUMERIC(15,2),
    winner_supplier_id VARCHAR(255),
    winner_supplier_name TEXT,
    winner_supplier_cnpj VARCHAR(14),
    award_date TIMESTAMPTZ,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `me_pre_order_items`
```sql
CREATE TABLE me_pre_order_items (
    id SERIAL PRIMARY KEY,
    pre_order_id INTEGER REFERENCES me_pre_orders(id),
    item_number INTEGER,
    description TEXT,
    quantity NUMERIC(15,3),
    unit VARCHAR(50),
    estimated_unit_value NUMERIC(15,2),
    estimated_total_value NUMERIC(15,2),
    category TEXT,
    specifications TEXT,
    technical_requirements TEXT,
    is_lacre BOOLEAN DEFAULT FALSE,  -- Classification
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pre_order_id, item_number)
);
```

### Unified View

Create a view combining PNCP and ME data:

```sql
CREATE VIEW vw_all_lacre_opportunities AS
SELECT
    'PNCP' as source,
    t.control_number as opportunity_id,
    o.name as organization_name,
    o.cnpj,
    o.state,
    t.publication_date as created_date,
    ti.description,
    ti.quantity,
    ti.unit,
    ti.estimated_unit_value,
    ti.homologated_unit_value as awarded_unit_value,
    ti.winner_name,
    ti.winner_cnpj
FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.is_lacre = TRUE

UNION ALL

SELECT
    'ME' as source,
    po.pre_order_id as opportunity_id,
    org.name as organization_name,
    org.cnpj,
    org.state,
    po.created_date,
    poi.description,
    poi.quantity,
    poi.unit,
    poi.estimated_unit_value,
    NULL as awarded_unit_value,  -- ME may not have this
    po.winner_supplier_name as winner_name,
    po.winner_supplier_cnpj as winner_cnpj
FROM me_pre_order_items poi
JOIN me_pre_orders po ON poi.pre_order_id = po.id
JOIN me_organizations org ON po.organization_id = org.id
WHERE poi.is_lacre = TRUE;
```

## Phase 4: Configuration (Week 3)

### Create `config_me.py`

```python
from dataclasses import dataclass
from typing import List, Set

# Reuse lacre keywords from PNCP config
from src.lacre.config_lacre import LACRE_KEYWORDS

@dataclass
class MEProcessingConfig:
    """ME-specific configuration"""
    enabled_categories: List[str] = None  # ME uses categories instead of states
    min_pre_order_value: float = 1_000.0
    allowed_statuses: List[str] = None  # open, closed, awarded
    fetch_awarded: bool = True  # Include awarded to get winner info

    def __post_init__(self):
        if self.enabled_categories is None:
            self.enabled_categories = [
                'Security & Safety',
                'Medical Supplies',
                'Healthcare Equipment'
            ]
        if self.allowed_statuses is None:
            self.allowed_statuses = ['open', 'awarded']

# Reuse same keyword sets
ME_LACRE_KEYWORDS = LACRE_KEYWORDS
```

## Phase 5: Discovery Engine (Week 4-5)

### Create `optimized_me_discovery.py`

Port the PNCP discovery logic with ME-specific adaptations:

```python
class OptimizedMEDiscovery:
    """ME pre-order discovery engine"""

    async def run_discovery(
        self,
        date_from: str,
        date_to: str,
        categories: List[str] = None
    ):
        """
        Main discovery pipeline:
        1. Bulk fetch pre-orders
        2. Quick filter (keywords)
        3. Full fetch (items)
        4. Classify items
        5. Save to database
        """

        # Stage 1: Bulk fetch
        pre_orders = await self._fetch_pre_orders_bulk(date_from, date_to)

        # Stage 2: Quick filter
        filtered = await self._quick_filter(pre_orders)

        # Stage 3: Full fetch + classify
        for pre_order_id in filtered:
            details = await self.api_client.get_pre_order_details(pre_order_id)

            # Classify items
            for item in details['items']:
                item['is_lacre'] = self._is_lacre_item(item['description'])

            # Stage 4: Save
            await self._save_to_db(details)
```

### Key Differences from PNCP
- **No geographic filtering**: Companies are nationwide
- **Category-based filtering**: Instead of modality codes
- **OAuth required**: Must handle token refresh
- **Different structure**: Pre-orders vs tenders
- **Private companies**: CNPJ instead of government organs

## Phase 6: Database Operations (Week 5)

### Create `database_me.py`

```python
class MEDatabase:
    """Database operations for ME data"""

    async def save_organization(self, org_data: Dict) -> int:
        """Save or update ME organization"""
        pass

    async def save_pre_order(self, pre_order_data: Dict) -> int:
        """Save pre-order with items"""
        pass

    async def check_pre_order_exists(self, pre_order_id: str) -> bool:
        """Deduplication check"""
        pass

    async def get_lacre_statistics(self) -> Dict:
        """Get ME lacre statistics"""
        pass
```

## Phase 7: Main Entry Point (Week 6)

### Create `main_me.py`

```python
async def main():
    """Main ME discovery entry point"""

    # Parse arguments
    args = parse_args()

    # Initialize
    api_client = MEApiClient(client_id, client_secret)
    db = MEDatabase(db_pool)
    discovery = OptimizedMEDiscovery(api_client, db)

    # Run discovery
    await discovery.run_discovery(
        date_from=args.start_date,
        date_to=args.end_date,
        categories=args.categories
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Usage
```bash
python src/mercado_eletronico/main_me.py \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --categories "Security & Safety" "Healthcare"
```

## Phase 8: Integration & Testing (Week 7-8)

### Create Execution Script

```bash
# run_me_discovery.sh
#!/bin/bash
export PYTHONPATH="/Users/gabrielreginatto/Desktop/Code/Seal:$PYTHONPATH"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/pncp-key.json"

python src/mercado_eletronico/main_me.py "$@"
```

### Unified Execution

```bash
# Run both systems
./run_lacre_discovery.sh --start-date 20240101 --end-date 20241231 --states SP
./run_me_discovery.sh --start-date 2024-01-01 --end-date 2024-12-31
```

### Testing Checklist
- [ ] Authentication works
- [ ] Pre-order fetching works
- [ ] Pagination works correctly
- [ ] Keyword filtering identifies lacre items
- [ ] Database saves correctly
- [ ] Deduplication prevents duplicates
- [ ] Rate limiting prevents 429 errors
- [ ] Error handling recovers gracefully
- [ ] Unified view returns both sources

## Phase 9: Analytics & Reporting (Week 9+)

### Create Combined Analytics

```python
# Query unified view
SELECT
    source,
    COUNT(*) as opportunities,
    SUM(quantity) as total_quantity,
    AVG(estimated_unit_value) as avg_unit_price,
    COUNT(DISTINCT organization_name) as unique_organizations
FROM vw_all_lacre_opportunities
GROUP BY source;
```

### Market Intelligence Reports
- Compare public vs private sector pricing
- Identify top buyers (both sectors)
- Track market trends over time
- Winner analysis across both platforms

## Success Metrics

### Technical
- [ ] 100% API authentication success rate
- [ ] < 1% failed requests (excluding rate limits)
- [ ] < 5 seconds average pre-order fetch time
- [ ] 95%+ keyword matching accuracy

### Business
- [ ] Discover 50+ ME lacre opportunities per month
- [ ] Cover 100+ private companies
- [ ] Identify pricing trends across sectors
- [ ] Enable comprehensive market analysis

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1. Research & Setup | 1 week | ✅ In Progress |
| 2. API Client | 1-2 weeks | ⏳ Pending |
| 3. Database Schema | 1 week | ⏳ Pending |
| 4. Configuration | 1 week | ⏳ Pending |
| 5. Discovery Engine | 2 weeks | ⏳ Pending |
| 6. Database Ops | 1 week | ⏳ Pending |
| 7. Main Entry Point | 1 week | ⏳ Pending |
| 8. Integration & Testing | 2 weeks | ⏳ Pending |
| 9. Analytics | Ongoing | ⏳ Pending |

**Estimated Total**: 8-10 weeks

## Dependencies

### Required
- ME API credentials (ClientId, ClientSecret)
- Same PostgreSQL database (new tables)
- Same Google Cloud SQL access
- Python dependencies: aiohttp, asyncpg, etc.

### Optional
- Notion integration for ME opportunities
- Separate dashboard for private sector
- Email alerts for high-value opportunities

## Risks & Mitigations

### Risk 1: API Access
**Issue**: May not get ME API credentials
**Mitigation**: Contact ME sales team, explain research/academic purpose

### Risk 2: Rate Limits
**Issue**: Unknown rate limits may slow discovery
**Mitigation**: Start conservative (60/min), monitor, adjust

### Risk 3: Data Structure Changes
**Issue**: API response may differ from SDK docs
**Mitigation**: Build flexible parsers, comprehensive error handling

### Risk 4: OAuth Complexity
**Issue**: Token refresh and management
**Mitigation**: Robust token management, auto-refresh before expiry

## Next Immediate Actions

1. **Register for ME API** (Gabriel)
   - Visit https://developer.me.com.br/
   - Sign up for developer access
   - Request API credentials

2. **Test Authentication** (Week 1)
   - Build minimal OAuth 2.0 client
   - Test token generation
   - Verify token refresh

3. **Explore API** (Week 1)
   - Fetch 10 sample pre-orders
   - Analyze response structure
   - Verify data matches docs

4. **Start Building** (Week 2+)
   - Create `me_api.py`
   - Create database schema
   - Begin discovery engine

---

**Created**: November 6, 2025
**Last Updated**: November 6, 2025
**Status**: Phase 1 - Research Complete ✅
