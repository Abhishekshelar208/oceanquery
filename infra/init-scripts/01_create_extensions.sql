-- Create necessary PostgreSQL extensions for OceanQuery
-- This script runs when the database is first initialized

-- PostGIS extension for geographic data (if needed)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Additional indexes for better performance
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Create schema for ARGO data
CREATE SCHEMA IF NOT EXISTS argo;

-- Grant permissions
GRANT USAGE ON SCHEMA argo TO postgres;
GRANT CREATE ON SCHEMA argo TO postgres;
