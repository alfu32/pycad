import os
import sys
import math
import time
from typing import List

import ezdxf
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QColorDialog, QSpinBox, QListWidget, QListWidgetItem,
    QLineEdit, QCheckBox, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QStyle, QLabel, QComboBox, QSizePolicy,
    QSpacerItem, QInputDialog,
)
from PySide6.QtGui import QPainter, QPen, QColor, QTransform, QMouseEvent
from PySide6.QtCore import Qt, QPoint, Signal
from ezdxf.sections.table import (
    LayerTable, Layer
)

from pycad.Drawable import Line, linetypes, lwrindex, dxf_app_id, lwindex, Text, Dimension, Drawable


def round_to_nearest(value, base):
    return base * round(value / base)


def floor_to_nearest(value, base):
    return base * math.floor(value / base)


def ceil_to_nearest(value, base):
    return base * math.ceil(value / base)


def distance(point1, point2):
    return math.sqrt((point1.x() - point2.x()) ** 2 + (point1.y() - point2.y()) ** 2)


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


def sort_points_on_line(line, points):
    def distance_to_start(p):
        return math.hypot(p.x() - line.start_point.x(), p.y() - line.start_point.y())

    return sorted(points, key=distance_to_start)


def split_line_by_points(line, points):
    segments = []
    start = line.start_point
    for point in points:
        segments.append(Line(start, point))
        start = point
    segments.append(Line(start, line.end_point))
    return segments


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
    size = 1
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


def draw_cursor(painter: QPainter, point: QPoint, size: int):
    x = point.x()
    y = point.y()
    pen = QPen(QColor(Qt.black), 1, Qt.SolidLine)
    painter.setPen(pen)
    painter.drawLine(x - 3 * size, y, x + 3 * size, y)
    painter.drawLine(x, y - 3 * size, x, y + 3 * size)
    painter.drawRect(x - size, y - size, 2 * size, 2 * size)
    # painter.drawArc(x - size, y - size, 2*size, 2*size, 1, math.pi)


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


class LayerModel:
    def __init__(self, name="Layer", color=QColor(Qt.black), width=2, visible=True):
        self.linetype = "Continuous"
        self.name = name
        self.color = color
        self.width = width
        self.visible = visible
        self.drawables = []
        self.flAutoCut = False

    def add_drawable(self, line: Line):
        self.drawables.append(line)
        if isinstance(line, Line):
            self.cleanup()

    def cleanup(self):
        if self.flAutoCut:
            self.rescan_intersections()
        self.remove_short_lines()
        self.cleanup_duplicates()

    def rescan_intersections(self):
        intersection_table = []
        for i, line1 in enumerate(self.drawables):
            for j, line2 in enumerate(self.drawables):
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
            line = self.drawables[line_idx]
            sorted_points = sort_points_on_line(line, intersect_points)
            new_lines.extend(split_line_by_points(line, sorted_points))

        self.drawables = [line for idx, line in enumerate(self.drawables) if idx not in intersection_groups]
        self.drawables.extend(new_lines)

    def cleanup_duplicates(self):
        unique_lines = set(self.drawables)
        self.drawables = list(unique_lines)

    def remove_short_lines(self):
        self.drawables = [line for line in self.drawables if not line.is_empty()]


