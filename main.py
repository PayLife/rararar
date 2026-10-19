import sys
import os
from PySide6.QtWidgets import QApplication
from main_window import DICOMStudyBrowserWindow
from styles import CYBER_MEDICAL_QSS
from sample_data_generator import generate_sample_dicom_dataset

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(CYBER_MEDICAL_QSS)

    db_path = "dicom_studies.db"
    demo_dir = "sample_dicom_data"

    # Automatically generate demo DICOM files if first run
    if not os.path.exists(demo_dir):
        print("First launch detected. Generating synthetic multi-modality DICOM study dataset...")
        generate_sample_dicom_dataset(demo_dir)

    window = DICOMStudyBrowserWindow(db_path=db_path)
    window.show()

    # Automatically scan demo directory if database has no studies yet
    if len(window.db.query_studies()) == 0 and os.path.exists(demo_dir):
        window._start_scan(demo_dir)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
