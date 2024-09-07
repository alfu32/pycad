from PySide6.QtCore import Signal, QPoint, QObject
from PySide6.QtGui import QPainter, Qt
from PySide6.QtWidgets import QPushButton

from pycad.Drawable import Drawable
from pycad.Plugin import BaseTool
from pycad.TextSignalData import TextSignalData


class MultipointTool(BaseTool):
    finished = Signal(QObject)
    point_received = Signal(QPoint)
    text_received = Signal(str)
    started = Signal(QObject)

    def __init__(self):
        super().__init__()
        self.identifier = "core_plugin_polyline"
        self.name = "Polyline"
        self.input_buffer = []
        self.button = QPushButton(f"{self.name}")
        self.button.clicked.connect(self.start)
        self.button.setCheckable(True)
        self.is_active = False
        print(f"{self.identifier} initialized", flush=True)

    def get_ui_fragment(self):
        return self.button

    def start(self):
        if self.is_active:
            pass
        else:
            self.input_buffer = []
            try:
                self.started.emit(self)
                print(f"emitted {self.identifier}::started", flush=True)
            except Exception as x:
                print(f" error emitting {self.identifier}::started signal ", flush=True)
                print(x)
            self.button.setChecked(True)
            self.is_active = True

    def push_model_point(self, point: QPoint):
        if self.is_active:
            if len(self.input_buffer) > 0 and point == self.input_buffer[0]:
                print(f"{self.identifier} finished by close point", flush=True)
                self.finalize()
            self.input_buffer.append(point)
            try:
                self.point_received.emit(point)
            except Exception as x:
                print(f" error emitting {self.identifier}::point_received signal ", flush=True)
                print(x)

            # print(f"{self.identifier}::push_model_point {point} , points:{self.built_object}", flush=True)

    def push_user_text(self, text: TextSignalData):
        if self.is_active:
            try:
                self.text_received.emit(text.text)
            except Exception as x:
                print(f" error emitting {self.identifier}::text_received signal ", flush=True)
                print(x)
            if text.key == Qt.Key_Escape:
                print(f"{self.identifier} finished by escape", flush=True)
                self.finalize()
            else:
                print(f"{self.identifier}::push_user_text {text.text}", flush=True)

    def draw(self, painter: QPainter, moving_point: QPoint):
        r = self.input_buffer
        l = len(r)
        # print(f"drawing Polyline Plugin figure {l} points : {r}", flush=True)
        if l > 1:
            a = r[0]
            b = r[1]
            painter.drawLine(a.x(), a.y(), b.x(), b.y())
            for i, p in enumerate(self.input_buffer):
                if i == 0:
                    continue
                else:
                    a = r[i]
                    b = r[i + 1] if (i + 1) < l else moving_point
                    painter.drawLine(a.x(), a.y(), b.x(), b.y())
        elif l > 0:
            a = r[0]
            b = moving_point
            painter.drawLine(a.x(), a.y(), b.x(), b.y())
        else:
            pass

        # raise NotImplementedError(f"{self.identifier} must implement draw method")

    def finalize(self):
        try:
            self.finished.emit(self)
            print(f"emitted {self.identifier}::finished", flush=True)
        except Exception as x:
            print(f" error emitting {self.identifier}::finished signal ", flush=True)
            print(x)
        self.button.setChecked(False)
        self.is_active = False
        return self.input_buffer

    def build(self):
        return self.input_buffer

    def destroy(self):
        pass