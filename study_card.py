import os
from typing import List, Dict, Any
from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QLinearGradient, QMouseEvent, QEnterEvent
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect
)
from thumbnail_loader import ThumbnailManager

MODALITY_COLORS = {
    'CT': ('#00F0FF', 'rgba(0, 240, 255, 0.25)'),
    'MR': ('#A855F7', 'rgba(168, 85, 247, 0.25)'),
    'CR': ('#10B981', 'rgba(16, 185, 129, 0.25)'),
    'XR': ('#10B981', 'rgba(16, 185, 129, 0.25)'),
    'US': ('#F59E0B', 'rgba(245, 158, 11, 0.25)'),
    'PT': ('#EC4899', 'rgba(236, 72, 153, 0.25)'),
}

class StudyCard(QFrame):
    """
    Card displaying study information with interactive real-time hover scrubbing across thumbnail slices.
    """
    card_clicked = Signal(str) # study_instance_uid

    def __init__(self, study_data: Dict[str, Any], instances: List[Dict[str, Any]], thumbnail_manager: ThumbnailManager, parent=None):
        super().__init__(parent)
        self.study_data = study_data
        self.instances = instances
        self.thumbnail_manager = thumbnail_manager
        self.current_slice_idx = 0
        self.is_hovered = False

        self.setFixedSize(280, 320)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        self._init_ui()
        self._setup_style()
        self._load_current_slice_thumbnail()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Patient Name & Modality Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        patient_name = self.study_data.get("patient_name", "ANONYMOUS").replace("^", " ")
        self.name_label = QLabel(patient_name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFFFFF;")

        modality = self.study_data.get("modalities", "OT").split(',')[0].strip()
        border_col, bg_col = MODALITY_COLORS.get(modality, ('#00F0FF', 'rgba(0,240,255,0.2)'))
        self.modality_badge = QLabel(modality)
        self.modality_badge.setAlignment(Qt.AlignCenter)
        self.modality_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_col};
                color: {border_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)

        header_layout.addWidget(self.name_label, stretch=1)
        header_layout.addWidget(self.modality_badge)

        # Patient ID and Date
        sub_header = QHBoxLayout()
        pid = self.study_data.get("patient_id", "UNKNOWN")
        sdate = self.study_data.get("study_date", "")
        if len(sdate) == 8:
            sdate = f"{sdate[:4]}-{sdate[4:6]}-{sdate[6:]}"

        self.id_label = QLabel(f"ID: {pid}")
        self.id_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.date_label = QLabel(sdate)
        self.date_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        sub_header.addWidget(self.id_label)
        sub_header.addStretch()
        sub_header.addWidget(self.date_label)

        # Thumbnail Image Container Area
        self.thumb_container = QWidget()
        self.thumb_container.setFixedHeight(170)
        self.thumb_container.setMouseTracking(True)
        thumb_layout = QVBoxLayout(self.thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0B0F19; border-radius: 8px;")

        # Scrubbing progress & overlay badge
        self.slice_badge = QLabel("Slice 1/1", self.thumb_container)
        self.slice_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(11, 15, 25, 0.85);
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.4);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.slice_badge.move(8, 8)

        thumb_layout.addWidget(self.image_label)

        # Description & Series/Instances count Footer
        desc = self.study_data.get("study_description", "No Description")
        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 500;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaxLines = 2 if hasattr(self.desc_label, 'setMaxLines') else None

        num_ser = self.study_data.get("num_series", 1)
        num_inst = self.study_data.get("num_instances", len(self.instances))
        self.count_label = QLabel(f"{num_ser} Series • {num_inst} Images")
        self.count_label.setStyleSheet("color: #64748B; font-size: 11px;")

        # Add to layout
        layout.addLayout(header_layout)
        layout.addLayout(sub_header)
        layout.addWidget(self.thumb_container)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.count_label)

    def _setup_style(self):
        self.normal_style = """
            StudyCard {
                background-color: rgba(26, 35, 58, 0.65);
                border: 1px solid rgba(0, 240, 255, 0.15);
                border-radius: 12px;
            }
        """
        self.hover_style = """
            StudyCard {
                background-color: rgba(30, 41, 59, 0.9);
                border: 1px solid #00F0FF;
                border-radius: 12px;
            }
        """
        self.setStyleSheet(self.normal_style)

    def enterEvent(self, event: QEnterEvent):
        self.is_hovered = True
        self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.setStyleSheet(self.normal_style)
        # Reset to slice 0 on leave
        self.current_slice_idx = 0
        self._update_slice_badge()
        self._load_current_slice_thumbnail()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Scrubbing over thumbnail container horizontally
        if self.instances:
            thumb_rect = self.thumb_container.geometry()
            pos_x = event.position().x() - thumb_rect.x()
            width = thumb_rect.width()
            if 0 <= pos_x <= width:
                ratio = max(0.0, min(1.0, pos_x / max(1, width)))
                new_idx = int(ratio * (len(self.instances) - 1))
                if new_idx != self.current_slice_idx:
                    self.current_slice_idx = new_idx
                    self._update_slice_badge()
                    self._load_current_slice_thumbnail()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.study_data["study_instance_uid"])
        super().mousePressEvent(event)

    def _update_slice_badge(self):
        total = len(self.instances) if self.instances else 1
        curr = self.current_slice_idx + 1
        self.slice_badge.setText(f"Slice {curr}/{total}")
        self.slice_badge.adjustSize()

    def _load_current_slice_thumbnail(self):
        if not self.instances:
            return

        instance = self.instances[self.current_slice_idx]
        file_path = instance["file_path"]

        def _on_pixmap_loaded(path: str, pixmap: QPixmap):
            if path == file_path:
                self.image_label.setPixmap(pixmap)

        self.thumbnail_manager.request_thumbnail(file_path, _on_pixmap_loaded, target_size=(256, 160))
