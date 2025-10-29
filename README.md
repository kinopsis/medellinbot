# MedellínBot - Intelligent Citizen Assistant

![MedellínBot Architecture](docs/architecture.png)

## Overview

MedellínBot is an AI-powered citizen assistance system for the municipality of Medellín, Colombia. It provides 24/7 automated support through Telegram for municipal procedures, PQRSD (Petitions, Complaints, Claims, Suggestions, Denunciations), social programs, and proactive notifications.

## Features

### 🤖 AI-Powered Assistance
- **Intent Classification**: Advanced NLP for understanding citizen requests
- **Specialized Agents**: Dedicated AI agents for different municipal services
- **Context Management**: Maintains conversation context for natural interactions
- **Multilingual Support**: Fully in Spanish with cultural adaptation

### 🏛️ Municipal Services
- **Trámites Municipales**: Information about municipal procedures, requirements, costs, and locations
- **PQRSD Management**: Automated creation and tracking of citizen petitions and complaints
- **Programas Sociales**: Information and eligibility verification for social programs
- **Notificaciones Proactivas**: Real-time alerts for traffic, events, and municipal announcements

### 🔒 Security & Compliance
- **Data Protection**: Compliant with Colombian data protection laws (Law 1581 of 2012)
- **Authentication**: Secure JWT-based authentication and authorization
- **Audit Logging**: Comprehensive logging for monitoring and compliance
- **Rate Limiting**: Protection against abuse and DDoS attacks

### 🚀 Cloud-Native Architecture
- **Microservices**: Independent, scalable components on Google Cloud Run
- **Serverless**: Auto-scaling with pay-per-use pricing
- **High Availability**: 99.9% uptime with automatic failover
- **Monitoring**: Real-time metrics and alerting

## Architecture

### High-Level Architecture

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

### Components

#### 1. Webhook Handler (Cloud Run)
- **Purpose**: Receives and processes Telegram webhook events
- **Features**:
  - Rate limiting and DDoS protection
  - Authentication and authorization
  - Request validation and normalization
  - Forwarding to orchestrator with timeout handling

#### 2. Orchestrator (Cloud Run)
- **Purpose**: Main routing and intent classification engine
- **Features**:
  - Intent classification using LLM
  - Conversation context management
  - Session state persistence
  - Routing to specialized agents

#### 3. Specialized Agents (Cloud Run)
- **Trámites Agent**: Municipal procedures and services
- **PQRSD Agent**: Petitions, complaints, and formal requests
- **Programas Sociales Agent**: Social programs and eligibility
- **Notificaciones Agent**: Proactive alerts and notifications

#### 4. Data Layer
- **Firestore**: Session management and conversation history
- **Cloud SQL**: Structured data for trámites and social programs
- **Vector Search**: Document embeddings and semantic search

## Quick Start

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Google Cloud SDK** installed and configured
3. **Docker** for local development
4. **Telegram Bot Token** from @BotFather

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/medellinbot.git
   cd medellinbot
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**:
   ```bash
   # Webhook
   cd webhook && pip install -r requirements.txt
   
   # Orchestrator
   cd ../orchestrator && pip install -r requirements.txt
   
   # Agents
   cd ../agents/tramites && pip install -r requirements.txt
   ```

4. **Run services locally**:
   ```bash
   # Webhook (port 8080)
   cd webhook && python app.py
   
   # Orchestrator (port 8081)
   cd orchestrator && python app.py
   
   # Trámites Agent (port 8082)
   cd agents/tramites && python app.py
   ```

### Production Deployment

1. **Configure deployment script**:
   ```bash
   cd deployment
   export PROJECT_ID="your-project-id"
   export REGION="us-central1"
   ```

2. **Run deployment**:
   ```bash
   ./deploy.sh deploy
   ```

3. **Run database migrations**:
   ```bash
   gcloud sql connect medellinbot-db --user=medellinbot_user
   \i deployment/migrate.sql
   ```

## Configuration

### Environment Variables

#### Webhook
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `ORCHESTRATOR_URL`: URL of the orchestrator service
- `ENVIRONMENT`: Environment name (development/production)
- `REQUIRE_AUTH`: Require JWT authentication (true/false)
- `RATE_LIMIT_REQUESTS`: Number of requests per window
- `RATE_LIMIT_WINDOW`: Rate limit window in seconds

