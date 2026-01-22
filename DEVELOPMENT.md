# D2D Development & Deployment Workflow

## Making Changes to the App

### Local Development Workflow

#### 1. Make Your Changes

**Backend (Python):**
```bash
cd /opt/d2d

# Edit backend files
nano app/main.py              # API endpoints
nano app/dicom_converter.py   # Conversion logic
nano app/dicom_sender.py      # DICOM send logic
nano app/models.py            # Data models
```

**Frontend (HTML/CSS/JS):**
```bash
# Edit frontend files
nano static/index.html        # HTML structure
nano static/styles.css        # Styling
nano static/app.js            # JavaScript logic
```

**Configuration:**
```bash
nano .env                     # Environment variables
nano requirements.txt         # Python dependencies
```

#### 2. Test Locally

**Option A: Run with Python (Fastest for testing)**
```bash
cd /opt/d2d
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With `--reload`, the server automatically restarts when you save files!

**Option B: Test with Docker**
```bash
cd /opt/d2d
docker build -t d2d:local .
docker run -p 8000:8000 -v $(pwd)/dicom_archive:/app/dicom_archive d2d:local
```

**Access locally:** http://10.60.60.172:8000

#### 3. Commit Your Changes

```bash
cd /opt/d2d
git add .
git commit -m "Description of your changes"
git push origin master  # If you have a remote repo
```

---

## Deploy to Azure

### Quick Update (Recommended)

**One command to rebuild and deploy:**
```bash
cd /opt/d2d
./update-azure.sh
```

I'll create this script for you (see below).

### Manual Update Process

**Step 1: Rebuild and push Docker image**
```bash
cd /opt/d2d

# Get your ACR name (from deployment)
ACR_NAME="d2dacr12345"  # Replace with yours

# Login to ACR
az acr login --name $ACR_NAME

# Build and push new image
az acr build --registry $ACR_NAME --image d2d:latest .
```

**Step 2: Update Container App**
```bash
# Get your app name (from deployment)
APP_NAME="d2d-app-67890"  # Replace with yours
RESOURCE_GROUP="d2d-rg"

# Update the app
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/d2d:latest
```

**Step 3: Verify deployment**
```bash
# Check status
az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.runningStatus" -o tsv

# View logs
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

---

## Update Scripts

### Create update-azure.sh

```bash
cat > /opt/d2d/update-azure.sh << 'EOF'
#!/bin/bash
set -e

# Configuration - Update these after first deployment
ACR_NAME=""
APP_NAME=""
RESOURCE_GROUP="d2d-rg"

# Check if variables are set
if [ -z "$ACR_NAME" ] || [ -z "$APP_NAME" ]; then
    echo "❌ Please edit update-azure.sh and set ACR_NAME and APP_NAME"
    echo ""
    echo "Find them with:"
    echo "  az containerapp list --resource-group $RESOURCE_GROUP -o table"
    echo "  az acr list --resource-group $RESOURCE_GROUP -o table"
    exit 1
fi

echo "=== Updating D2D in Azure ==="
echo ""
echo "📦 Container Registry: $ACR_NAME"
echo "🚀 App Name: $APP_NAME"
echo ""

# Login to ACR
echo "Step 1: Logging in to Azure Container Registry..."
az acr login --name $ACR_NAME

# Build and push
echo "Step 2: Building and pushing new image..."
az acr build --registry $ACR_NAME --image d2d:latest . --output none

# Update container app
echo "Step 3: Updating Container App..."
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/d2d:latest \
  --output none

echo ""
echo "✅ Update complete!"
echo ""
echo "View status:"
echo "  az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.runningStatus"
echo ""
echo "View logs:"
echo "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""

# Get URL
APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "🌐 App URL: https://$APP_URL"
echo ""
EOF

chmod +x /opt/d2d/update-azure.sh
```

### After First Deployment

Edit the script with your details:
```bash
nano /opt/d2d/update-azure.sh
```

Set:
```bash
ACR_NAME="d2dacr12345"     # From deployment output
APP_NAME="d2d-app-67890"    # From deployment output
```

Then updates are just:
```bash
cd /opt/d2d
./update-azure.sh
```

---

## Common Development Scenarios

### Scenario 1: Quick UI Change

**Example:** Change button color

```bash
cd /opt/d2d
nano static/styles.css

# Make your change
# Save file

# Test locally (with auto-reload)
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# When satisfied, deploy
git commit -am "Change button color"
./update-azure.sh
```

⏱️ **Time:** 2-3 minutes

### Scenario 2: Add New DICOM Tag

**Example:** Add PatientAge field

```bash
cd /opt/d2d

# 1. Update data model
nano app/models.py
# Add: patient_age: Optional[str] = None

# 2. Update conversion logic
nano app/dicom_converter.py
# Add: if metadata.patient_age:
#          ds.PatientAge = metadata.patient_age

# 3. Update frontend form
nano static/index.html
# Add input field for patient age

# 4. Update frontend JavaScript
nano static/app.js
# Add patient_age to getMetadata() function

# 5. Test locally
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Deploy
git commit -am "Add patient age field"
./update-azure.sh
```

