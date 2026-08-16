#!/usr/bin/env bash
set -euo pipefail

AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-rag-mcp-azure}"
# Use a region that is available for your subscription.
# If Azure rejects this value, run: az account list-locations -o table
# and replace LOCATION with a supported region.
LOCATION="${LOCATION:-northeurope}"
ACR_NAME="${ACR_NAME:-ragmcpazureacr}"
CONTAINERAPP_ENV="${CONTAINERAPP_ENV:-cae-rag-mcp-azure}"
CONTAINERAPP_NAME="${CONTAINERAPP_NAME:-rag-mcp-azure}"
IMAGE_NAME="rag-mcp-azure"

if [ -z "$AZURE_SUBSCRIPTION_ID" ]; then
  echo "AZURE_SUBSCRIPTION_ID is required. Example: export AZURE_SUBSCRIPTION_ID='<subscription-id>'"
  exit 1
fi

az login
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App --wait

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

az acr create \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Basic >/dev/null

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"

az containerapp env create \
  --name "$CONTAINERAPP_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" >/dev/null

az acr login --name "$ACR_NAME"

docker build -t "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest" .
docker push "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest"

az containerapp create \
  --name "$CONTAINERAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINERAPP_ENV" \
  --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest" \
  --target-port 8000 \
  --ingress external \
  --registry-server "$ACR_LOGIN_SERVER" \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 1 \
  --max-replicas 2

echo "Deployment complete. Container App URL:"
az containerapp show --name "$CONTAINERAPP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv
