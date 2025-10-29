# MedellínBot - Comprehensive Investigation and Implementation Plan

## Executive Summary

**Project**: MedellínBot - Intelligent Citizen Assistant for Medellín  
**Objective**: Create a 24/7 conversational AI agent on Telegram that helps citizens access information about municipal procedures, services, PQRSD, social programs, and proactive notifications.  
**Technology Stack**: Google ADK + LangChain/LlamaIndex, Gemini 2.0 Flash/Pro via Vertex AI, Cloud Run, Firestore, Cloud SQL, Vertex Vector Search  
**Implementation**: Complete end-to-end with all 4 specialized agents (Trámites, PQRSD, Programas Sociales, Notificaciones)

## 1. Detailed Requirements Analysis

### 1.1 Functional Requirements (RF)

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| RF-1 | Intelligent Procedure Guide | Natural language identification of procedures, explanation of requirements, costs, times, channels, and generation of records | High |
| RF-2 | PQRSD Router | Automatic classification of request type, determine competent entity, draft formal text, generate tracking number, and follow-up | High |
| RF-3 | Social Programs | Respond about "Medellín Te Quiere" plan, Buen Comienzo 365, and subsidies; verify eligibility and guide registration | Medium |
| RF-4 | Proactive Notifications | Personalized alerts for peak and plate, road closures, and neighborhood activities | Medium |
| RF-5 | 24/7 Attention | Continuous availability via Telegram for thousands of concurrent users | High |
| RF-6 | Multi-turn Conversations | Maintain conversational context for natural interactions | High |

### 1.2 Non-Functional Requirements (RNF)

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| RNF-1 | Scalability | Auto-scaling in Google Cloud Run and high concurrency without degrading experience | High |
| RNF-2 | Security and Privacy | Compliance with Colombian regulations (Law 1581 of 2012), data encryption, and explicit consent | High |
| RNF-3 | Latency | Responses in less than 3 seconds on average | High |
| RNF-4 | Availability | 99.9% uptime with monitoring and auto-recovery | High |
| RNF-5 | Maintainability | Modular architecture with specialized agents for easy evolution | Medium |
| RNF-6 | Usability | Clear interface, natural language, accessible to users without technical knowledge | Medium |

### 1.3 Success Criteria

- Functional prototype in 4 weeks
- >80% precision in classification
- 100 active beta users in pilot
- Responses in <3 seconds
- High user satisfaction (NPS >60)

## 2. Technical Architecture Design

### 2.1 High-Level Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │    │   Orchestrator   │    │   Domain Agents │
│   Bot API       │    │   (ADK + LLM)    │    │   (Specialized) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webhook       │    │   Context        │    │   Knowledge     │
│   (Cloud Run)   │    │   Manager        │    │   Layer         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Firestore     │    │   Vector Search  │    │   External APIs │
│   (Sessions)    │    │   (Vertex AI)    │    │   (Municipal)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 2.2 Component Responsibilities

#### A. Telegram Bot Interface (Cloud Run)
- **Responsibility**: Receive webhook, authenticate request, normalize messages, rate limiting, forward to Orchestrator
- **Technology**: Python (FastAPI/Flask)
- **Outputs**: `session_id`, `user_id`, `message_text`, `attachments`, `timestamp`

#### B. Orchestrator Agent (ADK)
- **Intent classification**: Lightweight model (fasttext, scikit-learn) or LLM few-shot
- **Routing**: Rules + confidence thresholds (if low confidence → ask for clarification / transfer to human)
- **Context manager**: Compose agent prompt with memory (last 50 messages)
- **Session memory**: Persist in Firestore
- **Tool invocation**: Calls to APIs (Cloud SQL, Firestore, external APIs)
- **Fallback**: Human case / queue

#### C. Domain Agents
- **Trámites Agent**: Procedure information, requirements, costs, locations
- **PQRSD Agent**: Classification, formal drafting, tracking number generation
- **Programas Sociales Agent**: Social program information, eligibility verification
- **Notificaciones Agent**: Proactive alerts, user preferences

