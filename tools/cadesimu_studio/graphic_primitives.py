"""
Primitivas gráficas vectoriales interactivas para el editor de símbolos.
Cada elemento (línea, rectángulo, círculo, arco, polígono, texto) es un
QGraphicsItem seleccionable, arrastrable y modificable con exportación a SVG.
"""
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsPolygonItem
)
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter,
    QPainterPath, QPolygonF, QTransform
)


# ─── Flags comunes ─────────────────────────────────────────────────────────────
_EDITABLE_FLAGS = (
    QGraphicsItem.ItemIsMovable |
    QGraphicsItem.ItemIsSelectable |
    QGraphicsItem.ItemSendsGeometryChanges
)

_SEL_PEN = QPen(QColor("#00e5ff"), 1.2, Qt.DashLine)
_DEFAULT_PEN = QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap)


class GraphicLineItem(QGraphicsLineItem):
    """Línea vectorial interactiva con ajuste magnético a rejilla y tiradores de extremo."""

    def __init__(self, x1=0, y1=0, x2=20, y2=20, parent=None):
        super().__init__(x1, y1, x2, y2, parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap))
        self.setZValue(20)
        self._dragging_endpoint = 0

    def boundingRect(self) -> QRectF:
        # Incluye el margen del grosor + 6px extra para los tiradores de extremo
        extra = self.pen().widthF() / 2.0 + 6.0
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(_SEL_PEN)
            line = self.line()
            painter.setBrush(QBrush(QColor("#00e5ff")))
            # Tiradores en ambos extremos para arrastrar interactivamente
            painter.drawEllipse(line.p1(), 4, 4)
            painter.drawEllipse(line.p2(), 4, 4)

    def mousePressEvent(self, event):
        pos = event.pos()
        p1 = self.line().p1()
        p2 = self.line().p2()
        if (pos - p1).manhattanLength() <= 8:
            self._dragging_endpoint = 1
            event.accept()
            return
        elif (pos - p2).manhattanLength() <= 8:
            self._dragging_endpoint = 2
            event.accept()
            return
        self._dragging_endpoint = 0
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_dragging_endpoint', 0) in (1, 2):
            self.prepareGeometryChange()
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                scene_pos = self.mapToScene(pos)
                snapped_scene = self.scene().snap_point(scene_pos)
                pos = self.mapFromScene(snapped_scene)
            line = self.line()
            if self._dragging_endpoint == 1:
                self.setLine(QLineF(pos, line.p2()))
            else:
                self.setLine(QLineF(line.p1(), pos))
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_dragging_endpoint', 0) in (1, 2):
            self._dragging_endpoint = 0
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        line = self.line()
        p = self.pen()
        c = p.color().name()
        w = p.widthF()
        dash = ' stroke-dasharray="4,3"' if p.style() == Qt.DashLine else ''
        return (f'<line x1="{line.x1():.2f}" y1="{line.y1():.2f}" '
                f'x2="{line.x2():.2f}" y2="{line.y2():.2f}" '
                f'stroke="{c}" stroke-width="{w}"{dash} />')


