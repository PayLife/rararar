from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame
)
from nl_filter import NaturalLanguageFilter

class TokenBadgeWidget(QLabel):
    """Visual pill/badge showing an automatically extracted filter token (e.g. [Modality: CT])."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("TokenBadge")
        self.setStyleSheet("""
            QLabel#TokenBadge {
                background-color: rgba(0, 240, 255, 0.2);
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.5);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }
        """)


class NaturalLanguageSearchBar(QFrame):
    """
    Innovative Search Bar with live natural language parsing token badges and quick actions.
    Emits search_changed(sql_where, params, tokens)
    """
    search_changed = Signal(str, list, dict)
    scan_requested = Signal()
    demo_gen_requested = Signal()
    hud_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchBarContainer")
        self.nl_parser = NaturalLanguageFilter()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # Search Icon
        self.icon_label = QLabel("⚡")
        self.icon_label.setStyleSheet("font-size: 16px; color: #00F0FF;")

        # Natural Language Input Field
        self.input_field = QLineEdit()
        self.input_field.setObjectName("SearchInput")
        self.input_field.setPlaceholderText("Search natural language (e.g., 'CT Chest from last week', 'MR Brain 2023')...")
        self.input_field.textChanged.connect(self._on_text_changed)

        # Layout for active token badges
        self.tokens_layout = QHBoxLayout()
        self.tokens_layout.setSpacing(4)
        self.tokens_widget = QWidget()
        self.tokens_widget.setLayout(self.tokens_layout)

        # Quick Action Buttons
        self.hud_btn = QPushButton("🎛️ HUD Filters")
        self.hud_btn.setToolTip("Toggle Floating HUD Filter Overlay")
        self.hud_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.8);
                color: #E2E8F0;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 0.2);
                border-color: #00F0FF;
                color: #00F0FF;
            }
        """)
        self.hud_btn.clicked.connect(self.hud_toggle_requested.emit)

        self.scan_btn = QPushButton("📁 Scan Dir")
        self.scan_btn.setToolTip("Select local folder to scan DICOM studies")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #00F0FF 0%, #7B2CBF 100%);
                color: #0B0F19;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #33F3FF 0%, #9D4EDD 100%);
            }
        """)
        self.scan_btn.clicked.connect(self.scan_requested.emit)

        self.demo_btn = QPushButton("⚡ Load Demo Data")
        self.demo_btn.setToolTip("Generate synthetic multi-modality DICOM study dataset")
        self.demo_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(123, 44, 191, 0.3);
                color: #D8B4FE;
                border: 1px solid rgba(123, 44, 191, 0.6);
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(123, 44, 191, 0.5);
                color: #FFFFFF;
            }
        """)
        self.demo_btn.clicked.connect(self.demo_gen_requested.emit)

        # Assemble layout
        layout.addWidget(self.icon_label)
        layout.addWidget(self.input_field, stretch=1)
        layout.addWidget(self.tokens_widget)
        layout.addWidget(self.hud_btn)
        layout.addWidget(self.scan_btn)
        layout.addWidget(self.demo_btn)

    def _on_text_changed(self, text: str):
        # Clear existing badges
        while self.tokens_layout.count():
            item = self.tokens_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sql_where, params, tokens = self.nl_parser.parse(text)

        # Create token badges
        if 'modality' in tokens:
            badge = TokenBadgeWidget(f"Modality: {tokens['modality']}")
            self.tokens_layout.addWidget(badge)
        if 'time_frame' in tokens:
            badge = TokenBadgeWidget(f"Date: {tokens['time_frame']}")
            self.tokens_layout.addWidget(badge)
        if 'free_text' in tokens:
            badge = TokenBadgeWidget(f"Text: \"{tokens['free_text']}\"")
            self.tokens_layout.addWidget(badge)

        self.search_changed.emit(sql_where, params, tokens)

    def set_text(self, text: str):
        self.input_field.setText(text)
