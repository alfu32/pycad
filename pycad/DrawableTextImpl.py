import math
from abc import ABC
from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.util_geometry import line_intersects_rect, line_contains_point, _points_equal
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace
from ezdxf.entities import Text as DXFText
from ezdxf.enums import TextEntityAlignment


class Text(Drawable, ABC):
    
    def __init__(self, start_point, end_point=None, height=1.0, text="init"):
        self.text = text
        self.start_point = start_point
        self.end_point = end_point
        self.height = height

    def isin(self,rect:QRect) -> bool:
        return rect.contains(self.start_point) or rect.contains(self.end_point)

    def intersects(self, rect: QRect) -> bool:
        return line_intersects_rect((self.start_point, self.end_point), rect)
    def set_start_point(self,value:QPoint):
        self.start_point=value

    def set_send_point(self,value:QPoint):
        self.end_point=value

    def get_hotspots(self) -> List[Tuple[HotspotClasses,QPoint,HotspotHandler]]:
        return [
            (HotspotClasses.ENDPOINT,self.start_point,self.set_start_point),
            (HotspotClasses.ENDPOINT,self.end_point,self.set_send_point),
        ]

    def get_snap_points(self) -> List[Tuple[HotspotClasses,QPoint]]:
        return [
            (HotspotClasses.ENDPOINT,self.start_point),
            (HotspotClasses.MIDPOINT, (self.start_point + self.end_point) / 2 ),
            (HotspotClasses.ENDPOINT,self.end_point),
        ]

    def update(self, painter: QPainter):
        # start_point = self.start_point
        # tw, th = get_text_dimensions(painter, self.text)
        # r = -self.get_rotation()
        # du = QPoint(tw*math.cos(r),tw*math.sin(r),)
        # self.end_point = QPoint(start_point.x() + du.x(), start_point.y() + du.y())
        pass

    def set_last_point(self, point: QPoint):
        self.end_point = point


    def contains_point(self, point):
        return line_contains_point((self.start_point, self.end_point),point)

    def intersect(self, other) -> bool:
        return False

    def is_empty(self, threshold=1.0) -> bool:
        return False

    def draw(self, painter: QPainter):
        start_point = self.start_point
        rotation_deg = (self.get_rotation() + math.pi) * 180 / math.pi
        text = f"{self.text} ({rotation_deg:.2f})"
        text = f"{self.text}"

        painter.save()
        painter.translate(start_point.x(), start_point.y())
        painter.rotate(rotation_deg)
        painter.drawText(0, 0, text)
        painter.restore()

    def length(self):
        return math.hypot(self.start_point.x() - self.end_point.x(), self.start_point.y() - self.end_point.y())

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
            (self.start_point.x(), self.start_point.y()),
            (self.end_point.x(), self.end_point.y()),
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

