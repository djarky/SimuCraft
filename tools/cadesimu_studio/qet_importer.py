"""
Importador y desglosador vectorial de archivos QElectroTech (.elmt).
Lee las geometrías de <description> (líneas, rectángulos, círculos, arcos, textos)
y los transforma en objetos gráficos editables interactivos normalizados en (0, 0).
"""
import math
from xml.etree import ElementTree as ET
from typing import Dict, List, Any, Tuple

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QFont

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicTextItem
)


class QETVectorImporter:
    """Extrae geometrías y terminales de un archivo .elmt a items de escena."""

    @staticmethod
    def parse_style(style_str: str) -> Tuple[QColor, float, Qt.PenStyle, QColor]:
        """Convierte estilo XML QET en propiedades de QPen y QBrush."""
        styles = {}
        if style_str:
            for part in style_str.split(';'):
                if ':' in part:
                    k, v = part.split(':', 1)
                    styles[k.strip()] = v.strip()

        # Color de línea
        color_str = styles.get('color', 'black')
        pen_color = QColor(color_str)
        if not pen_color.isValid() or pen_color.name() == '#000000':
            pen_color = QColor('#ffffff')  # En canvas oscuro de SimuCraft contrastamos blanco

        # Grosor
        weight = styles.get('line-weight', 'normal')
        pen_width = 1.8
        if weight == 'thin':
            pen_width = 1.0
        elif weight in ('hight', 'bold'):
            pen_width = 2.5

        # Estilo de trazo
        pen_style = Qt.SolidLine
        l_style = styles.get('line-style', 'normal')
        if l_style == 'dashed':
            pen_style = Qt.DashLine
        elif l_style == 'dotted':
            pen_style = Qt.DotLine

        # Relleno
        fill_str = styles.get('filling', 'none')
        brush_color = None
        if fill_str not in ('none', '', 'transparent'):
            brush_color = QColor(fill_str)
            if not brush_color.isValid():
                brush_color = None

        return pen_color, pen_width, pen_style, brush_color

    def import_from_elmt(self, elmt_path: str) -> Dict[str, Any]:
        """
        Lee el archivo .elmt y genera una lista de GraphicItems y bornes
        desplazados por hotspot_x y hotspot_y para anclarse en (0, 0).
        """
        tree = ET.parse(elmt_path)
        root = tree.getroot()

        hx = float(root.attrib.get('hotspot_x', 0))
        hy = float(root.attrib.get('hotspot_y', 0))
        w = float(root.attrib.get('width', 60))
        h = float(root.attrib.get('height', 60))

        items = []
        terminals = []

        desc = root.find('description')
        if desc is not None:
            for el in desc:
                tag = el.tag
                style_str = el.attrib.get('style', '')
                pen_color, pen_width, pen_style, brush_color = self.parse_style(style_str)

                if tag == 'line':
                    x1 = float(el.attrib.get('x1', 0)) + hx
                    y1 = float(el.attrib.get('y1', 0)) + hy
                    x2 = float(el.attrib.get('x2', 0)) + hx
                    y2 = float(el.attrib.get('y2', 0)) + hy
                    line_item = GraphicLineItem(x1, y1, x2, y2)
                    pen = QPen(pen_color, pen_width, pen_style, Qt.RoundCap)
                    line_item.setPen(pen)
                    items.append(line_item)

                elif tag == 'rect':
                    rx_pos = float(el.attrib.get('x', 0)) + hx
                    ry_pos = float(el.attrib.get('y', 0)) + hy
                    rw = float(el.attrib.get('width', 20))
                    rh = float(el.attrib.get('height', 20))
                    rx_corner = float(el.attrib.get('rx', 0))
                    ry_corner = float(el.attrib.get('ry', 0))
                    rect_item = GraphicRectItem(rx_pos, ry_pos, rw, rh, rx_corner, ry_corner)
                    rect_item.setPen(QPen(pen_color, pen_width, pen_style))
                    if brush_color:
                        rect_item.setBrush(QBrush(brush_color))
                    items.append(rect_item)

                elif tag == 'circle':
                    cx_raw = float(el.attrib.get('x', 0)) + hx
                    cy_raw = float(el.attrib.get('y', 0)) + hy
                    diam = float(el.attrib.get('diameter', 20))
                    circle_item = GraphicCircleItem(cx_raw, cy_raw, diam, diam)
                    circle_item.setPen(QPen(pen_color, pen_width, pen_style))
                    if brush_color:
                        circle_item.setBrush(QBrush(brush_color))
                    items.append(circle_item)

                elif tag == 'ellipse':
                    ex_raw = float(el.attrib.get('x', 0)) + hx
                    ey_raw = float(el.attrib.get('y', 0)) + hy
                    ew = float(el.attrib.get('width', 20))
                    eh = float(el.attrib.get('height', 20))
                    ellipse_item = GraphicCircleItem(ex_raw, ey_raw, ew, eh)
                    ellipse_item.setPen(QPen(pen_color, pen_width, pen_style))
                    if brush_color:
                        ellipse_item.setBrush(QBrush(brush_color))
                    items.append(ellipse_item)

                elif tag in ('text', 'dynamic_text'):
                    t_str = ""
                    if tag == 'text':
                        t_str = el.attrib.get('text', '')
                    else:
                        t_node = el.find('text')
                        if t_node is not None and t_node.text:
                            t_str = t_node.text
                    if t_str and t_str != '_':
                        tx = float(el.attrib.get('x', 0)) + hx
                        ty = float(el.attrib.get('y', 0)) + hy
                        txt_item = GraphicTextItem(t_str, tx, ty)
                        txt_item.setDefaultTextColor(pen_color)
                        items.append(txt_item)

                elif tag == 'terminal':
                    tx = float(el.attrib.get('x', 0)) + hx
                    ty = float(el.attrib.get('y', 0)) + hy
                    t_name = el.attrib.get('name') or el.attrib.get('uuid') or f"T{len(terminals)+1}"
                    orient = el.attrib.get('orientation', 'n')
                    terminals.append({
                        'id': t_name,
                        'name': t_name,
                        'x': tx,
                        'y': ty,
                        'orientation': orient,
                        'type': 'contact'
                    })

        return {
            'width': w,
            'height': h,
            'items': items,
            'terminals': terminals,
            'hotspot_x': hx,
            'hotspot_y': hy
        }

