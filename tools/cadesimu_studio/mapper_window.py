"""
Ventana Principal de CADe SIMU Mapper & Symbol Studio.
"""
import os
import json
import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QPushButton, QScrollArea, QTabWidget,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .config import (
    BASE_PATH, CATALOG_COMPLETE_PATH, QET_CATALOG_CSV_PATH,
    MANUAL_MAPPING_PATH, TILE_TO_CAD_PATH, DISPATCH_TABLE_PATH
)
from .tile_sheet_label import TileSheetLabel
from .gallery_widget import GalleryListWidget
from .symbol_editor_widget import SymbolEditorWidget

try:
    from src.qet.parser import QETParser
    PARSER = QETParser()
    USE_P = True
except Exception:
    PARSER = None
    USE_P = False

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
        catalog_path = CATALOG_COMPLETE_PATH
        if not catalog_path.exists():
            catalog_path = BASE_PATH / 'cadesimu_symbols_complete.json'
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.cad_symbols = json.load(f)
                for s in self.cad_symbols:
                    self.cad_symbols_by_id[str(s['CAD_ID'])] = s

        # 2. Catálogo QET
        self.qet = []
        qet_catalog = QET_CATALOG_CSV_PATH
        if not qet_catalog.exists():
            qet_catalog = BASE_PATH / 'qet_symbols_catalog.csv'
        if qet_catalog.exists():
            with open(qet_catalog, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    if r.get('Filename'):
                        self.qet.append(r)

        # 3. Mapeos existentes
        self.map = {}
        mapping_path = MANUAL_MAPPING_PATH
        if not mapping_path.exists():
            mapping_path = BASE_PATH / 'symbol_mapping_manual.json'
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    self.map = json.load(f)
            except Exception:
                self.map = {}

        # 4. Mapa tile → CAD_ID (generado por build_tile_map.py)
        self.tile_to_cad = {}
        tile_map_path = TILE_TO_CAD_PATH
        if tile_map_path.exists():
            try:
                with open(tile_map_path, 'r', encoding='utf-8') as f:
                    self.tile_to_cad = json.load(f)
            except Exception:
                self.tile_to_cad = {}

        # 5. Dispatch table CAD_ID → componente SimuCraft
        self.dispatch_table = {}
        dispatch_path = DISPATCH_TABLE_PATH
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
        
        # Panel Central: Galería / Biblioteca de Bitmaps (CADe SIMU)
        center_box = QGroupBox("Iconos & Bitmaps Originales (CADe SIMU)")
        center_layout = QVBoxLayout(center_box)

        # Barra superior con selector de categoría y buscador de BMPs
        center_nav = QHBoxLayout()
        self.gallery_filter_combo = QComboBox()
        self.gallery_filter_combo.addItems([
            "Todas las imágenes",
            "🛠 Toolbars GUI (21px)",
            "📋 Hojas de Tiles / PLC",
            "🖼 Vistas 2D y 3D de hardware",
            "ℹ Splash & Acerca de"
        ])
        self.gallery_filter_combo.currentIndexChanged.connect(self._filter_gallery)
        center_nav.addWidget(QLabel("Filtrar:"))
        center_nav.addWidget(self.gallery_filter_combo)

        self.gallery_search = QLineEdit()
        self.gallery_search.setPlaceholderText("Buscar bitmap (ej: 259, motor, 173)...")
        self.gallery_search.textChanged.connect(self._filter_gallery)
        center_nav.addWidget(self.gallery_search)

        # Botón para volver a la galería desde la vista detalle
        self.btn_back_to_gallery = QPushButton("⬅ Volver a Galería")
        self.btn_back_to_gallery.setStyleSheet("background: #34495e; color: white; font-weight: bold; padding: 4px 8px;")
        self.btn_back_to_gallery.clicked.connect(self._show_gallery_view)
        self.btn_back_to_gallery.setVisible(False)
        center_nav.addWidget(self.btn_back_to_gallery)

        center_layout.addLayout(center_nav)

        # Vista de Galería en Modo Thumbnails (GalleryListWidget modular)
        self.gallery_list = GalleryListWidget()
        self.gallery_list.itemDoubleClicked.connect(self._on_gallery_item_double_clicked)
        self.gallery_list.itemClicked.connect(self._on_gallery_item_clicked)
        center_layout.addWidget(self.gallery_list)

        # Contenedor para el visor ampliado con overlay interactivo de tiles
        self.sheet_viewer_scroll = QScrollArea()
        self.sheet_viewer_scroll.setWidgetResizable(False)
        self.sheet_viewer_scroll.setVisible(False)
        center_layout.addWidget(self.sheet_viewer_scroll)

        # Leyenda de estado de asociación visual
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Leyenda:"))
        lbl_set = QLabel("■ Verde: Mapeado a QET")
        lbl_set.setStyleSheet("color: #2ecc71; font-weight: bold;")
        lbl_bound = QLabel("■ Naranja: Con CAD_ID (pendiente QET)")
        lbl_bound.setStyleSheet("color: #f39c12; font-weight: bold;")
        lbl_unset = QLabel("■ Rojo: Sin asociar")
        lbl_unset.setStyleSheet("color: #e74c3c; font-weight: bold;")
        legend_layout.addWidget(lbl_set)
        legend_layout.addWidget(lbl_bound)
        legend_layout.addWidget(lbl_unset)
        legend_layout.addStretch()
        center_layout.addLayout(legend_layout)

        # Etiqueta de información del tile seleccionado
        self.tile_label = QLabel("Tile seleccionado: Ninguno — Haz doble clic en una imagen de la galería para explorar sus tiles")
        self.tile_label.setStyleSheet("font-weight: bold; color: #ffca28; padding: 5px; background: #1a1e24; border-radius: 3px;")
        center_layout.addWidget(self.tile_label)
        splitter.addWidget(center_box)

        # Poblar la galería con los recursos BMP categorizados
        self.gallery_list.filter_items(self.gallery_filter_combo.currentText(), self.gallery_search.text())
        
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

    def _filter_gallery(self):
        """Filtrar la galería visual por categoría y texto de búsqueda."""
        selected_cat = self.gallery_filter_combo.currentText()
        query = self.gallery_search.text()
        self.gallery_list.filter_items(selected_cat, query)

    def _on_gallery_item_clicked(self, list_item):
        d = list_item.data(Qt.UserRole)
        if not d:
            return
        self.tile_label.setText(
            f"🖼 Seleccionado: {d['filename']} ({d['width']}x{d['height']}px) — {d['category']} | Haz doble clic para abrir visor de tiles"
        )

    def _on_gallery_item_double_clicked(self, list_item):
        d = list_item.data(Qt.UserRole)
        if not d:
            return
        # Abrir el visor de la hoja/imagen con overlay de tiles
        self._open_sheet_viewer(d['path'], d.get('bmp_id'), d['filename'])

    def _open_sheet_viewer(self, img_path: str, bmp_id, filename: str):
        """Abrir visor ampliado de una imagen con grilla y señalizaciones de tiles."""
        self.gallery_list.setVisible(False)
        self.btn_back_to_gallery.setVisible(True)
        self.btn_back_to_gallery.setText(f"⬅ Volver a Galería (Viéndose: {filename})")

        tile_lbl = TileSheetLabel(
            img_path, bmp_id, self.tile_to_cad, self.map,
            on_tile_selected=self.on_tile_selected_from_sheet
        )
        self.sheet_viewer_scroll.setWidget(tile_lbl)
        self.sheet_viewer_scroll.setVisible(True)

    def _show_gallery_view(self):
        """Regresar de la vista de hoja individual a la galería de thumbnails."""
        self.sheet_viewer_scroll.setVisible(False)
        self.gallery_list.setVisible(True)
        self.btn_back_to_gallery.setVisible(False)

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
        mapping_path = MANUAL_MAPPING_PATH
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.map, f, indent=2, ensure_ascii=False)

    def export_csv(self):
        default_export = BASE_PATH / 'data' / 'mappings' / 'mapeo_simbolos_export.csv'
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


