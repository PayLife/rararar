import os
import pydicom
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtGui import QImage, QPixmap
from radial_menu import RadialMenuWidget

try:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    import vtkmodules.vtkInteractionStyle
    import vtkmodules.vtkRenderingOpenGL2
    import vtk
    VTK_AVAILABLE = True
except Exception:
    VTK_AVAILABLE = False


class CornerHudOverlay(QFrame):
    """Semi-transparent glassmorphic corner HUD label."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 8px;
                padding: 4px 10px;
            }
            QLabel {
                color: #00F0FF;
                font-family: 'Segoe UI', monospace;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        self.label = QLabel(text)
        layout.addWidget(self.label)

    def setText(self, text: str):
        self.label.setText(text)


class VTKDICOMViewportWidget(QWidget):
    """
    Zero-clutter 2D/3D DICOM Viewport with:
    - 100% full-viewport rendering
    - Animated Radial (Pie) Context Menu on right-click
    - Corner Floating HUD overlays for W/L, Zoom %, Slice location
    - Smooth Inertial Wheel Navigation with momentum
    """
    active_tool_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.series_files = []
        self.current_slice_idx = 0
        self.active_tool = "wl"
        self.patient_name = "PATIENT"
        self.modality = "CT"
        self.window = 400
        self.level = 40

        # Inertial Scrolling Physics State
        self.scroll_velocity = 0.0
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16) # ~60 FPS update
        self.scroll_timer.timeout.connect(self._process_scrolling_physics)

        self._init_ui()
        self._init_radial_menu()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Immersive Full Viewport Display
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #0B0F19;")
        self.layout.addWidget(self.image_label)

        # Corner Floating Overlay HUDs
        self.top_left_hud = CornerHudOverlay("PATIENT: N/A | MODALITY: CT", self)
        self.top_right_hud = CornerHudOverlay("W/L: 400 / 40", self)
        self.bottom_left_hud = CornerHudOverlay("SLICE: 1 / 1 (0.0 mm)", self)
        self.bottom_right_hud = CornerHudOverlay("ZOOM: 100%", self)

    def _init_radial_menu(self):
        self.radial_menu = RadialMenuWidget(self)
        self.radial_menu.tool_selected.connect(self.set_active_tool)

    def set_active_tool(self, tool_id: str):
        self.active_tool = tool_id
        self.active_tool_changed.emit(tool_id)
        if tool_id == "reset":
            self.reset_camera_and_wl()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 16
        w, h = self.width(), self.height()

        self.top_left_hud.raise_()
        self.top_right_hud.raise_()
        self.bottom_left_hud.raise_()
        self.bottom_right_hud.raise_()

        self.top_left_hud.move(margin, margin)
        self.top_right_hud.move(w - self.top_right_hud.width() - margin, margin)
        self.bottom_left_hud.move(margin, h - self.bottom_left_hud.height() - margin)
        self.bottom_right_hud.move(w - self.bottom_right_hud.width() - margin, h - self.bottom_right_hud.height() - margin)

        if self.series_files:
            self._render_current_slice()

    def load_dicom_series(self, files: list, patient_name: str = "PATIENT", modality: str = "CT"):
        if not files:
            return

        self.series_files = sorted(files)
        self.current_slice_idx = len(self.series_files) // 2
        self.patient_name = patient_name
        self.modality = modality

        self.top_left_hud.setText(f"{patient_name.upper()} | {modality}")

        # Compute initial W/L default from middle slice header
        try:
            ds = pydicom.dcmread(self.series_files[self.current_slice_idx], stop_before_pixels=False, force=True)
            if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
                wc = ds.WindowCenter
                ww = ds.WindowWidth
                if isinstance(wc, pydicom.multival.MultiValue): wc = wc[0]
                if isinstance(ww, pydicom.multival.MultiValue): ww = ww[0]
                self.level = float(wc)
                self.window = float(ww)
        except Exception:
            pass

        self._render_current_slice()
        self._update_hud_labels()

    def _render_current_slice(self):
        if not self.series_files:
            return

        file_path = self.series_files[self.current_slice_idx]
        try:
            ds = pydicom.dcmread(file_path, force=True)
            if hasattr(ds, 'pixel_array'):
                arr = ds.pixel_array.astype(float)

                slope = float(getattr(ds, 'RescaleSlope', 1.0))
                intercept = float(getattr(ds, 'RescaleIntercept', 0.0))
                arr = arr * slope + intercept

                # Apply Window / Level
                amin = self.level - self.window / 2.0
                amax = self.level + self.window / 2.0
                arr = np.clip(arr, amin, amax)

                pmin, pmax = arr.min(), arr.max()
                if pmax > pmin:
                    norm = ((arr - pmin) / (pmax - pmin) * 255.0).astype(np.uint8)
                else:
                    norm = np.zeros(arr.shape, dtype=np.uint8)

                height, width = norm.shape[:2]
                qimg = QImage(norm.data, width, height, width, QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimg)

                target_w = max(100, self.width())
                target_h = max(100, self.height())
                scaled = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            global_pos = self.mapToGlobal(event.position().toPoint())
            self.radial_menu.popup_at(global_pos)
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._on_wheel_forward()
        elif delta < 0:
            self._on_wheel_backward()
        super().wheelEvent(event)

    def _update_hud_labels(self):
        total = max(1, len(self.series_files))
        curr = self.current_slice_idx + 1
        w = int(self.window)
        l = int(self.level)

        self.top_right_hud.setText(f"W: {w} | L: {l}")
        self.bottom_left_hud.setText(f"SLICE: {curr} / {total}")
        self.bottom_right_hud.setText("ZOOM: 100%")

        self.top_right_hud.adjustSize()
        self.bottom_left_hud.adjustSize()
        self.bottom_right_hud.adjustSize()

    def _on_wheel_forward(self):
        self.scroll_velocity -= 1.8
        if not self.scroll_timer.isActive():
            self.scroll_timer.start()

    def _on_wheel_backward(self):
        self.scroll_velocity += 1.8
        if not self.scroll_timer.isActive():
            self.scroll_timer.start()

    def _process_scrolling_physics(self):
        if not self.series_files:
            self.scroll_timer.stop()
            return

        step = int(self.scroll_velocity)
        if step != 0:
            new_idx = max(0, min(len(self.series_files) - 1, self.current_slice_idx + step))
            if new_idx != self.current_slice_idx:
                self.current_slice_idx = new_idx
                self._render_current_slice()
                self._update_hud_labels()
            self.scroll_velocity -= step

        self.scroll_velocity *= 0.75
        if abs(self.scroll_velocity) < 0.1:
            self.scroll_velocity = 0.0
            self.scroll_timer.stop()

    def reset_camera_and_wl(self):
        self.window = 400
        self.level = 40
        self._render_current_slice()
        self._update_hud_labels()
