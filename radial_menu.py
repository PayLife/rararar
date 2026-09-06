import math
from PySide6.QtCore import Qt, Signal, QPoint, QPropertyAnimation, Property, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect

class RadialMenuWidget(QWidget):
    """
    Animated circular pie/radial HUD context menu around the cursor.
    """
    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self.tools = [
            {"id": "wl", "label": "W/L", "icon": "🌓"},
            {"id": "zoom", "label": "Zoom", "icon": "🔍"},
            {"id": "pan", "label": "Pan", "icon": "✋"},
            {"id": "measure", "label": "Measure", "icon": "📐"},
            {"id": "ai", "label": "AI Mode", "icon": "🧠"},
            {"id": "reset", "label": "Reset", "icon": "🔄"},
        ]

        self.inner_radius = 35
        self.outer_radius = 115
        self.menu_size = (self.outer_radius + 15) * 2
        self.setFixedSize(self.menu_size, self.menu_size)

        self.hovered_index = -1
        self._anim_progress = 0.0

        # Animation
        self.animation = QPropertyAnimation(self, b"anim_progress")
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.setMouseTracking(True)

    @Property(float)
    def anim_progress(self) -> float:
        return self._anim_progress

    @anim_progress.setter
    def anim_progress(self, val: float):
        self._anim_progress = val
        self.update()

    def popup_at(self, global_pos: QPoint):
        center_offset = QPoint(self.width() // 2, self.height() // 2)
        target_pos = global_pos - center_offset
        self.move(target_pos)
        self.hovered_index = -1
        self.show()
        self.raise_()

        self.animation.stop()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def _get_sector_at(self, pos: QPoint) -> int:
        cx, cy = self.width() / 2.0, self.height() / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < self.inner_radius or dist > self.outer_radius:
            return -1

        # Angle in degrees starting from top (12 o'clock, clockwise)
        angle = math.degrees(math.atan2(dy, dx)) + 90.0
        if angle < 0:
            angle += 360.0

        num_items = len(self.tools)
        sector_angle = 360.0 / num_items
        idx = int(angle // sector_angle) % num_items
        return idx

    def mouseMoveEvent(self, event):
        idx = self._get_sector_at(event.position().toPoint())
        if idx != self.hovered_index:
            self.hovered_index = idx
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._get_sector_at(event.position().toPoint())
            if idx != -1:
                tool_id = self.tools[idx]["id"]
                self.tool_selected.emit(tool_id)
                self.close()
            else:
                self.close()
        elif event.button() == Qt.RightButton:
            self.close()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2.0, self.height() / 2.0
        num_items = len(self.tools)
        sector_angle = 360.0 / num_items

        # Animated scaling effect
        scale = 0.5 + 0.5 * self._anim_progress
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        painter.translate(-cx, -cy)

        for i, tool in enumerate(self.tools):
            start_angle_deg = (i * sector_angle) - 90.0
            span_angle_deg = sector_angle - 2.0 # 2 degree gap between wedges

            is_hovered = (i == self.hovered_index)

            # Build Pie Wedge Path
            path = QPainterPath()
            rect_outer = QRectF(cx - self.outer_radius, cy - self.outer_radius, self.outer_radius * 2, self.outer_radius * 2)
            rect_inner = QRectF(cx - self.inner_radius, cy - self.inner_radius, self.inner_radius * 2, self.inner_radius * 2)

            path.arcMoveTo(rect_outer, -start_angle_deg)
            path.arcTo(rect_outer, -start_angle_deg, -span_angle_deg)
            path.arcTo(rect_inner, -(start_angle_deg + span_angle_deg), span_angle_deg)
            path.closeSubpath()

            # Colors
            if is_hovered:
                bg_color = QColor(0, 240, 255, 180) # Glowing Cyan
                border_color = QColor("#00F0FF")
                text_color = QColor("#0B0F19")
            else:
                bg_color = QColor(15, 23, 42, 220) # Translucent Dark Slate
                border_color = QColor(0, 240, 255, 60)
                text_color = QColor("#E2E8F0")

            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QBrush(bg_color))
            painter.drawPath(path)

            # Icon & Text Position
            mid_angle_rad = math.radians(start_angle_deg + span_angle_deg / 2.0)
            mid_r = (self.inner_radius + self.outer_radius) / 2.0
            tx = cx + mid_r * math.cos(mid_angle_rad)
            ty = cy + mid_r * math.sin(mid_angle_rad)

            painter.setPen(text_color)
            font = QFont("Segoe UI", 10, QFont.Bold if is_hovered else QFont.Medium)
            painter.setFont(font)

            label_str = f"{tool['icon']} {tool['label']}"
            painter.drawText(QRectF(tx - 40, ty - 15, 80, 30), Qt.AlignCenter, label_str)

        # Draw Center Core Dot
        center_path = QPainterPath()
        center_path.addEllipse(QRectF(cx - (self.inner_radius - 4), cy - (self.inner_radius - 4), (self.inner_radius - 4) * 2, (self.inner_radius - 4) * 2))
        painter.setPen(QPen(QColor("#00F0FF"), 2))
        painter.setBrush(QBrush(QColor(11, 15, 25, 240)))
        painter.drawPath(center_path)

        painter.setPen(QColor("#00F0FF"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(cx - 20, cy - 12, 40, 24), Qt.AlignCenter, "TOOLS")
