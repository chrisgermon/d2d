# D2D API Documentation

## Overview

The D2D API provides endpoints for converting documents to DICOM format and sending them to PACS servers.

**Base URL:** `http://10.200.1.8:8000` (private network) or `http://4.198.108.152:8000` (public - with auth)

**Authentication:** API Key (X-API-Key header)

---

## Authentication

All API requests must include an API key in the header:

```http
X-API-Key: your-api-key-here
```

**Get your API key:** Contact your D2D administrator

**Security:**
- API keys should be stored securely (environment variables, secret manager)
- Never commit API keys to version control
- Rotate keys regularly

---

## API Endpoints

### 1. Upload File

Upload a document or image file for conversion.

**Endpoint:** `POST /api/upload`

**Request:**
```http
POST /api/upload
Content-Type: multipart/form-data
X-API-Key: your-api-key

file: <binary file data>
```

**Response:**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "size": 245678,
  "content_type": "application/pdf"
}
```

**Supported File Types:**
- PDF (`.pdf`)
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)

---

### 2. Convert to DICOM

Convert an uploaded file to DICOM format.

**Endpoint:** `POST /api/convert`

**Request:**
```http
POST /api/convert
Content-Type: application/json
X-API-Key: your-api-key

{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "patient_name": "DOE^JOHN",
    "patient_id": "MRN123456",
    "patient_birth_date": "1990-01-15",
    "patient_sex": "M",
    "study_description": "Chest X-Ray Report",
    "series_description": "Document Series",
    "accession_number": "ACC123456",
    "referring_physician": "DR SMITH"
  },
  "destination": {
    "name": "Main PACS",
    "ae_title": "PACS_SERVER",
    "host": "10.17.1.21",
    "port": 5000,
    "calling_ae_title": "D2D_CLIENT"
  },
  "send_immediately": false
}
```

**Request Fields:**
- `file_id` (required): File ID from upload endpoint
- `metadata` (required): DICOM metadata
  - `patient_name` (required): Patient name in DICOM format (LAST^FIRST)
  - `patient_id` (required): Medical Record Number
  - `patient_birth_date` (optional): Date in YYYY-MM-DD format
  - `patient_sex` (optional): "M", "F", or "O"
  - `study_description` (required): Description of the study
  - `series_description` (required): Description of the series
  - `accession_number` (optional): Accession number
  - `referring_physician` (optional): Referring physician name
- `destination` (optional): PACS destination (required if send_immediately=true)
- `send_immediately` (optional): Send to PACS immediately after conversion

**Response:**
```json
{
  "success": true,
  "message": "File converted to DICOM successfully",
  "sop_instance_uid": "1.2.840.10008.5.1.4.1.1.104.1",
  "study_instance_uid": "1.2.840.113619.2.55.3.1",
  "series_instance_uid": "1.2.840.113619.2.55.3.2",
  "dicom_file_path": "/opt/d2d/dicom_archive/document.dcm"
}
```

---

### 3. Send to PACS

Send a converted DICOM file to a PACS server.

**Endpoint:** `POST /api/send`

**Request:**
```http
POST /api/send
Content-Type: application/json
X-API-Key: your-api-key

