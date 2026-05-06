# loading_screen.py — animated splash screen with progress bar
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QColor, QPainter, QLinearGradient

from config import ACCENT, SUBTEXT, BORDER, PANEL_BG, TEXT


class LoadingScreen(QWidget):
    """Frameless animated splash with progress bar and percentage counter."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 300)

        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        # ── Title ──────────────────────────────────────────────────────────────
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
        layout.addSpacing(6)

        # ── Dot animation ──────────────────────────────────────────────────────
        dot_row = QHBoxLayout()
        dot_row.setAlignment(Qt.AlignCenter)
        dot_row.setSpacing(10)
        self._dots: list[QLabel] = []
        for _ in range(5):
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(f"color:{BORDER}; font-size:14px; background:transparent;")
            dot_row.addWidget(dot)
            self._dots.append(dot)
        layout.addLayout(dot_row)

        # ── Progress bar (custom-painted via _ProgressBar widget) ─────────────
        self._progress_bar = _ProgressBar(self)
        self._progress_bar.setFixedHeight(10)
        layout.addSpacing(4)
        layout.addWidget(self._progress_bar)

        # ── Percentage + status on the same row ────────────────────────────────
        pct_row = QHBoxLayout()
        pct_row.setContentsMargins(0, 0, 0, 0)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFixedWidth(38)
        self._pct_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._pct_lbl.setStyleSheet(
            f"color:{ACCENT}; font-size:11px; font-weight:bold; background:transparent;"
        )
        pct_row.addWidget(self._pct_lbl)

        self._status_lbl = QLabel("Indlæser…")
        self._status_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._status_lbl.setStyleSheet(
            f"color:{SUBTEXT}; font-size:11px; background:transparent;"
        )
        pct_row.addWidget(self._status_lbl, stretch=1)
        layout.addLayout(pct_row)

        # ── Dot animation timer ────────────────────────────────────────────────
        self._dot_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)

        self._progress = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        """Update the status label only (no progress change)."""
        self._status_lbl.setText(text)
        QApplication.processEvents()

    def set_progress(self, percent: int, status: str = None) -> None:
        """
        Set the progress bar to `percent` (0–100) and optionally update
        the status label at the same time.
        """
        self._progress = max(0, min(100, percent))
        self._pct_lbl.setText(f"{self._progress}%")
        self._progress_bar.set_value(self._progress)
        if status is not None:
            self._status_lbl.setText(status)
        QApplication.processEvents()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        for i, dot in enumerate(self._dots):
            if i == self._dot_idx:
                dot.setStyleSheet(
                    f"color:{ACCENT}; font-size:16px; font-weight:bold; background:transparent;"
                )
            else:
                dot.setStyleSheet(
                    f"color:{BORDER}; font-size:14px; background:transparent;"
                )
        self._dot_idx = (self._dot_idx + 1) % len(self._dots)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(PANEL_BG))
        painter.setPen(QColor(ACCENT))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)


# ── Progress bar widget ────────────────────────────────────────────────────────

class _ProgressBar(QWidget):
    """Custom-painted progress bar matching the dark theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0

    def set_value(self, value: int) -> None:
        self._value = max(0, min(100, value))
        self.update()          # triggers paintEvent

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        r = h // 2            # corner radius = half height → pill shape

        # Track (background)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(BORDER))
        painter.drawRoundedRect(0, 0, w, h, r, r)

        # Fill (gradient left → right)
        fill_w = int(w * self._value / 100)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor("#505050"))   # dark gray
            grad.setColorAt(1.0, QColor(ACCENT))       # light gray accent
            painter.setBrush(grad)
            # Clip fill to pill shape by drawing into the same rounded rect
            painter.setClipRect(QRect(0, 0, fill_w, h))
            painter.drawRoundedRect(0, 0, w, h, r, r)