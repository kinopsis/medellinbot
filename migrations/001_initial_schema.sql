-- Migration 001: Initial schema for MedellínBot
-- Created: 2025-10-29
-- Description: Create initial tables for trámites and programas sociales

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create tramites table
CREATE TABLE IF NOT EXISTS tramites (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    requisitos JSONB,
    plazos VARCHAR(100),
    costo VARCHAR(100),
    ubicacion_oficinas JSONB,
    entidad VARCHAR(100),
    categoria VARCHAR(50),
    version INT DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);

-- Create programas_sociales table
CREATE TABLE IF NOT EXISTS programas_sociales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    elegibilidad_criteria JSONB,
    descripcion TEXT,
    periodo VARCHAR(100),
    contact_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_tramites_codigo ON tramites(codigo);
CREATE INDEX IF NOT EXISTS idx_tramites_categoria ON tramites(categoria);
CREATE INDEX IF NOT EXISTS idx_tramites_entidad ON tramites(entidad);
CREATE INDEX IF NOT EXISTS idx_tramites_active ON tramites(active);
CREATE INDEX IF NOT EXISTS idx_tramites_requisitos_gin ON tramites USING GIN(requisitos);
CREATE INDEX IF NOT EXISTS idx_programas_nombre ON programas_sociales(nombre);
CREATE INDEX IF NOT EXISTS idx_programas_active ON programas_sociales(active);
CREATE INDEX IF NOT EXISTS idx_programas_elegibilidad_gin ON programas_sociales USING GIN(elegibilidad_criteria);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_tramites_updated_at 
    BEFORE UPDATE ON tramites 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_programas_updated_at 
    BEFORE UPDATE ON programas_sociales 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for tramites
INSERT INTO tramites (codigo, titulo, descripcion, requisitos, plazos, costo, ubicacion_oficinas, entidad, categoria) VALUES
('PREDIAL-001', 'Pago de Impuesto Predial', 'Pago anual del impuesto predial para propiedades en Medellín', 
 '["Cédula de ciudadanía", "Certificado de tradición y libertad", "Último recibo de pago"]', 
 '30 días hábiles', '$50.000', 
 '[{"name": "Alcaldía de Medellín", "address": "Cra. 44 #52-11", "lat": 6.2442, "lng": -75.5812, "horario": "8:00-17:00", "telefono": "321 123 4567"}]', 
 'Alcaldía', 'Impuestos'),
('LICENCIA-001', 'Licencia de Construcción', 'Trámite para obtener licencia de construcción en el municipio', 
 '["Planos arquitectónicos", "Certificado de libertad y tradición", "Pago de derechos"]', 
 '15 días hábiles', '$200.000', 
 '[{"name": "Secretaría de Planeación", "address": "Cra. 52 #44-11", "lat": 6.2510, "lng": -75.5730, "horario": "8:00-16:00", "telefono": "321 987 6543"}]', 
 'Alcaldía', 'Construcción'),
('AGUA-001', 'Suspensión Temporal de Servicio de Acueducto', 'Solicitar suspensión temporal del servicio de acueducto por viaje o remodelación', 
 '["Cédula de ciudadanía", "Último recibo de pago", "Justificación de la suspensión"]', 
 '5 días hábiles', '$25.000', 
 '[{"name": "EPM - Oficina de Atención al Ciudadano", "address": "Cra. 50 #40-15", "lat": 6.2470, "lng": -75.5730, "horario": "7:00-18:00", "telefono": "321 456 7890"}]', 
 'EPM', 'Servicios Públicos'),
('INDUSTRIA-COMERCIO-001', 'Licencia de Industria y Comercio', 'Trámite para obtener licencia de industria y comercio para actividades económicas', 
 '["Cédula de ciudadanía", "RUT", "Certificado de cámara de comercio", "Pago de impuestos"]', 
 '10 días hábiles', '$75.000', 
 '[{"name": "Alcaldía de Medellín - Secretaría de Hacienda", "address": "Cra. 44 #52-11", "lat": 6.2442, "lng": -75.5812, "horario": "8:00-16:00", "telefono": "321 789 0123"}]', 
 'Alcaldía', 'Impuestos'),
