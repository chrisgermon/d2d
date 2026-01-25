# D2D MCP Module for Cloud Run

This module integrates D2D (Documents to DICOM) tools into your existing Cloud Run MCP service.

## Architecture

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Connection
         ▼
┌─────────────────────────────┐
│  Cloud Run MCP Service      │
│  (crowdit-mcp)              │
│                             │
│  ┌────────────────────┐    │
│  │ Your Existing      │    │
│  │ MCP Tools          │    │
│  └────────────────────┘    │
│                             │
│  ┌────────────────────┐    │
│  │ D2D Tools Module   │────┼──────┐
│  │ (d2d-tools.js)     │    │      │
│  └────────────────────┘    │      │
└─────────────────────────────┘      │
                                     │ HTTP API
                                     ▼
                           ┌──────────────────┐
                           │  D2D Server      │
                           │  (dicomtools)    │
                           │  Port 8000       │
                           └──────────────────┘
```

## Installation

### 1. Add to Your Cloud Run MCP Service

Copy `d2d-tools.js` to your Cloud Run MCP service repository:

```bash
# In your Cloud Run MCP service repo
mkdir -p lib/tools
cp d2d-tools.js lib/tools/
```

### 2. Update package.json

Add the required dependencies:

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "node-fetch": "^3.3.2",
    "form-data": "^4.0.0"
  }
}
```

### 3. Integrate into Your MCP Server

Update your main MCP server file (e.g., `index.js` or `server.js`):

```javascript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { d2dTools, handleD2dTool } from './lib/tools/d2d-tools.js';

// Your existing tools
import { yourExistingTools, handleYourTools } from './lib/tools/your-tools.js';

// Combine tool lists
const allTools = [
  ...yourExistingTools,
  ...d2dTools,
];

// In your ListTools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: allTools };
});

// In your CallTool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Route to appropriate handler
  if (name.startsWith('d2d_')) {
    return await handleD2dTool(name, args);
  } else {
    return await handleYourTools(name, args);
  }
});
```

### 4. Configure Environment Variables in Cloud Run

Set these environment variables in your Cloud Run service:

```bash
# D2D server URL (your dicomtools server)
D2D_API_URL=http://YOUR_D2D_SERVER:8000

# Optional: API key if authentication is enabled
D2D_API_KEY=your-api-key-here

# Optional: Request timeout in milliseconds
D2D_TIMEOUT=30000
```

**Important**: Make sure your Cloud Run service can reach your D2D server. You may need to:
- Use Cloud VPN if D2D is on-prem
- Use Private Service Connect
- Use public IP with firewall rules
- Use VPC peering

## Network Connectivity Options

### Option 1: Public IP with Firewall (Simplest)

If your D2D server has a public IP:

1. Configure D2D server firewall to allow Cloud Run IP ranges
2. Set `D2D_API_URL=http://YOUR_PUBLIC_IP:8000`

```bash
# On D2D server, allow Google Cloud IP ranges
sudo ufw allow from 34.96.0.0/20 to any port 8000
sudo ufw allow from 35.187.0.0/16 to any port 8000
```

### Option 2: Cloud VPN (Most Secure)

Connect your on-prem network to Google Cloud:

1. Set up Cloud VPN tunnel
2. Use private IP: `D2D_API_URL=http://10.60.60.172:8000`

### Option 3: VPC Connector (If D2D in GCP)

If D2D runs in GCP VM:

1. Create VPC Serverless Connector
2. Attach to Cloud Run service
3. Use internal IP: `D2D_API_URL=http://INTERNAL_IP:8000`

### Option 4: Cloud Endpoints (Production)

For production with authentication:

1. Deploy Cloud Endpoints in front of D2D
2. Enable API key authentication
3. Use: `D2D_API_URL=https://d2d.yourcompany.com`

## Example Integration Code

### Complete Server Example

```javascript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// Import D2D tools
import { d2dTools, handleD2dTool, checkD2dHealth } from './lib/tools/d2d-tools.js';

// Import your existing tools
import { myTools, handleMyTool } from './lib/tools/my-tools.js';

// Create server
const server = new Server(
  {
    name: 'crowdit-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Combine all tools
const allTools = [...myTools, ...d2dTools];

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: allTools };
});

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name.startsWith('d2d_')) {
      return await handleD2dTool(name, args);
    } else {
      return await handleMyTool(name, args);
    }
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// Health check endpoint (optional)
async function healthCheck() {
  const d2dHealth = await checkD2dHealth();
  console.log('D2D Health:', d2dHealth);
}

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('MCP Server running with D2D tools');
  console.error(`D2D URL: ${process.env.D2D_API_URL}`);

  // Periodic health check (optional)
  setInterval(healthCheck, 60000);
}

main().catch(console.error);
```

