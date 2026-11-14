"""
Widget interactivo para recorte y subdivisión dinámica de hojas de tiles y toolbars.

Permite:
- Desplazamiento dinámico de líneas de corte (guías) arrastrando con el ratón.
- Creación y eliminación de subdivisiones independientes (tamaños asimétricos por tile).
- Soporte para tiras 1D (toolbars) y cuadrículas 2D.
- Identificación visual de tiles mapeados ("usados") con overlay verde y badge de CAD_ID.
- Selección interactiva de tiles para vinculación a símbolos CADe SIMU.
- Persistencia de layouts en data/mappings/tileset_layouts.json.
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSpinBox, QMessageBox, QToolTip, QScrollArea, QMenu
)
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QFont, QCursor
)
from PIL import Image as _PILImage

from .config import BASE_PATH, DEFAULT_SCALE, DEFAULT_TILE_SIZE


LAYOUTS_PATH = BASE_PATH / 'data' / 'mappings' / 'tileset_layouts.json'


class DynamicTileCanvas(QWidget):
    """Lienzo que dibuja la hoja de imagen y las guías de corte interactivas."""

    tile_selected = Signal(dict)
    layout_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self._base_pix = QPixmap()
        self.img_path: str = ""
        self.bmp_id: Optional[int] = None
        self.scale: float = 2.0

        # Cortes en coordenadas originales de la imagen (píxeles reales)
        self.cuts_x: List[int] = []
        self.cuts_y: List[int] = []

        # Estado de interacción del ratón
        self._dragging_line: Optional[Tuple[str, int]] = None  # ('x', index) o ('y', index)
        self._hover_line: Optional[Tuple[str, int]] = None
        self._selected_line: Optional[Tuple[str, int]] = None

        self.selected_tile: Optional[Tuple[int, int]] = None  # (row, col)
        self.hovered_tile: Optional[Tuple[int, int]] = None

        # Datos de mapeo externo: tile_key -> info dict
        self.tile_to_cad: Dict[str, dict] = {}
        self.mapping: Dict[str, dict] = {}

    # ── Carga y Configuración ────────────────────────────────────────────────

    def load_image(self, img_path: str, bmp_id: Optional[int], layouts: dict):
        self.img_path = img_path
        self.bmp_id = bmp_id
        self.selected_tile = None
        self.hovered_tile = None
        self._selected_line = None

        # Cargar pixmap base con fallback de PIL
        self._base_pix = QPixmap(img_path)
        if self._base_pix.isNull():
            try:
                import tempfile
                pil = _PILImage.open(img_path).convert('RGB')
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                pil.save(tmp.name)
                tmp.close()
                self._base_pix = QPixmap(tmp.name)
                os.unlink(tmp.name)
            except Exception as e:
                print(f"Error cargando imagen {img_path}: {e}")
                self._base_pix = QPixmap()

        if self._base_pix.isNull():
            self.cuts_x = []
            self.cuts_y = []
            self.update()
            return

        w = self._base_pix.width()
        h = self._base_pix.height()

        # Cargar cortes guardados o calcular por defecto
        fname = Path(img_path).name
        saved = layouts.get(fname)
        if saved and 'cuts_x' in saved and 'cuts_y' in saved:
            self.cuts_x = sorted(list(set(int(x) for x in saved['cuts_x'] if 0 <= x <= w)))
            self.cuts_y = sorted(list(set(int(y) for y in saved['cuts_y'] if 0 <= y <= h)))
        else:
            self._generate_default_cuts(w, h)

        self._ensure_boundary_cuts(w, h)
        self._update_widget_size()
        self.update()

    def _ensure_boundary_cuts(self, w: int, h: int):
        if 0 not in self.cuts_x:
            self.cuts_x.insert(0, 0)
        if w not in self.cuts_x:
            self.cuts_x.append(w)
        if 0 not in self.cuts_y:
            self.cuts_y.insert(0, 0)
        if h not in self.cuts_y:
            self.cuts_y.append(h)
        self.cuts_x = sorted(list(set(self.cuts_x)))
        self.cuts_y = sorted(list(set(self.cuts_y)))

    def _generate_default_cuts(self, w: int, h: int):
        """Genera subdivisiones uniformes por defecto según sea 1D o 2D."""
        if h <= 25:
            # Tira 1D de botones de toolbar
            step = h if h > 0 else 21
            self.cuts_y = [0, h]
            self.cuts_x = [x for x in range(0, w + 1, step)]
            if w not in self.cuts_x:
                self.cuts_x.append(w)
        else:
            # Rejilla 2D estándar (24px)
            step = 24
            self.cuts_x = [x for x in range(0, w + 1, step)]
            self.cuts_y = [y for y in range(0, h + 1, step)]
            if w not in self.cuts_x:
                self.cuts_x.append(w)
            if h not in self.cuts_y:
                self.cuts_y.append(h)

    def set_scale(self, scale: float):
        self.scale = max(1.0, min(5.0, scale))
        self._update_widget_size()
        self.update()

    def _update_widget_size(self):
        if not self._base_pix.isNull():
            sw = int(self._base_pix.width() * self.scale)
            sh = int(self._base_pix.height() * self.scale)
            self.setFixedSize(sw, sh)

    # ── Métodos de Cortes Dinámicos ──────────────────────────────────────────

    def add_cut_x(self, x: Optional[int] = None):
        if self._base_pix.isNull():
            return
        w = self._base_pix.width()
        if x is None:
            # Insertar en medio del tile actualmente seleccionado o al centro
            if self.selected_tile and len(self.cuts_x) > 1:
                col = self.selected_tile[1]
                if col < len(self.cuts_x) - 1:
                    x = (self.cuts_x[col] + self.cuts_x[col + 1]) // 2
            if x is None:
                x = w // 2
        if 4 <= x <= w - 4 and x not in self.cuts_x:
            self.cuts_x.append(x)
            self.cuts_x.sort()
            self.layout_changed.emit()
            self.update()

    def add_cut_y(self, y: Optional[int] = None):
        if self._base_pix.isNull():
            return
        h = self._base_pix.height()
        if y is None:
            if self.selected_tile and len(self.cuts_y) > 1:
                row = self.selected_tile[0]
                if row < len(self.cuts_y) - 1:
                    y = (self.cuts_y[row] + self.cuts_y[row + 1]) // 2
            if y is None:
                y = h // 2
        if 4 <= y <= h - 4 and y not in self.cuts_y:
            self.cuts_y.append(y)
            self.cuts_y.sort()
            self.layout_changed.emit()
            self.update()

    def remove_selected_cut(self):
        if not self._selected_line:
            return
        axis, idx = self._selected_line
        if axis == 'x' and 0 < idx < len(self.cuts_x) - 1:
            self.cuts_x.pop(idx)
            self._selected_line = None
            self.layout_changed.emit()
            self.update()
        elif axis == 'y' and 0 < idx < len(self.cuts_y) - 1:
            self.cuts_y.pop(idx)
            self._selected_line = None
            self.layout_changed.emit()
            self.update()

    def reset_uniform(self, step_x: int, step_y: Optional[int] = None):
        if self._base_pix.isNull() or step_x <= 0:
            return
        w = self._base_pix.width()
        h = self._base_pix.height()
        self.cuts_x = [x for x in range(0, w + 1, step_x)]
        if w not in self.cuts_x:
            self.cuts_x.append(w)
        sy = step_y or (step_x if h > 25 else h)
        self.cuts_y = [y for y in range(0, h + 1, sy)]
        if h not in self.cuts_y:
            self.cuts_y.append(h)
        self.selected_tile = None
        self._selected_line = None
        self.layout_changed.emit()
        self.update()

    # ── Consultas Geométricas ────────────────────────────────────────────────

    def get_tile_rect(self, row: int, col: int) -> Optional[QRect]:
        if 0 <= col < len(self.cuts_x) - 1 and 0 <= row < len(self.cuts_y) - 1:
            x = self.cuts_x[col]
            y = self.cuts_y[row]
            w = self.cuts_x[col + 1] - x
            h = self.cuts_y[row + 1] - y
            return QRect(x, y, w, h)
        return None

    def get_tile_info(self, row: int, col: int) -> dict:
        r = self.get_tile_rect(row, col)
        if not r:
            return {}
        key = f"{self.bmp_id}_{row:02d}_{col:02d}" if self.bmp_id is not None else f"{Path(self.img_path).stem}_{row:02d}_{col:02d}"
        cad_info = self.tile_to_cad.get(key, {})
        cad_id = cad_info.get('cad_id')

        # Buscar si algún CADe SIMU tiene asignado este tile
        if cad_id is None:
            for k, info in self.tile_to_cad.items():
                if info.get('bitmap') == self.bmp_id and info.get('row') == row and info.get('col') == col:
                    cad_id = info.get('cad_id')
                    cad_info = info
                    break

        return {
            'key': key,
            'bitmap': self.bmp_id,
            'sheet': Path(self.img_path).name,
            'row': row,
            'col': col,
            'x': r.x(),
            'y': r.y(),
            'w': r.width(),
            'h': r.height(),
            'cad_id': cad_id,
            'cad_name': cad_info.get('name', ''),
            'cad_category': cad_info.get('category', ''),
        }

    def _find_line_at(self, pos: QPoint, threshold: int = 6) -> Optional[Tuple[str, int]]:
        """Determina si el cursor está sobre una línea de corte divisible."""
        sx = pos.x() / self.scale
        sy = pos.y() / self.scale

        # Verificar líneas X interiores (ignorar bordes 0 y N)
        for i in range(1, len(self.cuts_x) - 1):
            if abs(sx - self.cuts_x[i]) * self.scale <= threshold:
                return ('x', i)

        # Verificar líneas Y interiores
        for j in range(1, len(self.cuts_y) - 1):
            if abs(sy - self.cuts_y[j]) * self.scale <= threshold:
                return ('y', j)

        return None

    def _find_tile_at(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        sx = int(pos.x() / self.scale)
        sy = int(pos.y() / self.scale)
        col = -1
        for i in range(len(self.cuts_x) - 1):
            if self.cuts_x[i] <= sx < self.cuts_x[i + 1]:
                col = i
                break
        row = -1
        for j in range(len(self.cuts_y) - 1):
            if self.cuts_y[j] <= sy < self.cuts_y[j + 1]:
                row = j
                break
        if row >= 0 and col >= 0:
            return (row, col)
        return None

    # ── Eventos de Ratón ─────────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()

        # Si estamos arrastrando una línea divisoria
        if self._dragging_line:
            axis, idx = self._dragging_line
            if axis == 'x':
                val = int(pos.x() / self.scale)
                min_v = self.cuts_x[idx - 1] + 4
                max_v = self.cuts_x[idx + 1] - 4
                self.cuts_x[idx] = max(min_v, min(max_v, val))
            elif axis == 'y':
                val = int(pos.y() / self.scale)
                min_v = self.cuts_y[idx - 1] + 4
                max_v = self.cuts_y[idx + 1] - 4
                self.cuts_y[idx] = max(min_v, min(max_v, val))
            self.update()
            return

        # Detección de hover sobre línea
        line = self._find_line_at(pos)
        self._hover_line = line
        if line:
            axis, _ = line
            self.setCursor(Qt.SplitHCursor if axis == 'x' else Qt.SplitVCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)

        # Detección de hover sobre tile
        tile = self._find_tile_at(pos)
        if tile != self.hovered_tile:
            self.hovered_tile = tile
            self.update()
            if tile:
                info = self.get_tile_info(tile[0], tile[1])
                cad_id = info.get('cad_id')
                if cad_id is not None:
                    tip = (f"<b>CAD_ID: [{cad_id}] {info.get('cad_name', '')}</b><br>"
                           f"Categoría: {info.get('cad_category', '')}<br>"
                           f"<small>Tile [{tile[0]},{tile[1]}] • {info['w']}x{info['h']}px en ({info['x']},{info['y']})</small>")
                else:
                    tip = (f"<b>Tile [{tile[0]},{tile[1]}]</b><br>"
                           f"Dimensiones: {info['w']}x{info['h']} px en ({info['x']},{info['y']})<br>"
                           f"<i>Sin vincular a CADe SIMU</i>")
                QToolTip.showText(self.mapToGlobal(pos), tip, self)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()

        if event.button() == Qt.LeftButton:
            # Comprobar si se pulsó en una línea para arrastrar
            line = self._find_line_at(pos)
            if line:
                self._dragging_line = line
                self._selected_line = line
                self.update()
                return

            # Si no es línea, seleccionar el tile correspondiente
            tile = self._find_tile_at(pos)
            if tile:
                self.selected_tile = tile
                self._selected_line = None
                self.update()
                info = self.get_tile_info(tile[0], tile[1])
                self.tile_selected.emit(info)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging_line:
            self._dragging_line = None
            self.layout_changed.emit()
            self.update()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.hovered_tile = None
        self._hover_line = None
        self.update()
        super().leaveEvent(event)

    # ── Renderizado ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        if self._base_pix.isNull():
            painter.fillRect(self.rect(), QColor("#1e1e2e"))
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Sin imagen cargada")
            return

        # 1. Dibujar imagen escalada
        sw = int(self._base_pix.width() * self.scale)
        sh = int(self._base_pix.height() * self.scale)
        target_rect = QRect(0, 0, sw, sh)
        painter.drawPixmap(target_rect, self._base_pix)

        sc = self.scale
        id_font = QFont("Monospace", 6, QFont.Bold)
        painter.setFont(id_font)

        # 2. Dibujar overlays de estado de cada tile
        for r_idx in range(len(self.cuts_y) - 1):
            for c_idx in range(len(self.cuts_x) - 1):
                rx = int(self.cuts_x[c_idx] * sc)
                ry = int(self.cuts_y[r_idx] * sc)
                rw = int((self.cuts_x[c_idx + 1] - self.cuts_x[c_idx]) * sc)
                rh = int((self.cuts_y[r_idx + 1] - self.cuts_y[r_idx]) * sc)

                info = self.get_tile_info(r_idx, c_idx)
                cad_id = info.get('cad_id')

                # Si está mapeado / USADO -> Pintar verde
                if cad_id is not None:
                    painter.fillRect(rx, ry, rw, rh, QColor(46, 204, 113, 80))
                    # Badge indicador con CAD_ID
                    badge_rect = QRect(rx + 1, ry + 1, min(rw - 2, 34), 11)
                    painter.fillRect(badge_rect, QColor(39, 174, 96, 220))
                    painter.setPen(QColor(255, 255, 255))
                    painter.drawText(badge_rect, Qt.AlignCenter, str(cad_id)[-4:])

        # 3. Tile Hover (amarillo suave)
        if self.hovered_tile and self.hovered_tile != self.selected_tile:
            hr, hc = self.hovered_tile
            rect = self.get_tile_rect(hr, hc)
            if rect:
                hrx, hry = int(rect.x() * sc), int(rect.y() * sc)
                hrw, hrh = int(rect.width() * sc), int(rect.height() * sc)
                painter.fillRect(hrx, hry, hrw, hrh, QColor(255, 235, 59, 70))
                painter.setPen(QPen(QColor(255, 235, 59, 200), 1.5))
                painter.drawRect(hrx, hry, hrw - 1, hrh - 1)

        # 4. Tile Seleccionado (oro / cian brillante)
        if self.selected_tile:
            sr, sc_idx = self.selected_tile
            rect = self.get_tile_rect(sr, sc_idx)
            if rect:
                srx, sry = int(rect.x() * sc), int(rect.y() * sc)
                srw, srh = int(rect.width() * sc), int(rect.height() * sc)
                painter.fillRect(srx, sry, srw, srh, QColor(0, 229, 255, 90))
                painter.setPen(QPen(QColor(0, 229, 255), 2))
                painter.drawRect(srx, sry, srw - 1, srh - 1)

        # 5. Dibujar líneas divisorias de corte
        # Líneas verticales X
        for i, cx in enumerate(self.cuts_x):
            px = int(cx * sc)
            is_edge = (i == 0 or i == len(self.cuts_x) - 1)
            is_sel = (self._selected_line == ('x', i))
            is_hov = (self._hover_line == ('x', i))

            if is_sel:
                pen = QPen(QColor("#ff007f"), 2.2, Qt.SolidLine)
            elif is_hov:
                pen = QPen(QColor("#ffea00"), 2.0, Qt.SolidLine)
            elif is_edge:
                pen = QPen(QColor("#45475a"), 1.5, Qt.SolidLine)
            else:
                pen = QPen(QColor("#00e5ff"), 1.2, Qt.DashLine)

            painter.setPen(pen)
            painter.drawLine(px, 0, px, sh)

            # Tiradores en extremos si no es borde
            if not is_edge:
                painter.setBrush(QBrush(QColor("#ff007f") if is_sel else QColor("#00e5ff")))
                painter.drawRect(px - 2, 0, 5, 4)
                painter.drawRect(px - 2, sh - 4, 5, 4)

        # Líneas horizontales Y
        for j, cy in enumerate(self.cuts_y):
            py = int(cy * sc)
            is_edge = (j == 0 or j == len(self.cuts_y) - 1)
            is_sel = (self._selected_line == ('y', j))
            is_hov = (self._hover_line == ('y', j))

            if is_sel:
                pen = QPen(QColor("#ff007f"), 2.2, Qt.SolidLine)
            elif is_hov:
                pen = QPen(QColor("#ffea00"), 2.0, Qt.SolidLine)
            elif is_edge:
                pen = QPen(QColor("#45475a"), 1.5, Qt.SolidLine)
            else:
                pen = QPen(QColor("#00e5ff"), 1.2, Qt.DashLine)

            painter.setPen(pen)
            painter.drawLine(0, py, sw, py)

            if not is_edge:
                painter.setBrush(QBrush(QColor("#ff007f") if is_sel else QColor("#00e5ff")))
                painter.drawRect(0, py - 2, 4, 5)
                painter.drawRect(sw - 4, py - 2, 4, 5)


class DynamicTileCutterWidget(QWidget):
    """Contenedor completo con barra de herramientas de corte y lienzo con scroll."""

    tile_selected = Signal(dict)
    assign_tile_requested = Signal(dict)
    unbind_tile_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layouts: dict = {}
        self._load_layouts()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # ── Barra de herramientas de corte ───────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(6)

        tb.addWidget(QLabel("<b>Corte Dinámico:</b>"))

        btn_add_x = QPushButton("➕ Corte Vertical")
        btn_add_x.setStyleSheet("padding: 4px 8px; background: #2e7d32; color: white;")
        btn_add_x.clicked.connect(lambda: self.canvas.add_cut_x())
        tb.addWidget(btn_add_x)

        btn_add_y = QPushButton("➕ Corte Horizontal")
        btn_add_y.setStyleSheet("padding: 4px 8px; background: #2e7d32; color: white;")
        btn_add_y.clicked.connect(lambda: self.canvas.add_cut_y())
        tb.addWidget(btn_add_y)

        btn_del_cut = QPushButton("➖ Quitar Corte")
        btn_del_cut.setStyleSheet("padding: 4px 8px; background: #c0392b; color: white;")
        btn_del_cut.clicked.connect(lambda: self.canvas.remove_selected_cut())
        tb.addWidget(btn_del_cut)

        tb.addSpacing(10)
        tb.addWidget(QLabel("Auto-dividir:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["21 px (Toolbar)", "24 px (Tile estándar)", "15 px (Mini)", "32 px", "48 px"])
        self.preset_combo.setCurrentIndex(1)
        tb.addWidget(self.preset_combo)

        btn_apply_preset = QPushButton("↺ Aplicar")
        btn_apply_preset.clicked.connect(self._apply_preset)
        tb.addWidget(btn_apply_preset)

        tb.addSpacing(10)
        tb.addWidget(QLabel("Zoom:"))
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["1.5x", "2.0x (Normal)", "3.0x (Detalle)", "4.0x (Máximo)"])
        self.zoom_combo.setCurrentIndex(1)
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        tb.addWidget(self.zoom_combo)

        tb.addStretch()

        btn_save_layout = QPushButton("💾 Guardar Cortes")
        btn_save_layout.setStyleSheet("font-weight: bold; padding: 4px 10px; background: #1976d2; color: white;")
        btn_save_layout.clicked.connect(self.save_current_layout)
        tb.addWidget(btn_save_layout)

        main_layout.addLayout(tb)

        # ── Scroll Area con el Canvas ─────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.canvas = DynamicTileCanvas(self)
        self.canvas.tile_selected.connect(self.tile_selected.emit)
        self.canvas.layout_changed.connect(self.save_current_layout)
        self.scroll_area.setWidget(self.canvas)
        main_layout.addWidget(self.scroll_area)

    # ── Persistencia de Layouts ──────────────────────────────────────────────

    def _load_layouts(self):
        if LAYOUTS_PATH.exists():
            try:
                with open(LAYOUTS_PATH, 'r', encoding='utf-8') as f:
                    self.layouts = json.load(f)
            except Exception:
                self.layouts = {}
        else:
            self.layouts = {}

    def save_current_layout(self):
        if not self.canvas.img_path or self.canvas._base_pix.isNull():
            return
        fname = Path(self.canvas.img_path).name
        self.layouts[fname] = {
            'cuts_x': self.canvas.cuts_x,
            'cuts_y': self.canvas.cuts_y,
            'width': self.canvas._base_pix.width(),
            'height': self.canvas._base_pix.height()
        }
        LAYOUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(LAYOUTS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.layouts, f, indent=2)
        except Exception as e:
            print(f"Error guardando layouts: {e}")

    # ── Control ──────────────────────────────────────────────────────────────

    def load_sheet(self, img_path: str, bmp_id: Optional[int], tile_to_cad: dict, mapping: dict):
        self.canvas.tile_to_cad = tile_to_cad
        self.canvas.mapping = mapping
        self.canvas.load_image(img_path, bmp_id, self.layouts)

    def _apply_preset(self):
        text = self.preset_combo.currentText()
        if "21" in text:
            step = 21
        elif "24" in text:
            step = 24
        elif "15" in text:
            step = 15
        elif "32" in text:
            step = 32
        elif "48" in text:
            step = 48
        else:
            step = 24
        self.canvas.reset_uniform(step)
        self.save_current_layout()

    def _on_zoom_changed(self, idx: int):
        scales = [1.5, 2.0, 3.0, 4.0]
        if 0 <= idx < len(scales):
            self.canvas.set_scale(scales[idx])

