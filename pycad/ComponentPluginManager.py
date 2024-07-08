from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QListWidget, QCheckBox, QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt, Signal
import requests
import os
import importlib.util

from pycad.Drawable import Drawable


class PluginManagerDialog(QDialog):
    closed = Signal(bool)  # Define a custom signal with a generic object type

    def closeEvent(self, event):
        self.closed.emit(True)
    def __init__(self, parent=None, filename: str = ""):
        super(PluginManagerDialog, self).__init__(parent)

        self.setWindowTitle(f"PyCAD24 - Plugin Manager {filename}")
        self.setGeometry(100, 100, 300, 600)

        # Layouts
        main_layout = QVBoxLayout()
        plugins_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Plugins List
        self.plugins_list = QListWidget()
        self.load_plugins()

        # Load Button
        self.load_button = QPushButton("Load Selected Plugins")
        self.load_button.clicked.connect(self.load_selected_plugins)

        # Adding widgets to layouts
        plugins_layout.addWidget(QLabel("Available Plugins"))
        plugins_layout.addWidget(self.plugins_list)

        button_layout.addWidget(self.load_button)

        main_layout.addLayout(plugins_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def load_plugins(self):
        self.plugins_list.clear()
        response = requests.get('https://api.github.com/search/repositories?q=PyCabs24-plugin')
        if response.status_code == 200:
            plugins = response.json().get('items', [])
            for plugin in plugins:
                checkbox = QCheckBox(f"{plugin['name']} - {plugin['description']}")
                checkbox.setObjectName(plugin['full_name'])
                self.plugins_list.addItem(checkbox)
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch plugins from GitHub.")

    def load_selected_plugins(self):
        for index in range(self.plugins_list.count()):
            item = self.plugins_list.item(index)
            if item.isSelected():
                plugin_full_name = item.objectName()
                self.download_and_load_plugin(plugin_full_name)

    def download_and_load_plugin(self, full_name):
        plugin_url = f"https://raw.githubusercontent.com/{full_name}/main/plugin.py"
        response = requests.get(plugin_url)
        if response.status_code == 200:
            plugin_code = response.text
            plugin_path = os.path.join(os.getcwd(), 'plugin.py')
            with open(plugin_path, 'w') as file:
                file.write(plugin_code)
            self.load_plugin(plugin_path)
        else:
            QMessageBox.warning(self, "Error", f"Failed to download plugin: {full_name}")

    def load_plugin(self, path):
        spec = importlib.util.spec_from_file_location("plugin", path)
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)
        if hasattr(plugin_module, 'Plugin'):
            plugin_instance = plugin_module.Plugin()
            if isinstance(plugin_instance, Drawable):
                plugin_instance.initialize_controls()
            else:
                QMessageBox.warning(self, "Error", "The plugin does not conform to the Drawable interface.")
        else:
            QMessageBox.warning(self, "Error", "The plugin does not contain a Plugin class.")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = PluginManagerDialog()
    window.show()
    sys.exit(app.exec())
