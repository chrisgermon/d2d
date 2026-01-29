from pynetdicom import AE, evt
from pynetdicom.sop_class import ModalityWorklistInformationFind, StudyRootQueryRetrieveInformationModelFind, Verification
from pydicom.dataset import Dataset
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.dicom_logger import dicom_logger


# Complete list of all AE Titles for worklist queries
ALL_WORKLIST_AE_TITLES = [
    "AUBCRWL", "AUBCTWL", "AUBUSWL",
    "BOTCRWL", "BOTCTWL", "BOTUSWL",
    "BULBMDWL", "BULCRWL", "BULCTWL", "BULMGWL", "BULMRWL", "BULUSWL",
    "BUTCRWL", "BUTCTWL", "BUTUSWL",
    "CARCRWL", "CARCTWL", "CARMRWL", "CARUSWL",
    "COBBMDWL", "COBCRWL", "COBCTWL", "COBUSWL",
    "COEUSWL",
    "COLBMDWL", "COLCRWL", "COLCTWL", "COLUSWL",
    "COOBMDWL", "COOCRWL", "COOCTWL", "COOMRWL", "COOUSWL",
    "CRECRWL", "CRECTWL", "CREUSWL",
    "DAPBMDWL", "DAPCRWL", "DAPCTWL", "DAPMRWL", "DAPUSWL",
    "DIACRWL", "DIACTWL", "DIAUSWL",
    "EARBMDWL", "EARCRWL", "EARCTWL", "EARMGWL", "EAROPGWL", "EARUSWL",
    "ENEBMDWL", "ENECRWL", "ENECTWL", "ENEUSWL",
    "ENGCRWL", "ENGCTWL", "ENGDEWL", "ENGUSWL",
    "GRACRWL", "GRACTWL", "GRAUSWL",
    "GRECRWL", "GRECTWL", "GREMGWL", "GREUSWL",
    "GRNCRWL", "GRNCTWL", "GRNUSWL",
    "HAMBMDWL", "HAMCRWL", "HAMCTWL", "HAMMRWL", "HAMUSWL",
    "HAYBMDWL", "HAYCRWL", "HAYCTWL", "HAYMRWL", "HAYUSWL",
    "HPKCRWL", "HPKCTWL", "HPKUSWL",
    "KANBMDWL", "KANCRWL", "KANCTWL", "KANMRWL", "KANUSWL",
    "KLEBMDWL", "KLECRWL", "KLECTWL", "KLEMRWL", "KLEUSWL",
    "KYABMDWL", "KYACRWL", "KYACTWL", "KYAUSWL",
    "LAKCRWL", "LAKCTWL", "LAKDEWL", "LAKUSWL",
    "LILBMDWL", "LILCRWL", "LILCTWL", "LILMGWL", "LILMRWL", "LILUSWL",
    "LIVCRWL", "LIVCTWL", "LIVUSWL",
    "LOGCRWL", "LOGCTWL", "LOGMGWL", "LOGUSWL",
    "LYNBMDWL", "LYNCRWL", "LYNCTWL", "LYNUSWL",
    "MARBMDWL", "MARCRWL", "MARCTWL", "MARUSWL",
    "MENBMDWL", "MENCRWL", "MENCTWL", "MENMGWL", "MENMRWL", "MENUSWL",
    "MORBMDWL", "MORCRWL", "MORCTWL", "MORMRWL", "MORUSWL",
    "MOVCRWL", "MOVCTWL", "MOVMRWL", "MOVUSWL",
    "MULBMDWL", "MULCRWL", "MULCTWL", "MULMRWL", "MULUSWL",
    "NAEUSWL",
    "NAMBMDWL", "NAMCRWL", "NAMCTWL", "NAMUSWL",
    "NOEUSWL",
    "NOOBMDWL", "NOOCRWL", "NOOCTWL", "NOOUSWL",
    "NORCRWL", "NORCTWL", "NOREOSWL", "NORUSWL",
    "ONEUSWL",
    "RESCRWL", "RESCTWL", "RESMGWL", "RESMRWL", "RESUSWL",
    "RINBMDWL", "RINCRWL", "RINCTWL", "RINUSWL",
    "ROCCRWL", "ROCCTWL", "ROCUSWL",
    "SEBBMDWL", "SEBCRWL", "SEBCTWL", "SEBMRWL", "SEBUSWL",
    "SHEBMDWL", "SHECRWL", "SHECTWL", "SHEMRWL", "SHEUSWL",
    "TEEUSWL",
    "TEWBMDWL", "TEWCRWL", "TEWCTWL", "TEWUSWL",
    "THRBMDWL", "THRCRWL", "THRCTWL", "THRUSWL",
    "TORBMDWL", "TORCRWL", "TORCTWL", "TORMRWL", "TORUSWL",
    "UNLBMDWL", "UNLCRWL", "UNLCTWL", "UNLUSWL",
    "WARCRWL", "WARCTWL", "WARUSWL",
    "WERBMDWL", "WERCRWL", "WERCTWL", "WERMRWL", "WERUSWL",
    "WILBMDWL", "WILCRWL", "WILCTWL", "WILMRWL", "WILUSWL",
    "WOOCRWL", "WOOCTWL", "WOOUSWL",
    "WRRCRWL", "WRRCTWL", "WRRUSWL",
]


