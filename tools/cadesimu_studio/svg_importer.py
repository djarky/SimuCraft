"""Convierte SVG en primitivas editables del Symbol Studio.

El editor trabaja sobre un lienzo oscuro, por lo que los trazos y textos
oscuros de los SVG canónicos se adaptan a blanco. Los colores industriales
(rojo, azul, verde, etc.) se conservan.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
)

from .graphic_primitives import (
    GraphicCircleItem,
    GraphicLineItem,
    GraphicPathItem,
    GraphicPolygonItem,
    GraphicRectItem,
    GraphicTextItem,
)

_NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_SKIP_TAGS = {
    "defs",
    "clippath",
    "mask",
    "symbol",
    "marker",
    "pattern",
    "title",
    "desc",
    "metadata",
    "style",
    "script",
    "image",
}
_PRESENTATION_ATTRS = (
    "fill",
    "fill-opacity",
    "stroke",
    "stroke-opacity",
    "stroke-width",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "font-size",
    "font-family",
    "font-weight",
    "font-style",
    "display",
    "visibility",
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _numbers(value: Optional[str]) -> List[float]:
    if not value:
        return []
    return [float(number) for number in _NUMBER_RE.findall(value)]


def _to_float(value, default: float = 0.0) -> float:
    numbers = _numbers(str(value)) if value is not None else []
    return numbers[0] if numbers else default


def _parse_transform(value: Optional[str]) -> QTransform:
    transform = QTransform()
    if not value:
        return transform
    for name, args_text in re.findall(r"([a-zA-Z]+)\s*\(([^)]*)\)", value):
        args = _numbers(args_text)
        name = name.lower()
        if name == "matrix" and len(args) >= 6:
            current = QTransform(
                args[0], args[1], args[2], args[3], args[4], args[5]
            )
        elif name == "translate" and args:
            current = QTransform.fromTranslate(
                args[0], args[1] if len(args) > 1 else 0.0
            )
        elif name == "scale" and args:
            current = QTransform.fromScale(
                args[0], args[1] if len(args) > 1 else args[0]
            )
        elif name == "rotate" and args:
            current = QTransform()
            if len(args) >= 3:
                current.translate(args[1], args[2])
                current.rotate(args[0])
                current.translate(-args[1], -args[2])
            else:
                current.rotate(args[0])
        elif name == "skewx" and args:
            current = QTransform()
            current.shear(args[0] * 3.141592653589793 / 180.0, 0.0)
        elif name == "skewy" and args:
            current = QTransform()
            current.shear(0.0, args[0] * 3.141592653589793 / 180.0)
        else:
            continue
        transform = current * transform
    return transform


def _merge_style(parent: Dict[str, str], element) -> Dict[str, str]:
    style = dict(parent)
    for key in _PRESENTATION_ATTRS:
        value = element.get(key)
        if value is not None:
            style[key] = value
    for declaration in (element.get("style") or "").split(";"):
        if ":" not in declaration:
            continue
        key, value = declaration.split(":", 1)
        key = key.strip()
        if key:
            style[key] = value.strip()
    return style


def _adapt_color(value: Optional[str]) -> Optional[QColor]:
    """Adapta colores oscuros al lienzo del Studio y conserva los colores."""
    if not value:
        return None
    text = value.strip()
    if not text or text.lower() in {"none", "transparent"}:
        return None
    if text.lower() == "currentcolor":
        text = "#000000"
    color = QColor(text)
    if not color.isValid():
        return QColor("#ffffff")
    if color.alpha() == 0:
        return None
    # Negro y grises muy oscuros son invisibles sobre el lienzo #181a20.
    if max(color.red(), color.green(), color.blue()) < 80:
        color = QColor("#ffffff")
    return color


def _pen_from_style(style: Dict[str, str]):
    color = _adapt_color(style.get("stroke"))
    if color is None:
        return QPen(Qt.NoPen)
    width = _to_float(style.get("stroke-width"), 1.0)
    if width <= 0:
        width = 1.0
    if width < 0.8:
        width = 1.0
    dash = (style.get("stroke-dasharray") or "").strip().lower()
    pen_style = Qt.SolidLine
    if dash and dash not in {"none", "0"}:
        pen_style = Qt.DashLine
    opacity = _to_float(style.get("stroke-opacity"), 1.0)
    color.setAlphaF(max(0.0, min(1.0, opacity)))
    return QPen(color, width, pen_style, Qt.RoundCap, Qt.RoundJoin)


def _brush_from_style(style: Dict[str, str]):
    color = _adapt_color(style.get("fill", "black"))
    if color is None:
        return QBrush(Qt.NoBrush)
    opacity = _to_float(style.get("fill-opacity"), 1.0)
    color.setAlphaF(max(0.0, min(1.0, opacity)))
    return QBrush(color)


def _parse_path_data(data: str) -> QPainterPath:
    """Parser suficiente para M/L/H/V/C/S/Q/T/A/Z de SVG."""
    path = QPainterPath()
    if not data:
        return path

    tokens = re.findall(
        r"[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?",
        data,
    )
    index = 0
    command = None
    current = QPointF(0.0, 0.0)
    start = QPointF(0.0, 0.0)
    last_control = None
    last_command = ""

    def take(count: int) -> Optional[List[float]]:
        nonlocal index
        if index + count > len(tokens):
            return None
        values = []
        for _ in range(count):
            token = tokens[index]
            if token.isalpha():
                return None
            values.append(float(token))
            index += 1
        return values

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            command = token
            index += 1
        if command is None:
            index += 1
            continue

        upper = command.upper()
        relative = command.islower()

        if upper == "Z":
            path.closeSubpath()
            current = QPointF(start)
            last_command = "Z"
            command = None
            last_control = None
            continue

        if upper == "M":
            values = take(2)
            if values is None:
                break
            x, y = values
            if relative:
                x += current.x()
                y += current.y()
            current = QPointF(x, y)
            start = QPointF(current)
            path.moveTo(current)
            last_command = "M"
            last_control = None
            # Pares adicionales de un moveto son lineto.
            command = "l" if relative else "L"
            continue

        if upper == "L":
            values = take(2)
            if values is None:
                break
            x, y = values
            if relative:
                x += current.x()
                y += current.y()
            current = QPointF(x, y)
            path.lineTo(current)
            last_command = "L"
            last_control = None
            continue

        if upper == "H":
            values = take(1)
            if values is None:
                break
            x = values[0] + (current.x() if relative else 0.0)
            current = QPointF(x, current.y())
            path.lineTo(current)
            last_command = "H"
            last_control = None
            continue

        if upper == "V":
            values = take(1)
            if values is None:
                break
            y = values[0] + (current.y() if relative else 0.0)
            current = QPointF(current.x(), y)
            path.lineTo(current)
            last_command = "V"
            last_control = None
            continue

        if upper == "C":
            values = take(6)
            if values is None:
                break
            x1, y1, x2, y2, x, y = values
            if relative:
                x1 += current.x()
                y1 += current.y()
                x2 += current.x()
                y2 += current.y()
                x += current.x()
                y += current.y()
            control1 = QPointF(x1, y1)
            control2 = QPointF(x2, y2)
            end = QPointF(x, y)
            path.cubicTo(control1, control2, end)
            last_control = control2
            current = end
            last_command = "C"
            continue

        if upper == "S":
            values = take(4)
            if values is None:
                break
            x2, y2, x, y = values
            if relative:
                x2 += current.x()
                y2 += current.y()
                x += current.x()
                y += current.y()
            if last_command in {"C", "S"} and last_control is not None:
                control1 = QPointF(
                    2 * current.x() - last_control.x(),
                    2 * current.y() - last_control.y(),
                )
            else:
                control1 = QPointF(current)
            control2 = QPointF(x2, y2)
            end = QPointF(x, y)
            path.cubicTo(control1, control2, end)
            last_control = control2
            current = end
            last_command = "S"
            continue

        if upper == "Q":
            values = take(4)
            if values is None:
                break
            x1, y1, x, y = values
            if relative:
                x1 += current.x()
                y1 += current.y()
                x += current.x()
                y += current.y()
            control = QPointF(x1, y1)
            end = QPointF(x, y)
            path.quadTo(control, end)
            last_control = control
            current = end
            last_command = "Q"
            continue

        if upper == "T":
            values = take(2)
            if values is None:
                break
            x, y = values
            if relative:
                x += current.x()
                y += current.y()
            if last_command in {"Q", "T"} and last_control is not None:
                control = QPointF(
                    2 * current.x() - last_control.x(),
                    2 * current.y() - last_control.y(),
                )
            else:
                control = QPointF(current)
            end = QPointF(x, y)
            path.quadTo(control, end)
            last_control = control
            current = end
            last_command = "T"
            continue

        if upper == "A":
            values = take(7)
            if values is None:
                break
            _rx, _ry, _rotation, _large, _sweep, x, y = values
            if relative:
                x += current.x()
                y += current.y()
            # Aproximación suficiente para símbolos eléctricos; los SVG
            # canónicos de SimuCraft usan curvas cúbicas, no arcos A.
            end = QPointF(x, y)
            path.lineTo(end)
            current = end
            last_command = "A"
            last_control = None
            continue

        # Comando no soportado: evitar bucle infinito.
        index += 1

    return path


class SvgVectorImporter:
    """Extrae primitivas editables de un SVG o de un string SVG."""

    def import_from_svg(self, svg_content: str) -> Dict[str, Any]:
        if not isinstance(svg_content, str) or not svg_content.strip():
            return {"width": 90.0, "height": 72.0, "view_box": None, "items": []}
        try:
            root = ET.fromstring(svg_content)
        except ET.ParseError:
            return {"width": 90.0, "height": 72.0, "view_box": None, "items": []}

        view_box = self._view_box(root)
        width = view_box.width() if view_box else _to_float(root.get("width"), 90.0)
        height = view_box.height() if view_box else _to_float(root.get("height"), 72.0)
        if width <= 0:
            width = 90.0
        if height <= 0:
            height = 72.0

        items: List[Any] = []

        def walk(element, inherited_style: Dict[str, str], parent_transform: QTransform):
            tag = _local_name(element.tag)
            if tag in _SKIP_TAGS:
                return
            style = _merge_style(inherited_style, element)
            if style.get("display") == "none" or style.get("visibility") == "hidden":
                return
            transform = parent_transform * _parse_transform(element.get("transform"))

            if tag in {"svg", "g", "a"}:
                for child in element:
                    walk(child, style, transform)
                return

            if tag == "line":
                x1, y1 = _to_float(element.get("x1")), _to_float(element.get("y1"))
                x2, y2 = _to_float(element.get("x2")), _to_float(element.get("y2"))
                p1 = transform.map(QPointF(x1, y1))
                p2 = transform.map(QPointF(x2, y2))
                if p1 == p2:
                    return
                item = GraphicLineItem(p1.x(), p1.y(), p2.x(), p2.y())
                item.setPen(_pen_from_style(style))
                items.append(item)
                return

            if tag == "rect":
                x = _to_float(element.get("x"))
                y = _to_float(element.get("y"))
                w = _to_float(element.get("width"))
                h = _to_float(element.get("height"))
                if w <= 0 or h <= 0:
                    return
                rect = transform.mapRect(QRectF(x, y, w, h))
                if rect.width() <= 0 or rect.height() <= 0:
                    return
                item = GraphicRectItem(
                    rect.x(),
                    rect.y(),
                    rect.width(),
                    rect.height(),
                    _to_float(element.get("rx")),
                    _to_float(element.get("ry")),
                )
                item.setPen(_pen_from_style(style))
                item.setBrush(_brush_from_style(style))
                items.append(item)
                return

            if tag == "circle":
                cx = _to_float(element.get("cx"))
                cy = _to_float(element.get("cy"))
                radius = _to_float(element.get("r"))
                if radius <= 0:
                    return
                rect = transform.mapRect(
                    QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
                )
                item = GraphicCircleItem(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
                item.setPen(_pen_from_style(style))
                item.setBrush(_brush_from_style(style))
                items.append(item)
                return

            if tag == "ellipse":
                cx = _to_float(element.get("cx"))
                cy = _to_float(element.get("cy"))
                rx = _to_float(element.get("rx"))
                ry = _to_float(element.get("ry"))
                if rx <= 0 or ry <= 0:
                    return
                rect = transform.mapRect(
                    QRectF(cx - rx, cy - ry, rx * 2, ry * 2)
                )
                item = GraphicCircleItem(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
                item.setPen(_pen_from_style(style))
                item.setBrush(_brush_from_style(style))
                items.append(item)
                return

            if tag in {"polygon", "polyline"}:
                numbers = _numbers(element.get("points"))
                if len(numbers) < 4:
                    return
                points = [
                    transform.map(QPointF(numbers[i], numbers[i + 1]))
                    for i in range(0, len(numbers) - 1, 2)
                ]
                if tag == "polygon" and len(points) >= 3:
                    item = GraphicPolygonItem([(p.x(), p.y()) for p in points])
                    item.setPen(_pen_from_style(style))
                    item.setBrush(_brush_from_style(style))
                    items.append(item)
                else:
                    pen = _pen_from_style(style)
                    for start, end in zip(points, points[1:]):
                        if start == end:
                            continue
                        item = GraphicLineItem(
                            start.x(), start.y(), end.x(), end.y()
                        )
                        item.setPen(QPen(pen))
                        items.append(item)
                return

            if tag == "path":
                path = _parse_path_data(element.get("d") or "")
                if path.elementCount() == 0:
                    return
                mapped_path = transform.map(path)
                item = GraphicPathItem(mapped_path)
                item.setPen(_pen_from_style(style))
                item.setBrush(_brush_from_style(style))
                items.append(item)
                return

            if tag == "text":
                text = "".join(element.itertext()).strip()
                if not text:
                    return
                x = _to_float(element.get("x"))
                y = _to_float(element.get("y"))
                point = transform.map(QPointF(x, y))
                font_size = _to_float(style.get("font-size"), 9.0)
                if font_size <= 0:
                    font_size = 9.0
                item = GraphicTextItem(text, point.x(), point.y() - font_size)
                color = _adapt_color(style.get("fill", "black")) or QColor("#ffffff")
                item.setDefaultTextColor(color)
                weight = style.get("font-weight", "normal")
                bold = str(weight).lower() in {"bold", "bolder"} or _to_float(weight) >= 600
                font = QFont(style.get("font-family", "Sans Serif"))
                font.setPointSizeF(max(1.0, font_size))
                if bold:
                    font.setBold(True)
                item.setFont(font)
                items.append(item)
                return

        walk(root, {}, QTransform())
        return {
            "width": width,
            "height": height,
            "view_box": view_box,
            "items": items,
        }

    def import_from_file(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return self.import_from_svg(handle.read())

    @staticmethod
    def _view_box(root) -> Optional[QRectF]:
        values = _numbers(root.get("viewBox") or root.get("viewbox"))
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            return QRectF(values[0], values[1], values[2], values[3])
        return None
