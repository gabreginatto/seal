# Mercado Eletronico API Integration

> Python client for Mercado Eletronico API - Discovery system for private company procurement opportunities

## Overview

Mercado Eletronico is a B2B marketplace platform that connects companies for procurement opportunities. Unlike PNCP (public tenders), this API focuses on **private company procurement**.

**Reference SDK**: [me-api-sdk](https://github.com/mercadoeletronico/me-api-sdk) (C#)
**API Documentation**: https://developer.me.com.br/

## Key Concepts

### Business Opportunity Types

1. **Pre-Orders** - Procurement requests from companies looking for suppliers
2. **Quotations** - Price quotes submitted by suppliers
3. **Requests** - General procurement requests
4. **Pre-Requests** - Early-stage procurement inquiries

### Comparison: ME vs PNCP

| Aspect | PNCP | Mercado Eletronico |
|--------|------|-------------------|
| **Sector** | Public (Government) | Private (Companies) |
| **Access** | Public API | OAuth 2.0 Required |
| **Data Structure** | Tenders → Items | Pre-Orders → Items |
| **Discovery** | By date/state/modality | By filters/categories |
| **Rate Limits** | 60/min | TBD |
| **Auth** | Optional (public) | Required (OAuth 2.0) |

## API Structure

### Base URL
```
https://api.mercadoe.com
```

### Authentication
```
POST /api/meweb-auth-api/v1/auth/tokens
```

OAuth 2.0 with ClientId and ClientSecret

### Main Endpoints

#### Pre-Orders API
```
GET /api/me-integration-pre-order/v1/pre-orders
GET /api/me-integration-pre-order/v1/pre-orders/{preorderid}
```

#### Quotations API
```
GET /api/me-integration-quotation/v1/quotations
GET /api/me-integration-quotation/v1/quotations/{quotationid}
```

#### Requests API
```
GET /api/me-integration-request/v1/requests
GET /api/me-integration-request/v1/requests/{requestid}
```

## Available API Clients (from C# SDK)

1. **AuthClient** - OAuth 2.0 authentication
2. **PreOrderClient** - Pre-order discovery and retrieval
3. **DecisionTableClient** - Business logic and rules
4. **PreRequestClient** - Early-stage requests
5. **BillsClient** - Billing information
6. **InvoiceClient** - Invoice management
7. **UserClient** - User management
8. **LedgerClient** - Financial ledger

## Data Models

### Pre-Order Structure (Expected)
```python
{
    "preorder_id": str,
    "organization": {
        "name": str,
        "cnpj": str,  # Company tax ID
        "sector": str
    },
    "items": [
        {
            "item_number": int,
            "description": str,
            "quantity": float,
            "unit": str,
            "estimated_value": float,
            "category": str,
            "specifications": str
        }
    ],
    "status": str,
    "created_date": datetime,
    "deadline": datetime
}
```

### Key Fields to Extract

**Organization Data**:
- Company name
- CNPJ (Brazilian company tax ID)
- Business sector
- Location

**Item Data**:
- Product description
- Quantity and unit
- Estimated/target price
- Technical specifications
- Category/classification

**Opportunity Data**:
- Request ID
- Status (open, closed, awarded)
- Creation date
- Response deadline
- Winner information (if awarded)

## Discovery Strategy

### Similar to PNCP Pipeline

1. **Stage 1: Bulk Fetch**
   - Fetch pre-orders/requests using filters
   - Handle pagination
   - Apply date range filters

2. **Stage 2: Quick Filter**
   - Keyword-based filtering (lacre keywords)
   - Check for relevant categories
   - Database deduplication

3. **Stage 3: Item Analysis**
   - Fetch full pre-order details
   - Analyze item descriptions
   - Classify products (lacre vs other)

4. **Stage 4: Database Storage**
   - Store organizations (companies)
   - Store pre-orders (equivalent to tenders)
   - Store items with classifications

### Key Differences from PNCP

- **Authentication Required**: Must implement OAuth 2.0 flow
- **Private Data**: Company information, not public records
- **Different Structure**: Pre-orders instead of tenders
- **Unknown Rate Limits**: Need to test and implement throttling
- **No Geographic Filtering**: Companies are nationwide/international

## Implementation Plan

### Phase 1: API Client
- [ ] Implement OAuth 2.0 authentication
- [ ] Create MEApiClient class (Python)
- [ ] Implement PreOrderClient
- [ ] Add rate limiting
- [ ] Test authentication and basic fetching

### Phase 2: Data Models
- [ ] Define SQLAlchemy models for ME data
- [ ] Create database schema
- [ ] Map ME structure to our database
- [ ] Add migration scripts

### Phase 3: Discovery Engine
- [ ] Port discovery pipeline from PNCP
- [ ] Adapt filtering logic for ME
- [ ] Implement pre-order fetching
- [ ] Add item classification

### Phase 4: Integration
- [ ] Unified database (PNCP + ME)
- [ ] Combined dashboard
- [ ] Cross-platform analytics

## Required Credentials

```python
ME_CLIENT_ID = "your_client_id"
ME_CLIENT_SECRET = "your_client_secret"
ME_BASE_URL = "https://api.mercadoe.com"
```

## Next Steps

1. **Obtain API Credentials**
   - Register for ME API access
   - Get ClientId and ClientSecret
   - Test authentication

2. **Explore API**
   - Test pre-order endpoint
   - Understand response format
   - Check rate limits
   - Map data structure

3. **Build Python Client**
   - Create me_api.py (like pncp_api.py)
   - Implement authentication
   - Add main endpoints

4. **Adapt Discovery System**
   - Create config_me.py
   - Create database_me.py
   - Create main_me.py
   - Port discovery logic

## Files to Create

```
src/mercado_eletronico/
├── README.md                    # This file
├── me_api.py                    # API client (like pncp_api.py)
├── config_me.py                 # Configuration and keywords
├── database_me.py               # Database operations
├── classifier_me.py             # Product classification
├── optimized_me_discovery.py   # Discovery engine
└── main_me.py                   # Main entry point
```

## References

- [ME API SDK (C#)](https://github.com/mercadoeletronico/me-api-sdk)
- [ME Developer Portal](https://developer.me.com.br/)
- [OAuth 2.0 Spec](https://oauth.net/2/)

---

**Status**: Research phase - Understanding API structure
**Created**: November 6, 2025
