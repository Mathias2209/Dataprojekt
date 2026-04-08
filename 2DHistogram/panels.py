# panels.py — GraphPanel (single) and DualGraphPanel (side-by-side)
# ─────────────────────────────────────────────────────────────────────────────
# These widgets wire ControlPanel + PlotWidget together and handle sync logic.

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTabWidget,
)

from config import (
    DARK_BG, PANEL_BG, SUBTEXT, BORDER, ACCENT,
    SCALE_CONFIG, SAVE_DIR, DATASET_MAP,
)
from control_panel import ControlPanel
from plot_widget import PlotWidget


# ── GraphPanel ────────────────────────────────────────────────────────────────

class GraphPanel(QWidget):
    """Single-panel view: ControlPanel + filter panel + PlotWidget side by side."""

    def __init__(self, letter: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.ctrl        = ControlPanel(letter)
        self.ctrl.make_filter_panel()
        self.plot_widget = PlotWidget(letter)

        layout.addWidget(self.ctrl)
        layout.addWidget(self.plot_widget, stretch=1)

        self.ctrl.settings_changed.connect(self.redraw)
        self.ctrl.save_btn.clicked.connect(
            lambda: self.ctrl.do_save(self.plot_widget.canvas))
        self.ctrl.csv_btn.clicked.connect(self._do_csv)
        self.redraw()

    @property
    def canvas(self):
        return self.plot_widget.canvas

    def redraw(self) -> None:
        s = self.ctrl.get_settings()
        self.plot_widget.redraw(s, DATASET_MAP[s['datasæt']])

    def _do_csv(self) -> None:
        kd = self.plot_widget._last_filtered
        if kd is None:
            return
        s   = self.ctrl.get_settings()
        raw = self.ctrl.folder_edit.text().strip()
        stem = (raw.replace(' ', '_') if raw else
                f"{s['datasæt']}_{s['kassationsårsag']}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_'))
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, f"{stem}.csv")
        kd.to_csv(path, index=False, encoding='utf-8-sig')
        self.ctrl.io_label.setText(f"✔ CSV: {stem}.csv ({len(kd)} rækker)")


# ── DualGraphPanel ────────────────────────────────────────────────────────────

class DualGraphPanel(QWidget):
    """
    Two-panel view: tabbed controls on the left, two stacked plots on the right.
    Handles cross-panel synchronisation based on the sync checkboxes in Graf A's
    filter panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Left: tabbed controls ─────────────────────────────────────────────
        ctrl_container = QWidget()
        ctrl_container.setFixedWidth(628)
        ctrl_layout = QVBoxLayout(ctrl_container)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(4)

        self.ctrl_tabs = QTabWidget()
        self.ctrl_tabs.setStyleSheet(
            f"QTabWidget::pane {{ border:none; background:{DARK_BG}; }}"
            f"QTabBar::tab {{ background:{PANEL_BG}; color:{SUBTEXT}; padding:5px 20px;"
            f" border:1px solid {BORDER}; border-bottom:none; border-radius:4px 4px 0 0; }}"
            f"QTabBar::tab:selected {{ background:{ACCENT}; color:{DARK_BG}; font-weight:bold; }}"
        )

        self.ctrl_a = ControlPanel('A')
        self.ctrl_a.make_filter_panel()
        self.ctrl_a.sync_group.setVisible(True)
        tab_a = QWidget(); tab_a.setStyleSheet(f"background:{DARK_BG};")
        ta_layout = QHBoxLayout(tab_a)
        ta_layout.setContentsMargins(0, 4, 0, 0); ta_layout.setSpacing(6)
        ta_layout.addWidget(self.ctrl_a)

        self.ctrl_b = ControlPanel('B')
        self.ctrl_b.make_filter_panel()
        self.ctrl_b.sync_group.setVisible(True)
        tab_b = QWidget(); tab_b.setStyleSheet(f"background:{DARK_BG};")
        tb_layout = QHBoxLayout(tab_b)
        tb_layout.setContentsMargins(0, 4, 0, 0); tb_layout.setSpacing(6)
        tb_layout.addWidget(self.ctrl_b)

        self.ctrl_tabs.addTab(tab_a, "Graf A — Indstillinger")
        self.ctrl_tabs.addTab(tab_b, "Graf B — Indstillinger")
        ctrl_layout.addWidget(self.ctrl_tabs)

        # ── Right: stacked plots ──────────────────────────────────────────────
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

        self._syncing = False
        self.ctrl_a.settings_changed.connect(lambda: self._on_changed('A'))
        self.ctrl_b.settings_changed.connect(lambda: self._on_changed('B'))
        self.ctrl_a.save_btn.clicked.connect(
            lambda: self.ctrl_a.do_save(self.plot_a.canvas))
        self.ctrl_b.save_btn.clicked.connect(
            lambda: self.ctrl_b.do_save(self.plot_b.canvas))
        self.ctrl_a.csv_btn.clicked.connect(
            lambda: self._do_csv(self.ctrl_a, self.plot_a))
        self.ctrl_b.csv_btn.clicked.connect(
            lambda: self._do_csv(self.ctrl_b, self.plot_b))

        self._redraw('A')
        self._redraw('B')

    # ── Sync ──────────────────────────────────────────────────────────────────

    def _on_changed(self, source: str) -> None:
        if self._syncing:
            return
        synced_keys = self.ctrl_a.synced_keys()
        if synced_keys:
            src  = self.ctrl_a if source == 'A' else self.ctrl_b
            dest = self.ctrl_b if source == 'A' else self.ctrl_a
            self._push_sync(src, dest, synced_keys)
        self._redraw(source)
        if synced_keys:
            self._redraw('B' if source == 'A' else 'A')

    def _push_sync(self, src: ControlPanel, dest: ControlPanel,
                   keys: set) -> None:
        """Copy values for `keys` from src to dest without triggering recursion."""
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
                from widgets import toggle_style
                for b in dest.skala_btns.values(): b.setChecked(False)
                dest.skala_btns[s['x_skala']].setChecked(True)
                for b in dest.skala_btns.values():
                    b.setStyleSheet(toggle_style(b.isChecked()))
                dest._dage_section_label.setText({
                    'Dage':    'Dage i cirkulation',
                    'Måneder': 'Måneder i cirkulation',
                    'År':      'År i cirkulation',
                }[s['x_skala']])

            def _set(slider, edit, value, sync_fn):
                slider.blockSignals(True)
                slider.setValue(max(slider.minimum(),
                                    min(slider.maximum(), int(value))))
                slider.blockSignals(False)
                sync_fn()

            if 'min_dage' in keys:
                _set(dest.min_dage_slider, dest.min_dage_edit,
                     s['min_dage'], dest._sync_dage_slider_to_edit)
            if 'max_dage' in keys:
                _set(dest.max_dage_slider, dest.max_dage_edit,
                     s['max_dage'], dest._sync_dage_slider_to_edit)
            if 'min_vask' in keys:
                _set(dest.min_vask_slider, dest.min_vask_edit, s['min_vask'],
                     lambda: dest.min_vask_edit.setText(
                         str(dest.min_vask_slider.value())))
            if 'max_vask' in keys:
                _set(dest.max_vask_slider, dest.max_vask_edit, s['max_vask'],
                     lambda: dest.max_vask_edit.setText(
                         str(dest.max_vask_slider.value())))
            if 'min_ratio' in keys:
                _set(dest.min_ratio_slider, dest.min_ratio_edit,
                     int(round(s['min_ratio'] * 100)),
                     lambda: dest.min_ratio_edit.setText(
                         f"{dest.min_ratio_slider.value()/100:.2f}"))
            if 'max_ratio' in keys:
                _set(dest.max_ratio_slider, dest.max_ratio_edit,
                     int(round(s['max_ratio'] * 100)),
                     lambda: dest.max_ratio_edit.setText(
                         f"{dest.max_ratio_slider.value()/100:.2f}"))
            if 'bins' in keys:
                dest.bins_slider.blockSignals(True)
                dest.bins_slider.setValue(s['bins'])
                dest.bins_slider.blockSignals(False)
                dest.bins_val_lbl.setText(str(s['bins']))
            if 'smooth' in keys:
                dest.smooth_slider.blockSignals(True)
                dest.smooth_slider.setValue(s['smooth'])
                dest.smooth_slider.blockSignals(False)
                dest.smooth_val_lbl.setText(str(s['smooth']))
            if 'plot_type' in keys:
                dest.plot_type_combo.blockSignals(True)
                dest.plot_type_combo.setCurrentText(s['plot_type'])
                dest.plot_type_combo.blockSignals(False)
            for attr, key in [('log_cb',      'log_color'),
                               ('log_y_cb',    'log_y_hist'),
                               ('show_reg_cb', 'show_reg')]:
                if key in keys:
                    w = getattr(dest, attr)
                    w.blockSignals(True); w.setChecked(s[key]); w.blockSignals(False)
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

    # ── Redraw & CSV ──────────────────────────────────────────────────────────

    def _redraw(self, letter: str) -> None:
        ctrl = self.ctrl_a if letter == 'A' else self.ctrl_b
        plot = self.plot_a  if letter == 'A' else self.plot_b
        s    = ctrl.get_settings()
        plot.redraw(s, DATASET_MAP[s['datasæt']])

    def _do_csv(self, ctrl: ControlPanel, plot_widget: PlotWidget) -> None:
        kd = plot_widget._last_filtered
        if kd is None:
            return
        s   = ctrl.get_settings()
        raw = ctrl.folder_edit.text().strip()
        stem = (raw.replace(' ', '_') if raw else
                f"{s['datasæt']}_{s['kassationsårsag']}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_'))
        os.makedirs(SAVE_DIR, exist_ok=True)
        kd.to_csv(os.path.join(SAVE_DIR, f"{stem}.csv"),
                  index=False, encoding='utf-8-sig')
        ctrl.io_label.setText(f"✔ CSV: {stem}.csv ({len(kd)} rækker)")