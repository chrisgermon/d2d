"""
DICOM Query/Retrieve (Q/R) Module

Provides C-FIND and C-MOVE functionality for retrieving studies from PACS systems.
Includes a Storage SCP to receive incoming DICOM files.
"""

from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    PatientRootQueryRetrieveInformationModelFind,
    PatientRootQueryRetrieveInformationModelMove,
    Verification
)
from pydicom import dcmread
from pydicom.dataset import Dataset
from typing import List, Optional, Dict, Callable, Any
from datetime import datetime
from pathlib import Path
import threading
import logging
import os
import uuid
import asyncio
from collections import deque

# Configure logging
logger = logging.getLogger(__name__)


class StorageSCP:
    """
    DICOM Storage SCP (Service Class Provider) to receive incoming C-STORE requests.
    Runs in a background thread to receive files from C-MOVE operations.
    """

    def __init__(
        self,
        ae_title: str = "D2D_STORE",
        port: int = 11113,
        storage_path: str = "./qr_storage"
    ):
        self.ae_title = ae_title
        self.port = port
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._server = None
        self._thread = None
        self._running = False
        self._received_files: List[Dict] = []
        self._on_file_received: Optional[Callable] = None

    def _handle_store(self, event):
        """Handle incoming C-STORE requests"""
        try:
            ds = event.dataset
            ds.file_meta = event.file_meta

            # Generate filename from DICOM attributes
            patient_id = str(ds.get("PatientID", "UNKNOWN"))
            patient_name = str(ds.get("PatientName", ""))
            study_uid = str(ds.get("StudyInstanceUID", ""))
            series_uid = str(ds.get("SeriesInstanceUID", ""))
            sop_uid = str(ds.get("SOPInstanceUID", ""))
            accession = str(ds.get("AccessionNumber", ""))

            # Extract last name from PatientName (format: LastName^FirstName^...)
            last_name = patient_name.split("^")[0] if patient_name else ""

            # Clean filename components
            safe_patient_id = "".join(c for c in patient_id if c.isalnum() or c in "-_")[:20]
            safe_accession = "".join(c for c in accession if c.isalnum() or c in "-_")[:20]
            safe_last_name = "".join(c for c in last_name if c.isalnum() or c in "-_")[:20]

            # Create subdirectory structure: storage_path/accession-lastname/study_uid/
            if safe_accession:
                folder_name = f"{safe_accession}-{safe_last_name}" if safe_last_name else safe_accession
                study_dir = self.storage_path / folder_name / study_uid[:20]
            else:
                study_dir = self.storage_path / safe_patient_id / study_uid[:20]

            study_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{sop_uid[:20]}_{timestamp}.dcm"
            file_path = study_dir / filename

            # Save the DICOM file
            ds.save_as(file_path, write_like_original=False)

            # Track received file
            file_info = {
                "path": str(file_path),
                "patient_id": patient_id,
                "patient_name": str(ds.get("PatientName", "")),
                "study_uid": study_uid,
                "series_uid": series_uid,
                "sop_uid": sop_uid,
                "accession_number": accession,
                "modality": str(ds.get("Modality", "")),
                "study_description": str(ds.get("StudyDescription", "")),
                "series_description": str(ds.get("SeriesDescription", "")),
                "received_at": datetime.now().isoformat()
            }
            self._received_files.append(file_info)

            logger.info(f"Received DICOM file: {file_path}")

            # Call callback if registered
            if self._on_file_received:
                try:
                    self._on_file_received(file_info)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            return 0x0000  # Success

        except Exception as e:
            logger.error(f"Error handling C-STORE: {e}")
            return 0xC001  # Error

    def start(self):
        """Start the Storage SCP in a background thread"""
        if self._running:
            return True, "Storage SCP already running"

        try:
            # Create Application Entity
            self.ae = AE(ae_title=self.ae_title)

            # Add all standard storage contexts
            for context in StoragePresentationContexts:
                self.ae.add_supported_context(context.abstract_syntax)

            # Also support Verification (C-ECHO)
            self.ae.add_supported_context(Verification)

            # Event handlers
            handlers = [
                (evt.EVT_C_STORE, self._handle_store),
            ]

            # Start server in background thread
            def run_server():
                self._running = True
                try:
                    self._server = self.ae.start_server(
                        ("0.0.0.0", self.port),
                        block=True,
                        evt_handlers=handlers
                    )
                except Exception as e:
                    logger.error(f"Storage SCP error: {e}")
                finally:
                    self._running = False

            self._thread = threading.Thread(target=run_server, daemon=True)
            self._thread.start()

            # Wait a moment to ensure server started
            import time
            time.sleep(0.5)

            if self._running:
                logger.info(f"Storage SCP started on port {self.port} with AE Title {self.ae_title}")
                return True, f"Storage SCP started on port {self.port}"
            else:
                return False, "Failed to start Storage SCP"

        except Exception as e:
            logger.error(f"Failed to start Storage SCP: {e}")
            return False, f"Failed to start: {str(e)}"

    def stop(self):
        """Stop the Storage SCP"""
        if self._server:
            try:
                self._server.shutdown()
                self._running = False
                logger.info("Storage SCP stopped")
                return True, "Storage SCP stopped"
            except Exception as e:
                return False, f"Error stopping: {str(e)}"
        return True, "Storage SCP was not running"

    def is_running(self) -> bool:
        """Check if the Storage SCP is running"""
        return self._running

    def get_received_files(self) -> List[Dict]:
        """Get list of received files"""
        return self._received_files.copy()

    def clear_received_files(self):
        """Clear the list of received files"""
        self._received_files.clear()

    def set_callback(self, callback: Callable):
        """Set callback function for when files are received"""
        self._on_file_received = callback


