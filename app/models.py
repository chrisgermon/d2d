from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time

class DicomMetadata(BaseModel):
    """DICOM metadata for converted files"""
    patient_name: str = Field(..., description="Patient's full name")
    patient_id: str = Field(..., description="Patient ID or MRN")
    patient_birth_date: Optional[date] = Field(None, description="Patient birth date")
    patient_sex: Optional[str] = Field(None, description="Patient sex (M/F/O)")
    study_description: str = Field(default="Document Conversion", description="Study description")
    series_description: str = Field(default="Imported Document", description="Series description")
    modality: str = Field(default="OT", description="DICOM modality code")
    study_date: Optional[date] = Field(None, description="Study date")
    study_time: Optional[time] = Field(None, description="Study time")
    accession_number: Optional[str] = Field(None, description="Accession number")
    referring_physician: Optional[str] = Field(None, description="Referring physician name")

class DicomDestination(BaseModel):
    """DICOM destination configuration"""
    name: str = Field(..., description="Friendly name for this destination")
    ae_title: str = Field(..., description="Application Entity Title")
    host: str = Field(..., description="IP address or hostname")
    port: int = Field(..., description="DICOM port (typically 104 or 11112)")
    calling_ae_title: str = Field(default="D2D_SCU", description="Calling AE Title")

class ConversionRequest(BaseModel):
    """Request to convert and send a document"""
    file_id: str = Field(..., description="Uploaded file identifier")
    metadata: DicomMetadata
    destination: Optional[DicomDestination] = None
    send_immediately: bool = Field(default=False, description="Send to destination after conversion")

class ConversionResponse(BaseModel):
    """Response from conversion operation"""
    success: bool
    dicom_file_path: Optional[str] = None
    message: str
    sop_instance_uid: Optional[str] = None
    study_instance_uid: Optional[str] = None
    series_instance_uid: Optional[str] = None

class WorklistConfig(BaseModel):
    """Worklist server configuration"""
    host: str = Field(default="10.17.1.21", description="Worklist server IP")
    port: int = Field(default=5010, description="Worklist server port")
    ae_title: str = Field(default="LIVUSWL", description="Worklist server AE Title")
    calling_ae: str = Field(default="D2DSERVER", description="Our AE Title for worklist queries")

class WorklistQueryRequest(BaseModel):
    """Request to query modality worklist"""
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    accession_number: Optional[str] = None
    scheduled_date: Optional[date] = None
    modality: Optional[str] = None
    station_ae_title: Optional[str] = None
    config: Optional[WorklistConfig] = WorklistConfig()


class WorklistQueryAllRequest(BaseModel):
    """Request to query all modality worklists"""
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    accession_number: Optional[str] = None
    scheduled_date: Optional[date] = None
    modality: Optional[str] = None
    host: str = "10.17.1.21"
    port: int = 5010
    ae_title: str = "LIVUSWL"
    calling_ae: str = "D2DSERVER"


# Query/Retrieve Models
class QRSourceConfig(BaseModel):
    """PACS source configuration for Query/Retrieve"""
    name: str = Field(default="Default PACS", description="Friendly name for this PACS source")
    host: str = Field(..., description="PACS server IP address")
    port: int = Field(..., description="PACS server port")
    ae_title: str = Field(..., description="PACS server AE Title")
    calling_ae: str = Field(default="D2D_QR", description="Our AE Title for Q/R operations")


class QRStorageConfig(BaseModel):
    """Local Storage SCP configuration"""
    ae_title: str = Field(default="D2D_STORE", description="Storage SCP AE Title")
    port: int = Field(default=11113, description="Storage SCP port")


class QRQueryRequest(BaseModel):
    """Request to query studies by accession numbers"""
    accession_numbers: list[str] = Field(..., description="List of accession numbers to search")
    source: QRSourceConfig


class QRRetrieveRequest(BaseModel):
    """Request to retrieve studies"""
    study_uids: list[str] = Field(..., description="List of Study Instance UIDs to retrieve")
    source: QRSourceConfig
    storage: QRStorageConfig = QRStorageConfig()


class QRTestRequest(BaseModel):
    """Request to test connection to PACS"""
    source: QRSourceConfig


# Batch Q/R Models
class BatchItemStatus(BaseModel):
    """Status of a single accession number in a batch job"""
    accession_number: str
    status: str = "pending"  # pending, querying, query_complete, query_failed, retrieving, completed, failed, cancelled
    study_uid: Optional[str] = None
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    study_date: Optional[str] = None
    modality: Optional[str] = None
    num_instances: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BatchJobStatus(BaseModel):
    """Status of a batch retrieval job"""
    job_id: str
    status: str = "pending"  # pending, running, completed, cancelled, failed
    total_items: int = 0
    queried_items: int = 0
    retrieved_items: int = 0
    failed_items: int = 0
    progress_percent: float = 0.0
    items: list[BatchItemStatus] = []
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class BatchRetrieveRequest(BaseModel):
    """Request to start a batch retrieval job"""
    accession_numbers: list[str] = Field(..., description="List of accession numbers to retrieve")
    source: QRSourceConfig
    storage: QRStorageConfig = QRStorageConfig()
    auto_retrieve: bool = Field(default=True, description="Automatically retrieve after query")


# DICOM Upload Models
class DicomUploadResult(BaseModel):
    """Result for a single DICOM file upload"""
    filename: str
    success: bool
    message: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    study_uid: Optional[str] = None
    series_uid: Optional[str] = None
    sop_uid: Optional[str] = None
    accession_number: Optional[str] = None
    modality: Optional[str] = None


class DicomUploadResponse(BaseModel):
    """Response from DICOM upload operation"""
    success: bool
    total_files: int
    successful: int
    failed: int
    message: str
    results: list[DicomUploadResult] = []
