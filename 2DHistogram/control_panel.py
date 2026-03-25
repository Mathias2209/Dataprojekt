# control_panel.py — ControlPanel (settings) and its filter side-panel
# ─────────────────────────────────────────────────────────────────────────────
# This file owns all the left-panel controls: dataset selector, kassationsårsag,
# graftype, bins, smoothing, log toggles, load/save/delete, and the sync group.
# It also owns make_filter_panel() which builds the right-panel filter controls.

import os
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QCheckBox, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QButtonGroup, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from config import (
    PANEL_BG, DARK_BG, BORDER, ACCENT, TEXT, SUBTEXT, SUCCESS, DANGER, INFO,
    SCALE_CONFIG, REF_LINE_DEFS, REF_COLORS, RATIO_COL,
    SAVE_DIR, DEFAULT_MAX_DAGE, DEFAULT_MAX_VASK, DATASET_MAP,
)
from widgets import (
    styled_label, hr, styled_btn, toggle_style, style_combo,
    make_slider_with_edit, make_slider_with_label, get_saved_folders,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_arsager(df) -> list:
    return ['Alle'] + sorted(df['Kassationsårsag (ui)'].dropna().unique().tolist())


def ratio_range(df) -> tuple:
    import numpy as np
    if RATIO_COL not in df.columns:
        return 0.0, 10.0
    col = df[RATIO_COL].replace([np.inf, -np.inf], float('nan')).dropna()
    if len(col) == 0:
        return 0.0, 10.0
    return 0.0, round(float(col.quantile(0.999)), 2)


# ── ControlPanel ──────────────────────────────────────────────────────────────

class ControlPanel(QScrollArea):
    """
    Left panel: dataset, kassationsårsag, graftype, bins, log toggles,
    load/save section, and (in 2-graf mode) the sync group.
    """
    settings_changed = pyqtSignal()

    def __init__(self, letter: str, parent=None):
        super().__init__(parent)
        self.letter = letter
        self.setWidgetResizable(True)
        self.setFixedWidth(310)
        self.setStyleSheet(
            f"QScrollArea {{ background:{PANEL_BG}; border:1px solid {BORDER}; border-radius:8px; }}"
            f"QScrollBar:vertical {{ background:{DARK_BG}; width:8px; border-radius:4px; }}"
            f"QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:4px; }}"
        )

        container = QWidget()
        container.setStyleSheet(f"background:{PANEL_BG};")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(styled_label(f"Graf {letter} — Indstillinger",
                                      bold=True, size=12, color=ACCENT))
        layout.addWidget(hr())

        # ── Load / Delete ─────────────────────────────────────────────────────
        layout.addWidget(styled_label("📂 Indlæs / Slet", bold=True, color=INFO))
        self.load_combo = QComboBox()
        style_combo(self.load_combo)
        self._refresh_saved()
        row_load = QHBoxLayout()
        self.load_btn    = styled_btn("Indlæs", INFO)
        self.refresh_btn = styled_btn("🔄", SUBTEXT, w=36)
        self.delete_btn  = styled_btn("🗑",    DANGER,  w=36)
        row_load.addWidget(self.load_btn)
        row_load.addWidget(self.refresh_btn)
        row_load.addWidget(self.delete_btn)
        layout.addWidget(self.load_combo)
        layout.addLayout(row_load)
        self.io_label = styled_label("", color=SUCCESS)
        layout.addWidget(self.io_label)
        layout.addWidget(hr())

        # ── Dataset & kassationsårsag ─────────────────────────────────────────
        layout.addWidget(styled_label("Datasæt", bold=True))
        self.ds_combo = QComboBox()
        style_combo(self.ds_combo)
        for name in DATASET_MAP:
            self.ds_combo.addItem(name)
        layout.addWidget(self.ds_combo)

        layout.addWidget(styled_label("Kassationsårsag", bold=True))
        self.ar_combo = QComboBox()
        style_combo(self.ar_combo)
        self._update_arsager()
        layout.addWidget(self.ar_combo)

        # ── Graftype ──────────────────────────────────────────────────────────
        layout.addWidget(styled_label("Graftype", bold=True))
        self.plot_type_combo = QComboBox()
        style_combo(self.plot_type_combo)
        for pt in ['Begge', '2D Histogram', 'Overdødelighed']:
            self.plot_type_combo.addItem(pt)
        layout.addWidget(self.plot_type_combo)
        layout.addWidget(hr())

        # ── Bins ──────────────────────────────────────────────────────────────
        layout.addWidget(styled_label("Bins", bold=True))
        self.bins_slider, bins_lbl = make_slider_with_label(60, 5, 150)
        self.bins_val_lbl = bins_lbl
        r_bins = QHBoxLayout()
        r_bins.addWidget(self.bins_slider)
        r_bins.addWidget(bins_lbl)
        layout.addLayout(r_bins)

        layout.addWidget(styled_label("Glatning (Overdødelighed)", bold=True))
        self.smooth_slider, smooth_lbl = make_slider_with_label(15, 2, 60)
        self.smooth_val_lbl = smooth_lbl
        r_sm = QHBoxLayout()
        r_sm.addWidget(self.smooth_slider)
        r_sm.addWidget(smooth_lbl)
        layout.addLayout(r_sm)

        # ── Checkboxes ────────────────────────────────────────────────────────
        self.log_cb = QCheckBox("Logaritmisk farveskala (2D)")
        self.log_cb.setChecked(True)
        self.log_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(self.log_cb)

        self.log_y_cb = QCheckBox("Log y-akse (Overdødelighed)")
        self.log_y_cb.setChecked(False)
        self.log_y_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(self.log_y_cb)

        self.show_reg_cb = QCheckBox("Vis regressionsmodel")
        self.show_reg_cb.setChecked(True)
        self.show_reg_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(self.show_reg_cb)

        layout.addWidget(styled_label("Farve minimum (2D)"))
        self.vmin_slider, vmin_lbl = make_slider_with_label(1, 1, 200, scale=10.0)
        self.vmin_val_lbl = vmin_lbl
        r_vm = QHBoxLayout()
        r_vm.addWidget(self.vmin_slider)
        r_vm.addWidget(vmin_lbl)
        layout.addLayout(r_vm)
        layout.addWidget(hr())

        # ── Note / folder / save ──────────────────────────────────────────────
        layout.addWidget(styled_label("Note (valgfrit)", bold=True))
        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(60)
        self.note_edit.setStyleSheet(
            f"background:#13131f; color:{TEXT}; border:1px solid {BORDER}; border-radius:4px;"
        )
        layout.addWidget(self.note_edit)

        layout.addWidget(styled_label("Mappenavn", bold=True))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Lad stå tomt for auto-navn...")
        self.folder_edit.setStyleSheet(
            f"background:#13131f; color:{TEXT}; border:1px solid {BORDER};"
            f" border-radius:4px; padding:4px;"
        )
        layout.addWidget(self.folder_edit)

        row_save = QHBoxLayout()
        self.save_btn = styled_btn("💾 Gem", SUCCESS)
        self.csv_btn  = styled_btn("📄 CSV", SUBTEXT)
        row_save.addWidget(self.save_btn)
        row_save.addWidget(self.csv_btn)
        layout.addLayout(row_save)
        layout.addStretch()
        self.setWidget(container)

        # ── Signals ───────────────────────────────────────────────────────────
        self.ds_combo.currentTextChanged.connect(self._on_dataset_changed)
        self.ar_combo.currentTextChanged.connect(self.settings_changed)
        self.plot_type_combo.currentTextChanged.connect(self.settings_changed)
        self.bins_slider.valueChanged.connect(
            lambda v: [bins_lbl.setText(str(v)), self.settings_changed.emit()])
        self.smooth_slider.valueChanged.connect(
            lambda v: [smooth_lbl.setText(str(v)), self.settings_changed.emit()])
        self.vmin_slider.valueChanged.connect(
            lambda v: [vmin_lbl.setText(f"{v/10:.1f}"), self.settings_changed.emit()])
        self.log_cb.stateChanged.connect(self.settings_changed)
        self.log_y_cb.stateChanged.connect(self.settings_changed)
        self.show_reg_cb.stateChanged.connect(self.settings_changed)

        self.load_btn.clicked.connect(self._do_load)
        self.refresh_btn.clicked.connect(self._refresh_saved)
        self.delete_btn.clicked.connect(self._do_delete)

    # ── Filter panel factory ──────────────────────────────────────────────────

    def make_filter_panel(self) -> QScrollArea:
        """Build and return the right-side filter panel for this control panel."""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setFixedWidth(310)
        panel.setStyleSheet(
            f"QScrollArea {{ background:{PANEL_BG}; border:1px solid {BORDER}; border-radius:8px; }}"
            f"QScrollBar:vertical {{ background:{DARK_BG}; width:8px; border-radius:4px; }}"
            f"QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:4px; }}"
        )
        container = QWidget()
        container.setStyleSheet(f"background:{PANEL_BG};")
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(styled_label(f"Graf {self.letter} — Filtrering",
                                      bold=True, size=12, color=ACCENT))
        layout.addWidget(hr())

        # X-skala buttons
        layout.addWidget(styled_label("X-akse skala", bold=True))
        skala_row = QHBoxLayout()
        self.skala_btns: dict[str, QPushButton] = {}
        self.skala_group = QButtonGroup()
        for i, s in enumerate(['Dage', 'Måneder', 'År']):
            btn = QPushButton(s)
            btn.setCheckable(True)
            btn.setChecked(s == 'Dage')
            btn.setStyleSheet(toggle_style(s == 'Dage'))
            self.skala_btns[s] = btn
            self.skala_group.addButton(btn, i)
            skala_row.addWidget(btn)
        layout.addLayout(skala_row)
        self.skala_group.buttonClicked.connect(self._on_skala_changed)
        layout.addWidget(hr())

        # Dage sliders
        df       = DATASET_MAP[self.ds_combo.currentText()]
        dage_max = int(df['Dage i cirkulation'].max()) + 100
        self._dage_section_label = styled_label("Dage i cirkulation", bold=True)
        layout.addWidget(self._dage_section_label)

        self.min_dage_slider, self.min_dage_edit = make_slider_with_edit(
            0, 0, dage_max, step=50)
        self.max_dage_slider, self.max_dage_edit = make_slider_with_edit(
            min(DEFAULT_MAX_DAGE, dage_max), 0, dage_max, step=50)
        for lbl_txt, sl, ed in [("Min", self.min_dage_slider, self.min_dage_edit),
                                 ("Max", self.max_dage_slider, self.max_dage_edit)]:
            r = QHBoxLayout()
            r.addWidget(styled_label(lbl_txt))
            r.addWidget(sl, stretch=1)
            r.addWidget(ed)
            layout.addLayout(r)
        layout.addWidget(hr())

        # Vask sliders
        vask_max = int(df['Total antal vask'].max()) + 10
        layout.addWidget(styled_label("Total antal vask", bold=True))
        self.min_vask_slider, self.min_vask_edit = make_slider_with_edit(0, 0, vask_max)
        self.max_vask_slider, self.max_vask_edit = make_slider_with_edit(
            DEFAULT_MAX_VASK, 0, vask_max)
        for lbl_txt, sl, ed in [("Min", self.min_vask_slider, self.min_vask_edit),
                                 ("Max", self.max_vask_slider, self.max_vask_edit)]:
            r = QHBoxLayout()
            r.addWidget(styled_label(lbl_txt))
            r.addWidget(sl, stretch=1)
            r.addWidget(ed)
            layout.addLayout(r)

        # Ratio group
        rmin, rmax = ratio_range(df)
        self.ratio_group = QGroupBox("Vask per måned (ratio)")
        self.ratio_group.setStyleSheet(
            f"QGroupBox {{ color:{INFO}; font-weight:bold; border:1px solid {BORDER};"
            f" border-radius:6px; margin-top:8px; padding-top:8px; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:8px; }}"
        )
        ratio_layout = QVBoxLayout()
        self.min_ratio_slider, self.min_ratio_edit = make_slider_with_edit(
            int(rmin * 100), int(rmin * 100), int(rmax * 100), fmt='ratio')
        self.max_ratio_slider, self.max_ratio_edit = make_slider_with_edit(
            int(rmax * 100), int(rmin * 100), int(rmax * 100), fmt='ratio')
        for lbl_txt, sl, ed in [("Min", self.min_ratio_slider, self.min_ratio_edit),
                                 ("Max", self.max_ratio_slider, self.max_ratio_edit)]:
            r = QHBoxLayout()
            r.addWidget(styled_label(lbl_txt))
            r.addWidget(sl, stretch=1)
            r.addWidget(ed)
            ratio_layout.addLayout(r)
        self.ratio_group.setLayout(ratio_layout)
        layout.addWidget(self.ratio_group)
        self.ratio_group.setVisible(RATIO_COL in df.columns)

        layout.addWidget(hr())

        # Reference lines
        layout.addWidget(styled_label("Referencelinjer", bold=True))
        self.ref_cbs: dict[str, QCheckBox] = {}
        for i, (_, lbl) in enumerate(REF_LINE_DEFS):
            cb = QCheckBox(lbl)
            cb.setStyleSheet(
                f"color:{REF_COLORS[i]}; background:transparent; font-weight:bold;"
            )
            cb.stateChanged.connect(self.settings_changed)
            self.ref_cbs[lbl] = cb
            layout.addWidget(cb)

        layout.addWidget(hr())

        # Percentile lines
        layout.addWidget(styled_label("Kvantillinjer", bold=True))
        self.pct_cbs: dict[str, QCheckBox] = {}
        for lbl in ['25%', 'Median', '75%']:
            cb = QCheckBox(lbl)
            cb.setChecked(True)
            cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
            cb.stateChanged.connect(self.settings_changed)
            self.pct_cbs[lbl] = cb
            layout.addWidget(cb)

        layout.addWidget(hr())

        # Overdødelighed toggles
        layout.addWidget(styled_label("Overdødelighed — vis", bold=True))

        self.show_4sigma_cb = QCheckBox("4σ-tærskel")
        self.show_4sigma_cb.setChecked(True)
        self.show_4sigma_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self.show_4sigma_cb.stateChanged.connect(self.settings_changed)
        layout.addWidget(self.show_4sigma_cb)

        self.show_2sigma_cb = QCheckBox("2σ-tærskel")
        self.show_2sigma_cb.setChecked(True)
        self.show_2sigma_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self.show_2sigma_cb.stateChanged.connect(self.settings_changed)
        layout.addWidget(self.show_2sigma_cb)

        self.show_survival_cb = QCheckBox("Overlevelseskurve")
        self.show_survival_cb.setChecked(True)
        self.show_survival_cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self.show_survival_cb.stateChanged.connect(self.settings_changed)
        layout.addWidget(self.show_survival_cb)

        layout.addWidget(hr())

        # Sync group (hidden until 2-graf mode)
        self.sync_group = QGroupBox("🔗 Synkroniser A↔B")
        self.sync_group.setStyleSheet(
            f"QGroupBox {{ color:{ACCENT}; font-weight:bold; border:1px solid {BORDER};"
            f" border-radius:6px; margin-top:8px; padding-top:8px; background:{PANEL_BG}; }}"
            f"QGroupBox::title {{ subcontrol-origin:margin; left:8px; }}"
        )
        sync_layout = QVBoxLayout()
        sync_layout.setSpacing(4)
        self.sync_all_cb = QCheckBox("Alle")
        self.sync_all_cb.setStyleSheet(
            f"color:{INFO}; font-weight:bold; background:transparent;")
        sync_layout.addWidget(self.sync_all_cb)

        SYNC_GROUPS = [
            ("Datasæt",              ['datasæt']),
            ("Kassationsårsag",      ['kassationsårsag']),
            ("X-akse skala",         ['x_skala']),
            ("Dage i cirkulation",   ['min_dage', 'max_dage']),
            ("Antal vask",           ['min_vask', 'max_vask']),
            ("Vask per måned ratio", ['min_ratio', 'max_ratio']),
            ("Graftype & Bins",      ['plot_type', 'bins', 'smooth']),
            ("Farveskala & Linjer",  ['log_color', 'vmin', 'log_y_hist',
                                      'show_reg', 'ref_lines', 'show_percentiles']),
        ]
        self._sync_key_map = SYNC_GROUPS
        self.sync_cbs: dict[str, QCheckBox] = {}
        for label, _ in SYNC_GROUPS:
            cb = QCheckBox(label)
            cb.setStyleSheet(f"color:{TEXT}; background:transparent;")
            sync_layout.addWidget(cb)
            self.sync_cbs[label] = cb
        self.sync_group.setLayout(sync_layout)
        self.sync_group.setVisible(False)
        layout.addWidget(self.sync_group)

        self.sync_all_cb.stateChanged.connect(self._on_sync_all_changed)
        for cb in self.sync_cbs.values():
            cb.stateChanged.connect(self._on_sync_individual_changed)

        layout.addStretch()
        panel.setWidget(container)
        self.filter_panel = panel

        # Wire sliders ↔ edits
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
        for sl in [self.min_dage_slider, self.max_dage_slider,
                   self.min_vask_slider,  self.max_vask_slider,
                   self.min_ratio_slider, self.max_ratio_slider]:
            sl.valueChanged.connect(self.settings_changed)

        return panel

    # ── Slider ↔ edit sync helpers ────────────────────────────────────────────

    def _current_skala(self) -> str:
        return next((s for s, b in self.skala_btns.items() if b.isChecked()), 'Dage')

    def _days_to_display(self, days: int) -> str:
        skala = self._current_skala()
        div   = SCALE_CONFIG[skala]['divisor']
        if skala == 'Dage':    return str(int(round(days / div)))
        if skala == 'Måneder': return f"{days / div:.1f}"
        return f"{days / div:.2f}"

    def _display_to_days(self, text: str):
        try:
            return int(round(float(text) * SCALE_CONFIG[self._current_skala()]['divisor']))
        except (ValueError, KeyError):
            return None

    def _sync_dage_slider_to_edit(self):
        self.min_dage_edit.setText(self._days_to_display(self.min_dage_slider.value()))
        self.max_dage_edit.setText(self._days_to_display(self.max_dage_slider.value()))

    def _sync_dage_edit_to_slider(self, edit, slider):
        days = self._display_to_days(edit.text())
        if days is not None:
            slider.setValue(max(slider.minimum(), min(slider.maximum(), days)))
        else:
            edit.setText(self._days_to_display(slider.value()))

    def _sync_int_slider_to_edit(self, v, edit):
        edit.setText(str(v))

    def _sync_int_edit_to_slider(self, edit, slider):
        try:
            v = max(slider.minimum(),
                    min(slider.maximum(), int(round(float(edit.text())))))
            slider.setValue(v)
        except ValueError:
            edit.setText(str(slider.value()))

    def _sync_ratio_slider_to_edit(self, v, edit):
        edit.setText(f"{v / 100:.2f}")

    def _sync_ratio_edit_to_slider(self, edit, slider):
        try:
            v = max(slider.minimum(),
                    min(slider.maximum(), int(round(float(edit.text()) * 100))))
            slider.setValue(v)
        except ValueError:
            edit.setText(f"{slider.value() / 100:.2f}")

    # ── Sync group helpers ────────────────────────────────────────────────────

    def _on_sync_all_changed(self, state):
        checked = state == Qt.Checked
        for cb in self.sync_cbs.values():
            cb.blockSignals(True); cb.setChecked(checked); cb.blockSignals(False)

    def _on_sync_individual_changed(self):
        all_on = all(cb.isChecked() for cb in self.sync_cbs.values())
        self.sync_all_cb.blockSignals(True)
        self.sync_all_cb.setChecked(all_on)
        self.sync_all_cb.blockSignals(False)

    def synced_keys(self) -> set:
        keys = set()
        for label, key_list in self._sync_key_map:
            if self.sync_cbs[label].isChecked():
                keys.update(key_list)
        return keys

    # ── Skala change ──────────────────────────────────────────────────────────

    def _on_skala_changed(self, _btn):
        for s, b in self.skala_btns.items():
            b.setStyleSheet(toggle_style(b.isChecked()))
        self._dage_section_label.setText({
            'Dage':    'Dage i cirkulation',
            'Måneder': 'Måneder i cirkulation',
            'År':      'År i cirkulation',
        }[self._current_skala()])
        self._sync_dage_slider_to_edit()
        self.settings_changed.emit()

    # ── Dataset change ────────────────────────────────────────────────────────

    def _on_dataset_changed(self, name: str):
        df = DATASET_MAP[name]
        self._update_arsager()
        dage_max = int(df['Dage i cirkulation'].max()) + 100
        self.min_dage_slider.setMaximum(dage_max)
        self.max_dage_slider.setMaximum(dage_max)
        self.max_dage_slider.setValue(min(DEFAULT_MAX_DAGE, dage_max))
        self.min_dage_slider.setValue(0)
        self._sync_dage_slider_to_edit()
        vask_max = int(df['Total antal vask'].max()) + 10
        self.min_vask_slider.setMaximum(vask_max)
        self.max_vask_slider.setMaximum(vask_max)
        self.max_vask_slider.setValue(DEFAULT_MAX_VASK)
        self.min_vask_slider.setValue(0)
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
        df      = DATASET_MAP[self.ds_combo.currentText()]
        current = self.ar_combo.currentText()
        self.ar_combo.blockSignals(True)
        self.ar_combo.clear()
        for a in get_arsager(df):
            self.ar_combo.addItem(a)
        idx = self.ar_combo.findText(current)
        self.ar_combo.setCurrentIndex(max(0, idx))
        self.ar_combo.blockSignals(False)

    # ── Load / Save / Delete ──────────────────────────────────────────────────

    def _refresh_saved(self):
        self.load_combo.blockSignals(True)
        self.load_combo.clear()
        folders = get_saved_folders()
        for f in (folders or ["(ingen gemte grafer)"]):
            self.load_combo.addItem(f)
        self.load_combo.blockSignals(False)

    def _do_load(self):
        folder = self.load_combo.currentText()
        if folder == "(ingen gemte grafer)":
            return
        try:
            with open(os.path.join(SAVE_DIR, folder, 'settings.json'),
                      encoding='utf-8') as f:
                s = json.load(f)
        except Exception as e:
            self.io_label.setText(f"Fejl: {e}"); return

        if s.get('datasæt') in DATASET_MAP:
            self.ds_combo.setCurrentText(s['datasæt'])
        if s.get('kassationsårsag'):
            idx = self.ar_combo.findText(s['kassationsårsag'])
            if idx >= 0: self.ar_combo.setCurrentIndex(idx)
        if s.get('plot_type'):
            self.plot_type_combo.setCurrentText(s['plot_type'])
        if s.get('x_skala') in self.skala_btns:
            for btn in self.skala_btns.values(): btn.setChecked(False)
            self.skala_btns[s['x_skala']].setChecked(True)
            for b in self.skala_btns.values():
                b.setStyleSheet(toggle_style(b.isChecked()))
        if s.get('bins'):   self.bins_slider.setValue(s['bins'])
        if s.get('smooth'): self.smooth_slider.setValue(s['smooth'])
        if s.get('min_dage') is not None:
            self.min_dage_slider.setValue(min(s['min_dage'], self.min_dage_slider.maximum()))
        if s.get('max_dage') is not None:
            self.max_dage_slider.setValue(min(s['max_dage'], self.max_dage_slider.maximum()))
        self._sync_dage_slider_to_edit()
        if s.get('min_vask') is not None:
            self.min_vask_slider.setValue(min(s['min_vask'], self.min_vask_slider.maximum()))
        if s.get('max_vask') is not None:
            self.max_vask_slider.setValue(min(s['max_vask'], self.max_vask_slider.maximum()))
        if s.get('log_color')   is not None: self.log_cb.setChecked(s['log_color'])
        if s.get('log_y_hist')  is not None: self.log_y_cb.setChecked(s['log_y_hist'])
        if s.get('show_reg')    is not None: self.show_reg_cb.setChecked(s['show_reg'])
        if s.get('show_4sigma') is not None: self.show_4sigma_cb.setChecked(s['show_4sigma'])
        if s.get('show_2sigma') is not None: self.show_2sigma_cb.setChecked(s['show_2sigma'])
        if s.get('show_survival') is not None: self.show_survival_cb.setChecked(s['show_survival'])
        if s.get('vmin')       is not None: self.vmin_slider.setValue(int(s['vmin'] * 10))
        if s.get('ref_lines'):
            for lbl, cb in self.ref_cbs.items():
                cb.setChecked(lbl in s['ref_lines'])
        if s.get('show_percentiles'):
            for lbl, cb in self.pct_cbs.items():
                cb.setChecked(lbl in s['show_percentiles'])
        if s.get('min_ratio') is not None:
            self.min_ratio_slider.setValue(
                int(min(s['min_ratio'] * 100, self.min_ratio_slider.maximum())))
        if s.get('max_ratio') is not None:
            self.max_ratio_slider.setValue(
                int(min(s['max_ratio'] * 100, self.max_ratio_slider.maximum())))
        self.folder_edit.setText(folder)
        md_path = os.path.join(SAVE_DIR, folder, 'README.md')
        if os.path.isfile(md_path):
            txt  = open(md_path, encoding='utf-8').read()
            note = txt.split('## Note')[-1].strip().lstrip('\n') if '## Note' in txt else ''
            self.note_edit.setPlainText(note)
        self.io_label.setText(f"✔ Indlæst: {folder}")
        self.settings_changed.emit()

    def do_save(self, canvas) -> None:
        s   = self.get_settings()
        raw = self.folder_edit.text().strip()
        folder = (raw.replace(' ', '_') if raw else
                  f"{s['datasæt']}_{s['kassationsårsag']}_"
                  f"{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_'))
        subdir = os.path.join(SAVE_DIR, folder)
        os.makedirs(subdir, exist_ok=True)
        canvas.fig.savefig(os.path.join(subdir, 'histogram.jpeg'),
                           dpi=150, bbox_inches='tight')
        s['gemt'] = datetime.now().isoformat()
        with open(os.path.join(subdir, 'settings.json'), 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        with open(os.path.join(subdir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(f"# {s['datasæt']} — {s['kassationsårsag']}\n\n"
                    f"*{datetime.now():%Y-%m-%d %H:%M:%S}*\n\n")
            note = self.note_edit.toPlainText().strip()
            if note:
                f.write(f"## Note\n\n{note}\n")
        self.io_label.setText(f"✔ Gemt: {folder}/")
        self._refresh_saved()

    def _do_delete(self):
        folder = self.load_combo.currentText()
        if folder == "(ingen gemte grafer)":
            return
        if QMessageBox.question(self, "Slet", f"Slet '{folder}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            import shutil
            try:
                shutil.rmtree(os.path.join(SAVE_DIR, folder))
                self._refresh_saved()
                self.io_label.setText(f"✔ Slettet: {folder}")
            except Exception as e:
                self.io_label.setText(f"Fejl: {e}")

    # ── Settings dict ─────────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        skala = next((s for s, b in self.skala_btns.items() if b.isChecked()), 'Dage')
        return {
            'datasæt':          self.ds_combo.currentText(),
            'kassationsårsag':  self.ar_combo.currentText(),
            'plot_type':        self.plot_type_combo.currentText(),
            'bins':             self.bins_slider.value(),
            'smooth':           self.smooth_slider.value(),
            'log_color':        self.log_cb.isChecked(),
            'log_y_hist':       self.log_y_cb.isChecked(),
            'show_reg':         self.show_reg_cb.isChecked(),
            'show_4sigma':      self.show_4sigma_cb.isChecked(),
            'show_2sigma':      self.show_2sigma_cb.isChecked(),
            'show_survival':    self.show_survival_cb.isChecked(),
            'vmin':             self.vmin_slider.value() / 10.0,
            'ref_lines':        [l for l, cb in self.ref_cbs.items() if cb.isChecked()],
            'show_percentiles': [l for l, cb in self.pct_cbs.items() if cb.isChecked()],
            'x_skala':          skala,
            'min_dage':         self.min_dage_slider.value(),
            'max_dage':         self.max_dage_slider.value(),
            'min_vask':         self.min_vask_slider.value(),
            'max_vask':         self.max_vask_slider.value(),
            'min_ratio':        self.min_ratio_slider.value() / 100.0,
            'max_ratio':        self.max_ratio_slider.value() / 100.0,
        }