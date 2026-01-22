import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Union
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid, ImplicitVRLittleEndian
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path
import magic

from app.models import DicomMetadata
from app.config import settings

class DicomConverter:
    """Convert documents and images to DICOM format"""

    def __init__(self):
        self.temp_dir = Path("./temp")
        self.temp_dir.mkdir(exist_ok=True)

    def convert_to_dicom(
        self,
        file_path: Path,
        metadata: DicomMetadata
    ) -> tuple[Path, str, str, str]:
        """
        Convert a file to DICOM format

        Returns:
            tuple: (dicom_file_path, study_uid, series_uid, sop_uid)
        """
        # Detect file type
        mime_type = magic.from_file(str(file_path), mime=True)

        # Convert to PIL Image
        if 'pdf' in mime_type:
            images = self._convert_pdf_to_images(file_path)
        elif 'image' in mime_type:
            images = [Image.open(file_path)]
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")

        # Generate UIDs
        study_uid = generate_uid()
        series_uid = generate_uid()

        # Convert first image/page (can be extended to handle multi-page)
        if images:
            dicom_path, sop_uid = self._create_dicom_from_image(
                images[0],
                metadata,
                study_uid,
                series_uid
            )
            return dicom_path, study_uid, series_uid, sop_uid
        else:
            raise ValueError("No images could be extracted from file")

    def _convert_pdf_to_images(self, pdf_path: Path) -> list[Image.Image]:
        """Convert PDF pages to images"""
        try:
            images = convert_from_path(str(pdf_path), dpi=200)
            return images
        except Exception as e:
            raise ValueError(f"Failed to convert PDF: {str(e)}")

    def _create_dicom_from_image(
        self,
        image: Image.Image,
        metadata: DicomMetadata,
        study_uid: str,
        series_uid: str
    ) -> tuple[Path, str]:
        """Create a DICOM file from PIL Image"""

        # Convert image to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (max 2048x2048)
        max_size = 2048
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Create DICOM dataset
        file_meta = Dataset()
        file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        sop_uid = generate_uid()
        file_meta.MediaStorageSOPInstanceUID = sop_uid
        file_meta.ImplementationClassUID = generate_uid()

        ds = FileDataset(
            None,
            {},
            file_meta=file_meta,
            preamble=b"\0" * 128
        )

        # Patient Information
        ds.PatientName = metadata.patient_name
        ds.PatientID = metadata.patient_id
        if metadata.patient_birth_date:
            ds.PatientBirthDate = metadata.patient_birth_date.strftime('%Y%m%d')
        if metadata.patient_sex:
            ds.PatientSex = metadata.patient_sex

        # Study Information
        ds.StudyInstanceUID = study_uid
        ds.StudyDescription = metadata.study_description
        if metadata.study_date:
            ds.StudyDate = metadata.study_date.strftime('%Y%m%d')
        else:
            ds.StudyDate = datetime.now().strftime('%Y%m%d')
        if metadata.study_time:
            ds.StudyTime = metadata.study_time.strftime('%H%M%S')
        else:
            ds.StudyTime = datetime.now().strftime('%H%M%S')
        if metadata.accession_number:
            ds.AccessionNumber = metadata.accession_number
        if metadata.referring_physician:
            ds.ReferringPhysicianName = metadata.referring_physician

        # Series Information
        ds.SeriesInstanceUID = series_uid
        ds.SeriesDescription = metadata.series_description
        ds.SeriesNumber = 1
        ds.Modality = metadata.modality

        # Instance Information
        ds.SOPInstanceUID = sop_uid
        ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
        ds.InstanceNumber = 1

        # Image Information
        ds.SamplesPerPixel = 3
        ds.PhotometricInterpretation = "RGB"
        ds.Rows = image.height
        ds.Columns = image.width
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0

        # Convert image to bytes
        ds.PixelData = image.tobytes()

        # Save DICOM file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"D2D_{metadata.patient_id}_{timestamp}.dcm"
        dicom_path = settings.archive_path / filename

        ds.save_as(str(dicom_path), write_like_original=False)

        return dicom_path, sop_uid
