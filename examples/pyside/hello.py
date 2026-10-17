"""Run with: envstack pyside6 -- python hello.py"""

import sys

from PySide6.QtWidgets import QApplication, QLabel


def main():
    app = QApplication(sys.argv)
    label = QLabel("Hello from a shared PySide6 deployment!")
    label.setWindowTitle("envstack + PySide6")
    label.resize(360, 100)
    label.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
