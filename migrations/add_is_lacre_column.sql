-- Migration: Add is_lacre column to tender_items table
-- Database: pncp_lacre_data
-- Purpose: Mark which items in a tender are lacre items (V3 heterogeneous detection)

-- Add the is_lacre column
ALTER TABLE tender_items
ADD COLUMN IF NOT EXISTS is_lacre BOOLEAN DEFAULT FALSE NOT NULL;

-- Create partial index for better query performance (only indexes TRUE values)
CREATE INDEX IF NOT EXISTS idx_tender_items_is_lacre
ON tender_items(is_lacre)
WHERE is_lacre = TRUE;

-- Verify the migration
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'tender_items'
AND column_name = 'is_lacre';