#### Orchestrator
- `JWT_SECRET`: JWT signing secret
- `SESSION_TIMEOUT_HOURS`: Session timeout in hours
- `CONFIDENCE_THRESHOLD`: Minimum confidence for intent classification
- `TRAMITES_AGENT_URL`: URL of trámites agent
- `PQRSD_AGENT_URL`: URL of PQRSD agent
- `PROGRAMAS_AGENT_URL`: URL of programas agent
- `NOTIFICACIONES_AGENT_URL`: URL of notificaciones agent

#### Agents
- `DB_HOST`: Cloud SQL database host
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `LLM_PROVIDER`: LLM provider (vertex-ai/openai)
- `LLM_MODEL`: LLM model name
- `LLM_TEMPERATURE`: LLM temperature setting

### Secrets Management

Store sensitive information in Google Secret Manager:

```bash
# Telegram Bot Token
gcloud secrets create telegram-bot-token --data-file=token.txt

# JWT Secret
openssl rand -base64 32 | gcloud secrets create jwt-secret-key --data-file=-
```

## API Reference

### Webhook Endpoints

#### POST /process
Process incoming Telegram webhook events.

**Request**:
```json
{
  "session_id": "string",
  "user_id": "string",
  "chat_id": "string",
  "text": "string",
  "raw": "object"
}
```

**Response**:
```json
{
  "status": "ok",
  "session_id": "string",
  "processing_time": 0.123
}
```

#### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "medellinbot-webhook",
  "timestamp": "2025-10-29T00:00:00Z"
}
```

### Orchestrator Endpoints

#### POST /process
Process user requests and route to appropriate agents.

**Request**:
```json
{
  "session_id": "string",
  "user_id": "string",
  "user_message": "string",
  "conversation_context": "object",
  "intent": "string"
}
```

**Response**:
```json
{
  "response": "string",
  "suggested_actions": ["string"],
  "metadata": {
    "processing_time": 0.123,
    "intent": "string",
    "confidence": 0.95
  }
}
```

#### GET /session/{session_id}
Get session information.

**Response**:
```json
{
  "session_id": "string",
  "user_id": "string",
  "created_at": "2025-10-29T00:00:00Z",
  "last_active": "2025-10-29T00:00:00Z",
  "message_count": 10,
  "memory_summary": "string"
}
```

### Agent Endpoints

All agents follow the same interface pattern:

#### POST /process
Process specialized requests.

**Request**:
```json
{
  "user_message": "string",
  "conversation_context": "object",
  "intent": "string"
}
```

**Response**:
```json
{
  "match_score": 0.95,
  "tramite": {
    "codigo": "string",
    "titulo": "string",
    "descripcion": "string",
    "requisitos": ["string"],
    "plazos": "string",
    "costo": "string",
    "ubicacion_oficinas": [
      {
        "name": "string",
        "address": "string",
        "horario": "string",
        "telefono": "string",
        "lat": 0.0,
        "lng": 0.0
      }
    ],
    "pasos": ["string"],
    "fuente": "string",
    "documentos_adjuntos": ["string"]
  },
  "texto_usuario": "string",
  "preguntas_recomendadas": ["string"],
  "alternativas": [
    {
      "codigo": "string",
      "titulo": "string",
      "razon_similitud": "string"
    }
  ]
}
```

## Database Schema

### Cloud SQL Tables

#### tramites
```sql
CREATE TABLE tramites (
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
    active BOOLEAN DEFAULT true
);
```

#### programas_sociales
```sql
CREATE TABLE programas_sociales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    elegibilidad_criteria JSONB,
    descripcion TEXT,
    periodo VARCHAR(100),
    contact_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true
);
```

### Firestore Collections

#### sessions/{sessionId}
```javascript
{
  user_id: string,
  created_at: timestamp,
  last_active: timestamp,
  messages: array,
  memory_summary: string,
  user_preferences: object
}
```

#### radicados/{radicadoId}
```javascript
{
  user_id: string,
  tipo: string,
  entidad: string,
  status: string,
  created_at: timestamp,
  meta: object,
  attachments: array
}
```

## Security

### Data Protection
- **Encryption at Rest**: All data encrypted using Google Cloud's default encryption
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Access Control**: IAM roles with principle of least privilege
- **Audit Logging**: Comprehensive logging for all data access

### Authentication
- **JWT Tokens**: Secure authentication for all services
- **Service Accounts**: Dedicated service accounts for each component
- **Secret Management**: Sensitive data stored in Google Secret Manager

### Compliance
- **Law 1581 of 2012**: Colombian data protection law compliance
- **GDPR Principles**: Data minimization, accuracy, storage limitation
- **Regular Audits**: Security and compliance audits

## Monitoring & Observability

### Metrics
- **Request Rate**: Requests per second by service
- **Error Rate**: Percentage of failed requests
- **Latency**: Response time percentiles
- **Database Performance**: Query performance and connection pools

### Logging
- **Structured Logging**: JSON logs with consistent format
- **Correlation IDs**: Trace requests across services
- **Log-based Metrics**: Automatic metric creation from logs

### Alerting
- **Service Downtime**: Immediate alerts for service unavailability
- **High Error Rate**: Alerts when error rate exceeds thresholds
- **Performance Degradation**: Alerts for increased latency
- **Security Events**: Alerts for suspicious activities

## Testing

### Unit Tests
```bash
# Run webhook tests
cd webhook && python -m pytest tests/

