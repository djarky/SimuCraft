"""
Escena gráfica interactiva para previsualización y edición de símbolos y bornes.
"""
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class SymbolCanvasScene(QGraphicsScene):
    """Escena con cuadrícula eléctrica CADe SIMU (paso 6px y 18px) y caja de componente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-150, -150, 600, 600)
        self.comp_width = 90.0
        self.comp_height = 72.0
        self.svg_renderer = None
        self.comp_type = 'generic'
        self.grid_snap = 18

    def set_component_bounds(self, width: float, height: float, comp_type: str = 'generic', svg_renderer=None):
        self.comp_width = width
        self.comp_height = height
        self.comp_type = comp_type
        self.svg_renderer = svg_renderer
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Fondo oscuro técnico
        painter.fillRect(rect, QColor("#181a20"))

        # Rejilla fina (6px)
        painter.setPen(QPen(QColor("#222630"), 1))
        left = int(rect.left()) - (int(rect.left()) % 6)
        top = int(rect.top()) - (int(rect.top()) % 6)

        lines_6 = []
        for x in range(left, int(rect.right()), 6):
            if x % 18 != 0:
                lines_6.append(QPointF(x, rect.top()))
                lines_6.append(QPointF(x, rect.bottom()))
        for y in range(top, int(rect.bottom()), 6):
            if y % 18 != 0:
                lines_6.append(QPointF(rect.left(), y))
                lines_6.append(QPointF(rect.right(), y))
        if lines_6:
            painter.drawLines(lines_6)

        # Rejilla mayor (18px) - estándar de CADe SIMU
        painter.setPen(QPen(QColor("#2d3340"), 1.2))
        lines_18 = []
        left_18 = int(rect.left()) - (int(rect.left()) % 18)
        top_18 = int(rect.top()) - (int(rect.top()) % 18)
        for x in range(left_18, int(rect.right()), 18):
            lines_18.append(QPointF(x, rect.top()))
            lines_18.append(QPointF(x, rect.bottom()))
        for y in range(top_18, int(rect.bottom()), 18):
            lines_18.append(QPointF(rect.left(), y))
            lines_18.append(QPointF(rect.right(), y))
        if lines_18:
            painter.drawLines(lines_18)

        # Ejes de origen (0, 0)
        painter.setPen(QPen(QColor("#e74c3c"), 1.5, Qt.DashLine))
        painter.drawLine(0, int(rect.top()), 0, int(rect.bottom()))
        painter.drawLine(int(rect.left()), 0, int(rect.right()), 0)
        painter.setPen(QPen(QColor("#e74c3c")))
        painter.setFont(QFont("Sans Serif", 7, QFont.Bold))
        painter.drawText(4, -4, "(0,0) Origen")

        # -------------------------------------------------------------
        # Dibujar silueta o SVG del componente en el fondo
        # -------------------------------------------------------------
        comp_rect = QRectF(0, 0, self.comp_width, self.comp_height)

        # Caja exterior delimitadora del componente
        painter.setPen(QPen(QColor("#4a90e2"), 1.5, Qt.DashLine))
        painter.setBrush(QBrush(QColor(74, 144, 226, 18)))
        painter.drawRect(comp_rect)

        # Renderizar SVG si existe
        if self.svg_renderer and self.svg_renderer.isValid():
            self.svg_renderer.render(painter, comp_rect)
        else:
            # Dibujo esquemático indicativo según tipo
            painter.setPen(QPen(QColor("#a0b0c0"), 1.8))
            mid_y = self.comp_height / 2.0
            mid_x = self.comp_width / 2.0
            if 'motor' in self.comp_type:
                rad = min(mid_x, mid_y) - 6
                painter.setBrush(QBrush(QColor("#253040")))
                painter.drawEllipse(QPointF(mid_x, mid_y), rad, rad)
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Arial", 14, QFont.Bold))
                painter.drawText(int(mid_x - 7), int(mid_y + 5), "M")
            elif 'contactor' in self.comp_type:
                painter.setBrush(QBrush(QColor("#253040")))
                painter.drawRoundedRect(comp_rect.adjusted(6, 6, -6, -6), 4, 4)
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
                painter.drawText(int(mid_x - 12), int(mid_y + 4), "KM")
            elif 'breaker' in self.comp_type:
                painter.setBrush(QBrush(QColor("#2d3340")))
                painter.drawRect(comp_rect.adjusted(4, 4, -4, -4))
                painter.setPen(QPen(Qt.white))
                painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
                painter.drawText(int(mid_x - 6), int(mid_y + 4), "Q")