class DrawingManager(QWidget):
    changed = Signal(object)  # Define a custom signal with a generic object type

    def __init__(self):
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

    def apply_mouse_input_modifiers(self, pos: QPoint) -> QPoint:
        p = QPoint(pos.x(), pos.y())
        if self.flSnapPoints:
            nearest_point = find_nearest_point(self.get_all_points(), pos)
            if nearest_point is not None and distance(nearest_point, pos) <= (self.snapDistance / self.zoom_factor):
                p = QPoint(nearest_point.x(), nearest_point.y())
        if self.flSnapGrid:
            a0 = QPoint(floor_to_nearest(pos.x(), self.gridSpacing.x()),
                        floor_to_nearest(pos.y(), self.gridSpacing.y()))
            a1 = QPoint(ceil_to_nearest(pos.x(), self.gridSpacing.x()), floor_to_nearest(pos.y(), self.gridSpacing.y()))
            a2 = QPoint(floor_to_nearest(pos.x(), self.gridSpacing.x()), ceil_to_nearest(pos.y(), self.gridSpacing.y()))
            a3 = QPoint(ceil_to_nearest(pos.x(), self.gridSpacing.x()), ceil_to_nearest(pos.y(), self.gridSpacing.y()))
            nearest_point = find_nearest_point([a0, a1, a2, a3], pos)
            if nearest_point is not None and distance(nearest_point, pos) <= (self.snapDistance / self.zoom_factor):
                p = QPoint(nearest_point.x(), nearest_point.y())
        self.model_point_snapped = QPoint(p.x(), p.y())
        return p

    def update_mouse_positions(self, event: QMouseEvent):
        self.screen_point_raw = event.pos()
        self.model_point_raw = self.map_to_scene(event.pos())
        self.model_point_snapped = self.apply_mouse_input_modifiers(self.model_point_raw)
        self.screen_point_snapped = self.map_to_view(self.model_point_snapped)

    def create_drawable(self, p1: QPoint, p2: QPoint) -> Drawable:
        if self.mode == 'line':
            return Line(p1, p2)
        elif self.mode == 'text':
            return Text("placeholder", p1, p2, 25)
        elif self.mode == 'dimension':
            return Dimension(p1, p2)

    def mousePressEvent(self, event: QMouseEvent):
        self.update_mouse_positions(event)
        if event.button() == Qt.LeftButton:
            layer = self.layers[self.current_layer_index]
            self.current_drawable = self.create_drawable(
                self.model_point_snapped,
                self.model_point_snapped,
            )
        elif event.button() == Qt.RightButton:
            clayer = self.current_layer()
            for line in clayer.drawables:
                if line.contains_point(self.model_point_raw):
                    clayer.drawables.remove(line)
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
            self.current_drawable.width = layer.width
        self.update()

    def mouseReleaseEvent(self, event):
        self.update_mouse_positions(event)
        if self.current_drawable:
            end_point = self.model_point_snapped
            if event.modifiers() & Qt.ControlModifier:
                end_point = snap_to_angle(self.current_drawable.start_point, end_point)
            self.current_drawable.end_point = end_point
            if isinstance(self.current_drawable, Text):
                text, ok = QInputDialog.getText(self, 'Text Input Dialog', 'Enter some text:')
                self.current_drawable.text = text
            self.layers[self.current_layer_index].add_drawable(self.current_drawable)
            self.current_drawable = None
        self.changed.emit(self.layers)
        self.update()

    def paintEvent(self, event):
        painter: QPainter = QPainter(self)

        # Draw endpoint markers
        for layer in self.layers:
            if not layer.visible:
                continue
            for drawable in layer.drawables:
                draw_rect(painter, self.map_to_view(drawable.start_point))
                draw_rect(painter, self.map_to_view(drawable.end_point))

        if self.current_drawable:
            draw_rect(painter, self.map_to_view(self.current_drawable.start_point))
            draw_rect(painter, self.map_to_view(self.current_drawable.end_point))

        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        for layer in self.layers:
            if not layer.visible:
                continue
            for drawable in layer.drawables:
                pen = QPen(layer.color, layer.width / self.zoom_factor, Qt.SolidLine)
                pen.setDashPattern(linetypes[layer.linetype])
                painter.setPen(pen)
                drawable.draw(painter)
        if self.current_drawable:
            layer = self.current_layer()
            pen = QPen(self.current_layer().color, self.current_layer().width / self.zoom_factor, Qt.SolidLine)

            pen.setDashPattern(linetypes[layer.linetype])
            painter.setPen(pen)
            drawable.draw(painter)

        if self.flSnapGrid:
            self.draw_local_grid(painter, self.model_point_snapped, 0x8888887f)
        # Reset transformation to draw crosses in screen coordinates
        painter.setTransform(QTransform())
        draw_cursor(painter, self.screen_point_snapped, self.snapDistance)

    def get_all_points(self):
        points = []
        for layer in self.layers:
            for line in layer.drawables:
                points.append(line.start_point)
                points.append(line.end_point)
        return points

    def get_all_lines(self):
        lines = []
        for layer in self.layers:
            for line in layer.drawables:
                lines.append(line)
        return lines

    def draw_local_grid(self, painter: QPainter, center: QPoint, color: int):
        dx = self.gridSpacing.x()
        dy = self.gridSpacing.y()
        NX = dx * 40
        NY = dy * 40
        cx = round(center.x() / NX) * NX
        cy = round(center.y() / NY) * NY
        for ix in range(26):
            for iy in range(26):
                draw_point(painter, QPoint(cx + ix * dx, cy + iy * dy), color)
                draw_point(painter, QPoint(cx + ix * dx, cy - iy * dy), color)
                draw_point(painter, QPoint(cx - ix * dx, cy + iy * dy), color)
                draw_point(painter, QPoint(cx - ix * dx, cy - iy * dy), color)


