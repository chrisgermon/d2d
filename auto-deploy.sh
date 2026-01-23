#!/bin/bash

# Auto-deployment script for D2D
# Checks for updates from GitHub and redeploys if changes detected

LOG_FILE="/opt/d2d/auto-deploy.log"
DEPLOY_DIR="/opt/d2d"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Starting auto-deployment check"
log "========================================="

cd "$DEPLOY_DIR" || {
    log "ERROR: Cannot change to $DEPLOY_DIR"
    exit 1
}

# Fetch latest changes
log "Fetching latest changes from GitHub..."
git fetch origin master 2>&1 | tee -a "$LOG_FILE"

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No updates available. Already up to date."
    exit 0
fi

log "New changes detected!"
log "Local:  $LOCAL"
log "Remote: $REMOTE"

# Pull changes
log "Pulling changes..."
git pull origin master 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    log "ERROR: Git pull failed"
    exit 1
fi

# Stop containers
log "Stopping containers..."
sudo docker-compose down 2>&1 | tee -a "$LOG_FILE"

# Rebuild
log "Rebuilding containers..."
sudo docker-compose build 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    log "ERROR: Build failed"
    exit 1
fi

# Start containers
log "Starting containers..."
sudo docker-compose up -d 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    log "ERROR: Failed to start containers"
    exit 1
fi

# Wait for app to start
log "Waiting for application to start..."
sleep 10

# Test application
log "Testing application..."
if curl -f -s http://localhost:8000/ > /dev/null; then
    log "✓ Application is running successfully"
else
    log "✗ WARNING: Application may not be running correctly"
fi

# Show status
log "Container status:"
sudo docker-compose ps 2>&1 | tee -a "$LOG_FILE"

log "========================================="
log "Deployment complete!"
log "========================================="

# Keep last 1000 lines of log
tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
