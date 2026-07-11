from __future__ import annotations

from collections.abc import Callable
import traceback

from PySide6.QtCore import QObject, QThread, Signal


class BackgroundTaskWorker(QObject):
    finished = Signal(object)
    failed = Signal(str, str)
    progress = Signal(str, int, int)

    def __init__(self, task: Callable, accepts_progress: bool = False) -> None:
        super().__init__()
        self._task = task
        self._accepts_progress = accepts_progress

    def run(self) -> None:
        try:
            if self._accepts_progress:
                self.finished.emit(self._task(self.progress.emit))
            else:
                self.finished.emit(self._task())
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())


class BackgroundTaskHandle(QObject):
    finished = Signal(object)
    failed = Signal(str, str)
    progress = Signal(str, int, int)

    def __init__(self, task: Callable, parent: QObject | None = None, accepts_progress: bool = False) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._worker = BackgroundTaskWorker(task, accepts_progress=accepts_progress)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.progress.connect(self.progress.emit)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self.deleteLater)

    def start(self) -> None:
        self._thread.start()

    def _on_finished(self, result: object) -> None:
        self.finished.emit(result)

    def _on_failed(self, message: str, details: str) -> None:
        self.failed.emit(message, details)
