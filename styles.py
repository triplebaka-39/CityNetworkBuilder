"""Pixel-art stylesheet for City Network Builder (PySide6).

Call load_fonts() once after QApplication is created and BEFORE
setStyleSheet(APP_STYLE). Put the TTF files in  assets/fonts/ :
    PixelifySans-Regular.ttf   (or the variable font PixelifySans[wght].ttf)
    PressStart2P-Regular.ttf
"""
from pathlib import Path

from PySide6.QtGui import QFontDatabase

COLORS = {
    "cream": "#F4E7C7",     # backgrounds, canvas, light surfaces
    "yellow": "#E9A22A",    # secondary actions, highlights
    "teal": "#269297",      # primary actions, selected / active
    "red": "#E24D1D",       # destructive, warnings, rejected
    "brown": "#5B3525",     # text, borders, outlines
}

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
UI_FONT = "Pixelify Sans"
TITLE_FONT = "Press Start 2P"
_FALLBACK = '"Segoe UI", sans-serif'


def load_fonts():
    """Register bundled fonts. Returns the list of families that loaded."""
    loaded = []
    if FONT_DIR.is_dir():
        for ttf in sorted(FONT_DIR.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(ttf))
            if font_id != -1:
                loaded.extend(QFontDatabase.applicationFontFamilies(font_id))
    missing = [f for f in (UI_FONT, TITLE_FONT) if f not in loaded]
    if missing:
        print(f"[styles] fonts not loaded (check {FONT_DIR}): {missing}")
    return loaded


C = COLORS
_UI = f'"{UI_FONT}", {_FALLBACK}'
_TITLE = f'"{TITLE_FONT}", {_UI}'

