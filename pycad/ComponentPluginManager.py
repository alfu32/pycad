import subprocess
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QLineEdit, QListWidget, QTextEdit,
                               QPushButton, QLabel, QWidget)
from PySide6.QtCore import Signal
import requests
import os

from plugins.MultipointTool import MultipointTool

PLUGINS_DIR = 'plugins'
VALIDATION_URL = 'https://raw.githubusercontent.com/alfu32/pycad/main/validatedplugins.json'


class PluginManager(QDialog):
    closed = Signal(bool)
    github_plugins = []

    def __init__(self, filename: str, parent: QWidget = None):
        super(PluginManager, self).__init__(parent)
        self.loaded_plugins = [
            MultipointTool()
        ]
        self.setWindowTitle(f"pycad24 - Plugin Manager - {filename}")
        self.setGeometry(100, 100, 800, 600)

        # Layouts
        main_layout = QHBoxLayout()
        tab_widget = QTabWidget()

        # GitHub Tab
        github_tab = QWidget()
        github_layout = QVBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search for GitHub plugins")
        self.search_box.textChanged.connect(self.search_github_plugins)

        self.github_plugins_list = QListWidget()
        self.github_plugins_list.currentItemChanged.connect(self.display_github_plugin_details)

        github_layout.addWidget(self.search_box)
        github_layout.addWidget(self.github_plugins_list)
        github_tab.setLayout(github_layout)

        # Local Tab
        local_tab = QWidget()
        local_layout = QVBoxLayout()

        self.local_plugins_list = QListWidget()
        self.local_plugins_list.currentItemChanged.connect(self.display_local_plugin_details)
        self.load_local_plugins()

        local_layout.addWidget(self.local_plugins_list)
        local_tab.setLayout(local_layout)

        tab_widget.addTab(github_tab, "GitHub")
        tab_widget.addTab(local_tab, "Local")

        # Plugin Details
        details_layout = QVBoxLayout()

        self.plugin_name_label = QLabel("Plugin Name")
        self.plugin_short_description_label = QLabel("Short Description")

        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.install_plugin)
        self.uninstall_button = QPushButton("Uninstall")
        self.uninstall_button.clicked.connect(self.uninstall_plugin)

        details_layout.addWidget(self.plugin_name_label)
        details_layout.addWidget(self.plugin_short_description_label)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.uninstall_button)
        details_layout.addLayout(button_layout)

        self.plugin_description_text = QTextEdit()
        self.plugin_description_text.setReadOnly(True)
        details_layout.addWidget(self.plugin_description_text)

        main_layout.addWidget(tab_widget)
        main_layout.addLayout(details_layout)

        self.setLayout(main_layout)

    def search_github_plugins(self, query):
        self.github_plugins_list.clear()
        if query:
            response = requests.get(f"https://api.github.com/search/repositories?q=pycad24-plugin-{query}")
            if response.status_code == 200:
                plugins = response.json()["items"][:10]
                for plugin in plugins:
                    self.github_plugins_list.addItem(
                        f"{plugin['url'].replace('https://api.github.com/repos/', '')} - {plugin['default_branch']} - {plugin['description']} - {plugin['license']['name']}")

    def load_local_plugins(self):
        # Load local plugins (for simplicity, assumed to be in the current directory)
        self.local_plugins_list.clear()
        for item in os.listdir("plugins"):
            if item.find(".pycad24-plugin-") > -1 and item.endswith(".py"):
                nm = item[:-3]
                self.local_plugins_list.addItem(nm)

    def display_github_plugin_details(self, current, previous):
        if current:
            plugin_name = current.text().split(" - ")[0]
            self.plugin_name_label.setText(plugin_name)
            self.plugin_short_description_label.setText(current.text().split(" - ")[2])
            # Fetching README from GitHub
            readme_url = f"https://raw.githubusercontent.com/{plugin_name}/main/README.md"
            response = requests.get(readme_url)
            if response.status_code == 200:
                self.plugin_description_text.setText(response.text)
            else:
                self.plugin_description_text.setText("No description available.")
            self.install_button.setEnabled(True)
            self.uninstall_button.setEnabled(False)

    def display_local_plugin_details(self, current, previous):
        if current:
            plugin_name = current.text()
            self.plugin_name_label.setText(plugin_name)
            self.plugin_short_description_label.setText("")
            # Fetching README locally
            readme_path = os.path.join("plugins", f"{plugin_name}.md")
            print(f"reading {readme_path}")
            if os.path.exists(readme_path):
                with open(readme_path, "r") as file:
                    self.plugin_description_text.setText(file.read())
            else:
                self.plugin_description_text.setText("No description available.")
            self.install_button.setEnabled(False)
            self.uninstall_button.setEnabled(True)

    def install_plugin(self):
        plugin_name = self.plugin_name_label.text()
        github_url = f"git+https://github.com/{plugin_name}.git"
        result = subprocess.run(["python", "-m", "pip", "install", github_url])

        # Get the output
        output = result.stdout
        error_output = result.stderr

        # Print the output
        print("install_plugin Output:", output)
        print("install_plugin Error Output:", error_output)
        self.load_local_plugins()

    def uninstall_plugin(self):
        plugin_name = self.plugin_name_label.text()
        result = subprocess.run(["python", "-m", "pip", "uninstall", "-y", plugin_name])

        # Get the output
        output = result.stdout
        error_output = result.stderr

        # Print the output
        print("uninstall_plugin Output:", output)
        print("uninstall_plugin Error Output:", error_output)

        self.load_local_plugins()

    def closeEvent(self, event):
        self.closed.emit(True)
        super(PluginManager, self).closeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = PluginManager("---")
    window.show()

    sys.exit(app.exec())
