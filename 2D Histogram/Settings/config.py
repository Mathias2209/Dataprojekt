# config.py — shared constants, colours, and global state
# ─────────────────────────────────────────────────────────
# Read-only by convention: import values, never mutate them here.
# The one exception is DATASET_MAP, which is populated at startup by main().

# ── Colours ────────────────────────────────────────────────────────────────────
DARK_BG  = "#1a1a1a"
PANEL_BG = "#282828"
ACCENT   = "#e8e8e8"
TEXT     = "#b8b8b8"
SUBTEXT  = "#707070"
BORDER   = "#404040"
SUCCESS  = "#5a9e5a"
DANGER   = "#c0504d"
INFO     = "#707070"

# ── Scale config ───────────────────────────────────────────────────────────────
SCALE_CONFIG = {
    'Måneder': {'divisor': 30.437, 'label': 'Måneder i cirkulation'},
    'År':      {'divisor': 365.25, 'label': 'År i cirkulation'},
}

# ── Reference lines ────────────────────────────────────────────────────────────
REF_LINE_DEFS = [
    (30.437 / 4, '4 vask/måned'),
    (30.437 / 2, '2 vask/måned'),
    (30.437,     '1 vask/måned'),
    (30.437 * 3, '1 vask/3 mdr.'),
    (30.437 * 6, '1 vask/6 mdr.'),
]
REF_COLORS     = ["#e03030", "#f08030", "#f0f000", "#3070e0", "#30c050"]
REF_LINESTYLES = ['-', '-', '-', '-', '-']

# ── App defaults ───────────────────────────────────────────────────────────────
import os as _os
_HERE            = _os.path.dirname(_os.path.abspath(__file__))
SAVE_DIR         = 'Saved Histograms'
CACHE_FILE       = _os.path.join(_HERE, 'data_cache.pkl')
DEFAULT_MAX_DAGE = int(8  * 365.25)   # default slider start value (8 years)
MAX_DAGE         = int(10 * 365.25)   # hard cap on the slider maximum (10 years)
DEFAULT_MAX_VASK = 250
RATIO_COL        = 'Vask per måned'

# ── Dataset map ────────────────────────────────────────────────────────────────
# Populated at startup in main() — do not import this before main() runs.
DATASET_MAP: dict = {}