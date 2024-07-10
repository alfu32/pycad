from abc import ABC, abstractmethod
from typing import List

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from pycad.ComponentLayers import LayerModel
from pycad.Drawable import Drawable


class PluginInterface:
    _instance = None

    @staticmethod
    def get_instance() -> 'PluginInterface':
        if PluginInterface._instance is None:
            PluginInterface._instance = PluginInterface()
        return PluginInterface._instance

    def init_ui(self) -> QWidget:
        raise NotImplementedError("init_ui not implemented")

    def destroy_ui(self, element: QWidget):
        raise NotImplementedError("destroy_ui not implemented")

    def create_drawable(self, layer: LayerModel, start_point: QPoint) -> Drawable:
        raise NotImplementedError("create_drawable not implemented")

    def modify_drawable(self, layer: LayerModel, new_point: QPoint) -> Drawable:
        raise NotImplementedError("modify_drawable not implemented")