{
  "dicom_file_path": "/opt/d2d/dicom_archive/document.dcm",
  "destination": {
    "name": "Main PACS",
    "ae_title": "PACS_SERVER",
    "host": "10.17.1.21",
    "port": 5000,
    "calling_ae_title": "D2D_CLIENT"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "DICOM file sent to PACS successfully",
  "destination": "Main PACS",
  "instances_sent": 1
}
```

---

### 4. Query Modality Worklist

Query the modality worklist for scheduled studies.

**Endpoint:** `POST /api/worklist/query`

**Request:**
```http
POST /api/worklist/query
Content-Type: application/json
X-API-Key: your-api-key

{
  "patient_name": "*",
  "patient_id": null,
  "accession_number": null,
  "scheduled_date": "2026-01-23",
  "modality": "US",
  "config": {
    "host": "10.17.1.21",
    "port": 5010,
    "ae_title": "LIVUSWL",
    "calling_ae": "D2D_CLIENT"
  }
}
```

**Request Fields:**
- `patient_name` (optional): Patient name (* for all)
- `patient_id` (optional): Patient ID/MRN
- `accession_number` (optional): Accession number
- `scheduled_date` (optional): Date in YYYY-MM-DD format
- `modality` (optional): Modality code (US, CT, MR, etc.)
- `config` (required): Worklist server configuration

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "patient_name": "DOE^JOHN",
      "patient_id": "MRN123456",
      "patient_birth_date": "19900115",
      "patient_sex": "M",
      "accession_number": "ACC123456",
      "modality": "US",
      "scheduled_date": "20260123",
      "scheduled_time": "143000",
      "procedure_description": "Abdominal Ultrasound",
      "requested_procedure_description": "Abdominal US",
      "scheduled_physician": "DR SMITH"
    }
  ],
  "count": 1
}
```

---

### 5. Test Worklist Connection

Test connection to worklist server (C-ECHO).

**Endpoint:** `POST /api/worklist/test`

**Request:**
```http
POST /api/worklist/test
Content-Type: application/json
X-API-Key: your-api-key

{
  "host": "10.17.1.21",
  "port": 5010,
  "ae_title": "LIVUSWL",
  "calling_ae": "D2D_CLIENT"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful - Worklist server is responding"
}
```

---

### 6. Get Destinations

Get list of saved PACS destinations.

**Endpoint:** `GET /api/destinations`

**Request:**
```http
GET /api/destinations
X-API-Key: your-api-key
```

**Response:**
```json
{
  "destinations": [
    {
      "name": "Main PACS",
      "ae_title": "PACS_SERVER",
      "host": "10.17.1.21",
      "port": 5000,
      "calling_ae_title": "D2D_CLIENT"
    }
  ]
}
```

---

### 7. Add Destination

Add a new PACS destination.

**Endpoint:** `POST /api/destinations`

**Request:**
```http
POST /api/destinations
Content-Type: application/json
X-API-Key: your-api-key

{
  "name": "Main PACS",
  "ae_title": "PACS_SERVER",
  "host": "10.17.1.21",
  "port": 5000,
  "calling_ae_title": "D2D_CLIENT"
}
```

**Response:**
```json
{
  "message": "Destination saved successfully",
  "destination": {
    "name": "Main PACS",
    "ae_title": "PACS_SERVER",
    "host": "10.17.1.21",
    "port": 5000,
    "calling_ae_title": "D2D_CLIENT"
  }
}
```

---

### 8. Delete Destination

Delete a saved destination.

**Endpoint:** `DELETE /api/destinations/{destination_name}`

**Request:**
```http
DELETE /api/destinations/Main%20PACS
X-API-Key: your-api-key
```

**Response:**
```json
{
  "message": "Destination deleted successfully"
}
```

---

### 9. Verify Destination

Test connection to a PACS destination (C-ECHO).

**Endpoint:** `POST /api/destinations/verify`

**Request:**
```http
POST /api/destinations/verify
Content-Type: application/json
X-API-Key: your-api-key

{
  "name": "Main PACS",
  "ae_title": "PACS_SERVER",
  "host": "10.17.1.21",
  "port": 5000,
  "calling_ae_title": "D2D_CLIENT"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful - PACS is responding"
}
```

---

### 10. Get Archives

List archived DICOM files.

**Endpoint:** `GET /api/archives`

**Request:**
```http
GET /api/archives
X-API-Key: your-api-key
```

**Response:**
```json
{
  "archives": [
    {
      "filename": "document_20260123_143045.dcm",
      "size": 245678,
      "created": 1737653445.123
    }
  ]
}
```

---

### 11. Download Archive

Download a DICOM file from archives.

**Endpoint:** `GET /api/archives/{filename}`

**Request:**
```http
GET /api/archives/document_20260123_143045.dcm
X-API-Key: your-api-key
```

**Response:** Binary DICOM file download

---

## Error Responses

All endpoints return standard HTTP status codes:

**Success:**
- `200 OK` - Request successful
- `201 Created` - Resource created

**Client Errors:**
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error

**Server Errors:**
- `500 Internal Server Error` - Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Usage Examples

### Complete Workflow: Upload, Convert, Send

```javascript
// 1. Upload file
const formData = new FormData();
formData.append('file', fileBlob, 'report.pdf');

const uploadResponse = await fetch('http://d2d-api/api/upload', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: formData
});

const { file_id } = await uploadResponse.json();

// 2. Convert to DICOM
const convertResponse = await fetch('http://d2d-api/api/convert', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    file_id: file_id,
    metadata: {
      patient_name: 'DOE^JOHN',
      patient_id: 'MRN123456',
      patient_birth_date: '1990-01-15',
      patient_sex: 'M',
      study_description: 'Chest X-Ray Report',
      series_description: 'Document Series'
    },
    send_immediately: false
  })
});

const { dicom_file_path } = await convertResponse.json();

// 3. Send to PACS
const sendResponse = await fetch('http://d2d-api/api/send', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    dicom_file_path: dicom_file_path,
    destination: {
      name: 'Main PACS',
      ae_title: 'PACS_SERVER',
      host: '10.17.1.21',
      port: 5000,
      calling_ae_title: 'D2D_CLIENT'
    }
  })
});

const result = await sendResponse.json();
console.log('Success:', result.message);
```

### Query Worklist and Use Data

```javascript
// 1. Query worklist
const worklistResponse = await fetch('http://d2d-api/api/worklist/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    patient_name: '*',
    scheduled_date: '2026-01-23',
    modality: 'US',
    config: {
      host: '10.17.1.21',
      port: 5010,
      ae_title: 'LIVUSWL',
      calling_ae: 'D2D_CLIENT'
    }
  })
});

const { items } = await worklistResponse.json();

// 2. Use worklist data to populate conversion metadata
const selectedPatient = items[0];

const convertResponse = await fetch('http://d2d-api/api/convert', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    file_id: uploadedFileId,
    metadata: {
      patient_name: selectedPatient.patient_name,
      patient_id: selectedPatient.patient_id,
      patient_birth_date: selectedPatient.patient_birth_date,
      patient_sex: selectedPatient.patient_sex,
      study_description: selectedPatient.procedure_description,
      accession_number: selectedPatient.accession_number
    }
  })
});
```

---

## Rate Limiting

**Current:** No rate limiting implemented
**Recommended:** 100 requests per minute per API key

---

## Versioning

**Current Version:** 1.0.0

API versioning will be implemented in future releases via URL path:
- `/api/v1/upload`
- `/api/v2/upload`

---

## Support

**Issues:** https://github.com/chrisgermon/d2d/issues
**Documentation:** `/home/claudeagent/d2d/`

---

**Last Updated:** 2026-01-23