#### D. Knowledge Layer
- **Vertex AI Vector Search**: Document embeddings (PDFs, FAQs, regulations)
- **Firestore**: Sessions, transactions (tracking numbers), conversation logs
- **Cloud SQL (Postgres)**: Structured procedure catalog with relationships and versioning

## 3. Data Architecture and Schemas

### 3.1 Firestore Collections (NoSQL)

#### Sessions Collection
```javascript
sessions/{session_id}
  - user_id: string
  - created_at: timestamp
  - last_active: timestamp
  - messages: array of last 50 message metadata
    - text: string
    - role: "user" | "agent"
    - timestamp: timestamp
    - embedding_id: string (optional)
  - memory_summary: string (optional short summary)
```

#### Radicados Collection
```javascript
radicados/{radicado_id}
  - user_id: string
  - tipo: string (P, Q, R, S, D)
  - entidad: string (Alcaldía, EPM, Metro, etc.)
  - status: string
  - created_at: timestamp
  - meta: JSON (free fields)
  - attachments: array
```

#### Logs Collection
```javascript
logs/{log_id}
  - session_id: string
  - component: string
  - action: string
  - payload: JSON
  - timestamp: timestamp
```

**Note**: Store only essential data; if sensitive data (ID documents) encrypt and/or don't store.

### 3.2 Cloud SQL Tables (PostgreSQL)

#### Trámites Table
```sql
CREATE TABLE tramites (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR UNIQUE,
    titulo TEXT,
    descripcion TEXT,
    requisitos JSONB,
    plazos VARCHAR,
    costo VARCHAR,
    ubicacion_oficinas JSONB, -- list of {name,address,lat,lng,horario}
    entidad VARCHAR,
    categoria VARCHAR,
    version INT,
    updated_at TIMESTAMP
);
```

#### Programas Sociales Table
```sql
CREATE TABLE programas_sociales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR,
    elegibilidad_criteria JSONB,
    descripcion TEXT,
    periodo VARCHAR,
    contact_info JSONB
);
```

### 3.3 Memory Management

**Objective**: Maintain last 50 messages per session and a `memory_summary` capturing persistent points (e.g., address, document number - if applicable and with consent).

**Implementation**:
- In Firestore `sessions/{id}.messages` as array or subcollection `sessions/{id}/messages` with timestamp and role
- When array exceeds 50, remove oldest
- Optional: Every N messages (e.g., 10) run function that summarizes session in `memory_summary` (summarization models)
- **Usage in prompts**: Include `memory_summary` + last N messages (e.g., 8) to maintain context

## 4. Security and Compliance Framework

### 4.1 Colombian Data Protection Compliance (Law 1581 of 2012)

#### Data Protection Principles
- **Lawfulness, loyalty, and transparency**: Clear consent and purpose limitation
- **Data minimization**: Collect only necessary data
- **Accuracy**: Keep data accurate and up-to-date
- **Storage limitation**: Retain data only as long as necessary
- **Integrity and confidentiality**: Secure processing

#### Specific Requirements
- **Explicit consent**: Obtain user consent before processing personal data
- **Data subject rights**: Access, rectification, deletion, opposition
- **Security measures**: Technical and organizational measures to protect data
- **Data breach notification**: Notify authorities and affected individuals in case of breach

### 4.2 Security Implementation

#### Authentication and Authorization
- **Service accounts**: Use Google Cloud service accounts with minimal privileges
- **Secret Manager**: Store sensitive credentials securely
- **OAuth 2.0**: For external API integrations

#### Data Protection
- **Encryption at rest**: Use Google Cloud's default encryption
- **Encryption in transit**: TLS 1.2+ for all communications
- **Data residency**: Ensure data stays in Colombian regions (use `southamerica-west1` - Santiago, Chile or `southamerica-east1` - São Paulo, Brazil with data processing agreements)

#### Access Control
- **IAM roles**: Principle of least privilege
- **Audit logs**: Monitor access and changes
- **Network security**: VPC, firewall rules, private endpoints

