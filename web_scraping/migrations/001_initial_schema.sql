-- Web Scraping Database Schema
-- Initial migration for the MedellínBot web scraping framework

-- Create extension for UUID generation (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum type for data quality
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'data_quality') THEN
        CREATE TYPE data_quality AS ENUM ('high', 'medium', 'low', 'invalid');
    END IF;
END
$$;

-- Create scraped_data table
CREATE TABLE IF NOT EXISTS scraped_data (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,
    validation_errors TEXT DEFAULT '',
    content_hash VARCHAR(32),
    
    -- Indexes for performance
    INDEX idx_scraped_data_source (source),
    INDEX idx_scraped_data_type (data_type),
    INDEX idx_scraped_data_created_at (created_at),
    INDEX idx_scraped_data_content_hash (content_hash)
);

-- Create scraping_jobs table
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id SERIAL PRIMARY KEY,
    scraper_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_message TEXT,
    config JSONB DEFAULT '{}',
    
    -- Indexes for performance
    INDEX idx_scraping_jobs_scraper_name (scraper_name),
    INDEX idx_scraping_jobs_status (status),
    INDEX idx_scraping_jobs_start_time (start_time)
);

-- Create data_quality_metrics table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    quality_score data_quality NOT NULL,
    total_records INTEGER DEFAULT 0,
    valid_records INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_quality_metrics_source (source),
    INDEX idx_quality_metrics_type (data_type),
    INDEX idx_quality_metrics_measured_at (measured_at)
);

-- Create monitoring_metrics table
CREATE TABLE IF NOT EXISTS monitoring_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    source VARCHAR(255),
    data_type VARCHAR(100),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_monitoring_metrics_name (metric_name),
    INDEX idx_monitoring_metrics_source (source),
    INDEX idx_monitoring_metrics_recorded_at (recorded_at)
);

-- Create alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metric_name VARCHAR(255),
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved BOOLEAN DEFAULT FALSE,
    
    -- Indexes for performance
    INDEX idx_alerts_rule_name (rule_name),
    INDEX idx_alerts_severity (severity),
    INDEX idx_alerts_triggered_at (triggered_at),
    INDEX idx_alerts_resolved (resolved)
);

-- Create configuration table
CREATE TABLE IF NOT EXISTS configurations (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_configurations_key (config_key)
);

-- Insert default configuration
INSERT INTO configurations (config_key, config_value, description) VALUES 
(
    'default_scraping_config',
    '{
        "rate_limit_delay": 1.0,
        "timeout": 30,
        "max_retries": 3,
        "user_agent": "MedellínBot/1.0",
        "concurrent_requests": 5
    }',
    'Default scraping configuration parameters'
)
ON CONFLICT (config_key) DO NOTHING;

-- Insert source configurations
INSERT INTO configurations (config_key, config_value, description) VALUES 
(
    'source_config_alcaldia_medellin',
    '{
        "base_url": "https://medellin.gov.co",
        "rate_limit_delay": 2.0,
        "timeout": 30,
        "data_types": ["news", "tramites", "contact", "program"]
    }',
    'Alcaldía de Medellín source configuration'
),
(
    'source_config_secretaria_movilidad',
    '{
        "base_url": "https://movilidadmedellin.gov.co",
        "rate_limit_delay": 1.5,
        "timeout": 25,
        "data_types": ["traffic_alert", "pico_placa", "vial_closure", "contact"]
    }',
    'Secretaría de Movilidad source configuration'
)
ON CONFLICT (config_key) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_scraped_data_updated_at 
    BEFORE UPDATE ON scraped_data 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to calculate data quality score
CREATE OR REPLACE FUNCTION calculate_data_quality_score(
    p_total_records INTEGER,
    p_valid_records INTEGER,
    p_error_count INTEGER
) RETURNS data_quality AS $$
DECLARE
    completeness_ratio NUMERIC;
    error_ratio NUMERIC;
BEGIN
    IF p_total_records = 0 THEN
        RETURN 'invalid'::data_quality;
    END IF;
    
    completeness_ratio := p_valid_records::NUMERIC / p_total_records::NUMERIC;
    error_ratio := p_error_count::NUMERIC / p_total_records::NUMERIC;
    
    IF completeness_ratio >= 0.9 AND error_ratio <= 0.1 THEN
        RETURN 'high'::data_quality;
    ELSIF completeness_ratio >= 0.7 AND error_ratio <= 0.2 THEN
        RETURN 'medium'::data_quality;
    ELSIF completeness_ratio >= 0.5 AND error_ratio <= 0.3 THEN
        RETURN 'low'::data_quality;
    ELSE
        RETURN 'invalid'::data_quality;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to record scraping metrics
