# Notion Integration Setup Guide

This guide shows you how to set up Notion integration for your PNCP medical data processing system.

## 🎯 **Benefits of Notion Integration**

Instead of working with CSV files, you'll get:
- **Live Dashboard**: Real-time data in interactive Notion databases
- **Better Filtering**: Advanced filtering and sorting capabilities
- **Visual Analytics**: Charts, kanban boards, and custom views
- **Team Collaboration**: Share insights with your team
- **Mobile Access**: Access data on your phone/tablet
- **Automated Updates**: New tender data automatically appears

## 📋 **What You'll Get: 3 Notion Databases**

### 1. **🏛️ Tenders Database**
- Organization name and details
- Government level (Federal/State/Municipal)
- Total homologated value
- State and publication date
- Number of items and matches found

### 2. **📦 Items Database**
- Item descriptions and quantities
- Unit and total prices
- Winning suppliers
- Match status with your Fernandes catalog

### 3. **💰 Opportunities Database** (Most Important!)
- Products with competitive pricing opportunities
- Your FOB price vs market price
- Potential revenue calculations
- Match confidence scores
- Opportunity ratings (High/Medium/Low)

## 🔧 **Step-by-Step Setup**

### **Step 1: Create Notion Integration**

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New Integration"**
3. Name it **"PNCP Medical Processor"**
4. Select your workspace
5. Click **"Submit"**
6. **Copy the Integration Token** (starts with `secret_...`)

### **Step 2: Create Notion Databases**

#### **Create Tenders Database**
1. In Notion, create a new page called **"PNCP Tenders"**
2. Add a database with these properties:
   ```
   Title (Title) - Tender title
   Organization (Text) - Government organization
   CNPJ (Text) - Tax ID
   State (Select) - Add options: SP, RJ, MG, DF, etc.
   Government Level (Select) - Add options: Federal, State, Municipal
   Total Value (R$) (Number) - Format as currency
   Publication Date (Date)
   Status (Select) - Add option: Homologated
   Items Count (Number)
   Matches Found (Number)
   Processed Date (Date)
   ```

#### **Create Items Database**
1. Create page **"PNCP Items"**
2. Add database with properties:
   ```
   Description (Title) - Item description
   Tender ID (Text) - Reference to tender
   Organization (Text) - Government organization
   Item Number (Number)
   Unit (Text) - Unit of measure
   Quantity (Number)
   Unit Price (R$) (Number) - Format as currency
   Total Price (R$) (Number) - Format as currency
   Winner (Text) - Winning supplier
   State (Select) - Same options as above
   Has Match (Checkbox) - Whether we found a product match
   ```

#### **Create Opportunities Database**
1. Create page **"PNCP Opportunities"**
2. Add database with properties:
   ```
   Product (Title) - Fernandes product description
   Fernandes Code (Text) - Product code
   Tender Description (Text) - Original tender description
   Organization (Text) - Government organization
   Match Score (Number) - Percentage
   FOB Price (USD) (Number) - Format as currency
   Market Price (R$) (Number) - Format as currency
   Our Price (R$) (Number) - Format as currency
   Price Difference (%) (Number) - Percentage
   Competitive (Checkbox)
   State (Select) - Same options as above
   Opportunity Score (Select) - Add options: 🟢 High, 🟡 Medium, 🟠 Low, 🔴 Poor
   Quantity (Number)
   Potential Revenue (R$) (Number) - Format as currency
   ```

### **Step 3: Share Databases with Integration**

For each database:
1. Click **"Share"** in the top-right
2. Click **"Invite"**
3. Select **"PNCP Medical Processor"** (your integration)
4. Set permissions to **"Can edit"**
5. Click **"Invite"**

### **Step 4: Get Database IDs**

For each database, copy the database ID from the URL:
```
https://notion.so/your-workspace/DATABASE_ID?v=...
                                ^^^^^^^^^^^^
```

The database ID is the 32-character string (with dashes).

### **Step 5: Update Your .env File**

Add these lines to your `.env` file:

```env
# Notion Integration
NOTION_API_TOKEN=secret_your_integration_token_here
NOTION_TENDERS_DB_ID=your-tenders-database-id
NOTION_ITEMS_DB_ID=your-items-database-id
NOTION_OPPORTUNITIES_DB_ID=your-opportunities-database-id
```

### **Step 6: Test Connection**

Run this command to test your setup:

```bash
python -c "
from notion_integration import test_notion_connection
import asyncio
asyncio.run(test_notion_connection())
"
```

You should see: `✅ Connection successful!`

## 🚀 **Usage**

Once configured, every time you run the processor:

```bash
python main.py --start-date 20240101 --end-date 20240131 --states SP RJ
```

The system will automatically:
1. Process tender data
2. Find product matches
3. **Export results to your Notion databases**
4. Update your live dashboard

## 📊 **Notion Views You Can Create**

### **High-Value Opportunities View**
- Filter: `Opportunity Score = 🟢 High`
- Sort by: `Potential Revenue (R$)` descending
- Show only competitive products

### **By State Analysis**
- Group by: `State`
- Show: Total revenue potential per state

### **Recent Activity**
- Filter: `Processed Date` within last 7 days
- Sort by: `Processed Date` descending

### **Product Performance**
- Group by: `Fernandes Code`
- Show: How often each product appears in tenders

## 🔍 **Sample Data Preview**

After processing, your **Opportunities Database** might look like:

| Product | Fernandes Code | Market Price (R$) | Our Price (R$) | Difference | Opportunity |
|---------|----------------|-------------------|----------------|------------|-------------|
| Curativo IV Transparente | IVFS.5057 | R$0.45 | R$0.37 | +21.6% | 🟢 High |
| Luva Nitrilo Descartável | GLVN.M001 | R$0.18 | R$0.12 | +50.0% | 🟢 High |
| Seringa 10ML Descartável | SRG.10ML | R$0.35 | R$0.28 | +25.0% | 🟡 Medium |

## ⚡ **Automation Tips**

1. **Create Templates**: Set up database templates for quick data entry
2. **Use Formulas**: Calculate profit margins automatically
3. **Set Filters**: Create saved views for different business scenarios
4. **Add Relations**: Link databases together for deeper analysis
5. **Dashboard Page**: Create a summary page with database views

## 🚨 **Rate Limits**

- Notion API: 3 requests per second
- The system includes automatic rate limiting
- Large exports might take a few minutes

## 🛠️ **Troubleshooting**

**❌ "Notion API Token not configured"**
- Check your `.env` file has the correct token
- Make sure token starts with `secret_`

**❌ "Database not found"**
- Verify database IDs are correct
- Make sure integration has access to databases

**❌ "Property not found"**
- Check database column names match exactly
- Make sure all required properties exist

## 💡 **Pro Tips**

1. **Start with Opportunities Database**: This is where the business value is
2. **Use Notion Mobile**: Check opportunities while traveling
3. **Share with Sales Team**: Give them access to competitive intel
4. **Set up Notifications**: Get alerts for high-value opportunities
5. **Export to Excel**: Use Notion's export if you need spreadsheets

---

**Result**: Instead of sorting through CSV files, you'll have a live business intelligence dashboard that automatically updates with competitive opportunities from Brazilian government tenders! 🚀