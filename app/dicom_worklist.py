from pynetdicom import AE, evt
from pynetdicom.sop_class import ModalityWorklistInformationFind
from pydicom.dataset import Dataset
from typing import List, Optional, Dict
from datetime import datetime, date
import asyncio
from concurrent.futures import ThreadPoolExecutor


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
                return False, [], f"Failed to establish association with {self.ae_title}"

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
        worklist = WorklistQuery(
            host=host,
            port=port,
            ae_title=worklist_ae_title,
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
        return (worklist_ae_title, success, items, message)
    except Exception as e:
        return (worklist_ae_title, False, [], f"Error: {str(e)}")


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

    loop = asyncio.get_event_loop()

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

    return overall_success, unique_items, {"_summary": message, **status_dict}
