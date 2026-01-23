from pynetdicom import AE, evt
from pynetdicom.sop_class import ModalityWorklistInformationFind
from pydicom.dataset import Dataset
from typing import List, Optional, Dict
from datetime import datetime, date


class WorklistQuery:
    """Handle DICOM Modality Worklist (MWL) queries"""

    def __init__(self, host: str = "10.17.1.21", port: int = 5010,
                 ae_title: str = "AURVCMOD1", calling_ae: str = "LIVUSWL"):
        self.host = host
        self.port = port
        self.ae_title = ae_title
        self.calling_ae = calling_ae
        self.ae = AE(ae_title=calling_ae)
        self.ae.add_requested_context(ModalityWorklistInformationFind)

    def query_worklist(
        self,
        patient_name: Optional[str] = None,
        patient_id: Optional[str] = None,
        accession_number: Optional[str] = None,
        scheduled_date: Optional[date] = None,
        modality: Optional[str] = None
    ) -> tuple[bool, List[Dict], str]:
        """
        Query the modality worklist for scheduled studies

        Args:
            patient_name: Patient name (supports wildcards: * and ?)
            patient_id: Patient ID/MRN
            accession_number: Accession number
            scheduled_date: Scheduled procedure date (YYYYMMDD)
            modality: Modality code (e.g., 'US', 'CT', 'MR')

        Returns:
            tuple: (success, list of worklist items, message)
        """
        try:
            # Build query dataset
            query_ds = Dataset()

            # Patient Module (0010,xxxx)
            if patient_name:
                query_ds.PatientName = patient_name
            else:
                query_ds.PatientName = '*'  # Query all patients

            if patient_id:
                query_ds.PatientID = patient_id
            else:
                query_ds.PatientID = ''

            query_ds.PatientBirthDate = ''
            query_ds.PatientSex = ''
            query_ds.PatientWeight = ''

            # Requested Procedure Module (0032,xxxx and 0040,xxxx)
            if accession_number:
                query_ds.AccessionNumber = accession_number
            else:
                query_ds.AccessionNumber = ''

            query_ds.RequestedProcedureDescription = ''
            query_ds.RequestedProcedureID = ''

            # Scheduled Procedure Step Sequence (0040,0100)
            sps_item = Dataset()

            if scheduled_date:
                sps_item.ScheduledProcedureStepStartDate = scheduled_date.strftime('%Y%m%d')
            else:
                sps_item.ScheduledProcedureStepStartDate = ''

            sps_item.ScheduledProcedureStepStartTime = ''

            if modality:
                sps_item.Modality = modality
            else:
                sps_item.Modality = ''

            sps_item.ScheduledPerformingPhysicianName = ''
            sps_item.ScheduledProcedureStepDescription = ''
            sps_item.ScheduledStationAETitle = ''
            sps_item.ScheduledProcedureStepID = ''
            sps_item.ScheduledStationName = ''
            sps_item.ScheduledProcedureStepLocation = ''

            query_ds.ScheduledProcedureStepSequence = [sps_item]

            # Study Instance UID
            query_ds.StudyInstanceUID = ''

            # Perform C-FIND query
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if not assoc.is_established:
                return False, [], f"Failed to establish association with {self.ae_title}"

            # Send C-FIND request
            responses = assoc.send_c_find(query_ds, ModalityWorklistInformationFind)

            worklist_items = []
            for (status, identifier) in responses:
                if status and status.Status in [0xFF00, 0xFF01]:  # Pending
                    if identifier:
                        worklist_item = self._parse_worklist_item(identifier)
                        if worklist_item:
                            worklist_items.append(worklist_item)

            assoc.release()

            return True, worklist_items, f"Found {len(worklist_items)} worklist item(s)"

        except Exception as e:
            return False, [], f"Worklist query failed: {str(e)}"

    def _parse_worklist_item(self, dataset: Dataset) -> Optional[Dict]:
        """Parse DICOM worklist response into a dictionary"""
        try:
            item = {}

            # Patient Information
            item['patient_name'] = str(dataset.get('PatientName', ''))
            item['patient_id'] = str(dataset.get('PatientID', ''))
            item['patient_birth_date'] = self._parse_date(dataset.get('PatientBirthDate', ''))
            item['patient_sex'] = str(dataset.get('PatientSex', ''))

            # Study/Procedure Information
            item['accession_number'] = str(dataset.get('AccessionNumber', ''))
            item['requested_procedure_description'] = str(dataset.get('RequestedProcedureDescription', ''))
            item['requested_procedure_id'] = str(dataset.get('RequestedProcedureID', ''))
            item['study_instance_uid'] = str(dataset.get('StudyInstanceUID', ''))

            # Scheduled Procedure Step Information
            if 'ScheduledProcedureStepSequence' in dataset and len(dataset.ScheduledProcedureStepSequence) > 0:
                sps = dataset.ScheduledProcedureStepSequence[0]

                item['scheduled_date'] = self._parse_date(sps.get('ScheduledProcedureStepStartDate', ''))
                item['scheduled_time'] = self._parse_time(sps.get('ScheduledProcedureStepStartTime', ''))
                item['modality'] = str(sps.get('Modality', ''))
                item['scheduled_physician'] = str(sps.get('ScheduledPerformingPhysicianName', ''))
                item['procedure_description'] = str(sps.get('ScheduledProcedureStepDescription', ''))
                item['scheduled_station_ae'] = str(sps.get('ScheduledStationAETitle', ''))
                item['scheduled_station_name'] = str(sps.get('ScheduledStationName', ''))
                item['procedure_step_id'] = str(sps.get('ScheduledProcedureStepID', ''))

            return item

        except Exception as e:
            print(f"Error parsing worklist item: {e}")
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
        """Parse DICOM time (HHMMSS) to readable format"""
        if not time_str or len(time_str) < 6:
            return None
        try:
            return f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        except:
            return None

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to worklist server"""
        try:
            from pynetdicom.sop_class import Verification

            ae = AE(ae_title=self.calling_ae)
            ae.add_requested_context(Verification)

            assoc = ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if assoc.is_established:
                status = assoc.send_c_echo()
                assoc.release()

                if status:
                    return True, f"Successfully connected to worklist server {self.ae_title}"
                else:
                    return False, "C-ECHO failed"
            else:
                return False, f"Association rejected by {self.ae_title}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"
