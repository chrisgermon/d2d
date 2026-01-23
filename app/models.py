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
    ae_title: str = Field(default="AURVCMOD1", description="Worklist server AE Title")
    calling_ae: str = Field(default="LIVUSWL", description="Our AE Title for worklist queries")

class WorklistQueryRequest(BaseModel):
    """Request to query modality worklist"""
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    accession_number: Optional[str] = None
    scheduled_date: Optional[date] = None
    modality: Optional[str] = None
    config: Optional[WorklistConfig] = WorklistConfig()
