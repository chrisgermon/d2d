from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import shutil
import json
from pathlib import Path
from typing import Optional
import uuid
import os
import secrets
import asyncio

from app.config import settings
from app.models import (
    DicomMetadata,
    DicomDestination,
    ConversionRequest,
    ConversionResponse,
    WorklistConfig,
    WorklistQueryRequest,
    WorklistQueryAllRequest,
    QRSourceConfig,
    QRStorageConfig,
    QRQueryRequest,
    QRRetrieveRequest,
    QRTestRequest,
    BatchRetrieveRequest
)
from app.dicom_converter import DicomConverter
from app.dicom_sender import DicomSender
from app.dicom_worklist import WorklistQuery, query_all_worklists, ALL_WORKLIST_AE_TITLES
from app.dicom_logger import dicom_logger, DicomOperationType
from app.dicom_qr import QueryRetrieve, get_storage_scp, list_retrieved_studies, get_batch_job_manager

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

# API Key Authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)) -> Optional[str]:
    """Verify API key for protected endpoints (if API key requirement is enabled)"""
    # Check if API key requirement is disabled
    if not settings.require_api_key:
        return None  # Allow access without API key

    valid_keys = settings.get_api_keys_list()
    if api_key is None or api_key not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key

# Initialize services
converter = DicomConverter()
sender = DicomSender()

# Store uploaded files temporarily (in production, use a proper storage)
uploaded_files = {}

# Store DICOM destinations (in production, use a database)
# Use absolute path based on app directory to ensure consistency
destinations_file = Path(__file__).parent.parent / "destinations.json"
if not destinations_file.exists():
    destinations_file.write_text("[]")


def load_destinations() -> list:
    """Load destinations from file with error handling"""
    try:
        if destinations_file.exists():
            content = destinations_file.read_text()
            if content.strip():
                return json.loads(content)
        return []
    except (json.JSONDecodeError, IOError):
        return []