class GraphicRectItem(QGraphicsRectItem):
    """Rectángulo vectorial interactivo con esquinas redondeables, relleno y tiradores."""

    def __init__(self, x=0, y=0, w=40, h=40, rx=0, ry=0, parent=None):
        super().__init__(x, y, w, h, parent)
        self.rx = rx
        self.ry = ry
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)
        self._resizing_corner = False

    def boundingRect(self) -> QRectF:
        extra = self.pen().widthF() / 2.0 + 6.0
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        r = self.rect()
        if self.rx > 0 or self.ry > 0:
            painter.drawRoundedRect(r, self.rx, self.ry)
        else:
            painter.drawRect(r)
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r.adjusted(-2, -2, 2, 2))
            # Tirador en la esquina inferior derecha
            painter.fillRect(QRectF(r.right() - 4, r.bottom() - 4, 8, 8), QColor("#00e5ff"))

    def mousePressEvent(self, event):
        pos = event.pos()
        r = self.rect()
        br = QPointF(r.right(), r.bottom())
        if (pos - br).manhattanLength() <= 8:
            self._resizing_corner = True
            event.accept()
            return
        self._resizing_corner = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self.prepareGeometryChange()
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                scene_pos = self.mapToScene(pos)
                snapped_scene = self.scene().snap_point(scene_pos)
                pos = self.mapFromScene(snapped_scene)
            r = self.rect()
            new_w = max(6.0, pos.x() - r.left())
            new_h = max(6.0, pos.y() - r.top())
            self.setRect(QRectF(r.left(), r.top(), new_w, new_h))
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self._resizing_corner = False
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        r = self.rect()
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        rx_attr = f' rx="{self.rx}"' if self.rx > 0 else ''
        ry_attr = f' ry="{self.ry}"' if self.ry > 0 else ''
        return (f'<rect x="{r.x():.2f}" y="{r.y():.2f}" '
                f'width="{r.width():.2f}" height="{r.height():.2f}"'
                f'{rx_attr}{ry_attr} stroke="{c}" stroke-width="{w}" fill="{fill}" />')


class GraphicCircleItem(QGraphicsEllipseItem):
    """Círculo o elipse vectorial interactiva con tirador de redimensionado."""

    def __init__(self, x=0, y=0, w=30, h=30, parent=None):
        super().__init__(x, y, w, h, parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)
        self._resizing_corner = False

    def boundingRect(self) -> QRectF:
        extra = self.pen().widthF() / 2.0 + 6.0
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            r = self.rect()
            painter.drawRect(r.adjusted(-2, -2, 2, 2))
            # Tirador en la esquina inferior derecha
            painter.fillRect(QRectF(r.right() - 4, r.bottom() - 4, 8, 8), QColor("#00e5ff"))

    def mousePressEvent(self, event):
        pos = event.pos()
        r = self.rect()
        br = QPointF(r.right(), r.bottom())
        if (pos - br).manhattanLength() <= 8:
            self._resizing_corner = True
            event.accept()
            return
        self._resizing_corner = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self.prepareGeometryChange()
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                scene_pos = self.mapToScene(pos)
                snapped_scene = self.scene().snap_point(scene_pos)
                pos = self.mapFromScene(snapped_scene)
            r = self.rect()
            new_w = max(6.0, pos.x() - r.left())
            new_h = max(6.0, pos.y() - r.top())
            self.setRect(QRectF(r.left(), r.top(), new_w, new_h))
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self._resizing_corner = False
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        r = self.rect()
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        cx = r.x() + r.width() / 2.0
        cy = r.y() + r.height() / 2.0
        rx = r.width() / 2.0
        ry = r.height() / 2.0
        if abs(rx - ry) < 0.1:
            return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{rx:.2f}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'
        return f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'


class GraphicArcItem(QGraphicsPathItem):
    """Arco de elipse vectorial interactivo (sub-arco de un círculo/elipse)."""

    def __init__(self, x=0, y=0, w=30, h=30, start_angle=0, span_angle=90, parent=None):
        super().__init__(parent)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._start = start_angle   # grados, 0 = este (3 h del reloj)
        self._span = span_angle     # positivo = anti-horario
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)
        self._resizing_corner = False
        self._rebuild_path()

    def _rebuild_path(self):
        path = QPainterPath()
        path.arcMoveTo(self._x, self._y, self._w, self._h, self._start)
        path.arcTo(self._x, self._y, self._w, self._h, self._start, self._span)
        self.setPath(path)

    def boundingRect(self) -> QRectF:
        extra = self.pen().widthF() / 2.0 + 6.0
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def _handle_rect(self) -> QRectF:
        r = self.path().boundingRect()
        return QRectF(r.right() - 4, r.bottom() - 4, 8, 8)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())
        if self.isSelected():
            r = self.path().boundingRect()
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r.adjusted(-2, -2, 2, 2))
            painter.fillRect(self._handle_rect(), QColor("#00e5ff"))

    def mousePressEvent(self, event):
        if self._handle_rect().contains(event.pos()):
            self._resizing_corner = True
            event.accept()
            return
        self._resizing_corner = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self.prepareGeometryChange()
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                pos = self.mapFromScene(
                    self.scene().snap_point(self.mapToScene(pos))
                )
            self._w = max(6.0, pos.x() - self._x)
            self._h = max(6.0, pos.y() - self._y)
            self._rebuild_path()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self._resizing_corner = False
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        import math
        # Convertir a path SVG arc
        cx = self._x + self._w / 2.0
        cy = self._y + self._h / 2.0
        rx = self._w / 2.0
        ry = self._h / 2.0
        a1 = math.radians(-self._start)
        a2 = math.radians(-(self._start + self._span))
        x1 = cx + rx * math.cos(a1)
        y1 = cy + ry * math.sin(a1)
        x2 = cx + rx * math.cos(a2)
        y2 = cy + ry * math.sin(a2)
        large = 1 if abs(self._span) > 180 else 0
        sweep = 0 if self._span > 0 else 1
        p = self.pen()
        c = p.color().name()
        w = p.widthF()
        return (f'<path d="M {x1:.2f},{y1:.2f} A {rx:.2f},{ry:.2f} 0 {large},{sweep} {x2:.2f},{y2:.2f}" '
                f'stroke="{c}" stroke-width="{w}" fill="none" />')


