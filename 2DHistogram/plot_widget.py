# plot_widget.py — PlotWidget: canvas + header label, used inside panels
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

from config import ACCENT, PANEL_BG
from plot_canvas import PlotCanvas
from widgets import styled_label


class PlotWidget(QWidget):
    """
    Thin wrapper around PlotCanvas that adds a coloured header bar
    (e.g. "  Graf A") and stores the last filtered DataFrame for CSV export.
    """

    def __init__(self, letter: str, parent=None):
        super().__init__(parent)
        self.letter = letter
        self._last_filtered = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = styled_label(f"  Graf {letter}", bold=True, color=ACCENT, size=11)
        header.setStyleSheet(
            f"color:{ACCENT}; font-size:11px; font-weight:bold; "
            f"background:{PANEL_BG}; padding:3px 6px; border-radius:4px;"
        )
        layout.addWidget(header)

        self.canvas = PlotCanvas()
        layout.addWidget(self.canvas)

    def redraw(self, s: dict, df) -> None:
        """
        Re-render the plot from settings dict `s` and source DataFrame `df`.
        Stores the filtered result in self._last_filtered.
        """
        self._last_filtered = self.canvas.draw_histogram(
            data              = df,
            kassationsårsag   = s['kassationsårsag'],
            bins              = s['bins'],
            min_dage          = s['min_dage'],
            max_dage          = s['max_dage'],
            min_vask          = s['min_vask'],
            max_vask          = s['max_vask'],
            x_skala           = s['x_skala'],
            datasæt_navn      = s['datasæt'],
            total             = len(df),
            log_color         = s['log_color'],
            ref_lines         = s['ref_lines'],
            vmin              = s['vmin'],
            min_ratio         = s['min_ratio'],
            max_ratio         = s['max_ratio'],
            show_percentiles  = s.get('show_percentiles'),
            plot_type         = s.get('plot_type', 'Begge'),
            smooth            = s.get('smooth', 15),
            log_y_hist        = s.get('log_y_hist', False),
            show_regression   = s.get('show_reg', True),
            show_4sigma       = s.get('show_4sigma', True),
            show_2sigma       = s.get('show_2sigma', True),
            show_survival     = s.get('show_survival', True),
        )