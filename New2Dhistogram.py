import sys, os, copy, json, numpy as np
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSlider, QCheckBox, QPushButton, QLineEdit,
    QTextEdit, QScrollArea, QFrame, QButtonGroup, QSizePolicy,
    QMessageBox, QListWidget, QAbstractItemView, QTabWidget,
    QSplitter, QGroupBox, QToolButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QLinearGradient

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm, Normalize

DEMO_MODE = False

# Dataset globals — filled in during bootstrap inside main()
samlet_df = skjorte_data = shorts_data = bukse_data = tshirt_data = None
langærmet_data = jakke_data = fleece_data = overall_data = None
forklæde_data = kittel_data = busseron_data = kokkejakke_data = andre_data = None

# ── Global config ──────────────────────────────────────────────────────────────
SCALE_CONFIG = {
    'Dage':    {'divisor': 1,      'label': 'Dage i cirkulation'},
    'Måneder': {'divisor': 30.437, 'label': 'Måneder i cirkulation'},
    'År':      {'divisor': 365.25, 'label': 'År i cirkulation'},
}
# DATASET_MAP is built after bootstrap() loads the data
DATASET_MAP = {}

REF_LINE_DEFS = [
    (30.437 / 4, '4 vask/måned'),
    (30.437 / 2, '2 vask/måned'),
    (30.437,     '1 vask/måned'),
    (30.437 * 3, '1 vask/3 mdr.'),
    (30.437 * 6, '1 vask/6 mdr.'),
]
REF_COLORS    = ["#00ffd5", "#0095ff", "#00ff00", "#3700ff", "#ffea00"]
REF_LINESTYLES = ['-', '-', '-', '-', '-']
SAVE_DIR         = 'Saved Histograms'
DEFAULT_MAX_DAGE = int(8 * 365.25)
DEFAULT_MAX_VASK = 250
RATIO_COL        = 'Vask per måned'

DARK_BG   = "#1e1e2e"
PANEL_BG  = "#2a2a3e"
ACCENT    = "#7c6af7"
TEXT      = "#cdd6f4"
SUBTEXT   = "#a6adc8"
BORDER    = "#45475a"
SUCCESS   = "#a6e3a1"
DANGER    = "#f38ba8"
INFO      = "#89dceb"


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_arsager(df):
    return ['Alle'] + sorted(df['Kassationsårsag (ui)'].dropna().unique().tolist())

def ratio_range(df):
    if RATIO_COL not in df.columns: return 0.0, 10.0
    col = df[RATIO_COL].replace([np.inf, -np.inf], np.nan).dropna()
    if len(col) == 0: return 0.0, 10.0
    return 0.0, round(float(col.quantile(0.999)), 2)

def get_saved_folders():
    if not os.path.isdir(SAVE_DIR): return []
    return [f for f in sorted(os.listdir(SAVE_DIR))
            if os.path.isfile(os.path.join(SAVE_DIR, f, 'settings.json'))]


# ── Styled widgets ─────────────────────────────────────────────────────────────
def styled_label(text, bold=False, color=TEXT, size=11):
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px; font-weight:{weight}; background:transparent;")
    return lbl

def hr():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color:{BORDER}; background:{BORDER}; max-height:1px;")
    return line


