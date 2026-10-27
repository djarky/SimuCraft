"""
Widget de paleta y selector de tipos y colores de cables para el panel lateral derecho.
Permite alternar el tipo de conductor activo y aplicar colores y calibres a cables seleccionados.
"""
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QButtonGroup, QColorDialog, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from ..components.wire_types import WIRE_CATALOG, get_wire_info, create_wire_icon


class WirePaletteWidget(QFrame):
    """
    Panel interactivo con iconos y botones para seleccionar el tipo y color de cable
    según la norma de automatismos y CADe SIMU.
    """

    wire_type_selected = Signal(int, str, str)  # tid, name, color_hex

    def __init__(self, scene=None, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.current_tid = 4000
        self.current_color = "#8B4513"
        self._buttons: Dict[int, QPushButton] = {}

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            WirePaletteWidget {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
            QLabel {
                color: #cdd6f4;
            }
        """)

        self._setup_ui()
        self.set_active_type(4000)

        # Si se pasa la escena, conectar eventos
        if self.scene and hasattr(self.scene, 'wire_type_changed'):
            self.scene.wire_type_changed.connect(self._on_scene_wire_type_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Encabezado
        header_layout = QHBoxLayout()
        lbl_title = QLabel("⚡ Tipos y Colores de Cable")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #89b4fa; text-transform: uppercase;")
        header_layout.addWidget(lbl_title)

        self.lbl_active_badge = QLabel("Fase (L1)")
        self.lbl_active_badge.setStyleSheet("""
            background: #8B4513;
            color: #ffffff;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_active_badge)
        layout.addLayout(header_layout)

        # Descripción breve de ayuda
        lbl_desc = QLabel("Seleccione tipo para trazar o aplicar a cables seleccionados:")
        lbl_desc.setStyleSheet("font-size: 10px; color: #a6adc8;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Botonera agrupada de cables
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 2, 0, 2)

        # Orden de colocación prioritario estilo CADe SIMU
        ordered_tids = [4000, 4001, 4002, 4003, 4004, 4009, 4011, 4016, 4017, 4010, 4019]

        row, col = 0, 0
        for tid in ordered_tids:
            if tid not in WIRE_CATALOG:
                continue
            info = WIRE_CATALOG[tid]
            btn = QPushButton(f" {info['name']}")
            btn.setCheckable(True)
            btn.setIcon(create_wire_icon(info["color"], info.get("width", 2.0), info.get("style", Qt.SolidLine), size=20))
            btn.setToolTip(f"{info['full_name']} ({info['id']})\n{info['description']}\nColor: {info['color']}")
            btn.setStyleSheet(self._button_style(info["color"]))
            btn.clicked.connect(lambda checked, t=tid: self._on_button_clicked(t))

            self.btn_group.addButton(btn, tid)
            self._buttons[tid] = btn
            grid.addWidget(btn, row, col)

            col += 1
            if col > 1:
                col = 0
                row += 1

        layout.addLayout(grid)

        # Barra inferior de acciones (Color personalizado y Aplicar selección)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        btn_custom = QPushButton("🎨 Personalizado...")
        btn_custom.setToolTip("Elegir un color personalizado para el conductor activo")
        btn_custom.setStyleSheet("""
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #45475a;
                color: #ffffff;
            }
        """)
        btn_custom.clicked.connect(self._choose_custom_color)
        actions_layout.addWidget(btn_custom)

        btn_apply = QPushButton("🖌 Aplicar a Selección")
        btn_apply.setToolTip("Aplica el color y tipo seleccionado a todos los cables seleccionados en el esquema")
        btn_apply.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        btn_apply.clicked.connect(self._apply_to_selected)
        actions_layout.addWidget(btn_apply)

        layout.addLayout(actions_layout)

    def _button_style(self, color_hex: str) -> str:
        return f"""
            QPushButton {{
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 5px;
                padding: 5px 6px;
                text-align: left;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: #313244;
                border: 1px solid {color_hex};
                color: #ffffff;
            }}
            QPushButton:checked {{
                background: #313244;
                color: #ffffff;
                border: 2px solid {color_hex};
                font-weight: bold;
            }}
        """

    def _on_button_clicked(self, tid: int):
        self.set_active_type(tid)

    def set_active_type(self, tid: int, custom_color: Optional[str] = None):
        """Establece el tipo de cable activo y lo propaga a la escena."""
        self.current_tid = tid
        info = get_wire_info(tid)
        color = custom_color if custom_color else info["color"]
        self.current_color = color

        # Marcar botón correspondiente
        if tid in self._buttons:
            self._buttons[tid].setChecked(True)

        # Actualizar badge superior
        self.lbl_active_badge.setText(info["name"])
        self.lbl_active_badge.setStyleSheet(f"""
            background: {color};
            color: #ffffff;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        """)

        # Si tenemos escena asociada, actualizar el tipo de cable en la escena
        if self.scene and hasattr(self.scene, 'set_current_wire_type'):
            count = self.scene.set_current_wire_type(tid, color=color)
            main_win = getattr(self.scene, '_get_main_window', lambda: None)()
            if main_win and hasattr(main_win, 'statusBar'):
                if count > 0:
                    main_win.statusBar().showMessage(
                        f"✔ Color y tipo actualizado a '{info['name']}' para {count} cable(s) seleccionado(s)."
                    )
                else:
                    main_win.statusBar().showMessage(
                        f"✔ Cable activo: '{info['name']}' ({color}). Los nuevos cables se trazarán con este color."
                    )

        self.wire_type_selected.emit(tid, info["name"], color)

    def _apply_to_selected(self):
        """Aplica forzosamente el tipo y color activo a los cables seleccionados en la escena."""
        if self.scene and hasattr(self.scene, 'set_current_wire_type'):
            count = self.scene.set_current_wire_type(self.current_tid, color=self.current_color)
            main_win = getattr(self.scene, '_get_main_window', lambda: None)()
            if main_win and hasattr(main_win, 'statusBar'):
                if count > 0:
                    main_win.statusBar().showMessage(
                        f"✔ Aplicado '{get_wire_info(self.current_tid)['name']}' a {count} cable(s) seleccionado(s)."
                    )
                else:
                    main_win.statusBar().showMessage(
                        "ℹ Seleccione uno o más cables en el esquema para aplicar el color."
                    )

    def _choose_custom_color(self):
        """Abre un diálogo de selección de color libre."""
        initial = QColor(self.current_color)
        chosen = QColorDialog.getColor(initial, self, "Seleccionar Color de Conductor")
        if chosen.isValid():
            hex_color = chosen.name()
            self.set_active_type(self.current_tid, custom_color=hex_color)

    def _on_scene_wire_type_changed(self, tid: int, name: str, color_hex: str):
        if tid in self._buttons and not self._buttons[tid].isChecked():
            self._buttons[tid].setChecked(True)
        self.lbl_active_badge.setText(name)
        self.lbl_active_badge.setStyleSheet(f"""
            background: {color_hex};
            color: #ffffff;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        """)
