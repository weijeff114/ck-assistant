from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt


class LorebookDialog(QDialog):
    """世界书管理弹窗（待开发）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("世界书管理")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        label = QLabel("世界书功能待开发")
        layout.addWidget(label)
        btn = QPushButton("关闭")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