class GraphicPolygonItem(QGraphicsPolygonItem):
    """Polígono vectorial interactivo (triángulos, flechas, formas libres)."""

    def __init__(self, points: list, parent=None):
        """
        points: lista de (x, y) tuplas o QPointF
        """
        polygon = QPolygonF([QPointF(p[0], p[1]) if not isinstance(p, QPointF) else p
                             for p in points])
        super().__init__(polygon, parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)
        self._resizing_corner = False
        self._resize_origin_rect = QRectF()
        self._resize_origin_points = QPolygonF()

    def boundingRect(self) -> QRectF:
        extra = self.pen().widthF() / 2.0 + 6.0
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def _shape_rect(self) -> QRectF:
        return self.polygon().boundingRect()

    def _handle_rect(self) -> QRectF:
        r = self._shape_rect()
        return QRectF(r.right() - 4, r.bottom() - 4, 8, 8)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPolygon(self.polygon())
        if self.isSelected():
            r = self._shape_rect()
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r.adjusted(-2, -2, 2, 2))
            painter.fillRect(self._handle_rect(), QColor("#00e5ff"))

    def mousePressEvent(self, event):
        if self._handle_rect().contains(event.pos()):
            self._resizing_corner = True
            self._resize_origin_rect = QRectF(self._shape_rect())
            self._resize_origin_points = QPolygonF(self.polygon())
            event.accept()
            return
        self._resizing_corner = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self.prepareGeometryChange()
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                pos = self.mapFromScene(
                    self.scene().snap_point(self.mapToScene(pos))
                )
            origin = self._resize_origin_rect
            if origin.width() <= 0 or origin.height() <= 0:
                event.accept()
                return
            new_w = max(6.0, pos.x() - origin.left())
            new_h = max(6.0, pos.y() - origin.top())
            sx = new_w / origin.width()
            sy = new_h / origin.height()
            points = QPolygonF()
            for point in self._resize_origin_points:
                points.append(QPointF(
                    origin.left() + (point.x() - origin.left()) * sx,
                    origin.top() + (point.y() - origin.top()) * sy,
                ))
            self.setPolygon(points)
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self._resizing_corner = False
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        pts = " ".join(f"{p.x():.2f},{p.y():.2f}" for p in self.polygon())
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        return f'<polygon points="{pts}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'


class GraphicPathItem(QGraphicsPathItem):
    """Trayectoria SVG genérica (curvas, arcos y subrutas) editable."""

    def __init__(self, path=None, parent=None):
        super().__init__(path if isinstance(path, QPainterPath) else QPainterPath(), parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPath(self.path())
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(-2, -2, 2, 2))

    def to_svg(self) -> str:
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        return (
            f'<path d="{_qpainterpath_to_svg_d(self.path())}" '
            f'stroke="{c}" stroke-width="{w}" fill="{fill}" />'
        )