#### Privacy by Design
- **Anonymization**: Where possible, use pseudonymous identifiers
- **Consent management**: Clear consent flow at first interaction
- **Data deletion**: Mechanism to delete session and personal data on request

## 5. Implementation Roadmap and Phases

### 5.1 Phase Breakdown (18 weeks)

| Phase | Duration | Main Activities | Deliverables |
|-------|----------|-----------------|--------------|
| **Phase 1** | Weeks 1-4 | Infrastructure setup, basic prototype, Telegram webhook | Webhook Cloud Run, basic Orchestrator, Firestore sessions |
| **Phase 2** | Weeks 5-10 | Develop Trámites and PQRSD agents | Complete Trámites agent with Cloud SQL, PQRSD agent with Firestore integration |
| **Phase 3** | Weeks 11-14 | Social Programs and Notifications agents, memory management | Programas Sociales agent, Notificaciones agent, vector search integration |
| **Phase 4** | Weeks 15-18 | Optimization, security, pilot launch | Security framework, monitoring, pilot deployment |
| **Post-launch** | +3 months | Monitoring, continuous improvements, expansion | Performance metrics, user feedback, feature enhancements |

### 5.2 Sprint Planning (2-week sprints)

#### Sprint 1: Webhook + Basic Orchestrator
- Set up Cloud Run webhook
- Implement basic message handling
- Create Firestore session management
- Basic intent classification (rule-based)

#### Sprint 2: Trámites Agent Basic
- Cloud SQL setup and data migration
- Basic procedure search functionality
- Simple response generation
- Integration with Orchestrator

#### Sprint 3: PQRSD Agent
- Firestore radicado creation
- Formal text generation
- Entity classification
- Tracking number generation

#### Sprint 4: Programas Agent + Basic Vector Search
- Social program information retrieval
- Eligibility verification flow
- Basic FAQ retrieval with vector search
- User guidance workflows

#### Sprint 5: Advanced Vector Search Integration
- Document ingestion pipeline
- Embedding generation and storage
- Advanced retrieval capabilities
- Context enrichment

#### Sprint 6: Notificaciones Agent
- External API integration (pico/placa)
- User preference management
- Proactive notification system
- Scheduling and delivery

#### Sprint 7: Security and Compliance
- Consent management implementation
- Data encryption and security measures
- Privacy policy integration
- Compliance documentation

#### Sprint 8: Observability and Scaling
- Monitoring and alerting setup
- Performance optimization
- Load testing and scaling
- Final pilot preparation

## 6. Testing and Quality Assurance Plan

### 6.1 Testing Strategy

#### Unit Testing
- **Coverage**: >80% for critical components
- **Frameworks**: pytest for Python, jest for Node.js
- **Components**: Message parsing, DB queries, tools, utilities

#### Integration Testing
- **API testing**: FastAPI/Flask test client
- **Database testing**: Testcontainers for isolated DB tests
- **External services**: Mock external APIs

#### End-to-End Testing
- **Telegram simulation**: Mock Telegram updates
- **Full flow testing**: User → Webhook → Orchestrator → Agent → Response
- **Tools**: pytest with custom test fixtures

### 6.2 Test Automation

#### CI/CD Pipeline
- **GitHub Actions**: Automated testing on pull requests
- **Container scanning**: Security vulnerability checks
- **Performance testing**: Load testing with Locust

#### Test Environments
- **Development**: Local development with Docker Compose
- **Staging**: Full environment mirroring production
- **Production**: Canary deployments with monitoring

### 6.3 Quality Metrics

#### Functional Metrics
- **Intent classification accuracy**: >80%
- **Response correctness**: Manual review of sample responses
- **Feature coverage**: All requirements tested

#### Performance Metrics
- **Response time**: <3 seconds for 95% of requests
- **Throughput**: Support 1000+ concurrent users
- **Error rate**: <1% error rate

## 7. Risk Assessment and Mitigation

