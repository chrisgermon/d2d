# Integrating D2D into Your Cloud Run MCP Service

Quick guide to add D2D tools to your existing `crowdit-mcp` Cloud Run service.

## TL;DR

1. Copy `d2d-tools.js` to your MCP service repo
2. Import and merge tools in your server code
3. Set `D2D_API_URL` environment variable in Cloud Run
4. Deploy

## Step-by-Step

### 1. Add the Module to Your Repo

```bash
# In your crowdit-mcp repository
mkdir -p lib/tools
cp /path/to/d2d-tools.js lib/tools/

# Or download from GitHub
curl -o lib/tools/d2d-tools.js \
  https://raw.githubusercontent.com/chrisgermon/d2d/master/mcp-module/d2d-tools.js
```

### 2. Update Your Dependencies

Add to `package.json`:

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "node-fetch": "^3.3.2",
    "form-data": "^4.0.0"
  }
}
```

Run:
```bash
npm install
```

### 3. Integrate into Your MCP Server

Assuming your server is in `src/index.js` or similar:

```javascript
import { d2dTools, handleD2dTool } from '../lib/tools/d2d-tools.js';

// ... your existing code ...

// Merge D2D tools with your existing tools
const allTools = [
  ...yourExistingTools,
  ...d2dTools,
];

// In your ListToolsRequestSchema handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: allTools };
});

// In your CallToolRequestSchema handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Route D2D tools
  if (name.startsWith('d2d_')) {
    return await handleD2dTool(name, args);
  }

  // Your existing tool routing
  // ...
});
```

### 4. Configure Environment Variables

You need to tell your Cloud Run service where your D2D server is.

#### Option A: Cloud Console

1. Go to Cloud Run
2. Select your `crowdit-mcp` service
3. Click "Edit & Deploy New Revision"
4. Go to "Variables & Secrets" tab
5. Add:
   - Name: `D2D_API_URL`
   - Value: `http://YOUR_D2D_SERVER:8000`
6. Optional: Add `D2D_API_KEY` if authentication is enabled
7. Deploy

#### Option B: gcloud CLI

```bash
gcloud run services update crowdit-mcp \
  --region us-central1 \
  --set-env-vars="D2D_API_URL=http://YOUR_D2D_SERVER:8000"
```

With API key:
```bash
gcloud run services update crowdit-mcp \
  --region us-central1 \
  --set-env-vars="D2D_API_URL=http://YOUR_D2D_SERVER:8000,D2D_API_KEY=your-key"
```

#### Option C: Using Secret Manager (Recommended)

```bash
# Store D2D API key
echo -n "your-d2d-api-key" | \
  gcloud secrets create d2d-api-key --data-file=-

# Update Cloud Run to use secret
gcloud run services update crowdit-mcp \
  --region us-central1 \
  --set-env-vars="D2D_API_URL=http://YOUR_D2D_SERVER:8000" \
  --set-secrets="D2D_API_KEY=d2d-api-key:latest"
```

### 5. Handle Network Connectivity

Your Cloud Run service needs to reach your D2D server. Choose based on where D2D is:

#### D2D is on-prem (most common)

**Option 1: Public IP + Firewall**

Simplest approach:

```bash
# On your D2D server (dicomtools)
# Allow Cloud Run IP ranges
sudo ufw allow from 34.96.0.0/20 to any port 8000
sudo ufw allow from 35.187.0.0/16 to any port 8000

# Get list of Cloud Run IPs
# https://www.gstatic.com/ipranges/cloud.json
```

Then set:
```bash
D2D_API_URL=http://YOUR_PUBLIC_IP:8000
```

**Option 2: Cloud VPN** (More Secure)

Set up VPN between GCP and your network:

```bash
# After VPN is configured
D2D_API_URL=http://10.60.60.172:8000  # Use private IP
```

#### D2D is in GCP VM

Use VPC Connector:

```bash
# Create connector
gcloud compute networks vpc-access connectors create d2d-connector \
  --region us-central1 \
  --network default \
  --range 10.8.0.0/28

# Attach to Cloud Run
gcloud run services update crowdit-mcp \
  --vpc-connector d2d-connector \
  --region us-central1

# Use internal IP
D2D_API_URL=http://INTERNAL_IP:8000
```

### 6. Deploy

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT/crowdit-mcp

gcloud run deploy crowdit-mcp \
  --image gcr.io/YOUR_PROJECT/crowdit-mcp \
  --region us-central1 \
  --platform managed
```

Or if you have CI/CD, just push to your repo.

### 7. Test

From Claude Desktop:

```
Check D2D server status
```

Should see health check response.

Try uploading:
```
Show me the D2D PACS destinations
```

## Complete Example

Here's a minimal complete server with D2D integrated:

```javascript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { d2dTools, handleD2dTool } from './lib/tools/d2d-tools.js';

const server = new Server(
  { name: 'crowdit-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

// List all tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: d2dTools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  return await handleD2dTool(name, args);
});

// Start
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP Server running with D2D tools');
  console.error(`D2D: ${process.env.D2D_API_URL}`);
}

main().catch(console.error);
```

## Dockerfile

If you're using Docker, here's a minimal Dockerfile:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["node", "src/index.js"]
```

## Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `D2D_API_URL` | Yes | - | D2D server URL |
| `D2D_API_KEY` | No | - | API key if auth enabled |
| `D2D_TIMEOUT` | No | 30000 | Request timeout (ms) |

## Troubleshooting

### "Connection refused"

```bash
# Test from Cloud Run
gcloud run services describe crowdit-mcp --region us-central1

# Deploy a test job to verify connectivity
gcloud run jobs create test-d2d \
  --image gcr.io/google.com/cloudsdktool/cloud-sdk \
  --region us-central1 \
  --set-env-vars="D2D_URL=http://YOUR_D2D_SERVER:8000" \
  --command="sh" \
  --args="-c,curl -v \$D2D_URL/api/health"

gcloud run jobs execute test-d2d --region us-central1
```

### "Timeout"

Increase timeout:
```bash
gcloud run services update crowdit-mcp \
  --timeout 300 \
  --region us-central1
```

Or in d2d-tools.js, increase `D2D_TIMEOUT`.

### Check Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crowdit-mcp" \
  --limit 50 \
  --format json

# D2D server logs
ssh dicomtools "sudo journalctl -u d2d -f"
```

## Next Steps

1. Test all D2D tools from Claude
2. Configure PACS destinations
3. Set up monitoring and alerts
4. Enable HTTPS for D2D (if needed)
5. Document your workflow

## What You Get

Once deployed, from Claude Desktop you can:

✓ Check D2D health
✓ Upload documents and convert to DICOM
✓ Manage PACS destinations
✓ Send DICOM files to PACS
✓ List and manage archives
✓ Test PACS connections

All through your single MCP connection!
