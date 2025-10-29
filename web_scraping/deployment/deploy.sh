#!/bin/bash

# Web Scraping Service Deployment Script
# This script automates the deployment of the web scraping service to Google Cloud Platform

set -e  # Exit on any error

# Configuration
PROJECT_ID=${PROJECT_ID:?"PROJECT_ID environment variable must be set"}
REGION=${REGION:="us-central1"}
SERVICE_NAME="web-scraping-service"
REPOSITORY_NAME="web-scraping-repo"
IMAGE_NAME="web-scraping-service"
BUCKET_NAME="web-scraping-data-bucket"
SERVICE_ACCOUNT="web-scraping-service-account"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if required tools are installed
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install it first."
    fi
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
    fi
    
    log "Dependencies check completed."
}

# Authenticate with Google Cloud
authenticate() {
    log "Authenticating with Google Cloud..."
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with Google Cloud. Please run 'gcloud auth login' first."
    fi
    
    gcloud config set project $PROJECT_ID
    log "Authenticated with project: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    log "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log "Enabling $api..."
        gcloud services enable $api --project=$PROJECT_ID || warn "Failed to enable $api (may already be enabled)"
    done
    
    log "APIs enabled successfully."
}

# Create Artifact Registry repository
create_repository() {
    log "Creating Artifact Registry repository..."
    
    if ! gcloud artifacts repositories describe $REPOSITORY_NAME --repository-format=docker --location=$REGION &> /dev/null; then
        log "Creating repository $REPOSITORY_NAME..."
        gcloud artifacts.repositories create $REPOSITORY_NAME \
            --repository-format=docker \
            --location=$REGION \
            --description="Docker repository for web scraping service"
    else
        log "Repository $REPOSITORY_NAME already exists."
    fi
}

# Build and push Docker image
build_and_push_image() {
    log "Building and pushing Docker image..."
    
    local image_tag="us-central1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$IMAGE_NAME:latest"
    
    # Build the image
    docker build -t $image_tag -f deployment/Dockerfile .
    
    # Push to Artifact Registry
    docker push $image_tag
    
    log "Image built and pushed successfully: $image_tag"
}

# Create Cloud SQL instance (if needed)
create_cloud_sql() {
    log "Checking Cloud SQL instance..."
    
    # This is a placeholder - in production, you would want to check if the instance exists
    # and create it if it doesn't. For now, we'll just log a message.
    warn "Cloud SQL instance setup is not automated in this script."
    warn "Please ensure your Cloud SQL instance is created and configured."
    warn "Set the DATABASE_URL environment variable with your database connection string."
}

# Create Cloud Storage bucket
create_bucket() {
    log "Creating Cloud Storage bucket..."
    
    if ! gsutil ls gs://$BUCKET_NAME &> /dev/null; then
        log "Creating bucket $BUCKET_NAME..."
        gsutil mb -l $REGION gs://$BUCKET_NAME
        log "Bucket created successfully."
    else
        log "Bucket $BUCKET_NAME already exists."
    fi
}

# Create service account
create_service_account() {
    log "Creating service account..."
    
    local sa_email="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"
    
    if ! gcloud iam service-accounts describe $sa_email &> /dev/null; then
        log "Creating service account $SERVICE_ACCOUNT..."
        gcloud iam service-accounts create $SERVICE_ACCOUNT \
            --display-name="Web Scraping Service Account"
        
        # Add necessary roles
        local roles=(
            "roles/run.invoker"
            "roles/cloudsql.client"
            "roles/storage.objectAdmin"
            "roles/logging.logWriter"
            "roles/monitoring.metricWriter"
        )
        
        for role in "${roles[@]}"; do
            log "Granting role $role to service account..."
            gcloud projects add-iam-policy-binding $PROJECT_ID \
                --member="serviceAccount:$sa_email" \
                --role="$role"
        done
        
        log "Service account created and configured successfully."
    else
        log "Service account $SERVICE_ACCOUNT already exists."
    fi
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log "Deploying to Cloud Run..."
    
    local image_tag="us-central1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$IMAGE_NAME:latest"
    local sa_email="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Create or update the Cloud Run service
    gcloud run deploy $SERVICE_NAME \
        --image=$image_tag \
        --platform=managed \
        --region=$REGION \
        --service-account=$sa_email \
        --allow-unauthenticated-invocations \
        --port=8000 \
        --cpu-throttling=false \
        --concurrency=80 \
        --timeout=900 \
        --memory=4Gi \
        --cpu=2 \
        --set-env-vars="DATABASE_URL=YOUR_DATABASE_URL,GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=$BUCKET_NAME,LOG_LEVEL=INFO,ENABLE_PROMETHEUS=true,PROMETHEUS_PORT=8000" \
        --description="Web Scraping Service for MedellínBot"
    
    log "Service deployed successfully."
}

# Create Cloud Scheduler job for periodic scraping
create_scheduler_job() {
    log "Creating Cloud Scheduler job..."
    
    # Get the service URL
    local service_url=$(gcloud run services describe $SERVICE_NAME \
        --platform=managed \
        --region=$REGION \
        --format="value(status.url)")
    
    if [ -z "$service_url" ]; then
        warn "Could not get service URL. Skipping scheduler job creation."
        return
    fi
    
    # Create a scheduler job that triggers scraping every hour
    local job_name="web-scraping-scheduler"
    
    if ! gcloud scheduler jobs describe $job_name &> /dev/null; then
        log "Creating Cloud Scheduler job $job_name..."
        gcloud scheduler jobs create http $job_name \
            --schedule="0 * * * *" \
            --uri="$service_url/scrape" \
            --http-method=POST \
            --message-body='{"source":"all","force_refresh":false}' \
            --oidc-service-account-email=$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
            --oidc-token-audience=$service_url
        log "Scheduler job created successfully."
    else
        log "Scheduler job $job_name already exists."
    fi
}

# Setup monitoring and alerting
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Create a basic monitoring dashboard
    log "Creating monitoring dashboard..."
    
    # This would typically involve creating custom metrics and dashboards
    # For now, we'll just log a message
    warn "Manual setup required for monitoring dashboards and alerting policies."
    warn "Consider setting up alerts for:"
    warn "  - High error rates"
    warn "  - Low data quality scores"
    warn "  - Scraper timeouts"
    warn "  - Database connection issues"
}

# Main deployment function
main() {
    log "Starting web scraping service deployment..."
    
    check_dependencies
    authenticate
    enable_apis
    create_repository
    build_and_push_image
    create_bucket
    create_service_account
    deploy_to_cloud_run
    create_scheduler_job
    setup_monitoring
    
    log "Deployment completed successfully!"
    log ""
    log "Next steps:"
    log "1. Configure your Cloud SQL database and update DATABASE_URL"
    log "2. Set up monitoring dashboards and alerting policies"
    log "3. Test the deployment by visiting the service URL"
    log "4. Monitor logs using: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME'"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build-only")
        check_dependencies
        authenticate
        build_and_push_image
        ;;
    "deploy-only")
        authenticate
        deploy_to_cloud_run
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [deploy|build-only|deploy-only|help]"
        echo ""
        echo "Commands:"
        echo "  deploy       - Full deployment (default)"
        echo "  build-only   - Only build and push Docker image"
        echo "  deploy-only  - Only deploy to Cloud Run"
        echo "  help         - Show this help message"
        ;;
    *)
        error "Unknown command: $1"
        echo "Usage: $0 [deploy|build-only|deploy-only|help]"
        exit 1
        ;;
esac