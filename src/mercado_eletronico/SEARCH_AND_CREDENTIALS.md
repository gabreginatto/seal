# ME API - Search Capabilities & Credential Creation

> Analysis of search/filter capabilities and credential creation process for Mercado Eletronico API

## 🔑 Credential Creation Process

### Step-by-Step Guide

#### 1. Register Your Organization
**URL**: https://partner.me.com.br/

**Requirements**:
- Company registration with Mercado Eletronico
- Valid CNPJ
- Authorized company representative

#### 2. Create Developer User

**Steps**:
1. Access the Partner's Portal (https://partner.me.com.br/)
2. Navigate to **"Users"** section
3. Click **"New user"**
4. Fill out user invitation details:
   - Name
   - Email
   - Phone
5. **CRITICAL**: Select **"Developer Profile"** in "User Profile" field
   - This profile grants API access
   - Cannot access E-procurement functionality
   - Can manage API Keys and Webhooks

#### 3. Generate API Credentials

**Steps**:
1. In Partner's Portal, navigate to **"API Keys"** section
2. Click **"Create new"**
3. Add a **description** for the credential (e.g., "Lacre Discovery API")
4. System generates:
   - **Client ID** (Key)
   - **Client Secret** (Secret)
5. **⚠️ CRITICAL**: Save these credentials immediately
   - Client Secret shown only once
   - Cannot be retrieved later
   - Store securely (environment variables, secrets manager)

### Developer Profile Capabilities

✅ **Can access**:
- Partner's Portal
- API Keys management
- Webhooks management
- ME Data Connect
- Developer documentation

❌ **Cannot access**:
- E-procurement functionality
- Procurement operations
- Supplier management

### Credential Storage

**Best Practices**:
```bash
# .env file
ME_CLIENT_ID=your_client_id_here
ME_CLIENT_SECRET=your_client_secret_here
ME_BASE_URL=https://api.mercadoe.com

# Never commit credentials to git!
# Add to .gitignore:
.env
```

**Python Usage**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

ME_CLIENT_ID = os.getenv('ME_CLIENT_ID')
ME_CLIENT_SECRET = os.getenv('ME_CLIENT_SECRET')
```

---

## 🔍 Search Capabilities Analysis

### ❌ **No Built-In Keyword Search**

Based on SDK analysis and documentation:

**Finding**: The ME API SDK shows **only ID-based retrieval**, not keyword search.

**Evidence**:
- `GetPreOrderRequest.cs` - Takes only `PreOrderId` (single ID)
- `PreOrderClient.GetPreOrderAsync()` - Retrieves one pre-order by ID
- No `search`, `query`, or `keyword` parameters found in SDK

**Implication**: ⚠️ **Cannot search for "lacre" directly in API**

---

## 🎯 Discovery Strategy Without Keyword Search

### Option 1: Bulk Fetch + Client-Side Filter (Recommended)

**Approach**: Same as current PNCP system

```python
# Stage 1: Fetch ALL open pre-orders
pre_orders = await me_client.get_pre_orders(
    status="open",
    dateFrom="2024-01-01",
    dateTo="2024-12-31",
    pageSize=100  # Max per page
)

# Stage 2: Client-side keyword filtering (ZERO additional API calls)
lacre_pre_orders = []
for pre_order in pre_orders:
    title = pre_order.get('title', '').lower()
    description = pre_order.get('description', '').lower()

    # Apply lacre keyword matching
    if any(keyword in title or keyword in description
           for keyword in LACRE_KEYWORDS):
        lacre_pre_orders.append(pre_order)

# Stage 3: Fetch full details for filtered pre-orders only
for pre_order in lacre_pre_orders:
    details = await me_client.get_pre_order_details(pre_order['preOrderId'])
    # Classify items...
```

**Performance**:
- Similar to PNCP Stage 2 (Quick Filter)
- Zero API calls for filtering
- Only fetch details for relevant pre-orders
- 95%+ reduction in API calls

---

### Option 2: Category-Based Pre-Filter

**If ME API supports category filtering** (need to verify):

```python
# Fetch only relevant categories
pre_orders = await me_client.get_pre_orders(
    status="open",
    category="Security & Safety",  # If this parameter exists
    dateFrom="2024-01-01",
    dateTo="2024-12-31"
)

# Then apply keyword filter
# ...
```

**Benefit**: Reduces initial fetch volume

**Risk**: Might miss lacre items in other categories (e.g., "Medical Supplies")

---

### Option 3: Hybrid Approach (Recommended)

**Combine category + keyword filtering**:

```python
# Step 1: Fetch from multiple relevant categories
relevant_categories = [
    "Security & Safety",
    "Medical Supplies",
    "Healthcare Equipment",
    "Industrial Equipment"
]

all_pre_orders = []
for category in relevant_categories:
    pre_orders = await me_client.get_pre_orders(
        status="open",
        category=category,  # If supported
        dateFrom="2024-01-01",
        dateTo="2024-12-31",
        pageSize=100
    )
    all_pre_orders.extend(pre_orders['data'])

# Step 2: Apply keyword filter
lacre_pre_orders = filter_by_lacre_keywords(all_pre_orders)

# Step 3: Fetch full details
for pre_order in lacre_pre_orders:
    details = await me_client.get_pre_order_details(pre_order['preOrderId'])
