#!/bin/bash

# MedellínBot Deployment Script
# This script deploys all components to Google Cloud Run

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"medellinbot-prd-440915"}
REGION=${REGION:-"us-central1"}
IMAGE_REGISTRY=${IMAGE_REGISTRY:-"us-central1-docker.pkg.dev"}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-"medellinbot-service-account"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    log "Checking requirements..."
    
    if ! gcloud version &> /dev/null; then
        error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! docker --version &> /dev/null; then
        error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    if ! kubectl version --client &> /dev/null; then
        error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    success "All requirements satisfied"
}

# Authenticate with Google Cloud
authenticate() {
    log "Authenticating with Google Cloud..."
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with Google Cloud. Please run 'gcloud auth login' first."
        exit 1
    fi
    
    gcloud config set project $PROJECT_ID
    success "Authenticated with project: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    log "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "firestore.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
        "servicemanagement.googleapis.com"
        "iam.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log "Enabling $api..."
        gcloud services enable $api --project=$PROJECT_ID || warning "Failed to enable $api (may already be enabled)"
    done
    
    success "APIs enabled"
}

# Create Artifact Registry repository
create_registry() {
    log "Creating Artifact Registry repository..."
    
    if ! gcloud artifacts repositories describe medellinbot --repository-format=docker --location=$REGION &> /dev/null; then
        gcloud artifacts repositories create medellinbot \
            --repository-format=docker \
            --location=$REGION \
            --description="MedellínBot container images" \
            --project=$PROJECT_ID
        success "Artifact Registry repository created"
    else
        success "Artifact Registry repository already exists"
    fi
}

# Build and push Docker images
build_images() {
    log "Building and pushing Docker images..."
    
    local components=("webhook" "orchestrator" "agents/tramites" "agents/pqrsd" "agents/programas" "agents/notificaciones")
    
    for component in "${components[@]}"; do
        log "Building $component..."
        
        local image_name="$IMAGE_REGISTRY/$PROJECT_ID/medellinbot/$(basename $component)"
        
        # Build image
        docker build -t $image_name -f $component/Dockerfile $component
        
        # Push to registry
        docker push $image_name
        
        success "Built and pushed $component"
    done
}

# Create service account
create_service_account() {
    log "Creating service account..."
    
    if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null; then
        gcloud iam service-accounts create $SERVICE_ACCOUNT \
            --display-name="MedellínBot Service Account" \
            --project=$PROJECT_ID
        
        # Grant necessary roles
        local roles=(
            "roles/run.invoker"
            "roles/cloudsql.client"
            "roles/datastore.user"
            "roles/secretmanager.secretAccessor"
            "roles/logging.logWriter"
            "roles/monitoring.metricWriter"
        )
        
        for role in "${roles[@]}"; do
            gcloud projects add-iam-policy-binding $PROJECT_ID \
                --member="serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
                --role=$role
        done
        
        success "Service account created and configured"
    else
        success "Service account already exists"
    fi
}

# Deploy Cloud Run services
deploy_services() {
    log "Deploying Cloud Run services..."
    
    # Update placeholders in YAML files
    log "Updating configuration placeholders..."
    powershell -Command "(Get-Content cloud-run/*.yaml) -replace 'PROJECT_ID', '$PROJECT_ID' | Set-Content cloud-run/*.yaml"
    
    # Deploy webhook
    log "Deploying webhook service..."
    gcloud run services replace cloud-run/webhook.yaml --project=$PROJECT_ID --region=$REGION
    
    # Deploy orchestrator
    log "Deploying orchestrator service..."
    gcloud run services replace cloud-run/orchestrator.yaml --project=$PROJECT_ID --region=$REGION
    
    # Deploy agents
    log "Deploying specialized agents..."
    gcloud run services replace cloud-run/agents.yaml --project=$PROJECT_ID --region=$REGION
    
    success "All services deployed"
}

# Create Firestore database
create_firestore() {
    log "Creating Firestore database..."
    
    if ! gcloud firestore databases describe --project=$PROJECT_ID &> /dev/null; then
        gcloud firestore databases create \
            --region=$REGION \
            --project=$PROJECT_ID
        success "Firestore database created"
    else
        success "Firestore database already exists"
    fi
}

