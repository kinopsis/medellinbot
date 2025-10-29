# Web Scraping Service Deployment Guide
## MedellínBot - Production Deployment Documentation

### Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)
9. [Rollback Procedures](#rollback-procedures)

---

## Overview

This document provides comprehensive guidance for deploying the Web Scraping Service for MedellínBot to production environments. The service is designed to run on Google Cloud Platform using Cloud Run, with supporting infrastructure including Cloud SQL, Cloud Storage, and Cloud Monitoring.

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud Run     │    │  Cloud SQL      │    │ Cloud Storage   │
│  (Web Scraping │◄──►│   (PostgreSQL)  │◄──►│   (Data Files)  │
│    Service)     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Cloud Scheduler │    │ Cloud Monitoring│    │  Secret Manager │
│   (Triggers)    │    │   (Metrics)     │    │   (Secrets)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

- **Web Scraping Service**: Main application container running scraping logic
- **Cloud SQL**: PostgreSQL database for structured data storage
- **Cloud Storage**: Object storage for raw scraped data and files
- **Cloud Scheduler**: Automated job scheduling for periodic scraping
- **Cloud Monitoring**: Metrics collection and alerting
- **Secret Manager**: Secure storage for sensitive configuration

---

## Prerequisites

### Required Tools and Accounts

#### Google Cloud Platform
- [ ] Google Cloud account with billing enabled
- [ ] Project created and configured
- [ ] Required APIs enabled:
  - Cloud Run API
  - Cloud Build API
  - Artifact Registry API
  - Cloud SQL API
  - Cloud Storage API
  - Monitoring API
  - Logging API
  - Cloud Scheduler API
  - Secret Manager API

#### Development Tools
- [ ] Google Cloud SDK (`gcloud`)
- [ ] Docker
- [ ] Git
- [ ] Python 3.11+
- [ ] Kubernetes CLI (`kubectl`)
- [ ] Helm (optional)

#### Access Requirements
- [ ] IAM permissions for service account management
- [ ] Database admin permissions
- [ ] Storage admin permissions
- [ ] Cloud Run admin permissions

### Environment Variables

Before deployment, ensure the following environment variables are set:

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="web-scraping-service"
export DATABASE_NAME="web_scraping_db"
export BUCKET_NAME="web-scraping-data-bucket"
```

---

## Environment Setup

### 1. Project Configuration

```bash
# Set project and region
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
gcloud config set run/platform managed

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Container Registry Setup

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create web-scraping-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for web scraping service"

# Configure Docker to use Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev
```

### 3. Database Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create web-scraping-db \
    --database-version=POSTGRES_14 \
    --tier=db-custom-1-3840 \
    --region=$REGION \
    --root-password=your-root-password

# Create database
gcloud sql databases create web_scraping_db \
    --instance=web-scraping-db

# Create user
gcloud sql users create scraping_user \
    --instance=web-scraping-db \
    --password=your-user-password

# Get database connection string
gcloud sql instances describe web-scraping-db --format="value(connectionName)"
```

### 4. Storage Setup

```bash
# Create Cloud Storage bucket
gsutil mb -l $REGION gs://$BUCKET_NAME

# Set bucket permissions
gsutil iam ch serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://$BUCKET_NAME
```

### 5. Service Account Setup

```bash
# Create service account
gcloud iam service-accounts create web-scraping-service \
    --display-name="Web Scraping Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"
```

---

## Deployment Process

### 1. Build and Push Container Image

```bash
# Build container image
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/web-scraping-repo/web-scraping-service:latest -f deployment/Dockerfile .

# Push to Artifact Registry
docker push $REGION-docker.pkg.dev/$PROJECT_ID/web-scraping-repo/web-scraping-service:latest
```

### 2. Configure Secrets

```bash
# Store database password as secret
echo "your-database-password" | gcloud secrets create database-password --data-file=-

# Store other sensitive configuration
gcloud secrets create scraping-config --data-file=config/secrets.json
```

### 3. Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy web-scraping-service \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/web-scraping-repo/web-scraping-service:latest \
    --platform=managed \
    --region=$REGION \
    --service-account=web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com \
    --allow-unauthenticated-invocations \
    --port=8000 \
    --cpu-throttling=false \
    --concurrency=80 \
    --timeout=900 \
    --memory=4Gi \
    --cpu=2 \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=$BUCKET_NAME,LOG_LEVEL=INFO,ENABLE_PROMETHEUS=true,PROMETHEUS_PORT=8000" \
    --set-secrets="DATABASE_PASSWORD=database-password:latest" \
    --description="Web Scraping Service for MedellínBot"
```

### 4. Configure Scheduled Jobs

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe web-scraping-service --platform=managed --region=$REGION --format="value(status.url)")

# Create scheduler job for hourly scraping
gcloud scheduler jobs create http web-scraping-scheduler \
    --schedule="0 * * * *" \
    --uri="$SERVICE_URL/scrape" \
    --http-method=POST \
    --message-body='{"source":"all","force_refresh":false}' \
    --oidc-service-account-email=web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com \
    --oidc-token-audience=$SERVICE_URL
```

### 5. Database Migration

```bash
# Run database migrations
gcloud run jobs execute web-scraping-migration --region=$REGION --platform=managed
```

---

## Post-Deployment Validation

### 1. Service Health Check

```bash
# Check service status
gcloud run services describe web-scraping-service --platform=managed --region=$REGION

# Test health endpoint
curl https://web-scraping-service-$PROJECT_ID.a.run.app/health

# Test readiness endpoint
curl https://web-scraping-service-$PROJECT_ID.a.run.app/ready
```

### 2. Functionality Testing

```bash
# Test scraping endpoint
curl -X POST https://web-scraping-service-$PROJECT_ID.a.run.app/scrape \
    -H "Content-Type: application/json" \
    -d '{"source":"alcaldia_medellin","force_refresh":false}'

# Test metrics endpoint
curl https://web-scraping-service-$PROJECT_ID.a.run.app/metrics
```

### 3. Database Validation

```bash
# Connect to database
gcloud sql connect web-scraping-db --user=scraping_user

# Verify tables exist
\dt

# Check recent data
SELECT * FROM scraping_results ORDER BY created_at DESC LIMIT 10;
```

### 4. Monitoring Setup Verification

```bash
# Check logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=web-scraping-service' --limit=10

# Verify metrics
gcloud monitoring metrics list --filter="web_scraping"
```

---

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- `web_scraping_requests_total`: Total number of scraping requests
- `web_scraping_errors_total`: Total number of errors
- `web_scraping_scraper_duration_seconds`: Scraper execution time
- `web_scraping_data_quality_score`: Quality score of scraped data
- `web_scraping_database_connections_active`: Active database connections

#### Infrastructure Metrics
- CPU utilization
- Memory usage
- Network I/O
- Disk usage
- Request latency

### Alert Configuration

#### Critical Alerts
- Service downtime (> 1 minute)
- High error rate (> 10% of requests)
- Database connection failures
- Data quality score < 0.7
- Scraper timeout (> 5 minutes)

#### Warning Alerts
- High CPU usage (> 80%)
- High memory usage (> 80%)
- Slow response times (> 30 seconds)
- Database connection pool exhaustion

### Dashboard Setup

Use the provided Grafana dashboard configuration to set up monitoring dashboards:

```bash
# Apply monitoring configuration
kubectl apply -f monitoring/staging-monitoring-config.yaml
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Deployment Failures

**Issue**: Container image build fails
**Solution**:
```bash
# Check Docker build logs
docker build --no-cache -t test-image -f deployment/Dockerfile .

# Verify dependencies
pip install -r requirements.txt
```

**Issue**: Cloud Run deployment fails
**Solution**:
```bash
# Check deployment logs
gcloud run services describe web-scraping-service --platform=managed --region=$REGION --format="yaml"

# Verify service account permissions
gcloud iam service-accounts describe web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com
```

#### 2. Database Connection Issues

**Issue**: Cannot connect to Cloud SQL
**Solution**:
```bash
# Test database connection
gcloud sql connect web-scraping-db --user=scraping_user

# Check connection string format
# Should be: postgresql://user:password@host:5432/database

# Verify IAM permissions
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:web-scraping-service@$PROJECT_ID.iam.gserviceaccount.com"
```

#### 3. Performance Issues

**Issue**: High memory usage
**Solution**:
```bash
# Check memory usage
gcloud monitoring metrics list --filter="memory"

# Review scraping configuration
# Consider reducing concurrency or batch sizes
```

**Issue**: Slow scraping performance
**Solution**:
```bash
# Check rate limiting configuration
# Review target website restrictions
# Consider adding caching
```

#### 4. Monitoring Issues

**Issue**: Metrics not appearing
**Solution**:
```bash
# Verify Prometheus configuration
# Check service discovery
# Test metrics endpoint
curl http://localhost:8000/metrics
```

### Log Analysis

```bash
# View recent logs
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=web-scraping-service' --limit=50

# Filter by error level
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' --limit=20

# Search for specific errors
gcloud logging read 'jsonPayload.message:"database connection failed"'
```

---

## Maintenance

### Regular Tasks

#### Daily
- [ ] Monitor service health and performance
- [ ] Review error logs
- [ ] Check data quality metrics
- [ ] Verify scheduled jobs are running

#### Weekly
- [ ] Review resource usage and costs
- [ ] Update dependencies if needed
- [ ] Clean up old logs and data
- [ ] Test backup and restore procedures

#### Monthly
- [ ] Review and update security configurations
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Documentation updates

### Database Maintenance

```bash
# Regular backups
gcloud sql backups create --instance=web-scraping-db

# Monitor disk usage
gcloud sql instances describe web-scraping-db --format="value(diskUsageBytes)"

# Check connection limits
gcloud sql instances describe web-scraping-db --format="value(settings.databaseFlags)"
```

### Security Maintenance

#### Regular Security Tasks
- [ ] Review IAM permissions quarterly
- [ ] Update secrets and passwords annually
- [ ] Security scanning of container images
- [ ] Vulnerability assessment of dependencies
- [ ] Review and update firewall rules

#### Incident Response
1. **Detection**: Monitor alerts and logs for security events
2. **Containment**: Isolate affected systems if necessary
3. **Investigation**: Analyze logs and metrics to understand the issue
4. **Recovery**: Restore normal operations
5. **Post-incident**: Document and review the incident

---

## Rollback Procedures

### When to Rollback

Rollback should be performed when:
- Critical errors are detected in production
- Performance degradation affects users
- Security vulnerabilities are discovered
- Data corruption is detected
- Monitoring indicates system instability

### Rollback Steps

#### 1. Immediate Actions
```bash
# Stop traffic to current version
gcloud run services update-traffic web-scraping-service \
    --platform=managed \
    --region=$REGION \
    --to-revisions=REVISION_NAME \
    --remove-traffic=latest
```

#### 2. Database Rollback (if needed)
```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID --instance=web-scraping-db
```

#### 3. Configuration Rollback
```bash
# Revert environment variables
gcloud run services update web-scraping-service \
    --platform=managed \
    --region=$REGION \
    --set-env-vars="OLD_CONFIG_VALUES"
```

#### 4. Verification
```bash
# Test rolled back version
curl https://web-scraping-service-$PROJECT_ID.a.run.app/health

# Monitor for stability
gcloud monitoring dashboards list
```

### Rollback Verification Checklist

- [ ] Service health check passes
- [ ] Database connectivity verified
- [ ] Key functionality tested
- [ ] Performance within acceptable ranges
- [ ] No critical errors in logs
- [ ] Monitoring alerts cleared

---

## Contact Information

### Support Team
- **DevOps Team**: devops@medellinbot.com
- **Database Admin**: dba@medellinbot.com
- **Security Team**: security@medellinbot.com
- **On-Call Engineer**: +1-555-ONCALL

### Emergency Procedures
1. **Page on-call engineer** for critical issues
2. **Escalate to team leads** if not resolved within 30 minutes
3. **Contact management** for business-impacting issues
4. **Document incident** in tracking system

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-29 | DevOps Team | Initial deployment guide |

---

*This document should be reviewed and updated after each deployment cycle.*