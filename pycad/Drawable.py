import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Tuple, Callable, Optional

from PySide6.QtGui import QPainter
from PySide6.QtCore import QPoint, QRect, Signal

from ezdxf.document import Drawing as DXFDrawing

from pycad.util_geometry import Segment, HasSegment


class HotspotClasses(Enum):
    ENDPOINT = "ENDPOINT"
    MIDPOINT = "MIDPOINT"
    PERPENDICULAR = "PERPENDICULAR"
    TOUCHING = "TOUCHING"
    GRID = "GRID"


HotspotHandler = Callable[[QPoint], None]


class Drawable(ABC):
    changed = Signal(object)  # Define a custom signal with a generic object type
    finished = Signal(bool)  # Define a custom signal with a generic object type

    def __init__(self):
        self.segment: Segment = Segment(QPoint(0, 0), QPoint(0, 0))
        self._points = 0
        self.points: List[QPoint] = []
        self.moving_point: QPoint = None
        self.max_points: int = 2

    @abstractmethod
    def is_done(self):
        pass

    def push(self, point: QPoint):
        if self._points == 0:
            self.segment.a = point
            self._points += 1
        elif self._points == 1:
            self.segment.b = point
            self._points += 1
        self.points.append(point)

    @abstractmethod
    def isin(self, rect: QRect) -> bool:
        pass

    # TODO remove 1000
    @abstractmethod
    def update(self, painter: QPainter):
        pass

    def build_is_finished(self) -> bool:
        return len(self.points) == self.max_points

    # TODO remove 1000
    def set_next_point(self, point: QPoint):
        self.points.append(point)
        if self.build_is_finished():
            self.finished.emit(self)
        else:
            self.changed.emit(self)

    def set_moving_point(self, point: QPoint):
        self.moving_point = point

    def intersect(self, other: HasSegment) -> Optional[QPoint]:
        return None

    @abstractmethod
    def intersects(self, rect: QRect) -> bool:
        pass

    @abstractmethod
    def is_empty(self, threshold=1.0) -> bool:
        return False

    @abstractmethod
    def contains_point(self, point) -> bool:
        return False

    @abstractmethod
    def draw(self, painter: QPainter):
        pass

    @abstractmethod
    def save_to_dxf(self, dxf_document: DXFDrawing, layer_name: str):
        pass

    @abstractmethod
    def get_hotspots(self) -> List[Tuple[HotspotClasses, QPoint, HotspotHandler]]:
        pass

    @abstractmethod
    def get_snap_points(self) -> List[Tuple[HotspotClasses, QPoint]]:
        pass

    @abstractmethod
    def from_dxf(cls, entity_data) -> 'Drawable':
        pass

    def get_rotation(self):
        a = self.segment.a
        b = self.segment.b if self._points>=2 else self.moving_point
        return math.atan2(a.y() - b.y(), a.x() - b.x())

    def is_done(self) -> bool:
        pass
