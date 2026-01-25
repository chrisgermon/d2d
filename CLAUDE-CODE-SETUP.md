# Connecting D2D to Claude Code

This guide shows you how to access and manage your D2D server from Claude Code.

## Option 1: SSH Tunnel (Recommended)

The easiest way to access D2D from your local machine where Claude Code is running.

### Setup SSH Tunnel

On your local machine (where Claude Code runs):

```bash
# Create SSH tunnel to D2D server
ssh -L 8000:localhost:8000 user@your-d2d-server-ip

# Or run in background
ssh -f -N -L 8000:localhost:8000 user@your-d2d-server-ip
```

Now access D2D at `http://localhost:8000` in your browser or from Claude Code.

### From Claude Code

You can now interact with D2D through its API:

```bash
# Test connection
curl http://localhost:8000/api/health

# Upload and convert a file
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf" \
  -F "patient_name=John Doe" \
  -F "patient_id=12345"
```

## Option 2: Direct Network Access

If your D2D server is on the same network or has a public IP:

### From Claude Code

```bash
# Replace with your D2D server IP
D2D_SERVER="http://10.60.60.172:8000"

# Test connection
curl $D2D_SERVER/api/health

# List destinations
curl $D2D_SERVER/api/destinations

# Upload and convert
curl -X POST $D2D_SERVER/api/upload \
  -F "file=@document.pdf" \
  -F "patient_name=John Doe" \
  -F "patient_id=12345"
```

## Option 3: MCP Server (Advanced)

Create a Model Context Protocol server that Claude Code can use to interact with D2D.

See `mcp-server/` directory for the MCP server implementation.

### Install MCP Server

```bash
cd /opt/d2d/mcp-server
npm install
```

### Configure Claude Code

Add to your Claude Code MCP settings (`~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "d2d": {
      "command": "node",
      "args": ["/opt/d2d/mcp-server/index.js"],
      "env": {
        "D2D_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Use from Claude Code

Once configured, you can ask Claude Code to:
- "Upload this PDF to D2D"
- "List DICOM destinations"
- "Send this document to PACS"
- "Show D2D archives"

## Option 4: API Wrapper Script

Create a simple bash script to interact with D2D from Claude Code:

```bash
#!/bin/bash
# d2d-cli.sh - Command line interface for D2D

D2D_URL="${D2D_URL:-http://localhost:8000}"

case "$1" in
    upload)
        curl -X POST "$D2D_URL/api/upload" \
          -F "file=@$2" \
          -F "patient_name=$3" \
          -F "patient_id=$4"
        ;;

    destinations)
        curl "$D2D_URL/api/destinations" | jq .
        ;;

    archives)
        curl "$D2D_URL/api/archives" | jq .
        ;;

    send)
        curl -X POST "$D2D_URL/api/send" \
          -H "Content-Type: application/json" \
          -d "{\"filename\":\"$2\", \"destination\":\"$3\"}"
        ;;

    status)
        curl "$D2D_URL/api/health" | jq .
        ;;

    *)
        echo "Usage: $0 {upload|destinations|archives|send|status}"
        exit 1
        ;;
esac
```

### Usage

```bash
# Make executable
chmod +x d2d-cli.sh

# Check status
./d2d-cli.sh status

# Upload file
./d2d-cli.sh upload document.pdf "John Doe" "12345"

# List destinations
./d2d-cli.sh destinations

# View archives
./d2d-cli.sh archives
```

## Common D2D API Endpoints

### Health Check
```bash
GET /api/health
```

### Upload File
```bash
POST /api/upload
Content-Type: multipart/form-data

file: <file>
patient_name: string
patient_id: string
patient_dob: string (YYYYMMDD, optional)
patient_sex: string (M/F/O, optional)
study_description: string (optional)
accession_number: string (optional)
```

### Convert to DICOM
```bash
POST /api/convert
Content-Type: application/json

{
  "filename": "uploaded_file.pdf",
  "patient_name": "Doe^John",
  "patient_id": "12345",
  "patient_dob": "19800101",
  "patient_sex": "M",
  "study_description": "External Document",
  "modality": "DOC"
}
```

### Send to PACS
```bash
POST /api/send
Content-Type: application/json

{
  "filename": "converted_file.dcm",
  "destination": "Intelerad PACS"
}
```

### List Destinations
```bash
GET /api/destinations
```

### Add Destination
```bash
POST /api/destinations
Content-Type: application/json

