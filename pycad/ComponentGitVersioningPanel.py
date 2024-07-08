from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QListWidget, QTextEdit, QPushButton, QLabel, QTableWidgetItem, QTableWidget, QHeaderView)
from PySide6.QtCore import Qt, Signal
import git
import os

from git import Commit


class GitVersioningPanel(QDialog):
    closed = Signal(bool)  # Define a custom signal with a generic object type

    def closeEvent(self, event):
        self.closed.emit(True)

    def __init__(self, repo_path, parent=None, filename: str = ""):
        super(GitVersioningPanel, self).__init__(parent)
        self.repo_path = repo_path

        # Create and initialize repo if it doesn't exist
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
            self.repo = git.Repo.init(repo_path)
        else:
            self.repo = git.Repo(repo_path)

        self.setWindowTitle(f"PyCAD24 - Version Control - {filename}")
        self.setGeometry(100, 100, 600, 600)

        # Layouts
        main_layout = QVBoxLayout()
        commits_layout = QVBoxLayout()
        diff_layout = QVBoxLayout()
        message_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Monospace font
        monospace_font = QFont("Courier New")

        # Commits List
        self.commits_table = QTableWidget()
        self.commits_table.setColumnCount(3)
        self.commits_table.setHorizontalHeaderLabels(["Date", "Message", "SHA"])
        self.commits_table.setFont(monospace_font)
        self.load_commits()
        self.commits_table.itemSelectionChanged.connect(self.load_diff)

        # Current Diff List
        self.current_diff_table = QTableWidget()
        self.current_diff_table.setColumnCount(3)
        self.current_diff_table.setHorizontalHeaderLabels(["+", "-", "Filename"])
        self.current_diff_table.setFont(monospace_font)
        # Set fixed column widths
        self.current_diff_table.setColumnWidth(0, 25)  # Set width of column 1 to 100
        self.current_diff_table.setColumnWidth(1, 25)  # Set width of column 2 to 150

        # Commit Message Textbox
        self.commit_message_textbox = QTextEdit()
        self.commit_message_textbox.setObjectName("COMMIT_MESSAGE_TEXTBOX")
        self.commit_message_textbox.setFont(monospace_font)

        # Buttons
        self.revert_button = QPushButton("Revert")
        self.revert_button.setObjectName("REVERT_BUTTON")
        self.revert_button.clicked.connect(self.revert_changes)

        self.commit_button = QPushButton("Commit")
        self.commit_button.setObjectName("COMMIT_BUTTON")
        self.commit_button.clicked.connect(self.commit_changes)

        # Adding widgets to layouts
        commits_layout.addWidget(QLabel("Commits"))
        commits_layout.addWidget(self.commits_table)

        diff_layout.addWidget(QLabel("Current Diff"))
        diff_layout.addWidget(self.current_diff_table)

        message_layout.addWidget(QLabel("Commit Message"))
        message_layout.addWidget(self.commit_message_textbox)

        button_layout.addWidget(self.revert_button)
        button_layout.addWidget(self.commit_button)

        main_layout.addLayout(commits_layout)
        main_layout.addLayout(diff_layout)
        main_layout.addLayout(message_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def load_commits(self):
        self.commits_table.setRowCount(0)
        for commit in self.repo.iter_commits():
            row_position = self.commits_table.rowCount()
            self.commits_table.insertRow(row_position)
            self.commits_table.setItem(row_position, 0,
                                       QTableWidgetItem(f"{commit.committed_datetime:%Y-%m-%d %H:%M:%S}"))
            self.commits_table.setItem(row_position, 1, QTableWidgetItem(commit.message.splitlines()[0]))
            self.commits_table.setItem(row_position, 2, QTableWidgetItem(commit.hexsha))

        self.commits_table.horizontalHeader().setStretchLastSection(True)
        self.commits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.commits_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def load_diff(self):
        self.current_diff_table.setRowCount(0)
        selected_items = self.commits_table.selectedItems()
        if selected_items:
            row = self.commits_table.currentRow()
            commit_hash = self.commits_table.item(row, 2).text()
            commit = self.repo.commit(commit_hash)
            diffs = commit.diff('HEAD~1')
            for diff in diffs:
                if diff.a_path:
                    additions = sum(
                        1 for line in diff.diff.split('\n') if line.startswith('+') and not line.startswith('+++'))
                    deletions = sum(
                        1 for line in diff.diff.split('\n') if line.startswith('-') and not line.startswith('---'))
                    row_position = self.current_diff_table.rowCount()
                    self.current_diff_table.insertRow(row_position)
                    self.current_diff_table.setItem(row_position, 0, QTableWidgetItem(str(additions)))
                    self.current_diff_table.setItem(row_position, 1, QTableWidgetItem(str(deletions)))
                    self.current_diff_table.setItem(row_position, 2, QTableWidgetItem(diff.a_path))

        self.current_diff_table.horizontalHeader().setStretchLastSection(True)
        self.current_diff_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def commit_changes(self):
        message = self.commit_message_textbox.toPlainText()
        self.repo.git.add(A=True)
        self.repo.index.commit(message)
        self.load_commits()

    def revert_changes(self):
        self.repo.git.reset('--hard')
        self.load_commits()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # Example path, replace with the actual repository path
    repo_path = os.path.join(os.getcwd(), "example_repo.git")

    window = GitVersioningPanel(repo_path)
    window.show()

    sys.exit(app.exec())
