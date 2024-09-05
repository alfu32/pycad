import csv
import os
from time import sleep

import ezdxf
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFontDatabase, Qt, QColor, QPainter
from PySide6.QtWidgets import QMainWindow, QSpinBox, QPushButton, QVBoxLayout, QSizePolicy, QHBoxLayout, QCheckBox, \
    QLabel, QSpacerItem, QWidget
from ezdxf.sections.table import LayerTable

from plugins import MultipointTool
from pycad import DrawableLineImpl, DrawableDimensionImpl, DrawableTextImpl
from pycad.ComponentGitVersioningPanel import GitVersioningPanel
from pycad.ComponentLayers import LayerManager, LayerModel
from pycad.ComponentPluginManager import PluginManager
from pycad.ComponentsDrawingManager import DrawingManager, TextSignalData
from pycad.DrawableDimensionImpl import Dimension
from pycad.DrawableLineImpl import Line
from pycad.DrawableTextImpl import Text
from pycad.FailsafeOperations import OperationsQueue
from pycad.constants import dxf_app_id, linetypes, lwindex, lwrindex
from pycad.util_drawable import qcolor_to_dxf_color, get_true_color


class MainWindow(QMainWindow):
    # Define a light theme stylesheet
    light_theme = """
        * {
            background-color: #ffffff;
            color: #000000;
        }
    """
    dark_theme = """
        * {
            background-color: #111111;
            color: #eeeeee;
        }
    """

    def __init__(self, file: str, temp: str):
        super().__init__()
        # self.plugins = [
        #     MultipointTool,
        # ]
        self.setStyleSheet(self.light_theme)
        self.font_family = "Arial"
        self.dxf_file = file
        self.temp_file = temp
        self.grid_snap_x: QSpinBox = None
        self.grid_snap_y: QSpinBox = None
        self.snap_distance: QSpinBox = None
        self.layout_man_button: QPushButton = None
        self.plugin_manager_button: QPushButton = None
        self.vcs_button: QPushButton = None
        self.setGeometry(100, 100, 800, 600)  # Initial window size
        self.drawing_manager = DrawingManager(file)
        self.drawing_manager.setStyleSheet(self.dark_theme)
        self.drawing_manager.changed.connect(self.on_model_changed)
        self.drawing_manager.keyboard_input_changed.connect(self.on_keyboard_input_changed)
        self.drawing_manager.point_clicked.connect(self.on_model_clicked)
        self.drawing_manager.paint_event.connect(self.on_drawing_manager_paint_event)

        self.layer_manager = LayerManager(self.drawing_manager, filename=file)
        self.layer_manager.setMaximumWidth(720)
        self.layer_manager.setMinimumWidth(640)
        self.layer_manager.setMaximumHeight(720)
        self.layer_manager.setMinimumHeight(480)
        self.layer_manager.changed.connect(self.on_layers_changed)
        self.layer_manager.closed.connect(self.on_layer_manager_closed)
        self.layer_manager.setStyleSheet(self.light_theme)
        # self.layer_manager.show()  # Show the layer manager as a non-blocking modal

        self.versioning_panel = GitVersioningPanel(".git", filename=file)
        self.versioning_panel.closed.connect(self.on_versioning_panel_closed)
        # self.versioning_panel.show()

        self.plugin_manager_panel = PluginManager(filename=file, parent=self)
        self.plugin_manager_panel.closed.connect(self.on_plugin_manager_panel_closed)
        # self.plugin_manager_panel.show()

        self.line_mode_button: QPushButton = None
        self.dimension_mode_button: QPushButton = None
        self.text_mode_button: QPushButton = None

        self.init_ui()
        self.load_dxf(file)
        self.setWindowTitle(f"PyCAD 24 - {self.dxf_file}")
        # Initialize OperationsQueue
        #self.operation_queue = OperationsQueue()

        # Use OperationsQueue to execute a lambda function
        for plugin in self.plugin_manager_panel.loaded_plugins:
            print(f"plugin {plugin.name} subscribe drawable_ready", flush=True)
            #self.operation_queue.exec(lambda: plugin.drawable_ready.connect(self.on_plugin_finished))
            plugin.drawable_ready.connect(self.on_plugin_finished)

    def on_plugin_finished(self, drawable):
        self.statusBar().showMessage(f"finished {drawable}")

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

    def on_model_clicked(self, point):

        for plugin_instance in self.plugin_manager_panel.loaded_plugins:
            if plugin_instance.is_active:
                plugin_instance.push_model_point(point)

    def on_keyboard_input_changed(self, data: TextSignalData):
        for plugin_instance in self.plugin_manager_panel.loaded_plugins:
            if plugin_instance.is_active:
                plugin_instance.push_user_text(data)
        # print("model changed", flush=True)
        # print(f"{model}", flush=True)
        self.statusBar().showMessage(f"Input: {data.text} {data.number}")

    def on_drawing_manager_paint_event(self, painter: QPainter, moving_point: QPoint):
        # print("drawing plugins figures", flush=True)
        for plugin_instance in self.plugin_manager_panel.loaded_plugins:
            if plugin_instance.is_active:
                plugin_instance.draw(painter, moving_point)

    def on_layer_manager_closed(self, value):
        self.layout_man_button.setChecked(False)

    def on_versioning_panel_closed(self, value):
        self.vcs_button.setChecked(False)

    def on_plugin_manager_panel_closed(self, value):
        self.plugin_manager_button.setChecked(False)

    def init_ui(self):

        # Load custom font
        font_path = "./Bahnschrift-Font-Family/BAHNSCHRIFT.TTF"
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            print(f"font {font_path} found", flush=True)
            self.drawing_manager.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            print(f"font {font_path} not found", flush=True)
            self.drawing_manager.font_family = "Arial"  # Fallback font
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
        self.layout_man_button.setCheckable(True)
        self.layout_man_button.setChecked(False)
        control_layout.addWidget(self.layout_man_button)

        self.vcs_button = QPushButton("Versioning")
        self.vcs_button.clicked.connect(self.show_versioning)
        self.vcs_button.setCheckable(True)
        self.vcs_button.setChecked(False)
        control_layout.addWidget(self.vcs_button)

        self.plugin_manager_button = QPushButton("Plugins")
        self.plugin_manager_button.clicked.connect(self.show_plugins_manager)
        self.plugin_manager_button.setCheckable(True)
        self.plugin_manager_button.setChecked(False)
        control_layout.addWidget(self.plugin_manager_button)

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

        for plugin_instance in self.plugin_manager_panel.loaded_plugins:
            widget = plugin_instance.get_ui_fragment()
            control_layout.addWidget(widget)

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
        self.layout_man_button.setChecked(True)
        self.layer_manager.show()

    def show_versioning(self):
        self.vcs_button.setChecked(True)
        self.versioning_panel.show()

    def show_plugins_manager(self):
        self.plugin_manager_button.setChecked(True)
        self.plugin_manager_panel.show()

    def closeEvent(self, event):
        self.save_dxf(self.dxf_file)
        self.layer_manager.close()
        self.versioning_panel.close()
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
                drawable = Line()
                drawable.push(start_point)
                drawable.push(end_point)
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
                        "lineweight": lwindex[layer.lineweight],
                        "linetype": layer.linetype,
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
                drawable.save_to_dxf(doc, layer_name=layer.name)

        doc.saveas(filename)

    def save_csv(self, entities, filename):
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            for entity in entities:
                writer.writerow([entity.save_to_csv()])

    def load_csv(self, filename):
        entities = []
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                entity_type, csv_line = row[0].split(',', 1)
                if entity_type == 'Text':
                    entity = Text((0, 0), (0, 0))  # dummy points
                elif entity_type == 'Line':
                    entity = Line((0, 0), (0, 0))  # dummy points
                elif entity_type == 'Dimension':
                    entity = Dimension((0, 0), (0, 0))  # dummy points
                entity.load_from_csv(row[0])
                entities.append(entity)
        return entities
