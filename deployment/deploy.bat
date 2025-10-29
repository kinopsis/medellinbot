@echo off
REM MedellínBot Deployment Script for Windows
REM This script deploys all components to Google Cloud Run

setlocal

REM Configuration
set PROJECT_ID=medellinbot-prd-440915
set REGION=us-central1
set IMAGE_REGISTRY=us-central1-docker.pkg.dev
set SERVICE_ACCOUNT=medellinbot-service-account

echo [INFO] Starting MedellínBot deployment...

REM Check if required tools are installed
echo [INFO] Checking requirements...

where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] gcloud CLI is not installed. Please install it first.
    exit /b 1
)

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install it first.
    exit /b 1
)

where kubectl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] kubectl is not installed. Please install it first.
    exit /b 1
)

echo [SUCCESS] All requirements satisfied

REM Authenticate with Google Cloud
echo [INFO] Authenticating with Google Cloud...
gcloud auth list --filter=status:ACTIVE --format="value(account)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Not authenticated with Google Cloud. Please run 'gcloud auth login' first.
    exit /b 1
)

gcloud config set project %PROJECT_ID%
echo [SUCCESS] Authenticated with project: %PROJECT_ID%

REM Enable required APIs
echo [INFO] Enabling required Google Cloud APIs...
for %%A in (
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
) do (
    echo [INFO] Enabling %%A...
    gcloud services enable %%A --project=%PROJECT_ID% 2>nul || echo [WARNING] Failed to enable %%A (may already be enabled)
)

echo [SUCCESS] APIs enabled

REM Create Artifact Registry repository
echo [INFO] Creating Artifact Registry repository...
gcloud artifacts.repositories describe medellinbot --repository-format=docker --location=%REGION% >nul 2>&1
if %errorlevel% neq 0 (
    gcloud artifacts.repositories create medellinbot ^
        --repository-format=docker ^
        --location=%REGION% ^
        --description="MedellínBot container images" ^
        --project=%PROJECT_ID%
    echo [SUCCESS] Artifact Registry repository created
) else (
    echo [SUCCESS] Artifact Registry repository already exists
)

REM Create service account
echo [INFO] Creating service account...
gcloud iam service-accounts describe %SERVICE_ACCOUNT%@%PROJECT_ID%.iam.gserviceaccount.com >nul 2>&1
if %errorlevel% neq 0 (
    gcloud iam service-accounts create %SERVICE_ACCOUNT% ^
        --display-name="MedellínBot Service Account" ^
        --project=%PROJECT_ID%
    
    REM Grant necessary roles
    for %%R in (
        "roles/run.invoker"
        "roles/cloudsql.client"
        "roles/datastore.user"
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
    ) do (
        gcloud projects add-iam-policy-binding %PROJECT_ID% ^
            --member="serviceAccount:%SERVICE_ACCOUNT%@%PROJECT_ID%.iam.gserviceaccount.com" ^
            --role=%%R
    )
    echo [SUCCESS] Service account created and configured
) else (
    echo [SUCCESS] Service account already exists
)

REM Create Firestore database
echo [INFO] Creating Firestore database...
gcloud firestore databases describe --project=%PROJECT_ID% >nul 2>&1
if %errorlevel% neq 0 (
    gcloud firestore databases create ^
        --region=%REGION% ^
        --project=%PROJECT_ID%
    echo [SUCCESS] Firestore database created
) else (
    echo [SUCCESS] Firestore database already exists
)

REM Create Cloud SQL instance
echo [INFO] Creating Cloud SQL instance...
set INSTANCE_NAME=medellinbot-db
gcloud sql instances describe %INSTANCE_NAME% --project=%PROJECT_ID% >nul 2>&1
if %errorlevel% neq 0 (
    gcloud sql instances create %INSTANCE_NAME% ^
        --database-version=POSTGRES_15 ^
        --tier=db-custom-1-3840 ^
        --region=%REGION% ^
        --project=%PROJECT_ID%
    
    gcloud sql databases create medellinbot ^
        --instance=%INSTANCE_NAME% ^
        --project=%PROJECT_ID%
    
    gcloud sql users create medellinbot_user ^
        --instance=%INSTANCE_NAME% ^
        --password="CHANGE_THIS_PASSWORD_IN_PRODUCTION" ^
        --project=%PROJECT_ID%
    echo [SUCCESS] Cloud SQL instance created
) else (
    echo [SUCCESS] Cloud SQL instance already exists
)

