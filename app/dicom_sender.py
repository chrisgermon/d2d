from pathlib import Path
from pynetdicom import AE, evt
from pynetdicom.sop_class import SecondaryCaptureImageStorage
import pydicom

from app.models import DicomDestination

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
        try:
            # Read DICOM file
            ds = pydicom.dcmread(str(dicom_file_path))

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
                    return True, f"DICOM file sent successfully to {destination.name}"
                else:
                    return False, "C-STORE request failed"
            else:
                return False, f"Association rejected by {destination.name}"

        except Exception as e:
            return False, f"Failed to send DICOM: {str(e)}"

    def verify_destination(self, destination: DicomDestination) -> tuple[bool, str]:
        """
        Verify connection to DICOM destination using C-ECHO

        Returns:
            tuple: (success, message)
        """
        try:
            from pynetdicom.sop_class import VerificationSOPClass

            ae = AE()
            ae.add_requested_context(VerificationSOPClass)
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
                    return True, f"Successfully connected to {destination.name}"
                else:
                    return False, "C-ECHO failed"
            else:
                return False, f"Association rejected by {destination.name}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"
