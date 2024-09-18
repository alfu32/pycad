import io
import json
import shutil
import subprocess
import zipfile
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QLineEdit, QListWidget, QTextEdit,
                               QPushButton, QLabel, QWidget, QListWidgetItem)
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
    print(f"downloading the plugin {plugin}", flush=True)
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
        self.plugins_github: dict = {}
        self.plugins_local: dict = {}

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

        self.plugins_github_list_view = QListWidget()
        self.plugins_github_list_view.currentItemChanged.connect(self.on_select_github_plugin)

        github_layout.addWidget(self.search_box)
        github_layout.addWidget(self.plugins_github_list_view)
        github_tab.setLayout(github_layout)

        # Local Tab
        local_tab = QWidget()
        local_layout = QVBoxLayout()

        self.plugins_local_list_view = QListWidget()
        self.plugins_local_list_view.currentItemChanged.connect(self.on_select_local_plugin)

        local_layout.addWidget(self.plugins_local_list_view)
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
        self.load_local_plugins()
        self.search_github_plugins("")

        self.tab_changed(0)

    def tab_changed(self, a):
        print(f"tab changed to {a}", flush=True)
        if a == 0:
            if self.plugins_github_list_view.count() > 0:
                if self.current_plugin is None:
                    self.plugins_github_list_view.setCurrentRow(0)
                    ci=self.plugins_github_list_view.currentItem()
                else:
                    pass
                print(f"github list first item is {ci.text()}",flush=True)
                self.on_select_github_plugin(ci,ci)
            else:
                print(f"plugins_github_list_view count is 0",flush=True)
        elif a == 1:
            if self.plugins_local_list_view.count() > 0:
                self.plugins_local_list_view.setCurrentRow(0)
                ci=self.plugins_local_list_view.currentItem()
                print(f"local list first item is {ci.text()}",flush=True)
                self.on_select_local_plugin(ci,ci)
            else:
                print(f"plugins_local_list_view count is 0",flush=True)
        else:
            pass

    def render_github_plugins_list(self):
        self.plugins_github_list_view.clear()
        for key,plugin in self.plugins_github.items():
            self.plugins_github_list_view.addItem(plugin['python']['key'])

    def search_github_plugins(self, query=""):
        response = requests.get(f"https://api.github.com/search/repositories?q=pycad24-plugin-{query}")
        if response.status_code == 200:
            plugins_json = response.json()["items"][:10]

            self.plugins_github = {}
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
                self.plugins_github[pkg_key]=plugin

            self.store_github_plugins()
            self.render_github_plugins_list()
            self.render_local_plugins_list_view()

    def render_local_plugins_list_view(self):
        # Load local plugins (for simplicity, assumed to be in the current directory)
        self.plugins_local_list_view.clear()
        for key, plugin in self.plugins_local.items():
            self.plugins_local_list_view.addItem(plugin['python']['key'])

    def load_local_plugins(self):
        # Load local plugins (for simplicity, assumed to be in the current directory)
        if os.path.exists('plugins/plugins.json'):
            with open('plugins/plugins.json', 'r') as json_file:
                self.plugins_local = json.load(json_file)

    def compile_python_plugins_loader(self):

        print(f"compiling plugin loader {self.current_plugin['name']}", flush=True)
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
        print(f".... done compiling", flush=True)

    def fetch_readme(self, user, repo, branch="main"):
        url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/README.md"
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error: {response.status_code}")
            return None

    def on_select_github_plugin(self, current:QListWidgetItem,prev:QListWidgetItem):
        if current:
            current_key=current.text()
            self.select_github_plugin(current_key)

    def select_github_plugin(self, current_key:str):
        self.current_plugin = self.plugins_github[current_key]
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

    def on_select_local_plugin(self, current:QListWidgetItem,prev:QListWidgetItem):
        if current:
            current_key=current.text()
            self.select_local_plugin(current_key)

    def select_local_plugin(self, current_key:str):
        plugin = self.plugins_local[current_key]
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

    def store_local_plugins(self):
        print(f"dumping plugins.json", flush=True)
        with open("plugins/plugins.json", "w") as json_file:
            json.dump(self.plugins_local, json_file, indent=4)

    def store_github_plugins(self):
        print(f"dumping plugins-github.json", flush=True)
        with open("plugins/plugins-github.json", "w") as json_file:
            json.dump(self.plugins_github, json_file, indent=4)

    def install_plugin(self):
        if self.current_plugin is not None:
            index = self.current_plugin['python']['key']
            print(f"installing the plugin {index}")
            download_github_repo(self.current_plugin, "plugins")
            self.plugins_local[index] = self.current_plugin
            del self.plugins_github[index]

            self.store_local_plugins()
            self.store_github_plugins()
            self.compile_python_plugins_loader()
            self.render_github_plugins_list()
            self.render_local_plugins_list_view()
            self.tab_changed(0)
        else:
            print(f"no current plugin", flush=True)

    def uninstall_plugin(self):
        if self.current_plugin is not None:
            print(f"uninstalling the plugin {self.current_plugin['name']}", flush=True)
            index = self.current_plugin['python']['key']
            del self.plugins_local[self.current_plugin['python']['key']]
            self.plugins_github[index]=self.current_plugin

            self.store_local_plugins()
            self.store_github_plugins()
            self.compile_python_plugins_loader()
            self.render_github_plugins_list()
            self.render_local_plugins_list_view()
            self.tab_changed(1)
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