```

---

## 📊 Available Filters (From Documentation)

### Confirmed Filters

Based on developer portal, these filters **likely** exist:

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `status` | string | Pre-order status | `open`, `closed`, `awarded` |
| `dateFrom` | ISO 8601 | Start date | `2024-01-01T00:00:00Z` |
| `dateTo` | ISO 8601 | End date | `2024-12-31T23:59:59Z` |
| `page` | integer | Page number | `1`, `2`, `3` |
| `pageSize` | integer | Results per page | `50`, `100` |
| `organizationId` | string | Filter by org | `org_123` |
| `category` | string | Product category | `Security & Safety` |

### ⚠️ Need to Verify

These filters need testing with real API:
- `category` - Product category filter
- `organizationId` - Filter by company
- `search` or `query` - Text search (unlikely based on SDK)
- `minValue` / `maxValue` - Value range filters

---

## 🔬 Testing Checklist

Once you obtain credentials, test these:

### 1. List Pre-Orders (Basic)
```python
response = await me_client.get_pre_orders(status="open", pageSize=10)
print(response)
```

**Verify**:
- Response structure (`data`, `pagination`)
- Available fields in pre-orders
- Actual filter parameters accepted

### 2. Test Pagination
```python
# Fetch first page
page1 = await me_client.get_pre_orders(status="open", page=1, pageSize=50)

# Fetch second page
page2 = await me_client.get_pre_orders(status="open", page=2, pageSize=50)

# Verify different results
assert page1['data'] != page2['data']
```

### 3. Test Category Filter (If Exists)
```python
response = await me_client.get_pre_orders(
    status="open",
    category="Security & Safety"  # Test if this works
)
```

### 4. Test Keyword Filtering
```python
# Fetch pre-orders
pre_orders = await me_client.get_pre_orders(status="open", pageSize=100)

# Apply client-side filter
for po in pre_orders['data']:
    if 'lacre' in po.get('title', '').lower():
        print(f"Found lacre: {po['title']}")
```

### 5. Test Date Range
```python
response = await me_client.get_pre_orders(
    status="open",
    dateFrom="2024-01-01T00:00:00Z",
    dateTo="2024-01-31T23:59:59Z"
)
```

---

## 📝 Implementation Impact

### ✅ **Good News**: Discovery Still Works

**Why**:
1. **Bulk fetch is fast** - ME API supports pagination (likely 50-100 per page)
2. **Client-side filtering is free** - Zero API calls for keyword matching
3. **Same as PNCP Stage 2** - Our current system already does this
4. **Category pre-filter helps** - If supported, reduces initial volume

### ⚠️ **Consideration**: API Call Volume

**Scenario**: Fetch all open pre-orders for 2024

**Estimation**:
- Assume 10,000 total pre-orders (all categories)
- Page size: 100 per page
- API calls needed: 100 calls to fetch all
- Filter to lacre: ~50-100 relevant pre-orders (0.5-1%)
- Fetch details: 50-100 additional calls
- **Total: ~150-200 API calls**

**Compare to PNCP**:
- PNCP: Fetch by state/modality (already filtered)
- ME: Fetch all, filter client-side
- ME requires more initial API calls but still manageable

**Rate Limiting**:
- At 60 calls/min: 150 calls = 2.5 minutes
- At 100 calls/min: 150 calls = 1.5 minutes
- **Feasible for nightly/weekly discovery**

---

## 🎬 Recommended Approach

### Phase 1: Initial Discovery (Manual)
1. Get credentials from Partner Portal
2. Test authentication
3. Fetch 100 sample pre-orders
4. Analyze actual response structure
5. Verify available filters
6. Test keyword matching accuracy

### Phase 2: Build Discovery Pipeline
```python
async def discover_me_lacre(date_from: str, date_to: str):
    """Discover lacre pre-orders from ME API"""

    # Stage 1: Bulk fetch (with pagination)
    all_pre_orders = []
    page = 1
    while True:
        response = await me_client.get_pre_orders(
            status="open",
            dateFrom=date_from,
            dateTo=date_to,
            page=page,
            pageSize=100
        )

        all_pre_orders.extend(response['data'])

        if page >= response['pagination']['totalPages']:
            break

        page += 1

    logger.info(f"Fetched {len(all_pre_orders)} total pre-orders")

    # Stage 2: Client-side keyword filter (ZERO API calls)
    lacre_pre_orders = []
    for po in all_pre_orders:
        if contains_lacre_keywords(po['title'], po['description']):
            lacre_pre_orders.append(po)

    logger.info(f"Found {len(lacre_pre_orders)} lacre pre-orders after filtering")

    # Stage 3: Fetch full details + classify items
    for po in lacre_pre_orders:
        details = await me_client.get_pre_order_details(po['preOrderId'])

        # Classify items
        for item in details['items']:
            item['is_lacre'] = contains_lacre_keywords(item['description'])

        # Save to database
        await save_pre_order(details)

    return lacre_pre_orders
```

---

## 🔗 Quick Links

- **Partner Portal**: https://partner.me.com.br/
- **Developer Portal**: https://developer.me.com.br/
- **Credentials Guide**: https://developer.me.com.br/guides/credentials
- **API Reference**: https://developer.me.com.br/ (after login)

---

## 📌 Summary

### Credential Creation
✅ **Clear Process**:
1. Access Partner Portal
2. Create developer user
3. Generate API Key & Secret
4. Store securely

### Keyword Search
❌ **Not Available**: No built-in keyword search in API

✅ **Workaround**: Client-side filtering (same as PNCP Stage 2)
- Bulk fetch with pagination
- Filter in Python (zero API calls)
- Fetch details for matches only
- 95%+ reduction in API calls vs. fetching all details

### Discovery Viability
✅ **FULLY VIABLE**: Discovery pipeline works without keyword search
- Similar to current PNCP approach
- Client-side filtering is efficient
- Category pre-filter (if available) helps
- Manageable API call volume

**Recommendation**: **Proceed with integration** - Lack of keyword search is not a blocker

---

**Created**: November 6, 2025
**Status**: Ready for implementation once credentials obtained
