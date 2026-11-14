"""
Widget del editor visual interactivo SimuCraft Symbol & Terminal Studio.
"""
import copy
import os
import re
import unicodedata
from datetime import datetime, timezone
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

from .config import BASE_PATH
from .terminal_handle import TerminalHandleItem
from .canvas_scene import SymbolCanvasScene, SymbolGraphicsView
from .qet_importer import QETVectorImporter
from .standard_primitive_factory import create_standard_primitives
from .graphic_primitives import (
    clone_graphic_item,
    primitive_from_dict,
    serialize_primitives,
)
from .svg_importer import SvgVectorImporter

try:
    from src.components import symbol_registry
    from src.components.standard_components import (
        STANDARD_COMPONENTS,
        _BUILTIN_COMPONENTS,
        reload_custom_symbols,
    )
except Exception:
    symbol_registry = None
    STANDARD_COMPONENTS = {}
    _BUILTIN_COMPONENTS = set()

    def reload_custom_symbols():
        pass


CUSTOM_TAG = "CUSTOM"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "simbolo"


def _is_custom_symbol(symbol: dict) -> bool:
    if symbol_registry is not None:
        try:
            return symbol_registry.is_custom(symbol)
        except Exception:
            pass
    tags = [str(tag).upper() for tag in symbol.get("tags", [])]
    return bool(symbol.get("custom")) or symbol.get("origin") == "custom" or CUSTOM_TAG in tags

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

        btn_duplicate = QPushButton("📄 Duplicar como CUSTOM")
        btn_duplicate.setToolTip("Crea una variante CUSTOM sin modificar el símbolo actual")
        btn_duplicate.clicked.connect(self.duplicate_as_custom)
        toolbar.addWidget(btn_duplicate)
        
        btn_import_svg = QPushButton("📂 Importar SVG / .elmt")
        btn_import_svg.setToolTip("Crea un símbolo CUSTOM nuevo a partir de un SVG o .elmt")
        btn_import_svg.clicked.connect(self.import_svg_or_elmt)
        toolbar.addWidget(btn_import_svg)

        btn_browse_qet = QPushButton("📦 IMPORTAR QET")
        btn_browse_qet.setToolTip("Carga el .elmt seleccionado en el lienzo actual sin crear un CUSTOM")
        btn_browse_qet.clicked.connect(self.import_qet_into_current_canvas)
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
        self.scene.on_bounds_changed_callback = self.on_scene_bounds_changed
        
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

    def load_component_list(self, select_id: str = None):
        previous = select_id or self.comp_combo.currentData()
        self.comp_combo.blockSignals(True)
        self.comp_combo.clear()

        reload_custom_symbols()
        standard_keys = []
        custom_keys = []
        for key in sorted(STANDARD_COMPONENTS.keys()):
            symbol = STANDARD_COMPONENTS[key]
            if _is_custom_symbol(symbol):
                custom_keys.append(key)
            else:
                standard_keys.append(key)

        def add_header(text: str):
            self.comp_combo.addItem(text, None)
            index = self.comp_combo.count() - 1
            item = self.comp_combo.model().item(index)
            if item is not None:
                item.setEnabled(False)

        def add_symbol(key: str):
            symbol = STANDARD_COMPONENTS[key]
            name = symbol.get('name', '')
            if _is_custom_symbol(symbol):
                self.comp_combo.addItem(f"★ CUSTOM · {key} ({name})", key)
            else:
                self.comp_combo.addItem(f"{key} ({name})", key)

        if standard_keys:
            add_header("── Estándar ──")
            for key in standard_keys:
                add_symbol(key)
        if custom_keys:
            add_header("── CUSTOM ──")
            for key in custom_keys:
                add_symbol(key)

        keys = standard_keys + custom_keys
        target = previous if previous in keys else None
        if target is None:
            target = "motor_3p" if "motor_3p" in keys else (keys[0] if keys else None)
        if target is not None:
            index = self.comp_combo.findData(target)
            if index >= 0:
                self.comp_combo.setCurrentIndex(index)
        self.comp_combo.blockSignals(False)

        if target is not None:
            self.load_component(target)

    def on_component_selected(self, index):
        comp_key = self.comp_combo.currentData()
        if comp_key:
            self.load_component(comp_key)

    def _clear_scene_primitives(self):
        for item in list(self.scene.items()):
            if item is getattr(self.scene, "bounds_item", None):
                continue
            if not isinstance(item, TerminalHandleItem):
                self.scene.removeItem(item)

    def _load_primitives_into_scene(self, primitives) -> int:
        """Reconstruye la geometría editable guardada en ``visual.primitives``."""
        if not isinstance(primitives, list):
            return 0
        loaded = 0
        for data in primitives:
            try:
                item = primitive_from_dict(data)
            except Exception:
                item = None
            if item is not None:
                self.scene.addItem(item)
                loaded += 1
        return loaded

    def _load_svg_into_scene(self, svg_content: str) -> int:
        try:
            result = SvgVectorImporter().import_from_svg(svg_content)
        except Exception as exc:
            self.info_status.setText(f"⚠ SVG no editable: {exc}")
            return 0
        for item in result.get('items', []):
            self.scene.addItem(item)
        return len(result.get('items', []))

    def _scene_primitives(self) -> list:
        """Serializa la geometría editable actual en orden de apilado estable."""
        return serialize_primitives(self.scene.items(Qt.AscendingOrder))

    def on_scene_bounds_changed(self, width: float, height: float):
        """Sincroniza los campos de tamaño cuando se arrastra el marco."""
        self.cur_symbol.setdefault("visual", {})["width"] = float(width)
        self.cur_symbol.setdefault("visual", {})["height"] = float(height)
        for spin, value in ((self.spin_width, width), (self.spin_height, height)):
            spin.blockSignals(True)
            spin.setValue(max(20, int(round(value))))
            spin.blockSignals(False)

    def load_component(self, comp_key: str):
        if comp_key not in STANDARD_COMPONENTS:
            return

        src = STANDARD_COMPONENTS[comp_key]
        self.cur_symbol = copy.deepcopy(src)
        self._loaded_symbol_id = comp_key
        self._loaded_origin = "custom" if _is_custom_symbol(src) else "builtin"

        vis = self.cur_symbol.get('visual', {})
        w = float(vis.get('width', 90))
        h = float(vis.get('height', 72))
        ctype = self.cur_symbol.get('type', 'generic')

        # Actualizar campos. El ID de un builtin es canónico y no se renombra
        # desde el editor: para una variante se usa "Duplicar como CUSTOM".
        is_builtin = self._loaded_origin == "builtin"
        self.input_sym_id.setReadOnly(is_builtin)
        self.input_sym_id.setToolTip(
            "ID canónico del símbolo estándar. Usa 'Duplicar como CUSTOM' para una variante."
            if is_builtin else "ID del símbolo CUSTOM."
        )
        self.input_sym_id.setText(self.cur_symbol.get('id', comp_key))
        self.input_sym_name.setText(self.cur_symbol.get('name', ''))

        t_idx = self.input_sym_type.findText(ctype)
        if t_idx >= 0:
            self.input_sym_type.setCurrentIndex(t_idx)

        self.spin_width.setValue(int(w))
        self.spin_height.setValue(int(h))

        self._clear_scene_primitives()
        loaded_items = 0

        # Orden de carga: primitivas editables guardadas -> SVG canónico ->
        # .elmt -> factoría (solo builtins sin geometría registrada).
        loaded_items = self._load_primitives_into_scene(vis.get('primitives'))
        if not loaded_items:
            svg_content = vis.get('svg_content')
            if svg_content:
                loaded_items = self._load_svg_into_scene(svg_content)

        if not loaded_items:
            elmt_path = vis.get('elmt_path')
            if elmt_path and os.path.exists(elmt_path) and elmt_path.endswith('.elmt'):
                result = self._load_elmt_into_scene(elmt_path)
                loaded_items = len(result.get('items', [])) if result else 0

        if not loaded_items and self._loaded_origin == "builtin":
            for item in create_standard_primitives(comp_key, self.cur_symbol):
                self.scene.addItem(item)

        self.scene.set_component_bounds(w, h, ctype)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)
        label = "CUSTOM" if self._loaded_origin == "custom" else "Estándar"
        self.info_status.setText(
            f"Cargado: {comp_key} · {label} ({len(vis.get('terminals', []))} bornes)"
        )

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

        # Limpiar primitivas previas que no sean terminales ni el marco
        for it in list(self.scene.items()):
            if it is getattr(self.scene, "bounds_item", None):
                continue
            if not isinstance(it, TerminalHandleItem):
                self.scene.removeItem(it)

        # Añadir todos los items desglosados
        for it in result['items']:
            self.scene.addItem(it)

        return result

    def _unique_custom_id(self, base: str) -> str:
        existing = set(STANDARD_COMPONENTS.keys())
        if symbol_registry is not None:
            try:
                existing.update(symbol_registry.load_custom_symbols().keys())
            except Exception:
                pass
        candidate = base
        suffix = 2
        while candidate in existing or candidate in _BUILTIN_COMPONENTS:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    def _make_custom_symbol(
        self,
        name: str,
        width: float,
        height: float,
        terminals: list = None,
        svg_content: str = "",
        elmt_path: str = None,
        base_id: str = None,
        symbol_type: str = "generic",
        tag_prefix: str = "-K",
        logic: dict = None,
        primitives: list = None,
    ) -> dict:
        slug = _slugify(base_id or name)
        base = slug if slug.startswith("custom_") else f"custom_{slug}"
        symbol_id = self._unique_custom_id(base)
        now = _utc_now()
        return {
            "id": symbol_id,
            "origin": "custom",
            "custom": True,
            "tags": [CUSTOM_TAG],
            "type": symbol_type or "generic",
            "name": name or "Nuevo Símbolo Personalizado",
            "tag_prefix": tag_prefix or "-K",
            "visual": {
                "width": float(width),
                "height": float(height),
                "terminals": copy.deepcopy(terminals or []),
                "svg_content": svg_content or "",
                "elmt_path": elmt_path,
                "primitives": copy.deepcopy(primitives or []),
            },
            "logic": copy.deepcopy(logic) if logic else {
                "class": "AuxiliaryContact",
                "behavior": "passive",
                "internal_connections": [],
            },
            "meta": {
                "created_at": now,
                "updated_at": now,
                "schema_version": 1,
            },
        }

    def _apply_symbol_to_editor(self, symbol: dict, load_geometry: bool = True):
        self.cur_symbol = copy.deepcopy(symbol)
        self._loaded_symbol_id = self.cur_symbol.get("id")
        self._loaded_origin = "custom" if _is_custom_symbol(self.cur_symbol) else "builtin"

        vis = self.cur_symbol.setdefault("visual", {})
        w = float(vis.get("width", 90))
        h = float(vis.get("height", 72))
        ctype = self.cur_symbol.get("type", "generic")

        self.input_sym_id.setReadOnly(self._loaded_origin == "builtin")
        self.input_sym_id.setText(self.cur_symbol.get("id", ""))
        self.input_sym_name.setText(self.cur_symbol.get("name", ""))
        type_index = self.input_sym_type.findText(ctype)
        if type_index >= 0:
            self.input_sym_type.setCurrentIndex(type_index)
        else:
            self.input_sym_type.setCurrentText("generic")
        self.spin_width.setValue(max(20, int(w)))
        self.spin_height.setValue(max(20, int(h)))

        if load_geometry:
            self._clear_scene_primitives()
            loaded_items = self._load_primitives_into_scene(vis.get("primitives"))
            if not loaded_items and vis.get("svg_content"):
                loaded_items = self._load_svg_into_scene(vis["svg_content"])
            if not loaded_items:
                elmt_path = vis.get("elmt_path")
                if elmt_path and os.path.exists(elmt_path) and elmt_path.endswith(".elmt"):
                    result = self._load_elmt_into_scene(elmt_path)
                    loaded_items = len(result.get("items", [])) if result else 0
            if not loaded_items and self._loaded_origin == "builtin":
                for item in create_standard_primitives(self.cur_symbol["id"], self.cur_symbol):
                    self.scene.addItem(item)

        self.scene.set_component_bounds(w, h, ctype)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)

    def _persist_custom_and_select(self, symbol: dict) -> bool:
        if symbol_registry is None:
            QMessageBox.warning(
                self, "Error", "El registro de símbolos de SimuCraft no está disponible."
            )
            return False
        try:
            symbol_registry.save_custom_symbol(symbol)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))
            self.info_status.setText(f"⚠ No se pudo guardar el CUSTOM: {exc}")
            return False
        reload_custom_symbols()
        self.load_component_list(select_id=symbol["id"])
        return True

    def _import_elmt_as_custom(self, elmt_path: str, name: str = None) -> dict:
        result = self._load_elmt_into_scene(elmt_path)
        if result is None:
            return None

        w = max(40.0, float(result.get("width", 90)))
        h = max(40.0, float(result.get("height", 72)))
        self.scene.set_component_bounds(w, h, "generic")
        svg_content = self.scene.export_primitives_to_svg()
        new_symbol = self._make_custom_symbol(
            name=name or Path(elmt_path).stem,
            width=w,
            height=h,
            terminals=result.get("terminals", []),
            svg_content=svg_content,
            elmt_path=elmt_path,
            primitives=self._scene_primitives(),
        )
        self._apply_symbol_to_editor(new_symbol, load_geometry=False)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)
        self.info_status.setText(
            f"✔ .elmt importado como CUSTOM: {len(result.get('items', []))} elementos + "
            f"{len(result.get('terminals', []))} bornes"
        )
        return new_symbol

    def load_elmt_file(self, elmt_path: str, sym_id: str = '', sym_name: str = ''):
        """Importa un .elmt como un símbolo CUSTOM nuevo, sin pisar el actual."""
        new_symbol = self._import_elmt_as_custom(
            elmt_path, name=sym_name or Path(elmt_path).stem
        )
        if new_symbol is None:
            return
        self._persist_custom_and_select(new_symbol)

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
            new_symbol = self._import_elmt_as_custom(file_path)
            if new_symbol is None:
                return
            if self._persist_custom_and_select(new_symbol):
                QMessageBox.information(
                    self, "Importado con Éxito",
                    f"El archivo QET se ha añadido como CUSTOM '{new_symbol['id']}'.\n"
                    "El símbolo que estaba editando no se ha modificado.",
                )
            return

        if not file_path.endswith('.svg'):
            return

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as handle:
            svg_code = handle.read()

        try:
            parsed = SvgVectorImporter().import_from_svg(svg_code)
        except Exception:
            parsed = {"width": 90.0, "height": 72.0, "items": []}

        self._clear_scene_primitives()
        for item in parsed.get("items", []):
            self.scene.addItem(item)
        w = max(40.0, float(parsed.get("width", 90)))
        h = max(40.0, float(parsed.get("height", 72)))
        self.scene.set_component_bounds(w, h, "generic")

        new_symbol = self._make_custom_symbol(
            name=Path(file_path).stem,
            width=w,
            height=h,
            terminals=[],
            svg_content=svg_code,
            elmt_path=file_path,
            primitives=self._scene_primitives(),
        )
        self._apply_symbol_to_editor(new_symbol, load_geometry=False)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(w, h)
        if self._persist_custom_and_select(new_symbol):
            QMessageBox.information(
                self, "Importado con Éxito",
                f"El SVG se ha añadido como CUSTOM '{new_symbol['id']}'.\n"
                "El símbolo que estaba editando no se ha modificado.",
            )

    def new_custom_symbol(
        self,
        checked=False,
        base_id: str = None,
        name: str = None,
        width: float = 90.0,
        height: float = 72.0,
        terminals: list = None,
        symbol_type: str = "generic",
    ):
        self._clear_scene_primitives()
        width = max(20.0, float(width))
        height = max(20.0, float(height))
        if terminals is None:
            terminals = [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": height, "orientation": "s", "type": "contact"},
            ]
        new_symbol = self._make_custom_symbol(
            name=name or "Nuevo Símbolo Personalizado",
            width=width,
            height=height,
            terminals=terminals,
            svg_content="",
            base_id=base_id,
            symbol_type=symbol_type,
        )
        self._apply_symbol_to_editor(new_symbol, load_geometry=False)
        self.scene.set_component_bounds(width, height, symbol_type)
        self.refresh_terminal_items()
        self._fit_view_to_symbol(width, height)
        self.info_status.setText(
            f"Nuevo CUSTOM '{new_symbol['id']}' sin guardar. Pulsa 'Guardar en SimuCraft'."
        )

    def duplicate_as_custom(self, checked=False):
        if not self.cur_symbol:
            self.new_custom_symbol()
            return
        duplicate = copy.deepcopy(self.cur_symbol)
        source_name = duplicate.get("name") or duplicate.get("id") or "simbolo"
        duplicate = self._make_custom_symbol(
            name=f"Copia de {source_name}",
            width=float(duplicate.get("visual", {}).get("width", 90)),
            height=float(duplicate.get("visual", {}).get("height", 72)),
            terminals=duplicate.get("visual", {}).get("terminals", []),
            svg_content=duplicate.get("visual", {}).get("svg_content", ""),
            elmt_path=duplicate.get("visual", {}).get("elmt_path"),
            base_id=f"{duplicate.get('id', 'simbolo')}_copia",
            symbol_type=duplicate.get("type", "generic"),
            tag_prefix=duplicate.get("tag_prefix", "-K"),
            logic=duplicate.get("logic"),
            primitives=self._scene_primitives(),
        )
        # La escena actual ya contiene la geometría que se está duplicando.
        self._apply_symbol_to_editor(duplicate, load_geometry=False)
        self.refresh_terminal_items()
        self.info_status.setText(
            f"Variante CUSTOM '{duplicate['id']}' creada sin guardar. "
            "El símbolo original no se modificará."
        )

    def save_symbol_to_simucraft(self):
        if not self.cur_symbol:
            QMessageBox.warning(self, "Error", "No hay ningún símbolo cargado.")
            return

        symbol = copy.deepcopy(self.cur_symbol)
        sym_id = self.input_sym_id.text().strip()
        if not sym_id:
            QMessageBox.warning(self, "Error", "El símbolo debe tener un ID válido.")
            return

        origin = getattr(self, "_loaded_origin", None)
        if origin not in {"builtin", "custom"}:
            origin = "custom" if _is_custom_symbol(symbol) else "builtin"

        if origin == "builtin":
            loaded_id = getattr(self, "_loaded_symbol_id", None) or symbol.get("id")
            if sym_id != loaded_id:
                QMessageBox.warning(
                    self, "ID de símbolo estándar",
                    "El ID de un símbolo estándar no se puede cambiar.\n"
                    "Usa 'Duplicar como CUSTOM' para crear una variante.",
                )
                self.input_sym_id.setText(loaded_id or sym_id)
                return
            if _is_custom_symbol(symbol):
                QMessageBox.warning(
                    self, "Símbolo estándar inválido",
                    "Un símbolo estándar no puede tener custom=True ni la etiqueta CUSTOM.",
                )
                return
            symbol["id"] = loaded_id
            symbol["origin"] = "builtin"
            symbol.pop("custom", None)
            tags = [tag for tag in symbol.get("tags", []) if str(tag).upper() != CUSTOM_TAG]
            if tags:
                symbol["tags"] = tags
            else:
                symbol.pop("tags", None)
        else:
            # Un CUSTOM existente (incluidos los legados tipo ``cad_0``) se
            # sobrescribe con su ID real. Solo se genera ``custom_*`` cuando
            # el usuario cambia el ID o crea un símbolo nuevo.
            loaded_id = getattr(self, "_loaded_symbol_id", None)
            keep_loaded_id = (
                loaded_id
                and sym_id == loaded_id
                and loaded_id in STANDARD_COMPONENTS
                and _is_custom_symbol(STANDARD_COMPONENTS[loaded_id])
            )
            if not keep_loaded_id and not sym_id.startswith("custom_"):
                sym_id = self._unique_custom_id(f"custom_{_slugify(sym_id)}")
                self.input_sym_id.setText(sym_id)
            symbol["id"] = sym_id
            symbol["origin"] = "custom"
            symbol["custom"] = True
            tags = [str(tag) for tag in symbol.get("tags", []) if str(tag).strip()]
            if not any(tag.upper() == CUSTOM_TAG for tag in tags):
                tags.append(CUSTOM_TAG)
            symbol["tags"] = tags

        symbol["name"] = self.input_sym_name.text().strip() or symbol.get("name", sym_id)
        symbol["type"] = self.input_sym_type.currentText() or symbol.get("type", "generic")
        visual = symbol.setdefault("visual", {})
        visual["width"] = float(self.spin_width.value())
        visual["height"] = float(self.spin_height.value())
        visual["primitives"] = self._scene_primitives()
        visual["svg_content"] = self.scene.export_primitives_to_svg()

        meta = symbol.setdefault("meta", {})
        meta.setdefault("created_at", _utc_now())
        meta["updated_at"] = _utc_now()
        meta["schema_version"] = 1

        if symbol_registry is None:
            QMessageBox.warning(
                self, "Error", "El registro de símbolos de SimuCraft no está disponible."
            )
            return

        try:
            if origin == "builtin":
                symbol_registry.save_standard_symbol(symbol)
            else:
                symbol_registry.save_custom_symbol(symbol)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))
            self.info_status.setText(f"⚠ No se pudo guardar '{sym_id}': {exc}")
            return

        reload_custom_symbols()
        self.load_component_list(select_id=sym_id)
        if origin == "builtin":
            message = (
                f"El símbolo estándar '{sym_id}' se ha sobrescrito en "
                "data/symbols/standard_symbols.json.\n\n"
                "Reinicia SimuCraft para ver la edición."
            )
        else:
            message = (
                f"El símbolo CUSTOM '{sym_id}' se ha guardado en "
                "data/symbols/custom_symbols.json.\n\n"
                "Reinicia SimuCraft para verlo en la biblioteca."
            )
        QMessageBox.information(self, "Guardado con Éxito", message)
        self.info_status.setText(f"✔ Guardado: {sym_id} ({origin})")

    # ------------------------------------------------------------------ #
    # Clipboard                                                            #
    # ------------------------------------------------------------------ #

    def copy_selected(self):
        """Copia los elementos seleccionados al portapapeles interno."""
        self._clipboard = [it for it in self.scene.selectedItems() if hasattr(it, 'to_svg')]

    def paste_items(self):
        """Pega los elementos copiados desplazándolos una celda de rejilla."""
        if not self._clipboard:
            return
        offset = (18.0, 18.0)
        self.scene.clearSelection()
        new_items = []
        for src in self._clipboard:
            duplicate = clone_graphic_item(src, offset=offset)
            if duplicate is None:
                continue
            self.scene.addItem(duplicate)
            duplicate.setSelected(True)
            new_items.append(duplicate)
        if new_items and self.scene.undo_stack:
            from .undo_commands import AddItemsCommand
            self.scene.undo_stack.push(AddItemsCommand(self.scene, new_items))

    # ------------------------------------------------------------------ #
    # Explorador de Librería QET                                           #
    # ------------------------------------------------------------------ #

    def load_elmt_into_current(self, elmt_path: str):
        """Carga un .elmt en el lienzo del símbolo actual sin crear un CUSTOM.

        Se conserva el ID/nombre/tipo del símbolo abierto; solo se sustituyen
        la geometría, los bornes y el tamaño del canvas.
        """
        result = self._load_elmt_into_scene(elmt_path)
        if result is None:
            return None

        width = max(20.0, float(result.get('width', 90)))
        height = max(20.0, float(result.get('height', 72)))
        terminals = copy.deepcopy(result.get('terminals', []))

        visual = self.cur_symbol.setdefault('visual', {})
        visual['width'] = width
        visual['height'] = height
        visual['terminals'] = terminals
        visual['elmt_path'] = elmt_path

        for spin, value in ((self.spin_width, width), (self.spin_height, height)):
            spin.blockSignals(True)
            spin.setValue(max(20, int(round(value))))
            spin.blockSignals(False)

        self.scene.set_component_bounds(
            width, height, self.cur_symbol.get('type', 'generic')
        )
        self.refresh_terminal_items()
        self._fit_view_to_symbol(width, height)
        self.info_status.setText(
            f"✔ QET importado al lienzo actual: {len(result.get('items', []))} elementos + "
            f"{len(terminals)} bornes ({int(width)}x{int(height)} px)"
        )
        return result

    def import_qet_into_current_canvas(self):
        """Abre el explorador QET y carga el .elmt en el lienzo actual."""
        try:
            from .qet_browser_dialog import QETLibraryBrowserDialog
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el explorador QET:\n{e}")
            return
        dlg = QETLibraryBrowserDialog(self)
        if dlg.exec():
            path = dlg.get_selected_qet_path()
            if path:
                self.load_elmt_into_current(path)

    def import_from_qet_browser(self):
        """Alias compatible: el QET se importa en el lienzo actual."""
        self.import_qet_into_current_canvas()


