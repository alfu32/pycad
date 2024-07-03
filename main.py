import sys
import math
import time
from typing import List

import ezdxf
from PyQt5.uic.properties import QtCore
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QColorDialog, QSpinBox, QListWidget, QListWidgetItem,
    QLineEdit, QCheckBox, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QStyle, QLabel,
)
from PySide6.QtGui import QPainter, QPen, QColor, QTransform, QMouseEvent
from PySide6.QtCore import Qt, QPoint
from ezdxf.sections.table import (
    LayerTable, Layer
)

TOLERANCE = 2

lwindex = [0, 5, 9, 13, 15, 18, 20, 25,
           30, 35, 40, 50, 53, 60, 70, 80,
           90, 100, 106, 120, 140, 158, 200,
           ]
lwrindex = {0: 0, 5: 1, 9: 2, 13: 3, 15: 4, 18: 5, 20: 5, 25: 6,
            30: 7, 35: 8, 40: 9, 50: 10, 53: 11, 60: 12, 70: 13, 80: 13,
            90: 14, 100: 15, 106: 16, 120: 17, 140: 18, 158: 19, 200: 20,
            }


def round_to_nearest(value, base):
    return base * round(value / base)


def distance(point1, point2):
    return math.sqrt((point1.x() - point2.x()) ** 2 + (point1.y() - point2.y()) ** 2)


def find_nearest_point(point_list: List[QPoint], p: QPoint) -> QPoint:
    nearest_point = point_list[0]
    min_distance = distance(point_list[0], p)

    for point in point_list[1:]:
        dist = distance(point, p)
        if dist < min_distance:
            nearest_point = point
            min_distance = dist

    return nearest_point


class Line:
    def __init__(self, start_point, end_point, color, width):
        self.start_point = start_point
        self.end_point = end_point
        self.color = color
        self.width = width

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

    def _points_equal(self, p1, p2):
        return abs(p1.x() - p2.x()) <= TOLERANCE and abs(p1.y() - p2.y()) <= TOLERANCE

    def is_short(self, threshold=1.0):
        length = math.hypot(self.start_point.x() - self.end_point.x(), self.start_point.y() - self.end_point.y())
        return length < threshold

    def __eq__(self, other):
        if not isinstance(other, Line):
            return False
        return (self._points_equal(self.start_point, other.start_point) and self._points_equal(self.end_point,
                                                                                               other.end_point)) or \
            (self._points_equal(self.start_point, other.end_point) and self._points_equal(self.end_point,
                                                                                          other.start_point))

    def __hash__(self):
        start_tuple = (self.start_point.x(), self.start_point.y())
        end_tuple = (self.end_point.x(), self.end_point.y())
        return hash((min(start_tuple, end_tuple), max(start_tuple, end_tuple)))


class LayerModel:
    def __init__(self, name="Layer", color=QColor(Qt.black), width=2, visible=True):
        self.name = name
        self.color = color
        self.width = width
        self.visible = visible
        self.lines = []
        self.flAutoCut = True

    def add_line(self, line):
        self.lines.append(line)
        self.cleanup()

    def cleanup(self):
        if self.flAutoCut:
            self.rescan_intersections()
        self.remove_short_lines()
        self.cleanup_duplicates()

    def rescan_intersections(self):
        intersection_table = []
        for i, line1 in enumerate(self.lines):
            for j, line2 in enumerate(self.lines):
                if i < j:
                    intersect_point = line1.intersect(line2)
                    if intersect_point:
                        intersection_table.append((i, intersect_point))
                        intersection_table.append((j, intersect_point))

        intersection_groups = {}
        for line_idx, intersect_point in intersection_table:
            if line_idx not in intersection_groups:
                intersection_groups[line_idx] = []
            intersection_groups[line_idx].append(intersect_point)

        new_lines = []
        for line_idx, intersect_points in intersection_groups.items():
            line = self.lines[line_idx]
            sorted_points = self.sort_points_on_line(line, intersect_points)
            new_lines.extend(self.split_line_by_points(line, sorted_points))

        self.lines = [line for idx, line in enumerate(self.lines) if idx not in intersection_groups]
        self.lines.extend(new_lines)

    def sort_points_on_line(self, line, points):
        def distance_to_start(p):
            return math.hypot(p.x() - line.start_point.x(), p.y() - line.start_point.y())

        return sorted(points, key=distance_to_start)

    def split_line_by_points(self, line, points):
        segments = []
        start = line.start_point
        for point in points:
            segments.append(Line(start, point, line.color, line.width))
            start = point
        segments.append(Line(start, line.end_point, line.color, line.width))
        return segments

    def cleanup_duplicates(self):
        unique_lines = set(self.lines)
        self.lines = list(unique_lines)

    def remove_short_lines(self):
        self.lines = [line for line in self.lines if not line.is_short()]


class DrawingManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setCursor(Qt.BlankCursor)
        self.layers = [LayerModel(name="Layer-0")]
        self.current_layer_index = 0
        self.current_line = None
        self.zoom_factor = 1.0
        self.offset = QPoint(0, 0)
        self.dxf_file = None
        self.flSnapGrid = True
        self.gridSpacing = QPoint(10, 10)
        self.flSnapPoints = True
        self.snapDistance = 5
        self.model_point_snapped = QPoint(0, 0)
        self.model_point_raw = QPoint(0, 0)
        self.screen_point_raw = QPoint(0, 0)
        self.screen_point_snapped = QPoint(0, 0)

    def set_current_layer(self, index):
        self.current_layer_index = index

    def add_layer(self, layer):
        self.layers.append(layer)

    def remove_layer(self, index):
        if len(self.layers) > 1:
            del self.layers[index]
            if self.current_layer_index >= len(self.layers):
                self.current_layer_index = len(self.layers) - 1
            self.save_dxf()

    def get_true_color(self, dxf_layer: ezdxf.sections.table.Layer):
        if dxf_layer.has_dxf_attrib('true_color'):
            true_color = dxf_layer.dxf.true_color
            return true_color
        else:
            return 0x000000

    def load_dxf(self, file_path):
        self.layers = []
        doc = ezdxf.readfile(file_path)
        doc_layers: LayerTable = doc.layers
        for dxf_layer in doc_layers:
            color = QColor(self.get_true_color(dxf_layer))
            width0 = dxf_layer.dxf.lineweight if dxf_layer.dxf.hasattr('lineweight') else 1
            width = lwrindex[width0] if width0 >=0 else lwrindex[5]
            layer = LayerModel(name=dxf_layer.dxf.name, color=color, width=width,
                               visible=True)
            self.layers.append(layer)

        for entity in doc.entities:
            if entity.dxftype() == 'LINE':
                start_point = QPoint(entity.dxf.start.x, entity.dxf.start.y)
                end_point = QPoint(entity.dxf.end.x, entity.dxf.end.y)
                color = QColor(entity.dxf.color) if entity.dxf.hasattr('color') else QColor(Qt.black)
                width = entity.dxf.lineweight if entity.dxf.hasattr('lineweight') else 1
                line = Line(start_point, end_point, color, width)
                layer_name = entity.dxf.layer
                for layer in self.layers:
                    if layer.name == layer_name:
                        layer.add_line(line)
                        break

        self.current_layer_index = 0

    def qcolor_to_dxf_color(self, color):
        r = color.red()
        g = color.green()
        b = color.blue()
        return (r << 16) + (g << 8) + b

    def save_dxf(self):
        if not self.dxf_file:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.dxf_file = f"drawing_{timestamp}.dxf"

        doc = ezdxf.new()
        for index, layer in enumerate(self.layers):
            if layer.name != '0' and layer.name != 'Defpoints':
                doc.layers.add(
                    name=layer.name,
                    true_color=self.qcolor_to_dxf_color(layer.color),
                    lineweight=lwindex[layer.width]
                )
            for line in layer.lines:
                doc.modelspace().add_line(
                    (line.start_point.x(), line.start_point.y()),
                    (line.end_point.x(), line.end_point.y()),
                    dxfattribs={
                        'layer': layer.name,
                        'color': self.qcolor_to_dxf_color(layer.color),
                        'lineweight': lwindex[layer.width]
                    }
                )

        doc.saveas(self.dxf_file)

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

    def apply_mouse_input_modifiers(self, pos: QPoint) -> QPoint:
        p = QPoint(pos.x(), pos.y())
        if self.flSnapPoints:
            nearest_point = find_nearest_point(self.get_all_points(), pos)
            if nearest_point is not None and distance(nearest_point, pos) <= (self.snapDistance/self.zoom_factor):
                p = QPoint(nearest_point.x(), nearest_point.y())
        if self.flSnapGrid:
            p = QPoint(round_to_nearest(pos.x(), self.gridSpacing.x()), round_to_nearest(pos.y(), self.gridSpacing.y()))
        self.model_point_snapped = QPoint(p.x(), p.y())
        return p

    def update_mouse_positions(self, event: QMouseEvent):
        self.screen_point_raw = event.pos()
        self.model_point_raw = self.map_to_scene(event.pos())
        self.model_point_snapped = self.apply_mouse_input_modifiers(self.model_point_raw)
        self.screen_point_snapped = self.map_to_view(self.model_point_snapped)

    def mousePressEvent(self, event: QMouseEvent):
        self.update_mouse_positions(event)
        if event.button() == Qt.LeftButton:
            layer = self.layers[self.current_layer_index]
            self.current_line = Line(self.model_point_snapped, self.model_point_snapped, layer.color, layer.width)
        elif event.button() == Qt.RightButton:
            clayer = self.current_layer()
            for line in clayer.lines:
                if line.contains_point(self.model_point_raw):
                    clayer.lines.remove(line)
                    self.update()
                    self.save_dxf()
                    return

    def mouseMoveEvent(self, event):
        self.update_mouse_positions(event)
        if self.current_line:
            end_point = self.model_point_snapped
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            # Update line color and width to match the current layer
            layer = self.layers[self.current_layer_index]
            self.current_line.color = layer.color
            self.current_line.width = layer.width
        self.update()

    def mouseReleaseEvent(self, event):
        self.update_mouse_positions(event)
        if self.current_line:
            end_point = self.model_point_snapped
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            self.layers[self.current_layer_index].add_line(self.current_line)
            self.current_line = None
            self.save_dxf()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw endpoint markers
        for layer in self.layers:
            if not layer.visible:
                continue
            for line in layer.lines:
                self.draw_rect(painter, self.map_to_view(line.start_point))
                self.draw_rect(painter, self.map_to_view(line.end_point))

        if self.current_line:
            self.draw_rect(painter, self.map_to_view(self.current_line.start_point))
            self.draw_rect(painter, self.map_to_view(self.current_line.end_point))

        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        for layer in self.layers:
            if not layer.visible:
                continue
            for line in layer.lines:
                pen = QPen(layer.color, layer.width / self.zoom_factor, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawLine(line.start_point, line.end_point)
        if self.current_line:
            pen = QPen(self.current_layer().color, self.current_layer().width / self.zoom_factor, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.current_line.start_point, self.current_line.end_point)

        # Reset transformation to draw crosses in screen coordinates
        painter.setTransform(QTransform())
        self.draw_cursor(painter, self.screen_point_snapped)

    def draw_cross(self, painter: QPainter, point: QPoint):
        x = point.x()
        y = point.y()
        pen = QPen(QColor(Qt.red), 2, Qt.SolidLine)
        painter.setPen(pen)
        size = 4
        painter.drawLine(x - size, y - size, x + size, y + size)
        painter.drawLine(x + size, y - size, x - size, y + size)

    def draw_rect(self, painter: QPainter, point: QPoint):
        pen = QPen(QColor(Qt.blue), 1, Qt.SolidLine)
        painter.setPen(pen)
        color: QColor = QColor(0x0055ff)
        size = 4
        painter.fillRect(point.x() - size, point.y() - size, 2 * size, 2 * size, color)
        painter.drawRect(point.x() - size, point.y() - size, 2 * size, 2 * size)

    def draw_cursor(self, painter: QPainter, point: QPoint):
        x = point.x()
        y = point.y()
        pen = QPen(QColor(Qt.black), 1, Qt.SolidLine)
        painter.setPen(pen)
        size = 8
        painter.drawLine(x - 2 * size, y, x + 2 * size, y)
        painter.drawLine(x, y - 2 * size, x, y + 2 * size)
        painter.drawRect(x - size / 2, y - size / 2, size, size)

    def snap_to_angle(self, start_point, end_point):
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

    def get_all_points(self):
        points = []
        for layer in self.layers:
            for line in layer.lines:
                points.append(line.start_point)
                points.append(line.end_point)
        return points


class LayerItem(QWidget):
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.parent = parent

        layout = QHBoxLayout()

        self.radio_button = QRadioButton()
        self.radio_button.setChecked(parent.canvas.current_layer_index == parent.canvas.layers.index(layer))
        self.radio_button.toggled.connect(self.on_radio_button_toggled)
        layout.addWidget(self.radio_button)

        self.name_input = QLineEdit(self.layer.name)
        self.name_input.textChanged.connect(self.on_name_changed)
        layout.addWidget(self.name_input)

        self.width_input = QSpinBox()
        self.width_input.setValue(self.layer.width)
        self.width_input.valueChanged.connect(self.on_width_changed)
        layout.addWidget(self.width_input)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {self.layer.color.name()}")
        self.color_button.clicked.connect(self.select_color)
        layout.addWidget(self.color_button)

        self.visibility_label = QLabel()
        self.visibility_label.setText("visible")
        layout.addWidget(self.visibility_label)

        self.visibility_checkbox = QCheckBox()
        self.visibility_checkbox.setChecked(self.layer.visible)
        self.visibility_checkbox.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.visibility_checkbox)

        self.visibility_label = QLabel()
        self.visibility_label.setText("auto-cut")
        layout.addWidget(self.visibility_label)

        self.autocut_checkbox = QCheckBox()
        self.autocut_checkbox.setChecked(self.layer.visible)
        self.autocut_checkbox.stateChanged.connect(self.on_autocut_changed)
        layout.addWidget(self.autocut_checkbox)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        layout.addWidget(self.remove_button)

        self.setLayout(layout)

    def on_radio_button_toggled(self, checked):
        if checked:
            index = self.parent.canvas.layers.index(self.layer)
            self.parent.canvas.set_current_layer(index)
            self.parent.update_layer_list()

    def on_name_changed(self, text):
        self.layer.name = text

    def on_width_changed(self, value):
        self.layer.width = value

    def select_color(self):
        color = QColorDialog.getColor(self.layer.color, self)
        if color.isValid():
            self.layer.color = color
            self.color_button.setStyleSheet(f"background-color: {self.layer.color.name()}")

    def on_visibility_changed(self, state):
        self.layer.visible = bool(state)

    def on_autocut_changed(self, state):
        self.layer.flAutoCut = bool(state)

    def on_remove_clicked(self):
        self.parent.remove_layer(self.layer)


