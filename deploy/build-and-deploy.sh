#!/bin/bash


set -e

# Configuration
PROJECT_ID="first-renderer-462920-t5"
REGION="us-central1"
API_IMAGE="gcr.io/${PROJECT_ID}/healthy-snack-api"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/healthy-snack-frontend"

echo "🚀 Starting deployment to GCP..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"

# Enable required APIs
echo "📋 Enabling required GCP APIs..."
gcloud services enable containerregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Configure Docker for GCR
echo "🔧 Configuring Docker for Google Container Registry..."
gcloud auth configure-docker

# Build and push API image with multi-arch support
echo "🏗️  Building and pushing API image..."
docker buildx build --platform linux/amd64 \
  -f docker/Dockerfile.api \
  -t ${API_IMAGE}:latest \
  --push .

# Build and push Frontend image with multi-arch support
echo "🏗️  Building and pushing Frontend image..."
docker buildx build --platform linux/amd64 \
  -f docker/Dockerfile.frontend \
  -t ${FRONTEND_IMAGE}:latest \
  --push .

echo "✅ Images built and pushed successfully!"

# Deploy API to Cloud Run
echo "🚀 Deploying API to Cloud Run..."
gcloud run deploy healthy-snack-api \
  --image ${API_IMAGE}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10 \
  --set-env-vars "API_HOST=0.0.0.0,API_PORT=8000,LOG_LEVEL=INFO,REQUEST_TIMEOUT_S=60,MAX_CONCURRENCY=5" \
  --quiet

# Get API URL
API_URL=$(gcloud run services describe healthy-snack-api --region=${REGION} --format="value(status.url)")
echo "API deployed at: ${API_URL}"

# Deploy Frontend to Cloud Run
echo "🚀 Deploying Frontend to Cloud Run..."
gcloud run deploy healthy-snack-frontend \
  --image ${FRONTEND_IMAGE}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 7860 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10 \
  --set-env-vars "API_BASE_URL=${API_URL},FRONTEND_PORT=7860" \
  --quiet

# Get Frontend URL
FRONTEND_URL=$(gcloud run services describe healthy-snack-frontend --region=${REGION} --format="value(status.url)")

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📱 Frontend URL: ${FRONTEND_URL}"
echo "🔗 API URL: ${API_URL}"
echo "📊 API Health: ${API_URL}/health"
echo "📚 API Docs: ${API_URL}/docs"
echo ""
echo "⚠️  IMPORTANT: Don't forget to set your OPENAI_API_KEY in the environment variables!"
echo "   You can update it using:"
echo "   gcloud run services update healthy-snack-api --region=${REGION} --set-env-vars OPENAI_API_KEY=your_api_key_here"
echo "   gcloud run services update healthy-snack-frontend --region=${REGION} --update-env-vars API_BASE_URL=${API_URL}"