def _qpainterpath_to_svg_d(path: QPainterPath) -> str:
    """Convierte una ``QPainterPath`` en un atributo SVG ``d``."""
    parts = []
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        kind = element.type
        if kind == QPainterPath.MoveToElement:
            parts.append(f"M {element.x:.2f} {element.y:.2f}")
            index += 1
        elif kind == QPainterPath.LineToElement:
            parts.append(f"L {element.x:.2f} {element.y:.2f}")
            index += 1
        elif kind == QPainterPath.CurveToElement and index + 2 < count:
            control1 = element
            control2 = path.elementAt(index + 1)
            end = path.elementAt(index + 2)
            parts.append(
                f"C {control1.x:.2f} {control1.y:.2f} "
                f"{control2.x:.2f} {control2.y:.2f} "
                f"{end.x:.2f} {end.y:.2f}"
            )
            index += 3
        else:
            index += 1
    return " ".join(parts)


class GraphicTextItem(QGraphicsTextItem):
    """Texto o rótulo interactivo editable en el símbolo."""

    def __init__(self, text="Texto", x=0, y=0, parent=None):
        super().__init__(text, parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setDefaultTextColor(QColor("#ffffff"))
        self.setFont(QFont("Sans Serif", 9, QFont.Bold))
        self.setPos(x, y)
        self.setZValue(30)
        self._resizing_corner = False
        self._resize_origin_rect = QRectF()
        self._resize_origin_font_size = 9.0

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-6, -6, 6, 6)

    def _handle_rect(self) -> QRectF:
        r = super().boundingRect()
        return QRectF(r.right() - 4, r.bottom() - 4, 8, 8)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(super().boundingRect())
            painter.fillRect(self._handle_rect(), QColor("#00e5ff"))

    def mousePressEvent(self, event):
        if self._handle_rect().contains(event.pos()):
            self._resizing_corner = True
            self._resize_origin_rect = QRectF(super().boundingRect())
            size = self.font().pointSizeF()
            if size <= 0:
                size = float(self.font().pointSize() or 9)
            self._resize_origin_font_size = max(4.0, size)
            event.accept()
            return
        self._resizing_corner = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            pos = event.pos()
            if self.scene() and hasattr(self.scene(), 'snap_point'):
                pos = self.mapFromScene(
                    self.scene().snap_point(self.mapToScene(pos))
                )
            origin = self._resize_origin_rect
            if origin.height() <= 0:
                event.accept()
                return
            new_h = max(6.0, pos.y() - origin.top())
            factor = new_h / origin.height()
            new_size = max(4.0, self._resize_origin_font_size * factor)
            font = self.font()
            font.setPointSizeF(new_size)
            self.setFont(font)
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing_corner', False):
            self._resizing_corner = False
            if self.scene() and hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def to_svg(self) -> str:
        pos = self.pos()
        txt = self.toPlainText()
        color = self.defaultTextColor().name()
        size = self.font().pointSizeF()
        if size <= 0:
            size = float(self.font().pointSize() or 9)
        weight = "bold" if self.font().bold() else "normal"
        family = self.font().family() or "sans-serif"
        return (f'<text x="{pos.x():.2f}" y="{pos.y() + size:.2f}" '
                f'font-size="{size:.2f}" font-family="{family}" font-weight="{weight}" '
                f'fill="{color}">{txt}</text>')


