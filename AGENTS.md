# AGENTS.md

## Project overview
D2D (Documents to DICOM) is a FastAPI app with a static HTML/JS UI
that converts PDFs/JPG/PNG to DICOM and can send to PACS systems.
It also supports Modality Worklist (C-FIND) queries to auto-populate
metadata.

## Key directories and entrypoints
- app/
  - main.py: FastAPI app and API routes
  - dicom_converter.py: PDF/image to DICOM conversion
  - dicom_sender.py: DICOM C-STORE sender
  - dicom_worklist.py: Worklist (C-FIND) client
  - models.py: Pydantic request/response models
  - config.py: settings and paths
- static/
  - index.html, app.js, styles.css: UI
  - worklist.html: worklist UI
- test_pacs_connectivity.py: optional connectivity check
- Docs: README.md, WORKLIST-FEATURE.md, API-DOCUMENTATION.md

## Local development
Requirements: Python 3.8+ and Poppler (for PDF conversion).

Setup and run:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000.

## Docker
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## Tests
There is no automated test suite. Use manual checks:
- Upload and convert a PDF/JPG/PNG in the UI.
- Send to a configured PACS destination.
- Worklist query flow (if a MWL server is available).

Optional connectivity test (edit host/port in the script first):
```bash
python test_pacs_connectivity.py
```

## Configuration
Copy `.env.example` to `.env` and adjust as needed. Common keys:
- HOST, PORT
- ARCHIVE_PATH, UPLOAD_PATH
- MAX_FILE_SIZE

## Notes for changes
- If you add Python dependencies, update requirements.txt and ensure
  Docker builds still succeed.
- Avoid logging PHI and remember this app has no built-in auth.