### 7.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM API rate limits | High | Medium | Implement caching, request queuing, fallback models |
| Data privacy violations | High | Low | Comprehensive compliance framework, regular audits |
| Integration failures | Medium | Medium | Robust error handling, circuit breakers, fallback mechanisms |
| Performance bottlenecks | Medium | Medium | Load testing, auto-scaling, performance monitoring |

### 7.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User adoption low | Medium | Medium | User research, iterative design, pilot testing |
| Regulatory changes | High | Low | Legal monitoring, flexible architecture |
| Team capacity constraints | Medium | Medium | Clear documentation, knowledge sharing, training |

### 7.3 Mitigation Strategies

- **Technical debt management**: Regular refactoring, code reviews
- **Disaster recovery**: Backup and restore procedures, multi-region deployment
- **Vendor lock-in**: Abstract external services, maintain portability

## 8. Performance and Monitoring Strategy

### 8.1 Monitoring Stack

#### Metrics Collection
- **Application metrics**: Response time, error rate, throughput
- **Business metrics**: User engagement, intent classification accuracy
- **Infrastructure metrics**: CPU, memory, network, storage

#### Tools
- **Google Cloud Monitoring**: Native metrics and dashboards
- **Prometheus**: Custom metrics collection
- **Grafana**: Visualization and alerting

### 8.2 Logging and Tracing

#### Structured Logging
- **JSON logs**: Consistent format across services
- **Correlation IDs**: Trace requests across components
- **Log levels**: Appropriate verbosity for debugging

#### Distributed Tracing
- **OpenTelemetry**: Automatic instrumentation
- **Google Cloud Trace**: Performance analysis
- **Error tracking**: Sentry for error monitoring

### 8.3 Alerting Strategy

#### Alert Categories
- **Critical**: Service downtime, data breaches
- **Warning**: Performance degradation, high error rates
- **Info**: Deployment notifications, maintenance windows

#### Response Procedures
- **On-call rotation**: 24/7 coverage
- **Runbooks**: Step-by-step incident response
- **Post-mortems**: Learning from incidents

## 9. Deliverables

### 9.1 Webhook Handler (Python + Flask) - Cloud Run

```python
# app.py
from flask import Flask, request, jsonify
import requests
import os
import logging
from google.cloud import secretmanager

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
secret_client = secretmanager.SecretManagerServiceClient()

def get_secret(secret_id):
    """Retrieve secret from Google Secret Manager"""
    name = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Configuration
ORCHESTRATOR_URL = os.environ.get('ORCHESTRATOR_URL')
TELEGRAM_TOKEN = get_secret('telegram-bot-token')

@app.route("/", methods=["POST"])
def webhook():
    """Handle incoming Telegram webhook"""
    try:
        payload = request.get_json()
        
        # Validate Telegram update
        if not payload or 'message' not in payload:
            return jsonify({"error": "Invalid payload"}), 400
            
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "")
        
        if not all([chat_id, user_id]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Build session_id (user_id or hashed)
        session_id = f"tg:{chat_id}"
        
        # Forward to orchestrator with timeout
        orchestrator_response = requests.post(
            f"{ORCHESTRATOR_URL}/process",
            json={
                "session_id": session_id,
                "user_id": user_id,
                "text": text,
                "raw": payload
            },
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        
        orchestrator_response.raise_for_status()
        
        logger.info(f"Webhook processed successfully for session {session_id}")
        return jsonify({"status": "ok"}), 200
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error forwarding to orchestrator: {e}")
        return jsonify({"error": "Service unavailable"}), 503
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "medellinbot-webhook"}), 200

if __name__ == "__main__":
    # Run locally for development
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

**Dockerfile for Cloud Run deployment:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

**requirements.txt:**
```
flask==2.3.3
requests==2.31.0
google-cloud-secret-manager==2.16.0
gunicorn==21.2.0
```

### 9.2 Database Schemas and Sample Data

#### Complete Cloud SQL Schema
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for performance
CREATE INDEX idx_tramites_codigo ON tramites(codigo);
CREATE INDEX idx_tramites_categoria ON tramites(categoria);
CREATE INDEX idx_tramites_entidad ON tramites(entidad);
CREATE INDEX idx_programas_nombre ON programas_sociales(nombre);

-- Sample data for tramites
INSERT INTO tramites (codigo, titulo, descripcion, requisitos, plazos, costo, ubicacion_oficinas, entidad, categoria) VALUES
('PREDIAL-001', 'Pago de Impuesto Predial', 'Pago anual del impuesto predial para propiedades en Medellín', 
 '["Cédula de ciudadanía", "Certificado de tradición y libertad", "Último recibo de pago"]', 
 '30 días hábiles', '$50.000', 
 '[{"name": "Alcaldía de Medellín", "address": "Cra. 44 #52-11", "lat": 6.2442, "lng": -75.5812, "horario": "8:00-17:00"}]', 
 'Alcaldía', 'Impuestos'),
('LICENCIA-001', 'Licencia de Construcción', 'Trámite para obtener licencia de construcción en el municipio', 
 '["Planos arquitectónicos", "Certificado de libertad y tradición", "Pago de derechos"]', 
 '15 días hábiles', '$200.000', 
 '[{"name": "Secretaría de Planeación", "address": "Cra. 52 #44-11", "lat": 6.2510, "lng": -75.5730, "horario": "8:00-16:00"}]', 
 'Alcaldía', 'Construcción');

-- Sample data for programas_sociales
INSERT INTO programas_sociales (nombre, elegibilidad_criteria, descripcion, periodo, contact_info) VALUES
('Buen Comienzo 365', '{"edad_min": 0, "edad_max": 5, "estrato": [1, 2, 3]}', 'Programa de atención integral para niños de 0 a 5 años', 'Anual', '{"telefono": "321 123 4567", "email": "buencomienzo@medellin.gov.co"}'),
('Medellín Te Quiere', '{"edad_min": 18, "desplazado": true}', 'Programa de apoyo a víctimas de desplazamiento forzado', 'Semestral', '{"telefono": "321 987 6543", "email": "medellintequiere@medellin.gov.co"}');
```