### Minimal Integration

If you already have an MCP server, just add:

```javascript
import { d2dTools, handleD2dTool } from './lib/tools/d2d-tools.js';

// Add to your tools array
const tools = [...yourTools, ...d2dTools];

// Add to your handler
if (toolName.startsWith('d2d_')) {
  return await handleD2dTool(toolName, args);
}
```

## Testing

### 1. Test D2D Connectivity

```bash
# From your Cloud Run service
curl $D2D_API_URL/api/health
```

### 2. Test MCP Tools

Deploy your updated Cloud Run service, then from Claude:

```
Check D2D server status
```

Should respond with D2D health information.

### 3. Test File Upload

```
Upload /tmp/test.pdf to D2D for patient Smith^John with ID 12345
```

## Deployment

### Update Cloud Run Service

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT/crowdit-mcp
gcloud run deploy crowdit-mcp \
  --image gcr.io/YOUR_PROJECT/crowdit-mcp \
  --set-env-vars="D2D_API_URL=http://YOUR_D2D_SERVER:8000" \
  --set-env-vars="D2D_API_KEY=your-key" \
  --region=us-central1
```

### Using Cloud Build

Add to your `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/crowdit-mcp', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/crowdit-mcp']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'crowdit-mcp'
      - '--image=gcr.io/$PROJECT_ID/crowdit-mcp'
      - '--region=us-central1'
      - '--set-env-vars=D2D_API_URL=http://YOUR_D2D_SERVER:8000'
      - '--platform=managed'
```

## Troubleshooting

### Connection Refused

```bash
# Check if D2D is accessible from Cloud Run
# Deploy a test service to verify connectivity

# Check D2D server
curl http://YOUR_D2D_SERVER:8000/api/health

# Check firewall rules
sudo ufw status

# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crowdit-mcp" --limit 50
```

### Timeout Errors

Increase timeout:

```javascript
// Set higher timeout
D2D_TIMEOUT=60000
```

### Authentication Errors

Check API key:

```bash
# Test with curl
curl -H "X-API-Key: your-key" http://YOUR_D2D_SERVER:8000/api/health
```

## Security Best Practices

1. **Use VPN**: Connect Cloud Run to your on-prem network via Cloud VPN
2. **API Keys**: Enable D2D API key authentication
3. **Firewall**: Restrict D2D to only Cloud Run IP ranges
4. **HTTPS**: Use TLS for D2D API (via load balancer or Cloud Endpoints)
5. **Secrets**: Store API keys in Google Secret Manager

### Using Secret Manager

```bash
# Store API key
echo -n "your-d2d-api-key" | gcloud secrets create d2d-api-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding d2d-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with secret
gcloud run deploy crowdit-mcp \
  --image gcr.io/YOUR_PROJECT/crowdit-mcp \
  --set-env-vars="D2D_API_URL=http://YOUR_D2D_SERVER:8000" \
  --set-secrets="D2D_API_KEY=d2d-api-key:latest"
```

## Available D2D Tools

Once integrated, Claude can use these tools:

- `d2d_health_check` - Check D2D server status
- `d2d_upload_file` - Upload and convert documents to DICOM
- `d2d_list_destinations` - List PACS servers
- `d2d_add_destination` - Add new PACS destination
- `d2d_verify_destination` - Test PACS connection (C-ECHO)
- `d2d_send_to_pacs` - Send DICOM to PACS
- `d2d_list_archives` - List archived DICOM files
- `d2d_convert_document` - Convert document to DICOM

## Example Usage from Claude

```
User: "Check if D2D is running"
Claude: [Calls d2d_health_check]

User: "Upload this PDF for patient Jones^Sarah, MRN 54321"
Claude: [Calls d2d_upload_file with patient details]

User: "Send that file to Intelerad PACS"
Claude: [Calls d2d_send_to_pacs]

User: "List all DICOM files in the archive"
Claude: [Calls d2d_list_archives]
```

## Support

- **D2D Documentation**: `/opt/d2d/README.md`
- **Cloud Run Logs**: `gcloud logging read "resource.type=cloud_run_revision"`
- **D2D Logs**: `ssh dicomtools "sudo journalctl -u d2d -f"`

## License

MIT
