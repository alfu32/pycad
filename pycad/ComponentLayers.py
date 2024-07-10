from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QRadioButton, QLineEdit, QSpinBox, QPushButton, QLabel, QCheckBox, \
    QComboBox, QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QColorDialog

from pycad.DrawableLineImpl import Line, split_line_by_points
from pycad.constants import linetypes
from pycad.util_geometry import sort_points_on_line


class LayerModel:
    def __init__(self, name="Layer", color=QColor(Qt.black), width=2, visible=True):
        self.linetype = "Continuous"
        self.name = name
        self.color = color
        self.lineweight = width
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
        self.width_input.setValue(self.layer.lineweight)
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
        self.layer.lineweight = value
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

    def __init__(self, canvas, parent: QWidget = None, filename: str = ""):
        super().__init__(parent)

        self.setWindowTitle(f"PyCAD24 - Layer Manager - {filename}")
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