def save_destinations(destinations: list) -> None:
    """Save destinations to file with error handling"""
    destinations_file.write_text(json.dumps(destinations, indent=2))

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface"""
    html_file = Path("static/index.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>D2D - Documents to DICOM</h1><p>Static files not found</p>")

@app.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics():
    """Serve the network diagnostics page"""
    html_file = Path("static/diagnostics.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>Network Diagnostics</h1><p>Diagnostics page not found</p>")

@app.get("/worklist", response_class=HTMLResponse)
async def worklist():
    """Serve the worklist query page"""
    html_file = Path("static/worklist.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>Modality Worklist</h1><p>Worklist page not found</p>")

@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """Serve the settings configuration page"""
    html_file = Path("static/settings.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>Settings</h1><p>Settings page not found</p>")

@app.get("/api/network-info")
async def network_info():
    """Get container network information"""
    import socket
    import subprocess
    import os

    info = {}

    # Get hostname
    try:
        info["hostname"] = socket.gethostname()
    except:
        info["hostname"] = "unknown"

    # Get local IP addresses
    try:
        hostname = socket.gethostname()
        info["local_ips"] = socket.gethostbyname_ex(hostname)[2]
    except:
        info["local_ips"] = []

    # Try to get more detailed network info
    try:
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info["ip_addr_output"] = result.stdout
    except:
        info["ip_addr_output"] = "Command not available"

    # Get environment variables related to networking
    info["network_env"] = {
        k: v for k, v in os.environ.items()
        if any(x in k.upper() for x in ['HOST', 'PORT', 'IP', 'NETWORK', 'AZURE'])
    }

    return info

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
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
async def convert_to_dicom(request: ConversionRequest, api_key: str = Depends(verify_api_key)):
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
    destination: str = Form(...),
    api_key: str = Depends(verify_api_key)
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
async def get_destinations(api_key: str = Depends(verify_api_key)):
    """Get all saved DICOM destinations"""
    return {"destinations": load_destinations()}

@app.post("/api/destinations")
async def save_destination(destination: DicomDestination, api_key: str = Depends(verify_api_key)):
    """Save a new DICOM destination"""
    destinations = load_destinations()
    destinations.append(destination.model_dump())
    save_destinations(destinations)
    return {"success": True, "message": "Destination saved"}

@app.delete("/api/destinations/{destination_name}")
async def delete_destination(destination_name: str, api_key: str = Depends(verify_api_key)):
    """Delete a DICOM destination"""
    destinations = load_destinations()
    destinations = [d for d in destinations if d["name"] != destination_name]
    save_destinations(destinations)
    return {"success": True, "message": "Destination deleted"}

@app.post("/api/destinations/verify")
async def verify_destination(destination: DicomDestination, api_key: str = Depends(verify_api_key)):
    """Verify connection to a DICOM destination"""
    success, message = sender.verify_destination(destination)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)

@app.get("/api/archives")
async def list_archives(api_key: str = Depends(verify_api_key)):
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
async def download_archive(filename: str, api_key: str = Depends(verify_api_key)):
    """Download an archived DICOM file"""
    file_path = settings.archive_path / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/dicom", filename=filename)

@app.get("/api/test-pacs")
async def test_pacs_quick():
    """Quick test to PACS at 10.17.1.21:5000"""
    import socket
    host = "10.17.1.21"
    port = 5000

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        success = (result == 0)
        return {
            "target": f"{host}:{port}",
            "reachable": success,
            "error_code": result,
            "message": "Connection successful!" if success else f"Connection failed (error code: {result})"
        }
    except Exception as e:
        return {
            "target": f"{host}:{port}",
            "reachable": False,
            "error": str(e),
            "message": f"Test failed: {str(e)}"
        }

@app.post("/api/test-connectivity")
async def test_connectivity(host: str = Form(...), port: int = Form(...)):
    """Test network connectivity to a PACS server"""
    import socket
    results = {}

    # Test 1: TCP connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        tcp_success = (result == 0)
        results["tcp"] = {
            "success": tcp_success,
            "message": f"TCP connection {'successful' if tcp_success else 'failed'} (code: {result})"
        }
    except Exception as e:
        results["tcp"] = {"success": False, "message": f"TCP test failed: {str(e)}"}

    # Test 2: DICOM C-ECHO
    try:
        from pynetdicom import AE
        from pynetdicom.sop_class import Verification

        ae = AE()
        ae.add_requested_context(Verification)
        ae.ae_title = "D2D_SCU"

        assoc = ae.associate(host, port, ae_title="ANY-SCP")

        if assoc.is_established:
            status = assoc.send_c_echo()
            assoc.release()

            dicom_success = bool(status)
            results["dicom"] = {
                "success": dicom_success,
                "message": f"DICOM C-ECHO {'successful' if dicom_success else 'failed'}"
            }
        else:
            results["dicom"] = {"success": False, "message": "DICOM association rejected"}

    except Exception as e:
        results["dicom"] = {"success": False, "message": f"DICOM test failed: {str(e)}"}

    return {"results": results, "target": f"{host}:{port}"}

@app.post("/api/worklist/query")
async def query_worklist(request: WorklistQueryRequest, api_key: str = Depends(verify_api_key)):
    """Query the modality worklist for scheduled studies"""
    try:
        config = request.config or WorklistConfig()

        worklist = WorklistQuery(
            host=config.host,
            port=config.port,
            ae_title=config.ae_title,
            calling_ae=config.calling_ae
        )

        success, items, message = worklist.query_worklist(
            patient_name=request.patient_name,
            patient_id=request.patient_id,
            accession_number=request.accession_number,
            scheduled_date=request.scheduled_date,
            modality=request.modality,
            station_ae_title=request.station_ae_title
        )

        if success:
            return {
                "success": True,
                "items": items,
                "count": len(items),
                "message": message
            }
        else:
            raise HTTPException(status_code=500, detail=message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/worklist/test")
async def test_worklist_connection(config: WorklistConfig, api_key: str = Depends(verify_api_key)):
    """Test connection to worklist server"""
    try:
        worklist = WorklistQuery(
            host=config.host,
            port=config.port,
            ae_title=config.ae_title,
            calling_ae=config.calling_ae
        )

        success, message = worklist.test_connection()

        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=500, detail=message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/worklist/config")
async def get_worklist_config(api_key: str = Depends(verify_api_key)):
    """Get default worklist configuration"""
    return WorklistConfig().model_dump()


@app.post("/api/worklist/query-all")
async def query_all_worklists_endpoint(request: WorklistQueryAllRequest, api_key: str = Depends(verify_api_key)):
    """Query all modality worklists for scheduled studies across all AE Titles"""
    try:
        success, items, status_dict = await query_all_worklists(
            host=request.host,
            port=request.port,
            calling_ae=request.calling_ae,
            patient_name=request.patient_name,
            patient_id=request.patient_id,
            accession_number=request.accession_number,
            scheduled_date=request.scheduled_date,
            modality=request.modality
        )

        summary = status_dict.pop("_summary", "Query completed")

        return {
            "success": success,
            "items": items,
            "count": len(items),
            "message": summary,
            "ae_title_count": len(ALL_WORKLIST_AE_TITLES)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/worklist/ae-titles")
async def get_worklist_ae_titles(api_key: str = Depends(verify_api_key)):
    """Get list of all available AE Titles for worklist queries"""
    return {
        "ae_titles": ALL_WORKLIST_AE_TITLES,
        "count": len(ALL_WORKLIST_AE_TITLES)
    }


# Query/Retrieve page route
@app.get("/qr", response_class=HTMLResponse)
async def qr_page():
    """Serve the Query/Retrieve tool page (local access only)"""
    html_file = Path("static/qr.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>Query/Retrieve Tool</h1><p>QR page not found</p>")


# Query/Retrieve API endpoints
@app.post("/api/qr/test")
async def test_qr_connection(request: QRTestRequest):
    """Test connection to PACS server for Query/Retrieve"""
    try:
        qr = QueryRetrieve(
            host=request.source.host,
            port=request.source.port,
            ae_title=request.source.ae_title,
            calling_ae=request.source.calling_ae
        )

        success, message = qr.test_connection()

        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=500, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/qr/query")
async def query_studies(request: QRQueryRequest):
    """Query PACS for studies by accession numbers"""
    try:
        qr = QueryRetrieve(
            host=request.source.host,
            port=request.source.port,
            ae_title=request.source.ae_title,
            calling_ae=request.source.calling_ae
        )

        success, studies, message = qr.find_studies_by_accession(request.accession_numbers)

        return {
            "success": success,
            "studies": studies,
            "count": len(studies),
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/qr/retrieve")
async def retrieve_studies(request: QRRetrieveRequest):
    """Retrieve studies from PACS using C-MOVE"""
    try:
        # Ensure Storage SCP is running
        storage_scp = get_storage_scp()
        if not storage_scp.is_running():
            success, msg = storage_scp.start()
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to start Storage SCP: {msg}")

        qr = QueryRetrieve(
            host=request.source.host,
            port=request.source.port,
            ae_title=request.source.ae_title,
            calling_ae=request.source.calling_ae,
            move_destination_ae=request.storage.ae_title
        )

        success_count, failed_count, errors = qr.retrieve_studies(request.study_uids)

        return {
            "success": failed_count == 0,
            "retrieved": success_count,
            "failed": failed_count,
            "errors": errors,
            "message": f"Retrieved {success_count} studies, {failed_count} failed"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/storage/status")
async def get_storage_status():
    """Get Storage SCP status and configuration"""
    storage_scp = get_storage_scp()
    return {
        "running": storage_scp.is_running(),
        "ae_title": storage_scp.ae_title,
        "port": storage_scp.port,
        "storage_path": str(storage_scp.storage_path),
        "received_files_count": len(storage_scp.get_received_files())
    }


@app.post("/api/qr/storage/start")
async def start_storage_scp():
    """Start the Storage SCP"""
    try:
        storage_scp = get_storage_scp()
        if storage_scp.is_running():
            return {"success": True, "message": "Storage SCP already running"}

        success, message = storage_scp.start()
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=500, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/qr/storage/stop")
async def stop_storage_scp():
    """Stop the Storage SCP"""
    try:
        storage_scp = get_storage_scp()
        success, message = storage_scp.stop()
        return {"success": success, "message": message}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/storage/files")
async def list_storage_files():
    """List files received by Storage SCP in current session"""
    storage_scp = get_storage_scp()
    return {
        "files": storage_scp.get_received_files(),
        "count": len(storage_scp.get_received_files())
    }


@app.get("/api/qr/storage/studies")
async def list_stored_studies():
    """List all studies in the Q/R storage directory"""
    try:
        studies = list_retrieved_studies(str(settings.qr_storage_path))
        return {
            "success": True,
            "studies": studies,
            "count": len(studies),
            "storage_path": str(settings.qr_storage_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/config")
async def get_qr_config():
    """Get Q/R configuration including storage path"""
    return {
        "storage_path": str(settings.qr_storage_path),
        "scp_ae_title": settings.qr_scp_ae_title,
        "scp_port": settings.qr_scp_port
    }


# Batch Q/R API endpoints
@app.post("/api/qr/batch/start")
async def start_batch_job(request: BatchRetrieveRequest, background_tasks: BackgroundTasks):
    """
    Start a batch retrieval job.
    Returns immediately with a job_id for tracking progress.
    """
    try:
        # Ensure Storage SCP is running if auto_retrieve is enabled
        if request.auto_retrieve:
            storage_scp = get_storage_scp()
            if not storage_scp.is_running():
                success, msg = storage_scp.start()
                if not success:
                    raise HTTPException(status_code=500, detail=f"Failed to start Storage SCP: {msg}")

        # Create the batch job
        job_manager = get_batch_job_manager()
        job_id = job_manager.create_job(
            accession_numbers=request.accession_numbers,
            source_config=request.source.model_dump(),
            storage_config=request.storage.model_dump(),
            auto_retrieve=request.auto_retrieve
        )

        # Run the job in background
        async def run_job_task():
            await job_manager.run_job(job_id)

        background_tasks.add_task(asyncio.create_task, run_job_task())

        return {
            "success": True,
            "job_id": job_id,
            "message": f"Batch job started with {len(request.accession_numbers)} accession numbers",
            "total_items": len(request.accession_numbers)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/batch/{job_id}/status")
async def get_batch_job_status(job_id: str):
    """Get current status of a batch job"""
    job_manager = get_batch_job_manager()
    status = job_manager.get_job_status(job_id)

    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return status


@app.get("/api/qr/batch/{job_id}/progress")
async def batch_job_progress_stream(job_id: str):
    """
    Server-Sent Events (SSE) endpoint for real-time progress updates.
    Connect to this endpoint to receive live updates about job progress.
    """
    job_manager = get_batch_job_manager()

    # Verify job exists
    status = job_manager.get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def event_generator():
        queue = job_manager.subscribe(job_id)
        try:
            # Send initial status
            initial_status = job_manager.get_job_status(job_id)
            if initial_status:
                yield f"data: {json.dumps({'type': 'initial', **initial_status})}\n\n"

            # Stream events
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"

                    # Stop streaming if job is complete
                    if event.get("type") in ("job_completed", "job_failed", "job_cancelled"):
                        break

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f": keepalive\n\n"

                    # Check if job is still active
                    current_status = job_manager.get_job_status(job_id)
                    if current_status and current_status["status"] in ("completed", "failed", "cancelled"):
                        break

        finally:
            job_manager.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/qr/batch/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """Cancel a running batch job"""
    job_manager = get_batch_job_manager()

    status = job_manager.get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if status["status"] != "running":
        raise HTTPException(status_code=400, detail=f"Job is not running (status: {status['status']})")

    success = job_manager.cancel_job(job_id)

    if success:
        return {"success": True, "message": "Cancellation requested"}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


@app.get("/api/qr/batch/jobs")
async def list_batch_jobs():
    """List all batch jobs"""
    job_manager = get_batch_job_manager()
    jobs = job_manager.list_jobs()
    return {
        "success": True,
        "jobs": jobs,
        "count": len(jobs)
    }


# Settings API endpoints
@app.get("/api/settings")
async def get_settings():
    """Get current application settings (public - no auth required)"""
    return {
        "require_api_key": settings.require_api_key,
        "api_keys_count": len(settings.get_api_keys_list()),
        "max_file_size": settings.max_file_size,
        "archive_path": str(settings.archive_path),
        "upload_path": str(settings.upload_path),
        "host": settings.host,
        "port": settings.port,
        "deployment_timestamp": settings.deployment_timestamp
    }

@app.get("/api/settings/security")
async def get_security_settings():
    """Get security settings including API keys (public for configuration)"""
    return {
        "require_api_key": settings.require_api_key,
        "api_keys": settings.api_keys
    }

@app.post("/api/settings/security")
async def update_security_settings(
    require_api_key: bool = Form(...),
    api_keys: str = Form(...)
):
    """Update security settings"""
    # Validate that at least one API key is provided if requiring API keys
    keys_list = [k.strip() for k in api_keys.split(",") if k.strip()]
    if require_api_key and len(keys_list) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one API key is required when API key authentication is enabled"
        )

    # Save settings
    settings.save_runtime_settings(require_api_key=require_api_key, api_keys=api_keys)

    return {
        "success": True,
        "message": "Security settings updated successfully",
        "require_api_key": settings.require_api_key,
        "api_keys_count": len(settings.get_api_keys_list())
    }

@app.post("/api/settings/api-key/generate")
async def generate_api_key():
    """Generate a new random API key"""
    new_key = f"d2d-{secrets.token_urlsafe(32)}"
    return {"api_key": new_key}


# DICOM Logs API endpoints
@app.get("/api/dicom-logs")
async def get_dicom_logs(
    operation_type: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get DICOM operation logs with optional filtering

    Args:
        operation_type: Filter by operation type (worklist_query, worklist_query_all, dicom_send, dicom_verify)
        success: Filter by success status (true/false)
        limit: Maximum number of logs to return (default 100)
        offset: Number of logs to skip for pagination (default 0)
    """
    try:
        # Convert operation_type string to enum if provided
        op_type = None
        if operation_type:
            try:
                op_type = DicomOperationType(operation_type)
            except ValueError:
                valid_types = [t.value for t in DicomOperationType]
                return {
                    "success": False,
                    "error": f"Invalid operation_type. Valid values: {valid_types}"
                }

        logs, total_count = dicom_logger.get_logs(
            operation_type=op_type,
            success=success,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "logs": logs,
            "count": len(logs),
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/dicom-logs")
async def clear_dicom_logs():
    """Clear all DICOM operation logs"""
    try:
        dicom_logger.clear_logs()
        return {"success": True, "message": "All DICOM logs cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/dicom-logs/stats")
async def get_dicom_logs_stats():
    """Get statistics about DICOM operation logs"""
    try:
        all_logs, total = dicom_logger.get_logs(limit=10000)

        stats = {
            "total_operations": total,
            "by_type": {},
            "by_status": {
                "success": 0,
                "failed": 0
            },
            "recent_failures": []
        }

        # Count by type
        for op_type in DicomOperationType:
            type_logs, type_count = dicom_logger.get_logs(operation_type=op_type, limit=10000)
            success_count = sum(1 for l in type_logs if l.get("success"))
            stats["by_type"][op_type.value] = {
                "total": type_count,
                "success": success_count,
                "failed": type_count - success_count
            }

        # Count overall success/fail
        for log in all_logs:
            if log.get("success"):
                stats["by_status"]["success"] += 1
            else:
                stats["by_status"]["failed"] += 1

        # Get recent failures (last 10)
        failed_logs, _ = dicom_logger.get_logs(success=False, limit=10)
        stats["recent_failures"] = failed_logs

        return {"success": True, "stats": stats}

    except Exception as e:
        return {"success": False, "error": str(e)}


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
