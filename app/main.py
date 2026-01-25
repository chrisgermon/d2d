from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import shutil
import json
from pathlib import Path
from typing import Optional
import uuid
import os
import secrets

from app.config import settings
from app.models import (
    DicomMetadata,
    DicomDestination,
    ConversionRequest,
    ConversionResponse,
    WorklistConfig,
    WorklistQueryRequest,
    WorklistQueryAllRequest
)
from app.dicom_converter import DicomConverter
from app.dicom_sender import DicomSender
from app.dicom_worklist import WorklistQuery, query_all_worklists, ALL_WORKLIST_AE_TITLES
from app.dicom_logger import dicom_logger, DicomOperationType

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
