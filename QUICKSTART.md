# Quick Start Guide

## Prerequisites

Before running D2D, ensure you have:
- Python 3.8+ installed
- Poppler utilities installed (for PDF conversion)

## Installation

### Option 1: Quick Start Script (Recommended)

```bash
cd /home/claudeagent/d2d
./run.sh
```

The script will:
1. Create a virtual environment
2. Install all dependencies
3. Create .env file from template
4. Start the application

### Option 2: Manual Setup

```bash
cd /home/claudeagent/d2d

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Run the application
uvicorn app.main:app --reload
```

### Option 3: Docker

```bash
cd /home/claudeagent/d2d

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## First Run

1. **Open your browser**: http://localhost:8000

2. **Upload a test file**: Try uploading a PDF, JPG, or PNG

3. **Fill in metadata**:
   - Patient Name: TEST^PATIENT
   - Patient ID: TEST001
   - Study Description: Test Conversion

4. **Convert**: Click "Convert to DICOM"

5. **Check archive**: Your DICOM file is saved in `./dicom_archive/`

## Setting Up DICOM Destinations

### Step 1: Add a Destination

1. Click "Manage Destinations"
2. Fill in the form:
   - **Name**: My PACS
   - **AE Title**: PACS_SERVER
   - **Host**: 192.168.1.100
   - **Port**: 104
   - **Calling AE**: D2D_SCU

### Step 2: Test Connection

1. Click "Test Connection" before saving
2. Verify you see: ✓ Successfully connected

### Step 3: Use the Destination

1. Select the destination in Step 3
2. Check "Send immediately after conversion"
3. Convert your document

## Troubleshooting

### Poppler Not Found (PDF conversion fails)

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Verify installation:**
```bash
which pdftoppm
```

### Port 8000 Already in Use

Change the port in `.env`:
```env
PORT=8001
```

Or run with custom port:
```bash
uvicorn app.main:app --port 8001
```

### DICOM Send Fails

1. **Check connectivity:**
   ```bash
   ping <destination-host>
   ```

2. **Check firewall**: Ensure DICOM port (104/11112) is open

3. **Verify AE titles**: Must match on both sides

4. **Use Test Connection**: Built-in C-ECHO verification

### File Too Large

Edit `.env` and increase:
```env
MAX_FILE_SIZE=100000000  # 100MB
```

## Common Use Cases

### Converting Lab Reports

```
1. Upload PDF report
2. Metadata:
   - Patient Name: SMITH^JOHN
   - Patient ID: MRN12345
   - Study Description: Laboratory Report
   - Series Description: Blood Work 2026-01-22
3. Convert and send to PACS
```

### Converting External Images

```
1. Upload JPG/PNG image
2. Metadata:
   - Patient Name: DOE^JANE
   - Patient ID: EXT001
   - Study Description: External CT Scan
   - Modality: CT
   - Accession Number: ACC20260122
3. Convert (creates Secondary Capture)
```

### Bulk Processing

For multiple files, use the API:

```python
import requests

# Upload file
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f}
    )
file_id = response.json()['file_id']

# Convert to DICOM
requests.post('http://localhost:8000/api/convert', json={
    'file_id': file_id,
    'metadata': {
        'patient_name': 'TEST^PATIENT',
        'patient_id': 'TEST001',
        'study_description': 'Document Conversion'
    },
    'send_immediately': False
})
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## File Locations

- **Uploads**: `./uploads/` (temporary)
- **Archives**: `./dicom_archive/` (permanent)
- **Destinations**: `./destinations.json`
- **Logs**: Console output

## Next Steps

1. Configure your PACS destinations
2. Test with sample files
3. Integrate into your workflow
4. Consider adding authentication for production use

## Support

For issues or questions:
- Check the main README.md
- Review error messages in console
- Verify Poppler installation
- Test DICOM connectivity with C-ECHO

## Production Deployment

**Important**: This application has no authentication!

For production:
1. Add authentication middleware
2. Use HTTPS/TLS
3. Implement audit logging
4. Run behind reverse proxy (nginx/Apache)
5. Use proper database for destinations
6. Implement user management
7. Add role-based access control

Example nginx config:
```nginx
server {
    listen 80;
    server_name d2d.yourcompany.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
