"""First-run local model preparation, before the main window is constructed."""
import threading
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QHBoxLayout
from core.paths import resource_path
from core.setup.local_setup import LocalSetup, Cancelled, DEFAULT_MODEL


class SetupWorker(QThread):
    progress = pyqtSignal(str, object, object)
    outcome = pyqtSignal(str)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.cancelled = threading.Event()
        self.model = model

    def run(self):
        try:
            LocalSetup(self.progress.emit, self.cancelled, self.model).run()
            self.outcome.emit('')
        except Cancelled:
            self.outcome.emit('준비를 취소했습니다. 다시 시작하면 다운로드한 모델 부분을 재사용합니다.')
        except Exception as exc:
            self.outcome.emit(str(exc))


class SetupDialog(QDialog):
    def __init__(self, model=DEFAULT_MODEL):
        super().__init__()
        self.model = model
        self.worker = None
        self.pending_error = None
        self.setWindowTitle('묘리 시작하기')
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(QPixmap(str(resource_path('assets', 'characters', 'myorii_profile.png'))).scaled(
            120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(icon)
        title = QLabel('묘리가 대화할 준비를 할게요')
        title.setStyleSheet('font-size: 20px; font-weight: bold')
        layout.addWidget(title)
        self.description = QLabel(f'로컬 AI 사용에 필요한 Ollama와 {model} 모델을 준비합니다.\n'
                                  '없는 항목만 다운로드하며 기본 Qwen 모델은 약 3.3GB입니다.\n'
                                  '인터넷과 충분한 저장 공간이 필요합니다.')
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        self.status = QLabel('시작을 누르면 Ollama 설치와 모델 다운로드에 동의합니다.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setValue(0)
        layout.addWidget(self.bar)
        row = QHBoxLayout()
        self.start = QPushButton('준비 시작')
        self.start.clicked.connect(self.begin)
        row.addWidget(self.start)
        self.skip = QPushButton('API 사용 / 나중에')
        self.skip.clicked.connect(self.accept)
        row.addWidget(self.skip)
        self.cancel = QPushButton('닫기')
        self.cancel.clicked.connect(self.reject)
        row.addWidget(self.cancel)
        layout.addLayout(row)

    def begin(self):
        self.start.setEnabled(False)
        self.skip.setEnabled(False)
        self.cancel.setText('취소')
        self.worker = SetupWorker(self.model, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.outcome.connect(self.result_ready)
        self.worker.finished.connect(self.finished_work)
        self.worker.start()

    def update_progress(self, stage, done, total):
        self.status.setText(stage + (f'\n{done / 1024**3:.2f} / {total / 1024**3:.2f} GB' if total > 1024 else ''))
        self.bar.setRange(0, 100 if total else 0)
        if total:
            self.bar.setValue(min(100, int(done * 100 / total)))

    def result_ready(self, error):
        self.pending_error = error

    def finished_work(self):
        if self.pending_error == '':
            self.accept()
            return
        self.status.setText(self.pending_error or '준비가 중단되었습니다.')
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.start.setText('다시 시도')
        self.start.setEnabled(True)
        self.skip.setEnabled(True)
        self.cancel.setEnabled(True)
        self.cancel.setText('닫기')

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancelled.set()
            self.status.setText('취소 중입니다. 진행 중인 연결이 끝나면 멈춥니다.')
            self.cancel.setEnabled(False)
        else:
            super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)