class QueryRetrieve:
    """
    DICOM Query/Retrieve SCU for C-FIND and C-MOVE operations.
    """

    def __init__(
        self,
        host: str,
        port: int,
        ae_title: str,
        calling_ae: str = "D2D_QR",
        move_destination_ae: str = "D2D_STORE"
    ):
        self.host = host
        self.port = port
        self.ae_title = ae_title
        self.calling_ae = calling_ae
        self.move_destination_ae = move_destination_ae

        # Create Application Entity
        self.ae = AE(ae_title=calling_ae)
        self.ae.acse_timeout = 30
        self.ae.dimse_timeout = 120
        self.ae.network_timeout = 30

        # Add Query/Retrieve contexts
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(Verification)

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to PACS using C-ECHO"""
        try:
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if assoc.is_established:
                status = assoc.send_c_echo()
                assoc.release()

                if status and status.Status == 0x0000:
                    return True, f"Successfully connected to {self.ae_title} at {self.host}:{self.port}"
                else:
                    return False, "C-ECHO failed"
            else:
                return False, f"Association rejected by {self.ae_title}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def find_studies_by_accession(
        self,
        accession_numbers: List[str]
    ) -> tuple[bool, List[Dict], str]:
        """
        Find studies by accession numbers using C-FIND.

        Args:
            accession_numbers: List of accession numbers to search for

        Returns:
            tuple: (success, list of found studies, message)
        """
        all_studies = []
        failed = []

        try:
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if not assoc.is_established:
                return False, [], f"Failed to connect to {self.ae_title}"

            for accession in accession_numbers:
                accession = accession.strip()
                if not accession:
                    continue

                # Build query dataset
                query_ds = Dataset()
                query_ds.QueryRetrieveLevel = "STUDY"
                query_ds.AccessionNumber = accession

                # Request return keys
                query_ds.PatientName = ""
                query_ds.PatientID = ""
                query_ds.PatientBirthDate = ""
                query_ds.PatientSex = ""
                query_ds.StudyInstanceUID = ""
                query_ds.StudyDate = ""
                query_ds.StudyTime = ""
                query_ds.StudyDescription = ""
                query_ds.ModalitiesInStudy = ""
                query_ds.NumberOfStudyRelatedSeries = ""
                query_ds.NumberOfStudyRelatedInstances = ""
                query_ds.ReferringPhysicianName = ""

                # Perform C-FIND
                responses = assoc.send_c_find(
                    query_ds,
                    StudyRootQueryRetrieveInformationModelFind
                )

                found = False
                for (status, identifier) in responses:
                    if status and status.Status in [0xFF00, 0xFF01]:  # Pending
                        if identifier:
                            study = self._parse_study(identifier, accession)
                            if study:
                                all_studies.append(study)
                                found = True

                if not found:
                    failed.append(accession)

            assoc.release()

            message = f"Found {len(all_studies)} studies"
            if failed:
                message += f". Not found: {', '.join(failed)}"

            return True, all_studies, message

        except Exception as e:
            return False, all_studies, f"Query failed: {str(e)}"

    def _parse_study(self, dataset: Dataset, searched_accession: str) -> Optional[Dict]:
        """Parse C-FIND response into a dictionary"""
        try:
            study = {
                "accession_number": str(dataset.get("AccessionNumber", searched_accession)),
                "patient_name": str(dataset.get("PatientName", "")),
                "patient_id": str(dataset.get("PatientID", "")),
                "patient_birth_date": self._parse_date(str(dataset.get("PatientBirthDate", ""))),
                "patient_sex": str(dataset.get("PatientSex", "")),
                "study_instance_uid": str(dataset.get("StudyInstanceUID", "")),
                "study_date": self._parse_date(str(dataset.get("StudyDate", ""))),
                "study_time": self._parse_time(str(dataset.get("StudyTime", ""))),
                "study_description": str(dataset.get("StudyDescription", "")),
                "modalities": str(dataset.get("ModalitiesInStudy", "")),
                "num_series": str(dataset.get("NumberOfStudyRelatedSeries", "")),
                "num_instances": str(dataset.get("NumberOfStudyRelatedInstances", "")),
                "referring_physician": str(dataset.get("ReferringPhysicianName", ""))
            }
            return study
        except Exception as e:
            logger.error(f"Error parsing study: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse DICOM date (YYYYMMDD) to readable format"""
        if not date_str or len(date_str) < 8:
            return None
        try:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return None

    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse DICOM time to readable format"""
        if not time_str or len(time_str) < 4:
            return None
        try:
            return f"{time_str[0:2]}:{time_str[2:4]}"
        except:
            return None

    def retrieve_study(self, study_instance_uid: str) -> tuple[bool, str]:
        """
        Retrieve a study using C-MOVE.

        Args:
            study_instance_uid: The Study Instance UID to retrieve

        Returns:
            tuple: (success, message)
        """
        try:
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if not assoc.is_established:
                return False, f"Failed to connect to {self.ae_title}"

            # Build move dataset
            move_ds = Dataset()
            move_ds.QueryRetrieveLevel = "STUDY"
            move_ds.StudyInstanceUID = study_instance_uid

            # Perform C-MOVE
            responses = assoc.send_c_move(
                move_ds,
                self.move_destination_ae,
                StudyRootQueryRetrieveInformationModelMove
            )

            completed = 0
            failed = 0
            warning = 0

            for (status, identifier) in responses:
                if status:
                    if status.Status == 0x0000:  # Success
                        completed += 1
                    elif status.Status == 0xFF00:  # Pending
                        pass
                    elif status.Status in [0xB000, 0xB007]:  # Warning
                        warning += 1
                    else:
                        failed += 1

            assoc.release()

            if failed > 0:
                return False, f"Retrieve completed with errors. Failed: {failed}"
            elif completed == 0:
                return False, "Retrieve failed: No images transferred. Check PACS configuration for move destination AE."
            elif warning > 0:
                return True, f"Retrieve completed with warnings. Warnings: {warning}"
            else:
                return True, "Study retrieved successfully"

        except Exception as e:
            return False, f"Retrieve failed: {str(e)}"

    def retrieve_studies(self, study_uids: List[str]) -> tuple[int, int, List[str]]:
        """
        Retrieve multiple studies by Study Instance UID.

        Args:
            study_uids: List of Study Instance UIDs to retrieve

        Returns:
            tuple: (success_count, failed_count, list of error messages)
        """
        success_count = 0
        failed_count = 0
        errors = []

        for uid in study_uids:
            uid = uid.strip()
            if not uid:
                continue

            success, message = self.retrieve_study(uid)
            if success:
                success_count += 1
            else:
                failed_count += 1
                errors.append(f"{uid[:20]}...: {message}")

        return success_count, failed_count, errors


# Global Storage SCP instance
_storage_scp: Optional[StorageSCP] = None


def get_storage_scp() -> StorageSCP:
    """Get or create the global Storage SCP instance"""
    global _storage_scp
    if _storage_scp is None:
        from app.config import settings
        storage_path = getattr(settings, 'qr_storage_path', Path("./qr_storage"))
        _storage_scp = StorageSCP(
            ae_title="D2D_STORE",
            port=11113,
            storage_path=str(storage_path)
        )
    return _storage_scp


def list_retrieved_studies(storage_path: str = "./qr_storage") -> List[Dict]:
    """
    List all retrieved studies in the storage directory.
    Returns organized list of studies with their files.
    """
    storage = Path(storage_path)
    if not storage.exists():
        return []

    studies = []

    # Walk through accession/study directories
    for accession_dir in storage.iterdir():
        if not accession_dir.is_dir():
            continue

        for study_dir in accession_dir.iterdir():
            if not study_dir.is_dir():
                continue

            dcm_files = list(study_dir.glob("*.dcm"))
            if not dcm_files:
                continue

            # Read first file to get study info
            try:
                ds = dcmread(dcm_files[0], stop_before_pixels=True)
                study_info = {
                    "accession_number": accession_dir.name,
                    "study_uid": str(ds.get("StudyInstanceUID", study_dir.name)),
                    "patient_name": str(ds.get("PatientName", "")),
                    "patient_id": str(ds.get("PatientID", "")),
                    "study_date": str(ds.get("StudyDate", "")),
                    "study_description": str(ds.get("StudyDescription", "")),
                    "modality": str(ds.get("Modality", "")),
                    "file_count": len(dcm_files),
                    "directory": str(study_dir),
                    "total_size_mb": round(sum(f.stat().st_size for f in dcm_files) / (1024 * 1024), 2)
                }
                studies.append(study_info)
            except Exception as e:
                logger.error(f"Error reading {dcm_files[0]}: {e}")
                # Still add basic info
                studies.append({
                    "accession_number": accession_dir.name,
                    "study_uid": study_dir.name,
                    "file_count": len(dcm_files),
                    "directory": str(study_dir),
                    "error": str(e)
                })

    return studies


class BatchJobManager:
    """
    Manages batch DICOM Q/R jobs with progress tracking.
    Provides real-time updates via SSE (Server-Sent Events).
    """

    def __init__(self):
        self._jobs: Dict[str, Dict] = {}
        self._job_lock = threading.Lock()
        self._event_queues: Dict[str, List[asyncio.Queue]] = {}
        self._max_jobs_history = 50  # Keep last 50 completed jobs

    def create_job(
        self,
        accession_numbers: List[str],
        source_config: Dict,
        storage_config: Dict,
        auto_retrieve: bool = True
    ) -> str:
        """Create a new batch job and return job ID"""
        job_id = str(uuid.uuid4())[:8]

        # Clean and deduplicate accession numbers
        clean_accessions = list(dict.fromkeys([
            acc.strip() for acc in accession_numbers if acc.strip()
        ]))

        with self._job_lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "total_items": len(clean_accessions),
                "queried_items": 0,
                "retrieved_items": 0,
                "failed_items": 0,
                "progress_percent": 0.0,
                "items": [
                    {
                        "accession_number": acc,
                        "status": "pending",
                        "study_uid": None,
                        "patient_name": None,
                        "patient_id": None,
                        "study_date": None,
                        "modality": None,
                        "num_instances": None,
                        "error_message": None,
                        "started_at": None,
                        "completed_at": None
                    }
                    for acc in clean_accessions
                ],
                "source_config": source_config,
                "storage_config": storage_config,
                "auto_retrieve": auto_retrieve,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error_message": None,
                "cancel_requested": False
            }
            self._event_queues[job_id] = []

        logger.info(f"Created batch job {job_id} with {len(clean_accessions)} accession numbers")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of a job"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job:
                # Return a copy without internal fields
                return {
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "total_items": job["total_items"],
                    "queried_items": job["queried_items"],
                    "retrieved_items": job["retrieved_items"],
                    "failed_items": job["failed_items"],
                    "progress_percent": job["progress_percent"],
                    "items": job["items"],
                    "created_at": job["created_at"],
                    "started_at": job["started_at"],
                    "completed_at": job["completed_at"],
                    "error_message": job["error_message"]
                }
        return None

    def list_jobs(self) -> List[Dict]:
        """List all jobs with summary info"""
        with self._job_lock:
            return [
                {
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "total_items": job["total_items"],
                    "queried_items": job["queried_items"],
                    "retrieved_items": job["retrieved_items"],
                    "failed_items": job["failed_items"],
                    "progress_percent": job["progress_percent"],
                    "created_at": job["created_at"],
                    "completed_at": job["completed_at"]
                }
                for job in self._jobs.values()
            ]

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a pending or running job"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job["status"] == "pending":
                # For pending jobs, cancel immediately since they haven't started
                job["status"] = "cancelled"
                job["completed_at"] = datetime.now().isoformat()
                for item in job["items"]:
                    if item["status"] == "pending":
                        item["status"] = "cancelled"
                logger.info(f"Pending job {job_id} cancelled immediately")
                return True
            elif job["status"] == "running":
                job["cancel_requested"] = True
                logger.info(f"Cancellation requested for job {job_id}")
                return True
        return False

    def _update_job(self, job_id: str, updates: Dict):
        """Update job state and notify subscribers"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            for key, value in updates.items():
                if key == "items":
                    # Handle item updates specially
                    continue
                job[key] = value

            # Calculate progress percentage
            total = job["total_items"]
            if total > 0:
                if job["auto_retrieve"]:
                    # Progress = 50% query + 50% retrieve
                    query_progress = (job["queried_items"] / total) * 50
                    retrieve_progress = (job["retrieved_items"] / total) * 50
                    job["progress_percent"] = round(query_progress + retrieve_progress, 1)
                else:
                    # Query only
                    job["progress_percent"] = round((job["queried_items"] / total) * 100, 1)

        # Send event to all subscribers
        self._send_event(job_id, {
            "type": "progress",
            "job_id": job_id,
            "status": job["status"],
            "progress_percent": job["progress_percent"],
            "queried_items": job["queried_items"],
            "retrieved_items": job["retrieved_items"],
            "failed_items": job["failed_items"],
            "total_items": job["total_items"]
        })

    def _update_item(self, job_id: str, accession: str, updates: Dict):
        """Update a single item's status"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            for item in job["items"]:
                if item["accession_number"] == accession:
                    for key, value in updates.items():
                        item[key] = value
                    break

        # Send item update event
        self._send_event(job_id, {
            "type": "item_update",
            "job_id": job_id,
            "accession_number": accession,
            **updates
        })

    def _send_event(self, job_id: str, event_data: Dict):
        """Send event to all subscribed queues"""
        queues = self._event_queues.get(job_id, [])
        for queue in queues:
            try:
                queue.put_nowait(event_data)
            except asyncio.QueueFull:
                pass  # Skip if queue is full

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Subscribe to job events"""
        queue = asyncio.Queue(maxsize=100)
        with self._job_lock:
            if job_id in self._event_queues:
                self._event_queues[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        """Unsubscribe from job events"""
        with self._job_lock:
            if job_id in self._event_queues:
                try:
                    self._event_queues[job_id].remove(queue)
                except ValueError:
                    pass

    def _cleanup_old_jobs(self):
        """Remove old completed jobs to prevent memory buildup"""
        with self._job_lock:
            completed_jobs = [
                (job_id, job["completed_at"])
                for job_id, job in self._jobs.items()
                if job["status"] in ("completed", "cancelled", "failed") and job["completed_at"]
            ]

            if len(completed_jobs) > self._max_jobs_history:
                # Sort by completion time and remove oldest
                completed_jobs.sort(key=lambda x: x[1])
                to_remove = len(completed_jobs) - self._max_jobs_history
                for job_id, _ in completed_jobs[:to_remove]:
                    del self._jobs[job_id]
                    if job_id in self._event_queues:
                        del self._event_queues[job_id]

    async def run_job(self, job_id: str):
        """Run a batch job (query and optionally retrieve)"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job["status"] != "pending":
                return
            job["status"] = "running"
            job["started_at"] = datetime.now().isoformat()

        self._send_event(job_id, {
            "type": "job_started",
            "job_id": job_id,
            "status": "running"
        })

        try:
            # Create QueryRetrieve instance
            source = job["source_config"]
            storage = job["storage_config"]

            qr = QueryRetrieve(
                host=source["host"],
                port=source["port"],
                ae_title=source["ae_title"],
                calling_ae=source.get("calling_ae", "D2D_QR"),
                move_destination_ae=storage.get("ae_title", "D2D_STORE")
            )

            # Phase 1: Query all accession numbers
            items_to_retrieve = []

            for item in job["items"]:
                # Check for cancellation
                if job["cancel_requested"]:
                    self._handle_cancellation(job_id)
                    return

                accession = item["accession_number"]
                self._update_item(job_id, accession, {
                    "status": "querying",
                    "started_at": datetime.now().isoformat()
                })

                try:
                    # Query for this accession
                    success, studies, message = qr.find_studies_by_accession([accession])

                    if success and studies:
                        study = studies[0]
                        self._update_item(job_id, accession, {
                            "status": "query_complete",
                            "study_uid": study.get("study_instance_uid"),
                            "patient_name": study.get("patient_name"),
                            "patient_id": study.get("patient_id"),
                            "study_date": study.get("study_date"),
                            "modality": study.get("modalities"),
                            "num_instances": study.get("num_instances")
                        })
                        items_to_retrieve.append({
                            "accession": accession,
                            "study_uid": study.get("study_instance_uid")
                        })
                    else:
                        self._update_item(job_id, accession, {
                            "status": "query_failed",
                            "error_message": f"Study not found: {message}",
                            "completed_at": datetime.now().isoformat()
                        })
                        with self._job_lock:
                            job["failed_items"] += 1

                except Exception as e:
                    logger.error(f"Query error for {accession}: {e}")
                    self._update_item(job_id, accession, {
                        "status": "query_failed",
                        "error_message": str(e),
                        "completed_at": datetime.now().isoformat()
                    })
                    with self._job_lock:
                        job["failed_items"] += 1

                with self._job_lock:
                    job["queried_items"] += 1
                self._update_job(job_id, {"queried_items": job["queried_items"]})

                # Small delay to prevent overwhelming the PACS
                await asyncio.sleep(0.1)

            # Phase 2: Retrieve studies (if auto_retrieve is enabled)
            if job["auto_retrieve"] and items_to_retrieve:
                for item_info in items_to_retrieve:
                    # Check for cancellation
                    if job["cancel_requested"]:
                        self._handle_cancellation(job_id)
                        return

                    accession = item_info["accession"]
                    study_uid = item_info["study_uid"]

                    if not study_uid:
                        continue

                    self._update_item(job_id, accession, {
                        "status": "retrieving"
                    })

                    try:
                        success, message = qr.retrieve_study(study_uid)

                        if success:
                            self._update_item(job_id, accession, {
                                "status": "completed",
                                "completed_at": datetime.now().isoformat()
                            })
                            with self._job_lock:
                                job["retrieved_items"] += 1
                        else:
                            self._update_item(job_id, accession, {
                                "status": "failed",
                                "error_message": message,
                                "completed_at": datetime.now().isoformat()
                            })
                            with self._job_lock:
                                job["failed_items"] += 1

                    except Exception as e:
                        logger.error(f"Retrieve error for {accession}: {e}")
                        self._update_item(job_id, accession, {
                            "status": "failed",
                            "error_message": str(e),
                            "completed_at": datetime.now().isoformat()
                        })
                        with self._job_lock:
                            job["failed_items"] += 1

                    self._update_job(job_id, {"retrieved_items": job["retrieved_items"]})

                    # Small delay between retrievals
                    await asyncio.sleep(0.2)

            # Job completed
            with self._job_lock:
                job["status"] = "completed"
                job["completed_at"] = datetime.now().isoformat()
                job["progress_percent"] = 100.0

            self._send_event(job_id, {
                "type": "job_completed",
                "job_id": job_id,
                "status": "completed",
                "queried_items": job["queried_items"],
                "retrieved_items": job["retrieved_items"],
                "failed_items": job["failed_items"]
            })

        except Exception as e:
            logger.error(f"Batch job {job_id} failed: {e}")
            with self._job_lock:
                job["status"] = "failed"
                job["error_message"] = str(e)
                job["completed_at"] = datetime.now().isoformat()

            self._send_event(job_id, {
                "type": "job_failed",
                "job_id": job_id,
                "error_message": str(e)
            })

        finally:
            self._cleanup_old_jobs()

    def _handle_cancellation(self, job_id: str):
        """Handle job cancellation"""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job:
                job["status"] = "cancelled"
                job["completed_at"] = datetime.now().isoformat()

                # Mark remaining pending items as cancelled
                for item in job["items"]:
                    if item["status"] in ("pending", "querying", "query_complete", "retrieving"):
                        item["status"] = "cancelled"
                        item["completed_at"] = datetime.now().isoformat()

        self._send_event(job_id, {
            "type": "job_cancelled",
            "job_id": job_id,
            "status": "cancelled"
        })

        logger.info(f"Job {job_id} cancelled")


# Global batch job manager instance
_batch_job_manager: Optional[BatchJobManager] = None


def get_batch_job_manager() -> BatchJobManager:
    """Get or create the global batch job manager instance"""
    global _batch_job_manager
    if _batch_job_manager is None:
        _batch_job_manager = BatchJobManager()
    return _batch_job_manager
