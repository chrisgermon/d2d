from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import json
from pathlib import Path
from typing import Optional
import uuid

from app.config import settings
from app.models import (
    DicomMetadata,
    DicomDestination,
    ConversionRequest,
    ConversionResponse
)
from app.dicom_converter import DicomConverter
from app.dicom_sender import DicomSender

app = FastAPI(
    title="Documents to DICOM (D2D)",
    description="Convert documents and images to DICOM format and send to PACS",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
converter = DicomConverter()
sender = DicomSender()

# Store uploaded files temporarily (in production, use a proper storage)
uploaded_files = {}

# Store DICOM destinations (in production, use a database)
destinations_file = Path("destinations.json")
if not destinations_file.exists():
    destinations_file.write_text("[]")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface"""
    html_file = Path("static/index.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>D2D - Documents to DICOM</h1><p>Static files not found</p>")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document or image file"""
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_file_size / 1_000_000}MB"
        )

    # Check file type
    allowed_types = [
        'application/pdf',
        'image/jpeg',
        'image/jpg',
        'image/png'
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: PDF, JPG, PNG"
        )

    # Save file
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    file_path = settings.upload_path / f"{file_id}{file_extension}"

    with open(file_path, "wb") as f:
        f.write(file_content)

    # Store file info
    uploaded_files[file_id] = {
        "filename": file.filename,
        "path": str(file_path),
        "content_type": file.content_type
    }

    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": len(file_content)
    }

@app.post("/api/convert", response_model=ConversionResponse)
async def convert_to_dicom(request: ConversionRequest):
    """Convert uploaded file to DICOM"""
    # Get uploaded file
    if request.file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")

    file_info = uploaded_files[request.file_id]
    file_path = Path(file_info["path"])

    try:
        # Convert to DICOM
        dicom_path, study_uid, series_uid, sop_uid = converter.convert_to_dicom(
            file_path,
            request.metadata
        )

        # Send if requested
        send_message = None
        if request.send_immediately and request.destination:
            success, message = sender.send_dicom(dicom_path, request.destination)
            send_message = message
            if not success:
                return ConversionResponse(
                    success=False,
                    message=f"Conversion successful but send failed: {message}",
                    dicom_file_path=str(dicom_path),
                    sop_instance_uid=sop_uid,
                    study_instance_uid=study_uid,
                    series_instance_uid=series_uid
                )

        # Clean up uploaded file
        file_path.unlink(missing_ok=True)
        del uploaded_files[request.file_id]

        message = "DICOM file created successfully"
        if send_message:
            message += f". {send_message}"

        return ConversionResponse(
            success=True,
            message=message,
            dicom_file_path=str(dicom_path),
            sop_instance_uid=sop_uid,
            study_instance_uid=study_uid,
            series_instance_uid=series_uid
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send")
async def send_dicom_file(
    dicom_file_path: str = Form(...),
    destination: str = Form(...)
):
    """Send an existing DICOM file to a destination"""
    try:
        dest = DicomDestination(**json.loads(destination))
        success, message = sender.send_dicom(Path(dicom_file_path), dest)

        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=500, detail=message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/destinations")
async def get_destinations():
    """Get all saved DICOM destinations"""
    destinations = json.loads(destinations_file.read_text())
    return {"destinations": destinations}

@app.post("/api/destinations")
async def save_destination(destination: DicomDestination):
    """Save a new DICOM destination"""
    destinations = json.loads(destinations_file.read_text())
    destinations.append(destination.model_dump())
    destinations_file.write_text(json.dumps(destinations, indent=2))
    return {"success": True, "message": "Destination saved"}

@app.delete("/api/destinations/{destination_name}")
async def delete_destination(destination_name: str):
    """Delete a DICOM destination"""
    destinations = json.loads(destinations_file.read_text())
    destinations = [d for d in destinations if d["name"] != destination_name]
    destinations_file.write_text(json.dumps(destinations, indent=2))
    return {"success": True, "message": "Destination deleted"}

@app.post("/api/destinations/verify")
async def verify_destination(destination: DicomDestination):
    """Verify connection to a DICOM destination"""
    success, message = sender.verify_destination(destination)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

@app.get("/api/archives")
async def list_archives():
    """List all archived DICOM files"""
    archives = []
    for file in settings.archive_path.glob("*.dcm"):
        archives.append({
            "filename": file.name,
            "path": str(file),
            "size": file.stat().st_size,
            "created": file.stat().st_ctime
        })
    return {"archives": sorted(archives, key=lambda x: x["created"], reverse=True)}

@app.get("/api/archives/{filename}")
async def download_archive(filename: str):
    """Download an archived DICOM file"""
    file_path = settings.archive_path / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/dicom", filename=filename)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