def clone_graphic_item(item, offset=(0.0, 0.0)):
    """Clona una primitiva editable sin compartir estado con el original.

    Se usa para copy/paste y para duplicar símbolos. Devuelve ``None`` si el
    ítem no es una primitiva conocida (por ejemplo, un borne).
    """
    clone = None
    if isinstance(item, GraphicLineItem):
        line = item.line()
        clone = GraphicLineItem(line.x1(), line.y1(), line.x2(), line.y2())
        clone.setPen(QPen(item.pen()))
    elif isinstance(item, GraphicRectItem):
        rect = item.rect()
        clone = GraphicRectItem(
            rect.x(), rect.y(), rect.width(), rect.height(), item.rx, item.ry
        )
        clone.setPen(QPen(item.pen()))
        clone.setBrush(QBrush(item.brush()))
    elif isinstance(item, GraphicCircleItem):
        rect = item.rect()
        clone = GraphicCircleItem(rect.x(), rect.y(), rect.width(), rect.height())
        clone.setPen(QPen(item.pen()))
        clone.setBrush(QBrush(item.brush()))
    elif isinstance(item, GraphicArcItem):
        clone = GraphicArcItem(
            item._x, item._y, item._w, item._h, item._start, item._span
        )
        clone.setPen(QPen(item.pen()))
    elif isinstance(item, GraphicPolygonItem):
        clone = GraphicPolygonItem(
            [(point.x(), point.y()) for point in item.polygon()]
        )
        clone.setPen(QPen(item.pen()))
        clone.setBrush(QBrush(item.brush()))
    elif isinstance(item, GraphicPathItem):
        clone = GraphicPathItem(QPainterPath(item.path()))
        clone.setPen(QPen(item.pen()))
        clone.setBrush(QBrush(item.brush()))
    elif isinstance(item, GraphicTextItem):
        pos = item.pos()
        clone = GraphicTextItem(item.toPlainText(), pos.x(), pos.y())
        clone.setDefaultTextColor(QColor(item.defaultTextColor()))
        clone.setFont(QFont(item.font()))
    else:
        return None

    base_pos = item.pos()
    clone.setPos(base_pos.x() + offset[0], base_pos.y() + offset[1])
    clone.setTransform(item.transform())
    clone.setZValue(item.zValue())
    clone.setOpacity(item.opacity())
    clone.setVisible(item.isVisible())
    return clone


# ─── Serialización de primitivas ───────────────────────────────────────────────
# ``visual["primitives"]`` guarda la geometría editable del Studio. Es la
# fuente de verdad para recargar el editor; ``svg_content`` sigue siendo el
# formato que consume SimuCraft para renderizar el símbolo.

_PEN_STYLES = {
    Qt.SolidLine: "solid",
    Qt.DashLine: "dash",
    Qt.DotLine: "dot",
    Qt.DashDotLine: "dashdot",
    Qt.DashDotDotLine: "dashdotdot",
    Qt.CustomDashLine: "custom",
}
_PEN_STYLES_REVERSE = {value: key for key, value in _PEN_STYLES.items()}


def _color_to_dict(color: QColor) -> dict:
    return {"color": color.name(), "alpha": int(color.alpha())}


def _color_from_dict(data, default: QColor = None) -> QColor:
    if not isinstance(data, dict):
        return QColor(default or "#ffffff")
    color = QColor(str(data.get("color") or "#ffffff"))
    if not color.isValid():
        color = QColor(default or "#ffffff")
    try:
        color.setAlpha(int(data.get("alpha", 255)))
    except (TypeError, ValueError):
        pass
    return color


def _pen_to_dict(pen: QPen) -> dict:
    return {
        "style": _PEN_STYLES.get(pen.style(), "solid"),
        "width": float(pen.widthF()),
        "color": _color_to_dict(pen.color()),
    }


def _pen_from_dict(data) -> QPen:
    if not isinstance(data, dict):
        return QPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap))
    style = _PEN_STYLES_REVERSE.get(str(data.get("style")), Qt.SolidLine)
    try:
        width = float(data.get("width", 1.8))
    except (TypeError, ValueError):
        width = 1.8
    if width <= 0:
        width = 1.0
    return QPen(_color_from_dict(data.get("color")), width, style, Qt.RoundCap, Qt.RoundJoin)


def _brush_to_dict(brush: QBrush):
    if brush.style() == Qt.NoBrush:
        return None
    return _color_to_dict(brush.color())


def _brush_from_dict(data):
    if not isinstance(data, dict):
        return QBrush(Qt.NoBrush)
    return QBrush(_color_from_dict(data))


def _element_type_value(kind) -> int:
    """Normaliza ``QPainterPath.ElementType`` a entero (PySide6 usa enums)."""
    return int(getattr(kind, "value", kind))


