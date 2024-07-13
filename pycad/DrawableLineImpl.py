import math
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

import ezdxf
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.util_geometry import line_intersects_rect, line_contains_point, _points_equal, Segment, HasSegment
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace


def split_line_by_points(line: HasSegment, points):
    segments = []
    start = line.segment.a
    for point in points:
        segments.append(Line(start, point))
        start = point
    segments.append(Line(start, line.segment.b))
    return segments



class Line(Drawable, ABC):

    def __init__(self, start_point: QPoint, end_point: QPoint = None):
        super(Drawable, self).__init__()
        self.segment: Segment = Segment(start_point, end_point)
        self.segment.set(start_point, end_point)
        self.points: List[QPoint] = []
        self.moving_point: QPoint = None

    def is_done(self):
        return self.segment.a != self.segment.b

    def push(self, point: QPoint):
        self.points.append(point)
        self.segment.set(self.points[0], self.points[1])

    def isin(self, rect: QRect) -> bool:
        return self.segment.is_in(rect)

    def intersects(self, rect: QRect) -> bool:
        return self.segment.intersects(rect)

    def set_start_point(self, value: QPoint):
        self.segment.set(value, self.segment.b)

    def set_send_point(self, value: QPoint):
        self.segment.set(self.segment.a, value)

    def get_hotspots(self) -> List[Tuple[HotspotClasses, QPoint, HotspotHandler]]:
        return [
            (HotspotClasses.ENDPOINT, self.segment.a, self.set_start_point),
            (HotspotClasses.ENDPOINT, self.segment.b, self.set_send_point),
        ]

    def get_snap_points(self) -> List[Tuple[HotspotClasses, QPoint]]:
        return [
            (HotspotClasses.ENDPOINT, self.segment.a),
            (HotspotClasses.MIDPOINT, (self.segment.a + self.segment.b) / 2),
            (HotspotClasses.ENDPOINT, self.segment.b),
        ]

    def update(self, painter: QPainter):
        pass

    def set_next_point(self, point: QPoint):
        self.set_send_point(point)
        self.finished.emit(True)

    def contains_point(self, point):
        return self.segment.contains_point(point)

    def intersect(self, other: HasSegment) -> Optional[QPoint]:
        return self.segment.intersect(other.segment)

    def is_empty(self, threshold=1.0):
        length = math.hypot(self.segment.a.x() - self.segment.b.x(), self.segment.a.y() - self.segment.b.y())
        return length < threshold

    def __eq__(self, other: HasSegment):
        if not isinstance(other, Line):
            return False
        return (_points_equal(self.segment.a, other.segment.a) and _points_equal(self.segment.b,
                                                                                 other.segment.b)) or \
            (_points_equal(self.segment.a, other.segment.b) and _points_equal(self.segment.b,
                                                                              other.segment.a))

    def __hash__(self):
        start_tuple = (self.segment.a.x(), self.segment.a.y())
        end_tuple = (self.segment.b.x(), self.segment.b.y())
        return hash((min(start_tuple, end_tuple), max(start_tuple, end_tuple)))

    def draw(self, painter: QPainter):
        painter.drawLine(self.segment.a.x(), self.segment.a.y(), self.segment.b.x(), self.segment.b.y())

    def save_to_dxf(self, doc: DXFDrawing, layer_name: str):
        msp: DXFModelspace = doc.modelspace()

        msp.add_line(
            (self.segment.a.x(), self.segment.a.y()),
            (self.segment.b.x(), self.segment.b.y()),
            dxfattribs={
                'layer': layer_name,
            }
        )

    @classmethod
    def from_dxf(cls, entity_data: ezdxf.entities.Line):
        start_point = QPoint(entity_data.dxf.start.x, entity_data.dxf.start.y)
        end_point = QPoint(entity_data.dxf.end.x, entity_data.dxf.end.y)
        return cls(start_point, end_point)
