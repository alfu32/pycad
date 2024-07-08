from typing import List, Tuple

from PySide6.QtCore import QPoint, Qt, Signal, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QFont, QTransform, QPen
from PySide6.QtWidgets import QWidget, QInputDialog

from pycad.ComponentLayers import LayerModel
from pycad.Drawable import Drawable, HotspotClasses, HotspotHandler
from pycad.DrawableDimensionImpl import Dimension
from pycad.DrawableLineImpl import Line
from pycad.DrawableTextImpl import Text
from pycad.constants import linetypes
from pycad.util_drawable import draw_rect, draw_hotspot_class, draw_cursor, draw_point
from pycad.util_geometry import find_nearest_point, snap_to_angle
from pycad.util_math import distance, floor_to_nearest, ceil_to_nearest


class DrawingManager(QWidget):
    changed = Signal(object)  # Define a custom signal with a generic object type

    def __init__(self, filename: str):
        super().__init__()
        self.setMouseTracking(True)
        self.setCursor(Qt.BlankCursor)
        self.layers = [LayerModel(name="0")]
        self.current_layer_index = 0
        self.current_drawable: Drawable = None
        self.zoom_factor = 1.0
        self.offset = QPoint(0, 0)
        self.flSnapGrid = True
        self.gridSpacing = QPoint(25, 25)
        self.flSnapPoints = True
        self.snapDistance = 5
        self.model_point_snapped = QPoint(0, 0)
        self.model_point_raw = QPoint(0, 0)
        self.screen_point_raw = QPoint(0, 0)
        self.screen_point_snapped = QPoint(0, 0)
        self.mode = "line"  # Default mode
        self.font_family = "Arial"  # Default mode

    def set_mode(self, mode):
        self.mode = mode

    def set_current_layer(self, index):
        self.current_layer_index = index
        self.changed.emit(self.layers)

    def add_layer(self, layer):
        self.layers.append(layer)
        self.changed.emit(self.layers)

    def remove_layer(self, index):
        if len(self.layers) > 1:
            del self.layers[index]
            if self.current_layer_index >= len(self.layers):
                self.current_layer_index = len(self.layers) - 1
            self.changed.emit(self.layers)

    def wheelEvent(self, event):
        mouse_pos = event.position().toPoint()
        scene_pos = self.map_to_scene(mouse_pos)

        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.1
        else:
            factor = 0.9

        self.zoom_factor *= factor

        new_scene_pos = self.map_to_view(scene_pos)
        self.offset += mouse_pos - new_scene_pos

        self.update()

    def map_to_scene(self, point):
        return (point - self.offset) / self.zoom_factor

    def map_to_view(self, point):
        return point * self.zoom_factor + self.offset

    def current_layer(self, ):
        return self.layers[self.current_layer_index]

    def apply_snaps(self, pos: QPoint) -> QPoint:
        p = QPoint(pos.x(), pos.y())
        nearest_point = find_nearest_point([sp[1] for sp in self.get_snap_points( p )], pos)
        if nearest_point is not None and distance(nearest_point, pos) <= (self.snapDistance / self.zoom_factor):
            p = QPoint(nearest_point.x(), nearest_point.y())
        self.model_point_snapped = QPoint(p.x(), p.y())
        return p

    def update_mouse_positions(self, event: QMouseEvent):
        self.screen_point_raw = event.pos()
        self.model_point_raw = self.map_to_scene(event.pos())
        self.model_point_snapped = self.apply_snaps(self.model_point_raw)
        self.screen_point_snapped = self.map_to_view(self.model_point_snapped)

    def create_drawable(self, p1: QPoint, p2: QPoint) -> Drawable:
        if self.mode == 'line':
            return Line(p1, p2)
        elif self.mode == 'text':
            t = Text(p1, p2, 25, "I__________I")
            return t
        elif self.mode == 'dimension':
            return Dimension(p1, p2)

    def mousePressEvent(self, event: QMouseEvent):
        self.update_mouse_positions(event)
        if event.button() == Qt.LeftButton:
            layer = self.current_layer()
            self.current_drawable = self.create_drawable(
                self.model_point_snapped,
                self.model_point_snapped,
            )
        elif event.button() == Qt.RightButton:
            layer = self.current_layer()
            for line in layer.drawables:
                if line.contains_point(self.model_point_raw):
                    layer.drawables.remove(line)
                    self.update()
        self.changed.emit(self.layers)

    def mouseMoveEvent(self, event):
        self.update_mouse_positions(event)
        if self.current_drawable:
            end_point = self.model_point_snapped
            if event.modifiers() & Qt.ControlModifier:
                end_point = snap_to_angle(self.current_drawable.start_point, end_point)
            self.current_drawable.end_point = end_point
            # Update line color and width to match the current layer
            layer = self.layers[self.current_layer_index]
            self.current_drawable.color = layer.color
            self.current_drawable.width = layer.lineweight
        self.update()

    def mouseReleaseEvent(self, event):
        self.update_mouse_positions(event)
        if self.current_drawable:
            end_point = self.model_point_snapped
            if event.modifiers() & Qt.ControlModifier:
                end_point = snap_to_angle(self.current_drawable.start_point, end_point)
            self.current_drawable.end_point = end_point
            if isinstance(self.current_drawable, Text):
                text, ok = QInputDialog.getText(self, 'Text', ':')
                self.current_drawable.text = text
            self.layers[self.current_layer_index].add_drawable(self.current_drawable)
            self.current_drawable = None
        self.changed.emit(self.layers)
        self.update()

    def paintEvent(self, event):
        painter: QPainter = QPainter(self)
        font = QFont(self.font_family, 12)  # 12 is the font size
        painter.setFont(font)
        for drawable in self.get_drawables():
            drawable.update(painter)

        # Draw endpoint markers
        for hotspot in self.get_hotspots( self.model_point_raw ):
            cls,p,updater = hotspot
            if isinstance(p, QPoint):
                draw_rect(painter, self.map_to_view(p))

        # Draw endpoint markers
        for snap_point in self.get_snap_points( self.model_point_raw ):
            cls,p = snap_point
            if isinstance(p, QPoint):
                draw_hotspot_class(painter,cls, self.map_to_view(p))

        if self.current_drawable:
            draw_rect(painter, self.map_to_view(self.current_drawable.start_point))
            if isinstance(self.current_drawable.end_point, QPoint):
                draw_rect(painter, self.map_to_view(self.current_drawable.end_point))

        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        for layer in self.layers:
            if not layer.visible:
                continue
            pen = QPen(layer.color, layer.lineweight / self.zoom_factor, Qt.SolidLine)
            pen.setDashPattern(linetypes[layer.linetype])
            painter.setPen(pen)
            for drawable in layer.drawables:
                drawable.draw(painter)
        if self.current_drawable:
            layer = self.current_layer()
            pen = QPen(self.current_layer().color, self.current_layer().lineweight / self.zoom_factor, Qt.SolidLine)

            pen.setDashPattern(linetypes[layer.linetype])
            painter.setPen(pen)
            self.current_drawable.draw(painter)

        # if self.flSnapGrid:
        #     self.draw_local_grid(painter, self.model_point_snapped, 0x111111)
        # Reset transformation to draw crosses in screen coordinates
        painter.setTransform(QTransform())
        draw_cursor(painter, self.screen_point_snapped, self.snapDistance)

    def get_drawables(self, rect:QRect=None) -> List[Drawable]:
        drawables:List[Drawable] = []
        for layer in self.layers:
            if not layer.visible:
                continue
            for drawable in layer.drawables:
                if rect is None or rect is not None and drawable.intersects(rect):
                    drawables.append( drawable )
        return drawables

    def get_hotspots(self, pos:QPoint):
        rect:QRect =QRect(pos.x()-50,pos.y()-50,100,100)
        hotspots:List[Tuple[HotspotClasses,QPoint,HotspotHandler]] = []
        for drawable in self.get_drawables(rect):
            for hs in drawable.get_hotspots():
                hotspots.append( hs )
        return hotspots

    def get_snap_points(self, pos:QPoint) -> List[Tuple[HotspotClasses,QPoint]]:
        snap_points:List[Tuple[HotspotClasses,QPoint]] = []
        rect:QRect =QRect(pos.x()-50,pos.y()-50,100,100)
        p = pos
        X = p.x()
        Y = p.y()
        if pos is not None and self.flSnapGrid:
            snap_points.append((
                HotspotClasses.GRID,
                QPoint(floor_to_nearest(X, self.gridSpacing.x()),floor_to_nearest(Y, self.gridSpacing.y()))
            ))
            snap_points.append((
                HotspotClasses.GRID,
                QPoint(ceil_to_nearest(X, self.gridSpacing.x()), floor_to_nearest(Y, self.gridSpacing.y()))
            ))
            snap_points.append((
                HotspotClasses.GRID,
                QPoint(floor_to_nearest(X, self.gridSpacing.x()), ceil_to_nearest(Y, self.gridSpacing.y()))
            ))
            snap_points.append((
                HotspotClasses.GRID,
                QPoint(ceil_to_nearest(X, self.gridSpacing.x()), ceil_to_nearest(Y, self.gridSpacing.y()))
            ))
        if self.flSnapPoints:
            for drawable in self.get_drawables(rect):
                for sp in drawable.get_snap_points():
                    snap_points.append( sp )
        return snap_points

    def get_all_lines(self):
        lines = []
        for layer in self.layers:
            for line in layer.drawables:
                lines.append(line)
        return lines

    def draw_local_grid(self, painter: QPainter, center: QPoint, color: int):
        dx = self.gridSpacing.x()
        dy = self.gridSpacing.y()
        NX = dx * 10
        NY = dy * 10
        cx = round(center.x() / NX ) * NX
        cy = round(center.y() / NY ) * NY
        for ix in range(3):
            for iy in range(3):
                draw_point(painter, QPoint(cx + ix * dx, cy + iy * dy), color)
                draw_point(painter, QPoint(cx + ix * dx, cy - iy * dy), color)
                draw_point(painter, QPoint(cx - ix * dx, cy + iy * dy), color)
                draw_point(painter, QPoint(cx - ix * dx, cy - iy * dy), color)

