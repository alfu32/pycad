import math

import ezdxf
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QPen, Qt, QColor

from pycad.Drawable import HotspotClasses


def qcolor_to_dxf_color(color):
    r = color.red()
    g = color.green()
    b = color.blue()
    return (r << 16) + (g << 8) + b


def get_true_color(dxf_layer: ezdxf.sections.table.Layer):
    if dxf_layer.has_dxf_attrib('true_color'):
        true_color = dxf_layer.dxf.true_color
        return true_color
    else:
        return 0x000000




def draw_cross(painter: QPainter, point: QPoint):
    x = point.x()
    y = point.y()
    pen = QPen(QColor(Qt.red), 2, Qt.SolidLine)
    painter.setPen(pen)
    size = 4
    painter.drawLine(x - size, y - size, x + size, y + size)
    painter.drawLine(x + size, y - size, x - size, y + size)


def draw_point(painter: QPainter, point: QPoint, color: int = Qt.red):
    x = point.x()
    y = point.y()
    size = 2
    pen = QPen(QColor(color), size, Qt.SolidLine)
    painter.setPen(pen)
    painter.drawRect(x - 0.5, y - 0.5, 1.0, 1.0)


def draw_rect(painter: QPainter, point: QPoint):
    pen = QPen(QColor(Qt.blue), 1, Qt.SolidLine)
    painter.setPen(pen)
    color: QColor = QColor(0x0055ff)
    size = 4
    painter.fillRect(point.x() - size, point.y() - size, 2 * size, 2 * size, color)
    painter.drawRect(point.x() - size, point.y() - size, 2 * size, 2 * size)

def draw_hotspot_class(painter: QPainter,hs_class:HotspotClasses, point: QPoint):
    pen = QPen(QColor(Qt.red), 2, Qt.SolidLine)
    painter.setPen(pen)
    size = 10
    x = point.x()
    y=point.y()
    if hs_class == HotspotClasses.ENDPOINT:
        painter.drawRect(x - size, y - size, 2 * size, 2 * size)
    elif hs_class == HotspotClasses.GRID:
        painter.drawLine(x, y - size, x, y + size)
        painter.drawLine(x - size, y, x + size, y)
    elif hs_class == HotspotClasses.MIDPOINT:
        u=2*math.pi/3
        w=math.pi/6
        a=QPoint(math.ceil(x + size*math.cos(w+u)),math.ceil(y + size*math.sin(w+u)))
        b=QPoint(math.ceil(x + size*math.cos(w+2*u)),math.ceil(y + size*math.sin(w+2*u)))
        c=QPoint(math.ceil(x + size*math.cos(w+3*u)),math.ceil(y + size*math.sin(w+3*u)))
        painter.drawLine(a.x(),a.y(),b.x(),b.y())
        painter.drawLine(b.x(),b.y(),c.x(),c.y())
        painter.drawLine(c.x(),c.y(),a.x(),a.y())
    elif hs_class == HotspotClasses.PERPENDICULAR:
        painter.drawEllipse(point, size // 2, size // 2)
    elif hs_class == HotspotClasses.TOUCHING:
        painter.drawEllipse(point, size, size)
    else:
        painter.drawEllipse(point, size, size)

def draw_cursor(painter: QPainter, point: QPoint, size: int):
    x = point.x()
    y = point.y()
    pen = QPen(QColor(Qt.black), 1, Qt.SolidLine)
    painter.setPen(pen)
    painter.drawLine(x - 3 * size, y, x + 3 * size, y)
    painter.drawLine(x, y - 3 * size, x, y + 3 * size)
    painter.drawRect(x - size, y - size, 2 * size, 2 * size)
    # painter.drawArc(x - size, y - size, 2*size, 2*size, 1, math.pi)
