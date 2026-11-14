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
    QMessageBox, QFileDialog, QGraphicsScene, QInputDialog
)
from PySide6.QtCore import Qt, QSize, QByteArray, QRectF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QBrush, QFont
from PySide6.QtSvg import QSvgRenderer
from PIL import Image as _PILImage

from .config import (
    BASE_PATH, CATALOG_COMPLETE_PATH, QET_CATALOG_CSV_PATH,
    MANUAL_MAPPING_PATH, CAD_QET_MAPPING_PATH, TILE_TO_CAD_PATH, DISPATCH_TABLE_PATH,
    CAD_TO_SIMUCRAFT_ALIASES, SIMUCRAFT_TO_CAD_ALIASES, BMP_RESOURCE_DIR
)
try:
    from src.components.standard_components import STANDARD_COMPONENTS
except Exception:
    STANDARD_COMPONENTS = {}
from .tile_sheet_label import TileSheetLabel
from .gallery_widget import GalleryListWidget, BITMAP_NAMES_FILE
from .symbol_editor_widget import SymbolEditorWidget
from .dynamic_tile_cutter import DynamicTileCutterWidget
from .standard_primitive_factory import create_standard_primitives

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
        self.sheet_cache = {}
        self.current_sheet_data = None
        
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

        # Mapa inverso CAD_ID -> (tile_key, info)
        self.cad_to_tile = {}
        for tile_key, info in self.tile_to_cad.items():
            cid = info.get('cad_id')
            if cid is not None:
                self.cad_to_tile[str(cid)] = (tile_key, info)

        # 5. Dispatch table CAD_ID → componente SimuCraft
        self.dispatch_table = {}
        dispatch_path = DISPATCH_TABLE_PATH
        if dispatch_path.exists():
            try:
                with open(dispatch_path, 'r', encoding='utf-8') as f:
                    self.dispatch_table = json.load(f)
            except Exception:
                self.dispatch_table = {}

    def get_tile_pixmap_for_cad(self, cad_id: str):
        """Obtiene el recorte QPixmap del tile asignado a un CAD_ID."""
        cad_id = str(cad_id)
        cur_key = f"CAD:{cad_id}"
        map_entry = self.map.get(cur_key) or self.map.get(cad_id)
        tile_data = None
        if map_entry and isinstance(map_entry, dict) and map_entry.get('tile'):
            tile_data = map_entry['tile']
        elif cad_id in self.cad_to_tile:
            tile_key, info = self.cad_to_tile[cad_id]
            bmp_id = info.get('bitmap')
            row = info.get('row', 0)
            col = info.get('col', 0)
            tile_data = {
                'bmp_id': bmp_id,
                'sheet': f"bitmap_{bmp_id}.bmp" if bmp_id is not None else "",
                'row': row,
                'col': col,
                'x': info.get('x'),
                'y': info.get('y'),
                'w': info.get('w', 24),
                'h': info.get('h', 24)
            }
        if not tile_data:
            return None

        sheet = tile_data.get('sheet')
        bmp_id = tile_data.get('bmp_id')
        path = tile_data.get('path')
        if not path and sheet:
            cand = BMP_RESOURCE_DIR / sheet
            if cand.exists():
                path = str(cand)
        elif not path and bmp_id is not None:
            cand = BMP_RESOURCE_DIR / f"bitmap_{bmp_id}.bmp"
            if cand.exists():
                path = str(cand)

        if not path or not os.path.exists(path):
            return None

        if path not in self.sheet_cache:
            pix = QPixmap(path)
            if pix.isNull():
                try:
                    import tempfile
                    pil = _PILImage.open(path).convert('RGB')
                    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    pil.save(tmp.name)
                    tmp.close()
                    pix = QPixmap(tmp.name)
                    os.unlink(tmp.name)
                except Exception:
                    pix = QPixmap()
            self.sheet_cache[path] = pix

        base_pix = self.sheet_cache[path]
        if base_pix.isNull():
            return None

        x = tile_data.get('x')
        y = tile_data.get('y')
        w = tile_data.get('w') or tile_data.get('size', 24)
        h = tile_data.get('h') or tile_data.get('size', 24)

        if x is None or y is None:
            row = tile_data.get('row', 0)
            col = tile_data.get('col', 0)
            fname = Path(path).name
            if hasattr(self, 'tile_cutter') and hasattr(self.tile_cutter, 'layouts') and fname in self.tile_cutter.layouts:
                lay = self.tile_cutter.layouts[fname]
                cx = lay.get('cuts_x', [])
                cy = lay.get('cuts_y', [])
                if 0 <= col < len(cx) - 1 and 0 <= row < len(cy) - 1:
                    x = cx[col]
                    y = cy[row]
                    w = cx[col + 1] - x
                    h = cy[row + 1] - y
            if x is None or y is None:
                sz = 24
                x = col * sz
                y = row * sz
                w = sz
                h = sz

        if w <= 0 or h <= 0 or x + w > base_pix.width() or y + h > base_pix.height():
            return None

        return base_pix.copy(x, y, w, h)
                
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
        self.cad_list.setIconSize(QSize(22, 22))
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
            "📋 PLC",
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

        # Botón para renombrar bitmap
        self.btn_rename_bmp = QPushButton("✏️ Renombrar...")
        self.btn_rename_bmp.setStyleSheet("background: #4a5568; color: white; padding: 4px 8px; border-radius: 3px;")
        self.btn_rename_bmp.setToolTip("Asignar un nombre descriptivo al bitmap actual")
        self.btn_rename_bmp.clicked.connect(self.rename_current_bitmap)
        center_nav.addWidget(self.btn_rename_bmp)

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

        # Cortador y visor dinámico de tiles (DynamicTileCutterWidget)
        self.tile_cutter = DynamicTileCutterWidget()
        self.tile_cutter.tile_selected.connect(self._on_tile_cutter_selected)
        self.tile_cutter.setVisible(False)
        center_layout.addWidget(self.tile_cutter)

        # Leyenda de estado de asociación visual
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Leyenda:"))
        lbl_set = QLabel("■ Verde: Con CAD_ID asignado")
        lbl_set.setStyleSheet("color: #2ecc71; font-weight: bold;")
        lbl_sel = QLabel("■ Magenta: Tile seleccionado")
        lbl_sel.setStyleSheet("color: #ff007f; font-weight: bold;")
        lbl_unset = QLabel("■ Cyan: Línea de corte (arrastrable)")
        lbl_unset.setStyleSheet("color: #00e5ff; font-weight: bold;")
        legend_layout.addWidget(lbl_set)
        legend_layout.addWidget(lbl_sel)
        legend_layout.addWidget(lbl_unset)
        legend_layout.addStretch()
        center_layout.addLayout(legend_layout)

        # Etiqueta de información del tile seleccionado
        self.tile_label = QLabel("Tile seleccionado: Ninguno — Haz doble clic en una lámina de la galería para explorar sus tiles")
        self.tile_label.setStyleSheet("font-weight: bold; color: #ffca28; padding: 5px; background: #1a1e24; border-radius: 3px;")
        center_layout.addWidget(self.tile_label)
        splitter.addWidget(center_box)

        # Poblar la galería con los recursos BMP categorizados
        self.gallery_list.filter_items(self.gallery_filter_combo.currentText(), self.gallery_search.text())
        
        # Panel Derecho: SimuCraft Native & Asignación de Tile
        right_box = QGroupBox("⚡ Componente SimuCraft & Asignación de Tile")
        right_layout = QVBoxLayout(right_box)
        right_layout.setSpacing(8)

        # 1. Tarjeta informativa del CAD_ID activo
        self.cad_summary_card = QLabel("Selecciona un símbolo CADe SIMU a la izquierda")
        self.cad_summary_card.setStyleSheet(
            "background: #1e1e2e; color: #a6adc8; padding: 8px 12px; border-radius: 6px; "
            "border: 1px solid #313244; font-size: 13px;"
        )
        self.cad_summary_card.setWordWrap(True)
        right_layout.addWidget(self.cad_summary_card)

        # 2. Selector de Componente SimuCraft
        simu_sel_group = QGroupBox("Componente Equivalente en SimuCraft")
        simu_sel_layout = QVBoxLayout(simu_sel_group)
        simu_sel_layout.setContentsMargins(6, 6, 6, 6)

        combo_row = QHBoxLayout()
        self.simu_comp_combo = QComboBox()
        self.simu_comp_combo.addItem("— Sin componente SimuCraft asignado —", "")
        for c_k in sorted(STANDARD_COMPONENTS.keys()):
            c_name = STANDARD_COMPONENTS[c_k].get('name', c_k)
            self.simu_comp_combo.addItem(f"{c_name} ({c_k})", c_k)
        self.simu_comp_combo.currentIndexChanged.connect(self._on_simu_comp_changed)
        combo_row.addWidget(self.simu_comp_combo, 1)

        btn_auto_detect = QPushButton("🔍 Auto-detectar")
        btn_auto_detect.setToolTip("Buscar automáticamente el componente SimuCraft según el catálogo REA")
        btn_auto_detect.clicked.connect(self._auto_detect_simu_component)
        combo_row.addWidget(btn_auto_detect)
        simu_sel_layout.addLayout(combo_row)

        right_layout.addWidget(simu_sel_group)

        # 3. Vista previa vectorial interactiva del componente SimuCraft
        preview_group = QGroupBox("Vista Previa Vectorial del Componente SimuCraft")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(6, 6, 6, 6)

        self.simu_preview_label = QLabel("Vista previa vectorial")
        self.simu_preview_label.setAlignment(Qt.AlignCenter)
        self.simu_preview_label.setFixedHeight(210)
        self.simu_preview_label.setStyleSheet("background: #1e1e2e; border: 1px solid #45475a; border-radius: 4px;")
        preview_layout.addWidget(self.simu_preview_label)

        self.simu_elements_info = QLabel("—")
        self.simu_elements_info.setStyleSheet("color: #89b4fa; font-size: 11px;")
        preview_layout.addWidget(self.simu_elements_info)

        right_layout.addWidget(preview_group)

        # 4. Sección de Vinculación de Tile Gráfico
        tile_bind_group = QGroupBox("🖼 Asignación de Tile Gráfico de CADe SIMU")
        tile_bind_layout = QVBoxLayout(tile_bind_group)
        tile_bind_layout.setContentsMargins(8, 8, 8, 8)

        tile_status_row = QHBoxLayout()
        self.assigned_tile_preview = QLabel()
        self.assigned_tile_preview.setFixedSize(40, 40)
        self.assigned_tile_preview.setAlignment(Qt.AlignCenter)
        self.assigned_tile_preview.setStyleSheet("background: #252830; border: 2px solid #555; border-radius: 4px;")
        tile_status_row.addWidget(self.assigned_tile_preview)

        self.assigned_tile_label = QLabel("Tile asignado: <i>Ninguno</i>")
        self.assigned_tile_label.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        tile_status_row.addWidget(self.assigned_tile_label, 1)
        tile_bind_layout.addLayout(tile_status_row)

        tile_btn_row = QHBoxLayout()
        self.btn_link_tile = QPushButton("🔗 Vincular Tile Seleccionado")
        self.btn_link_tile.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_link_tile.setToolTip("Asigna el tile seleccionado en el panel central a este símbolo CAD")
        self.btn_link_tile.clicked.connect(self.assign_selected_tile_to_cad)
        tile_btn_row.addWidget(self.btn_link_tile)

        self.btn_unlink_tile = QPushButton("❌ Desvincular Tile")
        self.btn_unlink_tile.setStyleSheet("background: #c0392b; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_unlink_tile.setToolTip("Elimina la asociación del tile gráfico de este símbolo CAD")
        self.btn_unlink_tile.clicked.connect(self.unbind_tile_from_cad)
        tile_btn_row.addWidget(self.btn_unlink_tile)

        tile_bind_layout.addLayout(tile_btn_row)
        right_layout.addWidget(tile_bind_group)

        # 5. Barra inferior de acciones
        btn_bar = QHBoxLayout()
        btn_edit_studio = QPushButton("🎨 Abrir en Symbol Studio")
        btn_edit_studio.setStyleSheet("background: #1976d2; color: white; font-weight: bold; padding: 7px; border-radius: 4px;")
        btn_edit_studio.clicked.connect(self.open_current_in_studio)

        btn_save = QPushButton("💾 Guardar Mapeo")
        btn_save.clicked.connect(self.save_mapping)

        btn_export = QPushButton("📤 Exportar CSV")
        btn_export.clicked.connect(self.export_csv)

        btn_browse_qet = QPushButton("📦 Biblioteca QET...")
        btn_browse_qet.setToolTip("Explorar catálogo QElectroTech para importar .elmt")
        btn_browse_qet.clicked.connect(self.open_qet_browser_dialog)

        btn_bar.addWidget(btn_edit_studio)
        btn_bar.addWidget(btn_save)
        btn_bar.addWidget(btn_export)
        btn_bar.addWidget(btn_browse_qet)
        right_layout.addLayout(btn_bar)

        splitter.addWidget(right_box)
        splitter.setSizes([450, 600, 550])
        mapper_layout.addWidget(splitter)
        
        self.main_tabs.addTab(mapper_tab, "⚡ 1. Catálogo & Mapeador CADe SIMU ↔ SimuCraft")

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
        self.current_sheet_data = d
        self.gallery_list.setVisible(False)
        self.btn_back_to_gallery.setVisible(True)
        fname = d['filename']
        friendly = d.get('friendly_name')
        t_extra = f" - '{friendly}'" if friendly else ""
        self.btn_back_to_gallery.setText(f"⬅ Volver a Galería (Viéndose: {fname}{t_extra})")
        self.tile_cutter.setVisible(True)
        self.tile_cutter.load_sheet(d['path'], d.get('bmp_id'), self.tile_to_cad, self.map)

    def _show_gallery_view(self):
        """Regresar de la vista de hoja individual a la galería de thumbnails."""
        self.current_sheet_data = None
        self.tile_cutter.setVisible(False)
        self.gallery_list.setVisible(True)
        self.btn_back_to_gallery.setVisible(False)

    def rename_current_bitmap(self):
        """Permite asignar un nombre descriptivo al bitmap actual y persistirlo."""
        fname = None
        current_name = ""
        if getattr(self, 'current_sheet_data', None):
            fname = self.current_sheet_data['filename']
            current_name = self.current_sheet_data.get('friendly_name', '')
        else:
            cur_it = self.gallery_list.currentItem()
            if cur_it:
                d = cur_it.data(Qt.UserRole)
                if d:
                    fname = d['filename']
                    current_name = d.get('friendly_name', '')

        if not fname:
            QMessageBox.information(self, "Renombrar Bitmap", "Selecciona una imagen de la galería para renombrarla.")
            return

        new_name, ok = QInputDialog.getText(
            self, "Renombrar Bitmap",
            f"Asigna un nombre descriptivo para '{fname}':",
            text=current_name
        )
        if ok and new_name.strip():
            new_name = new_name.strip()
            custom_names = {}
            if BITMAP_NAMES_FILE.exists():
                try:
                    with open(BITMAP_NAMES_FILE, 'r', encoding='utf-8') as f:
                        custom_names = json.load(f)
                except Exception:
                    custom_names = {}
            custom_names[fname] = new_name
            BITMAP_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BITMAP_NAMES_FILE, 'w', encoding='utf-8') as f:
                json.dump(custom_names, f, indent=2, ensure_ascii=False)

            self.gallery_list.reload_items()
            self._filter_gallery()

            if getattr(self, 'current_sheet_data', None):
                self.current_sheet_data['friendly_name'] = new_name
                self.btn_back_to_gallery.setText(f"⬅ Volver a Galería (Viéndose: {fname} - '{new_name}')")

            QMessageBox.information(self, "Bitmap Renombrado", f"Nombre guardado para '{fname}': {new_name}")

    def _on_tile_cutter_selected(self, tile_info: dict):
        """Maneja la selección interactiva de un tile en DynamicTileCutter."""
        self.sel_tile = tile_info
        r = tile_info.get('row', 0)
        c = tile_info.get('col', 0)
        sheet = tile_info.get('sheet', '')
        cad_id = tile_info.get('cad_id')
        w = tile_info.get('w', 24)
        h = tile_info.get('h', 24)

        cad_str = f" | ⚡ Asignado a CAD [{cad_id}]" if cad_id is not None else " | <i>(Sin asignar)</i>"
        self.tile_label.setText(
            f"Tile seleccionado: <b>{sheet}</b> [Fila {r}, Col {c}] ({w}x{h} px){cad_str}"
        )

        if cad_id is not None:
            for i in range(self.cad_list.count()):
                it = self.cad_list.item(i)
                d = it.data(Qt.UserRole)
                if d and str(d.get('CAD_ID')) == str(cad_id):
                    self.cad_list.blockSignals(True)
                    self.cad_list.setCurrentRow(i)
                    self.cad_list.scrollToItem(it)
                    self.cad_list.blockSignals(False)
                    self.on_cad_selected(it)
                    break

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

            # Asignar icono de miniatura si existe tile asociado
            tile_pix = self.get_tile_pixmap_for_cad(tid)
            if tile_pix and not tile_pix.isNull():
                scaled = tile_pix.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                list_item.setIcon(QIcon(scaled))
            
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
        name = item.get('Nombre_Original_EXE', '')
        subtipo = item.get('Subtipo', '-')
        term = item.get('Terminales', '-')
        
        simu_key = self.get_simucraft_equivalent(tid)
        simu_str = f"✔ {simu_key} (Vinculado a SimuCraft)" if simu_key else "⚠ Sin componente nativo directo"

        map_entry = self.map.get(self.cur_key) or self.map.get(tid)
        qet_str = f"✔ {map_entry.get('qet_file')}" if (map_entry and map_entry.get('qet_file')) else "Sin archivo QET (.elmt) asignado"
        
        info_lines = [
            f"ID CAD: [{tid:>5}] | Categoria: {cat}",
            f"Nombre Oficial: {name}"
        ]

        if cat == 'Virtual_2D' or 'bitmap' in name.lower():
            info_lines.append("ℹ TIPO: Sprite Gráfico de Laboratorio Virtual 2D (Entorno Físico)")
            info_lines.append("ℹ CORRELACIÓN: No aplica a esquemáticos QET (es un elemento visual de CADe SIMU)")
        else:
            info_lines.append(f"SimuCraft Nativo: {simu_str}")
            info_lines.append(f"Mapeo QET: {qet_str}")

        info_lines.append(f"Subtipo: {subtipo} | Terminales: {term}")
        info_lines.append(f"Descripción: {item.get('Descripcion', '-')}")
        
        self.cad_info.setText("\n".join(info_lines))

        # Actualizar tarjeta del panel derecho
        self.cad_summary_card.setText(
            f"<b style='color: #4af626; font-size: 14px;'>[{tid}] {name}</b><br>"
            f"<span style='color: #89b4fa;'>Categoría:</span> {cat} | "
            f"<span style='color: #89b4fa;'>Subtipo:</span> {subtipo} | "
            f"<span style='color: #89b4fa;'>Terminales:</span> {term}"
        )

        # Sincronizar combobox SimuCraft
        self.simu_comp_combo.blockSignals(True)
        if simu_key:
            idx = self.simu_comp_combo.findData(simu_key)
            if idx >= 0:
                self.simu_comp_combo.setCurrentIndex(idx)
            else:
                self.simu_comp_combo.setCurrentIndex(0)
        else:
            self.simu_comp_combo.setCurrentIndex(0)
        self.simu_comp_combo.blockSignals(False)

        # Actualizar vista previa vectorial
        self.update_simucraft_preview(simu_key)

        # Actualizar estado del tile asignado
        self.update_assigned_tile_display(tid)

    def render_simucraft_preview(self, comp_key: str) -> QPixmap:
        """Renderiza una vista previa gráfica de alta fidelidad para el componente SimuCraft."""
        pix = QPixmap(340, 200)
        pix.fill(QColor("#1e1e2e"))
        if not comp_key or comp_key not in STANDARD_COMPONENTS:
            p = QPainter(pix)
            p.setPen(QColor("#888888"))
            p.drawText(pix.rect(), Qt.AlignCenter, f"Sin representación vectorial\n({comp_key or 'Sin componente'})")
            p.end()
            return pix

        comp_def = STANDARD_COMPONENTS[comp_key]
        scene = QGraphicsScene()
        items = create_standard_primitives(comp_key, comp_def)
        for it in items:
            scene.addItem(it)

        # Agregar representación de bornes y terminales
        terminals = comp_def.get('visual', {}).get('terminals', [])
        for t in terminals:
            tx = float(t.get('x', 0.0))
            ty = float(t.get('y', 0.0))
            tid = t.get('id', '')
            c = scene.addEllipse(tx - 4, ty - 4, 8, 8, QPen(QColor("#ff5722"), 1.5), QBrush(QColor("#ff9800")))
            c.setZValue(10)
            txt = scene.addSimpleText(tid, QFont("Monospace", 7, QFont.Bold))
            txt.setBrush(QBrush(QColor("#ffcc80")))
            txt.setPos(tx + 6, ty - 6)
            txt.setZValue(11)

        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor("#2a2b3d"), 1, Qt.DotLine))
        for gx in range(0, 340, 20):
            p.drawLine(gx, 0, gx, 200)
        for gy in range(0, 200, 20):
            p.drawLine(0, gy, 340, gy)

        items_rect = scene.itemsBoundingRect()
        if items_rect.width() > 0 and items_rect.height() > 0:
            items_rect.adjust(-15, -15, 15, 15)
            scene.render(p, QRectF(10, 10, 320, 180), items_rect)
        p.end()
        return pix

    def update_simucraft_preview(self, comp_key: str):
        """Actualiza el widget de vista previa vectorial de SimuCraft."""
        pix = self.render_simucraft_preview(comp_key)
        self.simu_preview_label.setPixmap(pix)
        if comp_key and comp_key in STANDARD_COMPONENTS:
            c_def = STANDARD_COMPONENTS[comp_key]
            n_terms = len(c_def.get('visual', {}).get('terminals', []))
            self.simu_elements_info.setText(
                f"⚡ {c_def.get('name', comp_key)} • {n_terms} terminales • Tipo: {c_def.get('type', 'generic')}"
            )
        elif self.cur_item and (self.cur_item.get('Categoria') == 'Virtual_2D' or 'bitmap' in self.cur_item.get('Nombre_Original_EXE', '').lower()):
            self.simu_elements_info.setText("ℹ Elemento de Laboratorio Virtual 2D (Sprite de hardware / entorno físico)")
        else:
            self.simu_elements_info.setText("⚠ Sin componente SimuCraft nativo asignado")

    def update_assigned_tile_display(self, cad_id: str):
        """Muestra el tile actualmente asociado al CAD_ID con miniatura y detalles."""
        cad_id = str(cad_id)
        pix = self.get_tile_pixmap_for_cad(cad_id)
        if pix and not pix.isNull():
            scaled = pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.assigned_tile_preview.setPixmap(scaled)

            t_info = None
            if cad_id in self.cad_to_tile:
                _, t_info = self.cad_to_tile[cad_id]
            elif self.cur_key in self.map and self.map[self.cur_key].get('tile'):
                t_info = self.map[self.cur_key]['tile']

            sheet = t_info.get('sheet') if t_info else ''
            bmp_id = t_info.get('bitmap') if t_info else ''
            sheet_txt = sheet or (f"bitmap_{bmp_id}.bmp" if bmp_id is not None else "Lámina")
            r = t_info.get('row', 0) if t_info else 0
            c = t_info.get('col', 0) if t_info else 0
            self.assigned_tile_label.setText(
                f"<b>Tile asignado:</b> {sheet_txt} [Fila {r}, Col {c}]<br>"
                f"<span style='color: #2ecc71;'>✔ Vinculado a CAD [{cad_id}]</span>"
            )
        else:
            blank = QPixmap(36, 36)
            blank.fill(QColor("#252830"))
            p = QPainter(blank)
            p.setPen(QColor("#666666"))
            p.drawRect(0, 0, 35, 35)
            p.drawText(blank.rect(), Qt.AlignCenter, "—")
            p.end()
            self.assigned_tile_preview.setPixmap(blank)
            self.assigned_tile_label.setText(
                "<b>Tile asignado:</b> <i>Ninguno</i><br>"
                "<span style='color: #f39c12;'>⚠ Selecciona un tile en el centro y pulsa 'Vincular Tile'</span>"
            )

    def update_cad_list_icon(self, cad_id: str):
        """Actualiza el icono del elemento en la lista de símbolos CAD."""
        cad_id = str(cad_id)
        for i in range(self.cad_list.count()):
            it = self.cad_list.item(i)
            d = it.data(Qt.UserRole)
            if d and str(d.get('CAD_ID')) == cad_id:
                tile_pix = self.get_tile_pixmap_for_cad(cad_id)
                if tile_pix and not tile_pix.isNull():
                    scaled = tile_pix.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    it.setIcon(QIcon(scaled))
                else:
                    it.setIcon(QIcon())
                break

    def assign_selected_tile_to_cad(self):
        """Vincula el tile seleccionado en DynamicTileCutter al CAD_ID activo."""
        if not self.cur_item:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un símbolo CAD en la lista izquierda primero.")
            return
        if not self.sel_tile:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un tile en la lámina del panel central.")
            return

        cad_id = self.cur_item['CAD_ID']
        cad_name = self.cur_item.get('Nombre_Original_EXE', '')
        cat = self.cur_item.get('Categoria', '')
        subtipo = self.cur_item.get('Subtipo', '')

        bmp_id = self.sel_tile.get('bmp_id')
        row = self.sel_tile.get('row', 0)
        col = self.sel_tile.get('col', 0)
        sheet = self.sel_tile.get('sheet', '')
        key = self.sel_tile.get('key') or f"{bmp_id}_{row:02d}_{col:02d}"

        old_cad = self.tile_to_cad.get(key, {}).get('cad_id')
        if old_cad and old_cad != cad_id:
            ret = QMessageBox.question(
                self, "Confirmar Reasignación",
                f"Este tile ya estaba asignado a CAD [{old_cad}]. ¿Deseas reasignarlo a [{cad_id}] {cad_name}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return

        tile_entry = {
            'cad_id': cad_id,
            'name': cad_name,
            'category': cat,
            'subtipo': subtipo,
            'bitmap': bmp_id,
            'row': row,
            'col': col,
            'sheet': sheet,
            'x': self.sel_tile.get('x'),
            'y': self.sel_tile.get('y'),
            'w': self.sel_tile.get('w', 24),
            'h': self.sel_tile.get('h', 24)
        }
        self.tile_to_cad[key] = tile_entry
        self.cad_to_tile[str(cad_id)] = (key, tile_entry)

        if self.cur_key not in self.map:
            self.map[self.cur_key] = {
                'cad_key': self.cur_key,
                'cad_id': cad_id,
                'cad_name': cad_name,
                'category': cat,
                'subtype': subtipo
            }
        self.map[self.cur_key]['tile'] = self.sel_tile
        comp_key = self.simu_comp_combo.currentData()
        if comp_key:
            self.map[self.cur_key]['component_key'] = comp_key

        self.save_tile_map()
        self.save_mapping()

        self.update_assigned_tile_display(str(cad_id))
        self.update_cad_list_icon(str(cad_id))

        self.tile_cutter.canvas.tile_to_cad = self.tile_to_cad
        self.tile_cutter.canvas.update()

        QMessageBox.information(
            self, "Tile Vinculado",
            f"Tile '{key}' vinculado exitosamente con CAD [{cad_id}] {cad_name}."
        )

    def unbind_tile_from_cad(self):
        """Desvincula el tile gráfico del CAD_ID activo."""
        if not self.cur_item:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un símbolo CAD en la lista izquierda.")
            return

        cad_id = str(self.cur_item['CAD_ID'])
        found_key = None
        if cad_id in self.cad_to_tile:
            found_key, _ = self.cad_to_tile[cad_id]
            del self.cad_to_tile[cad_id]

        if found_key and found_key in self.tile_to_cad:
            del self.tile_to_cad[found_key]

        keys_to_del = [k for k, v in self.tile_to_cad.items() if str(v.get('cad_id')) == cad_id]
        for k in keys_to_del:
            del self.tile_to_cad[k]

        if self.cur_key in self.map and 'tile' in self.map[self.cur_key]:
            del self.map[self.cur_key]['tile']

        self.save_tile_map()
        self.save_mapping()

        self.update_assigned_tile_display(cad_id)
        self.update_cad_list_icon(cad_id)

        self.tile_cutter.canvas.tile_to_cad = self.tile_to_cad
        self.tile_cutter.canvas.update()

        QMessageBox.information(self, "Tile Desvinculado", f"Tile desvinculado del símbolo CAD [{cad_id}].")

    def save_tile_map(self):
        """Guarda el mapa de tiles a CAD_ID en disco."""
        try:
            TILE_TO_CAD_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TILE_TO_CAD_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.tile_to_cad, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando tile_to_cad_id.json: {e}")

    def _on_simu_comp_changed(self):
        """Maneja el cambio manual de componente SimuCraft en el combo."""
        comp_key = self.simu_comp_combo.currentData() or ""
        self.update_simucraft_preview(comp_key)
        if self.cur_item and comp_key:
            cad_id = str(self.cur_item['CAD_ID'])
            if self.cur_key not in self.map:
                self.map[self.cur_key] = {
                    'cad_key': self.cur_key,
                    'cad_id': self.cur_item['CAD_ID'],
                    'cad_name': self.cur_item.get('Nombre_Original_EXE', ''),
                    'category': self.cur_item.get('Categoria', ''),
                    'subtype': self.cur_item.get('Subtipo', '')
                }
            self.map[self.cur_key]['component_key'] = comp_key
            self.dispatch_table[cad_id] = {
                'component_key': comp_key,
                'name': self.cur_item.get('Nombre_Original_EXE', '')
            }

    def _auto_detect_simu_component(self):
        """Auto-detecta el componente SimuCraft correspondiente."""
        if not self.cur_item:
            return
        cad_id = str(self.cur_item['CAD_ID'])
        simu_key = self.get_simucraft_equivalent(cad_id)
        if simu_key:
            idx = self.simu_comp_combo.findData(simu_key)
            if idx >= 0:
                self.simu_comp_combo.setCurrentIndex(idx)
                QMessageBox.information(self, "Detectado", f"Componente SimuCraft detectado: {simu_key}")
            else:
                QMessageBox.warning(self, "No encontrado", f"Clave '{simu_key}' no está en la lista estándar.")
        else:
            QMessageBox.information(self, "Sin coincidencia", "No se encontró un componente SimuCraft directo.")

    def open_qet_browser_dialog(self):
        """Abre el diálogo modal de exploración e importación del catálogo QET."""
        try:
            from .qet_browser_dialog import QETLibraryBrowserDialog
            dlg = QETLibraryBrowserDialog(self)
            if dlg.exec():
                sel_path = dlg.get_selected_qet_path()
                if sel_path and self.cur_item:
                    cad_id = str(self.cur_item['CAD_ID'])
                    self.map[self.cur_key]['qet_file'] = Path(sel_path).name
                    self.map[self.cur_key]['qet_path'] = sel_path
                    self.save_mapping()
                    QMessageBox.information(self, "QET Asignado", f"Archivo QET asignado a CAD [{cad_id}]: {Path(sel_path).name}")
        except Exception as e:
            QMessageBox.information(self, "Biblioteca QET", f"Explorador QET: {e}")

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
        """Abre el componente SimuCraft activo en Symbol Studio con todas sus primitivas vectoriales."""
        if not self.cur_item:
            if self.cad_list.count() > 0:
                self.cad_list.setCurrentRow(0)
                self.on_cad_selected(self.cad_list.currentItem())

        cad_name = self.cur_item.get('Nombre_Original_EXE', 'simbolo_cad') if self.cur_item else "nuevo_simbolo"
        cad_id = str(self.cur_item['CAD_ID']) if self.cur_item else "0"
        comp_key = self.simu_comp_combo.currentData() if hasattr(self, 'simu_comp_combo') else ""
        if not comp_key and self.cur_item:
            comp_key = self.get_simucraft_equivalent(cad_id)

        self._skip_next_tab_sync = True
        try:
            self.main_tabs.setCurrentIndex(1)
            if comp_key and comp_key in STANDARD_COMPONENTS:
                self.studio_tab.load_component(comp_key)
                self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
                self.studio_tab.input_sym_name.setText(cad_name)
                self.studio_tab.info_status.setText(
                    f"🎨 Componente SimuCraft '{comp_key}' cargado con sus primitivas vectoriales para CAD [{cad_id}]"
                )
            else:
                self.studio_tab.load_component('motor_3p')
                self.studio_tab.input_sym_id.setText(f"cad_{cad_id}")
                self.studio_tab.input_sym_name.setText(cad_name)
        finally:
            self._skip_next_tab_sync = False

    def save_mapping(self):
        """Persiste los mapeos manuales y la tabla de despacho."""
        mapping_path = MANUAL_MAPPING_PATH
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.map, f, indent=2, ensure_ascii=False)

        if hasattr(self, 'dispatch_table') and self.dispatch_table:
            DISPATCH_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DISPATCH_TABLE_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.dispatch_table, f, indent=2, ensure_ascii=False)

        QMessageBox.information(self, "Mapeo Guardado", "Mapeos guardados correctamente en symbol_mapping_manual.json")

    def export_csv(self):
        default_export = BASE_PATH / 'data' / 'mappings' / 'mapeo_simbolos_export.csv'
        out_path, _ = QFileDialog.getSaveFileName(self, "Exportar Mapeo CSV", str(default_export), "CSV (*.csv)")
        if out_path:
            with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['CAD_KEY', 'CAD_ID', 'NOMBRE', 'CATEGORIA', 'SUBTIPO', 'SIMUCRAFT_KEY', 'TILE_SHEET', 'TILE_ROW', 'TILE_COL'])
                for k, v in sorted(self.map.items()):
                    tile = v.get('tile') or {}
                    writer.writerow([
                        v.get('cad_key', k),
                        v.get('cad_id', ''),
                        v.get('cad_name', ''),
                        v.get('category', ''),
                        v.get('subtype', ''),
                        v.get('component_key', ''),
                        tile.get('sheet', ''),
                        tile.get('row', ''),
                        tile.get('col', '')
                    ])
            QMessageBox.information(self, "Exportado", f"Mapeo exportado exitosamente a:\n{out_path}")


