#!/bin/bash

# Setup auto-deployment for D2D
# This script configures automatic deployment from GitHub

echo "========================================="
echo "D2D Auto-Deployment Setup"
echo "========================================="
echo ""

# Make auto-deploy script executable
chmod +x /opt/d2d/auto-deploy.sh

echo "✓ Made auto-deploy.sh executable"

# Create cron job
# Options:
# 1. Every 5 minutes: */5 * * * *
# 2. Every 15 minutes: */15 * * * *
# 3. Every hour: 0 * * * *
# 4. Every 4 hours: 0 */4 * * *

read -p "How often should it check for updates? (5min/15min/hourly/4hourly) [15min]: " FREQUENCY
FREQUENCY=${FREQUENCY:-15min}

case $FREQUENCY in
    5min)
        CRON_SCHEDULE="*/5 * * * *"
        DESCRIPTION="every 5 minutes"
        ;;
    15min)
        CRON_SCHEDULE="*/15 * * * *"
        DESCRIPTION="every 15 minutes"
        ;;
    hourly)
        CRON_SCHEDULE="0 * * * *"
        DESCRIPTION="every hour"
        ;;
    4hourly)
        CRON_SCHEDULE="0 */4 * * *"
        DESCRIPTION="every 4 hours"
        ;;
    *)
        echo "Invalid option. Using default: every 15 minutes"
        CRON_SCHEDULE="*/15 * * * *"
        DESCRIPTION="every 15 minutes"
        ;;
esac

# Remove existing cron job if any
crontab -l 2>/dev/null | grep -v "auto-deploy.sh" | crontab -

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE /opt/d2d/auto-deploy.sh >> /opt/d2d/auto-deploy.log 2>&1") | crontab -

echo ""
echo "✓ Cron job configured to check $DESCRIPTION"
echo ""
echo "Current crontab:"
crontab -l | grep auto-deploy
echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "The system will now automatically:"
echo "1. Check for updates from GitHub $DESCRIPTION"
echo "2. Pull new changes if available"
echo "3. Rebuild and restart containers"
echo "4. Log all activity to /opt/d2d/auto-deploy.log"
echo ""
echo "Commands:"
echo "  View logs:        tail -f /opt/d2d/auto-deploy.log"
echo "  Manual deploy:    /opt/d2d/auto-deploy.sh"
echo "  View cron jobs:   crontab -l"
echo "  Remove auto-deploy: crontab -l | grep -v auto-deploy.sh | crontab -"
echo ""
