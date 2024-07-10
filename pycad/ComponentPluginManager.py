from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Signal, Qt
import requests
import os
import importlib.util
import hashlib
import json

PLUGINS_DIR = 'plugins'
VALIDATED_PLUGINS_URL = 'https://raw.githubusercontent.com/alfu32/pycad/main/validatedplugins.json'



class PluginManagerDialog(QDialog):
    closed = Signal(bool)  # Define a custom signal with a generic object type

    def closeEvent(self, event):
        self.closed.emit(True)

    def __init__(self, parent=None, filename: str = ""):
        super(PluginManagerDialog, self).__init__(parent)

        self.setWindowTitle(f"PyCAD24 - Plugin Manager {filename}")
        self.setGeometry(100, 100, 300, 600)

        # Create plugins directory if it doesn't exist
        if not os.path.exists(PLUGINS_DIR):
            os.makedirs(PLUGINS_DIR)

        # Load validated plugins JSON
        self.validated_plugins = self.load_validated_plugins()

        # Layouts
        main_layout = QVBoxLayout()
        plugins_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Plugins Table
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(3)
        self.plugins_table.setHorizontalHeaderLabels(["Plugin", "Description", "Validated"])
        self.plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
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

    def load_validated_plugins(self):
        response = requests.get(VALIDATED_PLUGINS_URL)
        if response.status_code == 200:
            return response.json()
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch validated plugins list.")
            return {}

    def load_plugins(self):
        self.plugins_table.setRowCount(0)
        response = requests.get('https://api.github.com/search/repositories?q=PyCabs24-plugin')
        local_plugins = self.get_local_plugins()
        if response.status_code == 200:
            plugins = response.json().get('items', [])
            for plugin in plugins:
                row_position = self.plugins_table.rowCount()
                self.plugins_table.insertRow(row_position)
                plugin_name = f"{plugin['full_name'].replace('/', '.')}.py"
                is_local = plugin_name in local_plugins
                is_validated = self.is_plugin_validated(plugin_name)

                checkbox = QCheckBox(f"{plugin['name']}")
                checkbox.setObjectName(plugin['full_name'])
                checkbox.setChecked(is_local)
                self.plugins_table.setCellWidget(row_position, 0, checkbox)

                self.plugins_table.setItem(row_position, 1, QTableWidgetItem(plugin['description']))

                validated_item = QTableWidgetItem("✔" if is_validated else "❗")
                self.plugins_table.setItem(row_position, 2, validated_item)
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch plugins from GitHub.")

    def get_local_plugins(self):
        return {file for file in os.listdir(PLUGINS_DIR) if file.endswith('.py')}

    def is_plugin_validated(self, plugin_name):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        if os.path.exists(plugin_path):
            with open(plugin_path, 'rb') as file:
                file_content = file.read()
                sha_signature = hashlib.sha256(file_content).hexdigest()
                return self.validated_plugins.get(plugin_name) == sha_signature
        return False

    def load_selected_plugins(self):
        for row in range(self.plugins_table.rowCount()):
            checkbox = self.plugins_table.cellWidget(row, 0)
            if checkbox.isChecked():
                plugin_full_name = checkbox.objectName()
                self.download_and_load_plugin(plugin_full_name)

    def download_and_load_plugin(self, full_name):
        plugin_url = f"https://raw.githubusercontent.com/{full_name}/main/plugin.py"
        readme_url = f"https://raw.githubusercontent.com/{full_name}/main/README.md"
        plugin_name = f"{full_name.replace('/', '.')}.py"
        readme_name = f"{full_name.replace('/', '.')}.md"

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
        for name, obj in plugin_module.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, PluginInterface) and obj is not PluginInterface:
                plugin_instance = obj.get_instance()
                if isinstance(plugin_instance, PluginInterface):
                    plugin_instance.init_ui()
                else:
                    QMessageBox.warning(self, "Error", "The plugin does not conform to the PluginInterface.")
                break

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = PluginManagerDialog()
    window.show()
    sys.exit(app.exec())