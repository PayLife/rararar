import os
import pydicom
from PySide6.QtCore import QThread, Signal, QObject
from database import DICOMDatabase

class DICOMScannerWorker(QObject):
    # Signals for UI updates
    progress_updated = Signal(int, int, str)  # current, total, status text
    study_scanned = Signal(dict)              # study info
    scan_finished = Signal(int)               # total scanned count
    scan_error = Signal(str)

    def __init__(self, root_dir: str, db_path: str = "dicom_studies.db"):
        super().__init__()
        self.root_dir = root_dir
        self.db_path = db_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        db = DICOMDatabase(self.db_path)
        dicom_files = []

        # Step 1: Collect all files in directory tree
        for root, _, files in os.walk(self.root_dir):
            if self._is_cancelled:
                return
            for f in files:
                # DICOM files usually end with .dcm or have no extension
                if f.lower().endswith(('.dcm', '.dicom')) or '.' not in f:
                    dicom_files.append(os.path.join(root, f))

        total_files = len(dicom_files)
        if total_files == 0:
            self.progress_updated.emit(0, 0, "No DICOM files found.")
            self.scan_finished.emit(0)
            return

        scanned_count = 0
        seen_studies = set()

        # Step 2: Read headers with stop_before_pixels=True for high performance
        for idx, file_path in enumerate(dicom_files, start=1):
            if self._is_cancelled:
                return

            self.progress_updated.emit(idx, total_files, f"Scanning {os.path.basename(file_path)}")

            try:
                # Fast header reading without loading heavy pixel arrays into RAM
                ds = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)

                # Check if valid DICOM dataset with SOPInstanceUID & StudyInstanceUID
                if not hasattr(ds, 'StudyInstanceUID') or not hasattr(ds, 'SOPInstanceUID'):
                    continue

                study_uid = str(ds.StudyInstanceUID)
                series_uid = str(getattr(ds, 'SeriesInstanceUID', study_uid + ".1"))
                sop_uid = str(ds.SOPInstanceUID)

                # Insert/Update Study
                study_data = {
                    "study_instance_uid": study_uid,
                    "patient_id": str(getattr(ds, 'PatientID', 'UNKNOWN')),
                    "patient_name": str(getattr(ds, 'PatientName', 'ANONYMOUS')),
                    "patient_sex": str(getattr(ds, 'PatientSex', 'U')),
                    "patient_birth_date": str(getattr(ds, 'PatientBirthDate', '')),
                    "study_date": str(getattr(ds, 'StudyDate', '')),
                    "study_time": str(getattr(ds, 'StudyTime', '')),
                    "study_description": str(getattr(ds, 'StudyDescription', 'Unspecified Study')),
                    "modalities": str(getattr(ds, 'Modality', 'OT')),
                    "accession_number": str(getattr(ds, 'AccessionNumber', ''))
                }
                db.upsert_study(study_data)

                # Insert/Update Series
                series_data = {
                    "series_instance_uid": series_uid,
                    "study_instance_uid": study_uid,
                    "series_number": int(getattr(ds, 'SeriesNumber', 1)),
                    "series_description": str(getattr(ds, 'SeriesDescription', 'Series')),
                    "modality": str(getattr(ds, 'Modality', 'OT')),
                    "body_part_examined": str(getattr(ds, 'BodyPartExamined', ''))
                }
                db.upsert_series(series_data)

                # Insert Instance
                instance_data = {
                    "sop_instance_uid": sop_uid,
                    "series_instance_uid": series_uid,
                    "study_instance_uid": study_uid,
                    "instance_number": int(getattr(ds, 'InstanceNumber', 1)),
                    "file_path": file_path,
                    "slice_location": float(getattr(ds, 'SliceLocation', 0.0)),
                    "rows": int(getattr(ds, 'Rows', 512)),
                    "columns": int(getattr(ds, 'Columns', 512))
                }
                db.upsert_instance(instance_data)

                scanned_count += 1
                if study_uid not in seen_studies:
                    seen_studies.add(study_uid)
                    self.study_scanned.emit(study_data)

            except Exception as e:
                # Non-DICOM or corrupted file, skip
                continue

        # Step 3: Recalculate series and instance counts per study
        db.update_counts()
        self.progress_updated.emit(total_files, total_files, f"Scan complete. Indexed {scanned_count} instances.")
        self.scan_finished.emit(scanned_count)


class DICOMScannerController(QObject):
    """Controller to manage background QThread scanner execution."""
    progress = Signal(int, int, str)
    study_found = Signal(dict)
    finished = Signal(int)

    def __init__(self, db_path: str = "dicom_studies.db"):
        super().__init__()
        self.db_path = db_path
        self.thread = None
        self.worker = None

    def start_scan(self, directory: str):
        if self.thread and self.thread.isRunning():
            self.stop_scan()

        self.thread = QThread()
        self.worker = DICOMScannerWorker(directory, self.db_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.progress.emit)
        self.worker.study_scanned.connect(self.study_found.emit)
        self.worker.scan_finished.connect(self._on_finished)

        self.thread.start()

    def _on_finished(self, count: int):
        self.finished.emit(count)
        if self.thread:
            self.thread.quit()
            self.thread.wait()

    def stop_scan(self):
        if self.worker:
            self.worker.cancel()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
