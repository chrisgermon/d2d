"""DICOM operation logging module for tracking worklist queries and DICOM sends"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import threading


class DicomOperationType(str, Enum):
    WORKLIST_QUERY = "worklist_query"
    WORKLIST_QUERY_ALL = "worklist_query_all"
    DICOM_SEND = "dicom_send"
    DICOM_VERIFY = "dicom_verify"
    DICOM_UPLOAD = "dicom_upload"


class DicomLogger:
    """Thread-safe logger for DICOM operations"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._file_lock = threading.Lock()
        self.log_file = Path(__file__).parent.parent / "dicom_logs.json"
        self.max_logs = 500  # Keep last 500 entries

        # Initialize log file if it doesn't exist
        if not self.log_file.exists():
            self._save_logs([])

    def _load_logs(self) -> List[Dict]:
        """Load logs from file"""
        try:
            if self.log_file.exists():
                content = self.log_file.read_text()
                if content.strip():
                    return json.loads(content)
            return []
        except (json.JSONDecodeError, IOError):
            return []

    def _save_logs(self, logs: List[Dict]) -> None:
        """Save logs to file"""
        with self._file_lock:
            self.log_file.write_text(json.dumps(logs, indent=2))

    def log(
        self,
        operation_type: DicomOperationType,
        success: bool,
        message: str,
        details: Optional[Dict] = None
    ) -> None:
        """Add a log entry"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation_type.value,
            "success": success,
            "message": message,
            "details": details or {}
        }

        logs = self._load_logs()
        logs.insert(0, entry)  # Add to beginning (newest first)

        # Trim to max size
        if len(logs) > self.max_logs:
            logs = logs[:self.max_logs]

        self._save_logs(logs)

    def log_worklist_query(
        self,
        success: bool,
        message: str,
        host: str,
        port: int,
        ae_title: str,
        calling_ae: str,
        patient_name: Optional[str] = None,
        patient_id: Optional[str] = None,
        accession_number: Optional[str] = None,
        modality: Optional[str] = None,
        results_count: int = 0
    ) -> None:
        """Log a worklist query operation"""
        details = {
            "host": host,
            "port": port,
            "ae_title": ae_title,
            "calling_ae": calling_ae,
            "filters": {
                "patient_name": patient_name,
                "patient_id": patient_id,
                "accession_number": accession_number,
                "modality": modality
            },
            "results_count": results_count
        }
        self.log(DicomOperationType.WORKLIST_QUERY, success, message, details)

    def log_worklist_query_all(
        self,
        success: bool,
        message: str,
        host: str,
        port: int,
        ae_title: str,
        ae_titles_queried: int,
        successful_queries: int,
        results_count: int
    ) -> None:
        """Log a query-all worklist operation"""
        details = {
            "host": host,
            "port": port,
            "ae_title": ae_title,
            "ae_titles_queried": ae_titles_queried,
            "successful_queries": successful_queries,
            "results_count": results_count
        }
        self.log(DicomOperationType.WORKLIST_QUERY_ALL, success, message, details)

    def log_dicom_send(
        self,
        success: bool,
        message: str,
        destination_name: str,
        host: str,
        port: int,
        ae_title: str,
        calling_ae: str,
        file_path: Optional[str] = None,
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        study_uid: Optional[str] = None,
        accession_number: Optional[str] = None
    ) -> None:
        """Log a DICOM send operation"""
        details = {
            "destination": {
                "name": destination_name,
                "host": host,
                "port": port,
                "ae_title": ae_title,
                "calling_ae": calling_ae
            },
            "file_path": file_path,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "study_uid": study_uid,
            "accession_number": accession_number
        }
        self.log(DicomOperationType.DICOM_SEND, success, message, details)

    def log_dicom_verify(
        self,
        success: bool,
        message: str,
        destination_name: str,
        host: str,
        port: int,
        ae_title: str,
        calling_ae: str
    ) -> None:
        """Log a DICOM verification (C-ECHO) operation"""
        details = {
            "destination": {
                "name": destination_name,
                "host": host,
                "port": port,
                "ae_title": ae_title,
                "calling_ae": calling_ae
            }
        }
        self.log(DicomOperationType.DICOM_VERIFY, success, message, details)

    def log_dicom_upload(
        self,
        success: bool,
        message: str,
        destination_name: str,
        host: str,
        port: int,
        ae_title: str,
        calling_ae: str,
        total_files: int = 0,
        successful_files: int = 0,
        failed_files: int = 0,
        file_details: Optional[List[Dict]] = None
    ) -> None:
        """Log a DICOM upload operation (external DICOM files sent to destination)"""
        details = {
            "destination": {
                "name": destination_name,
                "host": host,
                "port": port,
                "ae_title": ae_title,
                "calling_ae": calling_ae
            },
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "file_details": file_details or []
        }
        self.log(DicomOperationType.DICOM_UPLOAD, success, message, details)

    def get_logs(
        self,
        operation_type: Optional[DicomOperationType] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict], int]:
        """
        Get log entries with optional filtering

        Returns:
            tuple: (logs, total_count)
        """
        logs = self._load_logs()

        # Filter by operation type
        if operation_type:
            logs = [l for l in logs if l.get("operation") == operation_type.value]

        # Filter by success status
        if success is not None:
            logs = [l for l in logs if l.get("success") == success]

        total_count = len(logs)

        # Apply pagination
        logs = logs[offset:offset + limit]

        return logs, total_count

    def clear_logs(self) -> None:
        """Clear all logs"""
        self._save_logs([])


# Singleton instance
dicom_logger = DicomLogger()
