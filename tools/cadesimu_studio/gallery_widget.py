"""
Widget de galería visual / biblioteca de miniaturas de bitmaps de CADe SIMU.
"""
from pathlib import Path
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon
from PIL import Image as _PILImage

from .config import BMP_RESOURCE_DIR, KNOWN_BMP_IDS, SPLASH_FILES


class GalleryListWidget(QListWidget):
    """Galería de imágenes en miniatura categorizadas y filtrables."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(96, 96))
        self.setGridSize(QSize(116, 128))
        self.setSpacing(6)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setStyleSheet("""
            QListWidget {
                background: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
            }
            QListWidget::item {
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
                background: #1e1e2e;
            }
            QListWidget::item:hover {
                border: 1px solid #89b4fa;
                background: #313244;
            }
            QListWidget::item:selected {
                border: 2px solid #2ecc71;
                background: #253342;
                color: #ffffff;
            }
        """)
        self.all_gallery_items = []
        self._load_items()

    def _load_items(self):
        self.all_gallery_items = []
        if not BMP_RESOURCE_DIR.exists():
            return

        for bmp_path in sorted(BMP_RESOURCE_DIR.glob('*.bmp')):
            try:
                with _PILImage.open(bmp_path) as img:
                    w, h = img.size
            except Exception:
                continue

            fname = bmp_path.name
            if h <= 25:
                cat = "🛠 Toolbars GUI (21px)"
                desc = f"Toolbar ({w // 21} botones)" if h == 21 else f"Toolbar ({w}x{h})"
            elif fname in KNOWN_BMP_IDS:
                cat = "📋 Hojas de Tiles / PLC"
                desc = "Carátula PLC / Lámina de Símbolos"
            elif fname in SPLASH_FILES:
                cat = "ℹ Splash & Acerca de"
                desc = "Pantalla de Inicio / Créditos"
            else:
                cat = "🖼 Vistas 2D y 3D de hardware"
                desc = f"Componente ({w}x{h}px)"

            item_data = {
                'path': str(bmp_path),
                'filename': fname,
                'category': cat,
                'width': w,
                'height': h,
                'desc': desc,
                'bmp_id': KNOWN_BMP_IDS.get(fname)
            }
            self.all_gallery_items.append(item_data)

    def filter_items(self, selected_category: str, query: str):
        """Filtra y recarga la visualización de los thumbnails según categoría y texto."""
        self.clear()
        query = query.lower().strip()

        for d in self.all_gallery_items:
            if selected_category != "Todas las imágenes" and d['category'] != selected_category:
                continue
            if query and (query not in d['filename'].lower() and query not in d['desc'].lower()):
                continue

            label = f"{d['filename']}\n{d['width']}x{d['height']}"
            it = QListWidgetItem(label)

            # Generar icono centrado en canvas de 96x96
            pix = QPixmap(d['path'])
            cell = QPixmap(96, 96)
            cell.fill(QColor("#1e1e2e"))
            p = QPainter(cell)
            p.setRenderHint(QPainter.Antialiasing, True)

            if not pix.isNull():
                thumb = pix.scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ox = (96 - thumb.width()) // 2
                oy = (96 - thumb.height()) // 2
                p.drawPixmap(ox, oy, thumb)
            else:
                try:
                    pil_img = _PILImage.open(d['path']).convert('RGB')
                    pil_img.thumbnail((88, 88))
                    tmp_t = Path('/tmp') / f"thumb_{d['filename']}.png"
                    pil_img.save(str(tmp_t))
                    thumb = QPixmap(str(tmp_t))
                    ox = (96 - thumb.width()) // 2
                    oy = (96 - thumb.height()) // 2
                    p.drawPixmap(ox, oy, thumb)
                    tmp_t.unlink(missing_ok=True)
                except Exception:
                    pass

            # Borde indicador por categoría
            if d['category'] == "📋 Hojas de Tiles / PLC":
                p.setPen(QPen(QColor("#89b4fa"), 2))
                p.drawRect(1, 1, 94, 94)
            elif d['category'] == "🛠 Toolbars GUI (21px)":
                p.setPen(QPen(QColor("#f9e2af"), 1))
                p.drawRect(1, 1, 94, 94)

            p.end()
            it.setIcon(QIcon(cell))
            it.setData(Qt.UserRole, d)
            it.setToolTip(f"{d['filename']}\n{d['category']}\n{d['desc']}\nDimensiones: {d['width']}x{d['height']}px")
            self.addItem(it)