⏱️ **Time:** 10-15 minutes

### Scenario 3: Add New Python Dependency

**Example:** Add image enhancement library

```bash
cd /opt/d2d

# 1. Add to requirements.txt
echo "opencv-python==4.8.0" >> requirements.txt

# 2. Install locally
source venv/bin/activate
pip install opencv-python

# 3. Use in code
nano app/dicom_converter.py
# import cv2
# ... use opencv functions ...

# 4. Test locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Deploy (Docker will install new dependency)
git commit -am "Add image enhancement"
./update-azure.sh
```

⏱️ **Time:** 5-10 minutes

### Scenario 4: Change Environment Variables

**Example:** Increase max file size

```bash
# In Azure Container Apps
az containerapp update \
  --name $APP_NAME \
  --resource-group d2d-rg \
  --set-env-vars MAX_FILE_SIZE=100000000

# No rebuild needed!
```

⏱️ **Time:** 30 seconds

---

## Testing Strategy

### Local Testing Checklist

Before deploying to Azure, test:

- [ ] Upload a PDF - converts successfully
- [ ] Upload a JPG - converts successfully
- [ ] Upload a PNG - converts successfully
- [ ] Edit metadata - all fields work
- [ ] Test DICOM send (if PACS available locally)
- [ ] Download archived file
- [ ] Check browser console for errors
- [ ] Test on mobile browser

### Azure Testing Checklist

After deployment:

- [ ] Access HTTPS URL
- [ ] Upload and convert a file
- [ ] Check archives are persistent (upload, restart app, check archives)
- [ ] Test DICOM send to your PACS
- [ ] Check logs for errors: `az containerapp logs show --follow`

---

## Rollback to Previous Version

### Option 1: Revert Git Changes

```bash
cd /opt/d2d

# View recent commits
git log --oneline -5

# Revert to previous commit
git revert HEAD
git push

# Deploy reverted version
./update-azure.sh
```

### Option 2: Use Tagged Versions

```bash
# Before deploying changes, tag current version
git tag -a v1.0 -m "Stable version"
git push --tags

# To rollback:
git checkout v1.0
./update-azure.sh

# Return to latest:
git checkout master
```

### Option 3: Deploy Specific Image Tag

```bash
# Tag images in ACR when deploying
az acr build --registry $ACR_NAME --image d2d:v1.0 .
az acr build --registry $ACR_NAME --image d2d:latest .

# Rollback to specific version
az containerapp update \
  --name $APP_NAME \
  --resource-group d2d-rg \
  --image $ACR_NAME.azurecr.io/d2d:v1.0
```

---

## Development Tips

### Hot Reload for Fast Development

Keep this running while developing:
```bash
cd /opt/d2d
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Changes to Python files auto-reload!

### Debug Mode

Add debug logging:
```bash
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs locally:
```bash
# Logs print to console
```

View logs in Azure:
```bash
az containerapp logs show --name $APP_NAME --resource-group d2d-rg --follow
```

### Test DICOM Without PACS

```bash
# Use Orthanc as a test PACS
docker run -p 4242:4242 -p 8042:8042 orthancteam/orthanc

# Add as destination in D2D:
# Name: Local Orthanc
# AE Title: ORTHANC
# Host: 172.17.0.1  (Docker host)
# Port: 4242

# View received images: http://localhost:8042
# Username: orthanc
# Password: orthanc
```

---

## File Structure Quick Reference

```
/opt/d2d/
├── app/
│   ├── main.py              ← API endpoints, routes
│   ├── dicom_converter.py   ← PDF/Image → DICOM conversion
│   ├── dicom_sender.py      ← DICOM C-STORE logic
│   ├── models.py            ← Data models (metadata, etc)
│   └── config.py            ← Settings, paths
├── static/
│   ├── index.html           ← Web interface structure
│   ├── styles.css           ← Styling (colors, layout)
│   └── app.js               ← Frontend logic (upload, convert)
├── requirements.txt         ← Python dependencies
├── Dockerfile               ← Container build instructions
├── .env                     ← Local configuration
├── update-azure.sh          ← Quick update script
└── deploy-to-azure.sh       ← Initial deployment script
```

---

## Complete Workflow Summary

```bash
# 1. Make changes
nano app/main.py

# 2. Test locally
source venv/bin/activate
uvicorn app.main:app --reload

# 3. Commit
git add .
git commit -m "Add feature"

# 4. Deploy to Azure
./update-azure.sh

# 5. Verify
# Access HTTPS URL and test
```

**Total time for simple change:** 2-5 minutes
**Total time for complex feature:** 15-30 minutes

---

## Getting Help

**View deployed app info:**
```bash
az containerapp show --name $APP_NAME --resource-group d2d-rg
```

**View recent revisions:**
```bash
az containerapp revision list --name $APP_NAME --resource-group d2d-rg -o table
```

**Check resource usage:**
```bash
az containerapp show --name $APP_NAME --resource-group d2d-rg \
  --query "properties.template.containers[0].resources"
```

**Monitor costs:**
```bash
az consumption usage list --output table
```
