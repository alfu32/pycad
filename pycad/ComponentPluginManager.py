import io
import json
import shutil
import subprocess
import zipfile
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QLineEdit, QListWidget, QTextEdit,
                               QPushButton, QLabel, QWidget)
from PySide6.QtCore import Signal
import requests
import os

from pycad.Plugin import BaseTool
from pycad.Tool import PolylineTool

PLUGINS_DIR = 'plugins'
VALIDATION_URL = ('https://raw.githubusercontent.com/alfu32/pycad/main/'
                  'validatedplugins.json')


def kebab_to_camel(kebab_str):
    # Split by hyphen, capitalize each word, then join them
    return ''.join(word.capitalize() for word in kebab_str.split('-'))


def kebab_to_pascal(kebab_str):
    # Split by hyphen, capitalize each word, then join them
    return ''.join(word.capitalize() for word in kebab_str.split('-'))


def download_github_repo(plugin, base_folder):
    # Parse the repository URL to create the appropriate folder structure
    target_folder = os.path.join(base_folder, plugin['python']['folder'])
    if os.path.exists(target_folder):
        shutil.rmtree(target_folder)

    # Convert the repository URL to download the ZIP archive
    zip_url = plugin['clone_url'].replace(".git", "") + "/archive/refs/heads/main.zip"
    response = requests.get(zip_url)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        # Extract to a temporary location (in memory or file system)
        temp_extract_folder = os.path.join(base_folder, "temp_extract")
        zip_ref.extractall(temp_extract_folder)

        # Find the folder that contains the actual code (typically <repo-name>-<branch>)
        top_level_folder = os.path.join(temp_extract_folder, zip_ref.namelist()[0].split('/')[0])

        # Create target_folder if it doesn't exist
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # Move the contents of the top-level folder into the target folder
        for item in os.listdir(top_level_folder):
            source_path = os.path.join(top_level_folder, item)
            target_path = os.path.join(target_folder, item)
            if os.path.isdir(source_path):
                shutil.move(source_path, target_path)
            else:
                shutil.move(source_path, target_folder)

        # Clean up the temporary extraction folder
        shutil.rmtree(temp_extract_folder)

    print(f"Repository downloaded and extracted to {target_folder}")