class LayerItem(QWidget):
    changed = Signal(object)  # Define a custom signal with a generic object type

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
        self.color_button.clicked.connect(self.on_select_color)
        layout.addWidget(self.color_button)

        self.visibility_label = QLabel()
        self.visibility_label.setText("visible")
        layout.addWidget(self.visibility_label)

        self.visibility_checkbox = QCheckBox()
        self.visibility_checkbox.setChecked(self.layer.visible)
        self.visibility_checkbox.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.visibility_checkbox)

        self.autocut_label = QLabel()
        self.autocut_label.setText("auto-cut")
        layout.addWidget(self.autocut_label)

        self.autocut_checkbox = QCheckBox()
        self.autocut_checkbox.setChecked(self.layer.flAutoCut)
        self.autocut_checkbox.stateChanged.connect(self.on_autocut_changed)
        layout.addWidget(self.autocut_checkbox)

        # Add linetype combo box
        self.linetype_combo = QComboBox()
        self.linetype_combo.addItems(linetypes.keys())
        self.linetype_combo.setCurrentText(self.layer.linetype)
        self.linetype_combo.currentIndexChanged.connect(self.on_linetype_changed)
        # layout.addWidget(QLabel("Linetype:"))
        layout.addWidget(self.linetype_combo)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        layout.addWidget(self.remove_button)

        self.setLayout(layout)

    def emit_changed(self):
        self.changed.emit(self.layer)  # Emit the changed signal with the layer data model
        # QApplication.processEvents()  # Process any pending events

    def on_radio_button_toggled(self, checked):
        if checked:
            index = self.parent.canvas.layers.index(self.layer)
            self.parent.canvas.set_current_layer(index)
            self.parent.update_layer_list()
        self.emit_changed()

    def on_name_changed(self, text):
        self.layer.name = text
        self.emit_changed()

    def on_width_changed(self, value):
        self.layer.width = value
        self.emit_changed()

    def on_select_color(self):
        color = QColorDialog.getColor(self.layer.color, self)
        if color.isValid():
            self.layer.color = color
            self.color_button.setStyleSheet(f"background-color: {self.layer.color.name()}")
            self.emit_changed()

    def on_visibility_changed(self, state):
        self.layer.visible = bool(state)
        self.emit_changed()

    def on_autocut_changed(self, state):
        self.layer.flAutoCut = bool(state)
        self.emit_changed()

    def on_linetype_changed(self, index):
        linetype = self.linetype_combo.currentText()
        self.layer.linetype = linetype
        self.emit_changed()

    def on_remove_clicked(self):
        self.parent.remove_layer(self.layer)
        self.emit_changed()


