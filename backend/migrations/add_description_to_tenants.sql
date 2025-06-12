-- Add description column to tenants table
-- This migration adds the missing description field to support organization descriptions

ALTER TABLE tenants ADD COLUMN description TEXT;

-- Add a comment for documentation
COMMENT ON COLUMN tenants.description IS 'Optional description of the organization';