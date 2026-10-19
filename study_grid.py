from typing import List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QLabel
)
from study_card import StudyCard
from thumbnail_loader import ThumbnailManager

class ResponsiveStudyGrid(QScrollArea):
    """
    Responsive Scrollable Grid layout for displaying DICOM study cards.
    Dynamically recalculates column counts upon resizing.
    """
    study_selected = Signal(str)

    def __init__(self, thumbnail_manager: ThumbnailManager, parent=None):
        super().__init__(parent)
        self.thumbnail_manager = thumbnail_manager
        self.studies_data = [] # List of (study_dict, instances_list)
        self.card_widgets = []
        self.empty_label = None

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("QScrollArea { border: none; background-color: #0B0F19; }")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: #0B0F19;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.setWidget(self.container)

    def set_studies(self, studies_with_instances: List[tuple]):
        """Sets list of (study_dict, instances_list) and rebuilds grid."""
        self.studies_data = studies_with_instances
        self._rebuild_grid()

    def _clear_grid(self):
        # Explicitly hide, detach and schedule deletion for all existing card widgets
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
        self.card_widgets.clear()
        self.empty_label = None

    def _rebuild_grid(self):
        self._clear_grid()

        if not self.studies_data:
            self.empty_label = QLabel("No studies matching your search query or filter.")
            self.empty_label.setStyleSheet("color: #64748B; font-size: 14px; font-weight: 500; padding: 40px;")
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(self.empty_label, 0, 0, 1, -1, Qt.AlignCenter)
            return

        card_width = 280 + 16 # Card size + grid spacing
        available_width = max(300, self.viewport().width() - 32)
        cols = max(1, available_width // card_width)

        for idx, (study, instances) in enumerate(self.studies_data):
            row = idx // cols
            col = idx % cols
            card = StudyCard(study, instances, self.thumbnail_manager)
            card.card_clicked.connect(self.study_selected.emit)
            self.grid_layout.addWidget(card, row, col)
            self.card_widgets.append(card)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Recalculate columns on window resize
        if self.studies_data and self.card_widgets:
            card_width = 280 + 16
            available_width = max(300, self.viewport().width() - 32)
            cols = max(1, available_width // card_width)

            for idx, card in enumerate(self.card_widgets):
                row = idx // cols
                col = idx % cols
                self.grid_layout.removeWidget(card)
                self.grid_layout.addWidget(card, row, col)
