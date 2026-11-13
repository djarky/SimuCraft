"""
Factoría de primitivas gráficas vectoriales interactivas para componentes estándar.

Genera la descomposición completa en elementos vectoriales editables
(GraphicLineItem, GraphicRectItem, GraphicCircleItem, GraphicArcItem,
GraphicTextItem, GraphicPolygonItem) para cada uno de los 35 componentes
estándar de SimuCraft, perfectamente alineados con sus bornes y rejilla.
"""
import math
from typing import List
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QFont

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicArcItem,
    GraphicPolygonItem, GraphicTextItem
)


def _pen(color: str = "#ffffff", width: float = 1.8, style: Qt.PenStyle = Qt.SolidLine) -> QPen:
    return QPen(QColor(color), width, style, Qt.RoundCap)


def _brush(color: str) -> QBrush:
    return QBrush(QColor(color))


def create_standard_primitives(comp_key: str, comp_def: dict) -> List[QGraphicsItem]:
    """
    Crea la lista de primitivas vectoriales editables para el componente estándar.
    """
    items: List[QGraphicsItem] = []
    vis = comp_def.get('visual', {})
    w = float(vis.get('width', 90.0))
    h = float(vis.get('height', 72.0))
    mid_y = h / 2.0
    terminals = vis.get('terminals', [])
    c_type = comp_def.get('type', 'generic')

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Alimentación (Línea Fase L y Neutro N)
    # ─────────────────────────────────────────────────────────────────────────
    if c_type == 'power' or comp_key == 'power_l':
        line = GraphicLineItem(-25, 0, 25, 0)
        line.setPen(_pen("#e74c3c", 2.8))
        dot = GraphicCircleItem(-4, -4, 8, 8)
        dot.setPen(_pen("#e74c3c", 1.5))
        dot.setBrush(_brush("#e74c3c"))
        txt = GraphicTextItem("L (230V)", -22, -22)
        txt.setDefaultTextColor(QColor("#e74c3c"))
        txt.setFont(QFont("Sans Serif", 8, QFont.Bold))
        items.extend([line, dot, txt])

    elif c_type == 'neutral' or comp_key == 'power_n':
        line = GraphicLineItem(-25, 0, 25, 0)
        line.setPen(_pen("#3498db", 2.8))
        dot = GraphicCircleItem(-4, -4, 8, 8)
        dot.setPen(_pen("#3498db", 1.5))
        dot.setBrush(_brush("#3498db"))
        txt = GraphicTextItem("N (0V)", -18, 6)
        txt.setDefaultTextColor(QColor("#3498db"))
        txt.setFont(QFont("Sans Serif", 8, QFont.Bold))
        items.extend([line, dot, txt])

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Pulsadores e Interruptores de Mando
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'pushbutton':
        is_nc = 'nc' in comp_key.lower() or not comp_def.get('normally_open', True)
        is_mushroom = 'mushroom' in comp_key.lower()
        is_double = 'no_nc' in comp_key.lower()

        if is_double:
            # Pulsador doble NA+NC
            # Polo 1 (NA) en x=0, Polo 2 (NC) en x=36
            # Polo NA
            l1 = GraphicLineItem(0, 0, 0, mid_y - 7)
            l2 = GraphicLineItem(0, mid_y + 7, 0, h)
            d1 = GraphicCircleItem(-2.5, mid_y - 9.5, 5, 5)
            d2 = GraphicCircleItem(-2.5, mid_y + 4.5, 5, 5)
            blade_no = GraphicLineItem(-8, mid_y - 6, 0, mid_y + 7)
            # Polo NC
            l3 = GraphicLineItem(36, 0, 36, mid_y - 7)
            l4 = GraphicLineItem(36, mid_y + 7, 36, h)
            d3 = GraphicCircleItem(33.5, mid_y - 9.5, 5, 5)
            d4 = GraphicCircleItem(33.5, mid_y + 4.5, 5, 5)
            blade_nc = GraphicLineItem(36, mid_y - 7, 36, mid_y + 7)
            slash_nc = GraphicLineItem(30, mid_y - 4, 42, mid_y + 4)
            # Vástago común
            shaft = GraphicLineItem(-14, mid_y, 36, mid_y)
            shaft.setPen(_pen("#888888", 1.2, Qt.DashLine))
            cap = GraphicRectItem(-18, mid_y - 6, 4, 12)
            cap.setBrush(_brush("#2ecc71"))
            # Rótulos
            t1 = GraphicTextItem("13", 4, 8)
            t2 = GraphicTextItem("14", 4, h - 22)
            t3 = GraphicTextItem("21", 40, 8)
            t4 = GraphicTextItem("22", 40, h - 22)
            items.extend([l1, l2, d1, d2, blade_no, l3, l4, d3, d4, blade_nc, slash_nc, shaft, cap, t1, t2, t3, t4])
        else:
            # Pulsador simple NA o NC
            l1 = GraphicLineItem(0, 0, 0, mid_y - 7)
            l2 = GraphicLineItem(0, mid_y + 7, 0, h)
            d1 = GraphicCircleItem(-2.5, mid_y - 9.5, 5, 5)
            d2 = GraphicCircleItem(-2.5, mid_y + 4.5, 5, 5)
            d1.setBrush(_brush("#ffffff"))
            d2.setBrush(_brush("#ffffff"))

            if is_nc:
                blade = GraphicLineItem(0, mid_y - 7, 0, mid_y + 7)
                slash = GraphicLineItem(-6, mid_y - 4, 6, mid_y + 4)
                items.append(slash)
                lbl_top, lbl_bot = "11", "12"
                cap_color = "#e74c3c"
            else:
                blade = GraphicLineItem(-8, mid_y - 6, 0, mid_y + 7)
                lbl_top, lbl_bot = "13", "14"
                cap_color = "#2ecc71"

            # Vástago
            shaft = GraphicLineItem(-14, mid_y, -5, mid_y)
            shaft.setPen(_pen("#888888", 1.2, Qt.DashLine))

            if is_mushroom:
                # Cabeza de seta / hongo de parada de emergencia
                cap = GraphicArcItem(-24, mid_y - 8, 10, 16, -90, 180)
                cap.setPen(_pen("#e74c3c", 2.0))
            elif 'selector' in comp_key:
                # Maneta de selector giratorio
                cap = GraphicLineItem(-16, mid_y - 8, -6, mid_y + 8)
                cap.setPen(_pen("#f39c12", 2.2))
            elif 'limit' in comp_key:
                # Palanca de fin de carrera con rodillo
                cap = GraphicCircleItem(-18, mid_y - 4, 8, 8)
                cap.setPen(_pen("#3498db", 1.5))
            else:
                # Botón pulsador rasante
                cap = GraphicRectItem(-18, mid_y - 6, 4, 12)
                cap.setPen(_pen(cap_color, 1.2))
                cap.setBrush(_brush(cap_color))

            t1 = GraphicTextItem(lbl_top, 5, 8)
            t2 = GraphicTextItem(lbl_bot, 5, h - 22)
            items.extend([l1, l2, d1, d2, blade, shaft, cap, t1, t2])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Bobinas de Contactor y Relé
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'contactor' or 'coil' in comp_key:
        l1 = GraphicLineItem(0, 0, 0, mid_y - 14)
        l2 = GraphicLineItem(0, mid_y + 14, 0, h)
        # Rectángulo cuerpo de bobina
        rect = GraphicRectItem(-16, mid_y - 14, 32, 28, rx=4, ry=4)
        rect.setPen(_pen("#ffffff", 1.8))
        # Línea diagonal interior (norma IEC para bobina)
        diag = GraphicLineItem(-16, mid_y + 14, 16, mid_y - 14)
        diag.setPen(_pen("#ffffff", 1.4))
        # Rótulos
        t_a1 = GraphicTextItem("A1", 6, 8)
        t_a2 = GraphicTextItem("A2", 6, h - 22)
        tag_txt = GraphicTextItem("KM", -12, mid_y - 11)
        tag_txt.setFont(QFont("Sans Serif", 9, QFont.Bold))
        items.extend([l1, l2, rect, diag, t_a1, t_a2, tag_txt])

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Contactores de Potencia (1P, 2P, 3P, 4P)
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'contactor_power' or 'contactor_' in comp_key and any(p in comp_key for p in ['1p', '2p', '3p', '4p']):
        poles = sorted(list(set(int(t.get('x', 0)) for t in terminals if t.get('y', 0) == 0)))
        if not poles:
            poles = [0, 36, 72]

        for i, px in enumerate(poles):
            l_top = GraphicLineItem(px, 0, px, mid_y - 10)
            l_bot = GraphicLineItem(px, mid_y + 10, px, h)
            d_top = GraphicCircleItem(px - 2.5, mid_y - 12.5, 5, 5)
            d_bot = GraphicCircleItem(px - 2.5, mid_y + 7.5, 5, 5)
            d_top.setBrush(_brush("#ffffff"))
            d_bot.setBrush(_brush("#ffffff"))
            blade = GraphicLineItem(px - 6, mid_y - 9, px, mid_y + 9)
            # Semicírculo de potencia IEC
            arc = GraphicArcItem(px - 9, mid_y - 13, 6, 6, 0, 180)
            arc.setPen(_pen("#ffffff", 1.4))
            lbl_t = GraphicTextItem(str(2 * i + 1), px + 4, 8)
            lbl_b = GraphicTextItem(str(2 * i + 2), px + 4, h - 22)
            items.extend([l_top, l_bot, d_top, d_bot, blade, arc, lbl_t, lbl_b])

        # Enlace mecánico horizontal si hay más de 1 polo
        if len(poles) > 1:
            link = GraphicLineItem(min(poles) - 4, mid_y, max(poles) + 4, mid_y)
            link.setPen(_pen("#888888", 1.2, Qt.DashLine))
            items.append(link)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Contactos Auxiliares (NA y NC)
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type in ('contact_no', 'contact'):
        l1 = GraphicLineItem(0, 0, 0, mid_y - 8)
        l2 = GraphicLineItem(0, mid_y + 8, 0, h)
        d1 = GraphicCircleItem(-2.5, mid_y - 10.5, 5, 5)
        d2 = GraphicCircleItem(-2.5, mid_y + 5.5, 5, 5)
        d1.setBrush(_brush("#ffffff"))
        d2.setBrush(_brush("#ffffff"))
        blade = GraphicLineItem(-7, mid_y - 7, 0, mid_y + 8)
        t1 = GraphicTextItem("13", 5, 8)
        t2 = GraphicTextItem("14", 5, h - 22)
        items.extend([l1, l2, d1, d2, blade, t1, t2])

    elif c_type == 'contact_nc':
        l1 = GraphicLineItem(0, 0, 0, mid_y - 8)
        l2 = GraphicLineItem(0, mid_y + 8, 0, h)
        d1 = GraphicCircleItem(-2.5, mid_y - 10.5, 5, 5)
        d2 = GraphicCircleItem(-2.5, mid_y + 5.5, 5, 5)
        d1.setBrush(_brush("#ffffff"))
        d2.setBrush(_brush("#ffffff"))
        blade = GraphicLineItem(0, mid_y - 8, 0, mid_y + 8)
        slash = GraphicLineItem(-6, mid_y - 5, 6, mid_y + 5)
        t1 = GraphicTextItem("21", 5, 8)
        t2 = GraphicTextItem("22", 5, h - 22)
        items.extend([l1, l2, d1, d2, blade, slash, t1, t2])

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Lámparas Piloto / Indicadores Luminosos
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'lamp' or 'lamp' in comp_key:
        r = 15.0
        l1 = GraphicLineItem(0, 0, 0, mid_y - r)
        l2 = GraphicLineItem(0, mid_y + r, 0, h)
        circle = GraphicCircleItem(-r, mid_y - r, r * 2, r * 2)
        circle.setPen(_pen("#ffffff", 1.8))

        # Color de lámpara opcional
        fill_col = None
        if 'red' in comp_key:
            circle.setPen(_pen("#e74c3c", 2.0))
            fill_col = "#e74c3c"
        elif 'green' in comp_key:
            circle.setPen(_pen("#2ecc71", 2.0))
            fill_col = "#2ecc71"
        elif 'amber' in comp_key:
            circle.setPen(_pen("#f39c12", 2.0))
            fill_col = "#f39c12"

        # Cruz en aspa interior (símbolo normativo lámpara)
        diag = r * 0.707
        c1 = GraphicLineItem(-diag, mid_y - diag, diag, mid_y + diag)
        c2 = GraphicLineItem(-diag, mid_y + diag, diag, mid_y - diag)
        c1.setPen(_pen(fill_col or "#ffffff", 1.4))
        c2.setPen(_pen(fill_col or "#ffffff", 1.4))

        t1 = GraphicTextItem("X1", 5, 8)
        t2 = GraphicTextItem("X2", 5, h - 22)
        items.extend([l1, l2, circle, c1, c2, t1, t2])

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Relé Térmico
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'relay' or 'thermal' in comp_key:
        l1 = GraphicLineItem(0, 0, 0, mid_y - 8)
        l2 = GraphicLineItem(0, mid_y + 8, 0, h)
        d1 = GraphicCircleItem(-2.5, mid_y - 10.5, 5, 5)
        d2 = GraphicCircleItem(-2.5, mid_y + 5.5, 5, 5)
        d1.setBrush(_brush("#ffffff"))
        d2.setBrush(_brush("#ffffff"))
        blade = GraphicLineItem(0, mid_y - 8, 0, mid_y + 8)
        # Símbolo bimetal térmico (rectángulo adherido)
        bimetal = GraphicRectItem(-8, mid_y - 5, 8, 10)
        bimetal.setPen(_pen("#e67e22", 1.4))
        t1 = GraphicTextItem("95", 5, 8)
        t2 = GraphicTextItem("96", 5, h - 22)
        tag_f = GraphicTextItem("F", -18, mid_y - 8)
        tag_f.setFont(QFont("Sans Serif", 8, QFont.Bold))
        items.extend([l1, l2, d1, d2, blade, bimetal, t1, t2, tag_f])

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Disyuntores / Magnetotérmicos
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type in ('breaker', 'breaker_3p') or 'breaker' in comp_key:
        poles = sorted(list(set(int(t.get('x', 0)) for t in terminals if t.get('y', 0) == 0)))
        if not poles:
            poles = [0, 36, 72] if '3p' in comp_key else [0]

        left = min(poles) - 10
        right = max(poles) + 10
        box = GraphicRectItem(left, 8, right - left, h - 16, rx=4, ry=4)
        box.setPen(_pen("#f1c40f", 1.4, Qt.DashLine))

        for i, px in enumerate(poles):
            l_top = GraphicLineItem(px, 0, px, mid_y - 12)
            l_bot = GraphicLineItem(px, mid_y + 12, px, h)
            d_top = GraphicCircleItem(px - 2.5, mid_y - 14.5, 5, 5)
            d_bot = GraphicCircleItem(px - 2.5, mid_y + 9.5, 5, 5)
            d_top.setBrush(_brush("#ffffff"))
            d_bot.setBrush(_brush("#ffffff"))
            blade = GraphicLineItem(px - 6, mid_y - 10, px + 1, mid_y + 10)
            # Marca térmica X
            x1 = GraphicLineItem(px - 7, mid_y - 2, px - 3, mid_y + 2)
            x2 = GraphicLineItem(px - 3, mid_y - 2, px - 7, mid_y + 2)
            x1.setPen(_pen("#e74c3c", 1.2))
            x2.setPen(_pen("#e74c3c", 1.2))

            lbl_t = GraphicTextItem(str(2 * i + 1), px + 4, 8)
            lbl_b = GraphicTextItem(str(2 * i + 2), px + 4, h - 22)
            items.extend([l_top, l_bot, d_top, d_bot, blade, x1, x2, lbl_t, lbl_b])

        tag_q = GraphicTextItem("Q", left + 3, 10)
        tag_q.setFont(QFont("Sans Serif", 8, QFont.Bold))
        items.append(tag_q)
        items.append(box)

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Motores Eléctricos (Trifásicos y Monofásicos)
    # ─────────────────────────────────────────────────────────────────────────
    elif c_type == 'motor' or 'motor' in comp_key:
        top_terms = [t for t in terminals if t.get('y', 0) <= mid_y]
        bot_terms = [t for t in terminals if t.get('y', 0) > mid_y]

        phase_terms = [t for t in top_terms if t.get('id', '') != 'PE'] or top_terms or terminals
        center_x = sum(float(t.get('x', 0)) for t in phase_terms) / max(1, len(phase_terms))
        radius = 28.0

        # Conexiones superiores
        for t in top_terms:
            tx = float(t.get('x', 0))
            dx = abs(tx - center_x)
            if dx <= radius:
                dy = math.sqrt(max(0.0, radius * radius - dx * dx))
                line = GraphicLineItem(tx, 0, tx, mid_y - dy)
            else:
                line = GraphicLineItem(tx, 0, tx, mid_y)
            lbl = GraphicTextItem(t.get('name', ''), tx - 6, 6)
            lbl.setFont(QFont("Sans Serif", 6, QFont.Bold))
            items.extend([line, lbl])

        # Conexiones inferiores (arranque estrella-triángulo o dahlander)
        for t in bot_terms:
            tx = float(t.get('x', 0))
            dx = abs(tx - center_x)
            if dx <= radius:
                dy = math.sqrt(max(0.0, radius * radius - dx * dx))
                line = GraphicLineItem(tx, mid_y + dy, tx, h)
            else:
                line = GraphicLineItem(tx, mid_y, tx, h)
            lbl = GraphicTextItem(t.get('name', ''), tx - 6, h - 20)
            lbl.setFont(QFont("Sans Serif", 6, QFont.Bold))
            items.extend([line, lbl])

        # Cuerpo del motor (círculo)
        body = GraphicCircleItem(center_x - radius, mid_y - radius, radius * 2, radius * 2)
        body.setPen(_pen("#ffffff", 2.2))

        # Texto 'M' central
        txt_m = GraphicTextItem("M", center_x - 10, mid_y - 18)
        txt_m.setFont(QFont("Sans Serif", 14, QFont.Bold))

        # Subtexto (3 ~ o 1 ~)
        is_1p = '1p' in comp_key or 'mono' in comp_key
        sub_text = "1 ~" if is_1p else "3 ~"
        txt_sub = GraphicTextItem(sub_text, center_x - 12, mid_y + 3)
        txt_sub.setFont(QFont("Sans Serif", 9, QFont.Bold))

        items.extend([body, txt_m, txt_sub])

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Fallback Genérico
    # ─────────────────────────────────────────────────────────────────────────
    else:
        # Caja con ID del componente y conexiones directas a los bornes
        box = GraphicRectItem(4, 4, max(40, w - 8), max(40, h - 8), rx=4, ry=4)
        box.setPen(_pen("#4a90e2", 1.5, Qt.DashLine))
        title = GraphicTextItem(comp_def.get('name', comp_key), 8, mid_y - 8)
        items.extend([box, title])
        for t in terminals:
            tx = float(t.get('x', 0))
            ty = float(t.get('y', 0))
            t_lbl = GraphicTextItem(t.get('name', ''), tx + 2, ty + 2)
            items.append(t_lbl)

    return items

