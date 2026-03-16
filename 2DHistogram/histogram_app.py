# histogram_app.py — MainWindow, entry point, and bootstrap logic
# ─────────────────────────────────────────────────────────────────────────────
# Run with:  python histogram_app.py
# Requires:  pip install PyQt5 matplotlib numpy pandas scipy pyarrow
#
# File layout:
#   histogram_app.py   ← you are here (MainWindow + main)
#   config.py          ← colours, constants, DATASET_MAP
#   data_cache.py      ← load / cache / invalidate data
#   widgets.py         ← styled_label, hr, button/slider helpers
#   loading_screen.py  ← animated splash screen
#   plot_canvas.py     ← PlotCanvas + draw_histogram()
#   plot_widget.py     ← PlotWidget (canvas + header)
#   control_panel.py   ← ControlPanel + make_filter_panel()
#   panels.py          ← GraphPanel, DualGraphPanel

import sys

import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPalette

from config import DARK_BG, PANEL_BG, ACCENT, TEXT, SUBTEXT, BORDER, DANGER, INFO
from data_cache import load_data, invalidate_cache
from loading_screen import LoadingScreen
from widgets import styled_label, hr, top_btn, top_btn_style
from panels import GraphPanel, DualGraphPanel


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, demo_mode: bool = False, on_refresh=None):
        super().__init__()
        self._demo_mode  = demo_mode
        self._on_refresh = on_refresh

        self.setWindowTitle("2D Histogram — Produktcirkulation")
        self.resize(1400, 820)
        self.setStyleSheet(f"QMainWindow {{ background:{DARK_BG}; }}")

        central = QWidget()
        central.setStyleSheet(f"background:{DARK_BG};")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ── Top bar ────────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.addWidget(styled_label("  2D Histogram — Produktcirkulation",
                                   bold=True, size=14, color=ACCENT))
        top.addStretch()

        self.view_btn_1 = top_btn("1 Graf",  active=True)
        self.view_btn_2 = top_btn("2 Grafer", active=False)
        top.addWidget(self.view_btn_1)
        top.addWidget(self.view_btn_2)

        refresh_btn = QPushButton("🔄  Opdater data")
        refresh_btn.setToolTip("Slet cache og genindlæs fra dataloader, derefter genstart")
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background:#13131f; color:{INFO};"
            f" border:1px solid {BORDER}; border-radius:5px; padding:5px 14px; }}"
            f"QPushButton:hover {{ background:{INFO}; color:{DARK_BG}; }}"
        )
        if on_refresh:
            refresh_btn.clicked.connect(on_refresh)
        top.addWidget(refresh_btn)

        if demo_mode:
            top.addWidget(styled_label("  ⚠ DEMO-tilstand  ", color=DANGER, size=10))

        main_layout.addLayout(top)
        main_layout.addWidget(hr())

        # ── Single-graph tabs (Graf A / Graf B) ───────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabWidget::pane {{ border:none; background:{DARK_BG}; }}"
            f"QTabBar::tab {{ background:{PANEL_BG}; color:{SUBTEXT}; padding:6px 18px;"
            f" border:1px solid {BORDER}; border-bottom:none; border-radius:4px 4px 0 0; }}"
            f"QTabBar::tab:selected {{ background:{ACCENT}; color:{DARK_BG}; font-weight:bold; }}"
        )
        self.panel_a = GraphPanel('A')
        self.panel_b = GraphPanel('B')
        self.tabs.addTab(self.panel_a, "Graf A")
        self.tabs.addTab(self.panel_b, "Graf B")

        # ── Dual-graph panel ──────────────────────────────────────────────────
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

    def _set_view(self, n: int) -> None:
        self.view_btn_1.setChecked(n == 1)
        self.view_btn_2.setChecked(n == 2)
        self.view_btn_1.setStyleSheet(top_btn_style(n == 1))
        self.view_btn_2.setStyleSheet(top_btn_style(n == 2))
        self.tabs.setVisible(n == 1)
        self.dual_panel.setVisible(n == 2)


# ── Application entry point ───────────────────────────────────────────────────

def _apply_dark_palette(app: QApplication) -> None:
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


def main() -> None:
    app = QApplication(sys.argv)
    _apply_dark_palette(app)

    splash = LoadingScreen()
    splash.show()
    app.processEvents()

    def step1_data(force_refresh: bool = False) -> None:
        real_data = load_data(force_refresh=force_refresh,
                              status_cb=splash.set_status)
        demo_mode = not real_data
        QTimer.singleShot(0, lambda: step2_build(demo_mode))

    def step2_build(demo_mode: bool) -> None:
        splash.set_status("Bygger brugerfladen…")
        app.processEvents()

        win = MainWindow(
            demo_mode=demo_mode,
            on_refresh=lambda: _do_refresh(win),
        )
        app._main_win = win
        splash.set_status("Klar!")
        app.processEvents()
        QTimer.singleShot(350, lambda: _show(win))

    def _do_refresh(win: MainWindow) -> None:
        reply = QMessageBox.question(
            win, "Opdater data",
            "Dette sletter cachen og genindlæser data fra dataloader.\n"
            "Programmet genstarter. Fortsæt?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            invalidate_cache()
            import subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            app.quit()

    def _show(win: MainWindow) -> None:
        splash.close()
        win.show()

    QTimer.singleShot(50, lambda: step1_data(force_refresh=False))
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()