# Pixel look: 2-3px square-cornered borders, no radius, no gradients.
# Hard "drop shadow" is faked with a thicker bottom border on buttons.
APP_STYLE = f"""
QMainWindow, QWidget#page {{
    background-color: {C["cream"]};
    color: {C["brown"]};
    font-family: {_UI};
    font-size: 14px;
}}
QWidget {{ font-family: {_UI}; }}
QToolTip {{
    background-color: {C["cream"]};
    color: {C["brown"]};
    border: 2px solid {C["brown"]};
    padding: 3px;
}}

/* ---------- header ---------- */
QFrame#header {{
    background-color: {C["cream"]};
    border: 3px solid {C["brown"]};
    border-radius: 0px;
}}
QLabel#appTitle {{
    color: {C["brown"]};
    font-family: {_TITLE};
    font-size: 16px;
    letter-spacing: 1px;
}}
QLabel#appSubtitle {{
    color: {C["brown"]};
    font-size: 13px;
}}
QLabel#phaseLabel {{
    color: {C["brown"]};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}}

/* ---------- right-panel scroll area ---------- */
QScrollArea {{ border: none; background: transparent; }}
QWidget#panelContent {{ background-color: {C["cream"]}; }}
QStatusBar {{
    background-color: {C["cream"]};
    color: {C["brown"]};
    border-top: 2px solid {C["brown"]};
}}
QScrollBar:vertical {{
    background: {C["cream"]};
    border: 2px solid {C["brown"]};
    width: 14px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["teal"]};
    border: 2px solid {C["brown"]};
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ---------- section panels ---------- */
QGroupBox {{
    color: {C["brown"]};
    background-color: {C["cream"]};
    border: 3px solid {C["brown"]};
    border-radius: 0px;
    margin-top: 14px;
    padding: 10px 6px 6px 6px;
    font-size: 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 2px 6px;
    color: {C["cream"]};
    background-color: {C["brown"]};
    font-family: {_TITLE};
    font-size: 9px;
}}
QGroupBox#algorithmPanel, QGroupBox#primResultsPanel {{
    border: 3px solid {C["brown"]};
}}
QGroupBox#primResultsPanel::title {{
    background-color: {C["teal"]};
    color: {C["cream"]};
}}

/* ---------- labels ---------- */
QLabel {{ color: {C["brown"]}; }}
QLabel#algorithmInfo {{
    color: {C["brown"]};
    font-size: 13px;
    padding: 2px 1px;
}}
QLabel#stepNotification {{
    color: {C["cream"]};
    background-color: {C["brown"]};
    border: 2px solid {C["yellow"]};
    padding: 6px 10px;
    font-size: 12px;
}}
QLabel#primResultsStatus {{
    color: {C["brown"]};
    font-family: {_TITLE};
    font-size: 11px;
}}
QLabel#primResultsCost {{
    color: {C["brown"]};
    background-color: {C["yellow"]};
    border: 3px solid {C["brown"]};
    border-radius: 0px;
    padding: 6px 10px;
    font-family: {_TITLE};
    font-size: 14px;
}}
QLabel#primResultsDistrictCount,
QLabel#primResultsRoadCount,
QLabel#primResultsStart,
QLabel#primResultsDetail {{
    color: {C["brown"]};
    font-size: 13px;
}}

/* ---------- lists ---------- */
QListWidget#algorithmResults, QListWidget#primResultsRoads {{
    color: {C["brown"]};
    background-color: {C["cream"]};
    border: 2px solid {C["brown"]};
    border-radius: 0px;
    padding: 2px;
    font-size: 13px;
    outline: none;
}}
QListWidget::item {{ padding: 2px 3px; }}
QListWidget::item:selected {{
    color: {C["cream"]};
    background-color: {C["teal"]};
}}

/* ---------- canvas ---------- */
QGraphicsView#cityCanvas {{
    background-color: {C["cream"]};
    border: 4px solid {C["brown"]};
    border-radius: 0px;
}}

/* ---------- buttons ----------
   default QPushButton = primary action (teal)
   secondaryButton     = secondary action (yellow)
   toolButton          = checkable editing tool (cream, teal when active)
   manualModeButton    = mode toggle
   dangerButton        = destructive (red) - use for Delete / Reset Network */
QPushButton {{
    color: {C["cream"]};
    background-color: {C["teal"]};
    border: 2px solid {C["brown"]};
    border-bottom: 5px solid {C["brown"]};
    border-radius: 0px;
    padding: 4px 8px;
    min-height: 24px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton:hover {{ background-color: #2FA8AE; }}
QPushButton:pressed {{
    background-color: #1E7478;
    border-bottom: 2px solid {C["brown"]};
    padding-top: 7px;
}}
QPushButton:focus {{ border: 2px dashed {C["brown"]}; border-bottom: 5px solid {C["brown"]}; }}

QPushButton#secondaryButton {{
    background-color: {C["yellow"]};
    color: {C["brown"]};
}}
QPushButton#secondaryButton:hover {{ background-color: #F2B54D; }}
QPushButton#secondaryButton:pressed {{
    background-color: #C98A1C;
    border-bottom: 2px solid {C["brown"]};
    padding-top: 7px;
}}

QPushButton#toolButton, QPushButton#manualModeButton {{
    background-color: {C["cream"]};
    color: {C["brown"]};
}}
QPushButton#toolButton:hover, QPushButton#manualModeButton:hover {{
    background-color: {C["yellow"]};
}}
QPushButton#toolButton:checked, QPushButton#manualModeButton:checked {{
    background-color: {C["teal"]};
    color: {C["cream"]};
    border-bottom: 2px solid {C["brown"]};
    padding-top: 7px;
}}

QPushButton#dangerButton {{
    background-color: {C["red"]};
    color: {C["cream"]};
}}
QPushButton#dangerButton:hover {{ background-color: #EE6334; }}
QPushButton#dangerButton:pressed {{
    background-color: #B93A12;
    border-bottom: 2px solid {C["brown"]};
    padding-top: 7px;
}}

/* container-scoped sizing keeps the old objectName hooks working */
QWidget#tools QPushButton,
QWidget#algorithmControls QPushButton,
QWidget#manualControls QPushButton {{
    padding: 4px 6px;
    min-height: 24px;
}}

/* disabled: still readable (brown on cream), clearly inactive */
QPushButton:disabled,
QPushButton#secondaryButton:disabled,
QPushButton#toolButton:disabled,
QPushButton#manualModeButton:disabled,
QPushButton#dangerButton:disabled {{
    background-color: {C["cream"]};
    color: {C["brown"]};
    border: 2px dashed {C["brown"]};
    border-bottom: 2px dashed {C["brown"]};
}}

/* ---------- inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    color: {C["brown"]};
    background-color: {C["cream"]};
    border: 2px solid {C["brown"]};
    border-radius: 0px;
    padding: 5px 8px;
    selection-background-color: {C["teal"]};
    selection-color: {C["cream"]};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 3px solid {C["teal"]};
}}
QComboBox QAbstractItemView {{
    color: {C["brown"]};
    background-color: {C["cream"]};
    border: 2px solid {C["brown"]};
    selection-background-color: {C["teal"]};
    selection-color: {C["cream"]};
    outline: none;
}}

/* ---------- dialogs ---------- */
QDialog, QMessageBox {{
    color: {C["brown"]};
    background-color: {C["cream"]};
}}
QDialog QLabel, QMessageBox QLabel {{ color: {C["brown"]}; }}
QDialog QPushButton, QMessageBox QPushButton {{ min-width: 70px; }}
QMessageBox QPushButton:default {{
    background-color: {C["yellow"]};
    color: {C["brown"]};
}}
"""

# --- Colors for the QGraphicsScene items (use these in the canvas code, not QSS) ---
CANVAS_COLORS = {
    "background": C["cream"],
    "node_default": C["cream"],
    "node_outline": C["brown"],
    "node_selected": C["teal"],      # selected district
    "node_visited": C["yellow"],     # already in the MST
    "edge_default": C["brown"],
    "edge_eligible": C["yellow"],    # frontier candidates
    "edge_mst": C["teal"],           # chosen roads
    "edge_rejected": C["red"],       # would form a cycle
    "label_text": C["brown"],
}