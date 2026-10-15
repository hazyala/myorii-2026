"""Myorii application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QLockFile, QStandardPaths
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QIcon
from core.paths import resource_path
from storage import model_store
from ui.setup_dialog import SetupDialog
from core.setup.local_setup import LocalSetup

from platform.macos.menubar import MacMenuBar
from ui.main_window import MainWindow
from storage import database


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Myorii")
    app.setQuitOnLastWindowClosed(False)

    lock_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
    app_lock = QLockFile(f"{lock_path}/myorii.lock")
    app_lock.setStaleLockTime(1000)
    if not app_lock.tryLock(100):
        return 0
    
    database.initialize()

    app.setWindowIcon(QIcon(str(resource_path('assets', 'characters', 'myorii_profile.png'))))
    config = model_store.load()
    if config['provider'] == 'ollama':
        model = config['models']['ollama']
        # Fast probe only; all downloads and model loading run in the dialog worker.
        setup = LocalSetup(lambda *args: None, model=model)
        if not setup.has_model(setup.available()):
            if SetupDialog(model).exec() != QDialog.DialogCode.Accepted:
                return 0

    window = MainWindow()
    menu_bar = MacMenuBar(window)
    menu_bar.show()
    menu_bar.show_initial_window()

    app.setProperty("myorii_lock", app_lock)
    app.setProperty("myorii_window", window)
    app.setProperty("myorii_menu_bar", menu_bar)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
