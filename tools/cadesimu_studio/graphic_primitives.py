"""
Primitivas gráficas vectoriales interactivas para el editor de símbolos.
Cada elemento (línea, rectángulo, círculo, texto) es un QGraphicsItem seleccionable,
arrastrable y modificable con exportación a SVG.
"""
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsTextItem
)
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter


class GraphicLineItem(QGraphicsLineItem):
    """Línea vectorial interactiva con ajuste magnético a rejilla."""

    def __init__(self, x1=0, y1=0, x2=20, y2=20, parent=None):
        super().__init__(x1, y1, x2, y2, parent)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap))
        self.setZValue(20)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            line = self.line()
            # Puntos de control en extremos
            painter.setBrush(QBrush(QColor("#00e5ff")))
            painter.drawEllipse(line.p1(), 3, 3)
            painter.drawEllipse(line.p2(), 3, 3)

    def to_svg(self) -> str:
        line = self.line()
        p = self.pen()
        c = p.color().name()
        w = p.widthF()
        dash = ' stroke-dasharray="4,3"' if p.style() == Qt.DashLine else ''
        return f'<line x1="{line.x1()}" y1="{line.y1()}" x2="{line.x2()}" y2="{line.y2()}" stroke="{c}" stroke-width="{w}"{dash} />'


class GraphicRectItem(QGraphicsRectItem):
    """Rectángulo vectorial interactivo con esquinas redondeables y relleno."""

    def __init__(self, x=0, y=0, w=40, h=40, rx=0, ry=0, parent=None):
        super().__init__(x, y, w, h, parent)
        self.rx = rx
        self.ry = ry
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)

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

    def to_svg(self) -> str:
        r = self.rect()
        p = self.pen()
        b = self.brush()
        c = p.color().name()
        w = p.widthF()
        fill = b.color().name() if b.style() != Qt.NoBrush else "none"
        rx_attr = f' rx="{self.rx}"' if self.rx > 0 else ''
        ry_attr = f' ry="{self.ry}"' if self.ry > 0 else ''
        return f'<rect x="{r.x()}" y="{r.y()}" width="{r.width()}" height="{r.height()}"{rx_attr}{ry_attr} stroke="{c}" stroke-width="{w}" fill="{fill}" />'


class GraphicCircleItem(QGraphicsEllipseItem):
    """Círculo o elipse vectorial interactiva."""

    def __init__(self, x=0, y=0, w=30, h=30, parent=None):
        super().__init__(x, y, w, h, parent)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine))
        self.setBrush(Qt.NoBrush)
        self.setZValue(15)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawEllipse(self.rect())

        if self.isSelected():
            painter.setPen(QPen(QColor("#00e5ff"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(-2, -2, 2, 2))

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
            return f'<circle cx="{cx}" cy="{cy}" r="{rx}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke="{c}" stroke-width="{w}" fill="{fill}" />'


class GraphicTextItem(QGraphicsTextItem):
    """Texto o rótulo interactivo editable en el símbolo."""

    def __init__(self, text="Texto", x=0, y=0, parent=None):
        super().__init__(text, parent)
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
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
        return f'<text x="{pos.x()}" y="{pos.y() + size}" font-size="{size}" font-family="sans-serif" font-weight="bold" fill="{color}">{txt}</text>'