{
  "name": "My PACS",
  "ae_title": "PACSAE",
  "host": "10.0.0.10",
  "port": 104,
  "calling_ae_title": "D2D_SCU"
}
```

### Verify Destination (C-ECHO)
```bash
POST /api/destinations/verify
Content-Type: application/json

{
  "ae_title": "PACSAE",
  "host": "10.0.0.10",
  "port": 104,
  "calling_ae_title": "D2D_SCU"
}
```

### List Archives
```bash
GET /api/archives
```

### Download Archive
```bash
GET /api/archives/{filename}
```

## Security Considerations

### API Key Authentication

If D2D is configured with API keys (recommended), include the key in requests:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/api/destinations
```

### Environment Variable

Set the API key as an environment variable:

```bash
export D2D_API_KEY="your-api-key-here"

curl -H "X-API-Key: $D2D_API_KEY" \
  http://localhost:8000/api/destinations
```

### SSH Key Authentication

For SSH tunnels, use SSH keys instead of passwords:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy to D2D server
ssh-copy-id user@your-d2d-server-ip

# Now you can tunnel without password
ssh -f -N -L 8000:localhost:8000 user@your-d2d-server-ip
```

## Troubleshooting

### Connection Refused

```bash
# Check if D2D is running on server
ssh user@server "sudo systemctl status d2d"

# Check if port is open
nc -zv your-d2d-server-ip 8000

# Check firewall
ssh user@server "sudo ufw status"
```

### API Returns 401 Unauthorized

Check if API key authentication is enabled and you're providing the correct key:

```bash
# Check .env file on server
ssh user@server "grep D2D_API_KEYS /opt/d2d/.env"
```

### Tunnel Keeps Dropping

Use autossh to maintain persistent tunnel:

```bash
# Install autossh
sudo apt install autossh

# Create persistent tunnel
autossh -M 0 -f -N -L 8000:localhost:8000 user@your-d2d-server-ip
```

## Examples from Claude Code

### Upload and Convert PDF

```bash
# Upload PDF
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/document.pdf" \
  -F "patient_name=Smith^John" \
  -F "patient_id=MRN123456" \
  -F "patient_dob=19850615" \
  -F "patient_sex=M" \
  -F "study_description=Referral Letter"

# Response includes the converted DICOM filename
```

### Send to PACS

```bash
# Send previously converted file
curl -X POST http://localhost:8000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "20240101_120000_Smith_John.dcm",
    "destination": "Intelerad PACS"
  }'
```

### Batch Process Multiple Files

```bash
#!/bin/bash
# batch-upload.sh

D2D_URL="http://localhost:8000"
DESTINATION="Intelerad PACS"

for file in *.pdf; do
    echo "Processing $file..."

    # Upload and convert
    RESPONSE=$(curl -s -X POST "$D2D_URL/api/upload" \
      -F "file=@$file" \
      -F "patient_name=External^Document" \
      -F "patient_id=EXT$(date +%s)" \
      -F "study_description=External Document")

    # Extract filename from response
    FILENAME=$(echo $RESPONSE | jq -r '.filename')

    # Send to PACS
    if [ ! -z "$FILENAME" ]; then
        curl -X POST "$D2D_URL/api/send" \
          -H "Content-Type: application/json" \
          -d "{\"filename\":\"$FILENAME\", \"destination\":\"$DESTINATION\"}"
    fi

    sleep 1
done
```

## Integration with Workflows

### VRG Hub Integration

D2D can be integrated with VRG Hub for automated document processing:

```bash
# Example: Upload document from VRG Hub webhook
curl -X POST http://localhost:8000/api/upload \
  -F "file=@$DOCUMENT_PATH" \
  -F "patient_name=$PATIENT_NAME" \
  -F "patient_id=$MRN" \
  -F "accession_number=$ACCESSION"
```

### Automated Monitoring

Monitor D2D status from Claude Code:

```bash
#!/bin/bash
# monitor-d2d.sh

D2D_URL="http://localhost:8000"

while true; do
    STATUS=$(curl -s "$D2D_URL/api/health")

    if [ $? -eq 0 ]; then
        echo "$(date): D2D is healthy - $STATUS"
    else
        echo "$(date): D2D is down!" | mail -s "D2D Alert" admin@example.com
    fi

    sleep 300  # Check every 5 minutes
done
```

## Resources

- **D2D GitHub**: https://github.com/chrisgermon/d2d
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc
- **Server Logs**: `ssh user@server "sudo journalctl -u d2d -f"`