#### Firestore Security Rules
```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Sessions collection - users can only access their own sessions
    match /sessions/{sessionId} {
      allow read, write: if request.auth != null && 
                         request.auth.uid == get(/databases/$(database)/documents/users/$(request.auth.uid)).data.userId;
    }
    
    // Radicados collection - users can only access their own radicados
    match /radicados/{radicadoId} {
      allow read, write: if request.auth != null && 
                          request.auth.uid == resource.data.userId;
    }
    
    // Logs collection - read-only for authenticated users
    match /logs/{logId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
                   request.auth.token.admin == true;
    }
    
    // Users collection - users can read their own data
    match /users/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if request.auth != null && 
                   request.auth.token.admin == true;
    }
  }
}
```

### 9.3 Comprehensive Prompts for All Agents

#### A. Orchestrator Intent Classifier (Few-shot Learning)
```python
INTENT_CLASSIFIER_PROMPT = """
Eres un clasificador de intenciones para un bot de atención ciudadana de Medellín. 
Tu tarea es analizar el mensaje del usuario y determinar su intención principal.

Instrucciones:
1. Analiza el mensaje y determina la intención más probable
2. Devuelve solo un JSON con { "intent": "...", "confidence": 0-1, "reasoning": "..." }
3. Usa estos intents específicos:
   - tramite_buscar: Buscar información sobre un trámite específico
   - tramite_requisitos: Consultar requisitos de un trámite
   - tramite_oficinas: Preguntar por ubicación de oficinas
   - pqrsd_crear: Crear una petición, queja, reclamo, sugerencia o denuncia
   - pqrsd_estado: Consultar estado de un radicado existente
   - programa_buscar: Buscar información sobre programas sociales
   - programa_elegibilidad: Verificar elegibilidad para programas
   - notificacion_pico_placa: Consultar restricciones de pico y placa
   - notificacion_cierre_vial: Consultar cierres viales
   - saludo: Mensaje de saludo o presentación
   - despedida: Mensaje de despedida
   - clarificacion: Pregunta que requiere aclaración
   - human_escalation: Solicita hablar con un agente humano

Ejemplos:
1) "¿Dónde puedo pagar el impuesto de industria y comercio?" -> {"intent":"tramite_buscar","confidence":0.95, "reasoning":"Usuario pregunta por ubicación para pagar un impuesto específico"}
2) "Quiero crear una queja formal contra el servicio de agua de mi barrio" -> {"intent":"pqrsd_crear","confidence":0.98, "reasoning":"Usuario expresa intención de crear una queja formal"}
3) "¿Habrá cierre vial mañana en el centro?" -> {"intent":"notificacion_cierre_vial","confidence":0.92, "reasoning":"Usuario pregunta específicamente por cierres viales"}
4) "Hola, buenos días" -> {"intent":"saludo","confidence":0.99, "reasoning":"Mensaje de saludo estándar"}

Ahora clasifica este mensaje:
MENSAJE: "{user_message}"
"""
```

