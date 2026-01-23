# Documents to DICOM (D2D)

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![DICOM](https://img.shields.io/badge/DICOM-Standard-red.svg)](https://www.dicomstandard.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Azure](https://img.shields.io/badge/Azure-Deployed-0078D4.svg)](https://azure.microsoft.com/)
[![Status](https://img.shields.io/badge/status-production-success.svg)]()

Convert documents and images to DICOM format and send to PACS systems.

## Features

- 📄 **Multi-format Support**: Convert PDF, JPG, and PNG files to DICOM
- 🏥 **Modality Worklist Integration**: Query scheduled studies (C-FIND) and auto-populate patient data
- ✏️ **DICOM Metadata Editor**: Complete control over patient demographics and study information
- 🚀 **DICOM Send**: C-STORE to any DICOM destination (PACS, VNA, etc.)
- 💾 **Archive Management**: All converted DICOM files are stored locally
- 🎯 **Destination Management**: Save and manage multiple DICOM destinations
- 🔍 **Preview Before Send**: Review all metadata before conversion
- 🎨 **Modern UI**: Clean, intuitive drag-and-drop interface

## New: Modality Worklist Support

Query your RIS/PACS worklist server to find scheduled studies and automatically populate patient demographics:

- **Query worklist** by patient name, ID, accession number, date, or modality
- **Select patient** from results table
- **Auto-populate** all DICOM metadata fields (patient info, accession, study details)
- **Seamless workflow** - no manual data entry required

See [WORKLIST-FEATURE.md](WORKLIST-FEATURE.md) for complete documentation.

## Requirements

- Python 3.8+
- Poppler (for PDF conversion)

### Install Poppler

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
Download from: https://github.com/oschwartz10612/poppler-windows/releases/

## Quick Start

1. **Install dependencies:**
```bash
cd /home/claudeagent/d2d
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Run the application:**
```bash
python -m uvicorn app.main:app --reload
```

4. **Open browser:**
Navigate to: http://localhost:8000

## Usage

### 1. Upload a File
- Drag and drop a PDF, JPG, or PNG file
- Or click to browse and select a file

### 2. Enter DICOM Metadata
- **Required**: Patient Name, Patient ID
- **Optional**: Date of Birth, Sex, Study Description, etc.

### 3. Configure Destination (Optional)
- Click "Manage Destinations" to add DICOM servers
- Test connections with the built-in C-ECHO verification
- Select a destination if you want to send immediately

### 4. Convert and Send
- Review the preview
- Click "Convert to DICOM"
- Optionally check "Send immediately after conversion"

## API Endpoints

### File Operations
- `POST /api/upload` - Upload a document/image
- `POST /api/convert` - Convert to DICOM
- `POST /api/send` - Send DICOM file to destination

### Destination Management
- `GET /api/destinations` - List all destinations
- `POST /api/destinations` - Save a new destination
- `DELETE /api/destinations/{name}` - Delete a destination
- `POST /api/destinations/verify` - Test connection (C-ECHO)

### Archives
- `GET /api/archives` - List archived DICOM files
- `GET /api/archives/{filename}` - Download archived file

## Configuration

Edit `.env` file:

```env
HOST=0.0.0.0
PORT=8000
ARCHIVE_PATH=./dicom_archive
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=50000000
```

## DICOM Tags

The following DICOM tags are populated:

**Patient Module:**
- PatientName (0010,0010)
- PatientID (0010,0020)
- PatientBirthDate (0010,0030)
- PatientSex (0010,0040)

**Study Module:**
- StudyInstanceUID (0020,000D)
- StudyDate (0008,0020)
- StudyTime (0008,0030)
- StudyDescription (0008,1030)
- AccessionNumber (0008,0050)
- ReferringPhysicianName (0008,0090)

**Series Module:**
- SeriesInstanceUID (0020,000E)
- SeriesDescription (0008,103E)
- Modality (0008,0060)

**Image Module:**
- SOPInstanceUID (0008,0018)
- SOPClassUID (0008,0016) - Secondary Capture
- PixelData (7FE0,0010)

## File Structure

```
d2d/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── dicom_converter.py   # Document to DICOM conversion
│   └── dicom_sender.py      # DICOM C-STORE operations
├── static/
│   ├── index.html           # Web interface
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── dicom_archive/           # Converted DICOM files
├── uploads/                 # Temporary uploads
├── requirements.txt
├── .env
└── README.md
```

## Troubleshooting

### PDF Conversion Fails
- Ensure Poppler is installed: `which pdftoppm`
- Check PDF is not corrupted or password-protected

### DICOM Send Fails
- Verify destination is reachable: `ping <host>`
- Check firewall allows DICOM port (typically 104 or 11112)
- Use "Test Connection" to verify C-ECHO
- Verify AE titles match on both sides

### Large Files
- Adjust `MAX_FILE_SIZE` in `.env`
- Images are automatically resized to max 2048x2048

## Development

Run with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

View API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Notes

- This application has **no authentication** - use in trusted networks only
- For production use, add authentication middleware
- Consider using HTTPS for PHI data
- Implement audit logging for compliance

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please create an issue on GitHub.
