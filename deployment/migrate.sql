-- MedellínBot Database Migration Script
-- This script should be run after Cloud SQL instance creation

-- Connect to the database
\c medellinbot;

-- Run the initial schema migration
\i ../migrations/001_initial_schema.sql

-- Verify migration completion
SELECT 'Migration 001 completed successfully' as status;

-- Check that all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
  AND table_name IN ('tramites', 'programas_sociales');

-- Check sample data
SELECT 'Trámites count: ' || COUNT(*) as tramites_count FROM tramites;
SELECT 'Programas sociales count: ' || COUNT(*) as programas_count FROM programas_sociales;

-- Show active views
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public' 
  AND table_name IN ('tramites_activos', 'programas_activos');

-- Test a sample query
SELECT codigo, titulo, descripcion 
FROM tramites_activos 
LIMIT 3;

-- Test programas sociales query
SELECT nombre, descripcion 
FROM programas_activos 
LIMIT 3;

-- Create additional indexes for performance (if not already created)
CREATE INDEX IF NOT EXISTS idx_tramites_titulo_trgm ON tramites USING GIN (titulo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_programas_nombre_trgm ON programas_sociales USING GIN (nombre gin_trgm_ops);

-- Analyze tables for query optimization
ANALYZE tramites;
ANALYZE programas_sociales;

-- Show migration summary
SELECT 'Migration completed at: ' || CURRENT_TIMESTAMP as completion_time;