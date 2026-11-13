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
from PySide6.QtCore import Qt, QSize, QByteArray, QRectF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from .config import (
    BASE_PATH, CATALOG_COMPLETE_PATH, QET_CATALOG_CSV_PATH,
    MANUAL_MAPPING_PATH, CAD_QET_MAPPING_PATH, TILE_TO_CAD_PATH, DISPATCH_TABLE_PATH,
    CAD_TO_SIMUCRAFT_ALIASES, SIMUCRAFT_TO_CAD_ALIASES
)
try:
    from src.components.standard_components import STANDARD_COMPONENTS
except Exception:
    STANDARD_COMPONENTS = {}
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
        self._skip_next_tab_sync = False
        self._is_syncing_tabs = False
        
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

        # 3. Mapeos existentes: cargar mapa maestro pre-mapeado y sobreescribir con manual
        self.map = {}
        if CAD_QET_MAPPING_PATH.exists():
            try:
                with open(CAD_QET_MAPPING_PATH, 'r', encoding='utf-8') as f:
                    master_data = json.load(f)
                    for k, v in master_data.get('mappings', {}).items():
                        if v.get('qet_file') or v.get('simucraft_component'):
                            cad_key = f"CAD:{k}"
                            self.map[cad_key] = {
                                'cad_key': cad_key,
                                'cad_id': v.get('cad_id', int(k) if k.isdigit() else k),
                                'cad_name': v.get('name', ''),
                                'category': v.get('category', ''),
                                'subtype': v.get('subtype', ''),
                                'qet_file': v.get('qet_file') or '',
                                'component_key': v.get('simucraft_component') or ''
                            }
            except Exception as e:
                print(f"Error cargando cad_qet_mapping.json: {e}")

        mapping_path = MANUAL_MAPPING_PATH
        if not mapping_path.exists():
            mapping_path = BASE_PATH / 'symbol_mapping_manual.json'
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    self.map.update(json.load(f))
            except Exception:
                pass

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
        self.cat_combo.addItem("Todas las categorías", "Todas las categorías")
        categories = sorted(list(set(s.get('Categoria', 'Otros') for s in self.cad_symbols)))
        for cat in categories:
            label = cat
            if cat == "Virtual_2D":
                label = "Virtual_2D (Laboratorio Virtual / Bitmaps)"
            elif cat == "2D_3D":
                label = "2D_3D (Vistas físicas hardware)"
            self.cat_combo.addItem(label, cat)
        self.cat_combo.currentIndexChanged.connect(self.filter_cad_list)
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
        self.qet_list.currentItemChanged.connect(lambda cur, prev: self.preview_qet(cur) if cur else None)
        self.qet_list.itemDoubleClicked.connect(self.assign_mapping)
        right_layout.addWidget(self.qet_list)
        
        self.preview_label = QLabel("Vista previa SVG")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedHeight(230)
        self.preview_label.setStyleSheet("background: #ffffff; color: #333333; font-weight: bold; border: 2px solid #555; border-radius: 4px;")
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

        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)

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
        fname = d['filename']
        bmp_id = d.get('bmp_id')
        cat = d.get('category', '')

        # Contar cuántos tiles en esta imagen están asociados a CAD_ID
        cad_matches = []
        if bmp_id is not None:
            prefix = f"{bmp_id}_"
            for k, info in self.tile_to_cad.items():
                if k.startswith(prefix) and info.get('cad_id') is not None:
                    cad_matches.append(info['cad_id'])

        match_str = f" | ⚡ {len(cad_matches)} tiles vinculados a CADe SIMU" if cad_matches else ""
        if "Toolbars" in cat:
            cat_desc = "Botones barra GUI (interfaz)"
        elif "Hojas" in cat:
            cat_desc = "Lámina de Tiles / Catálogo de símbolos y PLC"
        elif "Vistas" in cat:
            cat_desc = "Vista de hardware 2D/3D (Laboratorio Virtual)"
        else:
            cat_desc = cat

        self.tile_label.setText(
            f"🖼 {fname} ({d['width']}x{d['height']}px) — {cat_desc}{match_str} | Doble clic para explorar tiles"
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
        cat_filter = self.cat_combo.currentData() or self.cat_combo.currentText()
        
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
        cat = item.get('Categoria', '')
        
        simu_key = self.get_simucraft_equivalent(tid)
        simu_str = f"✔ {simu_key} (Vinculado a SimuCraft)" if simu_key else "⚠ Sin componente nativo directo"

        map_entry = self.map.get(self.cur_key) or self.map.get(tid)
        qet_str = f"✔ {map_entry.get('qet_file')}" if (map_entry and map_entry.get('qet_file')) else "Sin archivo QET (.elmt) asignado"
        
        info_lines = [
            f"ID CAD: [{tid:>5}] | Categoria: {cat}",
            f"Nombre Oficial: {item.get('Nombre_Original_EXE', '-')}"
        ]

        if cat == 'Virtual_2D' or 'bitmap' in item.get('Nombre_Original_EXE', '').lower():
            info_lines.append("ℹ TIPO: Sprite Gráfico de Laboratorio Virtual 2D (Entorno Físico)")
            info_lines.append("ℹ CORRELACIÓN: No aplica a esquemáticos QET (es un elemento visual de CADe SIMU)")
        else:
            info_lines.append(f"SimuCraft Nativo: {simu_str}")
            info_lines.append(f"Mapeo QET: {qet_str}")

        info_lines.append(f"Subtipo: {item.get('Subtipo', '-')} | Terminales: {item.get('Terminales', '-')}")
        info_lines.append(f"Descripción: {item.get('Descripcion', '-')}")
        
        self.cad_info.setText("\n".join(info_lines))
        self.suggest_qet_items(item)

    def suggest_qet_items(self, item):
        self.qet_list.clear()
        name = item.get('Nombre_Original_EXE', '').lower()
        cat = item.get('Categoria', '').lower()
        tid = str(item.get('CAD_ID', ''))

        # Si es un elemento de Virtual_2D / Sprite bitmap de laboratorio
        if cat == 'virtual_2d' or 'bitmap' in name:
            it = QListWidgetItem("ℹ [Sprite 2D de Laboratorio Virtual — No aplica a esquemáticos QET]")
            it.setFlags(Qt.NoItemFlags)
            it.setForeground(QColor(240, 180, 80))
            self.qet_list.addItem(it)
            return

        # 1. Si ya tiene un archivo QET asignado/mapeado, colocarlo al inicio destacado en verde
        map_entry = self.map.get(f"CAD:{tid}") or self.map.get(tid)
        mapped_qet_file = map_entry.get('qet_file') if map_entry else None
        if mapped_qet_file:
            found = False
            for s in self.qet:
                if s['Filename'].lower() == mapped_qet_file.lower():
                    it = QListWidgetItem(f"✔ [Mapeado] {s['Filename']}")
                    it.setData(Qt.UserRole, s)
                    it.setBackground(QColor(30, 80, 40))
                    it.setForeground(QColor(180, 255, 180))
                    self.qet_list.addItem(it)
                    found = True
                    break
            if not found:
                full_cand = None
                for qdir in [BASE_PATH / 'elements', Path('/home/vibecode/DevS/qelectrotech-elements/elements')]:
                    if qdir.exists():
                        matches = list(qdir.rglob(mapped_qet_file))
                        if matches:
                            full_cand = str(matches[0])
                            break
                item_data = {
                    'Filename': mapped_qet_file,
                    'Full_Path': full_cand or ''
                }
                it = QListWidgetItem(f"✔ [Mapeo registrado] {mapped_qet_file}")
                it.setData(Qt.UserRole, item_data)
                it.setBackground(QColor(30, 80, 40))
                it.setForeground(QColor(180, 255, 180))
                self.qet_list.addItem(it)

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
                    if mapped_qet_file and s['Filename'].lower() == mapped_qet_file.lower():
                        continue
                    it = QListWidgetItem(s['Filename'])
                    it.setData(Qt.UserRole, s)
                    self.qet_list.addItem(it)
                    added += 1
                    if added >= 100:
                        break
                        
        if added == 0 and not mapped_qet_file:
            for s in self.qet[:100]:
                it = QListWidgetItem(s['Filename'])
                it.setData(Qt.UserRole, s)
                self.qet_list.addItem(it)

        # Seleccionar y mostrar vista previa del primer elemento si existe
        if self.qet_list.count() > 0:
            first_it = self.qet_list.item(0)
            self.qet_list.setCurrentRow(0)
            self.preview_qet(first_it)
        else:
            self.preview_label.clear()
            self.preview_label.setText("Sin elementos QET")

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

        if self.qet_list.count() > 0:
            first_it = self.qet_list.item(0)
            self.qet_list.setCurrentRow(0)
            self.preview_qet(first_it)
        else:
            self.preview_label.clear()
            self.preview_label.setText("Sin coincidencias")

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

    # Tabla de sustitución para archivos .elmt mencionados en cad_qet_mapping.json
    # que no existen en la biblioteca qelectrotech-elements con ese nombre exacto.
    _QET_FALLBACK_SUBSTITUTIONS = {
        'moteur_tri.elmt': 'moteur.elmt',
        'moteur_mono.elmt': '71007210_moteur.elmt',
        'moteur_1p.elmt': '71007210_moteur.elmt',
        'contacteur_2p.elmt': 'km_tri.elmt',
        'contacteur_4p.elmt': 'km_tri.elmt',
        'contacteur_1p.elmt': 'km_tri.elmt',
        'contacteur_3p.elmt': 'km_tri.elmt',
        'fusible.elmt': '71104001_cc_fusible.elmt',
        'disjoncteur_1p.elmt': 'disjoncteur-uni-dclic.elmt',
        'disjoncteur_3p.elmt': 'disjoncteur-tetra-dt40.elmt',
        'bobine_relais.elmt': '71105013_bouton_poussoir.elmt',
        'bobine_coil.elmt': '71105013_bouton_poussoir.elmt',
        'bobine_contacteur.elmt': '71105013_bouton_poussoir.elmt',
        'detecteur_inductif.elmt': 'detector-gas.elmt',
        'detecteur_capacitif.elmt': 'detector-gas.elmt',
        'detecteur_optico.elmt': 'detector-gas.elmt',
    }
    _QET_BASE = Path('/home/vibecode/DevS/qelectrotech-elements/elements')

    def _resolve_qet_path(self, data: dict) -> str:
        """Resuelve la ruta física de un .elmt usando múltiples estrategias de búsqueda."""
        # 1. Full_Path directo
        path = data.get('Full_Path', '')
        if path and os.path.exists(path):
            return path

        # 2. Rel_Path relativo a la raíz QET
        rel = data.get('Rel_Path') or data.get('qet_path')
        if rel:
            for base in [BASE_PATH / 'elements', self._QET_BASE]:
                cand = base / rel
                if cand.exists():
                    return str(cand)

        # 3. Nombre de archivo solamente
        fname = data.get('Filename') or data.get('qet_file') or ''
        base_fname = Path(fname).name if fname else ''
        if not base_fname:
            return ''

        # 3a. Sustitución directa si es un alias conocido
        sub = self._QET_FALLBACK_SUBSTITUTIONS.get(base_fname.lower())
        if sub:
            matches = list(self._QET_BASE.rglob(sub))
            if matches:
                return str(matches[0])

        # 3b. Búsqueda glob en la biblioteca QET
        matches = list(self._QET_BASE.rglob(base_fname))
        if matches:
            return str(matches[0])

        return ''

    def preview_qet(self, list_item):
        if not list_item:
            return
        data = list_item.data(Qt.UserRole)
        if not data or not isinstance(data, dict):
            self.preview_label.clear()
            self.preview_label.setText(list_item.text().lstrip('✔ ').strip())
            return

        path = self._resolve_qet_path(data)

        if not path or not os.path.exists(path):
            self.preview_label.clear()
            fname = data.get('Filename') or data.get('qet_file') or list_item.text()
            self.preview_label.setText(f"Sin archivo físico:\n{Path(fname).name}")
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

                        sz = renderer.defaultSize()
                        w = float(sz.width()) if sz.width() > 0 else 40.0
                        h = float(sz.height()) if sz.height() > 0 else 40.0
                        scale = min(200.0 / w, 200.0 / h)
                        tw, th = w * scale, h * scale
                        tx = (240.0 - tw) / 2.0
                        ty = (240.0 - th) / 2.0
                        target_rect = QRectF(tx, ty, tw, th)

                        renderer.render(painter, target_rect)
                        painter.end()
                        self.preview_label.setPixmap(pix)
                        return
        except Exception as e:
            print(f"Error previewing QET: {e}")

        self.preview_label.clear()
        self.preview_label.setText(data.get('Filename', 'Sin vista previa'))

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

    def _on_main_tab_changed(self, index: int):
        """Gestiona el cambio de pestaña y realiza la sincronización bidireccional."""
        if getattr(self, '_skip_next_tab_sync', False) or getattr(self, '_is_syncing_tabs', False):
            return
        self._is_syncing_tabs = True
        try:
            if index == 1:
                # Pestaña 2: Studio / Editor
                self.sync_mapper_to_studio()
            elif index == 0:
                # Pestaña 1: Mapper / Catálogo
                self.sync_studio_to_mapper()
        finally:
            self._is_syncing_tabs = False

    def get_simucraft_equivalent(self, cad_id: str) -> str:
        """Determina la clave de componente SimuCraft correspondiente a un CAD_ID."""
        cad_id = str(cad_id)
        # 1. ¿Existe como símbolo personalizado propio? (ej: cad_1000)
        custom_key = f"cad_{cad_id}"
        if custom_key in STANDARD_COMPONENTS:
            return custom_key
            
        # 2. Buscar en tabla de despacho CAD_ID -> Componente SimuCraft
        if cad_id in self.dispatch_table:
            entry = self.dispatch_table[cad_id]
            raw_key = entry.get('component_key') if isinstance(entry, dict) else str(entry)
            if raw_key:
                if raw_key in STANDARD_COMPONENTS:
                    return raw_key
                if raw_key in CAD_TO_SIMUCRAFT_ALIASES:
                    alias_key = CAD_TO_SIMUCRAFT_ALIASES[raw_key]
                    if alias_key in STANDARD_COMPONENTS:
                        return alias_key
                    return alias_key
                return raw_key

        # 3. Buscar en el mapeo manual (self.map)
        cur_key = f"CAD:{cad_id}"
        map_entry = self.map.get(cur_key) or self.map.get(cad_id)
        if map_entry and isinstance(map_entry, dict) and map_entry.get('component_key'):
            return map_entry['component_key']
                
        # 4. Buscar en el catálogo CAD por heurística según nombre y categoría
        item = self.cad_symbols_by_id.get(cad_id)
        if item:
            name = item.get('Nombre_Original_EXE', '').lower()
            cat = item.get('Categoria', '').lower()
            if 'motor' in name:
                if 'monof' in name or '1' in name:
                    return 'motor_1p'
                elif 'dahalander' in name or 'dahlander' in name:
                    return 'motor_dahlander'
                return 'motor_3p'
            elif 'contactor' in name or 'contactores' in cat:
                if '2' in name:
                    return 'contactor_2p'
                elif '4' in name:
                    return 'contactor_4p'
                return 'contactor_3p'
            elif 'pulsador' in name or 'accionamientos' in cat:
                if 'nc' in name:
                    return 'pushbutton_nc'
                elif 'seta' in name:
                    return 'pushbutton_mushroom_nc'
                return 'pushbutton_no'
            elif 'disyuntor' in name or 'automático' in name or 'protecciones' in cat:
                if '1' in name:
                    return 'breaker_1p'
                return 'breaker_3p'
            elif 'rele' in name or 'térmico' in name:
                return 'thermal_relay_3p'
            elif 'bobina' in name or 'bobinas' in cat:
                return 'contactor_coil'
            elif 'piloto' in name or 'señalizacion' in cat or 'senalizacion' in cat:
                return 'pilot_lamp'
            elif 'contacto' in name or 'contactos' in cat:
                if 'nc' in name:
                    return 'contactor_contact_nc'
                return 'contactor_contact_no'
                
        return ""

    def get_cad_equivalent(self, comp_key: str, sym_id: str = "") -> str:
        """Determina el CAD_ID de CADe SIMU correspondiente a un componente de SimuCraft."""
        # 1. Si el ID tiene prefijo cad_ (ej: cad_1000)
        for cand in [sym_id, comp_key]:
            if cand and cand.startswith('cad_'):
                clean = cand.replace('cad_', '')
                if clean in self.cad_symbols_by_id:
                    return clean

        # 2. Búsqueda inversa en dispatch_table usando clave y alias
        cand_keys = [comp_key]
        if comp_key in SIMUCRAFT_TO_CAD_ALIASES:
            cand_keys.append(SIMUCRAFT_TO_CAD_ALIASES[comp_key])

        for c_key in cand_keys:
            for cid, info in self.dispatch_table.items():
                target = info.get('component_key') if isinstance(info, dict) else str(info)
                if target == c_key:
                    return str(cid)

        # 3. Búsqueda en mapeo manual (self.map)
        for k, v in self.map.items():
            if isinstance(v, dict):
                if v.get('cad_id') and (v.get('component_key') == comp_key or comp_key in v.get('qet_file', '').lower()):
                    return str(v['cad_id'])

        # 4. Heurística inversa por nombre de componente
        ck_lower = comp_key.lower()
        if 'motor_3p' in ck_lower:
            return '1000'
        elif 'motor_1p' in ck_lower:
            return '1002'
        elif 'contactor_3p' in ck_lower or 'contactor' in ck_lower:
            return '2001'
        elif 'contact_no' in ck_lower:
            return '7000'
        elif 'contact_nc' in ck_lower:
            return '7001'
        elif 'pushbutton_no' in ck_lower:
            return '8000'
        elif 'pushbutton_nc' in ck_lower:
            return '8001'
        elif 'coil' in ck_lower:
            return '9000'
        elif 'lamp' in ck_lower:
            return '9008'
        elif 'breaker' in ck_lower:
            return '5002'

        return ""

    def sync_mapper_to_studio(self):
        """Sincroniza la selección de CADe SIMU hacia el Editor de Símbolos (Tab 2)."""
        if not self.cur_item:
            current_it = self.cad_list.currentItem()
            if current_it:
                self.cur_item = current_it.data(Qt.UserRole)
            elif self.cad_list.count() > 0:
                self.cad_list.setCurrentRow(0)
                current_it = self.cad_list.currentItem()
                if current_it:
                    self.cur_item = current_it.data(Qt.UserRole)

        if not self.cur_item:
            return

        cad_id = str(self.cur_item.get('CAD_ID', ''))
        cad_name = self.cur_item.get('Nombre_Original_EXE', '')
        
        simu_key = self.get_simucraft_equivalent(cad_id)
        
        if simu_key:
            # Buscar en el combo del Studio
            idx = self.studio_tab.comp_combo.findData(simu_key)
            if idx >= 0:
                self.studio_tab.comp_combo.blockSignals(True)
                self.studio_tab.comp_combo.setCurrentIndex(idx)
                self.studio_tab.comp_combo.blockSignals(False)
                self.studio_tab.load_component(simu_key)
                self.studio_tab.info_status.setText(
                    f"🔗 Sincronizado desde CADe SIMU: CAD [{cad_id}] '{cad_name}' ➔ SimuCraft '{simu_key}'"
                )
                return

        # Si no hay componente estándar coincidente en el combo, actualizar campos del studio
        self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
        self.studio_tab.input_sym_name.setText(cad_name)
        self.studio_tab.info_status.setText(
            f"🔗 Contexto activo: CAD [{cad_id}] '{cad_name}' (Listo para diseñar o asignar)"
        )

    def sync_studio_to_mapper(self):
        """Sincroniza el símbolo activo en el Studio hacia la lista CADe SIMU (Tab 1)."""
        comp_key = self.studio_tab.comp_combo.currentData() or ""
        sym_id = self.studio_tab.input_sym_id.text().strip() or self.studio_tab.cur_symbol.get('id', '')
        sym_name = self.studio_tab.input_sym_name.text().strip() or self.studio_tab.cur_symbol.get('name', '')

        target_cad_id = self.get_cad_equivalent(comp_key, sym_id)
        if not target_cad_id:
            return

        # Asegurar que el filtro no oculte el elemento
        target_item = self.cad_symbols_by_id.get(str(target_cad_id))
        needs_repopulate = False
        if target_item:
            cat = target_item.get('Categoria', '')
            current_filter = self.cat_combo.currentData() or self.cat_combo.currentText()
            if current_filter != "Todas las categorías" and current_filter != cat:
                self.cat_combo.blockSignals(True)
                idx_all = self.cat_combo.findData("Todas las categorías")
                if idx_all >= 0:
                    self.cat_combo.setCurrentIndex(idx_all)
                else:
                    self.cat_combo.setCurrentText("Todas las categorías")
                self.cat_combo.blockSignals(False)
                needs_repopulate = True
            if self.cad_search.text():
                self.cad_search.blockSignals(True)
                self.cad_search.clear()
                self.cad_search.blockSignals(False)
                needs_repopulate = True

        if needs_repopulate:
            self.populate_cad_list()

        # Seleccionar el ítem en la lista
        for i in range(self.cad_list.count()):
            it = self.cad_list.item(i)
            d = it.data(Qt.UserRole)
            if d and str(d.get('CAD_ID')) == str(target_cad_id):
                self.cad_list.setCurrentRow(i)
                self.cad_list.scrollToItem(it)
                self.on_cad_selected(it)
                break

    def open_current_in_studio(self):
        """Abre el símbolo QET seleccionado en Symbol Studio con todas sus primitivas vectoriales."""
        current_qet = self.qet_list.currentItem()
        qet_path = None
        if current_qet:
            data = current_qet.data(Qt.UserRole)
            if isinstance(data, dict):
                qet_path = self._resolve_qet_path(data)

        cad_name = self.cur_item.get('Nombre_Original_EXE', 'simbolo_cad') if self.cur_item else "nuevo_simbolo"
        cad_id = str(self.cur_item['CAD_ID']) if self.cur_item else "0"

        self._skip_next_tab_sync = True
        try:
            self.main_tabs.setCurrentIndex(1)

            if qet_path and os.path.exists(qet_path):
                # ── Importar directamente con el importador vectorial ──────
                self.studio_tab.load_elmt_file(qet_path, sym_id=f"cad_{cad_id}", sym_name=cad_name)
                self.studio_tab.info_status.setText(
                    f"🎨 QET desglosado vectorialmente para CAD {cad_id}: {Path(qet_path).name}"
                )
            elif self.cur_item:
                simu_key = self.get_simucraft_equivalent(cad_id)
                if simu_key and simu_key in STANDARD_COMPONENTS:
                    self.studio_tab.load_component(simu_key)
                    self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
                    self.studio_tab.input_sym_name.setText(cad_name)
                    self.studio_tab.info_status.setText(
                        f"🎨 Base SimuCraft cargada para CAD {cad_id}: {simu_key}"
                    )
                else:
                    self.studio_tab.load_component('motor_3p')
                    self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
                    self.studio_tab.input_sym_name.setText(cad_name)
        finally:
            self._skip_next_tab_sync = False

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


