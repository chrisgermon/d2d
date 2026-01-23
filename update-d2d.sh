#!/bin/bash
# Quick script to update the D2D app in Azure

set -e

RESOURCE_GROUP="d2d-rg"
ACR_NAME="d2dacr9129522"
APP_NAME="d2d-app-vnet"

echo "=== Updating D2D App in Azure ==="
echo ""

echo "Step 1: Building and pushing new Docker image..."
cd /home/claudeagent/d2d
az acr build --registry $ACR_NAME --image d2d:latest . --platform linux

echo ""
echo "Step 2: Updating container app..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/d2d:latest

echo ""
echo "=== ✅ Update Complete! ==="
echo ""
echo "App URL: https://$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)"
echo ""
echo "View logs:"
echo "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
