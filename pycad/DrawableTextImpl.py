import math
from abc import ABC
from typing import List, Tuple, Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.util_geometry import line_intersects_rect, line_contains_point, _points_equal, HasSegment, Segment
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace
from ezdxf.entities import Text as DXFText
from ezdxf.enums import TextEntityAlignment


class Text(Drawable, ABC):

    def __init__(self, start_point: QPoint, end_point: QPoint = None, height=1.0, text="init"):
        super(Drawable, self).__init__()
        self.text = text
        self.height = height
        self.segment: Segment = Segment(start_point,end_point)
        self.segment.set(start_point,end_point)

    def is_done(self):
        return self.segment.a != self.segment.b

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
        # start_point = self.segment.a
        # tw, th = get_text_dimensions(painter, self.text)
        # r = -self.get_rotation()
        # du = QPoint(tw*math.cos(r),tw*math.sin(r),)
        # self.segment.b = QPoint(start_point.x() + du.x(), start_point.y() + du.y())
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

    def draw(self, painter: QPainter):
        start_point = self.segment.a
        rotation_deg = (self.get_rotation() + math.pi) * 180 / math.pi
        text = f"{self.text} ({rotation_deg:.2f})"
        text = f"{self.text}"

        painter.save()
        painter.translate(start_point.x(), start_point.y())
        painter.rotate(rotation_deg)
        painter.drawText(0, 0, text)
        painter.restore()

    def length(self):
        return math.hypot(self.segment.a.x() - self.segment.b.x(), self.segment.a.y() - self.segment.b.y())

    def save_to_dxf(self, dxf_document: DXFDrawing, layer_name: str):
        msp: DXFModelspace = dxf_document.modelspace()
        text_entity: DXFText = msp.add_text(
            self.text,
            dxfattribs={
                'height': self.height,
                'rotation': (self.get_rotation() + math.pi) * 180 / math.pi,
                'width': self.length(),
                'layer': layer_name,
            }
        )
        align: TextEntityAlignment = TextEntityAlignment.LEFT
        text_entity.set_placement(
            (self.segment.a.x(), self.segment.a.y()),
            (self.segment.b.x(), self.segment.b.y()),
            align=align
        )
        # text_entity.set_pos((self.position.x(), self.position.y()), align='LEFT')

    @classmethod
    def from_dxf(cls, entity_data: DXFText):
        width = entity_data.dxf.get("width", 25)
        rotation = entity_data.dxf.get("rotation", 0)
        p1 = QPoint(entity_data.dxf.insert.x, entity_data.dxf.insert.y)
        a = rotation * math.pi / 180
        dp = QPoint(width * math.cos(a), width * math.sin(a))
        p2 = QPoint(p1.x() + dp.x(), p1.y() + dp.y(), )
        text_instance = cls(p1, p2, entity_data.dxf.height)
        text_instance.text = entity_data.dxf.text
        return text_instance