class LayerManager(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Layer Manager")
        self.canvas = canvas

        layout = QVBoxLayout()

        self.layer_list = QListWidget()
        layout.addWidget(self.layer_list)

        self.add_layer_button = QPushButton("Add Layer")
        self.add_layer_button.clicked.connect(self.add_layer)
        layout.addWidget(self.add_layer_button)

        self.setLayout(layout)
        self.update_layer_list()

    def update_layer_list(self):
        self.layer_list.clear()
        for i, layer in enumerate(self.canvas.layers):
            item = QListWidgetItem()
            widget = LayerItem(layer, self)
            item.setSizeHint(widget.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, widget)

    def add_layer(self):
        new_layer_name = f"Layer-{len(self.canvas.layers)}"
        new_layer = LayerModel(name=new_layer_name)
        self.canvas.add_layer(new_layer)
        self.update_layer_list()

    def remove_layer(self, layer):
        index = self.canvas.layers.index(layer)
        self.canvas.remove_layer(index)
        self.update_layer_list()


class MainWindow(QMainWindow):
    def __init__(self, file_path=None):
        super().__init__()
        self.setWindowTitle("PyCAD 14")
        self.setGeometry(100, 100, 800, 600)  # Initial window size
        self.drawing_manager = DrawingManager()
        self.drawing_manager.setStyleSheet("background-color: black;")
        if file_path:
            self.drawing_manager.load_dxf(file_path)
            self.drawing_manager.dxf_file = file_path
        self.layer_manager = LayerManager(self.drawing_manager)
        self.layer_manager.setMaximumWidth(720)
        self.layer_manager.setMinimumWidth(640)
        self.layer_manager.setMaximumHeight(720)
        self.layer_manager.setMinimumHeight(480)
        self.layer_manager.show()  # Show the layer manager as a non-blocking modal
        self.init_ui()

    def on_grid_snap_changed(self):
        self.drawing_manager.flSnapGrid = not self.drawing_manager.flSnapGrid
        self.statusBar().showMessage(f"flSnapGrid is {self.drawing_manager.flSnapGrid}")

    def on_vertex_snap_changed(self):
        self.drawing_manager.flSnapPoints = not self.drawing_manager.flSnapPoints
        self.statusBar().showMessage(f"flSnapPoints is {self.drawing_manager.flSnapPoints}")

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Add buttons and checkboxes
        control_layout = QHBoxLayout()
        grid_snap_checkbox = QCheckBox("Grid Snap")
        grid_snap_checkbox.setChecked(True)
        grid_snap_checkbox.stateChanged.connect(self.on_grid_snap_changed)
        vertex_snap_checkbox = QCheckBox("Vertex Snap")
        vertex_snap_checkbox.setChecked(True)
        vertex_snap_checkbox.stateChanged.connect(self.on_vertex_snap_changed)
        control_layout.addWidget(grid_snap_checkbox)
        control_layout.addWidget(vertex_snap_checkbox)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.drawing_manager)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        # Add status bar
        self.statusBar().showMessage("Status: Ready")

        self.layer_manager.update_layer_list()
        self.layer_manager.layer_list.setCurrentRow(0)
        self.drawing_manager.set_current_layer(0)

    def closeEvent(self, event):
        self.layer_manager.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = MainWindow(file_path)
    window.show()
    sys.exit(app.exec())