def _path_to_elements(path: QPainterPath) -> list:
    elements = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        elements.append([
            _element_type_value(element.type),
            float(element.x),
            float(element.y),
        ])
    return elements


def _path_from_elements(elements) -> QPainterPath:
    path = QPainterPath()
    if not isinstance(elements, list):
        return path
    index = 0
    while index < len(elements):
        try:
            kind, x, y = elements[index]
            kind = int(kind)
            x = float(x)
            y = float(y)
        except (TypeError, ValueError):
            index += 1
            continue
        if kind == _element_type_value(QPainterPath.MoveToElement):
            path.moveTo(x, y)
            index += 1
        elif kind == _element_type_value(QPainterPath.LineToElement):
            path.lineTo(x, y)
            index += 1
        elif kind == _element_type_value(QPainterPath.CurveToElement) and index + 2 < len(elements):
            try:
                _, x2, y2 = elements[index + 1]
                _, x3, y3 = elements[index + 2]
            except (TypeError, ValueError):
                index += 1
                continue
            path.cubicTo(x, y, float(x2), float(y2), float(x3), float(y3))
            index += 3
        else:
            index += 1
    return path


def _base_to_dict(item: QGraphicsItem, kind: str) -> dict:
    transform = item.transform()
    return {
        "kind": kind,
        "pos": [float(item.pos().x()), float(item.pos().y())],
        "transform": [
            float(transform.m11()), float(transform.m12()),
            float(transform.m21()), float(transform.m22()),
            float(transform.dx()), float(transform.dy()),
        ],
        "z": float(item.zValue()),
        "opacity": float(item.opacity()),
        "visible": bool(item.isVisible()),
        "pen": _pen_to_dict(item.pen()) if hasattr(item, "pen") else None,
        "brush": _brush_to_dict(item.brush()) if hasattr(item, "brush") else None,
    }


def primitive_to_dict(item) -> dict:
    """Convierte una primitiva editable en un diccionario JSON serializable."""
    if isinstance(item, GraphicLineItem):
        line = item.line()
        data = _base_to_dict(item, "line")
        data["line"] = [float(line.x1()), float(line.y1()), float(line.x2()), float(line.y2())]
        return data
    if isinstance(item, GraphicRectItem):
        rect = item.rect()
        data = _base_to_dict(item, "rect")
        data["rect"] = [float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height())]
        data["rx"] = float(item.rx)
        data["ry"] = float(item.ry)
        return data
    if isinstance(item, GraphicCircleItem):
        rect = item.rect()
        data = _base_to_dict(item, "circle")
        data["rect"] = [float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height())]
        return data
    if isinstance(item, GraphicArcItem):
        data = _base_to_dict(item, "arc")
        data.update({
            "x": float(item._x), "y": float(item._y),
            "w": float(item._w), "h": float(item._h),
            "start": float(item._start), "span": float(item._span),
        })
        return data
    if isinstance(item, GraphicPolygonItem):
        data = _base_to_dict(item, "polygon")
        data["points"] = [
            [float(point.x()), float(point.y())] for point in item.polygon()
        ]
        return data
    if isinstance(item, GraphicPathItem):
        data = _base_to_dict(item, "path")
        data["elements"] = _path_to_elements(item.path())
        return data
    if isinstance(item, GraphicTextItem):
        data = _base_to_dict(item, "text")
        font = item.font()
        size = font.pointSizeF()
        if size <= 0:
            size = float(font.pointSize() or 9)
        data.update({
            "text": item.toPlainText(),
            "color": _color_to_dict(item.defaultTextColor()),
            "font": {
                "family": font.family(),
                "size": float(size),
                "bold": bool(font.bold()),
                "italic": bool(font.italic()),
                "underline": bool(font.underline()),
            },
        })
        return data
    return None


def serialize_primitives(items) -> list:
    """Serializa una colección de ítems, ignorando bornes y elementos ajenos."""
    result = []
    for item in items:
        data = primitive_to_dict(item)
        if data is not None:
            result.append(data)
    return result