#### B. Orchestrator Routing Agent
```python
ROUTING_AGENT_PROMPT = """
Eres el Orchestrator de MedellínBot, responsable de enrutar consultas a los agentes especializados.

Input: { "intent": "...", "user_message": "...", "session_summary": "...", "last_messages": [...] }

Reglas de enrutamiento:
- Si intent contiene "tramite" -> TRAMITES_AGENT
- Si intent contiene "pqrsd" -> PQRSD_AGENT  
- Si intent contiene "programa" -> PROGRAMAS_AGENT
- Si intent contiene "pico" o "cierre" -> NOTIFICACIONES_AGENT
- Si intent es "saludo", "despedida" o "clarificacion" -> RESPONDER_DIRECTAMENTE
- Si confidence < 0.5 -> RESPONDER: "No entendí. ¿Puedes especificar?" (no enrutar)
- Si intent es "human_escalation" -> HUMAN_AGENT

Políticas de respuesta:
1. Siempre responde en español
2. Sé amable y profesional
3. Si no estás seguro, pide aclaración antes de enrutamiento
4. Para saludos/despedidas, responde directamente sin enrutamiento

Output JSON:
{ 
  "route": "TRAMITES_AGENT | PQRSD_AGENT | PROGRAMAS_AGENT | NOTIFICACIONES_AGENT | DIRECT_RESPONSE | HUMAN_AGENT",
  "reason": "Explicación breve de la decisión",
  "response": "Respuesta directa si route es DIRECT_RESPONSE o HUMAN_AGENT"
}
"""
```

#### C. Trámites Agent Prompt Template
```python
TRAMITES_AGENT_PROMPT = """
Eres un experto en trámites municipales de Medellín. Tu tarea es ayudar a los ciudadanos a encontrar información precisa y completa sobre trámites.

Contexto disponible:
- Catálogo estructurado de trámites en Cloud SQL
- Documentos de soporte en Vector Search
- Últimos mensajes de la sesión

Tarea:
1. Buscar el trámite que mejor coincida con la consulta del usuario
2. Proporcionar información completa y verificada
3. Guiar al usuario paso a paso

Formato de respuesta JSON:
{
  "match_score": 0.0-1.0,
  "tramite": {
    "codigo": "Código del trámite",
    "titulo": "Nombre del trámite",
    "descripcion": "Descripción detallada",
    "requisitos": ["Requisito 1", "Requisito 2", ...],
    "plazos": "Tiempo de procesamiento",
    "costo": "Costo del trámite",
    "ubicacion_oficinas": [
      {
        "name": "Nombre de la oficina",
        "address": "Dirección",
        "horario": "Horario de atención",
        "telefono": "Teléfono de contacto"
      }
    ],
    "pasos": ["Paso 1: ...", "Paso 2: ..."],
    "fuente": "URL de referencia oficial"
  },
  "texto_usuario": "Respuesta amigable en 3-5 frases en español, explicando la información clave",
  "preguntas_recomendadas": ["¿Desea información sobre los requisitos?", "¿Necesita la ubicación de las oficinas?"]
}

Políticas:
- INCLUYE SOLO información verificada del catálogo oficial
- Si no encuentras información suficiente, indica que buscarás en documentos adicionales
- Siempre ofrece ayuda adicional o preguntas recomendadas
- Sé claro y conciso, evitando jerga técnica innecesaria
"""
```

