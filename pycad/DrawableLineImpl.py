import math
from abc import ABC
from typing import List, Tuple

import ezdxf
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.util_geometry import line_intersects_rect, line_contains_point, _points_equal
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace


def split_line_by_points(line, points):
    segments = []
    start = line.start_point
    for point in points:
        segments.append(Line(start, point))
        start = point
    segments.append(Line(start, line.end_point))
    return segments


class Line(Drawable, ABC):
    def __init__(self, start_point: QPoint, end_point: QPoint = None):
        super(Drawable, self).__init__()
        self.start_point = start_point
        self.end_point = end_point

    def isin(self, rect: QRect) -> bool:
        return rect.contains(self.start_point) or rect.contains(self.end_point)

    def intersects(self, rect: QRect) -> bool:
        return line_intersects_rect((self.start_point, self.end_point), rect)

    def set_start_point(self, value: QPoint):
        self.start_point = value

    def set_send_point(self, value: QPoint):
        self.end_point = value

    def get_hotspots(self) -> List[Tuple[HotspotClasses, QPoint, HotspotHandler]]:
        return [
            (HotspotClasses.ENDPOINT, self.start_point, self.set_start_point),
            (HotspotClasses.ENDPOINT, self.end_point, self.set_send_point),
        ]

    def get_snap_points(self) -> List[Tuple[HotspotClasses, QPoint]]:
        return [
            (HotspotClasses.ENDPOINT, self.start_point),
            (HotspotClasses.MIDPOINT, (self.start_point + self.end_point) / 2),
            (HotspotClasses.ENDPOINT, self.end_point),
        ]

    def update(self, painter: QPainter):
        pass

    def set_next_point(self, point: QPoint):
        self.end_point = point
        self.finished.emit(True)

    def contains_point(self, point):
        return line_contains_point((self.start_point, self.end_point), point)

    def intersect(self, other):
        def ccw(A, B, C):
            return (C.y() - A.y()) * (B.x() - A.x()) > (B.y() - A.y()) * (C.x() - A.x())

        A = self.start_point
        B = self.end_point
        C = other.start_point
        D = other.end_point

        if ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D):
            denom = (A.x() - B.x()) * (C.y() - D.y()) - (A.y() - B.y()) * (C.x() - D.x())
            if denom == 0:
                return None
            intersect_x = ((A.x() * B.y() - A.y() * B.x()) * (C.x() - D.x()) - (A.x() - B.x()) * (
                    C.x() * D.y() - C.y() * D.x())) / denom
            intersect_y = ((A.x() * B.y() - A.y() * B.x()) * (C.y() - D.y()) - (A.y() - B.y()) * (
                    C.x() * D.y() - C.y() * D.x())) / denom
            return QPoint(intersect_x, intersect_y)
        return None

    def is_empty(self, threshold=1.0):
        length = math.hypot(self.start_point.x() - self.end_point.x(), self.start_point.y() - self.end_point.y())
        return length < threshold

    def __eq__(self, other):
        if not isinstance(other, Line):
            return False
        return (_points_equal(self.start_point, other.start_point) and _points_equal(self.end_point,
                                                                                     other.end_point)) or \
            (_points_equal(self.start_point, other.end_point) and _points_equal(self.end_point,
                                                                                other.start_point))

    def __hash__(self):
        start_tuple = (self.start_point.x(), self.start_point.y())
        end_tuple = (self.end_point.x(), self.end_point.y())
        return hash((min(start_tuple, end_tuple), max(start_tuple, end_tuple)))

    def draw(self, painter: QPainter):
        painter.drawLine(self.start_point.x(), self.start_point.y(), self.end_point.x(), self.end_point.y())

    def save_to_dxf(self, doc: DXFDrawing, layer_name: str):
        msp: DXFModelspace = doc.modelspace()

        msp.add_line(
            (self.start_point.x(), self.start_point.y()),
            (self.end_point.x(), self.end_point.y()),
            dxfattribs={
                'layer': layer_name,
            }
        )

    @classmethod
    def from_dxf(cls, entity_data: ezdxf.entities.Line):
        start_point = QPoint(entity_data.dxf.start.x, entity_data.dxf.start.y)
        end_point = QPoint(entity_data.dxf.end.x, entity_data.dxf.end.y)
        return cls(start_point, end_point)
