# D2D MCP Server

Model Context Protocol server for D2D (Documents to DICOM). This allows Claude Code to seamlessly interact with your D2D server.

## Installation

```bash
cd /opt/d2d/mcp-server
npm install
```

## Configuration

### Environment Variables

- `D2D_API_URL` - URL of your D2D server (default: `http://localhost:8000`)
- `D2D_API_KEY` - API key if authentication is enabled (optional)

### Claude Code Configuration

Add to your Claude Code MCP settings file:

**macOS/Linux**: `~/.config/claude/mcp.json`
**Windows**: `%APPDATA%\Claude\mcp.json`

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

If using SSH tunnel from your local machine:

```json
{
  "mcpServers": {
    "d2d": {
      "command": "node",
      "args": ["/path/to/d2d/mcp-server/index.js"],
      "env": {
        "D2D_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

With API key authentication:

```json
{
  "mcpServers": {
    "d2d": {
      "command": "node",
      "args": ["/opt/d2d/mcp-server/index.js"],
      "env": {
        "D2D_API_URL": "http://localhost:8000",
        "D2D_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Available Tools

### d2d_health_check
Check if D2D server is running and healthy.

**Example**:
```
Check if D2D is running
```

### d2d_upload_file
Upload a document to D2D and convert to DICOM.

**Parameters**:
- `file_path` (required) - Path to the file
- `patient_name` (required) - Patient name (LastName^FirstName)
- `patient_id` (required) - Patient ID/MRN
- `patient_dob` (optional) - Date of birth (YYYYMMDD)
- `patient_sex` (optional) - Sex (M/F/O)
- `study_description` (optional) - Study description
- `accession_number` (optional) - Accession number

**Example**:
```
Upload the PDF at /path/to/document.pdf for patient Smith^John with MRN 12345
```

### d2d_list_destinations
List all configured DICOM destinations.

**Example**:
```
Show me all DICOM destinations in D2D
```

### d2d_add_destination
Add a new DICOM destination (PACS server).

**Parameters**:
- `name` (required) - Friendly name
- `ae_title` (required) - PACS AE Title
- `host` (required) - PACS hostname/IP
- `port` (required) - PACS port
- `calling_ae_title` (required) - Source AE Title

**Example**:
```
Add a PACS destination named "Intelerad PACS" with AE title AURVCMOD1 at 10.17.1.21 port 5000, use D2D_SCU as calling AE
```

### d2d_verify_destination
Test connection to a PACS server (C-ECHO).

**Parameters**:
- `ae_title` (required) - PACS AE Title
- `host` (required) - PACS hostname/IP
- `port` (required) - PACS port
- `calling_ae_title` (required) - Source AE Title

**Example**:
```
Test connection to PACS at 10.17.1.21 port 5000 with AE title AURVCMOD1
```

### d2d_send_to_pacs
Send a DICOM file to a PACS destination.

**Parameters**:
- `filename` (required) - DICOM filename from archive
- `destination` (required) - Destination name

**Example**:
```
Send the DICOM file patient_123.dcm to Intelerad PACS
```

### d2d_list_archives
List all archived DICOM files.

**Example**:
```
Show me all archived DICOM files
```

### d2d_convert_document
Convert an uploaded document to DICOM.

**Parameters**:
- `filename` (required) - Uploaded filename
- `patient_name` (required) - Patient name
- `patient_id` (required) - Patient ID/MRN
- `patient_dob` (optional) - DOB (YYYYMMDD)
- `patient_sex` (optional) - Sex (M/F/O)
- `study_description` (optional) - Study description
- `modality` (optional) - DICOM modality (default: DOC)

**Example**:
```
Convert document.pdf to DICOM for patient Doe^Jane with ID 67890
```

## Usage Examples

### Basic Workflow

1. **Check D2D is running**:
   ```
   Is D2D running?
   ```

2. **Upload and convert a document**:
   ```
   Upload /home/user/referral.pdf to D2D for patient Jones^Sarah, MRN 54321, DOB 19900505, female
   ```

3. **List destinations**:
   ```
   Show me the DICOM destinations
   ```

4. **Send to PACS**:
   ```
   Send the most recent DICOM file to Intelerad PACS
   ```

### Advanced Workflow

1. **Add a new PACS destination**:
   ```
   Add a DICOM destination called "Test PACS" with AE title TESTPACS at 192.168.1.100 port 104, calling AE D2D
   ```

2. **Test the connection**:
   ```
   Test connection to Test PACS
   ```

3. **Batch upload documents**:
   ```
   Upload all PDFs in /home/user/documents/ to D2D
   ```

4. **View archives**:
   ```
   List all DICOM files in the archive
   ```

## Troubleshooting

### MCP Server Not Starting

```bash
# Test manually
cd /opt/d2d/mcp-server
D2D_API_URL=http://localhost:8000 node index.js
```

### Connection Issues

1. **Check D2D is running**:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Check SSH tunnel** (if using remote server):
   ```bash
   ssh -L 8000:localhost:8000 user@d2d-server
   ```

3. **Check API key** (if enabled):
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/api/health
   ```

### Tool Not Found

Make sure:
1. MCP server is configured in `~/.config/claude/mcp.json`
2. Claude Code has been restarted after configuration
3. Node.js is installed (`node --version`)

## Development

### Test the MCP server:

```bash
cd /opt/d2d/mcp-server
npm run dev
```

### Debug mode:

```bash
D2D_API_URL=http://localhost:8000 DEBUG=* node index.js
```

## License

MIT
