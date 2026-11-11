"""
Escena gráfica interactiva con modos de dibujo vectorial (Select, Line, Rect, Circle, Text)
y rejilla eléctrica de snapping CADe SIMU.
"""
from typing import Optional, List
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicTextItem
)


class SymbolCanvasScene(QGraphicsScene):
    """Lienzo de dibujo CAD con modos interactivos de edición y snapping."""

    # Modos de herramienta
    TOOL_SELECT = "select"
    TOOL_LINE = "line"
    TOOL_RECT = "rect"
    TOOL_CIRCLE = "circle"
    TOOL_TEXT = "text"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-150, -150, 700, 700)
        self.comp_width = 90.0
        self.comp_height = 72.0
        self.comp_type = 'generic'
        self.grid_snap = 18

        # Estado de la herramienta activa
        self.active_tool = self.TOOL_SELECT
        self.active_pen_color = QColor("#ffffff")
        self.active_pen_width = 1.8
        self.active_pen_style = Qt.SolidLine
        self.active_brush_color: Optional[QColor] = None

        # Variables temporales para el trazo en curso
        self._is_drawing = False
        self._start_point = QPointF()
        self._temp_item: Optional[QGraphicsItem] = None

        # Callback cuando cambia algún item
        self.on_item_changed_callback = None

    def set_tool(self, tool_name: str):
        self.active_tool = tool_name
        self.clearSelection()

    def set_grid_snap(self, snap: int):
        self.grid_snap = snap

    def snap_point(self, pt: QPointF) -> QPointF:
        if self.grid_snap <= 1:
            return pt
        sx = round(pt.x() / self.grid_snap) * self.grid_snap
        sy = round(pt.y() / self.grid_snap) * self.grid_snap
        return QPointF(sx, sy)

    def set_component_bounds(self, width: float, height: float, comp_type: str = 'generic'):
        self.comp_width = width
        self.comp_height = height
        self.comp_type = comp_type
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Fondo oscuro de estación de trabajo
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

        # Rejilla mayor (18px)
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

        # Delimitador del componente
        comp_rect = QRectF(0, 0, self.comp_width, self.comp_height)
        painter.setPen(QPen(QColor("#4a90e2"), 1.5, Qt.DashLine))
        painter.setBrush(QBrush(QColor(74, 144, 226, 15)))
        painter.drawRect(comp_rect)

    def mousePressEvent(self, event):
        pos = self.snap_point(event.scenePos())

        if self.active_tool == self.TOOL_SELECT:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.LeftButton:
            self._is_drawing = True
            self._start_point = pos

            pen = QPen(self.active_pen_color, self.active_pen_width, self.active_pen_style, Qt.RoundCap)
            brush = QBrush(self.active_brush_color) if self.active_brush_color else Qt.NoBrush

            if self.active_tool == self.TOOL_LINE:
                self._temp_item = GraphicLineItem(pos.x(), pos.y(), pos.x(), pos.y())
                self._temp_item.setPen(pen)
                self.addItem(self._temp_item)

            elif self.active_tool == self.TOOL_RECT:
                self._temp_item = GraphicRectItem(pos.x(), pos.y(), 0, 0)
                self._temp_item.setPen(pen)
                self._temp_item.setBrush(brush)
                self.addItem(self._temp_item)

            elif self.active_tool == self.TOOL_CIRCLE:
                self._temp_item = GraphicCircleItem(pos.x(), pos.y(), 0, 0)
                self._temp_item.setPen(pen)
                self._temp_item.setBrush(brush)
                self.addItem(self._temp_item)

            elif self.active_tool == self.TOOL_TEXT:
                txt_item = GraphicTextItem("Texto", pos.x(), pos.y())
                txt_item.setDefaultTextColor(self.active_pen_color)
                self.addItem(txt_item)
                self._is_drawing = False
                if self.on_item_changed_callback:
                    self.on_item_changed_callback()

    def mouseMoveEvent(self, event):
        if not self._is_drawing or not self._temp_item:
            super().mouseMoveEvent(event)
            return

        cur = self.snap_point(event.scenePos())
        p1 = self._start_point

        if self.active_tool == self.TOOL_LINE and isinstance(self._temp_item, GraphicLineItem):
            self._temp_item.setLine(QLineF(p1, cur))

        elif self.active_tool == self.TOOL_RECT and isinstance(self._temp_item, GraphicRectItem):
            rx = min(p1.x(), cur.x())
            ry = min(p1.y(), cur.y())
            rw = abs(cur.x() - p1.x())
            rh = abs(cur.y() - p1.y())
            self._temp_item.setRect(QRectF(rx, ry, rw, rh))

        elif self.active_tool == self.TOOL_CIRCLE and isinstance(self._temp_item, GraphicCircleItem):
            rx = min(p1.x(), cur.x())
            ry = min(p1.y(), cur.y())
            rw = abs(cur.x() - p1.x())
            rh = abs(cur.y() - p1.y())
            self._temp_item.setRect(QRectF(rx, ry, rw, rh))

    def mouseReleaseEvent(self, event):
        if self._is_drawing:
            self._is_drawing = False
            self._temp_item = None
            if self.on_item_changed_callback:
                self.on_item_changed_callback()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # Eliminar items seleccionados con Delete o Backspace
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected = self.selectedItems()
            for it in selected:
                # No eliminar TerminalHandleItem por error aquí si está manejado por su lista
                from .terminal_handle import TerminalHandleItem
                if not isinstance(it, TerminalHandleItem):
                    self.removeItem(it)
            if self.on_item_changed_callback:
                self.on_item_changed_callback()
        super().keyPressEvent(event)

    def export_primitives_to_svg(self) -> str:
        """Convierte todas las primitivas vectoriales de la escena en un string SVG."""
        svg_parts = []
        for it in self.items():
            if hasattr(it, 'to_svg'):
                svg_parts.append(it.to_svg())

        w = int(self.comp_width)
        h = int(self.comp_height)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
            + "\n".join(svg_parts) + "\n</svg>"
        )