# Run orchestrator tests
cd orchestrator && python -m pytest tests/

# Run agent tests
cd agents/tramites && python -m pytest tests/
```

### Integration Tests
```bash
# Run integration tests
cd tests/integration && python -m pytest
```

### Load Testing
```bash
# Install Locust
pip install locust

# Run load tests
locust -f tests/load/test_webhook.py --users 100 --spawn-rate 10 --host https://your-service-url
```

## Contributing

### Development Workflow
1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make changes** with comprehensive tests
4. **Run linting**: `black . && flake8 .`
5. **Submit pull request** with detailed description

### Code Standards
- **Python**: Follow PEP 8 style guide
- **Documentation**: Comprehensive docstrings for all functions
- **Testing**: Minimum 80% code coverage
- **Security**: Security review for all changes

### Issue Tracking
- **Bug Reports**: Include reproduction steps and expected behavior
- **Feature Requests**: Describe use case and implementation approach
- **Security Issues**: Report via security contact, not public issues

## Deployment

### Continuous Deployment
The project uses GitHub Actions for CI/CD:

1. **Code Push**: Triggers automated tests
2. **Build**: Creates Docker images
3. **Deploy**: Deploys to staging environment
4. **Promote**: Manual approval for production deployment

### Environment Configuration

#### Development
- **Services**: Local Docker containers
- **Database**: Local PostgreSQL
- **Authentication**: Mock JWT tokens
- **LLM**: Mock responses

#### Staging
- **Services**: Cloud Run (reduced scale)
- **Database**: Cloud SQL (staging instance)
- **Authentication**: Real JWT tokens
- **LLM**: Real API calls

#### Production
- **Services**: Cloud Run (full scale)
- **Database**: Cloud SQL (production instance)
- **Authentication**: Real JWT tokens with rotation
- **LLM**: Real API calls with rate limiting

## Support

### Documentation
- [API Documentation](docs/api.md)
- [Architecture Guide](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [Security Guide](docs/security.md)

### Community
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time community support
- **Email**: support@medellinbot.gov.co

### Professional Support
For enterprise support and customization:
- **Consulting Services**: Architecture and implementation
- **Training**: Team training and knowledge transfer
- **Maintenance**: Ongoing support and updates

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing Organizations

- **Alcaldía de Medellín**: Project sponsor and requirements
- **Secretaría de Tecnología**: Technical oversight and integration
- **Universidad de Antioquia**: Research and development support
- **Google Cloud**: Cloud infrastructure and AI expertise

## Acknowledgments

- **Municipal Staff**: For their dedication to citizen service
- **Open Source Community**: For their contributions and support
- **Beta Testers**: For their feedback and suggestions
- **Citizens of Medellín**: For their trust and engagement

---

*MedellínBot - Transforming citizen services through AI and cloud technology*"# Medell�nBot Project" 