REM Create secrets
echo [INFO] Creating secrets in Secret Manager...
gcloud secrets describe telegram-bot-token --project=%PROJECT_ID% >nul 2>&1
if %errorlevel% neq 0 (
    echo YOUR_TELEGRAM_BOT_TOKEN | gcloud secrets create telegram-bot-token ^
        --data-file=- ^
        --project=%PROJECT_ID%
    echo [SUCCESS] Telegram bot token secret created
) else (
    echo [SUCCESS] Telegram bot token secret already exists
)

gcloud secrets describe jwt-secret-key --project=%PROJECT_ID% >nul 2>&1
if %errorlevel% neq 0 (
    openssl rand -base64 32 | gcloud secrets create jwt-secret-key ^
        --data-file=- ^
        --project=%PROJECT_ID%
    echo [SUCCESS] JWT secret created
) else (
    echo [SUCCESS] JWT secret already exists
)

REM Update placeholders in YAML files
echo [INFO] Updating configuration placeholders...
powershell -Command "(Get-Content cloud-run/*.yaml) -replace 'PROJECT_ID', '%PROJECT_ID%' | Set-Content cloud-run/*.yaml"
echo [SUCCESS] Configuration placeholders updated

REM Build and push Docker images
echo [INFO] Building and pushing Docker images...

set COMPONENTS=webhook orchestrator agents/tramites agents/pqrsd agents/programas agents/notificaciones

for %%C in (%COMPONENTS%) do (
    echo [INFO] Building %%C...
    set IMAGE_NAME=%IMAGE_REGISTRY%/%PROJECT_ID%/medellinbot/%%~nC
    docker build -t %IMAGE_NAME% -f %%C/Dockerfile %%C
    docker push %IMAGE_NAME%
    echo [SUCCESS] Built and pushed %%C
)

REM Deploy Cloud Run services
echo [INFO] Deploying Cloud Run services...

echo [INFO] Deploying webhook service...
gcloud run services replace cloud-run/webhook.yaml --project=%PROJECT_ID% --region=%REGION%

echo [INFO] Deploying orchestrator service...
gcloud run services replace cloud-run/orchestrator.yaml --project=%PROJECT_ID% --region=%REGION%

echo [INFO] Deploying specialized agents...
gcloud run services replace cloud-run/agents.yaml --project=%PROJECT_ID% --region=%REGION%

echo [SUCCESS] All services deployed

REM Set up monitoring and logging
echo [INFO] Setting up monitoring and logging...

echo [INFO] Creating log-based metrics...

REM Webhook error rate
gcloud logging metrics create webhook-error-rate ^
    --description="Webhook error rate" ^
    --log-filter="resource.type=\"cloud_run_revision\" resource.labels.service_name=\"medellinbot-webhook\" severity>=ERROR" ^
    --project=%PROJECT_ID% 2>nul || echo [WARNING] Failed to create webhook error rate metric

REM Orchestrator processing time
gcloud logging metrics create orchestrator-processing-time ^
    --description="Orchestrator processing time" ^
    --log-filter="resource.type=\"cloud_run_revision\" resource.labels.service_name=\"medellinbot-orchestrator\" jsonPayload.metadata.processing_time" ^
    --project=%PROJECT_ID% 2>nul || echo [WARNING] Failed to create orchestrator processing time metric

echo [SUCCESS] Monitoring configured

REM Create alerts
echo [INFO] Creating alerting policies...

echo {
echo   "displayName": "Webhook High Error Rate",
echo   "combiner": "OR",
echo   "conditions": [
echo     {
echo       "displayName": "Webhook error rate > 5%",
echo       "conditionThreshold": {
echo         "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"medellinbot-webhook\" AND severity>=ERROR",
echo         "threshold": 0.05,
echo         "duration": "60s"
echo       }
echo     }
echo   ],
echo   "notificationChannels": [],
echo   "alertStrategy": {
echo     "autoClose": "3600s"
echo   }
echo } > webhook-alert.json

gcloud monitoring policies create --policy-from-file=webhook-alert.json --project=%PROJECT_ID% 2>nul || echo [WARNING] Failed to create webhook alert

echo [SUCCESS] Alerts configured

echo [SUCCESS] MedellínBot deployment completed successfully!
echo Services deployed:
echo   - Webhook: https://medellinbot-webhook-%PROJECT_ID%.a.run.app
echo   - Orchestrator: https://medellinbot-orchestrator-%PROJECT_ID%.a.run.app
echo   - Trámites Agent: https://medellinbot-tramites-%PROJECT_ID%.a.run.app
echo   - PQRSD Agent: https://medellinbot-pqrsd-%PROJECT_ID%.a.run.app
echo   - Programas Agent: https://medellinbot-programas-%PROJECT_ID%.a.run.app
echo   - Notificaciones Agent: https://medellinbot-notificaciones-%PROJECT_ID%.a.run.app

endlocal