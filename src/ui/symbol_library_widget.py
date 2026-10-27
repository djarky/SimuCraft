"""
Panel de biblioteca de símbolos y componentes con vista previa en tiempo real.
Permite explorar componentes estándar, símbolos vectoriales de QElectroTech y esquemas de ejemplo.
"""
import os
import json
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit,
    QFrame, QStyleOptionGraphicsItem, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize, QPointF, QByteArray, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QIcon
from PySide6.QtSvg import QSvgRenderer

from ..components.standard_components import STANDARD_COMPONENTS, create_standard_component
from ..graphics.component_item import ComponentItem
from ..qet import QETLoader
from ..qet.parser import QETParser

# Cargar catálogo de símbolos de CADe SIMU
CADESIMU_CATALOG = {}
_catalog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cadesimu_symbol_catalog_detailed.json")
if os.path.exists(_catalog_path):
    try:
        with open(_catalog_path, 'r', encoding='utf-8') as f:
            for item in json.load(f):
                CADESIMU_CATALOG[item['type_id']] = item
    except Exception:
        pass

# Cargar librería completa estilo CADe SIMU
CADESIMU_LIBRARY_COMPLETE = {}
_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cadesimu_library_complete.json")
if os.path.exists(_lib_path):
    try:
        with open(_lib_path, 'r', encoding='utf-8') as f:
            CADESIMU_LIBRARY_COMPLETE = json.load(f)
    except Exception:
        pass

# Agrupación por categorías CADe SIMU
CADESIMU_CATEGORIES = {
    "Motor": [1000],
    "Contactor": [2001, 2006],
    "Bobina": [9000],
    "Contacto": [7000, 7001, 10050, 10051, 10060],
    "Pulsador": [8000, 8001, 8002, 8005],
    "Piloto/Lámpara": [9008],
    "Protección/Guardamotor": [5000, 5003, 5008, 8016, 8017, 8018, 8019],
    "Disyuntor/Magnetotérmico": [6002, 6007, 6008, 6009, 6010, 6011],
    "Temporizador": [7004, 9004],
    "PLC/Autómata": [10202],
    "Barras/Conexiones": [3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009],
    "Cables/Hilos": [4000, 4001, 4009, 4010, 4018, 4019],
}


def render_component_preview(
    defn: Dict[str, Any],
    size: int = 140,
    bg_color: Optional[QColor] = None,
    show_terminals: bool = True
) -> QPixmap:
    """Renderizar un componente estándar o QET en un QPixmap nítido con antialiasing."""
    pix = QPixmap(size, size)
    if bg_color is not None:
        pix.fill(bg_color)
    else:
        pix.fill(Qt.transparent)

    try:
        visual = defn.get('visual', {})
        # 1. Si es un símbolo QET con SVG
        if visual.get('elmt_path'):
            svg_content = visual.get('svg_content')
            if not svg_content and os.path.exists(visual['elmt_path']):
                svg_content = QETParser().elmt_to_svg(visual['elmt_path'])
                visual['svg_content'] = svg_content

            if svg_content:
                renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
                if renderer.isValid():
                    p = QPainter(pix)
                    p.setRenderHint(QPainter.Antialiasing, True)
                    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                    pad = 12
                    renderer.render(p, QRectF(pad, pad, size - pad * 2, size - pad * 2))
                    p.end()
                    return pix

        # 2. Componente estándar dibujado por ComponentItem
        item = ComponentItem(defn)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        br = item.boundingRect()
        if br.width() > 0 and br.height() > 0:
            padding = 18
            scale = min((size - padding * 2) / br.width(), (size - padding * 2) / br.height())
            painter.translate(size / 2.0, size / 2.0)
            painter.scale(scale, scale)
            painter.translate(-br.center().x(), -br.center().y())

        opt = QStyleOptionGraphicsItem()
        item.paint(painter, opt, None)

        if show_terminals:
            for term in getattr(item, 'terminals', []):
                painter.save()
                painter.translate(term.pos())
                term.paint(painter, opt, None)
                painter.restore()

        painter.end()
    except Exception as e:
        print(f"Error renderizando vista previa: {e}")
        painter = QPainter(pix)
        painter.setPen(QColor("#888888"))
        painter.drawText(pix.rect(), Qt.AlignCenter, "⚡")
        painter.end()

    return pix


