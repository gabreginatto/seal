-- ============================================================================
-- LOOKER STUDIO VIEW FOR LACRE ANALYSIS
-- ============================================================================
-- Purpose: Single view for analyzing lacre (security seal) tender items
--
-- INSTRUCTIONS:
-- 1. Connect to your Cloud SQL database
-- 2. Run this file: psql -h <host> -U postgres -d <database_name> -f lacre_looker_view.sql
-- 3. Connect Looker Studio to this view: vw_lacre_items
--
-- ============================================================================

-- ============================================================================
-- VIEW: All Lacre Items with Complete Context
-- Base view with lacre items and full tender/organization details
-- ============================================================================
CREATE OR REPLACE VIEW vw_lacre_items AS
SELECT
    -- Item details
    ti.id as item_id,
    ti.item_number,
    ti.description as item_description,
    ti.unit,
    ti.quantity,
    ti.estimated_unit_value,
    ti.estimated_total_value,
    ti.homologated_unit_value,
    ti.homologated_total_value,
    ti.winner_name,
    ti.winner_cnpj,
    ti.is_lacre,  -- Flag showing if this item is a lacre
    ti.created_at as item_created_at,

    -- Tender details
    t.id as tender_id,
    t.control_number,
    t.ano as tender_year,
    t.sequencial as tender_sequential,
    t.publication_date,
    t.state_code,
    t.total_homologated_value as tender_total_value,
    t.contracting_modality as modality_code,
    t.modality_name,
    t.title as tender_title,
    t.status as tender_status,

    -- Organization details
    o.name as organization_name,
    o.cnpj as organization_cnpj,
    o.government_level,
    o.organization_type,

    -- Calculated fields
    CASE
        WHEN ti.estimated_unit_value > 0 AND ti.homologated_unit_value > 0 THEN
            ROUND(((ti.estimated_unit_value - ti.homologated_unit_value) / ti.estimated_unit_value * 100)::numeric, 2)
        ELSE NULL
    END as savings_percent,

    CASE
        WHEN ti.homologated_total_value >= 50000 THEN 'High (>50k)'
        WHEN ti.homologated_total_value >= 10000 THEN 'Medium (10-50k)'
        WHEN ti.homologated_total_value >= 1000 THEN 'Low (1-10k)'
        ELSE 'Very Low (<1k)'
    END as item_value_category,

    -- Tender statistics (computed via subquery)
    (SELECT COUNT(*) FROM tender_items WHERE tender_id = t.id) as total_items,
    (SELECT COUNT(*) FROM tender_items WHERE tender_id = t.id AND is_lacre = TRUE) as lacre_items_count,

    -- Tender categorization
    CASE
        WHEN (SELECT COUNT(*) FROM tender_items WHERE tender_id = t.id AND is_lacre = TRUE) =
             (SELECT COUNT(*) FROM tender_items WHERE tender_id = t.id) THEN 'Pure Lacre Tender'
        WHEN (SELECT COUNT(*) FROM tender_items WHERE tender_id = t.id AND is_lacre = TRUE) > 0 THEN 'Mixed Tender'
        ELSE 'No Lacre Items'
    END as tender_type

FROM tender_items ti
JOIN tenders t ON ti.tender_id = t.id
JOIN organizations o ON t.organization_id = o.id
WHERE ti.is_lacre = TRUE;  -- Only show lacre items (includes both ongoing and completed tenders)

COMMENT ON VIEW vw_lacre_items IS
'Complete view of all lacre items with full tender and organization context. Use this as the single data source for Looker Studio dashboards.';

-- ============================================================================
-- USAGE INSTRUCTIONS FOR LOOKER STUDIO
-- ============================================================================
--
-- SETUP:
-- 1. Run this file in your database
-- 2. In Looker Studio, connect to your Cloud SQL database
-- 3. Select "vw_lacre_items" as your data source
-- 4. Create charts and filters using the fields below
--
-- AVAILABLE FIELDS:
--
-- Item Information:
--   - item_description: Full lacre description
--   - quantity: Number of units
--   - unit: Unit of measurement (UN, CX, etc.)
--   - homologated_unit_value: Price per unit (BRL)
--   - homologated_total_value: Total price (BRL)
--   - winner_name: Winning supplier
--   - winner_cnpj: Supplier CNPJ
--
-- Tender Information:
--   - control_number: Tender ID
--   - tender_year: Year of tender
--   - publication_date: When published
--   - state_code: BR state (SP, RJ, etc.)
--   - tender_total_value: Total tender value
--   - total_items: Total items in tender
--   - lacre_items_count: How many items are lacres
--   - tender_type: 'Pure Lacre Tender' or 'Mixed Tender'
--
-- Organization Information:
--   - organization_name: Government entity name
--   - organization_cnpj: Organization CNPJ
--   - government_level: Federal/Estadual/Municipal
--   - organization_type: Type of organization
--
-- Calculated Fields:
--   - savings_percent: % savings from estimated price
--   - item_value_category: Value bucket (High/Medium/Low/Very Low)
--
-- RECOMMENDED CHARTS:
--
-- 1. Geographic Distribution:
--    - Map chart by state_code
--    - Metric: SUM(homologated_total_value)
--
-- 2. Top Suppliers:
--    - Table with winner_name
--    - Metrics: COUNT(item_id), SUM(homologated_total_value)
--    - Sort by total value DESC
--
-- 3. Price Analysis:
--    - Histogram of homologated_unit_value
--    - Filter by item_description keywords for specific lacre types
--
-- 4. Time Series:
--    - Line chart with publication_date
--    - Metric: COUNT(item_id) or SUM(homologated_total_value)
--
-- 5. Tender Type Distribution:
--    - Pie chart by tender_type
--    - Shows pure lacre tenders vs mixed tenders
--
-- 6. Top Organizations:
--    - Table with organization_name, government_level
--    - Metrics: COUNT(DISTINCT tender_id), SUM(homologated_total_value)
--
-- FILTERS TO ADD IN LOOKER:
--   - Date Range: publication_date
--   - State: state_code
--   - Government Level: government_level
--   - Tender Type: tender_type
--   - Value Range: homologated_unit_value
--   - Supplier: winner_name
--
-- EXAMPLE QUERIES TO TEST VIEW:
--
-- Total lacre items:
--   SELECT COUNT(*) FROM vw_lacre_items;
--
-- Total value by state:
--   SELECT state_code,
--          COUNT(*) as items,
--          SUM(homologated_total_value) as total_brl
--   FROM vw_lacre_items
--   GROUP BY state_code
--   ORDER BY total_brl DESC;
--
-- Top suppliers:
--   SELECT winner_name,
--          COUNT(*) as items,
--          SUM(homologated_total_value) as total_brl
--   FROM vw_lacre_items
--   GROUP BY winner_name
--   ORDER BY total_brl DESC
--   LIMIT 10;
--
-- Mixed vs Pure lacre tenders:
--   SELECT tender_type,
--          COUNT(DISTINCT tender_id) as tender_count
--   FROM vw_lacre_items
--   GROUP BY tender_type;
--
-- ============================================================================
