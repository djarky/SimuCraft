"""
Escena gráfica interactiva con modos de dibujo vectorial (Select, Line, Rect, Circle, Text)
y rejilla eléctrica de snapping CADe SIMU.
"""
from typing import Optional, List
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicTextItem,
    GraphicArcItem, GraphicPolygonItem,
    primitive_to_dict, apply_primitive_state,
)


class SymbolBoundsItem(QGraphicsItem):
    """Marco del símbolo con tiradores para redimensionar su bounds.

    El origen (0,0) queda fijo: los tiradores derecho, inferior y de la
    esquina inferior derecha cambian el ancho y/o alto del componente.
    """

    HANDLE_SIZE = 10.0

    def __init__(self, scene: "SymbolCanvasScene"):
        super().__init__()
        self._scene = scene
        self._width = float(scene.comp_width)
        self._height = float(scene.comp_height)
        self._active_handle = None
        self.setZValue(10000)
        self.setAcceptHoverEvents(True)

    def set_bounds(self, width: float, height: float):
        width = max(20.0, float(width))
        height = max(20.0, float(height))
        if width == self._width and height == self._height:
            return
        self.prepareGeometryChange()
        self._width = width
        self._height = height
        self.update()

    def boundingRect(self) -> QRectF:
        margin = self.HANDLE_SIZE
        return QRectF(-margin, -margin, self._width + margin * 2, self._height + margin * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        for rect in self._handle_rects().values():
            path.addRect(rect)
        return path

    def _handle_rects(self):
        size = self.HANDLE_SIZE
        half = size / 2.0
        return {
            "right": QRectF(self._width - half, self._height / 2.0 - half, size, size),
            "bottom": QRectF(self._width / 2.0 - half, self._height - half, size, size),
            "corner": QRectF(self._width - half, self._height - half, size, size),
        }

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor("#4a90e2"), 1.5, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(0, 0, self._width, self._height))
        painter.setPen(QPen(QColor("#4a90e2"), 1.0))
        painter.setBrush(QBrush(QColor("#4a90e2")))
        for rect in self._handle_rects().values():
            painter.drawRect(rect)

    def _handle_at(self, pos: QPointF):
        for name, rect in self._handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle in {"right", "corner"}:
            self.setCursor(Qt.SizeHorCursor if handle == "right" else Qt.SizeFDiagCursor)
        elif handle == "bottom":
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        handle = self._handle_at(event.pos())
        if event.button() == Qt.LeftButton and handle:
            self._active_handle = handle
            event.accept()
            return
        self._active_handle = None
        event.ignore()

    def resize_to(self, width: float, height: float):
        """Redimensiona el bounds del símbolo (usado por tests y API interna)."""
        self._scene.set_bounds_from_interaction(
            max(20.0, float(width)), max(20.0, float(height))
        )

    def resize_to_scene_point(self, point: QPointF):
        """Aplica el redimensionado a partir de un punto en coordenadas de escena."""
        if self._active_handle in {"right", "corner"}:
            width = max(20.0, float(point.x()))
        else:
            width = self._width
        if self._active_handle in {"bottom", "corner"}:
            height = max(20.0, float(point.y()))
        else:
            height = self._height
        self._scene.set_bounds_from_interaction(width, height)

    def mouseMoveEvent(self, event):
        if not self._active_handle:
            event.ignore()
            return
        point = event.scenePos()
        if hasattr(self._scene, "snap_point"):
            point = self._scene.snap_point(point)
        self.resize_to_scene_point(point)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            event.accept()
            return
        event.ignore()


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
        self.undo_stack = None
        self._pending_state = None

        # Callback cuando cambia algún item o el bounds del símbolo
        self.on_item_changed_callback = None
        self.on_bounds_changed_callback = None

        # Marco interactivo del símbolo (tiradores de redimensionado)
        self.bounds_item = SymbolBoundsItem(self)
        self.addItem(self.bounds_item)

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
        self.comp_width = max(20.0, float(width))
        self.comp_height = max(20.0, float(height))
        self.comp_type = comp_type
        if hasattr(self, "bounds_item"):
            self.bounds_item.set_bounds(self.comp_width, self.comp_height)
        self.update()

    def set_bounds_from_interaction(self, width: float, height: float):
        """Actualiza el bounds tras arrastrar un tirador del marco."""
        self.set_component_bounds(width, height, self.comp_type)
        if self.on_bounds_changed_callback:
            self.on_bounds_changed_callback(self.comp_width, self.comp_height)

    # ---------------- Estado para undo/redo geométrico ----------------

    def capture_state(self) -> dict:
        """Captura geometría y estilo de las primitivas y el tamaño del símbolo."""
        primitives = []
        for item in self.items():
            if item is getattr(self, "bounds_item", None):
                continue
            data = primitive_to_dict(item)
            if data is not None:
                primitives.append((item, data))
        return {
            "width": float(self.comp_width),
            "height": float(self.comp_height),
            "primitives": primitives,
        }

    def apply_state(self, state: dict) -> None:
        """Restaura un estado capturado por :meth:`capture_state`."""
        if not isinstance(state, dict):
            return
        self.set_component_bounds(
            float(state.get("width", self.comp_width)),
            float(state.get("height", self.comp_height)),
            self.comp_type,
        )
        for item, data in state.get("primitives", []):
            if item.scene() is self:
                apply_primitive_state(item, data)
        if self.on_bounds_changed_callback:
            self.on_bounds_changed_callback(self.comp_width, self.comp_height)
        self.update()

    def push_state_change(self, before: dict, text: str = "Editar símbolo") -> bool:
        """Registra un cambio de geometría si el estado difiere del capturado."""
        if self.undo_stack is None or before is None:
            return False
        after = self.capture_state()
        if before == after:
            return False
        from .undo_commands import SceneStateCommand
        self.undo_stack.push(SceneStateCommand(self, before, after, text))
        return True

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

    def mousePressEvent(self, event):
        pos = self.snap_point(event.scenePos())

        if self.active_tool == self.TOOL_SELECT:
            # Captura antes de que el ítem aplique mover/redimensionar. El
            # comando se crea en mouseReleaseEvent si la geometría cambió.
            self._pending_state = self.capture_state()
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
            created = self._temp_item
            self._temp_item = None
            if created and self.undo_stack:
                from .undo_commands import AddItemsCommand
                # Ya añadido, creamos el comando para que undo() lo retire
                cmd = AddItemsCommand(self, [created])
                self.undo_stack.push(cmd)
            if self.on_item_changed_callback:
                self.on_item_changed_callback()
        super().mouseReleaseEvent(event)
        if self._pending_state is not None:
            before = self._pending_state
            self._pending_state = None
            self.push_state_change(before)

    def keyPressEvent(self, event):
        # Eliminar items seleccionados con Delete o Backspace
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            from .terminal_handle import TerminalHandleItem
            selected = [it for it in self.selectedItems() if not isinstance(it, TerminalHandleItem)]
            if selected:
                if self.undo_stack:
                    from .undo_commands import DeleteItemsCommand
                    self.undo_stack.push(DeleteItemsCommand(self, selected))
                else:
                    for it in selected:
                        self.removeItem(it)
                if self.on_item_changed_callback:
                    self.on_item_changed_callback()
            event.accept()
            return
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


