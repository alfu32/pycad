import math
from typing import List, Tuple, Optional, Protocol

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter, QFontMetrics

from pycad.constants import TOLERANCE
from pycad.util_math import distance, mabs


def find_nearest_point(point_list: List[QPoint], p: QPoint) -> QPoint:
    if len(point_list) == 0:
        return p

    nearest_point = point_list[0]
    min_distance = distance(point_list[0], p)

    for point in point_list[1:]:
        dist = distance(point, p)
        if dist < min_distance:
            nearest_point = point
            min_distance = dist

    return nearest_point


def sort_points_on_line(line: 'HasSegment', points):
    def distance_to_start(p):
        return math.hypot(p.x() - line.segment.a.x(), p.y() - line.segment.a.y())

    return sorted(points, key=distance_to_start)


def snap_to_angle(start_point, end_point):
    dx = end_point.x() - start_point.x()
    dy = end_point.y() - start_point.y()
    angle = math.atan2(dy, dx)
    snap_angle = round(angle / (math.pi / 12)) * (math.pi / 12)
    length = math.hypot(dx, dy)
    snapped_end_point = QPoint(
        start_point.x() + length * math.cos(snap_angle),
        start_point.y() + length * math.sin(snap_angle)
    )
    return snapped_end_point


def _points_equal(start_point: QPoint, end_point: QPoint) -> bool:
    return abs(start_point.x() - end_point.x()) <= TOLERANCE and abs(start_point.y() - end_point.y()) <= TOLERANCE


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


def line_intersects_rect(line: Tuple[QPoint, QPoint], rect: QRect) -> bool:
    start_point, end_point = line
    # Check if either endpoint is inside the rectangle
    if rect.contains(start_point) or rect.contains(end_point):
        return True

    # Helper function to check if two line segments intersect
    def lines_intersect(p1, p2, q1, q2):
        def ccw(a, b, c):
            return (c.y() - a.y()) * (b.x() - a.x()) > (b.y() - a.y()) * (c.x() - a.x())

        return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)

    # Check intersection with each edge of the rectangle
    top_left = rect.topLeft()
    top_right = rect.topRight()
    bottom_left = rect.bottomLeft()
    bottom_right = rect.bottomRight()

    edges = [
        (top_left, top_right),
        (top_right, bottom_right),
        (bottom_right, bottom_left),
        (bottom_left, top_left)
    ]

    for edge in edges:
        if lines_intersect(start_point, end_point, edge[0], edge[1]):
            return True

    return False


def line_contains_point(line: Tuple[QPoint, QPoint], point: QPoint) -> bool:
    start_point, end_point = line
    margin = 5
    x1, y1 = start_point.x(), start_point.y()
    x2, y2 = end_point.x(), end_point.y()
    xp, yp = point.x(), point.y()

    if min(x1, x2) - margin <= xp <= max(x1, x2) + margin and min(y1, y2) - margin <= yp <= max(y1, y2) + margin:
        distance = abs((y2 - y1) * xp - (x2 - x1) * yp + x2 * y1 - y2 * x1) / math.hypot(y2 - y1, x2 - x1)
        return distance <= margin
    return False


# Example function to get text dimensions
def get_text_dimensions(painter, text):
    font = painter.font()
    metrics = QFontMetrics(font)
    width = metrics.horizontalAdvance(text)
    height = metrics.height()
    return width, height


class Segment:
    a: QPoint = QPoint(0, 0)
    b: QPoint = QPoint(0, 0)

    def __init__(self, a: QPoint, b: QPoint):
        self.a = a
        self.b = b

    def set_a(self, p):
        self.a = p

    def set_b(self, p):
        self.b = p

    def set(self, a: QPoint, b: QPoint) -> 'Segment':
        self.a = a
        self.b = b
        return self

    def is_in(self, rect: QRect) -> bool:
        return rect.contains(self.a) or rect.contains(self.b)

    def intersects(self, rect: QRect) -> bool:
        return line_intersects_rect((self.a, self.b), rect)

    def contains_point(self, point):
        return line_contains_point((self.a, self.b), point)

    def intersect(self, other: 'Segment') -> Optional[QPoint]:
        def ccw(A, B, C):
            return (C.y() - A.y()) * (B.x() - A.x()) > (B.y() - A.y()) * (C.x() - A.x())

        A = self.a
        B = self.b
        C = other.a
        D = other.b

        if ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D):
            denom = (A.x() - B.x()) * (C.y() - D.y()) - (A.y() - B.y()) * (C.x() - D.x())
            if denom == 0:
                return None
            intersect_x = ((A.x() * B.y() - A.y() * B.x()) * (C.x() - D.x()) - (A.x() - B.x()) * (
                    C.x() * D.y() - C.y() * D.x())) / denom
            intersect_y = ((A.x() * B.y() - A.y() * B.x()) * (C.y() - D.y()) - (A.y() - B.y()) * (
                    C.x() * D.y() - C.y() * D.x())) / denom
            return QPoint(int(intersect_x), int(intersect_y))
        return None

    def __eq__(self, other: 'Segment'):
        if not isinstance(other, Segment):
            return False
        return (_points_equal(self.a, other.a) and _points_equal(self.b, other.b)) or \
            (_points_equal(self.a, other.b) and _points_equal(self.b, other.a))


class HasSegment(Protocol):
    segment: Segment


class HasPoints(Protocol):
    points: List[QPoint] = []
    moving_point: QPoint = None
    max_points: int = 2
