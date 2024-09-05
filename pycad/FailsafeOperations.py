from PySide6.QtCore import QObject, QThread, QTimer, Signal
from collections import deque

class Worker(QObject):
    exec_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.queue = deque()
        self.exec_requested.connect(self._exec)

    def request_exec(self, func, success="", error=""):
        self.exec_requested.emit(func)

    def _exec(self, func):
        try:
            func()
            #print(success, flush=True)
        except Exception as e:
            self.queue.append(func)
            #print(error, flush=True)
            print(e, flush=True)

    def process_queue(self):
        new_queue = deque()
        while self.queue:
            func = self.queue.popleft()
            try:
                func()
            except Exception as e:
                new_queue.append(func)
        self.queue = new_queue

class OperationsQueue(QObject):
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        self.thread = QThread()
        self.timer = QTimer()
        self.timer.timeout.connect(self.worker.process_queue)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.start_timer)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.timer.stop)
        self.thread.start()

    def start_timer(self):
        self.timer.start(1000)  # process the queue every second

    def exec(self, func):
        self.worker.request_exec(func)

    def stop(self):
        self.thread.quit()
        self.thread.wait()