from PySide6.QtWidgets import QGraphicsView


class SymbolGraphicsView(QGraphicsView):
    """Vista gráfica con zoom centrado en el cursor, desplazamiento suave y atajos CAD."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # Eliminar glitch de arrastre: modo de actualización inteligente
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self._is_panning = False
        self._pan_start = QPointF()

    def wheelEvent(self, event):
        """Zoom progresivo centrado en el cursor con Ctrl + Rueda del ratón."""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                return
            factor = 1.15 if delta > 0 else (1.0 / 1.15)
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._is_panning = True
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            self._pan_start = pos
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            delta = pos - self._pan_start
            self._pan_start = pos
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_panning and (event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton):
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Abre el diálogo modal de propiedades al hacer doble clic sobre un elemento.
        Los bornes (TerminalHandleItem) se editan pero con sus propios campos.
        """
        from .terminal_handle import TerminalHandleItem
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        item = self.itemAt(pos)
        if item:
            # Subir hasta el item raíz (sin padre)
            target = item
            while target.parentItem():
                target = target.parentItem()
            # Abrir propiedades solo para tipos conocidos (primitivas + bornes)
            from .properties_dialog import PrimitivePropertiesDialog
            try:
                dlg = PrimitivePropertiesDialog(target, self)
                if dlg.exec():
                    sc = self.scene()
                    if sc and hasattr(sc, 'on_item_changed_callback') and sc.on_item_changed_callback:
                        sc.on_item_changed_callback()
            except Exception:
                pass  # Tipo no soportado → ignorar silenciosamente
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        nudge = 1.0 if (event.modifiers() & Qt.ShiftModifier) else 10.0
        selected = self.scene().selectedItems() if self.scene() else []
        if selected and event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            dx, dy = 0.0, 0.0
            if event.key() == Qt.Key_Left:
                dx = -nudge
            elif event.key() == Qt.Key_Right:
                dx = nudge
            elif event.key() == Qt.Key_Up:
                dy = -nudge
            elif event.key() == Qt.Key_Down:
                dy = nudge

            for it in selected:
                it.setPos(it.pos().x() + dx, it.pos().y() + dy)
            if hasattr(self.scene(), 'on_item_changed_callback') and self.scene().on_item_changed_callback:
                self.scene().on_item_changed_callback()
            event.accept()
            return

        super().keyPressEvent(event)
