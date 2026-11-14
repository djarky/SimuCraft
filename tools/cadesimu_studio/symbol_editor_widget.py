"""
Widget del editor visual interactivo SimuCraft Symbol & Terminal Studio.
"""
import os
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QComboBox, QPushButton, QLabel, QSpinBox, QFormLayout,
    QLineEdit, QGraphicsView, QMessageBox, QFileDialog, QListWidget,
    QListWidgetItem, QButtonGroup, QColorDialog
)
from PySide6.QtCore import Qt, QPointF, QByteArray, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QKeySequence, QUndoStack
from PySide6.QtGui import QShortcut

from .config import BASE_PATH, CUSTOM_SYMBOLS_PATH
from .terminal_handle import TerminalHandleItem
from .canvas_scene import SymbolCanvasScene, SymbolGraphicsView
from .qet_importer import QETVectorImporter
from .standard_primitive_factory import create_standard_primitives

try:
    from src.components.standard_components import STANDARD_COMPONENTS, reload_custom_symbols
except Exception:
    STANDARD_COMPONENTS = {}
    def reload_custom_symbols():
        pass

try:
    from src.qet.parser import QETParser
    PARSER = QETParser()
except Exception:
    PARSER = None

class SymbolEditorWidget(QWidget):
    """Editor interactivo visual de símbolos y posiciones de bornes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cur_symbol = {}
        self.terminal_items = []
        self.selected_item = None
        self.svg_renderer = None
        self._clipboard = []
        self.undo_stack = QUndoStack(self)
        self.init_ui()
        self.load_component_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # ---------------- Barra superior de herramientas ----------------
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("Componente:"))
        self.comp_combo = QComboBox()
        self.comp_combo.setMinimumWidth(260)
        self.comp_combo.currentIndexChanged.connect(self.on_component_selected)
        toolbar.addWidget(self.comp_combo)
        
        btn_new = QPushButton("➕ Nuevo Símbolo")
        btn_new.clicked.connect(self.new_custom_symbol)
        toolbar.addWidget(btn_new)
        
        btn_import_svg = QPushButton("📂 Importar SVG / .elmt")
        btn_import_svg.clicked.connect(self.import_svg_or_elmt)
        toolbar.addWidget(btn_import_svg)

        btn_browse_qet = QPushButton("📦 Explorar Librería QET")
        btn_browse_qet.clicked.connect(self.import_from_qet_browser)
        toolbar.addWidget(btn_browse_qet)

        toolbar.addSpacing(15)

        btn_undo = QPushButton("↩ Deshacer")
        btn_undo.setToolTip("Ctrl+Z")
        btn_undo.clicked.connect(self.undo_stack.undo)
        toolbar.addWidget(btn_undo)

        btn_redo = QPushButton("↪ Rehacer")
        btn_redo.setToolTip("Ctrl+Y")
        btn_redo.clicked.connect(self.undo_stack.redo)
        toolbar.addWidget(btn_redo)

        toolbar.addSpacing(15)
        toolbar.addWidget(QLabel("Rejilla:"))
        self.snap_combo = QComboBox()
        self.snap_combo.addItems(["18 px (Estándar CADe)", "6 px (Precisa)", "1 px (Libre)"])
        self.snap_combo.currentIndexChanged.connect(self.on_snap_changed)
        toolbar.addWidget(self.snap_combo)

        btn_align = QPushButton("📐 Auto-Alinear 18px")
        btn_align.clicked.connect(self.auto_align_terminals)
        toolbar.addWidget(btn_align)

        toolbar.addStretch()

        btn_save = QPushButton("💾 Guardar en SimuCraft")
        btn_save.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self.save_symbol_to_simucraft)
        toolbar.addWidget(btn_save)

        main_layout.addLayout(toolbar)

        # ---------------- Splitter: Lienzo (Izq) | Inspector (Der) ----------------
        splitter = QSplitter(Qt.Horizontal)

        # Lienzo Gráfico
        canvas_box = QGroupBox("Lienzo Interactivo de Símbolo")
        canvas_layout = QVBoxLayout(canvas_box)

        # ---------------- Barra de Herramientas de Dibujo (Estilo Inkscape / Paint) ----------------
        draw_bar = QHBoxLayout()
        draw_bar.addWidget(QLabel("<b>Herramienta:</b>"))

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools_def = [
            ("select", "🖱️ Seleccionar"),
            ("line", "📏 Línea"),
            ("rect", "⬜ Rectángulo"),
            ("circle", "⭕ Círculo"),
            ("text", "🔤 Texto")
        ]
        for mode, title in tools_def:
            btn = QPushButton(title)
            btn.setCheckable(True)
            if mode == "select":
                btn.setChecked(True)
            btn.clicked.connect(lambda chk, m=mode: self.set_draw_tool(m))
            self.tool_group.addButton(btn)
            draw_bar.addWidget(btn)

        draw_bar.addSpacing(10)
        draw_bar.addWidget(QLabel("Color:"))
        self.btn_color = QPushButton("■")
        self.btn_color.setFixedWidth(30)
        self.btn_color.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; background: #252830;")
        self.btn_color.clicked.connect(self.choose_stroke_color)
        draw_bar.addWidget(self.btn_color)

        draw_bar.addWidget(QLabel("Grosor:"))
        self.width_combo = QComboBox()
        self.width_combo.addItems(["1.0 px (Fino)", "1.8 px (Normal)", "2.5 px (Grueso)"])
        self.width_combo.setCurrentIndex(1)
        self.width_combo.currentIndexChanged.connect(self.on_stroke_width_changed)
        draw_bar.addWidget(self.width_combo)

        btn_del_primitive = QPushButton("🗑️ Eliminar Elemento")
        btn_del_primitive.setStyleSheet("background: #c0392b; color: white;")
        btn_del_primitive.clicked.connect(self.delete_selected_primitives)
        draw_bar.addWidget(btn_del_primitive)

        draw_bar.addStretch()
        canvas_layout.addLayout(draw_bar)
        
        self.scene = SymbolCanvasScene(self)
        self.scene.selectionChanged.connect(self.on_scene_selection_changed)
        self.scene.undo_stack = self.undo_stack
        
        self.view = SymbolGraphicsView(self.scene)
        canvas_layout.addWidget(self.view)
        
        # Atajos de teclado globales
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_stack.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.undo_stack.redo)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_selected)
        QShortcut(QKeySequence("Ctrl+V"), self, self.paste_items)
        
        # Barra de zoom del lienzo
        zoom_bar = QHBoxLayout()
        btn_zin = QPushButton("🔍 Zoom +")
        btn_zin.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        btn_zout = QPushButton("🔍 Zoom -")
        btn_zout.clicked.connect(lambda: self.view.scale(0.833, 0.833))
        btn_zreset = QPushButton("↺ Centrar Origen")
        btn_zreset.clicked.connect(lambda: self.view.centerOn(45, 36))
        zoom_bar.addWidget(btn_zin)
        zoom_bar.addWidget(btn_zout)
        zoom_bar.addWidget(btn_zreset)
        zoom_bar.addStretch()
        self.info_status = QLabel("Listo.")
        self.info_status.setStyleSheet("color: #888;")
        zoom_bar.addWidget(self.info_status)
        canvas_layout.addLayout(zoom_bar)
        
        splitter.addWidget(canvas_box)

        # Panel Inspector Lateral
        inspector_box = QGroupBox("Inspector de Símbolo y Bornes")
        inspector_layout = QVBoxLayout(inspector_box)
        inspector_layout.setSpacing(10)

        # Metadatos del Símbolo
        sym_form = QFormLayout()
        self.input_sym_id = QLineEdit()
        self.input_sym_name = QLineEdit()
        self.input_sym_type = QComboBox()
        self.input_sym_type.addItems([
            'motor', 'contactor_power', 'contactor', 'contact_no', 'contact_nc',
            'pushbutton', 'breaker', 'breaker_3p', 'lamp', 'relay', 'power', 'neutral', 'generic'
        ])
        self.input_sym_type.currentTextChanged.connect(self.on_sym_type_changed)
        
        dim_layout = QHBoxLayout()
        self.spin_width = QSpinBox()
        self.spin_width.setRange(20, 600)
        self.spin_width.setSingleStep(18)
        self.spin_width.valueChanged.connect(self.on_dimensions_changed)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(20, 600)
        self.spin_height.setSingleStep(18)
        self.spin_height.valueChanged.connect(self.on_dimensions_changed)
        dim_layout.addWidget(QLabel("Ancho:"))
        dim_layout.addWidget(self.spin_width)
        dim_layout.addWidget(QLabel("Alto:"))
        dim_layout.addWidget(self.spin_height)

        sym_form.addRow("ID Clave:", self.input_sym_id)
        sym_form.addRow("Nombre:", self.input_sym_name)
        sym_form.addRow("Tipo Lógico:", self.input_sym_type)
        sym_form.addRow("Tamaño (px):", dim_layout)
        inspector_layout.addLayout(sym_form)

        # Lista de Bornes
        inspector_layout.addWidget(QLabel("<b>Lista de Bornes / Terminales:</b>"))
        self.term_list_widget = QListWidget()
        self.term_list_widget.currentRowChanged.connect(self.on_term_list_selected)
        inspector_layout.addWidget(self.term_list_widget)

        term_btns = QHBoxLayout()
        btn_add_term = QPushButton("➕ Añadir Borne")
        btn_add_term.clicked.connect(self.add_new_terminal)
        btn_del_term = QPushButton("❌ Eliminar Borne")
        btn_del_term.clicked.connect(self.delete_selected_terminal)
        term_btns.addWidget(btn_add_term)
        term_btns.addWidget(btn_del_term)
        inspector_layout.addLayout(term_btns)

        # Formulario de Borne Seleccionado
        term_group = QGroupBox("Propiedades del Borne Seleccionado")
        term_form = QFormLayout(term_group)
        
        self.input_term_id = QLineEdit()
        self.input_term_id.textChanged.connect(self.on_term_field_edited)
        self.input_term_name = QLineEdit()
        self.input_term_name.textChanged.connect(self.on_term_field_edited)
        
        pos_layout = QHBoxLayout()
        self.spin_term_x = QSpinBox()
        self.spin_term_x.setRange(-200, 600)
        self.spin_term_x.setSingleStep(6)
        self.spin_term_x.valueChanged.connect(self.on_term_pos_spin_changed)
        self.spin_term_y = QSpinBox()
        self.spin_term_y.setRange(-200, 600)
        self.spin_term_y.setSingleStep(6)
        self.spin_term_y.valueChanged.connect(self.on_term_pos_spin_changed)
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.spin_term_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.spin_term_y)

        self.combo_term_orient = QComboBox()
        self.combo_term_orient.addItem("N (Norte / Arriba)", "n")
        self.combo_term_orient.addItem("S (Sur / Abajo)", "s")
        self.combo_term_orient.addItem("E (Este / Derecha)", "e")
        self.combo_term_orient.addItem("W (Oeste / Izquierda)", "w")
        self.combo_term_orient.currentIndexChanged.connect(self.on_term_field_edited)

        self.combo_term_type = QComboBox()
        self.combo_term_type.addItems([
            'motor_in', 'power_in', 'neutral', 'earth', 'contact',
            'coil_in', 'coil_out', 'lamp_in', 'lamp_out', 'generic'
        ])
        self.combo_term_type.currentIndexChanged.connect(self.on_term_field_edited)

        term_form.addRow("ID Borne:", self.input_term_id)
        term_form.addRow("Etiqueta:", self.input_term_name)
        term_form.addRow("Posición:", pos_layout)
        term_form.addRow("Orientación:", self.combo_term_orient)
        term_form.addRow("Tipo Borne:", self.combo_term_type)
        inspector_layout.addWidget(term_group)

        splitter.addWidget(inspector_box)
        splitter.setSizes([900, 450])
        main_layout.addWidget(splitter)

    # ---------------- Lógica de Componentes ----------------

    def load_component_list(self):
        self.comp_combo.blockSignals(True)
        self.comp_combo.clear()
        
        # Cargar componentes estándar
        reload_custom_symbols()
        keys = sorted(list(STANDARD_COMPONENTS.keys()))
        for k in keys:
            c = STANDARD_COMPONENTS[k]
            self.comp_combo.addItem(f"{k} ({c.get('name', '')})", k)
            
        self.comp_combo.blockSignals(False)
        if keys:
            # Seleccionar motor_3p por defecto
            idx = self.comp_combo.findData('motor_3p')
            self.comp_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.load_component(self.comp_combo.currentData())

    def on_component_selected(self, index):
        comp_key = self.comp_combo.currentData()
        if comp_key:
            self.load_component(comp_key)

    def load_component(self, comp_key: str):
        if comp_key not in STANDARD_COMPONENTS:
            return
            
        src = STANDARD_COMPONENTS[comp_key]
        import copy
        self.cur_symbol = copy.deepcopy(src)
        
        vis = self.cur_symbol.get('visual', {})
        w = float(vis.get('width', 90))
        h = float(vis.get('height', 72))
        ctype = self.cur_symbol.get('type', 'generic')
        
        # Actualizar campos
        self.input_sym_id.setText(self.cur_symbol.get('id', comp_key))
        self.input_sym_name.setText(self.cur_symbol.get('name', ''))
        
        t_idx = self.input_sym_type.findText(ctype)
        if t_idx >= 0:
            self.input_sym_type.setCurrentIndex(t_idx)
            
        self.spin_width.setValue(int(w))
        self.spin_height.setValue(int(h))

        # Cargar primitivas vectoriales si tiene archivo .elmt
        if vis.get('elmt_path') and os.path.exists(vis.get('elmt_path')) and vis.get('elmt_path').endswith('.elmt'):
            self._load_elmt_into_scene(vis['elmt_path'])
        else:
            # Sin .elmt: limpiar primitivas no-terminales previas
            for it in list(self.scene.items()):
                if not isinstance(it, TerminalHandleItem):
                    self.scene.removeItem(it)
            # Descomposición vectorial interactiva de elementos estándar
            std_items = create_standard_primitives(comp_key, self.cur_symbol)
            for it in std_items:
                self.scene.addItem(it)

        self.scene.set_component_bounds(w, h, ctype)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)
        self.info_status.setText(f"Cargado: {comp_key} ({len(vis.get('terminals', []))} bornes)")

    def refresh_terminal_items(self):
        # Limpiar escena de bornes anteriores
        for item in self.terminal_items:
            self.scene.removeItem(item)
        self.terminal_items.clear()
        
        self.term_list_widget.blockSignals(True)
        self.term_list_widget.clear()

        vis = self.cur_symbol.setdefault('visual', {})
        terms = vis.setdefault('terminals', [])
        
        snap = self.get_current_snap()
        for idx, t in enumerate(terms):
            handle = TerminalHandleItem(t, self.on_handle_moved, grid_snap=snap)
            self.scene.addItem(handle)
            self.terminal_items.append(handle)
            
            t_id = t.get('name') or t.get('id', f'T{idx}')
            pos_str = f"({int(t.get('x',0))}, {int(t.get('y',0))})"
            orient = t.get('orientation', 'n').upper()
            it = QListWidgetItem(f"[{orient}] {t_id} {pos_str}")
            it.setData(Qt.UserRole, handle)
            self.term_list_widget.addItem(it)

        self.term_list_widget.blockSignals(False)

        if self.terminal_items:
            self.terminal_items[0].setSelected(True)
            self.on_handle_selected(self.terminal_items[0])

    def get_current_snap(self) -> int:
        idx = self.snap_combo.currentIndex()
        if idx == 0:
            return 18
        elif idx == 1:
            return 6
        return 1

    def on_snap_changed(self):
        snap = self.get_current_snap()
        for it in self.terminal_items:
            it.grid_snap = snap

    def on_dimensions_changed(self):
        w = float(self.spin_width.value())
        h = float(self.spin_height.value())
        self.cur_symbol.setdefault('visual', {})['width'] = w
        self.cur_symbol.setdefault('visual', {})['height'] = h
        self.scene.set_component_bounds(w, h, self.input_sym_type.currentText())

    def on_sym_type_changed(self, text):
        self.cur_symbol['type'] = text
        self.scene.set_component_bounds(
            float(self.spin_width.value()),
            float(self.spin_height.value()),
            text
        )

    # ---------------- Manipulación de Bornes ----------------

    def on_handle_moved(self, handle: TerminalHandleItem):
        if handle == self.selected_item:
            self.spin_term_x.blockSignals(True)
            self.spin_term_y.blockSignals(True)
            self.spin_term_x.setValue(int(handle.term_data.get('x', 0)))
            self.spin_term_y.setValue(int(handle.term_data.get('y', 0)))
            self.spin_term_x.blockSignals(False)
            self.spin_term_y.blockSignals(False)
            self.update_terminal_list_item(handle)

    def on_scene_selection_changed(self):
        if getattr(self, '_is_updating_selection', False):
            return
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, TerminalHandleItem):
                self.on_handle_selected(item)
                break

    def on_handle_selected(self, handle: TerminalHandleItem):
        if getattr(self, '_is_updating_selection', False):
            return
        self._is_updating_selection = True
        try:
            self.selected_item = handle
            d = handle.term_data
            
            self.input_term_id.blockSignals(True)
            self.input_term_name.blockSignals(True)
            self.spin_term_x.blockSignals(True)
            self.spin_term_y.blockSignals(True)
            self.combo_term_orient.blockSignals(True)
            self.combo_term_type.blockSignals(True)

            self.input_term_id.setText(d.get('id', ''))
            self.input_term_name.setText(d.get('name', ''))
            self.spin_term_x.setValue(int(d.get('x', 0)))
            self.spin_term_y.setValue(int(d.get('y', 0)))

            orient = d.get('orientation', 'n').lower()
            idx = self.combo_term_orient.findData(orient)
            if idx >= 0:
                self.combo_term_orient.setCurrentIndex(idx)

            ttype = d.get('type', 'generic')
            idx2 = self.combo_term_type.findText(ttype)
            if idx2 >= 0:
                self.combo_term_type.setCurrentIndex(idx2)

            self.input_term_id.blockSignals(False)
            self.input_term_name.blockSignals(False)
            self.spin_term_x.blockSignals(False)
            self.spin_term_y.blockSignals(False)
            self.combo_term_orient.blockSignals(False)
            self.combo_term_type.blockSignals(False)

            # Sincronizar selección en la lista bloqueando señales
            self.term_list_widget.blockSignals(True)
            for r in range(self.term_list_widget.count()):
                it = self.term_list_widget.item(r)
                if it.data(Qt.UserRole) == handle:
                    self.term_list_widget.setCurrentRow(r)
                    break
            self.term_list_widget.blockSignals(False)
        finally:
            self._is_updating_selection = False

    def on_term_list_selected(self, row):
        if getattr(self, '_is_updating_selection', False):
            return
        self._is_updating_selection = True
        try:
            if row >= 0:
                it = self.term_list_widget.item(row)
                if it:
                    handle = it.data(Qt.UserRole)
                    if handle and isinstance(handle, TerminalHandleItem):
                        self.scene.blockSignals(True)
                        self.scene.clearSelection()
                        handle.setSelected(True)
                        self.scene.blockSignals(False)
                        self._is_updating_selection = False
                        self.on_handle_selected(handle)
        finally:
            self._is_updating_selection = False

    def on_term_field_edited(self):
        if not self.selected_item:
            return
        d = self.selected_item.term_data
        d['id'] = self.input_term_id.text().strip()
        d['name'] = self.input_term_name.text().strip()
        d['orientation'] = self.combo_term_orient.currentData()
        d['type'] = self.combo_term_type.currentText()
        self.selected_item.update()
        self.update_terminal_list_item(self.selected_item)

    def on_term_pos_spin_changed(self):
        if not self.selected_item:
            return
        x = float(self.spin_term_x.value())
        y = float(self.spin_term_y.value())
        self.selected_item.term_data['x'] = x
        self.selected_item.term_data['y'] = y
        self.selected_item.setPos(x, y)
        self.update_terminal_list_item(self.selected_item)

    def update_terminal_list_item(self, handle: TerminalHandleItem):
        for r in range(self.term_list_widget.count()):
            it = self.term_list_widget.item(r)
            if it.data(Qt.UserRole) == handle:
                t = handle.term_data
                t_id = t.get('name') or t.get('id', '')
                pos_str = f"({int(t.get('x',0))}, {int(t.get('y',0))})"
                orient = t.get('orientation', 'n').upper()
                it.setText(f"[{orient}] {t_id} {pos_str}")
                break

    def add_new_terminal(self):
        terms = self.cur_symbol.setdefault('visual', {}).setdefault('terminals', [])
        idx = len(terms) + 1
        # Sugerir posición en rejilla de 18px
        new_x = (len(terms) * 36) % int(max(self.spin_width.value(), 72))
        new_y = 0.0
        new_t = {
            "id": f"T{idx}",
            "name": f"T{idx}",
            "x": new_x,
            "y": new_y,
            "orientation": "n",
            "type": "contact"
        }
        terms.append(new_t)
        self.refresh_terminal_items()
        if self.terminal_items:
            last = self.terminal_items[-1]
            last.setSelected(True)
            self.on_handle_selected(last)

    def delete_selected_terminal(self):
        if not self.selected_item:
            QMessageBox.warning(self, "Atención", "Selecciona un borne en el lienzo o la lista para eliminar.")
            return
        terms = self.cur_symbol.setdefault('visual', {}).setdefault('terminals', [])
        if self.selected_item.term_data in terms:
            terms.remove(self.selected_item.term_data)
        self.refresh_terminal_items()

    def auto_align_terminals(self):
        """Alinea los bornes a la rejilla de 18px y distribuye simétricamente."""
        terms = self.cur_symbol.setdefault('visual', {}).setdefault('terminals', [])
        for t in terms:
            t['x'] = round(float(t.get('x', 0)) / 18.0) * 18.0
            t['y'] = round(float(t.get('y', 0)) / 18.0) * 18.0
        self.refresh_terminal_items()
        QMessageBox.information(self, "Alineado", "Todos los bornes han sido ajustados al paso estándar de 18px.")

    def set_draw_tool(self, tool_mode: str):
        self.scene.set_tool(tool_mode)
        if tool_mode == "select":
            self.view.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.view.setDragMode(QGraphicsView.NoDrag)
        self.info_status.setText(f"Herramienta activa: {tool_mode.capitalize()}")

    def choose_stroke_color(self):
        col = QColorDialog.getColor(self.scene.active_pen_color, self, "Seleccionar Color de Trazo")
        if col.isValid():
            self.scene.active_pen_color = col
            self.btn_color.setStyleSheet(f"color: {col.name()}; font-size: 16px; font-weight: bold; background: #252830;")

    def on_stroke_width_changed(self, index: int):
        widths = [1.0, 1.8, 2.5]
        if 0 <= index < len(widths):
            self.scene.active_pen_width = widths[index]

    def delete_selected_primitives(self):
        items = [it for it in self.scene.selectedItems() if not isinstance(it, TerminalHandleItem)]
        if not items:
            return
        if self.scene.undo_stack:
            from .undo_commands import DeleteItemsCommand
            self.scene.undo_stack.push(DeleteItemsCommand(self.scene, items))
        else:
            for it in items:
                self.scene.removeItem(it)

    def _load_elmt_into_scene(self, elmt_path: str):
        """
        Parsea un archivo .elmt con QETVectorImporter y carga TODAS las primitivas
        vectoriales en la escena, eliminando primero las no-terminales anteriores.
        Devuelve el dict resultado del importer o None si falla.
        """
        try:
            importer = QETVectorImporter()
            result = importer.import_from_elmt(elmt_path)
        except Exception as e:
            self.info_status.setText(f"⚠ Error al leer .elmt: {e}")
            return None

        # Limpiar primitivas previas que no sean terminales
        for it in list(self.scene.items()):
            if not isinstance(it, TerminalHandleItem):
                self.scene.removeItem(it)

        # Añadir todos los items desglosados
        for it in result['items']:
            self.scene.addItem(it)

        return result

    def load_elmt_file(self, elmt_path: str, sym_id: str = '', sym_name: str = ''):
        """
        Carga un archivo .elmt directamente en el editor:
        - Desglosa todas las primitivas vectoriales en el lienzo.
        - Reemplaza los bornes con los del archivo .elmt.
        - Ajusta dimensiones y centra la vista.
        Usado desde el mapper al hacer "Abrir en Symbol Studio".
        """
        result = self._load_elmt_into_scene(elmt_path)
        if result is None:
            return

        # Actualizar metadatos del símbolo
        self.cur_symbol = {
            'id':   sym_id or Path(elmt_path).stem,
            'name': sym_name or Path(elmt_path).stem,
            'type': 'generic',
            'visual': {
                'width':     result['width'],
                'height':    result['height'],
                'elmt_path': elmt_path,
                'terminals': result['terminals'],
            }
        }
        w = max(40, int(result['width']))
        h = max(40, int(result['height']))
        self.input_sym_id.setText(self.cur_symbol['id'])
        self.input_sym_name.setText(self.cur_symbol['name'])
        self.spin_width.setValue(w)
        self.spin_height.setValue(h)
        self.cur_symbol.setdefault('visual', {})['elmt_path'] = elmt_path
        self.scene.set_component_bounds(w, h, 'generic')
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)
        n_items = len(result['items'])
        n_terms = len(result['terminals'])
        self.info_status.setText(
            f"✔ .elmt cargado: {n_items} elementos vectoriales + {n_terms} bornes  —  {Path(elmt_path).name}"
        )

    def _fit_view_to_symbol(self, w: float, h: float):
        """Centra y ajusta el zoom de la vista para encuadrar el símbolo completo."""
        from PySide6.QtCore import QRectF
        margin = 60
        rect = self.scene.itemsBoundingRect()
        if rect.isNull():
            rect = QRectF(-margin, -margin, w + margin * 2, h + margin * 2)
        else:
            rect = rect.adjusted(-margin, -margin, margin, margin)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    def import_svg_or_elmt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Gráfico de Símbolo", str(BASE_PATH), "Archivos Símbolo (*.elmt *.svg)"
        )
        if not file_path:
            return

        if file_path.endswith('.elmt'):
            # Usar el método centralizado de carga vectorial
            result = self._load_elmt_into_scene(file_path)
            if result is None:
                return

            # Reemplazar bornes con los del archivo
            if result.get('terminals'):
                self.cur_symbol.setdefault('visual', {})['terminals'] = result['terminals']

            w = max(40, int(result.get('width', 90)))
            h = max(40, int(result.get('height', 72)))
            self.spin_width.setValue(w)
            self.spin_height.setValue(h)
            self.cur_symbol.setdefault('visual', {})['elmt_path'] = file_path
            self.scene.set_component_bounds(w, h, self.input_sym_type.currentText())
            self.refresh_terminal_items()
            self._fit_view_to_symbol(w, h)

            QMessageBox.information(
                self, "Importado con Éxito",
                f"Símbolo QET desglosado en {len(result['items'])} elementos vectoriales interactivos "
                f"y {len(result['terminals'])} bornes.\n\n"
                f"Tipos: líneas, rectángulos, círculos, arcos, polígonos, textos."
            )
        elif file_path.endswith('.svg'):
            # Fallback para SVG simple
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                svg_code = f.read()
            self.cur_symbol.setdefault('visual', {})['svg_content'] = svg_code
            self.cur_symbol['visual']['elmt_path'] = file_path
            QMessageBox.information(self, "Importado", f"Archivo SVG cargado: {file_path}")

    def new_custom_symbol(self):
        self.cur_symbol = {
            "id": "nuevo_simbolo",
            "type": "generic",
            "name": "Nuevo Símbolo Personalizado",
            "tag_prefix": "-K",
            "visual": {
                "width": 90,
                "height": 72,
                "terminals": [
                    {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                    {"id": "2", "name": "2", "x": 0, "y": 72, "orientation": "s", "type": "contact"}
                ]
            },
            "logic": {
                "class": "AuxiliaryContact",
                "behavior": "passive",
                "internal_connections": [("1", "2")]
            }
        }
        self.input_sym_id.setText(self.cur_symbol["id"])
        self.input_sym_name.setText(self.cur_symbol["name"])
        self.input_sym_type.setCurrentText("generic")
        self.spin_width.setValue(90)
        self.spin_height.setValue(72)
        self.svg_renderer = None
        self.scene.set_component_bounds(90, 72, "generic")
        self.refresh_terminal_items()

    def save_symbol_to_simucraft(self):
        sym_id = self.input_sym_id.text().strip()
        if not sym_id:
            QMessageBox.warning(self, "Error", "El símbolo debe tener un ID válido.")
            return

        # Actualizar diccionario
        self.cur_symbol['id'] = sym_id
        self.cur_symbol['name'] = self.input_sym_name.text().strip()
        self.cur_symbol['type'] = self.input_sym_type.currentText()
        vis = self.cur_symbol.setdefault('visual', {})
        vis['width'] = float(self.spin_width.value())
        vis['height'] = float(self.spin_height.value())
        # Exportar las geometrías de la escena a SVG
        vis['svg_content'] = self.scene.export_primitives_to_svg()
        
        # Archivo de destino en data/
        custom_file = BASE_PATH / "data" / "custom_symbols.json"
        custom_file.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if custom_file.exists():
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing[sym_id] = self.cur_symbol
        with open(custom_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        # Actualizar en memoria viva
        STANDARD_COMPONENTS[sym_id] = self.cur_symbol
        
        QMessageBox.information(
            self, "Guardado con Éxito",
            f"El símbolo '{sym_id}' se ha guardado en custom_symbols.json y está disponible de inmediato en SimuCraft."
        )
        self.load_component_list()

    # ------------------------------------------------------------------ #
    # Clipboard                                                            #
    # ------------------------------------------------------------------ #

    def copy_selected(self):
        """Copia los elementos seleccionados al portapapeles interno."""
        self._clipboard = [it for it in self.scene.selectedItems() if hasattr(it, 'to_svg')]

    def paste_items(self):
        """Pega los elementos copiados (implementación básica — pendiente serialización completa)."""
        if not self._clipboard:
            return
        offset = 18.0  # desplazamiento de 1 celda
        self.scene.clearSelection()
        new_items = []
        for src in self._clipboard:
            # Duplicar vía SVG round-trip cuando el item tiene to_svg
            try:
                import copy as _copy
                dup = _copy.copy(src)
                dup.setPos(src.pos().x() + offset, src.pos().y() + offset)
                self.scene.addItem(dup)
                dup.setSelected(True)
                new_items.append(dup)
            except Exception:
                pass
        if new_items and self.scene.undo_stack:
            from .undo_commands import AddItemsCommand
            self.scene.undo_stack.push(AddItemsCommand(self.scene, new_items))

    # ------------------------------------------------------------------ #
    # Explorador de Librería QET                                           #
    # ------------------------------------------------------------------ #

    def import_from_qet_browser(self):
        """Abre el diálogo de exploración de la librería QET y carga el .elmt seleccionado."""
        try:
            from .qet_browser_dialog import QETLibraryBrowserDialog
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el explorador QET:\n{e}")
            return
        dlg = QETLibraryBrowserDialog(self)
        if dlg.exec():
            path = dlg.get_selected_qet_path()
            if path:
                self.load_elmt_file(path)


