import sys
import time
from PySide6.QtWidgets import (
    QApplication
)

from pycad import register_tools
from pycad.ComponentGitVersioningPanel import GitVersioningPanel
from pycad.ComponentsMainWindow import MainWindow


if __name__ == '__main__':
    register_tools.register_all_tools()
    app = QApplication(sys.argv)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    default_file = f"drawing_{timestamp}.dxf"
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file
    temp_file = f"temp_{timestamp}_{file_path}"
    repo_path = f"{file_path}.git"
    window = MainWindow(file_path, temp_file)
    window.show()
    sys.exit(app.exec())
