"""
Cyber-Medical Dark Theme QSS Stylesheet
Features: Deep slate background, neon cyan & violet accents, translucent glassmorphic surfaces.
"""

CYBER_MEDICAL_QSS = """
/* Global Styles */
QWidget {
    background-color: #0B0F19;
    color: #E2E8F0;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #00F0FF;
    selection-color: #0B0F19;
}

QMainWindow, QDialog {
    background-color: #0B0F19;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #111827;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1F293D;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00F0FF;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #111827;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #1F293D;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #00F0FF;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Glassmorphic Panel Base */
.GlassPanel {
    background-color: rgba(26, 35, 58, 0.7);
    border: 1px solid rgba(0, 240, 255, 0.2);
    border-radius: 12px;
}

/* Top Search Bar Widget */
#SearchBarContainer {
    background-color: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(0, 240, 255, 0.25);
    border-radius: 16px;
    padding: 6px 12px;
}
#SearchBarContainer:focus-within {
    border: 1px solid #00F0FF;
    background-color: rgba(26, 35, 58, 0.95);
}

QLineEdit#SearchInput {
    background: transparent;
    border: none;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 500;
    padding: 6px;
}
QLineEdit#SearchInput::placeholder {
    color: #64748B;
}

/* Token Badges */
.TokenBadge {
    background-color: rgba(0, 240, 255, 0.15);
    color: #00F0FF;
    border: 1px solid rgba(0, 240, 255, 0.4);
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* HUD Filter Panel */
#HudPanel {
    background-color: rgba(15, 23, 42, 0.88);
    border: 1px solid rgba(0, 240, 255, 0.3);
    border-radius: 16px;
}

/* Modality Toggle Chips */
QPushButton.ChipButton {
    background-color: rgba(30, 41, 59, 0.8);
    color: #94A3B8;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 14px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton.ChipButton:hover {
    background-color: rgba(0, 240, 255, 0.1);
    border-color: rgba(0, 240, 255, 0.5);
    color: #00F0FF;
}
QPushButton.ChipButton:checked {
    background-color: rgba(0, 240, 255, 0.25);
    color: #00F0FF;
    border: 1px solid #00F0FF;
}

/* Primary Push Buttons */
QPushButton.PrimaryButton {
    background: linear-gradient(135deg, #00F0FF 0%, #7B2CBF 100%);
    color: #0B0F19;
    font-weight: bold;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}
QPushButton.PrimaryButton:hover {
    background: linear-gradient(135deg, #33F3FF 0%, #9D4EDD 100%);
}

/* Status Bar */
QStatusBar {
    background-color: #0D1322;
    color: #64748B;
    border-top: 1px solid #1E293B;
}
"""
