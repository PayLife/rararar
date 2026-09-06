import os
import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QStatusBar, QLabel, QStackedLayout, QProgressBar, QMessageBox
)
from database import DICOMDatabase
from dicom_scanner import DICOMScannerController
from thumbnail_loader import ThumbnailManager
from search_bar import NaturalLanguageSearchBar
from study_grid import ResponsiveStudyGrid
from hud_filter import FloatingHudFilterPanel
from sample_data_generator import generate_sample_dicom_dataset
from styles import CYBER_MEDICAL_QSS

class DICOMStudyBrowserWindow(QMainWindow):
    """Main window integrating search, card grid, background scanning, and floating HUD filter overlay."""

    def __init__(self, db_path: str = "dicom_studies.db"):
        super().__init__()
        self.db_path = db_path
        self.db = DICOMDatabase(self.db_path)
        self.scanner_controller = DICOMScannerController(self.db_path)
        self.thumbnail_manager = ThumbnailManager(parent=self)

        self.current_sql_where = ""
        self.current_params = []
        self.hud_filter_state = {"modalities": [], "min_slices": 0}

        self.setWindowTitle("CyberDICOM — Next-Gen DICOM Study Browser")
        self.resize(1280, 800)

        self._init_ui()
        self._connect_signals()
        self._reload_studies()

    def _init_ui(self):
        # Main Central Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(16, 16, 16, 16)
        main_vbox.setSpacing(12)

        # 1. Top Search Bar
        self.search_bar = NaturalLanguageSearchBar()
        main_vbox.addWidget(self.search_bar)

        # 2. Main View Overlay Container (Stack Grid and Floating HUD Panel)
        self.view_container = QWidget()
        view_layout = QHBoxLayout(self.view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable Study Grid
        self.study_grid = ResponsiveStudyGrid(self.thumbnail_manager)
        view_layout.addWidget(self.study_grid, stretch=1)

        # Floating HUD Overlay Panel
        self.hud_panel = FloatingHudFilterPanel(self.view_container)
        self.hud_panel.hide() # Hidden by default, toggled via search bar button

        main_vbox.addWidget(self.view_container, stretch=1)

        # 3. Status Bar & Scan Progress Indicator
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94A3B8;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #111827;
                border: 1px solid #1E293B;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #00F0FF, #7B2CBF);
                border-radius: 5px;
            }
        """)
        self.progress_bar.hide()

        self.status_bar.addWidget(self.status_label, stretch=1)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _connect_signals(self):
        # Search Bar Signals
        self.search_bar.search_changed.connect(self._on_search_changed)
        self.search_bar.scan_requested.connect(self._on_scan_dir_requested)
        self.search_bar.demo_gen_requested.connect(self._on_demo_gen_requested)
        self.search_bar.hud_toggle_requested.connect(self._on_hud_toggle_requested)

        # HUD Panel Signal
        self.hud_panel.filter_changed.connect(self._on_hud_filter_changed)

        # Scanner Controller Signals
        self.scanner_controller.progress.connect(self._on_scan_progress)
        self.scanner_controller.finished.connect(self._on_scan_finished)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position HUD panel floating over top-right of main view container
        if self.hud_panel.isVisible():
            self._position_hud_panel()

    def _position_hud_panel(self):
        self.hud_panel.raise_()
        x = self.view_container.width() - self.hud_panel.width() - 20
        y = 20
        self.hud_panel.move(max(20, x), y)

    def _on_hud_toggle_requested(self):
        if self.hud_panel.isVisible():
            self.hud_panel.hide()
        else:
            self.hud_panel.show()
            self._position_hud_panel()

    def _on_search_changed(self, sql_where: str, params: list, tokens: dict):
        self.current_sql_where = sql_where
        self.current_params = params
        self._reload_studies()

    def _on_hud_filter_changed(self, filter_state: dict):
        self.hud_filter_state = filter_state
        self._reload_studies()

    def _reload_studies(self):
        # Combine NL Search criteria with HUD Filter Panel criteria
        combined_where_clauses = []
        params = list(self.current_params)

        if self.current_sql_where:
            combined_where_clauses.append(f"({self.current_sql_where})")

        # HUD Modalities Filter
        active_mods = self.hud_filter_state.get("modalities", [])
        if active_mods:
            placeholders = ",".join("?" for _ in active_mods)
            combined_where_clauses.append(f"""
                s.study_instance_uid IN (
                    SELECT study_instance_uid FROM series WHERE modality IN ({placeholders})
                )
            """)
            params.extend(active_mods)

        # HUD Min Slices Filter
        min_slices = self.hud_filter_state.get("min_slices", 0)
        if min_slices > 0:
            combined_where_clauses.append("s.num_instances >= ?")
            params.append(min_slices)

        final_where = " AND ".join(combined_where_clauses) if combined_where_clauses else ""
        studies = self.db.query_studies(final_where, tuple(params))

        studies_data = []
        for s in studies:
            instances = self.db.get_study_instances(s["study_instance_uid"])
            studies_data.append((s, instances))

        self.study_grid.set_studies(studies_data)
        self.status_label.setText(f"Displaying {len(studies)} DICOM studies")

    def _on_scan_dir_requested(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select DICOM Directory to Scan")
        if dir_path:
            self._start_scan(dir_path)

    def _on_demo_gen_requested(self):
        self.status_label.setText("Generating synthetic multi-modality DICOM study dataset...")
        demo_dir = generate_sample_dicom_dataset("demo_dicom_data")
        self._start_scan(demo_dir)

    def _start_scan(self, dir_path: str):
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText(f"Scanning directory: {dir_path}...")
        self.scanner_controller.start_scan(dir_path)

    def _on_scan_progress(self, current: int, total: int, status_text: str):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.status_label.setText(status_text)

    def _on_scan_finished(self, total_scanned: int):
        self.progress_bar.hide()
        self.status_label.setText(f"Scan finished. Processed {total_scanned} DICOM instances.")
        self._reload_studies()
