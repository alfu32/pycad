import sys
import time
from PySide6.QtWidgets import (
    QApplication
)

from pycad.ComponentsMainWindow import MainWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    default_file = f"drawing_{timestamp}.dxf"
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file
    temp_file = f"temp_{timestamp}_{file_path}"
    window = MainWindow(file_path, temp_file)
    window.show()
    sys.exit(app.exec())
