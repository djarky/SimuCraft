"""
Diálogo Modal de Exploración y Selección de la Biblioteca QElectroTech (.elmt).

Permite:
- Navegación por el árbol de categorías nativo de QET (carpetas reales).
- Búsqueda reactiva por nombre de archivo o etiqueta en español/inglés/francés.
- Vista previa vectorial SVG de alta definición.
- Inspección de bornes y dimensiones originales del elemento.
- Inserción directa en el lienzo del Symbol Studio o asignación en el Mapper.
"""
import os
import csv
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QByteArray, QRectF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from .config import BASE_PATH, QET_CATALOG_CSV_PATH
try:
    from src.qet.parser import QETParser
    PARSER = QETParser()
except Exception:
    PARSER = None


QET_ELEMENTS_DIRS = [
    Path('/home/vibecode/DevS/qelectrotech-elements/elements'),
    BASE_PATH / 'elements'
]


class QETLibraryBrowserDialog(QDialog):
    """Diálogo modal para explorar la biblioteca completa de símbolos QET."""

    def __init__(self, parent=None, initial_search: str = ""):
        super().__init__(parent)
        self.setWindowTitle("📦 Biblioteca de Símbolos QElectroTech (.elmt)")
        self.resize(1100, 720)
        self.setMinimumSize(850, 550)

        self.selected_file_path: Optional[str] = None
        self.elements_root: Optional[Path] = None
        for d in QET_ELEMENTS_DIRS:
            if d.exists() and d.is_dir():
                self.elements_root = d
                break

        self.catalog_data: List[dict] = []
        self._load_catalog_csv()

        self.init_ui(initial_search)
        self.populate_category_tree()

        if initial_search:
            self.search_input.setText(initial_search)
            self._on_search_changed(initial_search)

    def _load_catalog_csv(self):
        """Carga el catálogo CSV si existe para búsquedas rápidas."""
        csv_path = QET_CATALOG_CSV_PATH
        if not csv_path.exists():
            csv_path = BASE_PATH / 'qet_symbols_catalog.csv'
        if csv_path.exists():
            try:
                with open(csv_path, encoding='utf-8-sig') as f:
                    for row in csv.DictReader(f):
                        if row.get('Filename'):
                            self.catalog_data.append(row)
            except Exception as e:
                print(f"Error cargando catálogo CSV QET: {e}")

    def init_ui(self, initial_search: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Barra Superior: Buscador ──────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>🔍 Buscar Símbolo:</b>"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe nombre o palabra clave (ej: motor, contactor, bouton, relay, voyant)...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_input, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #89b4fa; font-weight: bold;")
        top_bar.addWidget(self.lbl_count)

        layout.addLayout(top_bar)

        # ── Splitter Principal: Árbol/Lista Izquierda y Vista Previa Derecha ────
        splitter = QSplitter(Qt.Horizontal)

        # Panel Izquierdo: Árbol de Carpetas + Lista de Archivos
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.cat_tree = QTreeWidget()
        self.cat_tree.setHeaderLabel("Categorías QElectroTech")
        self.cat_tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.cat_tree, 1)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_file_item_clicked)
        self.file_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        left_layout.addWidget(self.file_list, 1)

        splitter.addWidget(left_widget)

        # Panel Derecho: Ficha del Símbolo + Previsualización SVG
        right_box = QGroupBox("Vista Previa & Especificaciones")
        right_layout = QVBoxLayout(right_box)
        right_layout.setSpacing(8)

        self.preview_label = QLabel("Selecciona un archivo .elmt")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 320)
        self.preview_label.setStyleSheet("background: #ffffff; border: 2px solid #45475a; border-radius: 6px;")
        right_layout.addWidget(self.preview_label, 1)

        self.info_card = QLabel("Detalles del símbolo:")
        self.info_card.setStyleSheet("background: #1e1e2e; color: #cdd6f4; padding: 10px; border-radius: 4px; font-size: 12px;")
        self.info_card.setWordWrap(True)
        right_layout.addWidget(self.info_card)

        # Botones de Acción
        action_bar = QHBoxLayout()
        self.btn_insert = QPushButton("📥 Cargar en Lienzo")
        self.btn_insert.setStyleSheet("background: #2e7d32; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        self.btn_insert.clicked.connect(self._accept_selection)
        self.btn_insert.setEnabled(False)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setStyleSheet("background: #555555; color: white; padding: 8px 16px; border-radius: 4px;")
        btn_cancel.clicked.connect(self.reject)

        action_bar.addStretch()
        action_bar.addWidget(self.btn_insert)
        action_bar.addWidget(btn_cancel)
        right_layout.addLayout(action_bar)

        splitter.addWidget(right_box)
        splitter.setSizes([480, 560])
        layout.addWidget(splitter)

    # ── Población del Árbol de Carpetas ──────────────────────────────────────

    def populate_category_tree(self):
        self.cat_tree.clear()
        if not self.elements_root or not self.elements_root.exists():
            item = QTreeWidgetItem(["No se encontró la carpeta de elementos QET"])
            self.cat_tree.addTopLevelItem(item)
            return

        def add_nodes(parent_item, dir_path: Path):
            subdirs = sorted([d for d in dir_path.iterdir() if d.is_dir() and not d.name.startswith('.')])
            for sd in subdirs:
                # Contar archivos .elmt dentro
                count = len(list(sd.glob('*.elmt')))
                txt = f"{sd.name} ({count})" if count > 0 else sd.name
                node = QTreeWidgetItem([txt])
                node.setData(0, Qt.UserRole, str(sd))
                if parent_item is None:
                    self.cat_tree.addTopLevelItem(node)
                else:
                    parent_item.addChild(node)
                # Recursivo si tiene subcarpetas
                if any(child.is_dir() for child in sd.iterdir()):
                    add_nodes(node, sd)

        add_nodes(None, self.elements_root)
        self.cat_tree.expandToDepth(0)

    def _on_tree_item_clicked(self, tree_item, column):
        dir_path = tree_item.data(0, Qt.UserRole)
        if not dir_path or not os.path.isdir(dir_path):
            return
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        self.file_list.clear()
        p = Path(dir_path)
        elmts = sorted(list(p.glob('*.elmt')))
        self.lbl_count.setText(f"{len(elmts)} archivos en '{p.name}'")

        for f in elmts:
            it = QListWidgetItem(f.name)
            it.setData(Qt.UserRole, str(f))
            self.file_list.addItem(it)

        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)
            self._on_file_item_clicked(self.file_list.item(0))

    # ── Búsqueda Reactiva ───────────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        query = text.strip().lower()
        self.file_list.clear()
        if not query:
            self.lbl_count.setText("")
            return

        matches = []
        if self.catalog_data:
            for r in self.catalog_data:
                fname = r.get('Filename', '').lower()
                rel = r.get('Rel_Path', '').lower()
                if query in fname or query in rel:
                    matches.append((r.get('Filename'), r.get('Full_Path')))
                    if len(matches) >= 150:
                        break
        elif self.elements_root and self.elements_root.exists():
            for f in self.elements_root.rglob('*.elmt'):
                if query in f.name.lower():
                    matches.append((f.name, str(f)))
                    if len(matches) >= 150:
                        break

        self.lbl_count.setText(f"{len(matches)} coincidencias encontradas")
        for fname, fpath in matches:
            it = QListWidgetItem(fname)
            it.setData(Qt.UserRole, fpath)
            self.file_list.addItem(it)

        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)
            self._on_file_item_clicked(self.file_list.item(0))

    # ── Selección y Previsualización ─────────────────────────────────────────

    def _on_file_item_clicked(self, list_item):
        if not list_item:
            return
        fpath = list_item.data(Qt.UserRole)
        if not fpath or not os.path.exists(fpath):
            self.preview_label.setText(f"Archivo no encontrado:\n{list_item.text()}")
            self.btn_insert.setEnabled(False)
            return

        self.selected_file_path = fpath
        self.btn_insert.setEnabled(True)
        self._render_preview(fpath)

    def _on_file_double_clicked(self, list_item):
        self._on_file_item_clicked(list_item)
        if self.selected_file_path:
            self._accept_selection()

    def _render_preview(self, file_path: str):
        """Renderiza la previsualización SVG del archivo .elmt seleccionado."""
        if not PARSER:
            self.preview_label.setText("Módulo QETParser no disponible")
            return

        try:
            svg = PARSER.elmt_to_svg(file_path)
            symbol_data = PARSER.parse_symbol(file_path)

            if svg:
                if '<svg' not in svg:
                    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">{svg}</svg>'
                renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
                if renderer.isValid():
                    pix = QPixmap(320, 320)
                    pix.fill(Qt.white)
                    painter = QPainter(pix)

                    sz = renderer.defaultSize()
                    w = float(sz.width()) if sz.width() > 0 else 40.0
                    h = float(sz.height()) if sz.height() > 0 else 40.0
                    scale = min(280.0 / w, 280.0 / h)
                    tw, th = w * scale, h * scale
                    tx = (320.0 - tw) / 2.0
                    ty = (320.0 - th) / 2.0
                    target_rect = QRectF(tx, ty, tw, th)

                    renderer.render(painter, target_rect)
                    painter.end()
                    self.preview_label.setPixmap(pix)
                else:
                    self.preview_label.setText("SVG no renderizable")

            # Actualizar ficha informativa
            names = symbol_data.get('names', {})
            friendly_name = names.get('es') or names.get('en') or names.get('fr') or Path(file_path).stem
            n_terms = len(symbol_data.get('terminals', []))
            w = symbol_data.get('width', '-')
            h = symbol_data.get('height', '-')

            self.info_card.setText(
                f"<b style='color: #4af626; font-size: 13px;'>{Path(file_path).name}</b><br>"
                f"<b>Nombre descriptivo:</b> {friendly_name}<br>"
                f"<b>Dimensiones originales:</b> {w} x {h} px<br>"
                f"<b>Terminales / Bornes:</b> {n_terms}<br>"
                f"<b>Ruta:</b> <span style='font-size: 10px; color: #888;'>{file_path}</span>"
            )
        except Exception as e:
            self.preview_label.setText(f"Error cargando previsualización:\n{e}")
            self.info_card.setText(f"Archivo: {Path(file_path).name}\nError: {e}")

    def _accept_selection(self):
        if self.selected_file_path and os.path.exists(self.selected_file_path):
            self.accept()
        else:
            QMessageBox.warning(self, "Atención", "Por favor selecciona un archivo .elmt válido.")

    def get_selected_qet_path(self) -> Optional[str]:
        return self.selected_file_path

