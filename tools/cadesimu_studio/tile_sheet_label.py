"""
Widget para previsualización ampliada de hojas BMP y toolbars con grilla y overlays.
"""
from pathlib import Path

from PySide6.QtWidgets import QLabel, QToolTip
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont

from .config import DEFAULT_TILE_SIZE, DEFAULT_SCALE

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
        if self._base_pix.isNull():
            # Fallback: convertir con PIL (necesario para BMPs en algunos sistemas)
            try:
                from PIL import Image as _PILImg
                import tempfile, os as _os
                pil = _PILImg.open(img_path).convert('RGB')
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                pil.save(tmp.name)
                tmp.close()
                self._base_pix = QPixmap(tmp.name)
                _os.unlink(tmp.name)
            except Exception as e:
                print(f"Error cargando {img_path}: {e}")
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

        # --- Overlay por cada tile del mapa ---
        ts_sc = ts * sc
        if self.bmp_id is not None:
            painter = QPainter(disp)
            painter.setRenderHint(QPainter.Antialiasing, False)

            # Usar fuente compacta para los badges de ID
            id_font = QFont("Monospace", 6, QFont.Bold)
            painter.setFont(id_font)

            for key, info in self.tile_to_cad.items():
                if not key.startswith(f"{self.bmp_id}_"):
                    continue
                row = info.get('row', 0)
                col = info.get('col', 0)
                cad_id = info.get('cad_id')
                rx = col * ts_sc
                ry = row * ts_sc

                # Estado de mapeo:
                # Verde (#2ecc71): Mapeado a QET (set)
                # Naranja (#f39c12): Tiene CAD_ID asignado en el catálogo pero sin QET asignado (unmapped/bound)
                # Rojo (#e74c3c): Sin CAD_ID asignado / huérfano (unset)
                map_key = f"CAD:{cad_id}" if cad_id is not None else None
                is_mapped = map_key and (map_key in self.mapping or str(cad_id) in self.mapping)

                if is_mapped:
                    # VERDE = seteado / mapeado a QET
                    painter.fillRect(rx, ry, ts_sc, ts_sc, QColor(46, 204, 113, 85))
                    painter.setPen(QPen(QColor(46, 204, 113, 220), 1))
                    painter.drawRect(rx, ry, ts_sc - 1, ts_sc - 1)
                    badge_bg = QColor(39, 174, 96, 220)
                    text_color = QColor(255, 255, 255)
                    label_str = str(cad_id)
                elif cad_id is not None:
                    # NARANJA = catalogado en CADe SIMU pero sin QET (unbound / pending)
                    painter.fillRect(rx, ry, ts_sc, ts_sc, QColor(243, 156, 18, 55))
                    painter.setPen(QPen(QColor(243, 156, 18, 190), 1))
                    painter.drawRect(rx, ry, ts_sc - 1, ts_sc - 1)
                    badge_bg = QColor(211, 84, 0, 200)
                    text_color = QColor(255, 255, 255)
                    label_str = str(cad_id)
                else:
                    # ROJO = unset / sin asignación CADe SIMU
                    painter.fillRect(rx, ry, ts_sc, ts_sc, QColor(231, 76, 60, 25))
                    painter.setPen(QPen(QColor(231, 76, 60, 90), 1, Qt.DotLine))
                    painter.drawRect(rx, ry, ts_sc - 1, ts_sc - 1)
                    badge_bg = None
                    label_str = None

                # Pequeño badge indicador con el CAD_ID en la esquina superior del tile
                if label_str and badge_bg:
                    text_rect = QRectF(rx + 1, ry + 1, min(ts_sc - 2, 28), 10)
                    painter.fillRect(text_rect, badge_bg)
                    painter.setPen(text_color)
                    painter.drawText(text_rect, Qt.AlignCenter, label_str[-4:])

            # --- Tile hover (amarillo brillante) ---
            if self.hovered_tile:
                hr, hc = self.hovered_tile
                painter.fillRect(hc * ts_sc, hr * ts_sc, ts_sc, ts_sc, QColor(255, 235, 59, 90))
                painter.setPen(QPen(QColor(255, 235, 59, 255), 2))
                painter.drawRect(hc * ts_sc, hr * ts_sc, ts_sc - 1, ts_sc - 1)

            # --- Tile seleccionado (cian eléctrico) ---
            if self.selected_tile:
                sr, sc2 = self.selected_tile
                painter.fillRect(sc2 * ts_sc, sr * ts_sc, ts_sc, ts_sc, QColor(0, 229, 255, 100))
                painter.setPen(QPen(QColor(0, 229, 255), 2))
                painter.drawRect(sc2 * ts_sc, sr * ts_sc, ts_sc - 1, ts_sc - 1)

            painter.end()
        else:
            # BMPs sin tilemap (e.g. tiras de toolbars de 21px o láminas): dibujar grid guía
            painter = QPainter(disp)
            painter.setRenderHint(QPainter.Antialiasing, False)
            ts_sc = ts * sc
            w_pix = disp.width()
            h_pix = disp.height()
            id_font = QFont("Monospace", 6)
            painter.setFont(id_font)

            painter.setPen(QPen(QColor(100, 120, 150, 110), 1))
            cols_count = w_pix // ts_sc
            rows_count = h_pix // ts_sc
            for c in range(cols_count + 1):
                painter.drawLine(c * ts_sc, 0, c * ts_sc, h_pix)
            for r in range(rows_count + 1):
                painter.drawLine(0, r * ts_sc, w_pix, r * ts_sc)

            # Numeración de índice en cada tile para fácil orientación
            for r in range(rows_count):
                for c in range(cols_count):
                    tx = c * ts_sc
                    ty = r * ts_sc
                    # Estado rojo (unset)
                    painter.fillRect(tx + 1, ty + 1, ts_sc - 2, ts_sc - 2, QColor(231, 76, 60, 25))
                    painter.setPen(QColor(200, 200, 200, 160))
                    idx_str = f"{c}" if rows_count == 1 else f"{r},{c}"
                    painter.drawText(QRectF(tx, ty + ts_sc - 10, ts_sc, 10), Qt.AlignRight, idx_str)

            # Hover y selección para BMPs sin tilemap
            if self.hovered_tile:
                hr, hc = self.hovered_tile
                painter.fillRect(hc * ts_sc, hr * ts_sc, ts_sc, ts_sc, QColor(255, 235, 59, 90))
                painter.setPen(QPen(QColor(255, 235, 59, 255), 2))
                painter.drawRect(hc * ts_sc, hr * ts_sc, ts_sc - 1, ts_sc - 1)
            if self.selected_tile:
                sr, sc2 = self.selected_tile
                painter.fillRect(sc2 * ts_sc, sr * ts_sc, ts_sc, ts_sc, QColor(0, 229, 255, 90))
                painter.setPen(QPen(QColor(0, 229, 255), 2))
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
            return {'row': row, 'col': col}
        key = f"{self.bmp_id}_{row:02d}_{col:02d}"
        return self.tile_to_cad.get(key, {'row': row, 'col': col})

    def mouseMoveEvent(self, event):
        row, col = self._tile_at(event.position())
        if (row, col) != self.hovered_tile:
            self.hovered_tile = (row, col)
            self._render()
            # Tooltip: siempre mostrar row/col, y CAD_ID si está disponible
            info = self._get_tile_info(row, col)
            from PySide6.QtWidgets import QToolTip
            from PySide6.QtCore import QPoint
            cad_id = info.get('cad_id')
            if cad_id is not None:
                name   = info.get('name', '') or '—'
                cat    = info.get('category', '')
                tags   = info.get('tags', '')
                tip = f"<b>CAD_ID: {cad_id}</b><br>{name}<br><i>{cat}</i><br><small>Tile [{row},{col}]</small>"
                if tags:
                    tip += f"<br><small>{tags}</small>"
            else:
                bmp_name = f"bitmap_{self.bmp_id}" if self.bmp_id else "BMP"
                tip = f"<b>{bmp_name}</b><br>Tile [{row},{col}]<br><i>Sin mapeo CADe SIMU</i>"
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
