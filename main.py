import sys
import math
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QColorDialog, \
    QSpinBox, QLabel, QComboBox
from PySide6.QtGui import QPainter, QPen, QColor, QTransform
from PySide6.QtCore import Qt, QPoint


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

    def __eq__(self, other):
        if not isinstance(other, Line):
            return False
        return (self.start_point == other.start_point and self.end_point == other.end_point) or \
            (self.start_point == other.end_point and self.end_point == other.start_point)

    def __hash__(self):
        start_tuple = (self.start_point.x(), self.start_point.y())
        end_tuple = (self.end_point.x(), self.end_point.y())
        return hash((min(start_tuple, end_tuple), max(start_tuple, end_tuple)))


class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.lines = []
        self.current_line = None
        self.current_color = QColor(Qt.black)
        self.current_width = 2
        self.operation_mode = "Draw"
        self.setMouseTracking(True)
        self.zoom_factor = 1.0
        self.offset = QPoint(0, 0)

    def set_color(self, color):
        self.current_color = color

    def set_width(self, width):
        self.current_width = width

    def set_mode(self, mode):
        self.operation_mode = mode

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
        if self.operation_mode == "Draw":
            self.current_line = Line(scene_pos, scene_pos, self.current_color, self.current_width)
        elif self.operation_mode == "Delete":
            for line in self.lines:
                if line.contains_point(scene_pos):
                    self.lines.remove(line)
                    self.update()
                    break

    def mouseMoveEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())
        if self.operation_mode == "Draw" and self.current_line:
            end_point = scene_pos
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            self.update()

    def mouseReleaseEvent(self, event):
        scene_pos = self.map_to_scene(event.pos())
        if self.operation_mode == "Draw" and self.current_line:
            end_point = scene_pos
            if event.modifiers() & Qt.ControlModifier:
                end_point = self.snap_to_angle(self.current_line.start_point, end_point)
            self.current_line.end_point = end_point
            self.handle_intersections(self.current_line)
            self.lines.append(self.current_line)
            self.current_line = None
            self.cleanup_duplicates()
            self.update()

    def handle_intersections(self, new_line):
        new_lines = [new_line]
        to_add = []
        to_remove = []
        for existing_line in self.lines:
            intersections = []
            for line in new_lines:
                intersect_point = line.intersect(existing_line)
                if intersect_point:
                    intersections.append((line, intersect_point))
            if intersections:
                to_remove.append(existing_line)
                for line, point in intersections:
                    to_remove.append(line)
                    to_add.extend(self.split_line(line, point))
                    to_add.extend(self.split_line(existing_line, point))
        for line in to_remove:
            if line in self.lines:
                self.lines.remove(line)
        self.lines.extend(to_add)

    def split_line(self, line, point):
        new_line1 = Line(line.start_point, point, line.color, line.width)
        new_line2 = Line(point, line.end_point, line.color, line.width)
        return [new_line1, new_line2]

    def cleanup_duplicates(self):
        unique_lines = set(self.lines)
        self.lines = list(unique_lines)

    def paintEvent(self, event):
        painter = QPainter(self)
        transform = QTransform()
        transform.translate(self.offset.x(), self.offset.y())
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        for line in self.lines:
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 Drawing Application")
        self.canvas = Canvas()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        color_button = QPushButton("Select Color")
        color_button.clicked.connect(self.select_color)
        control_layout.addWidget(color_button)

        self.width_spinbox = QSpinBox()
        self.width_spinbox.setValue(2)
        self.width_spinbox.valueChanged.connect(self.change_width)
        control_layout.addWidget(QLabel("Line Width:"))
        control_layout.addWidget(self.width_spinbox)

        self.mode_combobox = QComboBox()
        self.mode_combobox.addItems(["Draw", "Select", "Delete"])
        self.mode_combobox.currentTextChanged.connect(self.change_mode)
        control_layout.addWidget(QLabel("Mode:"))
        control_layout.addWidget(self.mode_combobox)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def select_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.set_color(color)

    def change_width(self, width):
        self.canvas.set_width(width)

    def change_mode(self, mode):
        self.canvas.set_mode(mode)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
