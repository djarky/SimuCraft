#!/usr/bin/env python3
"""
cadesimu_mapper_fixed.py
Suite integrada de ingeniería para SimuCraft:
1. Mapeador CADe SIMU -> QElectroTech / SimuCraft (Catálogo Maestro REA con 343 símbolos)
2. SimuCraft Symbol & Terminal Studio (Editor visual interactivo de símbolos y bornes)
"""
import json
import csv
import os
import re
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QSplitter,
    QLineEdit, QGroupBox, QMessageBox, QFileDialog, QScrollArea,
    QTabWidget, QGridLayout, QComboBox, QTextEdit, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QSpinBox, QFormLayout
)
from PySide6.QtCore import Qt, QSize, QPointF, QRectF, QByteArray, QRect
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QFont, QPolygonF,
    QPainterPath, QImage
)
from PySide6.QtSvg import QSvgRenderer

BASE = Path('/home/vibecode/DevS/SimuCraft')
sys.path.insert(0, str(BASE))

try:
    from src.qet.parser import QETParser
    PARSER = QETParser()
    USE_P = True
except Exception:
    PARSER = None
    USE_P = False

try:
    from src.components.standard_components import STANDARD_COMPONENTS, reload_custom_symbols
except Exception:
    STANDARD_COMPONENTS = {}
    def reload_custom_symbols():
        pass


# ==============================================================================
# 1. ELEMENTO GRÁFICO INTERACTIVO DE BORNE / TERMINAL
# ==============================================================================

class TerminalHandleItem(QGraphicsItem):
    """Pin o Borne interactivo arrastrable con encaje en rejilla y orientación."""
    
    TYPE_COLORS = {
        'motor_in': QColor('#e67e22'),   # Naranja
        'power_in': QColor('#e74c3c'),   # Rojo
        'neutral':  QColor('#3498db'),   # Azul
        'earth':    QColor('#2ecc71'),   # Verde
        'contact':  QColor('#9b59b6'),   # Púrpura
        'coil_in':  QColor('#00bcd4'),   # Cian
        'coil_out': QColor('#0097a7'),   # Cian oscuro
        'lamp_in':  QColor('#f1c40f'),   # Amarillo
        'lamp_out': QColor('#f39c12'),   # Ámbar
        'generic':  QColor('#bdc3c7')    # Gris
    }

    def __init__(self, term_data: dict, on_change_callback, grid_snap: int = 18):
        super().__init__()
        self.term_data = term_data
        self.callback = on_change_callback
        self.grid_snap = grid_snap
        
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(100)
        self.setPos(float(term_data.get('x', 0)), float(term_data.get('y', 0)))

    def boundingRect(self) -> QRectF:
        return QRectF(-18, -18, 56, 36)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        ttype = self.term_data.get('type', 'generic')
        color = self.TYPE_COLORS.get(ttype, QColor('#bdc3c7'))
        
        # Halo de selección
        if self.isSelected():
            painter.setPen(QPen(QColor('#00e5ff'), 2.5, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 229, 255, 40)))
            painter.drawEllipse(QPointF(0, 0), 12, 12)
            
        # Círculo del borne
        painter.setPen(QPen(Qt.white, 1.8))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(0, 0), 6, 6)
        
        # Flecha de orientación (N, S, E, W)
        orient = self.term_data.get('orientation', 'n').lower()
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(QBrush(Qt.white))
        arrow = QPolygonF()
        if orient == 'n':
            arrow.append(QPointF(0, -12))
            arrow.append(QPointF(-3, -7))
            arrow.append(QPointF(3, -7))
        elif orient == 's':
            arrow.append(QPointF(0, 12))
            arrow.append(QPointF(-3, 7))
            arrow.append(QPointF(3, 7))
        elif orient == 'e':
            arrow.append(QPointF(12, 0))
            arrow.append(QPointF(7, -3))
            arrow.append(QPointF(7, 3))
        elif orient == 'w':
            arrow.append(QPointF(-12, 0))
            arrow.append(QPointF(-7, -3))
            arrow.append(QPointF(-7, 3))
        if not arrow.isEmpty():
            painter.drawPolygon(arrow)
            
        # Etiqueta de texto (ID o nombre del borne)
        name = self.term_data.get('name') or self.term_data.get('id', '')
        painter.setPen(QPen(QColor('#ffffff')))
        font = QFont("Sans Serif", 7, QFont.Bold)
        painter.setFont(font)
        
        # Pequeña placa de fondo para legibilidad
        painter.setBrush(QBrush(QColor(20, 24, 30, 200)))
        painter.setPen(QPen(QColor(80, 90, 100), 1))
        painter.drawRoundedRect(8, -8, 26, 15, 3, 3)
        painter.setPen(QPen(Qt.white))
        painter.drawText(11, 3, name[:4])

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            snap = self.grid_snap
            if snap > 1:
                sx = round(new_pos.x() / snap) * snap
                sy = round(new_pos.y() / snap) * snap
                new_pos = QPointF(sx, sy)
            self.term_data['x'] = new_pos.x()
            self.term_data['y'] = new_pos.y()
            if self.callback:
                self.callback(self)
            return new_pos
        return super().itemChange(change, value)


