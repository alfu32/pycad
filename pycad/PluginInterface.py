from abc import ABC, abstractmethod

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget

from pycad.ComponentLayers import LayerModel
from pycad.Drawable import Drawable


class PluginInterface(ABC):

    @abstractmethod
    def init_ui(self, parent: QWidget):
        pass

    @abstractmethod
    def get_instance_of_drawable(self, layer: LayerModel, start_point: QPoint) -> Drawable:
        pass