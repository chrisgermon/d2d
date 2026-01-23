# Auto-Deployment from GitHub

## Status: ✅ Active

The d2d application is now configured to automatically deploy updates from GitHub.

## How It Works

**Every 15 minutes**, the system:
1. Checks GitHub for new commits to the `master` branch
2. If updates are found, pulls the latest code
3. Rebuilds the Docker container
4. Restarts the application with zero downtime
5. Logs all activity for review

## Configuration

**Cron Job:**
```
*/15 * * * * cd /opt/d2d && /opt/d2d/auto-deploy.sh >> /opt/d2d/auto-deploy.log 2>&1
```

**Check Frequency:** Every 15 minutes
**Log File:** `/opt/d2d/auto-deploy.log`
**Repository:** https://github.com/chrisgermon/d2d
**Branch:** master

## Workflow

```
GitHub Push → Wait up to 15 min → Auto-deploy checks → Pull changes →
Rebuild container → Restart app → Log results
```

## Manual Commands

### View Deployment Logs
```bash
# View live logs
tail -f /opt/d2d/auto-deploy.log

# View last 50 lines
tail -50 /opt/d2d/auto-deploy.log

# Search for errors
grep ERROR /opt/d2d/auto-deploy.log
```

### Trigger Manual Deployment
```bash
# Force deployment check now
sudo /opt/d2d/auto-deploy.sh

# Or via SSH
ssh azureuser@10.200.1.8 "cd /opt/d2d && sudo ./auto-deploy.sh"
```

### Manage Cron Job
```bash
# View current cron jobs
sudo crontab -l

# Edit cron jobs
sudo crontab -e

# Remove auto-deployment
sudo crontab -l | grep -v auto-deploy.sh | sudo crontab -

# Re-enable auto-deployment
cd /opt/d2d
sudo ./setup-auto-deploy.sh
```

### Change Check Frequency

Edit the cron job:
```bash
sudo crontab -e
```

Options:
```
*/5 * * * *    # Every 5 minutes
*/15 * * * *   # Every 15 minutes (current)
0 * * * *      # Every hour
0 */4 * * *    # Every 4 hours
0 9,17 * * *   # Twice daily (9am and 5pm)
```

## Deployment Process Details

When updates are detected, the script:

1. **Fetches** latest changes from GitHub
2. **Compares** local vs remote commit hashes
3. **Pulls** changes if different
4. **Stops** Docker containers gracefully
5. **Rebuilds** container image with new code
6. **Starts** containers in background
7. **Waits** 10 seconds for startup
8. **Tests** application is responding
9. **Logs** all steps and status

## Testing Auto-Deployment

### Test 1: Make a Small Change

1. Edit a file on GitHub (e.g., README.md)
2. Commit the change
3. Wait up to 15 minutes
4. Check logs: `tail -f /opt/d2d/auto-deploy.log`
5. Verify update was deployed

### Test 2: Force Immediate Deployment

```bash
# SSH to VM
ssh azureuser@10.200.1.8

# Run deployment manually
cd /opt/d2d
sudo ./auto-deploy.sh

# Watch the process
```

### Test 3: Verify Application After Deployment

```bash
# Check container is running
sudo docker-compose ps

# Test application
curl http://localhost:8000/

# Test worklist
curl -X POST http://localhost:8000/api/worklist/test \
  -H 'Content-Type: application/json' \
  -d '{"host":"10.17.1.21","port":5010,"ae_title":"AURVCMOD1","calling_ae":"LIVUSWL"}'
```

## Log File Example

