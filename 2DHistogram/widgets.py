# widgets.py — reusable styled Qt helper widgets and factory functions
# ─────────────────────────────────────────────────────────────────────────────
# Import from here whenever you need a styled label, separator, button,
# slider, or combobox.  Nothing in this file depends on data or plot logic.

import os
from PyQt5.QtWidgets import (
    QLabel, QFrame, QPushButton, QSlider, QLineEdit,
)
from PyQt5.QtCore import Qt

from config import (
    TEXT, SUBTEXT, BORDER, ACCENT, DARK_BG,
    SAVE_DIR,
)


# ── Labels & separators ───────────────────────────────────────────────────────

def styled_label(text: str, bold: bool = False,
                 color: str = TEXT, size: int = 11) -> QLabel:
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(
        f"color:{color}; font-size:{size}px; "
        f"font-weight:{weight}; background:transparent;"
    )
    return lbl


def hr() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color:{BORDER}; background:{BORDER}; max-height:1px;")
    return line


# ── Buttons ───────────────────────────────────────────────────────────────────

def styled_btn(text: str, color: str = TEXT, w: int = None) -> QPushButton:
    """Flat bordered button — hover fills with the accent colour."""
    btn = QPushButton(text)
    w_str = f"min-width:{w}px; max-width:{w}px;" if w else ""
    btn.setStyleSheet(f"""
        QPushButton {{
            background: #13131f; color: {color};
            border: 1px solid {color};
            border-radius: 4px; padding: 4px 10px; {w_str}
        }}
        QPushButton:hover {{ background: {color}; color: {DARK_BG}; }}
    """)
    return btn


def top_btn(text: str, active: bool = False) -> QPushButton:
    """Toggle button for the top toolbar (1 Graf / 2 Grafer)."""
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setChecked(active)
    btn.setStyleSheet(top_btn_style(active))
    return btn


def top_btn_style(active: bool) -> str:
    bg  = ACCENT if active else "#13131f"
    col = DARK_BG if active else TEXT
    return (
        f"QPushButton {{"
        f"  background:{bg}; color:{col};"
        f"  border:1px solid {BORDER};"
        f"  border-radius:5px; padding:5px 16px;"
        f"  font-weight:{'bold' if active else 'normal'};"
        f"}}"
        f"QPushButton:hover {{ background:{ACCENT}; color:{DARK_BG}; }}"
    )


def toggle_style(active: bool) -> str:
    """Style for the Dage/Måneder/År skala toggle buttons."""
    bg = ACCENT if active else "#13131f"
    return (
        f"QPushButton {{"
        f"  background:{bg}; color:{TEXT};"
        f"  border:1px solid {BORDER};"
        f"  border-radius:4px; padding:4px 10px;"
        f"  font-weight:{'bold' if active else 'normal'};"
        f"}}"
        f"QPushButton:hover {{ background:{ACCENT}; }}"
    )


# ── Sliders ───────────────────────────────────────────────────────────────────

_SLIDER_STYLE = f"""
    QSlider::groove:horizontal {{
        background: {BORDER}; height: 4px; border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT}; width: 12px; height: 12px;
        margin: -4px 0; border-radius: 6px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT}; border-radius: 2px;
    }}
"""


def make_slider(value: int, mn: int, mx: int, step: int = 1) -> QSlider:
    """Plain horizontal slider with the app style applied."""
    sl = QSlider(Qt.Horizontal)
    sl.setMinimum(mn)
    sl.setMaximum(mx)
    sl.setValue(value)
    sl.setSingleStep(step)
    sl.setStyleSheet(_SLIDER_STYLE)
    return sl


def make_slider_with_edit(value: int, mn: int, mx: int,
                          step: int = 1,
                          fmt: str = 'int') -> tuple:
    """
    Returns (QSlider, QLineEdit).
    fmt='int'   → edit shows plain integer
    fmt='ratio' → edit shows value/100 as 2 d.p. float
    """
    sl = make_slider(value, mn, mx, step)
    disp = f"{value / 100:.2f}" if fmt == 'ratio' else str(value)
    edit = QLineEdit(disp)
    edit.setFixedWidth(56)
    edit.setAlignment(Qt.AlignRight)
    edit.setStyleSheet(f"""
        QLineEdit {{
            background: #13131f; color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 3px; padding: 1px 4px; font-size: 11px;
        }}
        QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    """)
    return sl, edit


def make_slider_with_label(value: int, mn: int, mx: int,
                           step: int = 1,
                           scale: float = None) -> tuple:
    """
    Legacy helper for bins / vmin sliders in the left panel.
    Returns (QSlider, QLabel).
    """
    sl = make_slider(value, mn, mx, step)
    disp = f"{value / scale:.1f}" if scale else str(value)
    lbl = styled_label(disp, color=SUBTEXT)
    lbl.setFixedWidth(42)
    lbl.setAlignment(Qt.AlignRight)
    return sl, lbl


# ── Combobox ──────────────────────────────────────────────────────────────────

def style_combo(combo) -> None:
    """Apply the dark theme to a QComboBox in-place."""
    combo.setStyleSheet(f"""
        QComboBox {{
            background: #13131f; color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 4px; padding: 4px 8px;
        }}
        QComboBox::drop-down {{ border: none; }}
        QComboBox QAbstractItemView {{
            background: #13131f; color: {TEXT};
            selection-background-color: {ACCENT};
        }}
    """)


# ── Misc helpers ───────────────────────────────────────────────────────────────

def get_saved_folders() -> list:
    """Return sorted list of folder names under SAVE_DIR that have settings.json."""
    if not os.path.isdir(SAVE_DIR):
        return []
    return [
        f for f in sorted(os.listdir(SAVE_DIR))
        if os.path.isfile(os.path.join(SAVE_DIR, f, 'settings.json'))
    ]