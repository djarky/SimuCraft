"""
Elemento gráfico interactivo para manipulación de bornes y terminales.
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF

from .config import TERMINAL_TYPE_COLORS


class TerminalHandleItem(QGraphicsItem):
    """Pin o Borne interactivo arrastrable con encaje en rejilla y orientación."""

    TYPE_COLORS = TERMINAL_TYPE_COLORS

    def __init__(self, term_data: dict, on_change_callback, grid_snap: int = 18):
        super().__init__()
        self.term_data = term_data
        self.callback = on_change_callback
        self.grid_snap = grid_snap

        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setZValue(100)
        self.setPos(float(term_data.get('x', 0)), float(term_data.get('y', 0)))

    def boundingRect(self) -> QRectF:
        return QRectF(-18, -18, 56, 36)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)

        ttype = self.term_data.get('type', 'generic')
        color = self.TYPE_COLORS.get(ttype, QColor('#bdc3c7'))

        # Halo de selección
        if self.isSelected():
            painter.setPen(QPen(QColor('#00e5ff'), 2.5, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 229, 255, 40)))
            painter.drawEllipse(QPointF(0, 0), 12, 12)

        # Círculo del borne
        painter.setPen(QPen(Qt.white, 1.8))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(0, 0), 6, 6)

        # Flecha de orientación (N, S, E, W)
        orient = self.term_data.get('orientation', 'n').lower()
        painter.setPen(QPen(Qt.black, 1.5))
        painter.setBrush(QBrush(Qt.white))
        arrow = QPolygonF()
        if orient == 'n':
            arrow.append(QPointF(0, -12))
            arrow.append(QPointF(-3, -7))
            arrow.append(QPointF(3, -7))
        elif orient == 's':
            arrow.append(QPointF(0, 12))
            arrow.append(QPointF(-3, 7))
            arrow.append(QPointF(3, 7))
        elif orient == 'e':
            arrow.append(QPointF(12, 0))
            arrow.append(QPointF(7, -3))
            arrow.append(QPointF(7, 3))
        elif orient == 'w':
            arrow.append(QPointF(-12, 0))
            arrow.append(QPointF(-7, -3))
            arrow.append(QPointF(-7, 3))
        if not arrow.isEmpty():
            painter.drawPolygon(arrow)

        # Etiqueta de texto (ID o nombre del borne)
        name = self.term_data.get('name') or self.term_data.get('id', '')
        painter.setPen(QPen(QColor('#ffffff')))
        font = QFont("Sans Serif", 7, QFont.Bold)
        painter.setFont(font)

        # Pequeña placa de fondo para legibilidad
        painter.setBrush(QBrush(QColor(20, 24, 30, 200)))
        painter.setPen(QPen(QColor(80, 90, 100), 1))
        painter.drawRoundedRect(8, -8, 26, 15, 3, 3)
        painter.setPen(QPen(Qt.white))
        painter.drawText(11, 3, name[:4])

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            snap = self.grid_snap
            if snap > 1:
                sx = round(new_pos.x() / snap) * snap
                sy = round(new_pos.y() / snap) * snap
                new_pos = QPointF(sx, sy)
            self.term_data['x'] = new_pos.x()
            self.term_data['y'] = new_pos.y()
            if self.callback:
                self.callback(self)
            return new_pos
        return super().itemChange(change, value)

