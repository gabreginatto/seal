# Mercado Eletronico API Endpoints

> Complete reference of ME API endpoints for discovery system integration

## Base Information

**Base URL**: `https://api.mercadoe.com`
**Authentication**: OAuth 2.0 (Client Credentials)
**Response Format**: JSON

## Authentication

### Get Access Token

```
POST /api/meweb-auth-api/v1/auth/tokens
```

**Request Body**:
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "grant_type": "client_credentials"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Usage**:
```
Authorization: Bearer {access_token}
```

## Pre-Orders API

Pre-orders are the primary opportunity type - companies posting requests for products/services.

### List Pre-Orders

```
GET /api/me-integration-pre-order/v1/pre-orders
```

**Query Parameters**:
- `page` - Page number (default: 1)
- `pageSize` - Items per page (default: 50, max: 100)
- `status` - Filter by status: `open`, `closed`, `awarded`
- `dateFrom` - Start date (ISO 8601)
- `dateTo` - End date (ISO 8601)
- `category` - Product category filter
- `organizationId` - Filter by organization

**Response**:
```json
{
  "data": [
    {
      "preOrderId": "string",
      "organizationId": "string",
      "organization": {
        "id": "string",
        "name": "string",
        "cnpj": "string",
        "sector": "string",
        "state": "string",
        "city": "string"
      },
      "title": "string",
      "description": "string",
      "status": "open|closed|awarded",
      "createdDate": "2025-01-15T10:30:00Z",
      "deadline": "2025-02-15T18:00:00Z",
      "estimatedTotalValue": 50000.00,
      "itemCount": 5
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 50,
    "totalPages": 10,
    "totalRecords": 500
  }
}
```

### Get Pre-Order Details

```
GET /api/me-integration-pre-order/v1/pre-orders/{preorderid}
```

**Response**:
```json
{
  "preOrderId": "string",
  "organizationId": "string",
  "organization": {
    "id": "string",
    "name": "Empresa XYZ Ltda",
    "cnpj": "12345678000190",
    "sector": "Healthcare",
    "state": "SP",
    "city": "São Paulo"
  },
  "title": "Aquisição de Lacres de Segurança",
  "description": "Compra de lacres invioláveis para setor médico",
  "status": "open",
  "createdDate": "2025-01-15T10:30:00Z",
  "deadline": "2025-02-15T18:00:00Z",
  "estimatedTotalValue": 50000.00,
  "items": [
    {
      "itemNumber": 1,
      "description": "Lacre de segurança tipo âncora para sangue",
      "quantity": 10000,
      "unit": "Unidade",
      "estimatedUnitValue": 0.50,
      "estimatedTotalValue": 5000.00,
      "category": "Security Seals",
      "specifications": "Material: plástico ABS, cor vermelha...",
      "technicalRequirements": "Norma ISO 17712..."
    }
  ],
  "attachments": [
    {
      "fileName": "especificacao_tecnica.pdf",
      "url": "https://..."
    }
  ],
  "winner": {
    "supplierId": "string",
    "supplierName": "string",
    "supplierCnpj": "string",
    "awardedValue": 48000.00,
    "awardDate": "2025-02-01T14:00:00Z"
  }
}
```

## Quotations API

Quotations are supplier responses to pre-orders.

### List Quotations

```
GET /api/me-integration-quotation/v1/quotations
```

**Query Parameters**: Similar to pre-orders
- `page`
- `pageSize`
- `status`
- `preOrderId` - Filter by pre-order

**Response**:
```json
{
  "data": [
    {
      "quotationId": "string",
      "preOrderId": "string",
      "supplierId": "string",
      "supplier": {
        "name": "string",
        "cnpj": "string"
      },
      "totalValue": 48000.00,
      "status": "submitted|accepted|rejected",
      "submittedDate": "2025-01-20T15:00:00Z"
    }
  ],
  "pagination": {...}
}
```

### Get Quotation Details

```
GET /api/me-integration-quotation/v1/quotations/{quotationid}
```

## Requests API

Generic procurement requests (may be less detailed than pre-orders).

### List Requests

```
GET /api/me-integration-request/v1/requests
```

**Query Parameters**: Similar to pre-orders

### Get Request Details

```
GET /api/me-integration-request/v1/requests/{requestid}
```

## Categories/Classification

### List Product Categories

```
GET /api/me-integration/v1/categories
```

**Response**:
```json
{
  "categories": [
    {
      "id": "string",
      "name": "Security & Safety",
      "subcategories": [
        {
          "id": "string",
          "name": "Security Seals"
        }
      ]
    }
  ]
}
```

## Organizations

### Get Organization Details

```
GET /api/me-integration/v1/organizations/{organizationid}
```

**Response**:
```json
{
  "id": "string",
  "name": "Empresa XYZ Ltda",
  "cnpj": "12345678000190",
  "sector": "Healthcare",
  "state": "SP",
  "city": "São Paulo",
  "address": "...",
  "contactEmail": "contato@empresa.com",
  "contactPhone": "+55 11 98765-4321",
  "registrationDate": "2020-01-15T00:00:00Z",
  "verified": true
}
```

## Rate Limits

**Unknown** - Need to test and monitor:
- Requests per minute
- Requests per hour
- Concurrent connections

**Expected Strategy**:
- Start with 60 requests/minute (same as PNCP)
- Monitor response headers for rate limit info
- Implement exponential backoff on 429 errors

## Error Responses

### 401 Unauthorized
```json
{
  "error": "invalid_token",
  "error_description": "The access token is invalid or expired"
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "error_description": "API rate limit exceeded",
  "retry_after": 60
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "error_description": "Resource not found"
}
```

## Discovery Strategy

### Stage 1: Bulk Fetch
```
GET /api/me-integration-pre-order/v1/pre-orders?status=open&pageSize=100
```
- Fetch all open pre-orders
- Handle pagination
- Store pre-order IDs

### Stage 2: Filter
- Apply keyword filter to titles/descriptions
- Check categories for relevant types
- Database deduplication

### Stage 3: Full Fetch
```
GET /api/me-integration-pre-order/v1/pre-orders/{preorderid}
```
- Fetch full details for filtered pre-orders
- Get all items
- Extract organization info

### Stage 4: Classification
- Classify items (is_lacre boolean)
- Extract specifications
- Store in database

## Python Implementation Outline

```python
class MEApiClient:
    def __init__(self, client_id: str, client_secret: str):
        self.base_url = "https://api.mercadoe.com"
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

    async def authenticate(self) -> bool:
        """Get OAuth 2.0 access token"""
        pass

    async def get_pre_orders(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str = "open",
        date_from: str = None,
        date_to: str = None
    ) -> Tuple[int, Dict]:
        """List pre-orders with filters"""
        pass

    async def get_pre_order_details(
        self,
        pre_order_id: str
    ) -> Tuple[int, Dict]:
        """Get full pre-order with items"""
        pass
```

## Testing Checklist

- [ ] Test authentication flow
- [ ] Test pre-order listing with pagination
- [ ] Test pre-order details fetch
- [ ] Test filtering by date range
- [ ] Test filtering by status
- [ ] Identify rate limits
- [ ] Test error handling (401, 429, 404)
- [ ] Measure response times
- [ ] Check data structure matches docs
- [ ] Test with lacre-related pre-orders

## Next Steps

1. Obtain API credentials from ME
2. Build authentication module
3. Test basic endpoints
4. Map response structure
5. Implement full client
6. Build discovery pipeline

---

**Source**: https://developer.me.com.br/
**Last Updated**: November 6, 2025
