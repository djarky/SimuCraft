"""
Ventana principal de SimuCraft - Entorno CAD interactivo para automatismos eléctricos
Soporta carga de esquemas CADe SIMU (.cad), creación de esquemas, cableado dinámico,
previsualización interactiva de componentes con click simple, márgenes de hoja y simulación en tiempo real.
"""
import os
import json
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QStatusBar, QFileDialog, QMessageBox, QTabWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QHBoxLayout, QSplitter, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QIcon, QShortcut

from ..graphics import CircuitScene, CircuitView, ComponentItem
from ..core.simulation import Simulator
from ..core.commands import CommandManager, AddComponentCommand
from ..core.cad_loader import CADLoader
from ..components.standard_components import STANDARD_COMPONENTS, create_standard_component
from ..qet import QETLoader
from .symbol_library_widget import SymbolLibraryWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimuCraft - Modern CADe SIMU (PySide6)")
        self.setGeometry(80, 80, 1360, 900)
        
        # Localizar raíz del proyecto
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(self.current_dir, "..", ".."))
        
        # Escena y Vista con soporte para márgenes y previsualización
        self.scene = CircuitScene(self)
        self.view = CircuitView(self.scene, self)
        self.setCentralWidget(self.view)
        
        self.command_manager = CommandManager(self)
        self.simulator = Simulator(self.scene.circuit_graph, self)
        self.simulator.simulation_step.connect(self.scene.update_simulation_visuals)
        
        # Conexiones de la escena con la barra de estado
        self.scene.cursor_moved.connect(self._on_cursor_moved)
        self.scene.placement_changed.connect(self._on_placement_changed)

        # Cargador de símbolos QElectroTech
        self.qet_loader = QETLoader()
        local_symbols = os.path.join(self.project_root, "assets", "qet_symbols")
        if os.path.isdir(local_symbols):
            self.qet_loader.add_directory(local_symbols)
        qet_elements = "/home/vibecode/DevS/qelectrotech-elements/elements"
        if os.path.isdir(qet_elements):
            self.qet_loader.add_directory(qet_elements)
            
        # UI
        self._create_actions()
        self._create_toolbar()
        self._create_dock_widgets()
        self._create_status_bar()
        self._create_menus()
        
        # Cargar esquema de ejemplo inicial para demostración inmediata
        self._load_initial_example()
        
    def _create_actions(self):
        self.act_new = QAction("📄 &Nuevo Esquema", self)
        self.act_new.setShortcut(QKeySequence.New)
        self.act_new.setStatusTip("Crear un nuevo esquema en blanco")
        self.act_new.triggered.connect(self.new_circuit)
        
        self.act_open = QAction("📂 &Abrir Esquema...", self)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_open.setStatusTip("Abrir esquema de CADe SIMU (.cad) o SimuCraft (.json)")
        self.act_open.triggered.connect(self.open_circuit)
        
        self.act_save = QAction("💾 &Guardar Esquema...", self)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save.setStatusTip("Guardar esquema actual")
        self.act_save.triggered.connect(self.save_circuit)
        
        self.act_undo = QAction("↩ &Deshacer", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setStatusTip("Deshacer última acción (Ctrl+Z)")
        self.act_undo.triggered.connect(self.command_manager.undo)
        
        self.act_redo = QAction("↪ &Rehacer", self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.setStatusTip("Rehacer última acción deshecha (Ctrl+Y)")
        self.act_redo.triggered.connect(self.command_manager.redo)
        
        # Herramientas de edición
        self.act_select_mode = QAction("👆 Selección / Salir", self)
        self.act_select_mode.setShortcut("Esc")
        self.act_select_mode.setStatusTip("Modo selección normal / Cancelar inserción o cableado (ESC)")
        self.act_select_mode.triggered.connect(self._on_select_mode_clicked)

        self.act_wire = QAction("⚡ Modo Cablear", self)
        self.act_wire.setCheckable(True)
        self.act_wire.setShortcut("W")
        self.act_wire.setStatusTip("Activar/desactivar herramienta de cableado (clic en un borne y luego en otro)")
        self.act_wire.toggled.connect(self._on_wire_toggled)
        
        self.act_delete = QAction("🗑️ Eliminar Selección", self)
        self.act_delete.setShortcut(QKeySequence.Delete)
        self.act_delete.setStatusTip("Eliminar componentes o cables seleccionados (Supr / Backspace)")
        self.act_delete.triggered.connect(self.delete_selected)

        # Atajo alternativo para Backspace
        self.sc_backspace = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        self.sc_backspace.activated.connect(self.delete_selected)

        # Simulación
        self.act_sim_start = QAction("▶ Iniciar &Simulación", self)
        self.act_sim_start.setShortcut("F5")
        self.act_sim_start.setStatusTip("Ejecutar simulación eléctrica en tiempo real (F5)")
        self.act_sim_start.triggered.connect(self.start_simulation)
        
        self.act_sim_stop = QAction("⏹ &Parar Simulación", self)
        self.act_sim_stop.setShortcut("Shift+F5")
        self.act_sim_stop.setStatusTip("Detener simulación (Shift+F5)")
        self.act_sim_stop.triggered.connect(self.stop_simulation)
        self.act_sim_stop.setEnabled(False)
        
        # Zoom y vistas
        self.act_zoom_in = QAction("🔍 Zoom +", self)
        self.act_zoom_in.setShortcut(QKeySequence.ZoomIn)
        self.act_zoom_in.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        
        self.act_zoom_out = QAction("🔎 Zoom -", self)
        self.act_zoom_out.setShortcut(QKeySequence.ZoomOut)
        self.act_zoom_out.triggered.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        
        self.act_zoom_fit = QAction("🔲 Ajustar Vista", self)
        self.act_zoom_fit.setStatusTip("Ajustar la vista para encajar toda la hoja de dibujo")
        self.act_zoom_fit.triggered.connect(self._fit_view)
        
    def _create_toolbar(self):
        toolbar = QToolBar("Herramientas Principales")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: #1e1e2e;
                border-bottom: 1px solid #313244;
                spacing: 4px;
                padding: 4px 8px;
            }
            QToolButton {
                color: #cdd6f4;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QToolButton:hover {
                background: #313244;
                border: 1px solid #45475a;
                color: #ffffff;
            }
            QToolButton:pressed {
                background: #45475a;
            }
            QToolButton:checked {
                background: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                font-weight: bold;
            }
            QToolBar::separator {
                background: #45475a;
                width: 1px;
                margin: 4px 6px;
            }
        """)
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_select_mode)
        toolbar.addAction(self.act_wire)
        toolbar.addAction(self.act_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.act_sim_start)
        toolbar.addAction(self.act_sim_stop)
        toolbar.addSeparator()
        toolbar.addAction(self.act_zoom_in)
        toolbar.addAction(self.act_zoom_out)
        toolbar.addAction(self.act_zoom_fit)
        
    def _create_dock_widgets(self):
        # Panel lateral izquierdo: Biblioteca interactiva de símbolos con click simple y preview
        left_dock = QDockWidget("Biblioteca de Símbolos y Esquemas", self)
        left_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        left_dock.setMinimumWidth(320)
        
        self.library_widget = SymbolLibraryWidget(self.qet_loader, self.project_root, self)
        # Click simple activa previsualización y modo de inserción
        self.library_widget.component_selected.connect(self.start_component_placement)
        self.library_widget.component_double_clicked.connect(self.start_component_placement)
        self.library_widget.example_double_clicked.connect(self.load_cad_schematic)
        
        left_dock.setWidget(self.library_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # Panel de Propiedades y Conductores / Cables (Derecha)
        prop_dock = QDockWidget("Propiedades y Cables", self)
        prop_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        prop_dock.setMinimumWidth(320)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #1e1e2e; }")

        prop_widget = QWidget()
        prop_layout = QVBoxLayout(prop_widget)
        prop_layout.setContentsMargins(8, 8, 8, 8)
        prop_layout.setSpacing(10)
        
        # 1. Caja de información del esquema
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(6, 6, 6, 6)
        info_layout.setSpacing(6)

        self.lbl_info = QLabel("<b>Esquema actual:</b> Sin título<br>Seleccione un componente o cable para editarlo.")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("color: #cdd6f4; font-size: 11px;")
        info_layout.addWidget(self.lbl_info)
        
        btn_center = QPushButton("🔲 Centrar Hoja de Dibujo")
        btn_center.setStyleSheet("""
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #45475a;
                color: #ffffff;
            }
        """)
        btn_center.clicked.connect(self._fit_view)
        info_layout.addWidget(btn_center)
        prop_layout.addWidget(info_frame)

        # 2. Selector interactivo de tipos y colores de cables (debajo de las propiedades)
        from .wire_palette_widget import WirePaletteWidget
        self.wire_palette = WirePaletteWidget(scene=self.scene, parent=self)
        self.wire_palette.wire_type_selected.connect(self._on_wire_type_selected)
        prop_layout.addWidget(self.wire_palette)

        prop_layout.addStretch()
        scroll.setWidget(prop_widget)
        prop_dock.setWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, prop_dock)

        # Conectar cambios de selección en la escena para actualizar la tarjeta de propiedades
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)

    def _create_status_bar(self):
        sb = self.statusBar()
        sb.setStyleSheet("""
            QStatusBar {
                background: #181825;
                color: #a6adc8;
                border-top: 1px solid #313244;
                font-size: 11px;
            }
            QStatusBar QLabel {
                padding: 2px 6px;
            }
        """)

        # Badge indicador del modo de trabajo activo
        self.lbl_mode_badge = QLabel(" Modo: Selección ")
        self.lbl_mode_badge.setStyleSheet("""
            background: #313244;
            color: #89b4fa;
            font-weight: bold;
            font-size: 11px;
            border-radius: 4px;
            padding: 2px 8px;
            margin-right: 8px;
        """)
        sb.addPermanentWidget(self.lbl_mode_badge)

        # Coordenadas dinámicas del cursor
        self.lbl_coords = QLabel("X: 0  |  Y: 0")
        self.lbl_coords.setStyleSheet("""
            background: #1e1e2e;
            color: #a6e3a1;
            font-family: monospace;
            font-size: 11px;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        sb.addPermanentWidget(self.lbl_coords)

        sb.showMessage("Listo - SimuCraft (CADe SIMU Modern Clone)")
        
    def _create_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background: #1e1e2e;
                color: #cdd6f4;
                border-bottom: 1px solid #313244;
            }
            QMenuBar::item:selected {
                background: #313244;
                color: #ffffff;
            }
            QMenu {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected {
                background: #313244;
                color: #ffffff;
            }
        """)
        
        file_menu = menubar.addMenu("&Archivo")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_save)
        file_menu.addSeparator()
        file_menu.addAction("Salir", self.close)
        
        edit_menu = menubar.addMenu("&Editar")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_select_mode)
        edit_menu.addAction(self.act_wire)
        edit_menu.addAction(self.act_delete)
        
        sim_menu = menubar.addMenu("&Simulación")
        sim_menu.addAction(self.act_sim_start)
        sim_menu.addAction(self.act_sim_stop)
        
        view_menu = menubar.addMenu("&Ver")
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_fit)
        
        help_menu = menubar.addMenu("Ay&uda")
        help_menu.addAction("Acerca de SimuCraft", self._about)

    # ── MODO INSERCIÓN, PREVISUALIZACIÓN Y CABLEADO ───────────────────────────

    def start_component_placement(self, defn: dict):
        """
        Activar modo inserción con previsualización flotante al hacer click simple
        en cualquier componente de la biblioteca.
        """
        # Desactivar modo cablear si estaba activo
        if self.act_wire.isChecked():
            self.act_wire.setChecked(False)

        name = defn.get('name', 'Componente')
        tag = defn.get('tag') or defn.get('tag_prefix', '')
        
        self.scene.start_placement_mode(defn)
        self.statusBar().showMessage(
            f"📌 Insertando: '{name}' ({tag}) — Mueva el ratón en la hoja y haga CLIC para estampar | Presione ESC para cancelar"
        )

    def _on_select_mode_clicked(self):
        """Cancelar cualquier modo activo (inserción o cableado) y volver a selección."""
        if self.scene.placement_mode:
            self.scene.cancel_placement()
        if self.act_wire.isChecked():
            self.act_wire.setChecked(False)
        self.scene.set_wiring_mode(False)
        self.statusBar().showMessage("Modo Selección normal activo")

    def _on_wire_toggled(self, checked: bool):
        if checked:
            if self.scene.placement_mode:
                self.scene.cancel_placement()
            self.scene.set_wiring_mode(True)
            self.lbl_mode_badge.setText(" Modo: Cablear (W) ")
            self.lbl_mode_badge.setStyleSheet("""
                background: #f38ba8;
                color: #11111b;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 8px;
            """)
            self.statusBar().showMessage("Modo Cablear ACTIVO: Haga clic en un borne y luego en otro para conectar | ESC para salir")
        else:
            self.scene.set_wiring_mode(False)
            if not self.scene.placement_mode:
                self.lbl_mode_badge.setText(" Modo: Selección ")
                self.lbl_mode_badge.setStyleSheet("""
                    background: #313244;
                    color: #89b4fa;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 2px 8px;
                """)
            self.statusBar().showMessage("Modo Cablear DESACTIVADO")

    def _on_placement_changed(self, active: bool, comp_name: str):
        if active:
            self.lbl_mode_badge.setText(f" Insertando: {comp_name} ")
            self.lbl_mode_badge.setStyleSheet("""
                background: #a6e3a1;
                color: #11111b;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 8px;
            """)
        else:
            if not self.scene.wiring_mode:
                self.lbl_mode_badge.setText(" Modo: Selección ")
                self.lbl_mode_badge.setStyleSheet("""
                    background: #313244;
                    color: #89b4fa;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 2px 8px;
                """)

    def _on_wire_type_selected(self, tid: int, name: str, color_hex: str):
        pass

    def _on_scene_selection_changed(self):
        """Actualizar el panel de propiedades según los elementos seleccionados en la escena."""
        selected = self.scene.selectedItems()
        from ..graphics.component_item import ComponentItem
        from ..graphics.wire_item import WireItem
        from ..components.wire_types import get_wire_info

        if not selected:
            self.lbl_info.setText("<b>Esquema actual:</b> Activo<br>Seleccione un componente o cable para editarlo.")
            return

        components = [item for item in selected if isinstance(item, ComponentItem)]
        wires = [item for item in selected if isinstance(item, WireItem)]

        if wires and not components:
            if len(wires) == 1:
                w = wires[0]
                info = get_wire_info(w.wire_type)
                color_name = w.wire_color.name().upper()
                self.lbl_info.setText(
                    f"<b>Conductor seleccionado:</b> {info['name']}<br>"
                    f"Tipo: {info['full_name']}<br>"
                    f"Color: <span style='color:{color_name}; font-weight:bold;'>■ {color_name}</span> | Calibre: {w.wire_width}px<br>"
                    f"<i>Usa la paleta inferior para cambiar su tipo y color.</i>"
                )
            else:
                self.lbl_info.setText(
                    f"<b>{len(wires)} cables seleccionados.</b><br>"
                    f"<i>Haz clic en cualquier tipo o color en la paleta inferior para asignárselo a todos.</i>"
                )
        elif components and not wires:
            if len(components) == 1:
                c = components[0]
                tag = c.tag or c.name
                c_type = c.component_type.capitalize()
                terms = len(c.terminals)
                self.lbl_info.setText(
                    f"<b>Componente seleccionado:</b> {c.name}<br>"
                    f"Referencia: <b>{tag}</b> | Tipo: {c_type}<br>"
                    f"Bornes/Terminales: {terms}<br>"
                    f"<i>Doble clic para editar propiedades.</i>"
                )
            else:
                self.lbl_info.setText(f"<b>{len(components)} componentes seleccionados.</b>")
        else:
            self.lbl_info.setText(
                f"<b>Selección múltiple:</b> {len(components)} componentes y {len(wires)} cables.<br>"
                f"<i>Presione Supr para eliminar o elija un color de cable.</i>"
            )

    def _on_cursor_moved(self, x: float, y: float):
        self.lbl_coords.setText(f"X: {int(x):4d}  |  Y: {int(y):4d}")

    def delete_selected(self):
        """Eliminar los elementos seleccionados mediante el comando atómico Undo/Redo."""
        self.scene.delete_selected_items()

    def keyPressEvent(self, event):
        """Manejar atajos globales en la ventana principal."""
        if event.key() == Qt.Key_Escape:
            self._on_select_mode_clicked()
            event.accept()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    # ── CARGA Y DEMOSTRACIÓN DE ESQUEMAS ──────────────────────────────────────

    def _load_initial_example(self):
        """Cargar automáticamente Lab01.cad para que el lienzo no aparezca vacío"""
        lab01_path = os.path.join(self.project_root, "cadesimu", "examples", "Lab01.cad")
        if os.path.exists(lab01_path):
            try:
                self.load_cad_schematic(lab01_path)
            except Exception as e:
                print(f"Nota: No se cargó esquema inicial: {e}")

    def load_cad_schematic(self, filepath: str):
        """Cargar un archivo .cad en la escena"""
        stats = CADLoader.load_file(filepath, self.scene)
        self.simulator.set_graph(self.scene.circuit_graph)
        
        name = os.path.basename(filepath)
        self.lbl_info.setText(
            f"<b>Esquema CADe SIMU:</b> {name}<br>"
            f"Componentes: {stats['components_count']}<br>"
            f"Cables/Conexiones: {stats['wires_count']}<br>"
            f"<i>Haga clic en los pulsadores para conmutar estado. Inicie la simulación con ▶</i>"
        )
        self.statusBar().showMessage(f"Esquema cargado: {name} ({stats['components_count']} componentes, {stats['wires_count']} cables)")
        self._fit_view()

    def new_circuit(self):
        self.scene.clear_circuit()
        self.simulator.set_graph(self.scene.circuit_graph)
        self.lbl_info.setText("<b>Esquema actual:</b> Nuevo (en blanco)<br>Añada componentes desde la biblioteca.")
        self.statusBar().showMessage("Nuevo esquema en blanco preparado con hoja técnica de dibujo")

    def open_circuit(self):
        start_dir = os.path.join(self.project_root, "cadesimu", "examples")
        if not os.path.isdir(start_dir):
            start_dir = self.project_root
            
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Esquema Eléctrico",
            start_dir,
            "Esquemas CADe SIMU (*.cad);;Esquemas SimuCraft (*.json *.simu);;Todos los archivos (*.*)"
        )
        if filepath:
            if filepath.endswith(".cad"):
                self.load_cad_schematic(filepath)
            else:
                self._load_json_schematic(filepath)

    def _load_json_schematic(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.scene.clear_circuit()
            comp_map = {}
            for comp_data in data.get('components', []):
                comp_item = ComponentItem(comp_data['def'])
                if 'id' in comp_data:
                    comp_item.id = comp_data['id']
                comp_item.setPos(comp_data['x'], comp_data['y'])
                self.scene.add_component(comp_item)
                comp_map[comp_item.id] = comp_item

            for wire_data in data.get('wires', []):
                t1_info = wire_data.get('t1')
                t2_info = wire_data.get('t2')
                t1 = None
                t2 = None
                if t1_info and t1_info.get('comp_id') in comp_map:
                    t1 = comp_map[t1_info['comp_id']].get_terminal_by_id(t1_info.get('term_id'))
                if t2_info and t2_info.get('comp_id') in comp_map:
                    t2 = comp_map[t2_info['comp_id']].get_terminal_by_id(t2_info.get('term_id'))

                pt1 = QPointF(wire_data['pt1'][0], wire_data['pt1'][1]) if wire_data.get('pt1') else None
                pt2 = QPointF(wire_data['pt2'][0], wire_data['pt2'][1]) if wire_data.get('pt2') else None
                wt = wire_data.get('wire_type', 4000)
                wc = wire_data.get('color', None)

                if t1 and t2:
                    w = self.scene.connect_terminals(t1, t2)
                    if w and (wt or wc):
                        w.set_wire_type(wt, color=wc)
                elif pt1 and pt2:
                    self.scene.create_wire_between_points(pt1, pt2, t1, t2, wire_type=wt, color=wc)

            self.simulator.set_graph(self.scene.circuit_graph)
            self.statusBar().showMessage(f"Esquema JSON cargado: {os.path.basename(filepath)} ({len(comp_map)} componentes, {len(data.get('wires', []))} cables)")
            self._fit_view()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el esquema JSON:\n{e}")

    def save_circuit(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Esquema Eléctrico",
            self.project_root,
            "Esquemas SimuCraft (*.json *.simu)"
        )
        if filepath:
            data = {
                'version': "0.1.0",
                'components': [],
                'wires': [],
                'graph': self.scene.circuit_graph.to_dict()
            }
            for comp in self.scene.circuit_graph.components.values():
                if isinstance(comp, ComponentItem):
                    data['components'].append({
                        'id': comp.id,
                        'tag': comp.tag,
                        'x': comp.x(),
                        'y': comp.y(),
                        'def': comp.component_def
                    })
            for wire in self.scene.wires:
                t1_info = None
                t2_info = None
                if wire.terminal1 and wire.terminal1.parentItem():
                    t1_info = {
                        'comp_id': wire.terminal1.parentItem().id,
                        'term_id': wire.terminal1.terminal_id
                    }
                if wire.terminal2 and wire.terminal2.parentItem():
                    t2_info = {
                        'comp_id': wire.terminal2.parentItem().id,
                        'term_id': wire.terminal2.terminal_id
                    }
                pt1_info = [wire.pt1.x(), wire.pt1.y()] if wire.pt1 else None
                pt2_info = [wire.pt2.x(), wire.pt2.y()] if wire.pt2 else None
                data['wires'].append({
                    't1': t1_info,
                    't2': t2_info,
                    'pt1': pt1_info,
                    'pt2': pt2_info,
                    'wire_type': getattr(wire, 'wire_type', 4000),
                    'color': getattr(wire, 'wire_color', None).name() if getattr(wire, 'wire_color', None) else None
                })
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                self.statusBar().showMessage(f"Esquema guardado con éxito: {os.path.basename(filepath)} ({len(data['components'])} componentes, {len(data['wires'])} cables)")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar esquema:\n{e}")

    def start_simulation(self):
        self.simulator.start()
        self.act_sim_start.setEnabled(False)
        self.act_sim_stop.setEnabled(True)
        self.statusBar().showMessage("▶ Simulación EN EJECUCIÓN (Líneas energizadas en rojo)")

    def stop_simulation(self):
        self.simulator.stop()
        self.act_sim_start.setEnabled(True)
        self.act_sim_stop.setEnabled(False)
        self.scene.circuit_graph.clear_all_potentials()
        self.scene.update_simulation_visuals()
        self.statusBar().showMessage("⏹ Simulación DETENIDA")

    def _fit_view(self):
        self.view.fit_in_view()

    def _about(self):
        QMessageBox.about(
            self,
            "Acerca de SimuCraft",
            "<h3>SimuCraft v0.1.0</h3>"
            "<p>Clon moderno de <b>CADe SIMU</b> desarrollado con Python y PySide6.</p>"
            "<ul>"
            "<li><b>Hoja técnica normalizada:</b> Con márgenes, marco y cajetín de plano</li>"
            "<li><b>Inserción dinámica:</b> Vista previa flotante (ghost preview) y selección con clic simple</li>"
            "<li><b>Cancelación con ESC:</b> Salir ágilmente de cualquier modo de edición</li>"
            "<li><b>Eliminación atómica:</b> Supr / Backspace con soporte completo Undo/Redo</li>"
            "<li><b>Esquemas:</b> Carga nativa de archivos .cad clásicos</li>"
            "<li><b>Simulación interactiva:</b> Conducción y coloreado en tiempo real</li>"
            "</ul>"
        )
