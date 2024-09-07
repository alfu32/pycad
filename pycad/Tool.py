from typing import override

from PySide6.QtCore import Signal, QPoint, QObject
from PySide6.QtGui import QPainter, Qt
from PySide6.QtWidgets import QPushButton

from pycad.Drawable import Drawable
from pycad.Plugin import BaseTool
from pycad.TextSignalData import TextSignalData



class PolylineTool(BaseTool):

    def __init__(self):
        super().__init__()
        self.identifier = "core_plugin__polyline"
        self.name = "Polyline"
        self.button.setText(f"{self.name}")
        print(f"{self.identifier} initialized", flush=True)

    @override
    def build(self):
        return self.input_buffer