# ── Loading screen ─────────────────────────────────────────────────────────────
class LoadingScreen(QWidget):
    """Animated splash screen shown while the app initialises."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 280)

        # Centre on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # App title
        title = QLabel("2D Histogram")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color:{ACCENT}; font-size:26px; font-weight:bold; background:transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel("Produktcirkulation")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color:{SUBTEXT}; font-size:13px; background:transparent;"
        )
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Dot animation row
        dot_row = QHBoxLayout()
        dot_row.setAlignment(Qt.AlignCenter)
        dot_row.setSpacing(10)
        self._dots = []
        for _ in range(5):
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(f"color:{BORDER}; font-size:14px; background:transparent;")
            dot_row.addWidget(dot)
            self._dots.append(dot)
        layout.addLayout(dot_row)

        # Status label
        self._status = QLabel("Indlæser…")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(
            f"color:{SUBTEXT}; font-size:11px; background:transparent;"
        )
        layout.addWidget(self._status)

        # Animate dots
        self._dot_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)

    def set_status(self, text):
        self._status.setText(text)

    def _tick(self):
        for i, dot in enumerate(self._dots):
            if i == self._dot_idx:
                dot.setStyleSheet(f"color:{ACCENT}; font-size:16px; font-weight:bold; background:transparent;")
            else:
                dot.setStyleSheet(f"color:{BORDER}; font-size:14px; background:transparent;")
        self._dot_idx = (self._dot_idx + 1) % len(self._dots)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(PANEL_BG))
        painter.setPen(QColor(ACCENT))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)


# ── Plot canvas ────────────────────────────────────────────────────────────────
class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(8, 5), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setStyleSheet("background-color:%s;" % DARK_BG)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def draw_histogram(self, data, kassationsårsag, bins, min_dage, max_dage,
                       min_vask, max_vask, x_skala, datasæt_navn='', total=None,
                       log_color=True, ref_lines=None, vmin=0.1,
                       min_ratio=None, max_ratio=None, show_percentiles=None):
        self.fig.clear()
        ax = self.fig.add_subplot(111, facecolor="#13131f")

        kd = data if kassationsårsag == 'Alle' else data[data['Kassationsårsag (ui)'] == kassationsårsag]
        kd = kd[(kd['Dage i cirkulation'] >= min_dage) &
                (kd['Dage i cirkulation'] <= max_dage) &
                (kd['Total antal vask']   >= min_vask) &
                (kd['Total antal vask']   <= max_vask)]
        if RATIO_COL in kd.columns:
            if min_ratio is not None: kd = kd[kd[RATIO_COL] >= min_ratio]
            if max_ratio is not None: kd = kd[kd[RATIO_COL] <= max_ratio]

        div   = SCALE_CONFIG[x_skala]['divisor']
        xlabel = SCALE_CONFIG[x_skala]['label']
        x_min, x_max = min_dage / div, max_dage / div

        cmap = copy.copy(matplotlib.colormaps['Reds'])
        cmap.set_bad('#13131f'); cmap.set_under('#13131f')

        if len(kd) == 0:
            ax.text(0.5, 0.5, 'Ingen data i det valgte interval',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=13, color=SUBTEXT)
        else:
            h = ax.hist2d(kd['Dage i cirkulation'] / div, kd['Total antal vask'],
                          bins=bins, cmap=cmap,
                          range=[[x_min, x_max], [min_vask, max_vask]],
                          norm=LogNorm(vmin=vmin) if log_color else Normalize(vmin=vmin))
            cb = self.fig.colorbar(h[3], ax=ax,
                         label='Antal produkter (log)' if log_color else 'Antal produkter')
            cb.ax.yaxis.label.set_color(TEXT)
            cb.ax.tick_params(colors=TEXT)

        if ref_lines:
            xs = np.linspace(x_min, x_max, 300)
            for i, (interval_days, lbl) in enumerate(REF_LINE_DEFS):
                if lbl in ref_lines:
                    ax.plot(xs, (xs * div) / interval_days,
                            color=REF_COLORS[i], lw=1.5, ls=REF_LINESTYLES[i], label=lbl, alpha=0.9)
            ax.legend(fontsize=8, loc='upper left',
                      facecolor=PANEL_BG, edgecolor=BORDER, labelcolor=TEXT)

        if len(kd) > 0 and show_percentiles:
            col = kd['Dage i cirkulation']
            pct_defs = [
                ('25%',    col.quantile(0.25), '--',  0.85),
                ('Median', col.median(),       '-',   0.97),
                ('75%',    col.quantile(0.75), '--',  0.85),
            ]
            for label, val, ls, y_frac in pct_defs:
                if label not in show_percentiles:
                    continue
                vx = val / div
                if x_min < vx < x_max:
                    ax.axvline(vx, color='white', lw=1.5, ls=ls, alpha=0.85)
                    ax.text(vx, max_vask * y_frac,
                            f'{label}\n{val/365.25:.1f} år\n({val:.0f} dage)',
                            color='white', fontsize=7.5, ha='center', va='top',
                            bbox=dict(boxstyle='round,pad=0.2', fc='#13131f', alpha=0.8, ec='none'))

        title = f'{datasæt_navn} — {kassationsårsag}' if datasæt_navn else kassationsårsag
        pct_str = f'  ({100*len(kd)/total:.1f}% af datasæt)' if total else ''
        ax.set_title(f'{title}\n{len(kd)} produkter{pct_str}', color=TEXT, fontsize=11)
        ax.set_xlabel(xlabel, color=SUBTEXT); ax.set_ylabel('Total antal vask', color=SUBTEXT)
        ax.set_xlim(x_min, x_max); ax.set_ylim(min_vask, max_vask)
        ax.tick_params(colors=SUBTEXT)
        for spine in ax.spines.values(): spine.set_edgecolor(BORDER)

        self.fig.tight_layout()
        self.draw()
        return kd  # return filtered data for CSV export


# ── Control panel ──────────────────────────────────────────────────────────────
class ControlPanel(QScrollArea):
    settings_changed = pyqtSignal()

    def __init__(self, letter, parent=None):
        super().__init__(parent)
        self.letter = letter
        self.setWidgetResizable(True)
        self.setFixedWidth(310)
        self.setStyleSheet(f"""
            QScrollArea {{ background:{PANEL_BG}; border:1px solid {BORDER}; border-radius:8px; }}
            QScrollBar:vertical {{ background:{DARK_BG}; width:8px; border-radius:4px; }}
            QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:4px; }}
        """)

        container = QWidget()
        container.setStyleSheet(f"background:{PANEL_BG};")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        layout.addWidget(styled_label(f"Graf {letter} — Indstillinger", bold=True, size=12, color=ACCENT))
        layout.addWidget(hr())

        # ── Load/Save section ─────────────────────────────────────────
        layout.addWidget(styled_label("📂 Indlæs / Slet", bold=True, color=INFO))
        self.load_combo = QComboBox()
        self._style_combo(self.load_combo)
        self._refresh_saved()
        row = QHBoxLayout()
        self.load_btn    = self._btn("Indlæs", INFO)
        self.refresh_btn = self._btn("🔄", SUBTEXT, w=36)
        self.delete_btn  = self._btn("🗑", DANGER, w=36)
        row.addWidget(self.load_btn); row.addWidget(self.refresh_btn); row.addWidget(self.delete_btn)
        layout.addWidget(self.load_combo); layout.addLayout(row)
        self.io_label = styled_label("", color=SUCCESS)
        layout.addWidget(self.io_label)
        layout.addWidget(hr())

        # ── Dataset ───────────────────────────────────────────────────
        layout.addWidget(styled_label("Datasæt", bold=True))
        self.ds_combo = QComboBox()
        self._style_combo(self.ds_combo)
        for name in DATASET_MAP: self.ds_combo.addItem(name)
        layout.addWidget(self.ds_combo)

        layout.addWidget(styled_label("Kassationsårsag", bold=True))
        self.ar_combo = QComboBox()
        self._style_combo(self.ar_combo)
        self._update_arsager()
        layout.addWidget(self.ar_combo)
        layout.addWidget(hr())

        # ── Plot settings ─────────────────────────────────────────────
        layout.addWidget(styled_label("Bins", bold=True))
        self.bins_slider, bins_val = self._slider(60, 5, 80)
        row2 = QHBoxLayout(); row2.addWidget(self.bins_slider); row2.addWidget(bins_val)
        layout.addLayout(row2)
        self.bins_val_lbl = bins_val

        self.log_cb = QCheckBox("Logaritmisk farveskala")
        self.log_cb.setChecked(True)
        self.log_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(self.log_cb)

        layout.addWidget(styled_label("Farve minimum"))
        self.vmin_slider, vmin_val = self._slider(1, 1, 200, scale=10.0)
        row3 = QHBoxLayout(); row3.addWidget(self.vmin_slider); row3.addWidget(vmin_val)
        layout.addLayout(row3)
        self.vmin_val_lbl = vmin_val
        layout.addWidget(hr())

        # ── Note / Folder / Save ──────────────────────────────────────
        layout.addWidget(styled_label("Note (valgfrit)", bold=True))
        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(60)
        self.note_edit.setStyleSheet(f"background:#13131f; color:{TEXT}; border:1px solid {BORDER}; border-radius:4px;")
        layout.addWidget(self.note_edit)

        layout.addWidget(styled_label("Mappenavn", bold=True))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Lad stå tomt for auto-navn...")
        self.folder_edit.setStyleSheet(f"background:#13131f; color:{TEXT}; border:1px solid {BORDER}; border-radius:4px; padding:4px;")
        layout.addWidget(self.folder_edit)

        row4 = QHBoxLayout()
        self.save_btn = self._btn("💾 Gem", SUCCESS)
        self.csv_btn  = self._btn("📄 CSV", SUBTEXT)
        row4.addWidget(self.save_btn); row4.addWidget(self.csv_btn)
        layout.addLayout(row4)
        layout.addStretch()

        self.setWidget(container)

        # ── Connect signals ───────────────────────────────────────────
        self.ds_combo.currentTextChanged.connect(self._on_dataset_changed)
        self.ar_combo.currentTextChanged.connect(self.settings_changed)
        self.bins_slider.valueChanged.connect(lambda v: [bins_val.setText(str(v)), self.settings_changed.emit()])
        self.vmin_slider.valueChanged.connect(lambda v: [vmin_val.setText(f"{v/10:.1f}"), self.settings_changed.emit()])
        self.log_cb.stateChanged.connect(self.settings_changed)
        self.load_btn.clicked.connect(self._do_load)
        self.refresh_btn.clicked.connect(self._refresh_saved)
        self.delete_btn.clicked.connect(self._do_delete)

    # ── Right panel (filters) ─────────────────────────────────────────────────
    def make_filter_panel(self):
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setFixedWidth(310)
        panel.setStyleSheet(f"""
            QScrollArea {{ background:{PANEL_BG}; border:1px solid {BORDER}; border-radius:8px; }}
            QScrollBar:vertical {{ background:{DARK_BG}; width:8px; border-radius:4px; }}
            QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:4px; }}
        """)
        container = QWidget()
        container.setStyleSheet(f"background:{PANEL_BG};")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(styled_label(f"Graf {self.letter} — Filtrering", bold=True, size=12, color=ACCENT))
        layout.addWidget(hr())

        # X-skala
        layout.addWidget(styled_label("X-akse skala", bold=True))
        skala_row = QHBoxLayout()
        self.skala_btns = {}
        self.skala_group = QButtonGroup()
        for i, s in enumerate(['Dage', 'Måneder', 'År']):
            btn = QPushButton(s)
            btn.setCheckable(True)
            btn.setChecked(s == 'Dage')
            btn.setStyleSheet(self._toggle_style(s == 'Dage'))
            self.skala_btns[s] = btn
            self.skala_group.addButton(btn, i)
            skala_row.addWidget(btn)
        layout.addLayout(skala_row)
        self.skala_group.buttonClicked.connect(self._on_skala_changed)
        layout.addWidget(hr())

        # Dage sliders — always store days internally; display in current unit
        df = DATASET_MAP[self.ds_combo.currentText()]
        dage_max = int(df['Dage i cirkulation'].max()) + 100
        self._dage_section_label = styled_label("Dage i cirkulation", bold=True)
        layout.addWidget(self._dage_section_label)

        self._min_dage_row_label = styled_label("Min")
        self.min_dage_slider, self.min_dage_edit = self._slider_edit(0, 0, dage_max, step=50)
        r = QHBoxLayout()
        r.addWidget(self._min_dage_row_label)
        r.addWidget(self.min_dage_slider, stretch=1)
        r.addWidget(self.min_dage_edit)
        layout.addLayout(r)

        self._max_dage_row_label = styled_label("Max")
        self.max_dage_slider, self.max_dage_edit = self._slider_edit(min(DEFAULT_MAX_DAGE, dage_max), 0, dage_max, step=50)
        r2 = QHBoxLayout()
        r2.addWidget(self._max_dage_row_label)
        r2.addWidget(self.max_dage_slider, stretch=1)
        r2.addWidget(self.max_dage_edit)
        layout.addLayout(r2)
        layout.addWidget(hr())

        # Vask sliders
        vask_max = int(df['Total antal vask'].max()) + 10
        layout.addWidget(styled_label("Total antal vask", bold=True))

        self.min_vask_slider, self.min_vask_edit = self._slider_edit(0, 0, vask_max)
        r3 = QHBoxLayout()
        r3.addWidget(styled_label("Min"))
        r3.addWidget(self.min_vask_slider, stretch=1)
        r3.addWidget(self.min_vask_edit)
        layout.addLayout(r3)

        self.max_vask_slider, self.max_vask_edit = self._slider_edit(DEFAULT_MAX_VASK, 0, vask_max)
        r4 = QHBoxLayout()
        r4.addWidget(styled_label("Max"))
        r4.addWidget(self.max_vask_slider, stretch=1)
        r4.addWidget(self.max_vask_edit)
        layout.addLayout(r4)

        # Ratio sliders
        rmin, rmax = ratio_range(df)
        self.ratio_group = QGroupBox("Vask per måned (ratio)")
        self.ratio_group.setStyleSheet(f"""
            QGroupBox {{ color:{INFO}; font-weight:bold; border:1px solid {BORDER};
                         border-radius:6px; margin-top:8px; padding-top:8px; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:8px; }}
        """)
        ratio_layout = QVBoxLayout()
        self.min_ratio_slider, self.min_ratio_edit = self._slider_edit(
            int(rmin * 100), int(rmin * 100), int(rmax * 100), fmt='ratio')
        r5 = QHBoxLayout()
        r5.addWidget(styled_label("Min"))
        r5.addWidget(self.min_ratio_slider, stretch=1)
        r5.addWidget(self.min_ratio_edit)
        ratio_layout.addLayout(r5)
        self.max_ratio_slider, self.max_ratio_edit = self._slider_edit(
            int(rmax * 100), int(rmin * 100), int(rmax * 100), fmt='ratio')
        r6 = QHBoxLayout()
        r6.addWidget(styled_label("Max"))
        r6.addWidget(self.max_ratio_slider, stretch=1)
        r6.addWidget(self.max_ratio_edit)
        ratio_layout.addLayout(r6)
        self.ratio_group.setLayout(ratio_layout)
        layout.addWidget(self.ratio_group)
        self.ratio_group.setVisible(RATIO_COL in df.columns)

        layout.addWidget(hr())

        # ── Reference lines ───────────────────────────────────────────
        layout.addWidget(styled_label("Referencelinjer", bold=True))
        self.ref_cbs = {}
        for i, (_, lbl) in enumerate(REF_LINE_DEFS):
            cb = QCheckBox(lbl)
            cb.setStyleSheet(f"color:{REF_COLORS[i]}; background:transparent; font-weight:bold;")
            cb.stateChanged.connect(self.settings_changed)
            self.ref_cbs[lbl] = cb
            layout.addWidget(cb)

        layout.addWidget(hr())

        # ── Percentile lines ──────────────────────────────────────────
        layout.addWidget(styled_label("Kvantillinjer", bold=True))
        self.pct_cbs = {}
        for lbl in ['25%', 'Median', '75%']:
            cb = QCheckBox(lbl)
            cb.setChecked(True)
            cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
            cb.stateChanged.connect(self.settings_changed)
            self.pct_cbs[lbl] = cb
            layout.addWidget(cb)

        layout.addWidget(hr())

        # ── Sync section (only visible in 2-graf mode, toggled externally) ────
        self.sync_group = QGroupBox("🔗 Synkroniser A↔B")
        self.sync_group.setStyleSheet(f"""
            QGroupBox {{ color:{ACCENT}; font-weight:bold; border:1px solid {BORDER};
                         border-radius:6px; margin-top:8px; padding-top:8px; background:{PANEL_BG}; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:8px; }}
        """)
        sync_layout = QVBoxLayout()
        sync_layout.setSpacing(4)

        self.sync_all_cb = QCheckBox("Alle")
        self.sync_all_cb.setStyleSheet(f"color:{INFO}; font-weight:bold; background:transparent;")
        sync_layout.addWidget(self.sync_all_cb)

        self.sync_cbs = {}
        SYNC_GROUPS = [
            ("Datasæt",              ['datasæt']),
            ("Kassationsårsag",      ['kassationsårsag']),
            ("X-akse skala",         ['x_skala']),
            ("Dage i cirkulation",   ['min_dage', 'max_dage']),
            ("Antal vask",           ['min_vask', 'max_vask']),
            ("Vask per måned ratio", ['min_ratio', 'max_ratio']),
            ("Bins",                 ['bins']),
            ("Farveskala",           ['log_color', 'vmin']),
            ("Referencelinjer",      ['ref_lines']),
            ("Kvantillinjer",        ['show_percentiles']),
        ]
        self._sync_key_map = SYNC_GROUPS
        for label, _ in SYNC_GROUPS:
            cb = QCheckBox(label)
            cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
            sync_layout.addWidget(cb)
            self.sync_cbs[label] = cb

        self.sync_group.setLayout(sync_layout)
        self.sync_group.setVisible(False)   # hidden until 2-graf mode
        layout.addWidget(self.sync_group)

        # Wire sync "Alle" toggle
        self.sync_all_cb.stateChanged.connect(self._on_sync_all_changed)
        for cb in self.sync_cbs.values():
            cb.stateChanged.connect(self._on_sync_individual_changed)

        layout.addStretch()
        panel.setWidget(container)
        self.filter_panel = panel

        # ── Wire slider → edit ────────────────────────────────────────
        self.min_dage_slider.valueChanged.connect(self._sync_dage_slider_to_edit)
        self.max_dage_slider.valueChanged.connect(self._sync_dage_slider_to_edit)
        self.min_vask_slider.valueChanged.connect(
            lambda v: self._sync_int_slider_to_edit(v, self.min_vask_edit))
        self.max_vask_slider.valueChanged.connect(
            lambda v: self._sync_int_slider_to_edit(v, self.max_vask_edit))
        self.min_ratio_slider.valueChanged.connect(
            lambda v: self._sync_ratio_slider_to_edit(v, self.min_ratio_edit))
        self.max_ratio_slider.valueChanged.connect(
            lambda v: self._sync_ratio_slider_to_edit(v, self.max_ratio_edit))

        # ── Wire edit → slider ────────────────────────────────────────
        self.min_dage_edit.editingFinished.connect(
            lambda: self._sync_dage_edit_to_slider(self.min_dage_edit, self.min_dage_slider))
        self.max_dage_edit.editingFinished.connect(
            lambda: self._sync_dage_edit_to_slider(self.max_dage_edit, self.max_dage_slider))
        self.min_vask_edit.editingFinished.connect(
            lambda: self._sync_int_edit_to_slider(self.min_vask_edit, self.min_vask_slider))
        self.max_vask_edit.editingFinished.connect(
            lambda: self._sync_int_edit_to_slider(self.max_vask_edit, self.max_vask_slider))
        self.min_ratio_edit.editingFinished.connect(
            lambda: self._sync_ratio_edit_to_slider(self.min_ratio_edit, self.min_ratio_slider))
        self.max_ratio_edit.editingFinished.connect(
            lambda: self._sync_ratio_edit_to_slider(self.max_ratio_edit, self.max_ratio_slider))

        # ── Emit settings_changed on any slider move ──────────────────
        for sl in [self.min_dage_slider, self.max_dage_slider,
                   self.min_vask_slider, self.max_vask_slider,
                   self.min_ratio_slider, self.max_ratio_slider]:
            sl.valueChanged.connect(self.settings_changed)

        return panel

    # ── Unit-aware dage sync helpers ──────────────────────────────────────────
    def _current_skala(self):
        return next((s for s, b in self.skala_btns.items() if b.isChecked()), 'Dage')

    def _days_to_display(self, days):
        skala = self._current_skala()
        div = SCALE_CONFIG[skala]['divisor']
        if skala == 'Dage':    return str(int(round(days / div)))
        if skala == 'Måneder': return f"{days / div:.1f}"
        return f"{days / div:.2f}"

    def _display_to_days(self, text):
        skala = self._current_skala()
        div = SCALE_CONFIG[skala]['divisor']
        try:
            return int(round(float(text) * div))
        except ValueError:
            return None

    def _sync_dage_slider_to_edit(self):
        self.min_dage_edit.setText(self._days_to_display(self.min_dage_slider.value()))
        self.max_dage_edit.setText(self._days_to_display(self.max_dage_slider.value()))

    def _sync_dage_edit_to_slider(self, edit, slider):
        days = self._display_to_days(edit.text())
        if days is not None:
            days = max(slider.minimum(), min(slider.maximum(), days))
            slider.setValue(days)
        else:
            edit.setText(self._days_to_display(slider.value()))

    def _sync_int_slider_to_edit(self, v, edit):
        edit.setText(str(v))

    def _sync_int_edit_to_slider(self, edit, slider):
        try:
            v = int(round(float(edit.text())))
            v = max(slider.minimum(), min(slider.maximum(), v))
            slider.setValue(v)
        except ValueError:
            edit.setText(str(slider.value()))

    def _sync_ratio_slider_to_edit(self, v, edit):
        edit.setText(f"{v/100:.2f}")

    def _sync_ratio_edit_to_slider(self, edit, slider):
        try:
            v = int(round(float(edit.text()) * 100))
            v = max(slider.minimum(), min(slider.maximum(), v))
            slider.setValue(v)
        except ValueError:
            edit.setText(f"{slider.value()/100:.2f}")

    def _on_sync_all_changed(self, state):
        checked = state == Qt.Checked
        for cb in self.sync_cbs.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)

    def _on_sync_individual_changed(self):
        all_on = all(cb.isChecked() for cb in self.sync_cbs.values())
        self.sync_all_cb.blockSignals(True)
        self.sync_all_cb.setChecked(all_on)
        self.sync_all_cb.blockSignals(False)

    def synced_keys(self):
        keys = set()
        for label, key_list in self._sync_key_map:
            if self.sync_cbs[label].isChecked():
                keys.update(key_list)
        return keys

    def _on_skala_changed(self, btn):
        for s, b in self.skala_btns.items():
            b.setStyleSheet(self._toggle_style(b.isChecked()))
        # Update section label and dage edit fields to reflect new unit
        skala = self._current_skala()
        unit_map = {'Dage': 'Dage i cirkulation', 'Måneder': 'Måneder i cirkulation', 'År': 'År i cirkulation'}
        self._dage_section_label.setText(unit_map[skala])
        self._sync_dage_slider_to_edit()
        self.settings_changed.emit()

    def _toggle_style(self, active):
        bg = ACCENT if active else "#13131f"
        return (f"QPushButton {{ background:{bg}; color:{TEXT}; border:1px solid {BORDER}; "
                f"border-radius:4px; padding:4px 10px; font-weight:{'bold' if active else 'normal'}; }}"
                f"QPushButton:hover {{ background:{ACCENT}; }}")

    def _on_dataset_changed(self, name):
        df = DATASET_MAP[name]
        self._update_arsager()
        # Update dage range (sliders always store days)
        dage_max = int(df['Dage i cirkulation'].max()) + 100
        self.min_dage_slider.setMaximum(dage_max)
        self.max_dage_slider.setMaximum(dage_max)
        self.max_dage_slider.setValue(min(DEFAULT_MAX_DAGE, dage_max))
        self.min_dage_slider.setValue(0)
        self._sync_dage_slider_to_edit()
        # Update vask range
        vask_max = int(df['Total antal vask'].max()) + 10
        self.min_vask_slider.setMaximum(vask_max)
        self.max_vask_slider.setMaximum(vask_max)
        self.max_vask_slider.setValue(DEFAULT_MAX_VASK)
        self.min_vask_slider.setValue(0)
        # Update ratio range
        rmin, rmax = ratio_range(df)
        self.min_ratio_slider.setMinimum(int(rmin * 100))
        self.min_ratio_slider.setMaximum(int(rmax * 100))
        self.max_ratio_slider.setMinimum(int(rmin * 100))
        self.max_ratio_slider.setMaximum(int(rmax * 100))
        self.min_ratio_slider.setValue(int(rmin * 100))
        self.max_ratio_slider.setValue(int(rmax * 100))
        self.ratio_group.setVisible(RATIO_COL in df.columns)
        self.settings_changed.emit()

    def _update_arsager(self):
        df = DATASET_MAP[self.ds_combo.currentText()]
        current = self.ar_combo.currentText()
        self.ar_combo.blockSignals(True)
        self.ar_combo.clear()
        for a in get_arsager(df): self.ar_combo.addItem(a)
        idx = self.ar_combo.findText(current)
        self.ar_combo.setCurrentIndex(max(0, idx))
        self.ar_combo.blockSignals(False)

    def _refresh_saved(self):
        self.load_combo.blockSignals(True)
        self.load_combo.clear()
        folders = get_saved_folders()
        if folders:
            for f in folders: self.load_combo.addItem(f)
        else:
            self.load_combo.addItem("(ingen gemte grafer)")
        self.load_combo.blockSignals(False)

    def _do_load(self):
        folder = self.load_combo.currentText()
        if folder == "(ingen gemte grafer)": return
        path = os.path.join(SAVE_DIR, folder, 'settings.json')
        try:
            with open(path, encoding='utf-8') as f: s = json.load(f)
        except Exception as e:
            self.io_label.setText(f"Fejl: {e}"); return

        if s.get('datasæt') in DATASET_MAP:
            self.ds_combo.setCurrentText(s['datasæt'])
        if s.get('kassationsårsag'):
            idx = self.ar_combo.findText(s['kassationsårsag'])
            if idx >= 0: self.ar_combo.setCurrentIndex(idx)
        if s.get('x_skala') in self.skala_btns:
            for btn in self.skala_btns.values(): btn.setChecked(False)
            self.skala_btns[s['x_skala']].setChecked(True)
            for b in self.skala_btns.values():
                b.setStyleSheet(self._toggle_style(b.isChecked()))
        if s.get('bins'): self.bins_slider.setValue(s['bins'])
        if s.get('min_dage') is not None: self.min_dage_slider.setValue(min(s['min_dage'], self.min_dage_slider.maximum()))
        if s.get('max_dage') is not None: self.max_dage_slider.setValue(min(s['max_dage'], self.max_dage_slider.maximum()))
        self._sync_dage_slider_to_edit()
        if s.get('min_vask') is not None: self.min_vask_slider.setValue(min(s['min_vask'], self.min_vask_slider.maximum()))
        if s.get('max_vask') is not None: self.max_vask_slider.setValue(min(s['max_vask'], self.max_vask_slider.maximum()))
        if s.get('log_color') is not None: self.log_cb.setChecked(s['log_color'])
        if s.get('vmin') is not None: self.vmin_slider.setValue(int(s['vmin'] * 10))
        if s.get('ref_lines'):
            for lbl, cb in self.ref_cbs.items(): cb.setChecked(lbl in s['ref_lines'])
        if s.get('min_ratio') is not None:
            self.min_ratio_slider.setValue(int(min(s['min_ratio'] * 100, self.min_ratio_slider.maximum())))
        if s.get('max_ratio') is not None:
            self.max_ratio_slider.setValue(int(min(s['max_ratio'] * 100, self.max_ratio_slider.maximum())))
        self.folder_edit.setText(folder)
        md_path = os.path.join(SAVE_DIR, folder, 'README.md')
        if os.path.isfile(md_path):
            txt = open(md_path, encoding='utf-8').read()
            note = txt.split('## Note')[-1].strip().lstrip('\n') if '## Note' in txt else ''
            self.note_edit.setPlainText(note)
        self.io_label.setText(f"✔ Indlæst: {folder}")
        self.settings_changed.emit()

    def _do_delete(self):
        folder = self.load_combo.currentText()
        if folder == "(ingen gemte grafer)": return
        reply = QMessageBox.question(self, "Slet", f"Slet '{folder}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            import shutil
            try:
                shutil.rmtree(os.path.join(SAVE_DIR, folder))
                self._refresh_saved()
                self.io_label.setText(f"✔ Slettet: {folder}")
            except Exception as e:
                self.io_label.setText(f"Fejl: {e}")

    def get_settings(self):
        skala = next((s for s, b in self.skala_btns.items() if b.isChecked()), 'Dage')
        return {
            'datasæt':        self.ds_combo.currentText(),
            'kassationsårsag': self.ar_combo.currentText(),
            'bins':            self.bins_slider.value(),
            'log_color':       self.log_cb.isChecked(),
            'vmin':            self.vmin_slider.value() / 10.0,
            'ref_lines':        [l for l, cb in self.ref_cbs.items() if cb.isChecked()],
            'show_percentiles': [l for l, cb in self.pct_cbs.items() if cb.isChecked()],
            'x_skala':         skala,
            'min_dage':        self.min_dage_slider.value(),
            'max_dage':        self.max_dage_slider.value(),
            'min_vask':        self.min_vask_slider.value(),
            'max_vask':        self.max_vask_slider.value(),
            'min_ratio':       self.min_ratio_slider.value() / 100.0,
            'max_ratio':       self.max_ratio_slider.value() / 100.0,
        }

    def do_save(self, canvas):
        s = self.get_settings()
        raw = self.folder_edit.text().strip()
        folder = raw.replace(' ', '_') if raw else \
            f"{s['datasæt']}_{s['kassationsårsag']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_')
        subdir = os.path.join(SAVE_DIR, folder)
        os.makedirs(subdir, exist_ok=True)
        canvas.fig.savefig(os.path.join(subdir, 'histogram.jpeg'), dpi=150, bbox_inches='tight')
        s['gemt'] = datetime.now().isoformat()
        with open(os.path.join(subdir, 'settings.json'), 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        with open(os.path.join(subdir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(f"# {s['datasæt']} — {s['kassationsårsag']}\n\n*{datetime.now():%Y-%m-%d %H:%M:%S}*\n\n")
            note = self.note_edit.toPlainText().strip()
            if note: f.write(f"## Note\n\n{note}\n")
        self.io_label.setText(f"✔ Gemt: {folder}/")
        self._refresh_saved()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _btn(self, text, color=TEXT, w=None):
        btn = QPushButton(text)
        w_str = f"min-width:{w}px; max-width:{w}px;" if w else ""
        btn.setStyleSheet(f"""
            QPushButton {{ background:#13131f; color:{color}; border:1px solid {color};
                           border-radius:4px; padding:4px 10px; {w_str} }}
            QPushButton:hover {{ background:{color}; color:{DARK_BG}; }}
        """)
        return btn

    def _slider_edit(self, value, mn, mx, step=1, fmt='int'):
        """Returns (QSlider, QLineEdit). Slider stores raw int; edit shows formatted value."""
        sl = QSlider(Qt.Horizontal)
        sl.setMinimum(mn); sl.setMaximum(mx); sl.setValue(value); sl.setSingleStep(step)
        sl.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background:{BORDER}; height:4px; border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{ACCENT}; width:12px; height:12px;
                                          margin:-4px 0; border-radius:6px; }}
            QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
        """)
        if fmt == 'ratio':
            disp = f"{value/100:.2f}"
        else:
            disp = str(value)
        edit = QLineEdit(disp)
        edit.setFixedWidth(56)
        edit.setAlignment(Qt.AlignRight)
        edit.setStyleSheet(f"""
            QLineEdit {{ background:#13131f; color:{TEXT}; border:1px solid {BORDER};
                         border-radius:3px; padding:1px 4px; font-size:11px; }}
            QLineEdit:focus {{ border:1px solid {ACCENT}; }}
        """)
        return sl, edit

    def _slider(self, value, mn, mx, step=1, scale=None):
        """Legacy helper used for bins/vmin in the left panel — returns (slider, label)."""
        sl = QSlider(Qt.Horizontal)
        sl.setMinimum(mn); sl.setMaximum(mx); sl.setValue(value); sl.setSingleStep(step)
        sl.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background:{BORDER}; height:4px; border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{ACCENT}; width:12px; height:12px;
                                          margin:-4px 0; border-radius:6px; }}
            QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
        """)
        disp = f"{value/scale:.1f}" if scale else str(value)
        lbl = styled_label(disp, color=SUBTEXT)
        lbl.setFixedWidth(42)
        lbl.setAlignment(Qt.AlignRight)
        return sl, lbl

    def _style_combo(self, combo):
        combo.setStyleSheet(f"""
            QComboBox {{ background:#13131f; color:{TEXT}; border:1px solid {BORDER};
                         border-radius:4px; padding:4px 8px; }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{ background:#13131f; color:{TEXT};
                                           selection-background-color:{ACCENT}; }}
        """)


# ── Plot-only widget (canvas + toolbar, no controls) ──────────────────────────
class PlotWidget(QWidget):
    def __init__(self, letter, parent=None):
        super().__init__(parent)
        self.letter = letter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = styled_label(f"  Graf {letter}", bold=True, color=ACCENT, size=11)
        header.setStyleSheet(f"color:{ACCENT}; font-size:11px; font-weight:bold; "
                             f"background:{PANEL_BG}; padding:3px 6px; border-radius:4px;")
        layout.addWidget(header)

        self.canvas = PlotCanvas()
        layout.addWidget(self.canvas)
        self._last_filtered = None

    def redraw(self, s, df):
        self._last_filtered = self.canvas.draw_histogram(
            data=df,
            kassationsårsag=s['kassationsårsag'],
            bins=s['bins'],
            min_dage=s['min_dage'],
            max_dage=s['max_dage'],
            min_vask=s['min_vask'],
            max_vask=s['max_vask'],
            x_skala=s['x_skala'],
            datasæt_navn=s['datasæt'],
            total=len(df),
            log_color=s['log_color'],
            ref_lines=s['ref_lines'],
            vmin=s['vmin'],
            min_ratio=s['min_ratio'],
            max_ratio=s['max_ratio'],
            show_percentiles=s.get('show_percentiles'),
        )


# ── Graph panel (controls + one plot, used in 1-graf mode) ────────────────────
class GraphPanel(QWidget):
    def __init__(self, letter, parent=None):
        super().__init__(parent)
        self.letter = letter
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.ctrl = ControlPanel(letter)
        self.filter_panel = self.ctrl.make_filter_panel()
        self.plot_widget = PlotWidget(letter)

        layout.addWidget(self.ctrl)
        layout.addWidget(self.filter_panel)
        layout.addWidget(self.plot_widget, stretch=1)

        self.ctrl.settings_changed.connect(self.redraw)
        self.ctrl.save_btn.clicked.connect(lambda: self.ctrl.do_save(self.plot_widget.canvas))
        self.ctrl.csv_btn.clicked.connect(self.do_csv)
        self.redraw()

    @property
    def canvas(self):
        return self.plot_widget.canvas

    def redraw(self):
        s = self.ctrl.get_settings()
        df = DATASET_MAP[s['datasæt']]
        self.plot_widget.redraw(s, df)

    def do_csv(self):
        kd = self.plot_widget._last_filtered
        if kd is None: return
        s = self.ctrl.get_settings()
        raw = self.ctrl.folder_edit.text().strip()
        stem = raw.replace(' ', '_') if raw else \
            f"{s['datasæt']}_{s['kassationsårsag']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_')
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, f"{stem}.csv")
        kd.to_csv(path, index=False, encoding='utf-8-sig')
        self.ctrl.io_label.setText(f"✔ CSV: {stem}.csv ({len(kd)} rækker)")


# ── Dual panel: shared controls on left, two plots stacked on right ────────────
class DualGraphPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Left side: tab between Graf A / B controls ────────────────────────
        ctrl_container = QWidget()
        ctrl_container.setFixedWidth(640)
        ctrl_layout = QVBoxLayout(ctrl_container)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(4)

        self.ctrl_tabs = QTabWidget()
        self.ctrl_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; background:{DARK_BG}; }}
            QTabBar::tab {{ background:{PANEL_BG}; color:{SUBTEXT}; padding:5px 20px;
                            border:1px solid {BORDER}; border-bottom:none;
                            border-radius:4px 4px 0 0; }}
            QTabBar::tab:selected {{ background:{ACCENT}; color:{DARK_BG}; font-weight:bold; }}
        """)

        # Panel A controls — show sync group in its filter panel
        self.ctrl_a = ControlPanel('A')
        self.filter_a = self.ctrl_a.make_filter_panel()
        self.ctrl_a.sync_group.setVisible(True)
        tab_a = QWidget()
        tab_a.setStyleSheet(f"background:{DARK_BG};")
        tab_a_layout = QHBoxLayout(tab_a)
        tab_a_layout.setContentsMargins(0, 4, 0, 0)
        tab_a_layout.setSpacing(6)
        tab_a_layout.addWidget(self.ctrl_a)
        tab_a_layout.addWidget(self.filter_a)

        # Panel B controls — sync group visible but driven by ctrl_a choices
        self.ctrl_b = ControlPanel('B')
        self.filter_b = self.ctrl_b.make_filter_panel()
        self.ctrl_b.sync_group.setVisible(True)
        tab_b = QWidget()
        tab_b.setStyleSheet(f"background:{DARK_BG};")
        tab_b_layout = QHBoxLayout(tab_b)
        tab_b_layout.setContentsMargins(0, 4, 0, 0)
        tab_b_layout.setSpacing(6)
        tab_b_layout.addWidget(self.ctrl_b)
        tab_b_layout.addWidget(self.filter_b)

        self.ctrl_tabs.addTab(tab_a, "Graf A — Indstillinger")
        self.ctrl_tabs.addTab(tab_b, "Graf B — Indstillinger")
        ctrl_layout.addWidget(self.ctrl_tabs)

        # ── Right side: two plots stacked vertically ──────────────────────────
        plots_container = QWidget()
        plots_layout = QVBoxLayout(plots_container)
        plots_layout.setContentsMargins(0, 0, 0, 0)
        plots_layout.setSpacing(6)

        self.plot_a = PlotWidget('A')
        self.plot_b = PlotWidget('B')
        plots_layout.addWidget(self.plot_a, stretch=1)
        plots_layout.addWidget(self.plot_b, stretch=1)

        layout.addWidget(ctrl_container)
        layout.addWidget(plots_container, stretch=1)

        # ── Sync propagation guard ────────────────────────────────────────────
        self._syncing = False

        # ── Connect signals ───────────────────────────────────────────────────
        self.ctrl_a.settings_changed.connect(lambda: self._on_changed('A'))
        self.ctrl_b.settings_changed.connect(lambda: self._on_changed('B'))
        self.ctrl_a.save_btn.clicked.connect(lambda: self.ctrl_a.do_save(self.plot_a.canvas))
        self.ctrl_b.save_btn.clicked.connect(lambda: self.ctrl_b.do_save(self.plot_b.canvas))
        self.ctrl_a.csv_btn.clicked.connect(lambda: self._do_csv(self.ctrl_a, self.plot_a))
        self.ctrl_b.csv_btn.clicked.connect(lambda: self._do_csv(self.ctrl_b, self.plot_b))

        self._redraw('A')
        self._redraw('B')

    def _on_changed(self, source):
        """Called when either panel's settings change. Syncs if needed, then redraws."""
        if self._syncing:
            return
        synced_keys = self.ctrl_a.synced_keys()
        if synced_keys:
            src  = self.ctrl_a if source == 'A' else self.ctrl_b
            dest = self.ctrl_b if source == 'A' else self.ctrl_a
            self._push_sync(src, dest, synced_keys)
        self._redraw(source)
        # Also redraw the other panel since its values may have been pushed
        if synced_keys:
            other = 'B' if source == 'A' else 'A'
            self._redraw(other)

    def _push_sync(self, src, dest, keys):
        """Copy values for `keys` from src ControlPanel to dest ControlPanel."""
        self._syncing = True
        try:
            s = src.get_settings()

            if 'datasæt' in keys and s['datasæt'] in DATASET_MAP:
                dest.ds_combo.blockSignals(True)
                dest.ds_combo.setCurrentText(s['datasæt'])
                dest.ds_combo.blockSignals(False)
                dest._on_dataset_changed(s['datasæt'])

            if 'kassationsårsag' in keys:
                idx = dest.ar_combo.findText(s['kassationsårsag'])
                if idx >= 0:
                    dest.ar_combo.blockSignals(True)
                    dest.ar_combo.setCurrentIndex(idx)
                    dest.ar_combo.blockSignals(False)

            if 'x_skala' in keys and s['x_skala'] in dest.skala_btns:
                for b in dest.skala_btns.values(): b.setChecked(False)
                dest.skala_btns[s['x_skala']].setChecked(True)
                for b in dest.skala_btns.values():
                    b.setStyleSheet(dest._toggle_style(b.isChecked()))
                unit_map = {'Dage': 'Dage i cirkulation',
                            'Måneder': 'Måneder i cirkulation',
                            'År': 'År i cirkulation'}
                dest._dage_section_label.setText(unit_map[s['x_skala']])

            def _set_slider(slider, edit, value, sync_edit_fn):
                slider.blockSignals(True)
                slider.setValue(max(slider.minimum(), min(slider.maximum(), int(value))))
                slider.blockSignals(False)
                sync_edit_fn()

            if 'min_dage' in keys:
                _set_slider(dest.min_dage_slider, dest.min_dage_edit,
                            s['min_dage'], dest._sync_dage_slider_to_edit)
            if 'max_dage' in keys:
                _set_slider(dest.max_dage_slider, dest.max_dage_edit,
                            s['max_dage'], dest._sync_dage_slider_to_edit)

            if 'min_vask' in keys:
                _set_slider(dest.min_vask_slider, dest.min_vask_edit,
                            s['min_vask'],
                            lambda: dest.min_vask_edit.setText(str(dest.min_vask_slider.value())))
            if 'max_vask' in keys:
                _set_slider(dest.max_vask_slider, dest.max_vask_edit,
                            s['max_vask'],
                            lambda: dest.max_vask_edit.setText(str(dest.max_vask_slider.value())))

            if 'min_ratio' in keys:
                v = int(round(s['min_ratio'] * 100))
                _set_slider(dest.min_ratio_slider, dest.min_ratio_edit, v,
                            lambda: dest.min_ratio_edit.setText(
                                f"{dest.min_ratio_slider.value()/100:.2f}"))
            if 'max_ratio' in keys:
                v = int(round(s['max_ratio'] * 100))
                _set_slider(dest.max_ratio_slider, dest.max_ratio_edit, v,
                            lambda: dest.max_ratio_edit.setText(
                                f"{dest.max_ratio_slider.value()/100:.2f}"))

            if 'bins' in keys:
                dest.bins_slider.blockSignals(True)
                dest.bins_slider.setValue(s['bins'])
                dest.bins_slider.blockSignals(False)
                dest.bins_val_lbl.setText(str(s['bins']))

            if 'log_color' in keys:
                dest.log_cb.blockSignals(True)
                dest.log_cb.setChecked(s['log_color'])
                dest.log_cb.blockSignals(False)
            if 'vmin' in keys:
                dest.vmin_slider.blockSignals(True)
                dest.vmin_slider.setValue(int(s['vmin'] * 10))
                dest.vmin_slider.blockSignals(False)
                dest.vmin_val_lbl.setText(f"{s['vmin']:.1f}")

            if 'ref_lines' in keys:
                for lbl, cb in dest.ref_cbs.items():
                    cb.blockSignals(True)
                    cb.setChecked(lbl in s['ref_lines'])
                    cb.blockSignals(False)

            if 'show_percentiles' in keys:
                for lbl, cb in dest.pct_cbs.items():
                    cb.blockSignals(True)
                    cb.setChecked(lbl in s.get('show_percentiles', []))
                    cb.blockSignals(False)

        finally:
            self._syncing = False

    def _redraw(self, letter):
        ctrl = self.ctrl_a if letter == 'A' else self.ctrl_b
        plot = self.plot_a  if letter == 'A' else self.plot_b
        s = ctrl.get_settings()
        plot.redraw(s, DATASET_MAP[s['datasæt']])

    def _do_csv(self, ctrl, plot_widget):
        kd = plot_widget._last_filtered
        if kd is None: return
        s = ctrl.get_settings()
        raw = ctrl.folder_edit.text().strip()
        stem = raw.replace(' ', '_') if raw else \
            f"{s['datasæt']}_{s['kassationsårsag']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_')
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, f"{stem}.csv")
        kd.to_csv(path, index=False, encoding='utf-8-sig')
        ctrl.io_label.setText(f"✔ CSV: {stem}.csv ({len(kd)} rækker)")


