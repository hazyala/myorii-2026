import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from platform.macos.menubar import MacMenuBar
from storage import database
app=QApplication([])
app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path',return_value=Path(folder)/'test.db'), patch('ui.main_window.ModelWarmupWorker.start'), patch('ui.main_window.ModelListWorker.start'), patch('ui.main_window.InternetStatusWatcher.check_now'):
    database.initialize()
    w=MainWindow()
    m=MacMenuBar(w)
    captures=[]
    original=w.toggle_at
    def captured(rect):
        original(rect)
        captures.append({'icon':[rect.x(),rect.y(),rect.width(),rect.height()], 'window':[w.x(),w.y(),w.width(),w.height()], 'expected':[w._position_for(rect).x(),w._position_for(rect).y()]})
    w.toggle_at=captured
    m.show()
    m.show_initial_window()
    def finish():
        rect=m.tray_icon.geometry()
        success=bool(captures) and rect.isValid() and w.pos()==w._position_for(rect)
        print(json.dumps({'success':success,'first_show':captures,'final_icon':[rect.x(),rect.y(),rect.width(),rect.height()]},ensure_ascii=False),flush=True)
        m.tray_icon.hide();w.hide();app.exit(0 if success else 1)
    QTimer.singleShot(2500,finish)
    code=app.exec()
    raise SystemExit(code)
