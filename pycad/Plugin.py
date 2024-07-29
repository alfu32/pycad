from abc import ABC, abstractmethod
from typing import List

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QPushButton

from pycad.ComponentLayers import LayerModel
from pycad.Drawable import Drawable


class BasePlugin:
    github_url: str = ""
    _instance = None

    @staticmethod
    def get_instance() -> 'BasePlugin':
        if BasePlugin._instance is None:
            BasePlugin._instance = BasePlugin()
        return BasePlugin._instance

    drawable_ready = Signal()
    point_received = Signal(object)
    text_received = Signal(str)
    drawable_started = Signal()

    def __init__(self):
        super().__init__()
        self.identifier = "plugin_base"
        self.name = "Base Plugin"

    def get_ui_fragment(self):
        button = QPushButton(f"Start {self.name}")
        return button

    def start(self):
        raise NotImplementedError(f"{self.identifier} must implement start method")

    def push_model_point(self, point:QPoint):
        raise NotImplementedError(f"{self.identifier} must implement push_model_point method")

    def push_user_text(self, text:str):
        raise NotImplementedError(f"{self.identifier} must implement push_user_text method")

    def draw(self, painter:QPainter,moving_point:QPoint):
        raise NotImplementedError(f"{self.identifier} must implement draw method")

    def destroy(self):
        pass