# Create Cloud SQL instance
create_cloud_sql() {
    log "Creating Cloud SQL instance..."
    
    local instance_name="medellinbot-db"
    
    if ! gcloud sql instances describe $instance_name --project=$PROJECT_ID &> /dev/null; then
        gcloud sql instances create $instance_name \
            --database-version=POSTGRES_15 \
            --tier=db-custom-1-3840 \
            --region=$REGION \
            --project=$PROJECT_ID
        
        # Create database
        gcloud sql databases create medellinbot \
            --instance=$instance_name \
            --project=$PROJECT_ID
        
        # Create user
        gcloud sql users create medellinbot_user \
            --instance=$instance_name \
            --password="CHANGE_THIS_PASSWORD_IN_PRODUCTION" \
            --project=$PROJECT_ID
        
        success "Cloud SQL instance created"
    else
        success "Cloud SQL instance already exists"
    fi
}

# Create secrets
create_secrets() {
    log "Creating secrets in Secret Manager..."
    
    # Telegram bot token
    if ! gcloud secrets describe telegram-bot-token --project=$PROJECT_ID &> /dev/null; then
        echo "YOUR_TELEGRAM_BOT_TOKEN" | gcloud secrets create telegram-bot-token \
            --data-file=- \
            --project=$PROJECT_ID
        success "Telegram bot token secret created"
    else
        success "Telegram bot token secret already exists"
    fi
    
    # JWT secret
    if ! gcloud secrets describe jwt-secret-key --project=$PROJECT_ID &> /dev/null; then
        openssl rand -base64 32 | gcloud secrets create jwt-secret-key \
            --data-file=- \
            --project=$PROJECT_ID
        success "JWT secret created"
    else
        success "JWT secret already exists"
    fi
}

# Set up monitoring and logging
setup_monitoring() {
    log "Setting up monitoring and logging..."
    
    # Create log-based metrics
    log "Creating log-based metrics..."
    
    # Webhook error rate
    gcloud logging metrics create webhook-error-rate \
        --description="Webhook error rate" \
        --log-filter='resource.type="cloud_run_revision" resource.labels.service_name="medellinbot-webhook" severity>=ERROR' \
        --project=$PROJECT_ID || warning "Failed to create webhook error rate metric"
    
    # Orchestrator processing time
    gcloud logging metrics create orchestrator-processing-time \
        --description="Orchestrator processing time" \
        --log-filter='resource.type="cloud_run_revision" resource.labels.service_name="medellinbot-orchestrator" jsonPayload.metadata.processing_time' \
        --project=$PROJECT_ID || warning "Failed to create orchestrator processing time metric"
    
    success "Monitoring configured"
}

# Create alerts
create_alerts() {
    log "Creating alerting policies..."
    
    # Webhook error rate alert
    cat > /tmp/webhook-alert.json << 'EOF'
{
  "displayName": "Webhook High Error Rate",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Webhook error rate > 5%",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"medellinbot-webhook\" AND severity>=ERROR",
        "threshold": 0.05,
        "duration": "60s"
      }
    }
  ],
  "notificationChannels": [],
  "alertStrategy": {
    "autoClose": "3600s"
  }
}
EOF

    gcloud monitoring policies create --policy-from-file=/tmp/webhook-alert.json --project=$PROJECT_ID || warning "Failed to create webhook alert"
    
    success "Alerts configured"
}

# Main deployment function
main() {
    log "Starting MedellínBot deployment..."
    
    check_requirements
    authenticate
    enable_apis
    create_registry
    create_service_account
    create_firestore
    create_cloud_sql
    create_secrets
    build_images
    deploy_services
    setup_monitoring
    create_alerts
    
    success "MedellínBot deployment completed successfully!"
    log "Services deployed:"
    log "  - Webhook: https://medellinbot-webhook-$PROJECT_ID.a.run.app"
    log "  - Orchestrator: https://medellinbot-orchestrator-$PROJECT_ID.a.run.app"
    log "  - Trámites Agent: https://medellinbot-tramites-$PROJECT_ID.a.run.app"
    log "  - PQRSD Agent: https://medellinbot-pqrsd-$PROJECT_ID.a.run.app"
    log "  - Programas Agent: https://medellinbot-programas-$PROJECT_ID.a.run.app"
    log "  - Notificaciones Agent: https://medellinbot-notificaciones-$PROJECT_ID.a.run.app"
}

# Handle script arguments
case "${1:-}" in
    "deploy")
        main
        ;;
    "build-only")
        check_requirements
        authenticate
        build_images
        ;;
    "deploy-only")
        check_requirements
        authenticate
        deploy_services
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [deploy|build-only|deploy-only|help]"
        echo ""
        echo "Commands:"
        echo "  deploy      - Full deployment (default)"
        echo "  build-only  - Build and push images only"
        echo "  deploy-only - Deploy services only"
        echo "  help        - Show this help message"
        ;;
    *)
        main
        ;;
esac