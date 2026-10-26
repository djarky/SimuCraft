#!/usr/bin/env python3
"""
SimuCraft - Punto de entrada principal
"""
import os
import sys

# Asegurar que la raíz del proyecto esté en sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SimuCraft")
    app.setOrganizationName("SimuCraft")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
