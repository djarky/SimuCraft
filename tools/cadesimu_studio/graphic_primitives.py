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
    QPainterPath, QPolygonF
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
        self._rebuild_path()

    def _rebuild_path(self):
        path = QPainterPath()
        path.arcMoveTo(self._x, self._y, self._w, self._h, self._start)
        path.arcTo(self._x, self._y, self._w, self._h, self._start, self._span)
        self.setPath(path)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.drawRect(self.boundingRect().adjusted(-2, -2, 2, 2))

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

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPolygon(self.polygon())
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(-2, -2, 2, 2))

    def to_svg(self) -> str:
        pts = " ".join(f"{p.x():.2f},{p.y():.2f}" for p in self.polygon())
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        return f'<polygon points="{pts}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'


class GraphicTextItem(QGraphicsTextItem):
    """Texto o rótulo interactivo editable en el símbolo."""

    def __init__(self, text="Texto", x=0, y=0, parent=None):
        super().__init__(text, parent)
        self.setFlags(_EDITABLE_FLAGS)
        self.setDefaultTextColor(QColor("#ffffff"))
        self.setFont(QFont("Sans Serif", 9, QFont.Bold))
        self.setPos(x, y)
        self.setZValue(30)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def to_svg(self) -> str:
        pos = self.pos()
        txt = self.toPlainText()
        color = self.defaultTextColor().name()
        size = self.font().pointSize()
        return (f'<text x="{pos.x():.2f}" y="{pos.y() + size:.2f}" '
                f'font-size="{size}" font-family="sans-serif" font-weight="bold" '
                f'fill="{color}">{txt}</text>')
