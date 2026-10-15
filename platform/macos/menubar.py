from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QRect, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon

from ui.main_window import MainWindow


class MacMenuBar(QObject):
    ICON_PATH = Path("assets") / "icons" / "menubar_icon.png"
    ICON_SIZE = 36

    def __init__(self, window: MainWindow) -> None:
        super().__init__()

        self._initial_timer = QTimer(self)
        self._initial_timer.setInterval(100)
        self._initial_timer.timeout.connect(self._check_initial_position)
        self._last_geometry = QRect()
        self._stable_samples = 0
        self._position_checks = 0
        self.window = window
        self.tray_icon = QSystemTrayIcon(self._icon(), self)
        self.tray_icon.setToolTip("Myorii")
        self.tray_icon.activated.connect(self._handle_activation)

    def show(self) -> None:
        self.tray_icon.show()

    def show_initial_window(self) -> None:
        # Cocoa installs the status item asynchronously. A zero-delay callback
        # can still see an empty rectangle and place the window at screen right.
        self._last_geometry = QRect()
        self._stable_samples = 0
        self._position_checks = 0
        self._initial_timer.start()

    def _check_initial_position(self) -> None:
        self._position_checks += 1
        geometry = self.tray_icon.geometry()
        if geometry.isValid() and not geometry.isNull():
            self._stable_samples = self._stable_samples + 1 if geometry == self._last_geometry else 1
            self._last_geometry = QRect(geometry)
            if self._stable_samples >= 5:
                self._initial_timer.stop()
                if not self.window.isVisible():
                    self.window.toggle_at(geometry)
                return
        else:
            self._stable_samples = 0
            self._last_geometry = QRect()
        if self._position_checks >= 50:
            # Keep the menu icon available; never auto-open at a guessed position.
            self._initial_timer.stop()

    def toggle_window(self) -> None:
        # A user click owns visibility from now on; a delayed auto-open must not
        # reopen a window that the user has just closed.
        self._initial_timer.stop()
        self.window.toggle_at(self.tray_icon.geometry())

    def _handle_activation(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window()

    def _icon_path(self) -> Path:
        app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        return app_root / self.ICON_PATH

    def _icon(self) -> QIcon:
        icon_path = self._icon_path()
        pixmap = QPixmap(str(icon_path))
        if pixmap.isNull():
            return QIcon(str(icon_path))

        scaled_pixmap = pixmap.scaled(
            self.ICON_SIZE,
            self.ICON_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QIcon(scaled_pixmap)