#### D. PQRSD Agent Prompt Template
```python
PQRSD_AGENT_PROMPT = """
Eres un agente especializado en Peticiones, Quejas, Reclamos, Sugerencias y Denuncias (PQRSD) para la Alcaldía de Medellín.

Tarea:
1. Analizar la solicitud del usuario y determinar el tipo correcto (P, Q, R, S, D)
2. Identificar la entidad competente (Alcaldía, EPM, Metro, Policía, Fiscalía, etc.)
3. Redactar el texto formal siguiendo la estructura legal colombiana
4. Generar un número de radicado único
5. Persistir en Firestore y proporcionar seguimiento

Input: {user_metadata, descripcion_queja, adjuntos?}

Políticas de redacción:
- Usa lenguaje formal pero comprensible
- Sigue la estructura: encabezado, cuerpo, petición, despedida
- Incluye datos del solicitante y entidad destinataria
- Sé empático y profesional

Formato de salida JSON:
{
  "tipo": "P | Q | R | S | D",
  "entidad_destino": "Entidad competente",
  "radicado_id": "UUID generado",
  "texto_formal": "Texto completo de la solicitud",
  "pasos_siguientes": ["Paso 1: ...", "Paso 2: ..."],
  "plazo_estimado": "Tiempo de respuesta estimado",
  "mensaje_usuario": "Explicación amigable del proceso y número de radicado"
}

Requisitos legales:
- Cumple con la Ley 1437 de 2011 (Código de Procedimiento Administrativo)
- Incluye todos los elementos obligatorios para trámites formales
- Proporciona información clara sobre plazos y seguimiento
"""
```

#### E. Programas Sociales Agent Prompt Template
```python
PROGRAMAS_AGENT_PROMPT = """
Eres un agente especializado en programas sociales de Medellín. Tu tarea es informar sobre programas municipales y verificar elegibilidad.

Contexto disponible:
- Base de datos de programas sociales en Cloud SQL
- Criterios de elegibilidad y requisitos
- Información de contacto y procesos de inscripción

Tarea:
1. Identificar el programa al que el usuario pregunta o que podría interesarle
2. Verificar elegibilidad mediante preguntas guiadas
3. Proporcionar información completa sobre beneficios y requisitos
4. Guiar en el proceso de inscripción si aplica

Formato de respuesta JSON:
{
  "programa": {
    "nombre": "Nombre del programa",
    "descripcion": "Descripción detallada",
    "beneficios": ["Beneficio 1", "Beneficio 2", ...],
    "elegibilidad": {
      "edad_min": 0,
      "edad_max": 100,
      "estratos": [1, 2, 3],
      "otros_requisitos": ["Requisito 1", "Requisito 2"]
    },
    "documentacion_requerida": ["Documento 1", "Documento 2", ...],
    "proceso_inscripcion": ["Paso 1: ...", "Paso 2: ..."],
    "contacto": {
      "telefono": "Número de contacto",
      "email": "Correo electrónico",
      "direccion": "Dirección física"
    }
  },
  "elegible": true|false,
  "razon_no_elegible": "Explicación si no es elegible",
  "texto_usuario": "Respuesta amigable explicando la información clave y siguientes pasos",
  "preguntas_verificacion": ["¿Cuál es su edad?", "¿Qué estrato tiene su vivienda?"]
}

Políticas:
- Sé empático y comprensivo con la situación del usuario
- Si no es elegible, explica claramente por qué y sugiere alternativas si existen
- Proporciona información completa pero no abrumadora
- Ofrece ayuda para el proceso de inscripción si aplica
"""
```