('PASAPORTE-001', 'Renovación de Pasaporte', 'Renovación de pasaporte colombiano para viajes internacionales', 
 '["Cédula de ciudadanía", "Pasaporte anterior", "Foto tipo documento", "Pago de derechos"]', 
 '7 días hábiles', '$150.000', 
 '[{"name": "Cancillería - Oficina de Pasaportes", "address": "Cra. 70 #50-20", "lat": 6.2520, "lng": -75.5700, "horario": "8:00-17:00", "telefono": "321 012 3456"}]', 
 'Cancillería', 'Documentos');

-- Insert sample data for programas_sociales
INSERT INTO programas_sociales (nombre, elegibilidad_criteria, descripcion, periodo, contact_info) VALUES
('Buen Comienzo 365', '{"edad_min": 0, "edad_max": 5, "estrato": [1, 2, 3], "ingresos_max": 2000000}', 'Programa de atención integral para niños de 0 a 5 años con servicios de salud, nutrición y educación inicial', 'Anual', '{"telefono": "321 123 4567", "email": "buencomienzo@medellin.gov.co", "direccion": "Cra. 44 #52-11, Alcaldía de Medellín"}'),
('Medellín Te Quiere', '{"edad_min": 18, "desplazado": true, "victima_conflicto": true}', 'Programa de apoyo psicosocial, económico y legal a víctimas del conflicto armado y desplazados', 'Semestral', '{"telefono": "321 987 6543", "email": "medellintequiere@medellin.gov.co", "direccion": "Cra. 52 #44-11, Secretaría de Inclusión Social"}'),
('Jóvenes en Acción', '{"edad_min": 16, "edad_max": 28, "estudiante": true, "estrato": [1, 2, 3]}', 'Programa de becas y oportunidades laborales para jóvenes en situación de vulnerabilidad', 'Trimestral', '{"telefono": "321 456 7890", "email": "jovenes@medellin.gov.co", "direccion": "Cra. 67 #50-10, Secretaría de Educación"}'),
('Adulto Mayor', '{"edad_min": 60, "pensionado": false, "discapacidad": false}', 'Programa de acompañamiento, salud y actividades recreativas para adultos mayores', 'Mensual', '{"telefono": "321 789 0123", "email": "adultomayor@medellin.gov.co", "direccion": "Cra. 43 #51-20, Secretaría de Salud"}'),
('Empleo Joven', '{"edad_min": 18, "edad_max": 30, "desempleado": true, "formalizado": false}', 'Programa de capacitación y colocación laboral para jóvenes en busca de su primer empleo', 'Bimestral', '{"telefono": "321 012 3456", "email": "empleojoven@medellin.gov.co", "direccion": "Cra. 55 #45-30, Secretaría de Desarrollo Económico"}');

-- Create view for active tramites
CREATE OR REPLACE VIEW tramites_activos AS
SELECT id, codigo, titulo, descripcion, requisitos, plazos, costo, ubicacion_oficinas, entidad, categoria, version, updated_at, created_at
FROM tramites
WHERE active = true;

-- Create view for active programas sociales
CREATE OR REPLACE VIEW programas_activos AS
SELECT id, nombre, elegibilidad_criteria, descripcion, periodo, contact_info, updated_at, created_at
FROM programas_sociales
WHERE active = true;

-- Grant permissions (adjust as needed for your security model)
GRANT SELECT, INSERT, UPDATE ON tramites TO medellinbot_user;
GRANT SELECT, INSERT, UPDATE ON programas_sociales TO medellinbot_user;
GRANT USAGE, SELECT ON SEQUENCE tramites_id_seq TO medellinbot_user;
GRANT USAGE, SELECT ON SEQUENCE programas_sociales_id_seq TO medellinbot_user;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 001 completed successfully';
END $$;