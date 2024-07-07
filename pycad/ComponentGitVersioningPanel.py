from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                               QListWidget, QTextEdit, QPushButton, QLabel)
from PySide6.QtCore import Qt
import git
import os

class GitVersioningPanel(QDialog):
    def __init__(self, repo_path, parent=None):
        super(GitVersioningPanel, self).__init__(parent)
        self.repo_path = repo_path
        self.repo = git.Repo(repo_path)
        
        self.setWindowTitle("Git Versioning")
        self.setGeometry(100, 100, 800, 600)
        
        # Layouts
        main_layout = QVBoxLayout()
        commits_layout = QVBoxLayout()
        diff_layout = QVBoxLayout()
        message_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        
        # Commits List
        self.commits_list = QListWidget()
        self.commits_list.setObjectName("COMMITS_LIST")
        self.load_commits()
        
        # Current Diff List
        self.current_diff_list = QListWidget()
        self.current_diff_list.setObjectName("CURRENT_DIFF_LIST")
        self.commits_list.currentItemChanged.connect(self.load_diff)
        
        # Commit Message Textbox
        self.commit_message_textbox = QTextEdit()
        self.commit_message_textbox.setObjectName("COMMIT_MESSAGE_TEXTBOX")
        
        # Buttons
        self.revert_button = QPushButton("Revert")
        self.revert_button.setObjectName("REVERT_BUTTON")
        self.revert_button.clicked.connect(self.revert_changes)
        
        self.commit_button = QPushButton("Commit")
        self.commit_button.setObjectName("COMMIT_BUTTON")
        self.commit_button.clicked.connect(self.commit_changes)
        
        # Adding widgets to layouts
        commits_layout.addWidget(QLabel("Commits"))
        commits_layout.addWidget(self.commits_list)
        
        diff_layout.addWidget(QLabel("Current Diff"))
        diff_layout.addWidget(self.current_diff_list)
        
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
        self.commits_list.clear()
        for commit in self.repo.iter_commits():
            self.commits_list.addItem(str(commit))
    
    def load_diff(self, current, previous):
        self.current_diff_list.clear()
        if current:
            commit = self.repo.commit(current.text().split()[0])
            diffs = commit.diff('HEAD~1', create_patch=True)
            for diff in diffs:
                self.current_diff_list.addItem(diff.diff.decode('utf-8'))
    
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
    
    # Initialize repository if not exists
    if not os.path.exists(repo_path):
        repo = git.Repo.init(repo_path)
    
    window = GitVersioningPanel(repo_path)
    window.show()
    
    sys.exit(app.exec())
