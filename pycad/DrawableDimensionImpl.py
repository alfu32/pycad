import math
from abc import ABC

from typing import List, Tuple

from PySide6.QtCore import QPoint, QRect, QPointF
from PySide6.QtGui import QPainter

from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace
from ezdxf.entities import Dimension as DXFDimension
from pycad.util_geometry import line_intersects_rect, line_contains_point, get_text_dimensions, \
    get_pen_width, set_pen_width, mod

class Dimension(Drawable, ABC):
    
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.offset_distance = 25


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
        pass

    def set_last_point(self, point: QPoint):
        self.end_point = point


    def contains_point(self, point):
        return line_contains_point((self.start_point, self.end_point),point)

    def intersect(self, other) -> bool:
        return False

    def is_empty(self, threshold=1.0) -> bool:
        return False

    def get_rotation(self):
        return math.atan2(self.start_point.y() - self.end_point.y(), self.start_point.x() - self.end_point.x())
        # return math.atan2(self.end_point.y() - self.start_point.y(), self.start_point.x() - self.end_point.x())
        # return math.atan2(self.end_point.y() - self.start_point.y(), self.end_point.x() - self.start_point.x())

    def draw(self, painter: QPainter):
        start_point = self.offset_point(self.start_point, self.offset_distance)
        end_point = self.offset_point(self.end_point, self.offset_distance)
        rotation = (self.get_rotation() + math.pi) * 180 / math.pi
        dir = -1 if 90 < rotation <= 270 else 0.5
        text = f"{self.length():.2f} ({rotation:.2f} [{dir}])"
        text = f"{self.length():.1f}"
        tw, th = get_text_dimensions(painter, text)
        mid_point = QPoint(
            (start_point.x() + self.end_point.x()) / 2,
            (start_point.y() + self.end_point.y()) / 2,
        )
        # Placeholder for drawing dimensions; real implementation may vary
        painter.drawLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        painter.drawLine(self.start_point.x(), self.start_point.y(), start_point.x(), start_point.y())
        painter.drawLine(self.end_point.x(), self.end_point.y(), end_point.x(), end_point.y())
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
        return math.hypot(self.start_point.x() - self.end_point.x(), self.start_point.y() - self.end_point.y())

    def offset_point(self, p: QPoint, offset_distance=25) -> QPoint:
        # Calculate direction vector
        direction_vector = QPointF(self.end_point.x() - self.start_point.x(), self.end_point.y() - self.start_point.y())

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
        p1: QPoint = self.start_point
        p2: QPoint = self.end_point
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
        return cls(p1, p2)
        # start_point = QPoint(entity_data.dxf.text_midpoint.x, entity_data.dxf.text_midpoint.y)
        # end_point = QPoint(entity_data.dxf.insert.x, entity_data.dxf.insert.y)
        # return cls(start_point, end_point)