class LayerManager(QDialog):
    changed = Signal(object)  # Define a custom signal with a generic object type
    closed = Signal(bool)  # Define a custom signal with a generic object type

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

    def emit_change(self):
        self.changed.emit(self.layer_list)
        # QApplication.processEvents()

    def update_layer_list(self):
        self.layer_list.clear()
        for i, layer in enumerate(self.canvas.layers):
            item = QListWidgetItem()
            widget = LayerItem(layer, self)
            widget.changed.connect(self.on_layer_changed)
            item.setSizeHint(widget.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, widget)

    def add_layer(self):
        new_layer_name = f"Layer-{len(self.canvas.layers)}"
        new_layer = LayerModel(name=new_layer_name)
        self.canvas.add_layer(new_layer)
        self.update_layer_list()
        # print(f"add_layer {new_layer.name}", flush=True)
        self.emit_change()

    def remove_layer(self, layer):
        index = self.canvas.layers.index(layer)
        self.canvas.remove_layer(index)
        self.update_layer_list()
        # print(f"remove_layer {layer.name}", flush=True)
        self.emit_change()

    def on_layer_changed(self, layer):
        # print(f"child layer changed {layer.name}", flush=True)
        # Handle the layer data change here
        self.emit_change()

    def closeEvent(self, event):
        self.closed.emit(True)


