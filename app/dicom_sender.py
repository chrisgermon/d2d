from pathlib import Path
from pynetdicom import AE, evt
from pynetdicom.sop_class import SecondaryCaptureImageStorage
import pydicom

from app.models import DicomDestination
from app.dicom_logger import dicom_logger

class DicomSender:
    """Handle DICOM C-STORE operations"""

    def __init__(self):
        self.ae = AE()
        self.ae.add_requested_context(SecondaryCaptureImageStorage)

    def send_dicom(
        self,
        dicom_file_path: Path,
        destination: DicomDestination
    ) -> tuple[bool, str]:
        """
        Send DICOM file to destination

        Returns:
            tuple: (success, message)
        """
        # Extract DICOM metadata for logging
        patient_id = None
        patient_name = None
        study_uid = None
        accession_number = None

        try:
            # Read DICOM file
            ds = pydicom.dcmread(str(dicom_file_path))

            # Extract metadata for logging
            patient_id = str(ds.get("PatientID", ""))
            patient_name = str(ds.get("PatientName", ""))
            study_uid = str(ds.get("StudyInstanceUID", ""))
            accession_number = str(ds.get("AccessionNumber", ""))

            # Set calling AE title
            self.ae.ae_title = destination.calling_ae_title

            # Associate with peer
            assoc = self.ae.associate(
                destination.host,
                destination.port,
                ae_title=destination.ae_title
            )

            if assoc.is_established:
                # Send C-STORE
                status = assoc.send_c_store(ds)

                # Release association
                assoc.release()

                if status:
                    message = f"DICOM file sent successfully to {destination.name}"
                    dicom_logger.log_dicom_send(
                        success=True,
                        message=message,
                        destination_name=destination.name,
                        host=destination.host,
                        port=destination.port,
                        ae_title=destination.ae_title,
                        calling_ae=destination.calling_ae_title,
                        file_path=str(dicom_file_path),
                        patient_id=patient_id,
                        patient_name=patient_name,
                        study_uid=study_uid,
                        accession_number=accession_number
                    )
                    return True, message
                else:
                    message = "C-STORE request failed"
                    dicom_logger.log_dicom_send(
                        success=False,
                        message=message,
                        destination_name=destination.name,
                        host=destination.host,
                        port=destination.port,
                        ae_title=destination.ae_title,
                        calling_ae=destination.calling_ae_title,
                        file_path=str(dicom_file_path),
                        patient_id=patient_id,
                        patient_name=patient_name,
                        study_uid=study_uid,
                        accession_number=accession_number
                    )
                    return False, message
            else:
                message = f"Association rejected by {destination.name}"
                dicom_logger.log_dicom_send(
                    success=False,
                    message=message,
                    destination_name=destination.name,
                    host=destination.host,
                    port=destination.port,
                    ae_title=destination.ae_title,
                    calling_ae=destination.calling_ae_title,
                    file_path=str(dicom_file_path),
                    patient_id=patient_id,
                    patient_name=patient_name,
                    study_uid=study_uid,
                    accession_number=accession_number
                )
                return False, message

        except Exception as e:
            message = f"Failed to send DICOM: {str(e)}"
            dicom_logger.log_dicom_send(
                success=False,
                message=message,
                destination_name=destination.name,
                host=destination.host,
                port=destination.port,
                ae_title=destination.ae_title,
                calling_ae=destination.calling_ae_title,
                file_path=str(dicom_file_path),
                patient_id=patient_id,
                patient_name=patient_name,
                study_uid=study_uid,
                accession_number=accession_number
            )
            return False, message

    def verify_destination(self, destination: DicomDestination) -> tuple[bool, str]:
        """
        Verify connection to DICOM destination using C-ECHO

        Returns:
            tuple: (success, message)
        """
        try:
            from pynetdicom.sop_class import Verification

            ae = AE()
            ae.add_requested_context(Verification)
            ae.ae_title = destination.calling_ae_title

            assoc = ae.associate(
                destination.host,
                destination.port,
                ae_title=destination.ae_title
            )

            if assoc.is_established:
                status = assoc.send_c_echo()
                assoc.release()

                if status:
                    message = f"Successfully connected to {destination.name}"
                    dicom_logger.log_dicom_verify(
                        success=True,
                        message=message,
                        destination_name=destination.name,
                        host=destination.host,
                        port=destination.port,
                        ae_title=destination.ae_title,
                        calling_ae=destination.calling_ae_title
                    )
                    return True, message
                else:
                    message = "C-ECHO failed"
                    dicom_logger.log_dicom_verify(
                        success=False,
                        message=message,
                        destination_name=destination.name,
                        host=destination.host,
                        port=destination.port,
                        ae_title=destination.ae_title,
                        calling_ae=destination.calling_ae_title
                    )
                    return False, message
            else:
                message = f"Association rejected by {destination.name}"
                dicom_logger.log_dicom_verify(
                    success=False,
                    message=message,
                    destination_name=destination.name,
                    host=destination.host,
                    port=destination.port,
                    ae_title=destination.ae_title,
                    calling_ae=destination.calling_ae_title
                )
                return False, message

        except Exception as e:
            message = f"Connection failed: {str(e)}"
            dicom_logger.log_dicom_verify(
                success=False,
                message=message,
                destination_name=destination.name,
                host=destination.host,
                port=destination.port,
                ae_title=destination.ae_title,
                calling_ae=destination.calling_ae_title
            )
            return False, message
