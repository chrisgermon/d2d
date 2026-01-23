# DICOM Modality Worklist Integration

## Overview

The D2D application now includes full DICOM Modality Worklist (MWL) query functionality, allowing you to search for scheduled studies and automatically populate patient demographics and study information.

## Features

### ✅ Worklist Query (C-FIND)
- Query scheduled studies from your PACS/RIS worklist server
- Search by multiple criteria:
  - Patient Name (supports wildcards: `*` and `?`)
  - Patient ID/MRN
  - Accession Number
  - Scheduled Date
  - Modality (US, CT, MR, XA, etc.)

### ✅ Patient Selection
- Display results in an interactive table
- View complete patient and procedure information
- Select patient with one click

### ✅ Auto-Population
- Automatically fills all DICOM metadata fields:
  - Patient Name, ID, Date of Birth, Sex
  - Accession Number
  - Study Description
  - Modality
  - Referring Physician
  - Study Date/Time

### ✅ Seamless Workflow
- Query worklist → Select patient → Upload document → Convert → Send to PACS
- All metadata is pre-filled from worklist
- Reduces manual data entry errors
- Ensures consistency with scheduled procedures

## Configuration

### Default Worklist Server Settings

```
Host:        10.17.1.21
Port:        5010
AE Title:    AURVCMOD1
Calling AE:  LIVUSWL
```

These settings are pre-configured but can be modified in the worklist interface.

## Usage

### Step 1: Access Worklist Interface

Navigate to: **http://10.200.1.8:8000/worklist**

Or click the "🏥 Query Worklist" button on the main D2D page.

### Step 2: Test Connection (Optional)

Click "Test Connection" to verify connectivity to the worklist server.

Expected result:
```json
{
    "success": true,
    "message": "Successfully connected to worklist server AURVCMOD1"
}
```

### Step 3: Search for Patients

**Search All Patients Today:**
- Leave "Patient Name" as `*` (or enter `*` for all)
- Set "Scheduled Date" to today
- Click "Search Worklist"

**Search Specific Patient:**
- Enter patient name: `SMITH*` or `SMITH^JOHN`
- Enter patient ID if known
- Click "Search Worklist"

**Search by Accession:**
- Enter accession number
- Click "Search Worklist"

**Filter by Modality:**
- Select modality from dropdown (US, CT, MR, etc.)
- Click "Search Worklist"

### Step 4: Review Results

Results are displayed in a table with:
- Patient Name
- Patient ID
- Date of Birth
- Accession Number
- Modality
- Scheduled Date/Time
- Procedure Description

### Step 5: Select Patient

Click on any row in the table to select that patient.

The selected patient's full details will be displayed below the table.

### Step 6: Use in D2D

Click "Use This Patient in D2D"

You will be redirected to the main D2D page with all fields automatically populated.

### Step 7: Upload and Convert

1. Upload your document/image
2. Review the pre-filled metadata
3. Select DICOM destination
4. Click "Convert to DICOM" or "Convert and Send"

## API Endpoints

### Test Worklist Connection

```bash
POST /api/worklist/test
Content-Type: application/json

{
  "host": "10.17.1.21",
  "port": 5010,
  "ae_title": "AURVCMOD1",
  "calling_ae": "LIVUSWL"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to worklist server AURVCMOD1"
}
```

### Query Worklist

