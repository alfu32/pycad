from abc import ABC, abstractmethod
from typing import List

from PySide6.QtCore import QPoint, Signal, Qt, QObject
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QPushButton

from pycad.ComponentLayers import LayerModel
from pycad.Drawable import Drawable
from pycad.TextSignalData import TextSignalData


class BaseTool(QObject):
    github_url: str = ""
    _instance = None

    drawable_ready = Signal(Drawable)
    point_received = Signal(QPoint)
    text_received = Signal(str)
    drawable_started = Signal(Drawable)

    @staticmethod
    def get_instance() -> 'BaseTool':
        if BaseTool._instance is None:
            BaseTool._instance = BaseTool()
        return BaseTool._instance

    def __init__(self):
        super(QObject, self).__init__()
        self.identifier = "plugin_base"
        self.name = "Base Plugin"
        self.button = QPushButton(f"{self.name}")
        self.button.clicked.connect(self.start)
        self.built_object = []
        print(f"{self.identifier} initialized", flush=True)

    def get_ui_fragment(self):
        return self.button

    def start(self):
        if self.is_active:
            pass
        else:
            self.built_object = []
            print(f"{self.identifier}::start", flush=True)
            try:
                self.drawable_started.emit(self.built_object)
            except:
                pass
            self.button.setChecked(True)
            self.is_active = True
        # raise NotImplementedError(f"{self.identifier} must implement start method")

    def push_model_point(self, point: QPoint):
        try:
            self.point_received.emit(point)
        except:
            pass
        print(f"{self.identifier}::push_model_point {point}", flush=True)
        self.built_object.append(point)
        # raise NotImplementedError(f"{self.identifier} must implement push_model_point method")

    def push_user_text(self, text: TextSignalData):
        if self.is_active:
            try:
                self.text_received.emit(text.text)
            except:
                pass
            if text.text == Qt.Key_Escape:
                print(f"{self.identifier} finished by escape", flush=True)
                self.is_active = False
            else:
                print(f"{self.identifier}::push_user_text {text.text}", flush=True)

    def draw(self, painter: QPainter, moving_point: QPoint):
        raise NotImplementedError(f"{self.identifier} must implement draw method")


    def finalize(self):
        try:
            self.drawable_ready.emit(self.built_object)
        except:
            pass
        self.button.setChecked(False)
        self.is_active = False
    def build(self):
        return self.built_object

    def destroy(self):
        pass
