#!/usr/bin/env python3
"""
CADe SIMU Mapper & Symbol Studio 2.0 - SimuCraft
Punto de entrada para la suite modular de mapeo y edición de símbolos.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from tools.cadesimu_studio import CADeSimuMapperWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = CADeSimuMapperWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