```bash
POST /api/worklist/query
Content-Type: application/json

{
  "patient_name": "*",
  "patient_id": null,
  "accession_number": null,
  "scheduled_date": "2026-01-23",
  "modality": "US",
  "config": {
    "host": "10.17.1.21",
    "port": 5010,
    "ae_title": "AURVCMOD1",
    "calling_ae": "LIVUSWL"
  }
}
```

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "patient_name": "SMITH^JOHN",
      "patient_id": "12345",
      "patient_birth_date": "1980-05-15",
      "patient_sex": "M",
      "accession_number": "ACC001",
      "modality": "US",
      "scheduled_date": "2026-01-23",
      "scheduled_time": "10:30:00",
      "procedure_description": "Abdominal Ultrasound",
      "scheduled_physician": "DR^JONES",
      "study_instance_uid": "1.2.840...."
    }
  ],
  "count": 1,
  "message": "Found 1 worklist item(s)"
}
```

### Get Worklist Configuration

```bash
GET /api/worklist/config
```

**Response:**
```json
{
  "host": "10.17.1.21",
  "port": 5010,
  "ae_title": "AURVCMOD1",
  "calling_ae": "LIVUSWL"
}
```

## DICOM Technical Details

### MWL Query (C-FIND)

The application performs a DICOM C-FIND query against the Modality Worklist Information Model.

**SOP Class:** Modality Worklist Information Find (1.2.840.10008.5.1.4.31)

**Query Dataset Includes:**
- Patient Module (0010,xxxx)
  - PatientName
  - PatientID
  - PatientBirthDate
  - PatientSex

- Requested Procedure Module (0032,xxxx)
  - AccessionNumber
  - RequestedProcedureDescription
  - RequestedProcedureID

- Scheduled Procedure Step Sequence (0040,0100)
  - ScheduledProcedureStepStartDate
  - ScheduledProcedureStepStartTime
  - Modality
  - ScheduledPerformingPhysicianName
  - ScheduledProcedureStepDescription

- Study Instance UID (0020,000D)

### Wildcard Matching

The worklist query supports standard DICOM wildcards:
- `*` - Matches any sequence of characters
- `?` - Matches any single character

**Examples:**
- `SMITH*` - All patients with last name starting with SMITH
- `*JOHN*` - All patients with JOHN anywhere in the name
- `SMITH^J*` - Last name SMITH, first name starting with J

## Troubleshooting

### No Results Returned

**Possible Causes:**
1. No scheduled procedures for the search criteria
2. Worklist server has no data for today
3. Search filters are too restrictive

**Solutions:**
- Try searching with `*` for all patients
- Remove date filter to search all dates
- Check that the worklist server has scheduled procedures

### Connection Failed

**Possible Causes:**
1. Worklist server is down
2. Network connectivity issue
3. Incorrect AE Title or port

**Solutions:**
- Verify server is running: `telnet 10.17.1.21 5010`
- Check VPN/network connectivity
- Verify AE Title configuration matches worklist server

### Association Rejected

**Possible Causes:**
1. Calling AE Title not registered on worklist server
2. Worklist server does not accept queries from this IP

**Solutions:**
- Register `LIVUSWL` as an allowed AE Title on the worklist server
- Allow connections from 10.200.1.8 (d2d-vm IP)

## Benefits

### Accuracy
- Eliminates manual data entry errors
- Ensures patient demographics match RIS/PACS
- Accession numbers are always correct

### Efficiency
- Faster workflow (no typing patient information)
- Reduced training requirements
- Fewer workflow interruptions

### Compliance
- Ensures proper patient identification
- Links imported documents to correct studies
- Maintains data integrity

## Files Modified/Added

**Backend:**
- `app/dicom_worklist.py` - Worklist query handler (NEW)
- `app/models.py` - Added WorklistConfig, WorklistQueryRequest models
- `app/main.py` - Added worklist API endpoints
- `app/dicom_sender.py` - Fixed import for Verification SOP class

**Frontend:**
- `static/worklist.html` - Worklist query interface (NEW)
- `static/index.html` - Added worklist button
- `static/app.js` - Added auto-population from worklist

## Testing

### Test Worklist Connection

```bash
curl -X POST http://10.200.1.8:8000/api/worklist/test \
  -H 'Content-Type: application/json' \
  -d '{
    "host": "10.17.1.21",
    "port": 5010,
    "ae_title": "AURVCMOD1",
    "calling_ae": "LIVUSWL"
  }'
```

### Query All Patients

```bash
curl -X POST http://10.200.1.8:8000/api/worklist/query \
  -H 'Content-Type: application/json' \
  -d '{
    "patient_name": "*",
    "config": {
      "host": "10.17.1.21",
      "port": 5010,
      "ae_title": "AURVCMOD1",
      "calling_ae": "LIVUSWL"
    }
  }'
```

### Query Specific Patient

```bash
curl -X POST http://10.200.1.8:8000/api/worklist/query \
  -H 'Content-Type: application/json' \
  -d '{
    "patient_name": "SMITH^JOHN",
    "patient_id": "12345",
    "config": {
      "host": "10.17.1.21",
      "port": 5010,
      "ae_title": "AURVCMOD1",
      "calling_ae": "LIVUSWL"
    }
  }'
```

## Security Considerations

- Worklist queries transmit PHI over the network
- Ensure network connection is secure (VPN/private network)
- Worklist server should require authentication (AE Title verification)
- D2D VM is on private network (10.200.1.8) - no public access
- All traffic between d2d-vm and worklist server stays on private network

## Future Enhancements

Possible additions:
- Save worklist query results for later use
- Auto-refresh worklist at intervals
- Support for multiple worklist servers
- Advanced filtering options
- Export worklist results to CSV
- Scheduled procedure reminders

---

**Document Version:** 1.0
**Last Updated:** 2026-01-23
**Status:** Production Ready ✅
