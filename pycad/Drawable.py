import math
from abc import ABC, abstractmethod
import ezdxf
from PySide6.QtGui import QPainter, QFontMetrics
from PySide6.QtCore import Qt, QPoint, Signal, QPointF

from ezdxf.entities import Text as DXFText
from ezdxf.entities import Dimension as DXFDimension
from ezdxf.document import Drawing as DXFDrawing
from ezdxf.document import Modelspace as DXFModelspace
from ezdxf.enums import TextEntityAlignment

TOLERANCE = 2

lwindex = [0, 5, 9, 13, 15, 18, 20, 25,
           30, 35, 40, 50, 53, 60, 70, 80,
           90, 100, 106, 120, 140, 158, 200,
           ]
lwrindex = {0: 0, 5: 1, 9: 2, 13: 3, 15: 4, 18: 5, 20: 5, 25: 6,
            30: 7, 35: 8, 40: 9, 50: 10, 53: 11, 60: 12, 70: 13, 80: 13,
            90: 14, 100: 15, 106: 16, 120: 17, 140: 18, 158: 19, 200: 20,
            }
linetypes = {
    "Continuous": [],
    "Dashed": [10, 10],  # 10 units on, 10 units off
    "DashedLarge": [20, 10],  # 10 units on, 10 units off
    "Dotted": [1, 10],  # 1 unit on, 10 units off
    "DottedLarge": [1, 20],  # 1 unit on, 10 units off
    "DashDot": [10, 5, 1, 5],  # 10 units on, 5 units off, 1 unit on, 5 units off
    "DashDotLarge": [20, 10, 1, 10],  # 10 units on, 5 units off, 1 unit on, 5 units off
    "DashDotDot": [10, 5, 1, 5, 1, 5],  # 10 units on, 5 units off, 1 unit on, 5 units off, 1 unit on, 5 units off
    "DashDotDotLarge": [20, 10, 1, 10, 1, 10]
    # 10 units on, 5 units off, 1 unit on, 5 units off, 1 unit on, 5 units off
}

dxf_app_id = "e8ec01b43m15-PYCAD-1.0.0"


# Example function to get text dimensions
def get_text_dimensions(painter, text):
    font = painter.font()
    metrics = QFontMetrics(font)
    width = metrics.horizontalAdvance(text)
    height = metrics.height()
    return width, height


def sign(n):
    return -1 if n < 0 else 1


def mabs(n):
    return sign(n) * n


def mod(number, module):
    if module == 0:
        return number
    n = number
    m = mabs(module)
    while n > m:
        n -= m
    return n


def get_pen_width(painter: QPainter):
    # Get the current pen
    pen = painter.pen()
    # Modify the pen width
    return pen.width()


def set_pen_width(painter, width):
    # Get the current pen
    pen = painter.pen()
    # Modify the pen width
    pen.setWidth(width)
    # Set the modified pen back to the painter
    painter.setPen(pen)


class Drawable(ABC):
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point

    @abstractmethod
    def update(self, painter: QPainter):
        pass

    @abstractmethod
    def set_last_point(self, point: QPoint):
        pass

    @abstractmethod
    def intersect(self, other) -> bool:
        return False

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
    def from_dxf(cls, entity_data) -> 'Drawable':
        pass

    def get_rotation(self):
        return math.atan2(self.start_point.y() - self.end_point.y(), self.start_point.x() - self.end_point.x())


def _points_equal(start_point, end_point):
    return abs(start_point.x() - end_point.x()) <= TOLERANCE and abs(start_point.y() - end_point.y()) <= TOLERANCE


class Line(Drawable, ABC):

    def __init__(self, start_point: QPoint, end_point: QPoint):
        self.start_point: QPoint = start_point
        self.end_point: QPoint = end_point

    def update(self, painter: QPainter):
        pass

    def set_last_point(self, point: QPoint):
        self.end_point = point

    def contains_point(self, point):
        margin = 5
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.end_point.x(), self.end_point.y()
        xp, yp = point.x(), point.y()

        if min(x1, x2) - margin <= xp <= max(x1, x2) + margin and min(y1, y2) - margin <= yp <= max(y1, y2) + margin:
            distance = abs((y2 - y1) * xp - (x2 - x1) * yp + x2 * y1 - y2 * x1) / math.hypot(y2 - y1, x2 - x1)
            return distance <= margin
        return False

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


class Text(Drawable):
    def __init__(self, start_point, end_point=None, height=1.0, text="init"):
        self.text = text
        self.start_point = start_point
        self.end_point = end_point
        self.height = height

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
        margin = self.height
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.end_point.x(), self.end_point.y()
        xp, yp = point.x(), point.y()

        if min(x1, x2) - margin <= xp <= max(x1, x2) + margin and min(y1, y2) - margin <= yp <= max(y1, y2) + margin:
            distance = abs((y2 - y1) * xp - (x2 - x1) * yp + x2 * y1 - y2 * x1) / math.hypot(y2 - y1, x2 - x1)
            return distance <= margin
        return False

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


class Dimension(Drawable):
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.offset_distance = 25

    def update(self, painter: QPainter):
        pass

    def set_last_point(self, point: QPoint):
        self.end_point = point

    def contains_point(self, point):
        margin = 5
        x1, y1 = self.start_point.x(), self.start_point.y()
        x2, y2 = self.end_point.x(), self.end_point.y()
        xp, yp = point.x(), point.y()

        if min(x1, x2) - margin <= xp <= max(x1, x2) + margin and min(y1, y2) - margin <= yp <= max(y1, y2) + margin:
            distance = abs((y2 - y1) * xp - (x2 - x1) * yp + x2 * y1 - y2 * x1) / math.hypot(y2 - y1, x2 - x1)
            return distance <= margin
        return False

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
