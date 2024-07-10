from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem, QCheckBox, QPushButton, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal
import requests
import os
import importlib.util
import hashlib
import json

from pycad.Plugin import PluginInterface

PLUGINS_DIR = 'plugins'
VALIDATION_URL = 'https://raw.githubusercontent.com/alfu32/pycad/main/validatedplugins.json'

class PluginManagerDialog(QDialog):
    closed = Signal(bool)  # Define a custom signal with a generic object type

    def closeEvent(self, event):
        self.closed.emit(True)

    def __init__(self, parent=None,filename:str=""):
        super(PluginManagerDialog, self).__init__(parent)

        self.setWindowTitle(f"PyCAD24 - Plugin Manager {filename}")
        self.setGeometry(100, 100, 300, 600)

        # Create plugins directory if it doesn't exist
        if not os.path.exists(PLUGINS_DIR):
            os.makedirs(PLUGINS_DIR)

        # Layouts
        main_layout = QVBoxLayout()
        plugins_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Plugins List
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(3)
        self.plugins_table.setHorizontalHeaderLabels(["Plugin", "Description", "Validated"])
        self.plugins_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.load_plugins()

        # Load Button
        self.load_button = QPushButton("Load Selected Plugins")
        self.load_button.clicked.connect(self.load_selected_plugins)

        # Adding widgets to layouts
        plugins_layout.addWidget(QLabel("Available Plugins"))
        plugins_layout.addWidget(self.plugins_table)

        button_layout.addWidget(self.load_button)

        main_layout.addLayout(plugins_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def load_plugins(self):
        self.plugins_table.setRowCount(0)
        response = requests.get('https://api.github.com/search/repositories?q=pycad24-plugin')
        local_plugins = self.get_local_plugins()
        validated_plugins = self.get_validated_plugins()

        if response.status_code == 200:
            plugins = response.json().get('items', [])
            for plugin in plugins:
                plugin_name = f"github.{plugin['full_name'].replace('/', '.')}"

                print(f"loading plugin {plugin_name}")
                is_local = plugin_name in local_plugins
                checkbox = QCheckBox(f"{plugin['name']}")
                checkbox.setObjectName(plugin['full_name'])
                checkbox.setChecked(is_local)

                validated = "No"
                plugin_info = next((item for item in validated_plugins if item['name'] == plugin_name), None)

                print(f"plugin_info {plugin_info}")

                #plugin_info = [info for info in validated_plugins if ]


                if plugin_info :
                    plugin_path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
                    verification_id = plugin_info['verification_id']
                    file_sha = self.chk(plugin_path)
                    print(f"comparing sha of {plugin_path} with validation id of {plugin_name} \nverification_id {verification_id}\n file sha     {file_sha}")
                    if file_sha == verification_id:
                        validated = "Yes"

                row_position = self.plugins_table.rowCount()
                self.plugins_table.insertRow(row_position)
                self.plugins_table.setCellWidget(row_position, 0, checkbox)
                self.plugins_table.setItem(row_position, 1, QTableWidgetItem(plugin['description']))
                self.plugins_table.setItem(row_position, 2, QTableWidgetItem(validated))
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch plugins from GitHub.")

    def get_local_plugins(self):
        return {file for file in os.listdir(PLUGINS_DIR) if file.endswith('.py')}

    def get_validated_plugins(self):
        response = requests.get(VALIDATION_URL)
        if response.status_code == 200:
            return response.json()
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch validated plugins.")
            return []
    def chk(self,plugin_path:str) -> str:
        if os.path.exists(plugin_path):
            with open(plugin_path, 'rb') as file:
                file_data = file.read()
                sha1_hash = hashlib.sha1(file_data).hexdigest()
                return sha1_hash
        return "000"

    def validate_plugin(self, plugin_name, verification_id):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        return self.chk(plugin_path) == verification_id

    def load_selected_plugins(self):
        for index in range(self.plugins_table.rowCount()):
            checkbox = self.plugins_table.cellWidget(index, 0)
            if isinstance(checkbox,QCheckBox) and checkbox.isChecked():
                plugin_full_name = checkbox.objectName()
                self.download_and_load_plugin(plugin_full_name)

    def download_and_load_plugin(self, full_name):
        plugin_url = f"https://raw.githubusercontent.com/{full_name}/main/plugin.py"
        readme_url = f"https://raw.githubusercontent.com/{full_name}/main/README.md"
        plugin_name = f"github.{full_name.replace('/', '.')}.py"
        readme_name = f"github.{full_name.replace('/', '.')}.md"

        # Download plugin.py
        response = requests.get(plugin_url)
        if response.status_code == 200:
            plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
            with open(plugin_path, 'w') as file:
                file.write(response.text)
        else:
            QMessageBox.warning(self, "Error", f"Failed to download plugin: {full_name}")

        # Download README.md
        response = requests.get(readme_url)
        if response.status_code == 200:
            readme_path = os.path.join(PLUGINS_DIR, readme_name)
            with open(readme_path, 'w') as file:
                file.write(response.text)

        # Load plugin
        self.load_plugin(plugin_name)

    def load_plugin(self, plugin_name):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        spec = importlib.util.spec_from_file_location(plugin_name.replace('.', '_'), plugin_path)
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        for name, cls in plugin_module.__dict__.items():
            if isinstance(cls, type) and issubclass(cls, PluginInterface) and cls is not PluginInterface:
                plugin_instance = cls.get_instance()
                if isinstance(plugin_instance, PluginInterface):
                    # plugin_instance.init_ui()
                    print(f"plugin {name} loaded :::: {plugin_instance}")
                else:
                    QMessageBox.warning(self, "Error", "The plugin does not conform to the PluginInterface.")
                break

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = PluginManagerDialog()
    window.show()
    sys.exit(app.exec())