def apply_primitive_state(item, data: dict) -> None:
    """Aplica un estado serializado sobre una primitiva ya existente."""
    if not isinstance(data, dict):
        return

    if isinstance(item, GraphicLineItem) and "line" in data:
        try:
            x1, y1, x2, y2 = data["line"]
            item.setLine(QLineF(float(x1), float(y1), float(x2), float(y2)))
        except (TypeError, ValueError):
            pass
    elif isinstance(item, GraphicRectItem) and "rect" in data:
        try:
            x, y, w, h = data["rect"]
            item.setRect(QRectF(float(x), float(y), float(w), float(h)))
            item.rx = float(data.get("rx", 0))
            item.ry = float(data.get("ry", 0))
        except (TypeError, ValueError):
            pass
    elif isinstance(item, GraphicCircleItem) and "rect" in data:
        try:
            x, y, w, h = data["rect"]
            item.setRect(QRectF(float(x), float(y), float(w), float(h)))
        except (TypeError, ValueError):
            pass
    elif isinstance(item, GraphicArcItem):
        try:
            item.prepareGeometryChange()
            item._x = float(data.get("x", item._x))
            item._y = float(data.get("y", item._y))
            item._w = float(data.get("w", item._w))
            item._h = float(data.get("h", item._h))
            item._start = float(data.get("start", item._start))
            item._span = float(data.get("span", item._span))
            item._rebuild_path()
        except (TypeError, ValueError):
            pass
    elif isinstance(item, GraphicPolygonItem) and "points" in data:
        points = []
        for point in data.get("points") or []:
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError, IndexError):
                continue
        if points:
            item.setPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    elif isinstance(item, GraphicPathItem) and "elements" in data:
        item.setPath(_path_from_elements(data.get("elements")))
    elif isinstance(item, GraphicTextItem):
        if "text" in data:
            item.setPlainText(str(data.get("text", "")))
        if "color" in data:
            item.setDefaultTextColor(_color_from_dict(data.get("color")))
        font_data = data.get("font")
        if isinstance(font_data, dict):
            font = QFont(str(font_data.get("family") or "Sans Serif"))
            try:
                font.setPointSizeF(max(1.0, float(font_data.get("size", 9))))
            except (TypeError, ValueError):
                font.setPointSizeF(9.0)
            font.setBold(bool(font_data.get("bold")))
            font.setItalic(bool(font_data.get("italic")))
            font.setUnderline(bool(font_data.get("underline")))
            item.setFont(font)

    if "pen" in data and hasattr(item, "setPen"):
        item.setPen(_pen_from_dict(data.get("pen")))
    if "brush" in data and hasattr(item, "setBrush"):
        item.setBrush(_brush_from_dict(data.get("brush")))
    if "z" in data:
        try:
            item.setZValue(float(data["z"]))
        except (TypeError, ValueError):
            pass
    if "opacity" in data:
        try:
            item.setOpacity(float(data["opacity"]))
        except (TypeError, ValueError):
            pass
    if "visible" in data:
        item.setVisible(bool(data["visible"]))
    if "transform" in data:
        try:
            m11, m12, m21, m22, dx, dy = data["transform"]
            item.setTransform(QTransform(
                float(m11), float(m12), float(m21), float(m22), float(dx), float(dy)
            ))
        except (TypeError, ValueError):
            pass
    if "pos" in data:
        try:
            x, y = data["pos"]
            item.setPos(float(x), float(y))
        except (TypeError, ValueError):
            pass


def primitive_from_dict(data: dict):
    """Reconstruye una primitiva editable desde su diccionario serializado."""
    if not isinstance(data, dict):
        return None
    kind = data.get("kind")
    item = None
    if kind == "line":
        item = GraphicLineItem()
    elif kind == "rect":
        item = GraphicRectItem()
    elif kind == "circle":
        item = GraphicCircleItem()
    elif kind == "arc":
        item = GraphicArcItem()
    elif kind == "polygon":
        item = GraphicPolygonItem([])
    elif kind == "path":
        item = GraphicPathItem()
    elif kind == "text":
        item = GraphicTextItem("")
    if item is None:
        return None
    apply_primitive_state(item, data)
    return item