CREATE OR REPLACE FUNCTION record_scraping_metrics(
    p_source VARCHAR(255),
    p_data_type VARCHAR(100),
    p_records_processed INTEGER,
    p_success_count INTEGER,
    p_error_count INTEGER
) RETURNS VOID AS $$
DECLARE
    quality_score data_quality;
BEGIN
    -- Calculate quality score
    quality_score := calculate_data_quality_score(
        p_records_processed,
        p_success_count,
        p_error_count
    );
    
    -- Insert quality metrics
    INSERT INTO data_quality_metrics (
        source,
        data_type,
        quality_score,
        total_records,
        valid_records,
        error_count
    ) VALUES (
        p_source,
        p_data_type,
        quality_score,
        p_records_processed,
        p_success_count,
        p_error_count
    );
    
    -- Insert monitoring metrics
    INSERT INTO monitoring_metrics (metric_name, metric_value, source, data_type) VALUES
        ('total_records', p_records_processed, p_source, p_data_type),
        ('success_rate', 
         CASE WHEN p_records_processed > 0 
         THEN (p_success_count::NUMERIC / p_records_processed::NUMERIC) * 100 
         ELSE 0 END, 
         p_source, p_data_type),
        ('error_rate', 
         CASE WHEN p_records_processed > 0 
         THEN (p_error_count::NUMERIC / p_records_processed::NUMERIC) * 100 
         ELSE 0 END, 
         p_source, p_data_type);
END;
$$ LANGUAGE plpgsql;

-- Create function to check for duplicate content
CREATE OR REPLACE FUNCTION check_duplicate_content(
    p_source VARCHAR(255),
    p_data_type VARCHAR(100),
    p_content_hash VARCHAR(32)
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM scraped_data 
        WHERE source = p_source 
        AND data_type = p_data_type 
        AND content_hash = p_content_hash
        AND created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to get recent data with pagination
CREATE OR REPLACE FUNCTION get_recent_data(
    p_source VARCHAR(255) DEFAULT NULL,
    p_data_type VARCHAR(100) DEFAULT NULL,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
) RETURNS TABLE (
    id INTEGER,
    source VARCHAR(255),
    data_type VARCHAR(100),
    content JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    is_valid BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sd.id,
        sd.source,
        sd.data_type,
        sd.content,
        sd.created_at,
        sd.is_valid
    FROM scraped_data sd
    WHERE (p_source IS NULL OR sd.source = p_source)
    AND (p_data_type IS NULL OR sd.data_type = p_data_type)
    ORDER BY sd.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO web_scraping_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO web_scraping_user;

-- Add comments for documentation
COMMENT ON TABLE scraped_data IS 'Stores all scraped data from various sources';
COMMENT ON TABLE scraping_jobs IS 'Tracks scraping job executions and results';
COMMENT ON TABLE data_quality_metrics IS 'Records data quality measurements over time';
COMMENT ON TABLE monitoring_metrics IS 'Stores monitoring metrics for system health';
COMMENT ON TABLE alerts IS 'Tracks alert conditions and resolutions';
COMMENT ON TABLE configurations IS 'Stores system and source configurations';

COMMENT ON COLUMN scraped_data.source IS 'Source identifier (e.g., alcaldia_medellin)';
COMMENT ON COLUMN scraped_data.data_type IS 'Type of data (e.g., news, tramites, contact)';
COMMENT ON COLUMN scraped_data.content IS 'The actual scraped data in JSON format';
COMMENT ON COLUMN scraped_data.content_hash IS 'MD5 hash for duplicate detection';

COMMENT ON COLUMN scraping_jobs.status IS 'Job status: pending, running, completed, failed';
COMMENT ON COLUMN scraping_jobs.records_processed IS 'Total records processed in this job';
COMMENT ON COLUMN scraping_jobs.success_count IS 'Number of successfully processed records';
COMMENT ON COLUMN scraping_jobs.error_count IS 'Number of records that failed processing';

COMMENT ON COLUMN data_quality_metrics.quality_score IS 'Data quality assessment: high, medium, low, invalid';