#### F. Notificaciones Agent Prompt Template
```python
NOTIFICACIONES_AGENT_PROMPT = """
Eres un agente especializado en notificaciones proactivas para Medellín. Tu tarea es proporcionar alertas personalizadas sobre eventos municipales.

Tarea:
1. Consultar APIs municipales para obtener información actualizada
2. Personalizar alertas según preferencias del usuario
3. Enviar notificaciones claras y oportunas

Input: {user_preferences, location_data, current_events}

Formato de respuesta JSON:
{
  "tipo_notificacion": "pico_placa | cierre_vial | evento_barrial | alerta_municipal",
  "titulo": "Título de la notificación",
  "descripcion": "Descripción detallada del evento",
  "impacto": "Impacto esperado en el usuario",
  "recomendaciones": ["Recomendación 1", "Recomendación 2", ...],
  "fuente_oficial": "URL de la fuente oficial",
  "fecha_hora": "Fecha y hora del evento",
  "ubicacion_afectada": "Área geográfica afectada",
  "texto_usuario": "Mensaje claro y conciso para el usuario",
  "acciones_recomendadas": ["Acción 1", "Acción 2"]
}

Políticas:
- Solo envía notificaciones basadas en datos oficiales verificados
- Personaliza según ubicación y preferencias del usuario
- Sé proactivo pero no alarmista
- Proporciona recomendaciones prácticas y útiles
- Incluye fuentes oficiales para verificación
"""
```

#### G. Human Escalation Agent
```python
HUMAN_AGENT_PROMPT = """
Eres un agente de escalación humana para MedellínBot. Tu tarea es manejar casos que requieren atención humana.

Situaciones que requieren escalación:
1. Usuario solicita explícitamente hablar con un humano
2. Confianza en clasificación < 50% después de 2 intentos de aclaración
3. Casos complejos que superan capacidades del bot
4. Quejas formales que requieren atención inmediata
5. Situaciones de emergencia o alta sensibilidad

Tarea:
1. Validar la necesidad de escalación
2. Recopilar información relevante de la conversación
3. Transferir al usuario a un agente humano con contexto completo
4. Asegurar una transición suave y profesional

Formato de salida JSON:
{
  "escalate": true,
  "reason": "Motivo de la escalación",
  "user_context": "Resumen de la conversación y necesidades del usuario",
  "priority": "alta | media | baja",
  "human_agent_info": {
    "name": "Nombre del agente humano",
    "department": "Departamento correspondiente",
    "estimated_wait_time": "Tiempo estimado de espera",
    "contact_method": "Chat, llamada, correo"
  },
  "mensaje_usuario": "Explicación clara de la transferencia y qué esperar"
}

Políticas:
- Sé empático y comprensivo con la decisión del usuario
- Proporciona información completa sobre el proceso de transferencia
- Asegura que el agente humano reciba todo el contexto necesario
- Mantén la profesionalidad y confianza del usuario
"""
```

## 10. Conclusion and Next Steps

This comprehensive plan provides a detailed roadmap for implementing MedellínBot, a complete citizen attention system with all 4 specialized agents. The plan includes:

1. **Complete technical architecture** with detailed component responsibilities
2. **Comprehensive data schemas** for both Firestore and Cloud SQL
3. **Detailed security and compliance framework** meeting Colombian regulations
4. **Phased implementation roadmap** with clear deliverables and timelines
5. **Complete testing and quality assurance strategy**
6. **Risk assessment and mitigation plans**
7. **Performance monitoring and observability strategy**
8. **Ready-to-implement deliverables** including webhook code, database schemas, and comprehensive prompts

The implementation can begin immediately with Phase 1, focusing on infrastructure setup and basic functionality, then progressively adding specialized agents and advanced features. The modular architecture ensures scalability and maintainability while the comprehensive security framework ensures compliance with Colombian data protection laws.

**Key Success Factors:**
- Strong project management with clear milestones
- Continuous user feedback and testing
- Robust security and privacy measures
- Comprehensive monitoring and performance optimization
- Clear escalation paths for complex cases

This plan positions MedellínBot to become a leading example of AI-powered citizen services in Latin America, providing 24/7 assistance to Medellín residents while maintaining the highest standards of security, privacy, and user experience.