class SymbolPreviewCard(QFrame):
    """Tarjeta interactiva que muestra la vista previa ampliada y ficha técnica del símbolo."""

    add_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_defn: Optional[Dict[str, Any]] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            SymbolPreviewCard {
                background: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
            QLabel {
                color: #cdd6f4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Encabezado
        header_layout = QHBoxLayout()
        lbl_title = QLabel("👁 Vista Previa")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #89b4fa; text-transform: uppercase;")
        header_layout.addWidget(lbl_title)

        self.lbl_tag_badge = QLabel("-")
        self.lbl_tag_badge.setStyleSheet("""
            background: #45475a;
            color: #f5e0dc;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_tag_badge)
        layout.addLayout(header_layout)

        # Cuadro de dibujo del símbolo con cuadrícula técnica sutil
        self.preview_box = QLabel()
        self.preview_box.setAlignment(Qt.AlignCenter)
        self.preview_box.setMinimumHeight(125)
        self.preview_box.setMaximumHeight(150)
        self.preview_box.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #45475a;
            border-radius: 6px;
        """)
        layout.addWidget(self.preview_box)

        # Metadatos del componente
        self.lbl_name = QLabel("Seleccione un símbolo")
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #cdd6f4;")
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name)

        self.lbl_type = QLabel("Categoría: -")
        self.lbl_type.setStyleSheet("font-size: 11px; color: #a6adc8;")
        layout.addWidget(self.lbl_type)

        self.lbl_terminals = QLabel("Bornes: -")
        self.lbl_terminals.setStyleSheet("font-size: 10px; color: #94e2d5;")
        self.lbl_terminals.setWordWrap(True)
        layout.addWidget(self.lbl_terminals)

        self.btn_add = QPushButton("➕ Añadir al Esquema")
        self.btn_add.setEnabled(False)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
        """)
        self.btn_add.clicked.connect(self._on_add_clicked)
        layout.addWidget(self.btn_add)

        self.lbl_hint = QLabel("💡 Clic simple para insertar con vista previa | ESC para salir")
        self.lbl_hint.setStyleSheet("font-size: 10px; color: #89dceb; font-style: italic;")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_hint)

    def set_component(self, defn: Optional[Dict[str, Any]]):
        """Actualizar la tarjeta con la información y dibujo del símbolo."""
        self.current_defn = defn
        if not defn:
            self.preview_box.clear()
            self.lbl_name.setText("Seleccione un símbolo")
            self.lbl_type.setText("Categoría: -")
            self.lbl_terminals.setText("Bornes: -")
            self.lbl_tag_badge.setText("-")
            self.btn_add.setEnabled(False)
            return

        name = defn.get('name', 'Componente')
        tag = defn.get('tag', '') or defn.get('tag_prefix', '')
        c_type = defn.get('type', 'desconocido')

        # Terminales
        visual = defn.get('visual', {})
        terminals = visual.get('terminals', [])
        term_names = [str(t.get('id', '')) for t in terminals if t.get('id')]
        terms_str = f"Bornes ({len(term_names)}): " + (", ".join(term_names) if term_names else "Sin bornes")

        self.lbl_name.setText(name)
        self.lbl_type.setText(f"Tipo: {c_type.capitalize()}")
        self.lbl_terminals.setText(terms_str)
        self.lbl_tag_badge.setText(tag if tag else "SYM")
        self.btn_add.setEnabled(True)

        # Generar vista previa con fondo blanco técnico
        pix = render_component_preview(defn, size=130, bg_color=QColor("#ffffff"), show_terminals=True)
        self.preview_box.setPixmap(pix)

    def _on_add_clicked(self):
        if self.current_defn:
            self.add_requested.emit(self.current_defn)


class SymbolLibraryWidget(QWidget):
    """Widget principal de la Biblioteca de Símbolos con pestañas y vista previa dinámica."""

    component_selected = Signal(dict)
    component_double_clicked = Signal(dict)
    example_double_clicked = Signal(str)

    def __init__(self, qet_loader: QETLoader, project_root: str, parent=None):
        super().__init__(parent)
        self.qet_loader = qet_loader
        self.project_root = project_root
        self.thumbnail_cache: Dict[str, QIcon] = {}
        self._all_qet_symbols: List[str] = []
        self._create_default_icons()
        self._setup_ui()
        self._populate_all()

    def _create_default_icons(self):
        # Icono por defecto elegante para símbolos QET
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor("#89b4fa"), 1.5))
        p.setBrush(QBrush(QColor("#313244")))
        p.drawRoundedRect(2, 2, 32, 32, 4, 4)
        p.setFont(QFont("Sans Serif", 9, QFont.Bold))
        p.setPen(QColor("#a6e3a1"))
        p.drawText(pix.rect(), Qt.AlignCenter, "⚡")
        p.end()
        self.default_qet_icon = QIcon(pix)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Splitter vertical que divide la lista de símbolos de la tarjeta de vista previa
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # Parte superior: pestañas de navegación
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #313244;
                border-radius: 4px;
                background: #181825;
            }
            QTabBar::tab {
                background: #1e1e2e;
                color: #a6adc8;
                padding: 6px 10px;
                border: 1px solid #313244;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #313244;
                color: #ffffff;
                font-weight: bold;
            }
        """)

        # 1. Pestaña Componentes Estándar (con categorías CADe SIMU)
        std_widget = QWidget()
        std_layout = QVBoxLayout(std_widget)
        std_layout.setContentsMargins(4, 4, 4, 4)
        std_layout.setSpacing(4)
        
        # Filtro por categoría (estilo CADe SIMU)
        self.std_cat_filter = QComboBox()
        self.std_cat_filter.setStyleSheet("""
            QComboBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #1e1e2e;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        self.std_cat_filter.addItem("Todas las categorías")
        # Añadir categorías estilo CADe SIMU
        for group, subcats in CADESIMU_LIBRARY_COMPLETE.items():
            for subcat in subcats.keys():
                self.std_cat_filter.addItem(f"{group} » {subcat}")
        for cat in CADESIMU_CATEGORIES.keys():
            self.std_cat_filter.addItem(cat)
        self.std_cat_filter.currentTextChanged.connect(self._filter_standard_by_category)
        std_layout.addWidget(self.std_cat_filter)
        
        self.std_list = QListWidget()
        self.std_list.setIconSize(QSize(36, 36))
        self.std_list.setStyleSheet(self._list_stylesheet())
        self.std_list.itemClicked.connect(self._on_std_item_clicked)
        self.std_list.currentItemChanged.connect(self._on_std_current_changed)
        self.std_list.itemDoubleClicked.connect(self._on_std_item_double_clicked)
        std_layout.addWidget(self.std_list)
        self.tabs.addTab(std_widget, "⚡ Bibliotecas")

        # 2. Pestaña QElectroTech
        qet_widget = QWidget()
        qet_layout = QVBoxLayout(qet_widget)
        qet_layout.setContentsMargins(4, 4, 4, 4)
        qet_layout.setSpacing(4)

        # Barra de búsqueda para los miles de símbolos
        self.qet_search = QLineEdit()
        self.qet_search.setPlaceholderText("🔍 Filtrar símbolos (motor, relé, etc.)...")
        self.qet_search.setClearButtonEnabled(True)
        self.qet_search.setStyleSheet("""
            QLineEdit {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
        """)
        self.qet_search.textChanged.connect(self._filter_qet_symbols)
        qet_layout.addWidget(self.qet_search)

        self.qet_list = QListWidget()
        self.qet_list.setIconSize(QSize(36, 36))
        self.qet_list.setStyleSheet(self._list_stylesheet())
        self.qet_list.itemClicked.connect(self._on_qet_item_clicked)
        self.qet_list.currentItemChanged.connect(self._on_qet_current_changed)
        self.qet_list.itemDoubleClicked.connect(self._on_qet_item_double_clicked)
        qet_layout.addWidget(self.qet_list)
        self.tabs.addTab(qet_widget, "🌐 QElectroTech")

        # 3. Pestaña Esquemas Ejemplo CADe SIMU
        ex_widget = QWidget()
        ex_layout = QVBoxLayout(ex_widget)
        ex_layout.setContentsMargins(4, 4, 4, 4)
        self.ex_list = QListWidget()
        self.ex_list.setIconSize(QSize(28, 28))
        self.ex_list.setStyleSheet(self._list_stylesheet())
        self.ex_list.itemDoubleClicked.connect(self._on_example_double_clicked)
        ex_layout.addWidget(self.ex_list)
        self.tabs.addTab(ex_widget, "📐 Ejemplos CAD")

        splitter.addWidget(self.tabs)

        # Parte inferior: Tarjeta de Vista Previa
        self.preview_card = SymbolPreviewCard()
        self.preview_card.add_requested.connect(self.component_selected.emit)
        self.preview_card.add_requested.connect(self.component_double_clicked.emit)
        splitter.addWidget(self.preview_card)

        # Proporciones iniciales del divisor (60% lista, 40% preview)
        splitter.setSizes([350, 240])

        main_layout.addWidget(splitter)

    def _list_stylesheet(self) -> str:
        return """
            QListWidget {
                background: #181825;
                color: #cdd6f4;
                border: none;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px 6px;
                border-radius: 4px;
                margin: 1px 0;
            }
            QListWidget::item:hover {
                background: #313244;
            }
            QListWidget::item:selected {
                background: #45475a;
                color: #ffffff;
                font-weight: bold;
            }
        """

    def _populate_all(self):
        self._populate_standard_components()
        self._populate_qet_symbols()
        self._populate_examples()

    def _populate_standard_components(self):
        self._all_std_items = []
        self.std_list.clear()
        for key, defn in STANDARD_COMPONENTS.items():
            pix = render_component_preview(defn, size=36, bg_color=QColor("#ffffff"), show_terminals=False)
            icon = QIcon(pix)
            tag_pref = defn.get('tag_prefix', '')
            name = defn.get('name', key)
            ctype = defn.get('type', '')

            # Mapear a categoría CADe SIMU
            category = "Otros"
            if ctype == 'motor':
                category = "Motor"
            elif ctype == 'contactor':
                category = "Contactor"
            elif ctype in ('contact_no', 'contact'):
                category = "Contacto"
            elif ctype == 'pushbutton':
                category = "Pulsador"
            elif ctype == 'lamp':
                category = "Piloto/Lámpara"
            elif ctype == 'relay':
                category = "Protección/Guardamotor"
            elif ctype in ('breaker', 'breaker_3p'):
                category = "Disyuntor/Magnetotérmico"
            elif ctype == 'power':
                category = "PLC/Autómata"
            elif ctype == 'neutral':
                category = "Barras/Conexiones"

            item = QListWidgetItem(icon, f"{name} ({tag_pref})")
            item.setData(Qt.UserRole, key)
            item.setData(Qt.UserRole + 1, category)
            self._all_std_items.append((key, defn, icon, category))
            self.std_list.addItem(item)

        if self.std_list.count() > 0:
            self.std_list.setCurrentRow(0)
            first_key = self.std_list.item(0).data(Qt.UserRole)
            self.preview_card.set_component(create_standard_component(first_key))

    def _filter_standard_by_category(self, category: str):
        self.std_list.clear()
        for key, defn, icon, cat in getattr(self, '_all_std_items', []):
            if category == "Todas las categorías":
                show = True
            elif "»" in category:
                group_sub = category.split(" » ")
                show = False
                if len(group_sub) == 2:
                    g, s = group_sub
                    # Mapear
                    if g == "Protección" and s in ["Disyuntor/Magnetotérmico", "Guardamotor", "Seccionador", "Interruptor Diferencial"] and cat in ["Disyuntor/Magnetotérmico", "Protección/Guardamotor"]:
                        show = True
                    elif g == "Maniobra" and s == "Contactor" and cat == "Contactor":
                        show = True
                    elif g == "Maniobra" and s == "Bobina" and key.startswith('contactor_coil'):
                        show = True
                    elif g == "Maniobra" and s == "Pulsador" and cat == "Pulsador":
                        show = True
                    elif g == "Maniobra" and s == "Final de Carrera":
                        show = False
                    elif g == "Receptores" and s == "Motor" and cat == "Motor":
                        show = True
                    elif g == "Receptores" and s == "Lámpara/Piloto" and cat == "Piloto/Lámpara":
                        show = True
                    elif g == "Auxiliares" and s == "Contacto Auxiliar" and cat == "Contacto":
                        show = True
                    elif g == "Auxiliares" and s == "Temporizador" and cat == "Temporizador":
                        show = True
                    elif g == "PLC/Automatismo" and cat == "PLC/Autómata":
                        show = True
                    elif g == "Distribución" and cat in ["Barras/Conexiones"]:
                        show = True
                    else:
                        show = cat == category
            else:
                show = cat == category
            
            if show:
                name = defn.get('name', key)
                tag_pref = defn.get('tag_prefix', '')
                new_item = QListWidgetItem(icon, f"{name} ({tag_pref})")
                new_item.setData(Qt.UserRole, key)
                new_item.setData(Qt.UserRole + 1, cat)
                self.std_list.addItem(new_item)
        if self.std_list.count() > 0:
            self.std_list.setCurrentRow(0)
            first_key = self.std_list.item(0).data(Qt.UserRole)
            self.preview_card.set_component(create_standard_component(first_key))

    def _populate_qet_symbols(self):
        self._all_qet_symbols = self.qet_loader.scan_available()
        self._filter_qet_symbols(self.qet_search.text())

    def _filter_qet_symbols(self, text: str):
        query = text.strip().lower()
        self.qet_list.clear()

        matches = []
        for path in self._all_qet_symbols:
            base = os.path.basename(path).lower()
            if not query or query in base or query in path.lower():
                matches.append(path)
                if len(matches) >= 60:
                    break

        for path in matches:
            base = os.path.basename(path).replace(".elmt", "").replace("_", " ")
            item = QListWidgetItem(self.default_qet_icon, base.capitalize())
            item.setData(Qt.UserRole, path)
            self.qet_list.addItem(item)

    def _populate_examples(self):
        examples_dir = os.path.join(self.project_root, "cadesimu", "examples")
        if os.path.isdir(examples_dir):
            files = sorted(os.listdir(examples_dir))
            for f in files:
                if f.endswith(".cad"):
                    pix = QPixmap(28, 28)
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    p.setRenderHint(QPainter.Antialiasing, True)
                    p.setPen(QPen(QColor("#89b4fa"), 2))
                    p.setBrush(QBrush(QColor("#1e1e2e")))
                    p.drawRoundedRect(2, 2, 24, 24, 4, 4)
                    p.setFont(QFont("Sans Serif", 7, QFont.Bold))
                    p.setPen(QColor("#cdd6f4"))
                    p.drawText(pix.rect(), Qt.AlignCenter, "CAD")
                    p.end()

                    item = QListWidgetItem(QIcon(pix), f"{f}")
                    item.setData(Qt.UserRole, os.path.join(examples_dir, f))
                    self.ex_list.addItem(item)

    def _on_std_item_clicked(self, item: QListWidgetItem):
        self._update_std_preview(item)
        key = item.data(Qt.UserRole)
        if key:
            defn = create_standard_component(key)
            if defn:
                self.component_selected.emit(defn)

    def _on_std_current_changed(self, current: Optional[QListWidgetItem], previous):
        if current:
            self._update_std_preview(current)

    def _update_std_preview(self, item: QListWidgetItem):
        key = item.data(Qt.UserRole)
        if key:
            defn = create_standard_component(key)
            self.preview_card.set_component(defn)

    def _on_std_item_double_clicked(self, item: QListWidgetItem):
        key = item.data(Qt.UserRole)
        if key:
            defn = create_standard_component(key)
            self.component_double_clicked.emit(defn)

    def _on_qet_item_clicked(self, item: QListWidgetItem):
        self._update_qet_preview(item)
        path = item.data(Qt.UserRole)
        if path:
            defn = self.qet_loader.load_symbol(path)
            if defn:
                self.component_selected.emit(defn)

    def _on_qet_current_changed(self, current: Optional[QListWidgetItem], previous):
        if current:
            self._update_qet_preview(current)

    def _update_qet_preview(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            defn = self.qet_loader.load_symbol(path)
            if defn:
                self.preview_card.set_component(defn)

    def _on_qet_item_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            defn = self.qet_loader.load_symbol(path)
            if defn:
                self.component_double_clicked.emit(defn)

    def _on_example_double_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            self.example_double_clicked.emit(path)
