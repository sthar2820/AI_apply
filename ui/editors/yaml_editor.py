from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPlainTextEdit,
                           QPushButton, QMessageBox)
import yaml

class YamlEditor(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

        layout = QVBoxLayout()

        # Editor
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Courier New';
                font-size: 12px;
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
            }
        """)

        # Load content
        with open(file_path, 'r') as f:
            self.editor.setPlainText(f.read())

        # Save button
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)

        layout.addWidget(self.editor)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save_changes(self):
        try:
            # Validate YAML
            yaml.safe_load(self.editor.toPlainText())

            # Save if valid
            with open(self.file_path, 'w') as f:
                f.write(self.editor.toPlainText())
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "Invalid YAML", str(e))