class MainWindow(QMainWindow):
    def __init__(self, file: str, temp: str):
        super().__init__()
        self.dxf_file = file
        self.temp_file = temp
        self.grid_snap_x: QSpinBox = None
        self.grid_snap_y: QSpinBox = None
        self.snap_distance: QSpinBox = None
        self.layout_man_button: QPushButton = None
        self.setGeometry(100, 100, 800, 600)  # Initial window size
        self.drawing_manager = DrawingManager()
        self.drawing_manager.setStyleSheet("background-color: black;")
        self.drawing_manager.changed.connect(self.on_model_changed)
        self.layer_manager = LayerManager(self.drawing_manager)
        self.layer_manager.setMaximumWidth(720)
        self.layer_manager.setMinimumWidth(640)
        self.layer_manager.setMaximumHeight(720)
        self.layer_manager.setMinimumHeight(480)
        self.layer_manager.changed.connect(self.on_layers_changed)
        self.layer_manager.closed.connect(self.on_layer_manager_closed)
        self.layer_manager.show()  # Show the layer manager as a non-blocking modal

        self.line_mode_button: QPushButton = None
        self.dimension_mode_button: QPushButton = None
        self.text_mode_button: QPushButton = None

        self.init_ui()
        self.load_dxf(file)
        self.setWindowTitle(f"PyCAD 14 - {self.dxf_file}")

    def on_grid_snap_changed(self, checked):
        self.drawing_manager.flSnapGrid = bool(checked)
        self.statusBar().showMessage(f"flSnapGrid is {self.drawing_manager.flSnapGrid}")

    def on_vertex_snap_changed(self, checked):
        self.drawing_manager.flSnapPoints = bool(checked)
        self.statusBar().showMessage(f"flSnapPoints is {self.drawing_manager.flSnapPoints}")

    def on_grid_spacing_x_changed(self, value):
        self.drawing_manager.gridSpacing.setX(value)
        self.statusBar().showMessage(f"snap_grid.x is {self.drawing_manager.gridSpacing}")

    def on_grid_spacing_y_changed(self, value):
        self.drawing_manager.gridSpacing.setY(value)
        self.statusBar().showMessage(f"snap_grid.y is {self.drawing_manager.gridSpacing}")

    def on_grid_snap_distance_changed(self, value):
        self.drawing_manager.snapDistance = value
        self.statusBar().showMessage(f"snap_grid.y is {self.drawing_manager.snapDistance}")

    def on_layers_changed(self, layers):
        # print("layers changed", flush=True)
        # print(f"{layers}", flush=True)
        self.save_dxf(self.temp_file)

    def on_model_changed(self, model):
        # print("model changed", flush=True)
        # print(f"{model}", flush=True)
        self.save_dxf(self.temp_file)

    def on_layer_manager_closed(self, value):
        self.layout_man_button.setEnabled(value)

    def init_ui(self):
        main_layout = QVBoxLayout()
        size_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Add buttons and checkboxes
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignLeft)

        vertex_snap_checkbox = QCheckBox("Vertex Snap")
        vertex_snap_checkbox.setChecked(True)
        vertex_snap_checkbox.stateChanged.connect(self.on_vertex_snap_changed)
        control_layout.addWidget(vertex_snap_checkbox)

        grid_snap_checkbox = QCheckBox("Grid Snap")
        grid_snap_checkbox.setChecked(True)
        grid_snap_checkbox.stateChanged.connect(self.on_grid_snap_changed)
        control_layout.addWidget(grid_snap_checkbox)

        control_layout.addWidget(QLabel("grid spacing X"))

        self.grid_snap_x = QSpinBox()
        self.grid_snap_x.setValue(self.drawing_manager.gridSpacing.x())
        self.grid_snap_x.valueChanged.connect(self.on_grid_spacing_x_changed)
        control_layout.addWidget(self.grid_snap_x)

        control_layout.addWidget(QLabel("Y"))

        self.grid_snap_y = QSpinBox()
        self.grid_snap_y.setValue(self.drawing_manager.gridSpacing.x())
        self.grid_snap_y.valueChanged.connect(self.on_grid_spacing_y_changed)
        control_layout.addWidget(self.grid_snap_y)

        control_layout.addWidget(QLabel("snap distance"))

        self.snap_distance = QSpinBox()
        self.snap_distance.setValue(self.drawing_manager.snapDistance)
        self.snap_distance.valueChanged.connect(self.on_grid_snap_distance_changed)
        control_layout.addWidget(self.snap_distance)

        control_layout.addItem(QSpacerItem(40, 20, size_policy.horizontalPolicy(), size_policy.verticalPolicy()))

        self.layout_man_button = QPushButton("Layers")
        self.layout_man_button.clicked.connect(self.show_layers)
        self.layout_man_button.setEnabled(False)
        control_layout.addWidget(self.layout_man_button)

        self.line_mode_button = QPushButton("Line")
        self.line_mode_button.setCheckable(True)
        self.line_mode_button.setChecked(True)
        self.line_mode_button.clicked.connect(self.set_line_mode)
        control_layout.addWidget(self.line_mode_button)

        self.dimension_mode_button = QPushButton("Dimension")
        self.dimension_mode_button.setCheckable(True)
        self.dimension_mode_button.clicked.connect(self.set_dimension_mode)
        control_layout.addWidget(self.dimension_mode_button)

        self.text_mode_button = QPushButton("Text")
        self.text_mode_button.setCheckable(True)
        self.text_mode_button.clicked.connect(self.set_text_mode)
        control_layout.addWidget(self.text_mode_button)

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

    def set_line_mode(self):
        self.statusBar().showMessage("Mode: line")
        self.drawing_manager.set_mode("line")
        self.line_mode_button.setChecked(True)
        self.dimension_mode_button.setChecked(False)
        self.text_mode_button.setChecked(False)

    def set_dimension_mode(self):
        self.statusBar().showMessage("Mode: dimension")
        self.drawing_manager.set_mode("dimension")
        self.line_mode_button.setChecked(False)
        self.dimension_mode_button.setChecked(True)
        self.text_mode_button.setChecked(False)

    def set_text_mode(self):
        self.statusBar().showMessage("Mode: text")
        self.drawing_manager.set_mode("text")
        self.line_mode_button.setChecked(False)
        self.dimension_mode_button.setChecked(False)
        self.text_mode_button.setChecked(True)

    def show_layers(self):

        self.layout_man_button.setEnabled(False)
        self.layer_manager.show()

    def closeEvent(self, event):
        self.save_dxf(self.dxf_file)
        self.layer_manager.close()
        event.accept()
        os.unlink(self.temp_file)

    def load_dxf(self, filename):
        self.drawing_manager.layers = []
        self.layer_manager.layers = []
        doc = ezdxf.readfile(filename)
        doc_layers: LayerTable = doc.layers
        for dxf_layer in doc_layers:
            color = QColor(get_true_color(dxf_layer))
            width0 = dxf_layer.dxf.lineweight if dxf_layer.dxf.hasattr('lineweight') else 1
            width = lwrindex[width0] if width0 >= 0 else lwrindex[5]
            linetype = dxf_layer.dxf.get('linetype', 'Continuous')
            # print(f"layer {dxf_layer.dxf.name} has linetype {linetype}", flush=True)

            layer = LayerModel(name=dxf_layer.dxf.name, color=color, width=width,
                               visible=True)
            layer.linetype = dxf_layer.dxf.get('linetype', 'Continuous')
            # Read XDATA
            if dxf_layer.has_xdata(dxf_app_id):
                xdata = dxf_layer.get_xdata(dxf_app_id)
                for code, value in xdata:
                    if code == 1000 and value == "autocut":
                        # print(f"Layer {layer.name} has autocut set to: {value}", flush=True)
                        pass
                    if code == 1070:
                        # print(f"Layer {layer.name} integer value to: {value}", flush=True)
                        layer.flAutoCut = True if value == 1 else False
                    else:
                        layer.flAutoCut = False

            self.layer_manager.layers.append(layer)
            self.drawing_manager.layers.append(layer)

        for entity in doc.entities:
            drawable = None
            if entity.dxftype() == 'LINE':
                start_point = QPoint(entity.dxf.start.x, entity.dxf.start.y)
                end_point = QPoint(entity.dxf.end.x, entity.dxf.end.y)
                color = QColor(entity.dxf.color) if entity.dxf.hasattr('color') else QColor(Qt.black)
                width = entity.dxf.lineweight if entity.dxf.hasattr('lineweight') else 1
                drawable = Line(start_point, end_point)
            elif entity.dxftype() == 'TEXT':
                drawable = Text.from_dxf(entity)
            elif entity.dxftype() == 'DIMENSION':
                drawable = Dimension.from_dxf(entity)
            layer_name = entity.dxf.layer
            if drawable:
                for layer in self.drawing_manager.layers:
                    if layer is not None and layer.name is not None and layer.name == layer_name:
                        layer.add_drawable(drawable)
                        break

        self.layer_manager.current_layer_index = 0
        self.drawing_manager.update()
        self.layer_manager.update_layer_list()

    def save_dxf(self, filename):

        doc: ezdxf.drawing.Drawing = ezdxf.new()

        if not doc.appids.has_entry(dxf_app_id):
            doc.appids.new(dxf_app_id)

        for linetype in linetypes:
            if linetype != "Continuous":
                if not doc.linetypes.has_entry(linetype):
                    doc.linetypes.new(linetype, dxfattribs={'description': linetype, 'pattern': linetypes[linetype]})

        for index, layer in enumerate(self.drawing_manager.layers):
            if layer.name != '0' and layer.name != 'Defpoints':
                dxf_layer = doc.layers.new(
                    name=layer.name,
                    dxfattribs={
                        "true_color": qcolor_to_dxf_color(layer.color),
                    }
                )

                # Add XDATA to the layer
                xdata = [
                    (1001, dxf_app_id),
                    (1000, "autocut"),
                    (1070, 1 if layer.flAutoCut else 0),
                ]
                dxf_layer.set_xdata(dxf_app_id, xdata)
            for drawable in layer.drawables:
                drawable.save_to_dxf(doc,layer_name=layer.name)

        doc.saveas(filename)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    default_file = f"drawing_{timestamp}.dxf"
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file
    temp_file = f"temp_{timestamp}_{file_path}"
    window = MainWindow(file_path, temp_file)
    window.show()
    sys.exit(app.exec())
