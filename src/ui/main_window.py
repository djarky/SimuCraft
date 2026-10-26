"""
Ventana principal de SimuCraft - Entorno CAD interactivo para automatismos eléctricos
Soporta carga de esquemas CADe SIMU (.cad), creación de esquemas, cableado dinámico y simulación
"""
import os
import json
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QStatusBar, QFileDialog, QMessageBox, QTabWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QHBoxLayout, QSplitter
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QIcon

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
        self.setGeometry(100, 100, 1280, 850)
        
        # Localizar raíz del proyecto
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(self.current_dir, "..", ".."))
        
        # Core
        self.scene = CircuitScene(self)
        self.view = CircuitView(self.scene, self)
        self.setCentralWidget(self.view)
        
        self.command_manager = CommandManager(self)
        self.simulator = Simulator(self.scene.circuit_graph, self)
        self.simulator.simulation_step.connect(self.scene.update_simulation_visuals)
        
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
        self.act_new = QAction("&Nuevo Esquema", self)
        self.act_new.setShortcut(QKeySequence.New)
        self.act_new.setStatusTip("Crear un nuevo esquema en blanco")
        self.act_new.triggered.connect(self.new_circuit)
        
        self.act_open = QAction("&Abrir Esquema...", self)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_open.setStatusTip("Abrir esquema de CADe SIMU (.cad) o SimuCraft (.json)")
        self.act_open.triggered.connect(self.open_circuit)
        
        self.act_save = QAction("&Guardar Esquema...", self)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save.setStatusTip("Guardar esquema actual")
        self.act_save.triggered.connect(self.save_circuit)
        
        self.act_undo = QAction("&Deshacer", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.triggered.connect(self.command_manager.undo)
        
        self.act_redo = QAction("&Rehacer", self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.triggered.connect(self.command_manager.redo)
        
        self.act_wire = QAction("&Modo Cablear", self)
        self.act_wire.setCheckable(True)
        self.act_wire.setShortcut("W")
        self.act_wire.setStatusTip("Activar/desactivar herramienta de cableado (clic en un borne y luego en otro)")
        self.act_wire.toggled.connect(self._on_wire_toggled)
        
        self.act_sim_start = QAction("▶ Iniciar &Simulación", self)
        self.act_sim_start.setShortcut("F5")
        self.act_sim_start.setStatusTip("Ejecutar simulación eléctrica en tiempo real")
        self.act_sim_start.triggered.connect(self.start_simulation)
        
        self.act_sim_stop = QAction("⏹ &Parar Simulación", self)
        self.act_sim_stop.setShortcut("Shift+F5")
        self.act_sim_stop.setStatusTip("Detener simulación")
        self.act_sim_stop.triggered.connect(self.stop_simulation)
        
        self.act_zoom_in = QAction("Zoom +", self)
        self.act_zoom_in.setShortcut(QKeySequence.ZoomIn)
        self.act_zoom_in.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        
        self.act_zoom_out = QAction("Zoom -", self)
        self.act_zoom_out.setShortcut(QKeySequence.ZoomOut)
        self.act_zoom_out.triggered.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        
        self.act_zoom_fit = QAction("Ajustar Vista", self)
        self.act_zoom_fit.triggered.connect(self._fit_view)
        
    def _create_toolbar(self):
        toolbar = QToolBar("Herramientas Principales")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_wire)
        toolbar.addSeparator()
        toolbar.addAction(self.act_sim_start)
        toolbar.addAction(self.act_sim_stop)
        toolbar.addSeparator()
        toolbar.addAction(self.act_zoom_in)
        toolbar.addAction(self.act_zoom_out)
        toolbar.addAction(self.act_zoom_fit)
        
    def _create_dock_widgets(self):
        # Panel lateral izquierdo: Biblioteca interactiva de símbolos con vista previa y búsqueda
        left_dock = QDockWidget("Biblioteca de Símbolos y Esquemas", self)
        left_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        left_dock.setMinimumWidth(310)
        
        self.library_widget = SymbolLibraryWidget(self.qet_loader, self.project_root, self)
        self.library_widget.component_double_clicked.connect(self.add_component_from_defn)
        self.library_widget.example_double_clicked.connect(self.load_cad_schematic)
        
        left_dock.setWidget(self.library_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # Panel de Propiedades / Estado
        prop_dock = QDockWidget("Propiedades del Esquema", self)
        prop_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        prop_widget = QWidget()
        prop_layout = QVBoxLayout(prop_widget)
        
        self.lbl_info = QLabel("<b>Esquema actual:</b> Sin título<br>Seleccione un componente para editarlo.")
        self.lbl_info.setWordWrap(True)
        prop_layout.addWidget(self.lbl_info)
        
        btn_center = QPushButton("Centrar Esquema")
        btn_center.clicked.connect(self._fit_view)
        prop_layout.addWidget(btn_center)
        
        prop_layout.addStretch()
        prop_dock.setWidget(prop_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, prop_dock)

    def _create_status_bar(self):
        sb = self.statusBar()
        sb.showMessage("Listo - SimuCraft v0.1.0 (CADe SIMU Modern Clone)")
        
    def _create_menus(self):
        menubar = self.menuBar()
        
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
        edit_menu.addAction(self.act_wire)
        
        sim_menu = menubar.addMenu("&Simulación")
        sim_menu.addAction(self.act_sim_start)
        sim_menu.addAction(self.act_sim_stop)
        
        view_menu = menubar.addMenu("&Ver")
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_fit)
        
        help_menu = menubar.addMenu("Ay&uda")
        help_menu.addAction("Acerca de SimuCraft", self._about)
        
    def _populate_examples(self):
        examples_dir = os.path.join(self.project_root, "cadesimu", "examples")
        if os.path.isdir(examples_dir):
            files = sorted(os.listdir(examples_dir))
            for f in files:
                if f.endswith(".cad"):
                    item = QListWidgetItem(f"📐 {f}")
                    item.setData(Qt.UserRole, os.path.join(examples_dir, f))
                    self.examples_list.addItem(item)
                    
    def _populate_qet_symbols(self):
        available = self.qet_loader.scan_available()
        # Mostrar los primeros 50 para rapidez
        for name in available[:50]:
            item = QListWidgetItem(f"🔹 {os.path.basename(name)}")
            item.setData(Qt.UserRole, name)
            self.qet_list.addItem(item)

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
        self.statusBar().showMessage("Nuevo esquema en blanco preparado")

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
            # 1. Cargar componentes
            comp_map = {}
            for comp_data in data.get('components', []):
                comp_item = ComponentItem(comp_data['def'])
                if 'id' in comp_data:
                    comp_item.id = comp_data['id']
                comp_item.setPos(comp_data['x'], comp_data['y'])
                self.scene.add_component(comp_item)
                comp_map[comp_item.id] = comp_item

            # 2. Recrear cables
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

                if t1 and t2:
                    self.scene.connect_terminals(t1, t2)
                elif pt1 and pt2:
                    self.scene.create_wire_between_points(pt1, pt2, t1, t2)

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
                    'pt2': pt2_info
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
        # Limpiar potenciales y actualizar cables a color normal
        self.scene.circuit_graph.clear_all_potentials()
        self.scene.update_simulation_visuals()
        self.statusBar().showMessage("⏹ Simulación DETENIDA")

    def _on_wire_toggled(self, checked: bool):
        self.scene.set_wiring_mode(checked)
        if checked:
            self.statusBar().showMessage("Modo Cablear ACTIVO: Haga clic en un borne para iniciar y en otro para conectar")
        else:
            self.statusBar().showMessage("Modo Cablear DESACTIVADO")

    def add_component_from_defn(self, defn: dict):
        """Insertar un componente en el esquema con registro en Undo/Redo"""
        comp_item = ComponentItem(defn)
        center = self.view.mapToScene(self.view.viewport().rect().center())
        comp_item.setPos(center)
        cmd = AddComponentCommand(
            self.scene, comp_item,
            f"Añadir {defn.get('name', 'Componente')}"
        )
        self.command_manager.push(cmd)
        tag = defn.get('tag') or defn.get('tag_prefix', '')
        self.statusBar().showMessage(f"Componente añadido: {defn.get('name')} ({tag}) — Ctrl+Z para deshacer")

    def _fit_view(self):
        rect = self.scene.itemsBoundingRect()
        if not rect.isEmpty():
            self.view.fitInView(rect.adjusted(-50, -50, 50, 50), Qt.KeepAspectRatio)

    def _about(self):
        QMessageBox.about(
            self,
            "Acerca de SimuCraft",
            "<h3>SimuCraft v0.1.0</h3>"
            "<p>Clon moderno de <b>CADe SIMU</b> desarrollado con Python y PySide6.</p>"
            "<ul>"
            "<li><b>Esquemas:</b> Carga nativa de archivos .cad clásicos</li>"
            "<li><b>Grafo Relacional:</b> Conexiones lógicas magnéticas sin píxeles rígidos</li>"
            "<li><b>Símbolos QElectroTech:</b> Parser XML/SVG vectorial</li>"
            "<li><b>Simulación interactiva:</b> Conducción y coloreado en tiempo real</li>"
            "</ul>"
        )