class WorklistQuery:
    """Handle DICOM Modality Worklist (MWL) queries"""

    def __init__(self, host: str = "10.17.1.21", port: int = 5010,
                 ae_title: str = "LIVUSWL", calling_ae: str = "D2DSERVER"):
        self.host = host
        self.port = port
        self.ae_title = ae_title
        self.calling_ae = calling_ae
        self.ae = AE(ae_title=calling_ae)
        self.ae.acse_timeout = 5  # Connection timeout in seconds
        self.ae.dimse_timeout = 10  # Operation timeout in seconds
        self.ae.network_timeout = 5  # Network timeout in seconds
        self.ae.add_requested_context(ModalityWorklistInformationFind)

    def query_worklist(
        self,
        patient_name: Optional[str] = None,
        patient_id: Optional[str] = None,
        accession_number: Optional[str] = None,
        scheduled_date: Optional[date] = None,
        modality: Optional[str] = None,
        station_ae_title: Optional[str] = None
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
            cleaned_patient_name = (patient_name or "").strip()
            if cleaned_patient_name and cleaned_patient_name != "*":
                query_ds.PatientName = cleaned_patient_name
            else:
                # Use empty value for "match all" to avoid servers
                # that treat "*" as a literal character.
                query_ds.PatientName = ''

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
            station_ae = (station_ae_title or "").strip()
            if station_ae:
                # Only filter when explicitly requested.
                sps_item.ScheduledStationAETitle = station_ae
            else:
                # Empty value requests return without filtering.
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
                message = f"Failed to establish association with {self.ae_title}"
                dicom_logger.log_worklist_query(
                    success=False,
                    message=message,
                    host=self.host,
                    port=self.port,
                    ae_title=self.ae_title,
                    calling_ae=self.calling_ae,
                    patient_name=patient_name,
                    patient_id=patient_id,
                    accession_number=accession_number,
                    modality=modality,
                    results_count=0
                )
                return False, [], message

            # Send C-FIND request
            responses = assoc.send_c_find(query_ds, ModalityWorklistInformationFind)

            worklist_items = []
            for (status, identifier) in responses:
                if status and status.Status in [0xFF00, 0xFF01]:  # Pending
                    if identifier:
                        worklist_item = self._parse_worklist_item(identifier)
                        if worklist_item:
                            worklist_item['station_ae_title'] = station_ae
                            worklist_items.append(worklist_item)

            assoc.release()

            message = f"Found {len(worklist_items)} worklist item(s)"
            dicom_logger.log_worklist_query(
                success=True,
                message=message,
                host=self.host,
                port=self.port,
                ae_title=self.ae_title,
                calling_ae=self.calling_ae,
                patient_name=patient_name,
                patient_id=patient_id,
                accession_number=accession_number,
                modality=modality,
                results_count=len(worklist_items)
            )
            return True, worklist_items, message

        except Exception as e:
            message = f"Worklist query failed: {str(e)}"
            dicom_logger.log_worklist_query(
                success=False,
                message=message,
                host=self.host,
                port=self.port,
                ae_title=self.ae_title,
                calling_ae=self.calling_ae,
                patient_name=patient_name,
                patient_id=patient_id,
                accession_number=accession_number,
                modality=modality,
                results_count=0
            )
            return False, [], message

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

            # Include AE titles used for this query
            item['calling_ae'] = self.calling_ae
            item['server_ae_title'] = self.ae_title
            item['worklist_ae_title'] = self.ae_title

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


def query_single_ae(
    calling_ae: str,
    host: str,
    port: int,
    worklist_ae_title: str,
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    accession_number: Optional[str] = None,
    scheduled_date: Optional[date] = None,
    modality: Optional[str] = None,
    station_ae_title: Optional[str] = None
) -> tuple[str, bool, List[Dict], str]:
    """
    Query a single worklist AE Title and return results.
    Returns: (worklist_ae_title, success, items, message)
    """
    try:
        ae_title = worklist_ae_title
        worklist = WorklistQuery(
            host=host,
            port=port,
            ae_title=ae_title,
            calling_ae=calling_ae
        )
        success, items, message = worklist.query_worklist(
            patient_name=patient_name,
            patient_id=patient_id,
            accession_number=accession_number,
            scheduled_date=scheduled_date,
            modality=modality,
            station_ae_title=station_ae_title
        )
        return (ae_title, success, items, message)
    except Exception as e:
        return (ae_title, False, [], f"Error: {str(e)}")


async def query_all_worklists(
    host: str = "10.17.1.21",
    port: int = 5010,
    calling_ae: str = "D2DSERVER",
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    accession_number: Optional[str] = None,
    scheduled_date: Optional[date] = None,
    modality: Optional[str] = None,
    ae_titles: Optional[List[str]] = None,
    max_workers: int = 20
) -> tuple[bool, List[Dict], Dict[str, str]]:
    """
    Query all worklist AE Titles concurrently and return combined results.

    Args:
        host: Worklist server IP
        port: Worklist server port
        calling_ae: Calling AE Title for the association
        patient_name: Patient name filter
        patient_id: Patient ID filter
        accession_number: Accession number filter
        scheduled_date: Scheduled date filter
        modality: Modality filter
        ae_titles: List of worklist AE Titles to query (defaults to ALL_WORKLIST_AE_TITLES)
        max_workers: Maximum concurrent queries

    Returns:
        tuple: (success, combined_items, status_dict)
        - success: True if at least one query succeeded
        - combined_items: All worklist items from all successful queries
        - status_dict: Dict mapping AE Title to status message
    """
    if ae_titles is None:
        ae_titles = ALL_WORKLIST_AE_TITLES

    all_items = []
    status_dict = {}
    successful_count = 0

    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create futures for all worklist AE Title queries
        futures = [
            loop.run_in_executor(
                executor,
                query_single_ae,
                calling_ae,
                host,
                port,
                worklist_ae_title,
                patient_name,
                patient_id,
                accession_number,
                scheduled_date,
                modality,
                None
            )
            for worklist_ae_title in ae_titles
        ]

        # Wait for all queries to complete
        results = await asyncio.gather(*futures, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                continue

            worklist_ae_title, success, items, message = result
            status_dict[worklist_ae_title] = message

            if success:
                successful_count += 1
                all_items.extend(items)

    # Remove duplicates based on accession number (if present) or patient_id + scheduled_date
    seen = set()
    unique_items = []
    for item in all_items:
        # Create a unique key for deduplication
        key = (
            item.get('accession_number', ''),
            item.get('patient_id', ''),
            item.get('scheduled_date', ''),
            item.get('modality', '')
        )
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    overall_success = successful_count > 0
    message = f"Queried {len(ae_titles)} AE Titles, {successful_count} successful, found {len(unique_items)} unique items"

    # Log the query-all operation
    dicom_logger.log_worklist_query_all(
        success=overall_success,
        message=message,
        host=host,
        port=port,
        ae_title=calling_ae,
        ae_titles_queried=len(ae_titles),
        successful_queries=successful_count,
        results_count=len(unique_items)
    )

    return overall_success, unique_items, {"_summary": message, **status_dict}


class CompletedStudyQuery:
    """
    Query PACS for completed studies using DICOM C-FIND at STUDY level.
    Used to search for studies that have already been performed (not scheduled).
    """

    def __init__(self, host: str = "10.17.1.21", port: int = 104,
                 ae_title: str = "AURVCMOD1", calling_ae: str = "D2DSERVER"):
        self.host = host
        self.port = port
        self.ae_title = ae_title
        self.calling_ae = calling_ae
        self.ae = AE(ae_title=calling_ae)
        self.ae.acse_timeout = 10
        self.ae.dimse_timeout = 30
        self.ae.network_timeout = 10
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(Verification)

    def query_completed_studies(
        self,
        patient_name: Optional[str] = None,
        patient_id: Optional[str] = None,
        accession_number: Optional[str] = None,
        study_date_from: Optional[date] = None,
        study_date_to: Optional[date] = None,
        modality: Optional[str] = None
    ) -> tuple[bool, List[Dict], str]:
        """
        Query PACS for completed studies within a date range.

        Args:
            patient_name: Patient name (supports wildcards: * and ?)
            patient_id: Patient ID/MRN
            accession_number: Accession number
            study_date_from: Start date for study search (inclusive)
            study_date_to: End date for study search (inclusive)
            modality: Modality code filter

        Returns:
            tuple: (success, list of study items, message)
        """
        try:
            # Build query dataset
            query_ds = Dataset()
            query_ds.QueryRetrieveLevel = "STUDY"

            # Patient Information
            cleaned_patient_name = (patient_name or "").strip()
            if cleaned_patient_name and cleaned_patient_name != "*":
                query_ds.PatientName = cleaned_patient_name
            else:
                query_ds.PatientName = ''

            if patient_id:
                query_ds.PatientID = patient_id
            else:
                query_ds.PatientID = ''

            query_ds.PatientBirthDate = ''
            query_ds.PatientSex = ''

            # Study Information
            if accession_number:
                query_ds.AccessionNumber = accession_number
            else:
                query_ds.AccessionNumber = ''

            # Build date range query
            if study_date_from and study_date_to:
                date_range = f"{study_date_from.strftime('%Y%m%d')}-{study_date_to.strftime('%Y%m%d')}"
                query_ds.StudyDate = date_range
            elif study_date_from:
                query_ds.StudyDate = f"{study_date_from.strftime('%Y%m%d')}-"
            elif study_date_to:
                query_ds.StudyDate = f"-{study_date_to.strftime('%Y%m%d')}"
            else:
                # Default to today and yesterday only
                today = date.today()
                yesterday = today - timedelta(days=1)
                date_range = f"{yesterday.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"
                query_ds.StudyDate = date_range

            query_ds.StudyTime = ''
            query_ds.StudyDescription = ''
            query_ds.StudyInstanceUID = ''
            query_ds.ReferringPhysicianName = ''

            # Modality filter
            if modality:
                query_ds.ModalitiesInStudy = modality
            else:
                query_ds.ModalitiesInStudy = ''

            # Additional return keys
            query_ds.NumberOfStudyRelatedSeries = ''
            query_ds.NumberOfStudyRelatedInstances = ''

            # Perform C-FIND query
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if not assoc.is_established:
                message = f"Failed to establish association with {self.ae_title}"
                return False, [], message

            # Send C-FIND request
            responses = assoc.send_c_find(query_ds, StudyRootQueryRetrieveInformationModelFind)

            study_items = []
            for (status, identifier) in responses:
                if status and status.Status in [0xFF00, 0xFF01]:  # Pending
                    if identifier:
                        study_item = self._parse_study_item(identifier)
                        if study_item:
                            study_items.append(study_item)

            assoc.release()

            message = f"Found {len(study_items)} completed study(ies)"
            return True, study_items, message

        except Exception as e:
            message = f"Completed study query failed: {str(e)}"
            return False, [], message

    def _parse_study_item(self, dataset: Dataset) -> Optional[Dict]:
        """Parse DICOM C-FIND response into a dictionary compatible with worklist format"""
        try:
            item = {}

            # Patient Information (same format as worklist)
            item['patient_name'] = str(dataset.get('PatientName', ''))
            item['patient_id'] = str(dataset.get('PatientID', ''))
            item['patient_birth_date'] = self._parse_date(dataset.get('PatientBirthDate', ''))
            item['patient_sex'] = str(dataset.get('PatientSex', ''))

            # Study/Procedure Information
            item['accession_number'] = str(dataset.get('AccessionNumber', ''))
            item['study_description'] = str(dataset.get('StudyDescription', ''))
            item['procedure_description'] = str(dataset.get('StudyDescription', ''))  # Alias for compatibility
            item['study_instance_uid'] = str(dataset.get('StudyInstanceUID', ''))

            # Study date/time (map to scheduled_date/time for UI compatibility)
            item['study_date'] = self._parse_date(dataset.get('StudyDate', ''))
            item['study_time'] = self._parse_time(dataset.get('StudyTime', ''))
            item['scheduled_date'] = item['study_date']  # For UI compatibility
            item['scheduled_time'] = item['study_time']  # For UI compatibility

            # Modality
            modalities = str(dataset.get('ModalitiesInStudy', ''))
            item['modality'] = modalities.split('\\')[0] if modalities else ''  # Take first modality if multiple
            item['modalities_in_study'] = modalities

            # Referring physician
            item['referring_physician'] = str(dataset.get('ReferringPhysicianName', ''))
            item['scheduled_physician'] = item['referring_physician']  # For UI compatibility

            # Study counts
            item['num_series'] = str(dataset.get('NumberOfStudyRelatedSeries', ''))
            item['num_instances'] = str(dataset.get('NumberOfStudyRelatedInstances', ''))

            # Mark as completed study (not from worklist)
            item['source'] = 'completed_study'
            item['server_ae_title'] = self.ae_title
            item['calling_ae'] = self.calling_ae

            return item

        except Exception as e:
            print(f"Error parsing study item: {e}")
            return None

    def _parse_date(self, date_str) -> Optional[str]:
        """Parse DICOM date (YYYYMMDD) to readable format"""
        if not date_str:
            return None
        date_str = str(date_str)
        if len(date_str) < 8:
            return None
        try:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return None

    def _parse_time(self, time_str) -> Optional[str]:
        """Parse DICOM time (HHMMSS) to readable format"""
        if not time_str:
            return None
        time_str = str(time_str)
        if len(time_str) < 6:
            return None
        try:
            return f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        except:
            return None

    def test_connection(self) -> tuple[bool, str]:
        """Test connection to PACS server"""
        try:
            assoc = self.ae.associate(
                self.host,
                self.port,
                ae_title=self.ae_title
            )

            if assoc.is_established:
                status = assoc.send_c_echo()
                assoc.release()

                if status:
                    return True, f"Successfully connected to PACS {self.ae_title}"
                else:
                    return False, "C-ECHO failed"
            else:
                return False, f"Association rejected by {self.ae_title}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"


# Default PACS configuration for completed study queries
DEFAULT_PACS_CONFIG = {
    "host": "10.17.1.21",
    "port": 104,
    "ae_title": "AURVCMOD1",
    "calling_ae": "D2DSERVER"
}
