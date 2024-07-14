import math
from abc import ABC

from typing import List, Tuple, Optional, override

from PySide6.QtCore import QPoint, QRect, QPointF
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace
from ezdxf.entities import Dimension as DXFDimension
from pycad.util_geometry import line_intersects_rect, line_contains_point, get_text_dimensions, \
    get_pen_width, set_pen_width, mod, HasSegment, Segment


class Dimension(Drawable, ABC):

    def __init__(self):
        super(Drawable, self).__init__()
        self.offset_distance = 25
        self.segment: Segment = Segment(QPoint(0, 0), QPoint(0, 0))
        self._points = 0
        self.points: List[QPoint] = []
        self.moving_point: QPoint = None
        self.max_points: int = 2

    @override
    def is_done(self):
        return self._points >= 2

    def isin(self, rect: QRect) -> bool:
        return self.segment.is_in(rect)

    def intersects(self, rect: QRect) -> bool:
        return self.segment.intersects(rect)

    def set_start_point(self, value: QPoint):
        self.segment.set(value, self.segment.b)

    def set_send_point(self, value: QPoint):
        self.segment.set(self.segment.a, value)

    def get_hotspots(self) -> List[Tuple[HotspotClasses, QPoint, HotspotHandler]]:
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        return [
            (HotspotClasses.ENDPOINT, a, self.set_start_point),
            (HotspotClasses.ENDPOINT, b, self.set_send_point),
        ]

    def get_snap_points(self) -> List[Tuple[HotspotClasses, QPoint]]:
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        return [
            (HotspotClasses.ENDPOINT, a),
            (HotspotClasses.MIDPOINT, (a + b) / 2),
            (HotspotClasses.ENDPOINT, b),
        ]

    # TODO remove 1000
    def update(self, painter: QPainter):
        pass

    def contains_point(self, point):
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        return line_contains_point((a, b), point)

    def intersect(self, other: HasSegment) -> Optional[QPoint]:
        return None

    def is_empty(self, threshold=1.0) -> bool:
        return False

    def get_rotation(self):
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        return math.atan2(a.y() - b.y(), a.x() - b.x())
        # return math.atan2(self.segment.b.y() - self.segment.a.y(), self.segment.a.x() - self.segment.b.x())
        # return math.atan2(self.segment.b.y() - self.segment.a.y(), self.segment.b.x() - self.segment.a.x())

    def draw(self, painter: QPainter):
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        start_point = self.offset_point(a, self.offset_distance)
        end_point = self.offset_point(b, self.offset_distance)
        rotation = (self.get_rotation() + math.pi) * 180 / math.pi
        dir = -1 if 90 < rotation <= 270 else 0.5
        text = f"{self.length():.2f} ({rotation:.2f} [{dir}])"
        text = f"{self.length():.1f}"
        tw, th = get_text_dimensions(painter, text)
        mid_point = QPoint(
            (start_point.x() + b.x()) / 2,
            (start_point.y() + b.y()) / 2,
        )
        # Placeholder for drawing dimensions; real implementation may vary
        painter.drawLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        painter.drawLine(a.x(), a.y(), start_point.x(), start_point.y())
        painter.drawLine(b.x(), b.y(), end_point.x(), end_point.y())
        pw = get_pen_width(painter)
        set_pen_width(painter, pw * 4)
        painter.drawLine(start_point.x() - 2, start_point.y() + 2, start_point.x() + 2, start_point.y() - 2)
        painter.drawLine(end_point.x() - 2, end_point.y() + 2, end_point.x() + 2, end_point.y() - 2)
        set_pen_width(painter, pw)

        painter.save()
        painter.translate(mid_point.x(), mid_point.y())
        rotation = mod(rotation + 90, 180) - 90
        painter.rotate(rotation)
        # painter.drawText(
        #     0,
        #     0,
        #     "I__I__I",
        # )
        painter.translate(-tw / 2, dir * th)
        painter.drawText(
            0,
            0,
            text,
        )
        painter.restore()

    def length(self):
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        return math.hypot(a.x() - b.x(), a.y() - b.y())

    def offset_point(self, p: QPoint, offset_distance=25) -> QPoint:
        a = self.segment.a
        b = self.segment.b if self._points >= 2 else self.moving_point
        # Calculate direction vector
        direction_vector = QPointF(b.x() - a.x(), b.y() - a.y())

        # Normalize the direction vector
        length = math.hypot(direction_vector.x(), direction_vector.y())
        if length == 0:
            return QPoint(p.x(), p.y())
        unit_direction_vector = QPointF(direction_vector.x() / length, direction_vector.y() / length)

        # Calculate the perpendicular vector (rotate by 90 degrees)
        perpendicular_vector = QPointF(-unit_direction_vector.y(), unit_direction_vector.x())

        # Scale the perpendicular vector by the offset distance
        offset_vector = QPointF(perpendicular_vector.x() * offset_distance, perpendicular_vector.y() * offset_distance)

        # Calculate the base point
        offsetted = QPointF(p.x() + offset_vector.x(), p.y() + offset_vector.y())

        return QPoint(offsetted.x(), offsetted.y())

    def save_to_dxf(self, dxf_document: DXFDrawing, layer_name: str):
        msp: DXFModelspace = dxf_document.modelspace()
        p1: QPoint = self.segment.a
        p2: QPoint = self.segment.b
        dim = msp.add_linear_dim(
            base=(p1.x(), p1.y()),
            p1=(p1.x(), p1.y()),
            p2=(p2.x(), p2.y()),
            location=(p2.x(), p2.y()),
            dxfattribs={
                'layer': layer_name,
                'defpoint2': (p1.x(), p1.y()),
                'defpoint3': (p2.x(), p2.y()),
            }
        )
        dim.render()

    @classmethod
    def from_dxf(cls, entity_data: DXFDimension):
        p1 = QPoint(entity_data.dxf.defpoint2.x, entity_data.dxf.defpoint2.y)
        p2 = QPoint(entity_data.dxf.defpoint3.x, entity_data.dxf.defpoint3.y)
        # print(f"entity_data.dxf.geometry: {entity_data.dxf.geometry}", flush=True)
        # print(f"entity_data.dxf.defpoint: {entity_data.dxf.defpoint}", flush=True)
        # print(f"entity_data.dxf.text_midpoint: {entity_data.dxf.text_midpoint}", flush=True)
        # print(f"entity_data.dxf.insert: {entity_data.dxf.insert}", flush=True)
        # print(f"entity_data.dxf.defpoint2: {entity_data.dxf.defpoint2}", flush=True)
        # print(f"entity_data.dxf.defpoint3: {entity_data.dxf.defpoint3}", flush=True)
        # print(f"entity_data.dxf.defpoint4: {entity_data.dxf.defpoint4}", flush=True)
        # print(f"entity_data.dxf.defpoint5: {entity_data.dxf.defpoint5}", flush=True)
        dim = Dimension()
        dim.push(p1)
        dim.push(p2)
        dim.moving_point=p2
        # start_point = QPoint(entity_data.dxf.text_midpoint.x, entity_data.dxf.text_midpoint.y)
        # end_point = QPoint(entity_data.dxf.insert.x, entity_data.dxf.insert.y)
        # return cls(start_point, end_point)
        return dim
