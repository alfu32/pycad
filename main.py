import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QColorDialog, QSpinBox, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QLineEdit, QCheckBox, QColorDialog, QHBoxLayout, QVBoxLayout, QDialog, QRadioButton, QButtonGroup
)
from PySide6.QtGui import QPainter, QPen, QColor, QTransform
from PySide6.QtCore import Qt, QPoint

TOLERANCE = 2

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


class Layer:
    def __init__(self, name="Layer", color=QColor(Qt.black), width=2, visible=True):
        self.name = name
        self.color = color
        self.width = width
        self.visible = visible
        self.lines = []

    def add_line(self, line):
        self.lines.append(line)
        self.cleanup()

    def cleanup(self):
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


class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.layers = [Layer(name="Layer-0")]
        self.current_layer_index = 0
        self.current_line = None
        self.zoom_factor = 1.0
        self.offset = QPoint(0, 0)

    def set_current_layer(self, index):
        self.current_layer_index = index

    def add_layer(self, layer):
        self.layers.append(layer)

    def remove_layer(self, index):
        if len(self.layers) > 1:
            del self.layers[index]
            if self.current_layer_index >= len(self.layers):
                self.current_layer_index = len(self.layers) - 1

    def wheelEvent(self, event):
        mouse_pos = event.position().toPoint()
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.1
        else:
            factor = 0.9

        old_zoom_factor = self.zoom_factor
        self.zoom_factor *= factor
        self.offset = self.offset - mouse_pos + (mouse_pos / old_zoom_factor) * self.zoom_factor

        self.update()

    def map_to_scene(self, point):
        return (point - self.offset) / self.zoom_factor

    def map_to_view(self, point):
        return point * self.zoom_factor + self.offset

    def mousePressEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())
        if event.button() == Qt.LeftButton:
            layer = self.layers[self.current_layer_index]
            self.current_line = Line(scene_pos, scene_pos, layer.color, layer.width)
        elif event.button() == Qt.RightButton:
            for layer in self.layers:
                if not layer.visible:
                    continue
                for line in layer.lines:
                    if line.contains_point(scene_pos):
                        layer.lines.remove(line)
                        self.update()
                        return

    def mouseMoveEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())
        if self.current_line:
            end_point = scene_pos
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            # Update line color and width to match the current layer
            layer = self.layers[self.current_layer_index]
            self.current_line.color = layer.color
            self.current_line.width = layer.width
            self.update()

    def mouseReleaseEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())
        if self.current_line:
            end_point = scene_pos
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            self.layers[self.current_layer_index].add_line(self.current_line)
            self.current_line = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        for layer in self.layers:
            if not layer.visible:
                continue
            for line in layer.lines:
                pen = QPen(line.color, line.width / self.zoom_factor, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawLine(line.start_point, line.end_point)
                self.draw_cross(painter, line.start_point)
                self.draw_cross(painter, line.end_point)
        if self.current_line:
            pen = QPen(self.current_line.color, self.current_line.width / self.zoom_factor, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.current_line.start_point, self.current_line.end_point)
            self.draw_cross(painter, self.current_line.start_point)
            self.draw_cross(painter, self.current_line.end_point)

    def draw_cross(self, painter, point):
        pen = QPen(QColor(Qt.red), 2, Qt.SolidLine)
        painter.setPen(pen)
        size = 5
        painter.drawLine(point.x() - size, point.y() - size, point.x() + size, point.y() + size)
        painter.drawLine(point.x() + size, point.y() - size, point.x() - size, point.y() + size)

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

        self.visibility_checkbox = QCheckBox()
        self.visibility_checkbox.setChecked(self.layer.visible)
        self.visibility_checkbox.stateChanged.connect(self.on_visibility_changed)
        layout.addWidget(self.visibility_checkbox)

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
            if i == self.canvas.current_layer_index:
                widget.setStyleSheet("background-color: lightblue;")
            item.setSizeHint(widget.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, widget)

    def add_layer(self):
        new_layer_name = f"Layer-{len(self.canvas.layers)}"
        new_layer = Layer(name=new_layer_name)
        self.canvas.add_layer(new_layer)
        self.update_layer_list()

    def remove_layer(self, layer):
        index = self.canvas.layers.index(layer)
        self.canvas.remove_layer(index)
        self.update_layer_list()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Drawing Application")
        self.setGeometry(100, 100, 800, 600)  # Initial window size
        self.canvas = Canvas()
        self.layer_manager = LayerManager(self.canvas)
        self.layer_manager.show()  # Show the layer manager as a non-blocking modal
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        main_layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.layer_manager.update_layer_list()
        self.layer_manager.layer_list.setCurrentRow(0)
        self.canvas.set_current_layer(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