# ==============================================================================
# 2. LIENZO GRÁFICO DEL EDITOR DE SÍMBOLOS
# ==============================================================================

class SymbolCanvasScene(QGraphicsScene):
    """Escena con cuadrícula eléctrica CADe SIMU (paso 6px y 18px) y caja de componente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-150, -150, 600, 600)
        self.comp_width = 90.0
        self.comp_height = 72.0
        self.svg_renderer = None
        self.comp_type = 'generic'
        self.grid_snap = 18

    def set_component_bounds(self, width: float, height: float, comp_type: str = 'generic', svg_renderer=None):
        self.comp_width = width
        self.comp_height = height
        self.comp_type = comp_type
        self.svg_renderer = svg_renderer
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Fondo oscuro técnico
        painter.fillRect(rect, QColor("#181a20"))
        
        # Rejilla fina (6px)
        painter.setPen(QPen(QColor("#222630"), 1))
        left = int(rect.left()) - (int(rect.left()) % 6)
        top = int(rect.top()) - (int(rect.top()) % 6)
        
        lines_6 = []
        for x in range(left, int(rect.right()), 6):
            if x % 18 != 0:
                lines_6.append(QPointF(x, rect.top()))
                lines_6.append(QPointF(x, rect.bottom()))
        for y in range(top, int(rect.bottom()), 6):
            if y % 18 != 0:
                lines_6.append(QPointF(rect.left(), y))
                lines_6.append(QPointF(rect.right(), y))
        if lines_6:
            painter.drawLines(lines_6)
            
        # Rejilla mayor (18px) - estándar de CADe SIMU
        painter.setPen(QPen(QColor("#2d3340"), 1.2))
        lines_18 = []
        left_18 = int(rect.left()) - (int(rect.left()) % 18)
        top_18 = int(rect.top()) - (int(rect.top()) % 18)
        for x in range(left_18, int(rect.right()), 18):
            lines_18.append(QPointF(x, rect.top()))
            lines_18.append(QPointF(x, rect.bottom()))
        for y in range(top_18, int(rect.bottom()), 18):
            lines_18.append(QPointF(rect.left(), y))
            lines_18.append(QPointF(rect.right(), y))
        if lines_18:
            painter.drawLines(lines_18)

        # Ejes de origen (0, 0)
        painter.setPen(QPen(QColor("#e74c3c"), 1.5, Qt.DashLine))
        painter.drawLine(0, int(rect.top()), 0, int(rect.bottom()))
        painter.drawLine(int(rect.left()), 0, int(rect.right()), 0)
        painter.setPen(QPen(QColor("#e74c3c")))
        painter.setFont(QFont("Sans Serif", 7, QFont.Bold))
        painter.drawText(4, -4, "(0,0) Origen")

        # -------------------------------------------------------------
        # Dibujar silueta o SVG del componente en el fondo
        # -------------------------------------------------------------
        comp_rect = QRectF(0, 0, self.comp_width, self.comp_height)
        
        # Caja exterior delimitadora del componente
        painter.setPen(QPen(QColor("#4a90e2"), 1.5, Qt.DashLine))
        painter.setBrush(QBrush(QColor(74, 144, 226, 18)))
        painter.drawRect(comp_rect)

        # Renderizar SVG si existe
        if self.svg_renderer and self.svg_renderer.isValid():
            self.svg_renderer.render(painter, comp_rect)
        else:
            # Dibujo esquemático indicativo según tipo
            painter.setPen(QPen(QColor("#a0b0c0"), 1.8))
            mid_y = self.comp_height / 2.0
            mid_x = self.comp_width / 2.0
            if 'motor' in self.comp_type:
                rad = min(mid_x, mid_y) - 6
                painter.setBrush(QBrush(QColor("#253040")))
                painter.drawEllipse(QPointF(mid_x, mid_y), rad, rad)
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Arial", 14, QFont.Bold))
                painter.drawText(int(mid_x - 7), int(mid_y + 5), "M")
            elif 'contactor' in self.comp_type:
                painter.setBrush(QBrush(QColor("#253040")))
                painter.drawRoundedRect(comp_rect.adjusted(6, 6, -6, -6), 4, 4)
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
                painter.drawText(int(mid_x - 12), int(mid_y + 4), "KM")
            elif 'breaker' in self.comp_type:
                painter.setBrush(QBrush(QColor("#2d3340")))
                painter.drawRect(comp_rect.adjusted(4, 4, -4, -4))
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
                painter.drawText(int(mid_x - 6), int(mid_y + 4), "Q")


# ==============================================================================
# 3. PESTAÑA: SIMUCRAFT SYMBOL & TERMINAL STUDIO
# ==============================================================================

class SymbolEditorWidget(QWidget):
    """Editor interactivo visual de símbolos y posiciones de bornes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cur_symbol = {}
        self.terminal_items = []
        self.selected_item = None
        self.svg_renderer = None
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
        canvas_box = QGroupBox("Lienzo Interactivo (Arrastra los bornes con el ratón)")
        canvas_layout = QVBoxLayout(canvas_box)
        
        self.scene = SymbolCanvasScene(self)
        self.scene.selectionChanged.connect(self.on_scene_selection_changed)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        canvas_layout.addWidget(self.view)
        
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

        # Cargar SVG si tiene
        self.svg_renderer = None
        svg_content = vis.get('svg_content')
        if not svg_content and vis.get('elmt_path') and os.path.exists(vis.get('elmt_path')) and PARSER:
            svg_content = PARSER.elmt_to_svg(vis.get('elmt_path'))
            vis['svg_content'] = svg_content
        if svg_content:
            data = QByteArray(svg_content.encode('utf-8'))
            rend = QSvgRenderer(data)
            if rend.isValid():
                self.svg_renderer = rend

        self.scene.set_component_bounds(w, h, ctype, self.svg_renderer)
        self.refresh_terminal_items()
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
        self.scene.set_component_bounds(w, h, self.input_sym_type.currentText(), self.svg_renderer)

    def on_sym_type_changed(self, text):
        self.cur_symbol['type'] = text
        self.scene.set_component_bounds(
            float(self.spin_width.value()),
            float(self.spin_height.value()),
            text,
            self.svg_renderer
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

    def import_svg_or_elmt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Gráfico de Símbolo", str(BASE), "Archivos Símbolo (*.elmt *.svg)"
        )
        if not file_path:
            return
        svg_code = ""
        if file_path.endswith('.elmt') and PARSER:
            parsed = PARSER.parse_symbol(file_path)
            svg_code = parsed.get('svg_content', '')
            if parsed.get('terminals'):
                reply = QMessageBox.question(
                    self, "Importar Bornes",
                    f"El archivo contiene {len(parsed['terminals'])} bornes definidos.\n¿Deseas reemplazar los bornes actuales por los del archivo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.cur_symbol.setdefault('visual', {})['terminals'] = parsed['terminals']
            w = parsed.get('width', 90)
            h = parsed.get('height', 72)
            self.spin_width.setValue(int(w))
            self.spin_height.setValue(int(h))
        elif file_path.endswith('.svg'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                svg_code = f.read()

        if svg_code:
            self.cur_symbol.setdefault('visual', {})['svg_content'] = svg_code
            self.cur_symbol['visual']['elmt_path'] = file_path
            data = QByteArray(svg_code.encode('utf-8'))
            self.svg_renderer = QSvgRenderer(data)
            self.scene.set_component_bounds(
                float(self.spin_width.value()),
                float(self.spin_height.value()),
                self.input_sym_type.currentText(),
                self.svg_renderer
            )
            self.refresh_terminal_items()
            QMessageBox.information(self, "Importado", f"Gráfico vectorial cargado correctamente desde:\n{file_path}")

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
        self.scene.set_component_bounds(90, 72, "generic", None)
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
        
        # Archivo de destino en data/
        custom_file = BASE / "data" / "custom_symbols.json"
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


# ==============================================================================
# 4. WIDGET TILESET CON TOOLTIPS Y OVERLAY (reemplaza QLabel simple)
# ==============================================================================

class TileSheetLabel(QLabel):
    """
    Muestra un tileset de CADe SIMU escalado 2x con:
    - Overlay verde semitransparente en tiles ya mapeados
    - Tooltip en hover mostrando CAD_ID, nombre y categoría
    - Callback al hacer clic en un tile
    """
    TILE_SIZE = 24   # Tamaño original de cada tile en px
    SCALE     = 2    # Factor de escala para visualización

    def __init__(self, img_path: str, bmp_id, tile_to_cad: dict, mapping: dict,
                 on_tile_selected=None, parent=None):
        super().__init__(parent)
        self.img_path       = img_path
        self.bmp_id         = bmp_id
        self.tile_to_cad    = tile_to_cad
        self.mapping        = mapping
        self.on_tile_selected = on_tile_selected
        self.hovered_tile   = None   # (row, col) del tile bajo el cursor
        self.selected_tile  = None   # (row, col) del tile seleccionado

        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        # Cargar imagen base
        self._base_pix = QPixmap(img_path)
        self._render()

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render(self):
        """Re-renderiza el QLabel con overlays actualizados."""
        if self._base_pix.isNull():
            return
        ts   = self.TILE_SIZE
        sc   = self.SCALE
        disp = self._base_pix.scaled(
            self._base_pix.width() * sc,
            self._base_pix.height() * sc,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        ).copy()

        if self.bmp_id is not None:
            painter = QPainter(disp)
            painter.setRenderHint(QPainter.Antialiasing, False)

            # --- Overlay por cada tile del mapa ---
            ts_sc = ts * sc
            for key, info in self.tile_to_cad.items():
                if not key.startswith(f"{self.bmp_id}_"):
                    continue
                row = info.get('row', 0)
                col = info.get('col', 0)
                cad_id = info.get('cad_id')
                rx = col * ts_sc
                ry = row * ts_sc

                # Verde = ya mapeado
                map_key = f"CAD:{cad_id}" if cad_id is not None else None
                is_mapped = map_key and (map_key in self.mapping or str(cad_id) in self.mapping)
                if is_mapped:
                    painter.fillRect(rx, ry, ts_sc, ts_sc, QColor(0, 200, 80, 80))
                    painter.setPen(QPen(QColor(0, 230, 80, 180), 1))
                    painter.drawRect(rx, ry, ts_sc - 1, ts_sc - 1)

            # --- Tile hover (amarillo) ---
            if self.hovered_tile:
                hr, hc = self.hovered_tile
                painter.fillRect(hc * ts_sc, hr * ts_sc, ts_sc, ts_sc, QColor(255, 200, 0, 60))
                painter.setPen(QPen(QColor(255, 200, 0, 220), 1))
                painter.drawRect(hc * ts_sc, hr * ts_sc, ts_sc - 1, ts_sc - 1)

            # --- Tile seleccionado (cian) ---
            if self.selected_tile:
                sr, sc2 = self.selected_tile
                painter.fillRect(sc2 * ts_sc, sr * ts_sc, ts_sc, ts_sc, QColor(0, 220, 255, 70))
                painter.setPen(QPen(QColor(0, 220, 255), 2))
                painter.drawRect(sc2 * ts_sc, sr * ts_sc, ts_sc - 1, ts_sc - 1)

            painter.end()

        self.setPixmap(disp)
        self.resize(disp.size())

    # ── Eventos de ratón ─────────────────────────────────────────────────────

    def _tile_at(self, event_pos):
        ts_sc = self.TILE_SIZE * self.SCALE
        x = int(event_pos.x())
        y = int(event_pos.y())
        row = y // ts_sc
        col = x // ts_sc
        return row, col

    def _get_tile_info(self, row, col):
        if self.bmp_id is None:
            return {}
        key = f"{self.bmp_id}_{row:02d}_{col:02d}"
        return self.tile_to_cad.get(key, {})

    def mouseMoveEvent(self, event):
        row, col = self._tile_at(event.position())
        if (row, col) != self.hovered_tile:
            self.hovered_tile = (row, col)
            self._render()
            # Tooltip
            info = self._get_tile_info(row, col)
            if info:
                cad_id = info.get('cad_id', '?')
                name   = info.get('name', '') or '—'
                cat    = info.get('category', '')
                tags   = info.get('tags', '')
                from PySide6.QtWidgets import QToolTip
                from PySide6.QtCore import QPoint
                tip = f"<b>CAD_ID: {cad_id}</b><br>{name}<br><i>{cat}</i>"
                if tags:
                    tip += f"<br><small>{tags}</small>"
                QToolTip.showText(self.mapToGlobal(QPoint(int(event.position().x()), int(event.position().y()))), tip, self)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            row, col = self._tile_at(event.position())
            self.selected_tile = (row, col)
            self._render()
            info = self._get_tile_info(row, col)
            if self.on_tile_selected:
                self.on_tile_selected(self.img_path, self.bmp_id, row, col, info)
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.hovered_tile = None
        self._render()
        super().leaveEvent(event)


# ==============================================================================
# 5. VENTANA PRINCIPAL CON PESTAÑAS (MAPPER + SYMBOL STUDIO)
# ==============================================================================

class CADeSimuMapperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CADe SIMU Mapper & Symbol Studio 2.0 - SimuCraft')
        self.resize(1650, 980)
        
        self.cur_key = None
        self.cur_item = None
        self.sel_tile = None
        
        self.load_catalogs()
        self.init_ui()
        
    def load_catalogs(self):
        # 1. Catálogo REA
        self.cad_symbols = []
        self.cad_symbols_by_id = {}
        catalog_path = BASE / 'data' / 'catalogs' / 'cadesimu_symbols_complete.json'
        if not catalog_path.exists():
            catalog_path = BASE / 'cadesimu_symbols_complete.json'
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.cad_symbols = json.load(f)
                for s in self.cad_symbols:
                    self.cad_symbols_by_id[str(s['CAD_ID'])] = s

        # 2. Catálogo QET
        self.qet = []
        qet_catalog = BASE / 'data' / 'catalogs' / 'qet_symbols_catalog.csv'
        if not qet_catalog.exists():
            qet_catalog = BASE / 'qet_symbols_catalog.csv'
        if qet_catalog.exists():
            with open(qet_catalog, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    if r.get('Filename'):
                        self.qet.append(r)

        # 3. Mapeos existentes
        self.map = {}
        mapping_path = BASE / 'data' / 'mappings' / 'symbol_mapping_manual.json'
        if not mapping_path.exists():
            mapping_path = BASE / 'symbol_mapping_manual.json'
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    self.map = json.load(f)
            except Exception:
                self.map = {}

        # 4. Mapa tile → CAD_ID (generado por build_tile_map.py)
        self.tile_to_cad = {}
        tile_map_path = BASE / 'data' / 'mappings' / 'tile_to_cad_id.json'
        if tile_map_path.exists():
            try:
                with open(tile_map_path, 'r', encoding='utf-8') as f:
                    self.tile_to_cad = json.load(f)
            except Exception:
                self.tile_to_cad = {}

        # 5. Dispatch table CAD_ID → componente SimuCraft
        self.dispatch_table = {}
        dispatch_path = BASE / 'data' / 'mappings' / 'cad_id_to_component.json'
        if dispatch_path.exists():
            try:
                with open(dispatch_path, 'r', encoding='utf-8') as f:
                    self.dispatch_table = json.load(f)
            except Exception:
                self.dispatch_table = {}
                
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Header banner
        header = QLabel(f"⚡ CADe SIMU Mapper & Symbol Studio 2.0 | Catálogo REA: {len(self.cad_symbols)} símbolos | QET: {len(self.qet)} elementos | SimuCraft Native")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #1a1e24; color: #4af626; border-radius: 4px;")
        main_layout.addWidget(header)
        
        # Tabs de Navegación
        self.main_tabs = QTabWidget()
        
        # ----------------- TAB 1: MAPPER (CATÁLOGO REA <-> QET) -----------------
        mapper_tab = QWidget()
        mapper_layout = QVBoxLayout(mapper_tab)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel Izquierdo: Símbolos CAD
        left_box = QGroupBox(f"Símbolos CADe SIMU ({len(self.cad_symbols)})")
        left_layout = QVBoxLayout(left_box)
        
        filter_layout = QHBoxLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("Todas las categorías")
        categories = sorted(list(set(s.get('Categoria', 'Otros') for s in self.cad_symbols)))
        for cat in categories:
            self.cat_combo.addItem(cat)
        self.cat_combo.currentTextChanged.connect(self.filter_cad_list)
        filter_layout.addWidget(self.cat_combo)
        
        self.cad_search = QLineEdit()
        self.cad_search.setPlaceholderText("Buscar ID o nombre...")
        self.cad_search.textChanged.connect(self.filter_cad_list)
        filter_layout.addWidget(self.cad_search)
        left_layout.addLayout(filter_layout)
        
        self.cad_list = QListWidget()
        self.cad_list.itemClicked.connect(self.on_cad_selected)
        left_layout.addWidget(self.cad_list)
        
        self.cad_info = QTextEdit()
        self.cad_info.setReadOnly(True)
        self.cad_info.setFixedHeight(120)
        self.cad_info.setStyleSheet("background: #252830; color: #eee; font-family: monospace; font-size: 12px; border: 1px solid #444;")
        left_layout.addWidget(self.cad_info)
        splitter.addWidget(left_box)
        
        # Panel Central: Bitmaps Originales (con tooltips y overlay)
        center_box = QGroupBox("Iconos & Bitmaps Originales (CADe SIMU) — Hover para ver ID, Clic para seleccionar")
        center_layout = QVBoxLayout(center_box)
        self.bmp_tabs = QTabWidget()
        # Bitmaps de símbolo disponibles (259 y 262 tienen tiles catalogados)
        bmp_entries = [
            ('bitmap_259.png', 259, 'Contactos / Bobinas / Accionamientos / Protecciones'),
            ('bitmap_262.png', 262, 'Motores / Contactores / Alimentaciones / Detectores'),
            ('bitmap_263.png', None, 'Símbolos 2D adicionales'),
            ('bitmap_265.png', None, 'Sensores / Detectores extra'),
            ('bitmap_266.png', None, 'PLC / Neumática / GRAFCET'),
        ]
        for bmp_name, bmp_id, bmp_desc in bmp_entries:
            p = BASE / 'cadesimu' / 'bmp_extract' / 'cadesimu_all_bmps' / bmp_name
            if not p.exists():
                p = BASE / 'cadesimu_all_bmps' / bmp_name
            if p.exists():
                scroll = QScrollArea()
                scroll.setWidgetResizable(False)
                tile_lbl = TileSheetLabel(
                    str(p), bmp_id, self.tile_to_cad, self.map,
                    on_tile_selected=self.on_tile_selected_from_sheet
                )
                scroll.setWidget(tile_lbl)
                tab_name = bmp_name.replace('.png', '')
                self.bmp_tabs.addTab(scroll, tab_name)
        center_layout.addWidget(self.bmp_tabs)
        self.tile_label = QLabel("Tile seleccionado: Ninguno — Mueve el mouse sobre los tiles para ver su ID")
        self.tile_label.setStyleSheet("font-weight: bold; color: #ffca28; padding: 4px; background: #1a1e24; border-radius: 3px;")
        center_layout.addWidget(self.tile_label)
        splitter.addWidget(center_box)
        
        # Panel Derecho: QElectroTech
        right_box = QGroupBox("Elementos QElectroTech (.elmt)")
        right_layout = QVBoxLayout(right_box)
        
        self.qet_search = QLineEdit()
        self.qet_search.setPlaceholderText("Filtrar elementos QET...")
        self.qet_search.textChanged.connect(self.filter_qet_list)
        right_layout.addWidget(self.qet_search)
        
        self.qet_list = QListWidget()
        self.qet_list.itemClicked.connect(self.preview_qet)
        self.qet_list.itemDoubleClicked.connect(self.assign_mapping)
        right_layout.addWidget(self.qet_list)
        
        self.preview_label = QLabel("Vista previa SVG")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedHeight(230)
        self.preview_label.setStyleSheet("background: white; border: 2px solid #555; border-radius: 4px;")
        right_layout.addWidget(self.preview_label)
        
        btn_bar = QHBoxLayout()
        btn_assign = QPushButton("✔ Asignar Mapeo")
        btn_assign.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 7px;")
        btn_assign.clicked.connect(self.assign_current_mapping)
        
        btn_edit_studio = QPushButton("🎨 Abrir en Symbol Studio")
        btn_edit_studio.setStyleSheet("background: #1976d2; color: white; font-weight: bold; padding: 7px;")
        btn_edit_studio.clicked.connect(self.open_current_in_studio)
        
        btn_save = QPushButton("💾 Guardar Mapeo")
        btn_save.clicked.connect(self.save_mapping)
        
        btn_export = QPushButton("📤 Exportar CSV")
        btn_export.clicked.connect(self.export_csv)
        
        btn_bar.addWidget(btn_assign)
        btn_bar.addWidget(btn_edit_studio)
        btn_bar.addWidget(btn_save)
        btn_bar.addWidget(btn_export)
        right_layout.addLayout(btn_bar)
        
        splitter.addWidget(right_box)
        splitter.setSizes([450, 580, 570])
        mapper_layout.addWidget(splitter)
        
        self.main_tabs.addTab(mapper_tab, "⚡ 1. Catálogo & Mapeador CADe SIMU ↔ QET")

        # ----------------- TAB 2: SYMBOL & TERMINAL STUDIO -----------------
        self.studio_tab = SymbolEditorWidget(self)
        self.main_tabs.addTab(self.studio_tab, "🎨 2. SimuCraft Symbol & Terminal Studio (Editor)")

        main_layout.addWidget(self.main_tabs)
        self.populate_cad_list()

    # ---------------- Métodos del Mapper ----------------

    def populate_cad_list(self):
        self.cad_list.clear()
        query = self.cad_search.text().lower().strip()
        cat_filter = self.cat_combo.currentText()
        
        for item in self.cad_symbols:
            tid = str(item['CAD_ID'])
            name = item.get('Nombre_Original_EXE', '')
            cat = item.get('Categoria', '')
            tags = item.get('Tags', '')
            
            if cat_filter != "Todas las categorías" and cat != cat_filter:
                continue
            if query and (query not in tid and query not in name.lower() and query not in tags.lower()):
                continue
                
            display_text = f"[{tid:>5}] {name}  | {cat}"
            if tags:
                display_text += f" ({tags})"
            
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item)
            
            if f"CAD:{tid}" in self.map or tid in self.map:
                list_item.setBackground(QColor(30, 80, 40))
                list_item.setForeground(QColor(180, 255, 180))
                
            self.cad_list.addItem(list_item)
            
    def filter_cad_list(self):
        self.populate_cad_list()
        
    def on_cad_selected(self, list_item):
        item = list_item.data(Qt.UserRole)
        if not item:
            return
        self.cur_item = item
        tid = str(item['CAD_ID'])
        self.cur_key = f"CAD:{tid}"
        
        info_text = (
            f"ID: {tid} | Categoria: {item.get('Categoria', '-')}\n"
            f"Nombre Oficial: {item.get('Nombre_Original_EXE', '-')}\n"
            f"Subtipo: {item.get('Subtipo', '-')}\n"
            f"Tags: {item.get('Tags', '-')}\n"
            f"Terminales: {item.get('Terminales', '-')}\n"
            f"Descripción: {item.get('Descripcion', '-')}"
        )
        self.cad_info.setText(info_text)
        self.suggest_qet_items(item)

    def suggest_qet_items(self, item):
        self.qet_list.clear()
        name = item.get('Nombre_Original_EXE', '').lower()
        cat = item.get('Categoria', '').lower()
        
        kws = []
        if 'motor' in name or 'motor' in cat:
            kws = ['motor', 'moteur']
        elif 'contactor' in name or 'contactores' in cat:
            kws = ['contacteur', 'km']
        elif 'bobina' in name or 'bobinas' in cat:
            kws = ['bobine', 'coil', 'relais']
        elif 'rele' in name or 'térmico' in name:
            kws = ['thermique', 'relais']
        elif 'pulsador' in name or 'accionamientos' in cat:
            kws = ['poussoir', 'bouton']
        elif 'disyuntor' in name or 'automático' in name or 'protecciones' in cat:
            kws = ['disjoncteur', 'fusible']
        elif 'piloto' in name or 'señalizacion' in cat:
            kws = ['voyant', 'lamp']
        elif 'detector' in name or 'detectores' in cat:
            kws = ['capteur', 'sensor', 'detecteur']
        elif 'contacto' in name or 'contactos' in cat:
            kws = ['contact', 'aux']
            
        added = 0
        if kws:
            for s in self.qet:
                fname = s['Filename'].lower()
                if any(k in fname for k in kws):
                    it = QListWidgetItem(s['Filename'])
                    it.setData(Qt.UserRole, s)
                    self.qet_list.addItem(it)
                    added += 1
                    if added >= 100:
                        break
                        
        if added == 0:
            for s in self.qet[:100]:
                it = QListWidgetItem(s['Filename'])
                it.setData(Qt.UserRole, s)
                self.qet_list.addItem(it)

    def filter_qet_list(self, text):
        self.qet_list.clear()
        if not text:
            if self.cur_item:
                self.suggest_qet_items(self.cur_item)
            return
        query = text.lower().strip()
        added = 0
        for s in self.qet:
            if query in s['Filename'].lower():
                it = QListWidgetItem(s['Filename'])
                it.setData(Qt.UserRole, s)
                self.qet_list.addItem(it)
                added += 1
                if added >= 150:
                    break

    def on_tile_selected_from_sheet(self, path: str, bmp_id, row: int, col: int, tile_info: dict):
        """Callback cuando el usuario hace clic en un tile del TileSheetLabel."""
        nm = Path(path).name
        sz = 24
        sx = col * sz
        sy = row * sz
        self.sel_tile = {'path': path, 'x': sx, 'y': sy, 'size': sz, 'sheet': nm,
                         'row': row, 'col': col, 'bmp_id': bmp_id}

        cad_id = tile_info.get('cad_id')
        name   = tile_info.get('name', '')
        cat    = tile_info.get('category', '')
        subtip = tile_info.get('subtipo', '')

        if cad_id is not None:
            # Buscar si ya hay mapeo
            map_key = f"CAD:{cad_id}"
            has_map = map_key in self.map or str(cad_id) in self.map
            mapped_str = f" ✔ YA MAPEADO → {self.map.get(map_key, self.map.get(str(cad_id), {})).get('qet_file', '')}" if has_map else ""
            self.tile_label.setText(
                f"⚡ Tile [{row},{col}] | CAD_ID={cad_id} | {name} | {cat} / {subtip}{mapped_str}"
            )
            # Seleccionar automáticamente el símbolo en la lista CAD
            for i in range(self.cad_list.count()):
                it = self.cad_list.item(i)
                if it and it.data(Qt.UserRole) and str(it.data(Qt.UserRole).get('CAD_ID', '')) == str(cad_id):
                    self.cad_list.setCurrentRow(i)
                    self.on_cad_selected(it)
                    break
        else:
            self.tile_label.setText(f"Tile [{row},{col}] — Sin CAD_ID conocido (fuera del catálogo)")

    # Compatibilidad con código antiguo
    def on_sheet_clicked(self, event, path, name):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        raw_x = int(pos.x() / 2)
        raw_y = int(pos.y() / 2)
        ts = 24
        row, col = raw_y // ts, raw_x // ts
        bmp_id = int(Path(path).stem.replace('bitmap_', ''))
        key = f"{bmp_id}_{row:02d}_{col:02d}"
        tile_info = self.tile_to_cad.get(key, {})
        self.on_tile_selected_from_sheet(path, bmp_id, row, col, tile_info)

    def preview_qet(self, list_item):
        data = list_item.data(Qt.UserRole)
        path = data.get('Full_Path')
        if not path or not os.path.exists(path):
            self.preview_label.clear()
            self.preview_label.setText(data['Filename'])
            return
            
        try:
            if USE_P and PARSER:
                svg = PARSER.elmt_to_svg(path)
                if svg:
                    if '<svg' not in svg:
                        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">{svg}</svg>'
                    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
                    if renderer.isValid():
                        pix = QPixmap(240, 240)
                        pix.fill(Qt.white)
                        painter = QPainter(pix)
                        renderer.render(painter)
                        painter.end()
                        self.preview_label.setPixmap(pix)
                        return
        except Exception as e:
            print(f"Error previewing QET: {e}")
            
        self.preview_label.clear()
        self.preview_label.setText(data['Filename'])

    def assign_current_mapping(self):
        if not self.cur_key:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un símbolo CAD en la lista izquierda.")
            return
        current_qet = self.qet_list.currentItem()
        if not current_qet:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un elemento QET en la lista derecha.")
            return
        self.assign_mapping(current_qet)

    def assign_mapping(self, list_item):
        if not self.cur_key or not self.cur_item:
            QMessageBox.warning(self, "Atención", "Selecciona un símbolo CAD primero.")
            return
            
        qet_data = list_item.data(Qt.UserRole)
        self.map[self.cur_key] = {
            'cad_key': self.cur_key,
            'cad_id': self.cur_item['CAD_ID'],
            'cad_name': self.cur_item.get('Nombre_Original_EXE', ''),
            'category': self.cur_item.get('Categoria', ''),
            'subtype': self.cur_item.get('Subtipo', ''),
            'tile': self.sel_tile,
            'qet_file': qet_data['Filename'],
            'qet_path': qet_data.get('Rel_Path', '')
        }
        self.save_mapping()
        self.populate_cad_list()
        QMessageBox.information(self, "Asignado", f"Mapeo guardado para {self.cur_item.get('Nombre_Original_EXE')} ({self.cur_key}) -> {qet_data['Filename']}")

    def open_current_in_studio(self):
        """Abre el símbolo seleccionado actualmente en la pestaña Symbol Studio."""
        current_qet = self.qet_list.currentItem()
        qet_path = None
        if current_qet:
            data = current_qet.data(Qt.UserRole)
            qet_path = data.get('Full_Path')
            
        cad_name = self.cur_item.get('Nombre_Original_EXE', 'simbolo_cad') if self.cur_item else "nuevo_simbolo"
        cad_id = str(self.cur_item['CAD_ID']) if self.cur_item else "0"
        
        # Cambiar a la pestaña de Studio
        self.main_tabs.setCurrentIndex(1)
        
        if qet_path and os.path.exists(qet_path) and PARSER:
            comp_def = PARSER.create_component_definition(qet_path)
            comp_def['id'] = f"cad_{cad_id}"
            comp_def['name'] = cad_name
            self.studio_tab.cur_symbol = comp_def
            self.studio_tab.input_sym_id.setText(comp_def['id'])
            self.studio_tab.input_sym_name.setText(comp_def['name'])
            self.studio_tab.input_sym_type.setCurrentText(comp_def.get('type', 'generic'))
            vis = comp_def.get('visual', {})
            self.studio_tab.spin_width.setValue(int(vis.get('width', 90)))
            self.studio_tab.spin_height.setValue(int(vis.get('height', 72)))
            if vis.get('svg_content'):
                self.studio_tab.svg_renderer = QSvgRenderer(QByteArray(vis['svg_content'].encode('utf-8')))
            self.studio_tab.scene.set_component_bounds(
                vis.get('width', 90), vis.get('height', 72), comp_def.get('type', 'generic'), self.studio_tab.svg_renderer
            )
            self.studio_tab.refresh_terminal_items()
        elif self.cur_item:
            # Buscar si hay un componente nativo equivalente para cargar como base
            cat = self.cur_item.get('Categoria', '').lower()
            name = cad_name.lower()
            base_key = 'generic'
            if 'motor' in name:
                base_key = 'motor_3p'
            elif 'contactor' in name or 'contactores' in cat:
                base_key = 'contactor_3p'
            elif 'pulsador' in name:
                base_key = 'pushbutton_no'
            elif 'disyuntor' in name:
                base_key = 'breaker_3p'
            if base_key in STANDARD_COMPONENTS:
                self.studio_tab.load_component(base_key)
                self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
                self.studio_tab.input_sym_name.setText(cad_name)

    def save_mapping(self):
        mapping_path = BASE / 'data' / 'mappings' / 'symbol_mapping_manual.json'
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.map, f, indent=2, ensure_ascii=False)

    def export_csv(self):
        default_export = BASE / 'data' / 'mappings' / 'mapeo_simbolos_export.csv'
        out_path, _ = QFileDialog.getSaveFileName(self, "Exportar Mapeo CSV", str(default_export), "CSV (*.csv)")
        if out_path:
            with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['CAD_KEY', 'CAD_ID', 'NOMBRE', 'CATEGORIA', 'SUBTIPO', 'QET_FILE', 'TILE_SHEET', 'TILE_X', 'TILE_Y'])
                for k, v in sorted(self.map.items()):
                    tile = v.get('tile') or {}
                    writer.writerow([
                        v.get('cad_key', k),
                        v.get('cad_id', ''),
                        v.get('cad_name', ''),
                        v.get('category', ''),
                        v.get('subtype', ''),
                        v.get('qet_file', ''),
                        tile.get('sheet', ''),
                        tile.get('x', ''),
                        tile.get('y', '')
                    ])
            QMessageBox.information(self, "Exportado", f"Mapeo exportado exitosamente a:\n{out_path}")


def main():
    app = QApplication(sys.argv)
    window = CADeSimuMapperWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