class PluginManager(QDialog):
    closed = Signal(bool)

    def __init__(self, filename: str, parent: QWidget = None):
        super(PluginManager, self).__init__(parent)
        self.current_plugin = None
        self.plugins_github = []
        self.plugins_local: dict = {}
        if os.path.exists('plugins/plugins.json'):
            with open('plugins/plugins.json', 'r') as json_file:
                self.plugins_local = json.load(json_file)

        self.loaded_plugins = [
            BaseTool(),
            PolylineTool(),
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
        self.github_plugins_list.currentRowChanged.connect(self.display_github_plugin_details)

        github_layout.addWidget(self.search_box)
        github_layout.addWidget(self.github_plugins_list)
        github_tab.setLayout(github_layout)

        # Local Tab
        local_tab = QWidget()
        local_layout = QVBoxLayout()

        self.local_plugins_list = QListWidget()
        self.local_plugins_list.currentRowChanged.connect(self.display_local_plugin_details)
        self.load_local_plugins()

        local_layout.addWidget(self.local_plugins_list)
        local_tab.setLayout(local_layout)

        tab_widget.addTab(github_tab, "GitHub")
        tab_widget.addTab(local_tab, "Local")
        tab_widget.currentChanged.connect(self.tab_changed)
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
        self.search_github_plugins("p")

        self.tab_changed(0)

    def tab_changed(self, a):
        print(f"tab changed to {a}", flush=True)
        if a == 0:
            if self.github_plugins_list.count() > 0:
                self.github_plugins_list.setCurrentRow(0)
                self.display_github_plugin_details(0)
        elif a == 1:
            if self.local_plugins_list.count() > 0:
                self.local_plugins_list.setCurrentRow(0)
                self.display_local_plugin_details(0)
        else:
            pass

    def search_github_plugins(self, query):
        self.github_plugins_list.clear()
        if query:
            response = requests.get(f"https://api.github.com/search/repositories?q=pycad24-plugin-{query}")
            if response.status_code == 200:
                plugins_json = response.json()["items"][:10]

                self.plugins_github = []
                for plugin in plugins_json:
                    _space, _author, _name = (
                        plugin["clone_url"]
                        .replace('https://', '')
                        .replace('.git', '')
                        .replace('github.com', 'github')
                    ).split('/')
                    pkg_space = kebab_to_pascal(_space)
                    pkg_author = kebab_to_pascal(_author)
                    pkg_name = kebab_to_pascal(_name)
                    pkg_key = f'{pkg_space}/{pkg_author}/{pkg_name}'
                    pkg_ord = self.plugins_github.count()
                    if pkg_key in self.plugins_local:
                        continue

                    plugin['python'] = {
                        'key': pkg_key,
                        'pkg_space': _space,
                        'pkg_author': _author,
                        'pkg_name': _name,
                        'folder': f'{pkg_space}/{pkg_author}/{pkg_name}',
                        'package': f'{pkg_space}.{pkg_author}.{pkg_name}',
                        'header': f'from {pkg_space}.{pkg_author}.{pkg_name}.plugin import init_plugin as {pkg_space}_{pkg_author}_{pkg_name}__init_plugin',
                        'init': f'    {pkg_space}_{pkg_author}_{pkg_name}__init_plugin(app)',
                        'is_loaded': pkg_key in self.plugins_local,
                        'readme_path': os.path.join(f'plugins/{pkg_space}/{pkg_author}/{pkg_name}', f"README.md"),
                        'short_description': f"{plugin['url'].replace('https://api.github.com/repos/', '')} - {plugin['default_branch']} - {plugin['description']} - {plugin['license']['name']}",
                    }
                    plugin['download_base_url'] = f"{plugin['html_url']}.git"
                    plugin['package_path'] = kebab_to_pascal(plugin['html_url'].replace('http://github.com', 'github'))
                    self.plugins_github.append(plugin)
                    self.github_plugins_list.addItem(plugin['python']['short_description'])

                with open('plugins/plugins-github.json', 'w+') as local:
                    json.dump(self.plugins_github, local, indent=4)

    def load_local_plugins(self):
        # Load local plugins (for simplicity, assumed to be in the current directory)
        self.local_plugins_list.clear()
        for key, plugin in self.plugins_local.items():
            self.local_plugins_list.addItem(plugin['python']['short_description'])

    def compile_python_plugins_loader(self):
        imports = []
        inits = [
            "# plugins init",
            "def plugins_init(app):"
        ]
        if os.path.exists('plugins/plugins.json'):
            with open('plugins/plugins.json', 'r') as json_file:
                plugins = json.load(json_file)
                for key, plugin in plugins.items():
                    imports.append(plugin['python']['header'])
                    inits.append(plugin['python']['init'])
            with open("plugins/__init__.py", "w") as file:
                # Write each line to the file
                for im in imports:
                    file.write(im + "\n")  # Add newline character after each line
                file.write("\n\n")  # Add newline character after each line
                for ini in inits:
                    file.write(f"{ini}\n")  # Add newline character after each line
                file.write("    pass\n")  # Add newline character after each line

    def fetch_readme(self, user, repo, branch="main"):
        url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/README.md"
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error: {response.status_code}")
            return None

    def display_github_plugin_details(self, row_index):

        self.current_plugin = self.plugins_github[row_index]
        print(f"selecting {self.current_plugin['name']}", flush=True)
        plugin_name = self.current_plugin['name']
        self.plugin_name_label.setText(plugin_name)
        self.plugin_short_description_label.setText("")
        # # Fetching README locally
        # readme_path = plugin['python']['readme_path']
        # print(f"reading {readme_path}")
        readme = self.fetch_readme(self.current_plugin['owner']['login'], self.current_plugin['name'],
                                   self.current_plugin['default_branch'])
        if readme is not None:
            self.plugin_description_text.setText(readme)
        else:
            self.plugin_description_text.setText("No description available.")

        self.install_button.setEnabled(True)
        self.uninstall_button.setEnabled(False)

    def display_local_plugin_details(self, row_index):
        current_index = row_index
        key, plugin = list(self.plugins_local.items())[row_index]
        plugin_name = plugin['name']
        self.plugin_name_label.setText(plugin_name)
        self.plugin_short_description_label.setText("")
        # Fetching README locally
        readme_path = plugin['python']['readme_path']
        print(f"local::reading {readme_path}",flush=True)
        if os.path.exists(readme_path):
            with open(readme_path, "r") as file:
                self.plugin_description_text.setText(file.read())
        else:
            self.plugin_description_text.setText("No description available.")
        self.current_plugin = plugin
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(True)

    def install_plugin(self):
        if self.current_plugin is not None:
            index = self.plugins_github.index(self.current_plugin)
            print(f"current plugin is {index}th in the github plugins list")
            print(f"downloading the plugin {self.current_plugin['name']}", flush=True)
            download_github_repo(self.current_plugin, "plugins")
            print(f".... done downloading the plugin {self.current_plugin['name']}", flush=True)
            self.plugins_local[self.current_plugin['python']['key']] = self.current_plugin
            print(f"dumping plugins.json {self.current_plugin['name']}", flush=True)
            with open("plugins/plugins.json", "w") as json_file:
                json.dump(self.plugins_local, json_file, indent=4)
            print(f"compiling plugin loader {self.current_plugin['name']}", flush=True)
            self.compile_python_plugins_loader()
            print(f".... done", flush=True)
            self.plugins_github.remove(self.current_plugin)
            self.github_plugins_list.model().removeRow(index)
            self.plugins_local[self.current_plugin['python']['key']] = (self.current_plugin)
            self.local_plugins_list.addItem(self.current_plugin['python']['short_description'])

        else:
            print(f"no current plugin", flush=True)

    def uninstall_plugin(self):
        if self.current_plugin is not None:
            print(f"uninstalling the plugin {self.current_plugin['name']}", flush=True)
            index = list(self.plugins_local.keys()).index(self.current_plugin['python']['key'])
            print(f"found {self.current_plugin['name']} at index {index}",flush=True)
            del self.plugins_local[self.current_plugin['python']['key']]
            self.plugins_github.append(self.current_plugin)
            self.local_plugins_list.model().removeRow(index)
            self.github_plugins_list.addItem(self.current_plugin['python']['short_description'])

            print(f"dumping plugins.json {self.current_plugin['name']}", flush=True)
            with open("plugins/plugins.json", "w") as json_file:
                json.dump(self.plugins_local, json_file, indent=4)
            print(f"compiling plugin loader {self.current_plugin['name']}", flush=True)
            self.compile_python_plugins_loader()
            print(f".... done", flush=True)
        else:
            print(f"no current plugin selected", flush=True)

    def closeEvent(self, event):
        self.closed.emit(True)
        super(PluginManager, self).closeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = PluginManager("---")
    window.show()

    sys.exit(app.exec())