# ── Main window ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Histogram — Produktcirkulation")
        self.resize(1400, 820)
        self.setStyleSheet(f"QMainWindow {{ background:{DARK_BG}; }}")

        central = QWidget()
        central.setStyleSheet(f"background:{DARK_BG};")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ── Top bar ────────────────────────────────────────────────────
        top = QHBoxLayout()
        title = styled_label("  2D Histogram — Produktcirkulation", bold=True, size=14, color=ACCENT)
        top.addWidget(title)
        top.addStretch()

        self.view_btn_1 = self._top_btn("1 Graf")
        self.view_btn_2 = self._top_btn("2 Grafer")
        self.view_btn_1.setChecked(True)
        self.view_btn_1.setStyleSheet(self._top_btn_style(True))
        self.view_btn_2.setStyleSheet(self._top_btn_style(False))
        top.addWidget(self.view_btn_1)
        top.addWidget(self.view_btn_2)

        if DEMO_MODE:
            demo_lbl = styled_label("  ⚠ DEMO-tilstand (ingen dataloader fundet)  ", color=DANGER, size=10)
            top.addWidget(demo_lbl)

        main_layout.addLayout(top)
        main_layout.addWidget(hr())

        # ── Single graph: tabbed A / B ─────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; background:{DARK_BG}; }}
            QTabBar::tab {{ background:{PANEL_BG}; color:{SUBTEXT}; padding:6px 18px;
                            border:1px solid {BORDER}; border-bottom:none; border-radius:4px 4px 0 0; }}
            QTabBar::tab:selected {{ background:{ACCENT}; color:{DARK_BG}; font-weight:bold; }}
        """)
        self.panel_a = GraphPanel('A')
        self.panel_b = GraphPanel('B')
        self.tabs.addTab(self.panel_a, "Graf A")
        self.tabs.addTab(self.panel_b, "Graf B")

        # ── Dual graph: shared controls left, two plots stacked right ──
        self.dual_panel = DualGraphPanel()

        self.stack = QWidget()
        stack_layout = QVBoxLayout(self.stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.addWidget(self.tabs)
        stack_layout.addWidget(self.dual_panel)
        self.dual_panel.hide()

        main_layout.addWidget(self.stack)

        self.view_btn_1.clicked.connect(lambda: self._set_view(1))
        self.view_btn_2.clicked.connect(lambda: self._set_view(2))

    def _set_view(self, n):
        self.view_btn_1.setChecked(n == 1)
        self.view_btn_2.setChecked(n == 2)
        self.view_btn_1.setStyleSheet(self._top_btn_style(n == 1))
        self.view_btn_2.setStyleSheet(self._top_btn_style(n == 2))
        self.tabs.setVisible(n == 1)
        self.dual_panel.setVisible(n == 2)

    def _top_btn(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet(self._top_btn_style(False))
        return btn

    def _top_btn_style(self, active):
        bg = ACCENT if active else "#13131f"
        col = DARK_BG if active else TEXT
        return (f"QPushButton {{ background:{bg}; color:{col}; border:1px solid {BORDER}; "
                f"border-radius:5px; padding:5px 16px; font-weight:{'bold' if active else 'normal'}; }}"
                f"QPushButton:hover {{ background:{ACCENT}; color:{DARK_BG}; }}")


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(DARK_BG))
    palette.setColor(QPalette.WindowText,      QColor(TEXT))
    palette.setColor(QPalette.Base,            QColor("#13131f"))
    palette.setColor(QPalette.AlternateBase,   QColor(PANEL_BG))
    palette.setColor(QPalette.ToolTipBase,     QColor(TEXT))
    palette.setColor(QPalette.ToolTipText,     QColor(DARK_BG))
    palette.setColor(QPalette.Text,            QColor(TEXT))
    palette.setColor(QPalette.Button,          QColor(PANEL_BG))
    palette.setColor(QPalette.ButtonText,      QColor(TEXT))
    palette.setColor(QPalette.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor(DARK_BG))
    app.setPalette(palette)

    splash = LoadingScreen()
    splash.show()
    app.processEvents()

    def step1_data():
        splash.set_status("Indlæser data…")
        app.processEvents()
        global DEMO_MODE
        global samlet_df, skjorte_data, shorts_data, bukse_data, tshirt_data
        global langærmet_data, jakke_data, fleece_data, overall_data
        global forklæde_data, kittel_data, busseron_data, kokkejakke_data, andre_data

        try:
            from dataloader import samlet_df as _s
            from dataloader import (
                skjorte_data as _sk, shorts_data as _sh, bukse_data as _bu,
                tshirt_data as _ts, langærmet_data as _la, jakke_data as _ja,
                fleece_data as _fl, overall_data as _ov, forklæde_data as _fo,
                kittel_data as _ki, busseron_data as _bs,
                kokkejakke_data as _ko, andre_data as _an,
            )
            samlet_df = _s; skjorte_data = _sk; shorts_data = _sh
            bukse_data = _bu; tshirt_data = _ts; langærmet_data = _la
            jakke_data = _ja; fleece_data = _fl; overall_data = _ov
            forklæde_data = _fo; kittel_data = _ki; busseron_data = _bs
            kokkejakke_data = _ko; andre_data = _an
            DEMO_MODE = False
        except ImportError:
            import pandas as pd
            print("⚠  dataloader not found — running in DEMO mode with synthetic data.")
            DEMO_MODE = True
            rng = np.random.default_rng(42)
            def _make_df(n=3000):
                dage    = rng.integers(30, 2800, n)
                vask    = (dage / 365.25 * rng.uniform(10, 60, n)).astype(int)
                ratio   = vask / (dage / 30.437)
                årsager = rng.choice(['Slidt', 'Beskadiget', 'Forældet', 'Andet'], n)
                return pd.DataFrame({'Dage i cirkulation': dage,
                                     'Total antal vask':   vask,
                                     'Vask per måned':     ratio,
                                     'Kassationsårsag (ui)': årsager})
            samlet_df      = _make_df(8000)
            skjorte_data   = _make_df(1200); shorts_data     = _make_df(800)
            bukse_data     = _make_df(900);  tshirt_data     = _make_df(1100)
            langærmet_data = _make_df(600);  jakke_data      = _make_df(500)
            fleece_data    = _make_df(400);  overall_data    = _make_df(300)
            forklæde_data  = _make_df(350);  kittel_data     = _make_df(450)
            busseron_data  = _make_df(250);  kokkejakke_data = _make_df(200)
            andre_data     = _make_df(700)

        DATASET_MAP.update({
            'Samlet':    samlet_df,      'Skjorte':    skjorte_data,
            'Shorts':    shorts_data,    'Bukser':     bukse_data,
            'T-shirt':   tshirt_data,    'Langærmet':  langærmet_data,
            'Jakke':     jakke_data,     'Fleece':     fleece_data,
            'Forklæde':  forklæde_data,  'Kittel':     kittel_data,
            'Busseron':  busseron_data,  'Kokkejakke': kokkejakke_data,
            'Overall':   overall_data,   'Andet':      andre_data,
        })
        QTimer.singleShot(0, step2_build)

    def step2_build():
        splash.set_status("Bygger brugerfladen…")
        app.processEvents()
        win = MainWindow()
        app._main_win = win
        splash.set_status("Klar!")
        app.processEvents()
        QTimer.singleShot(350, lambda: _show(win))

    def _show(win):
        splash.close()
        win.show()

    # Kick off after the splash has fully painted
    QTimer.singleShot(50, step1_data)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()