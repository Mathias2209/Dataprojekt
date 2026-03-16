# loading_screen.py — animated splash screen shown during startup
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter

from config import ACCENT, SUBTEXT, BORDER, PANEL_BG


class LoadingScreen(QWidget):
    """Frameless animated splash shown while data loads."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 280)

        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

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

        self._status_lbl = QLabel("Indlæser…")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color:{SUBTEXT}; font-size:11px; background:transparent;"
        )
        layout.addWidget(self._status_lbl)

        self._dot_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)

    # ── Public ────────────────────────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        self._status_lbl.setText(text)
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