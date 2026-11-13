"""
Importador y desglosador vectorial de archivos QElectroTech (.elmt).

Convierte las geometrías de <description> (líneas, rectángulos, círculos,
arcos, polígonos, textos, terminales) en objetos gráficos editables de Qt.

Convención de coordenadas QET:
  - El elemento <definition> define hotspot_x / hotspot_y: el punto de anclaje
    dentro del área width × height.
  - Todas las coordenadas en <description> son **relativas al hotspot**, es
    decir pueden ser negativas (por encima/izquierda del hotspot).
  - Para renderizar en escena con origen (0, 0) = hotspot, sumamos
    hotspot_x / hotspot_y a cada coordenada.
"""
import math
from xml.etree import ElementTree as ET
from typing import Dict, List, Any, Tuple

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QFont

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicArcItem,
    GraphicPolygonItem, GraphicTextItem,
)


class QETVectorImporter:
    """Extrae geometrías y terminales de un archivo .elmt a items de escena."""

    # ── Interpretación de estilos ─────────────────────────────────────────────

    @staticmethod
    def parse_style(style_str: str) -> Tuple[QColor, float, Qt.PenStyle, QColor]:
        """Convierte el atributo `style` de QET en propiedades de QPen/QBrush."""
        styles: dict = {}
        if style_str:
            for part in style_str.split(';'):
                if ':' in part:
                    k, v = part.split(':', 1)
                    styles[k.strip()] = v.strip()

        # Color de trazo
        color_str = styles.get('color', 'black')
        pen_color = QColor(color_str)
        if not pen_color.isValid():
            pen_color = QColor('#000000')
        # En el lienzo oscuro de SimuCraft el negro puro se hace blanco para contrastar
        if pen_color.name() in ('#000000', '#000'):
            pen_color = QColor('#ffffff')

        # Grosor
        weight = styles.get('line-weight', 'normal')
        pen_width = 1.8
        if weight == 'thin':
            pen_width = 1.0
        elif weight in ('hight', 'bold', 'strong'):
            pen_width = 2.5

        # Estilo de trazo
        pen_style = Qt.SolidLine
        l_style = styles.get('line-style', 'normal')
        if l_style == 'dashed':
            pen_style = Qt.DashLine
        elif l_style == 'dotted':
            pen_style = Qt.DotLine
        elif l_style == 'dashdot':
            pen_style = Qt.DashDotLine

        # Relleno
        fill_str = styles.get('filling', 'none')
        brush_color = None
        if fill_str not in ('none', '', 'transparent'):
            bc = QColor(fill_str)
            if bc.isValid():
                # Negro puro → blanco en lienzo oscuro
                if bc.name() == '#000000':
                    bc = QColor('#ffffff')
                brush_color = bc

        return pen_color, pen_width, pen_style, brush_color

    # ── Parseo de polígono ────────────────────────────────────────────────────

    @staticmethod
    def _parse_polygon_points(el, hx: float, hy: float) -> list:
        """
        Extrae pares de puntos de un elemento <polygon>.
        QET usa atributos x1,y1 x2,y2 … xN,yN (hasta 99 pares).
        """
        points = []
        i = 1
        while True:
            xs = el.attrib.get(f'x{i}')
            ys = el.attrib.get(f'y{i}')
            if xs is None or ys is None:
                break
            points.append((float(xs) + hx, float(ys) + hy))
            i += 1
        return points

    # ── Importador principal ──────────────────────────────────────────────────

    def import_from_elmt(self, elmt_path: str) -> Dict[str, Any]:
        """
        Lee el archivo .elmt y genera listas de GraphicItems y terminales.

        Los ítems se posicionan en coordenadas de escena donde (0, 0) es el
        hotspot del símbolo QET.  El caller debe añadirlos a la escena sin
        desplazamiento adicional.

        Returns
        -------
        dict con claves:
          'width'      – ancho declarado del símbolo (px QET ≈ px pantalla)
          'height'     – alto declarado
          'hotspot_x'  – valor hotspot_x del XML
          'hotspot_y'  – valor hotspot_y del XML
          'items'      – lista de QGraphicsItem listos para addItem()
          'terminals'  – lista de dicts {id, name, x, y, orientation, type}
        """
        tree = ET.parse(elmt_path)
        root = tree.getroot()

        # El root puede ser <definition> o <element>
        hx = float(root.attrib.get('hotspot_x', 0))
        hy = float(root.attrib.get('hotspot_y', 0))
        w  = float(root.attrib.get('width',  60))
        h  = float(root.attrib.get('height', 60))

        items: list = []
        terminals: list = []

        desc = root.find('description')
        if desc is None:
            return {'width': w, 'height': h, 'hotspot_x': hx, 'hotspot_y': hy,
                    'items': items, 'terminals': terminals}

        for el in desc:
            tag = el.tag
            style_str = el.attrib.get('style', '')
            pen_color, pen_width, pen_style, brush_color = self.parse_style(style_str)

            pen = QPen(pen_color, pen_width, pen_style, Qt.RoundCap)
            brush = QBrush(brush_color) if brush_color else Qt.NoBrush

            # ── Línea ──────────────────────────────────────────────────────
            if tag == 'line':
                x1 = float(el.attrib.get('x1', 0)) + hx
                y1 = float(el.attrib.get('y1', 0)) + hy
                x2 = float(el.attrib.get('x2', 0)) + hx
                y2 = float(el.attrib.get('y2', 0)) + hy
                item = GraphicLineItem(x1, y1, x2, y2)
                item.setPen(pen)
                items.append(item)

            # ── Rectángulo ─────────────────────────────────────────────────
            elif tag == 'rect':
                rx_pos = float(el.attrib.get('x', 0)) + hx
                ry_pos = float(el.attrib.get('y', 0)) + hy
                rw = float(el.attrib.get('width',  20))
                rh = float(el.attrib.get('height', 20))
                rx_corner = float(el.attrib.get('rx', 0))
                ry_corner = float(el.attrib.get('ry', 0))
                item = GraphicRectItem(rx_pos, ry_pos, rw, rh, rx_corner, ry_corner)
                item.setPen(pen)
                item.setBrush(brush)
                items.append(item)

            # ── Círculo ────────────────────────────────────────────────────
            elif tag == 'circle':
                # QET: x,y es la esquina superior-izquierda del bounding box
                cx = float(el.attrib.get('x', 0)) + hx
                cy = float(el.attrib.get('y', 0)) + hy
                diam = float(el.attrib.get('diameter', 20))
                item = GraphicCircleItem(cx, cy, diam, diam)
                item.setPen(pen)
                item.setBrush(brush)
                items.append(item)

            # ── Elipse ─────────────────────────────────────────────────────
            elif tag == 'ellipse':
                ex = float(el.attrib.get('x', 0)) + hx
                ey = float(el.attrib.get('y', 0)) + hy
                ew = float(el.attrib.get('width',  20))
                eh = float(el.attrib.get('height', 20))
                item = GraphicCircleItem(ex, ey, ew, eh)
                item.setPen(pen)
                item.setBrush(brush)
                items.append(item)

            # ── Arco ───────────────────────────────────────────────────────
            elif tag == 'arc':
                ax = float(el.attrib.get('x', 0)) + hx
                ay = float(el.attrib.get('y', 0)) + hy
                aw = float(el.attrib.get('width',  20))
                ah = float(el.attrib.get('height', 20))
                # QET: start y angle en décimas de grado (ángulos QET = °×16 en Qt)
                # Pero en QET moderno son grados directos
                start  = float(el.attrib.get('start', 0))
                angle  = float(el.attrib.get('angle', 90))
                item = GraphicArcItem(ax, ay, aw, ah, start, angle)
                item.setPen(pen)
                items.append(item)

            # ── Polígono ───────────────────────────────────────────────────
            elif tag == 'polygon':
                pts = self._parse_polygon_points(el, hx, hy)
                if len(pts) >= 2:
                    item = GraphicPolygonItem(pts)
                    item.setPen(pen)
                    item.setBrush(brush)
                    items.append(item)

            # ── Texto estático ─────────────────────────────────────────────
            elif tag == 'text':
                t_str = el.attrib.get('text', '').strip()
                if t_str and t_str != '_':
                    tx = float(el.attrib.get('x', 0)) + hx
                    ty = float(el.attrib.get('y', 0)) + hy
                    # Parsear tamaño de fuente desde atributo font si existe
                    font_attr = el.attrib.get('font', '')
                    pt_size = 9
                    if font_attr:
                        parts = font_attr.split(',')
                        if len(parts) > 1:
                            try:
                                pt_size = max(6, int(float(parts[1])))
                            except ValueError:
                                pass
                    item = GraphicTextItem(t_str, tx, ty)
                    item.setDefaultTextColor(pen_color)
                    fnt = QFont("Sans Serif", pt_size)
                    item.setFont(fnt)
                    items.append(item)

            # ── Texto dinámico (label de referencia, se muestra como placeholder) ─
            elif tag == 'dynamic_text':
                # Buscar texto hijo
                t_node = el.find('text')
                info_node = el.find('info_name')
                t_str = ''
                if t_node is not None and t_node.text:
                    t_str = t_node.text.strip()
                if not t_str and info_node is not None and info_node.text:
                    t_str = f'[{info_node.text.strip()}]'
                if not t_str:
                    t_str = '[label]'
                tx = float(el.attrib.get('x', 0)) + hx
                ty = float(el.attrib.get('y', 0)) + hy
                font_attr = el.attrib.get('font', '')
                pt_size = 7
                if font_attr:
                    parts = font_attr.split(',')
                    if len(parts) > 1:
                        try:
                            pt_size = max(5, int(float(parts[1])))
                        except ValueError:
                            pass
                item = GraphicTextItem(t_str, tx, ty)
                item.setDefaultTextColor(QColor('#aaaaaa'))   # gris para distinguirlo
                fnt = QFont("Sans Serif", pt_size)
                item.setFont(fnt)
                items.append(item)

            # ── Input (texto editable en QET, placeholder en SimuCraft) ───
            elif tag == 'input':
                t_str = el.attrib.get('text', '[input]').strip() or '[input]'
                tx = float(el.attrib.get('x', 0)) + hx
                ty = float(el.attrib.get('y', 0)) + hy
                item = GraphicTextItem(t_str, tx, ty)
                item.setDefaultTextColor(QColor('#88ccff'))
                items.append(item)

            # ── Terminal ───────────────────────────────────────────────────
            elif tag == 'terminal':
                tx = float(el.attrib.get('x', 0)) + hx
                ty = float(el.attrib.get('y', 0)) + hy
                t_name = (el.attrib.get('name') or
                          el.attrib.get('uuid') or
                          f"T{len(terminals) + 1}")
                orient = el.attrib.get('orientation', 'n')
                terminals.append({
                    'id':          t_name,
                    'name':        t_name,
                    'x':           tx,
                    'y':           ty,
                    'orientation': orient,
                    'type':        'contact',
                })

        return {
            'width':     w,
            'height':    h,
            'hotspot_x': hx,
            'hotspot_y': hy,
            'items':     items,
            'terminals': terminals,
        }
