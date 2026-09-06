from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSlider, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

class ModalityChip(QPushButton):
    """Filter toggle chip button with cyber-medical styling."""
    def __init__(self, modality: str, parent=None):
        super().__init__(modality, parent)
        self.modality = modality
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "ChipButton")
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.8);
                color: #94A3B8;
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 12px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 0.15);
                border-color: rgba(0, 240, 255, 0.5);
                color: #00F0FF;
            }
            QPushButton:checked {
                background-color: rgba(0, 240, 255, 0.25);
                color: #00F0FF;
                border: 1px solid #00F0FF;
            }
        """)


class FloatingHudFilterPanel(QFrame):
    """
    Floating HUD panel overlay for fast modality & criteria filtering.
    Supports smooth collapse/expand animation and emit filter_changed signals.
    """
    filter_changed = Signal(dict) # dict of active filter state

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HudPanel")
        self.is_expanded = True
        self.active_modalities = set()
        self.min_slices = 0

        self.setFixedWidth(320)
        self._setup_style()
        self._init_ui()

    def _setup_style(self):
        self.setStyleSheet("""
            QFrame#HudPanel {
                background-color: rgba(15, 23, 42, 0.92);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 240, 255, 60))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        title_icon = QLabel("🎛️")
        title_icon.setStyleSheet("font-size: 16px; color: #00F0FF;")
        title = QLabel("HUD Quick Filters")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFFFFF;")

        self.toggle_btn = QPushButton("−")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.05);
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 0.2);
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_expand)

        header.addWidget(title_icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.toggle_btn)

        # Content Widget
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Modality Toggle Chips
        mod_lbl = QLabel("MODALITY CHIPS")
        mod_lbl.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 1px;")

        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        self.modality_chips = {}
        for mod in ["CT", "MR", "CR", "US", "PT"]:
            chip = ModalityChip(mod)
            chip.toggled.connect(self._on_chip_toggled)
            self.modality_chips[mod] = chip
            chips_layout.addWidget(chip)

        # Slice Count Filter Slider
        slider_lbl_layout = QHBoxLayout()
        slider_title = QLabel("MIN SLICES PER SERIES")
        slider_title.setStyleSheet("color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        self.slider_val_lbl = QLabel("0")
        self.slider_val_lbl.setStyleSheet("color: #00F0FF; font-weight: bold; font-size: 11px;")
        slider_lbl_layout.addWidget(slider_title)
        slider_lbl_layout.addStretch()
        slider_lbl_layout.addWidget(self.slider_val_lbl)

        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setRange(0, 20)
        self.slice_slider.setValue(0)
        self.slice_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #1E293B;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #00F0FF;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #00F0FF;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        self.slice_slider.valueChanged.connect(self._on_slider_changed)

        # Reset Filters Button
        self.reset_btn = QPushButton("Reset HUD Filters")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #94A3B8;
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                padding: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border-color: #EF4444;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_filters)

        content_layout.addWidget(mod_lbl)
        content_layout.addLayout(chips_layout)
        content_layout.addLayout(slider_lbl_layout)
        content_layout.addWidget(self.slice_slider)
        content_layout.addWidget(self.reset_btn)

        self.main_layout.addLayout(header)
        self.main_layout.addWidget(self.content_widget)

    def _on_chip_toggled(self, checked: bool):
        chip = self.sender()
        if chip:
            if checked:
                self.active_modalities.add(chip.modality)
            else:
                self.active_modalities.discard(chip.modality)
            self._emit_filter_state()

    def _on_slider_changed(self, value: int):
        self.min_slices = value
        self.slider_val_lbl.setText(str(value))
        self._emit_filter_state()

    def reset_filters(self):
        for chip in self.modality_chips.values():
            chip.blockSignals(True)
            chip.setChecked(False)
            chip.blockSignals(False)
        self.active_modalities.clear()

        self.slice_slider.blockSignals(True)
        self.slice_slider.setValue(0)
        self.slice_slider.blockSignals(False)
        self.slider_val_lbl.setText("0")
        self.min_slices = 0

        self._emit_filter_state()

    def _emit_filter_state(self):
        state = {
            "modalities": list(self.active_modalities),
            "min_slices": self.min_slices
        }
        self.filter_changed.emit(state)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self.toggle_btn.setText("−" if self.is_expanded else "+")
        self.adjustSize()