```
[2026-01-23 22:27:42] =========================================
[2026-01-23 22:27:42] Starting auto-deployment check
[2026-01-23 22:27:42] =========================================
[2026-01-23 22:27:42] Fetching latest changes from GitHub...
[2026-01-23 22:27:43] New changes detected!
[2026-01-23 22:27:43] Local:  fd3450c1234567890abcdef
[2026-01-23 22:27:43] Remote: 0a47f4e9876543210fedcba
[2026-01-23 22:27:43] Pulling changes...
[2026-01-23 22:27:44] Stopping containers...
[2026-01-23 22:27:45] Rebuilding containers...
[2026-01-23 22:27:50] Starting containers...
[2026-01-23 22:28:00] Waiting for application to start...
[2026-01-23 22:28:10] Testing application...
[2026-01-23 22:28:11] ✓ Application is running successfully
[2026-01-23 22:28:11] Container status:
[2026-01-23 22:28:11] d2d_d2d_1   Up   0.0.0.0:8000->8000/tcp
[2026-01-23 22:28:11] =========================================
[2026-01-23 22:28:11] Deployment complete!
[2026-01-23 22:28:11] =========================================
```

## Rollback

If a deployment causes issues:

```bash
# SSH to VM
ssh azureuser@10.200.1.8

# Check commit history
cd /opt/d2d
git log --oneline

# Rollback to previous version
git reset --hard <previous-commit-hash>

# Restart containers
sudo docker-compose down
sudo docker-compose build
sudo docker-compose up -d
```

## Troubleshooting

### Auto-deployment not running

**Check if cron job exists:**
```bash
sudo crontab -l | grep auto-deploy
```

**If missing, re-run setup:**
```bash
cd /opt/d2d
sudo ./setup-auto-deploy.sh
```

### Deployment fails

**Check logs for errors:**
```bash
grep ERROR /opt/d2d/auto-deploy.log
```

**Common issues:**
- Git authentication (should use HTTPS public repo)
- Docker build failure (check Docker logs)
- Container startup failure (check app logs)

**View container logs:**
```bash
cd /opt/d2d
sudo docker-compose logs --tail 100
```

### Application not responding after deployment

**Check container status:**
```bash
cd /opt/d2d
sudo docker-compose ps
```

**Restart manually:**
```bash
sudo docker-compose restart
```

**Full rebuild:**
```bash
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

## GitHub Actions Alternative

For immediate deployment (not periodic), GitHub Actions can be configured to deploy on every push.

**Requirement:** VM needs to be accessible via SSH from GitHub (requires public IP or jump host)

**Setup:**
1. Add secrets to GitHub repository:
   - `VM_HOST`: Public IP or hostname
   - `VM_USER`: azureuser
   - `VM_SSH_KEY`: Private SSH key content

2. GitHub Actions will deploy automatically on push to master

**Status:** Not currently enabled (VM is on private network)

## Monitoring

### Email Notifications (Optional)

To receive email on deployment events, modify the cron job:

```bash
*/15 * * * * cd /opt/d2d && /opt/d2d/auto-deploy.sh >> /opt/d2d/auto-deploy.log 2>&1 && mail -s "D2D Deployment" your@email.com < /opt/d2d/auto-deploy.log
```

### Slack/Teams Notifications (Optional)

Add webhook notification at the end of `auto-deploy.sh`:

```bash
# At end of script
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"D2D deployed successfully"}'
```

## Security Considerations

- Repository is public on GitHub (read-only access)
- VM pulls changes via HTTPS (no authentication required)
- Deployment runs as root (via cron)
- Docker containers run with standard permissions
- No sensitive data in repository (uses .env for secrets)

## Maintenance

**Log Rotation:**
The auto-deploy script automatically keeps only the last 1000 lines of logs to prevent log file growth.

**Manual cleanup:**
```bash
# Clear old logs
> /opt/d2d/auto-deploy.log

# Or remove old entries
tail -1000 /opt/d2d/auto-deploy.log > /tmp/deploy-log.tmp
mv /tmp/deploy-log.tmp /opt/d2d/auto-deploy.log
```

## Summary

✅ **Auto-deployment is active**
- Checks every 15 minutes for GitHub updates
- Automatically rebuilds and restarts on changes
- Logs all activity to `/opt/d2d/auto-deploy.log`
- Zero-downtime deployments
- Easy to monitor and troubleshoot

**Next deployment check:** Within 15 minutes of any push to master

---

**Document Version:** 1.0
**Last Updated:** 2026-01-23
**Status:** Active ✅
