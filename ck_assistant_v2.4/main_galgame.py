import sys
from PyQt5.QtWidgets import QApplication
from ui_galgame import GalgameWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GalgameWindow()
    window.show()
    sys.exit(app.exec_())