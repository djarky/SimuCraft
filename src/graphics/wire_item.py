"""
Item gráfico para cables dinámicos en el circuito eléctrico.
Soporta ruteo ortogonal flexible con waypoints (nodos intermedios), puntos de bifurcación,
manejadores de control interactivos (handles) para mover y acomodar cables enrutados
manteniendo sus puntos de anclaje, tipos y colores normalizados y estados de simulación.
"""
from typing import Optional, Any, List
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem, QGraphicsEllipseItem, QStyleOptionGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QPainterPath, QColor, QPainter, QBrush, QCursor, QPainterPathStroker

from ..components.wire_types import get_wire_info, WIRE_CATALOG


class WireHandleItem(QGraphicsEllipseItem):
    """
    Manejador visual interactivo de control que permite desplazar vértices
    y segmentos de un cable manteniendo intactos sus anclajes de conexión.
    """

    def __init__(self, wire_item: "WireItem", handle_type: str, index: int = -1, parent=None):
        # Círculo de 12x12 px centrado en el punto de control
        super().__init__(-6, -6, 12, 12, parent)
        self.wire_item = wire_item
        self.handle_type = handle_type  # 'mid_x', 'waypoint', etc.
        self.index = index

        self.setZValue(30)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#2563eb"), 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.SizeAllCursor if handle_type == 'waypoint' else Qt.SizeHorCursor)

        self.setToolTip("Arrastrar para ajustar ruta | Clic derecho para eliminar nodo" if handle_type == 'waypoint' else "Arrastrar para ajustar ruta")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            event.accept()
            return
        elif event.button() == Qt.RightButton:
            if self.handle_type == 'waypoint' and self.wire_item:
                self.wire_item.remove_waypoint_at_index(self.index)
                event.accept()
                return
            elif self.handle_type == 'mid_x' and self.wire_item:
                self.wire_item.clear_waypoints()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            scene_pos = event.scenePos()
            # Snap a la cuadrícula de 20 px
            GRID = 20.0
            snap_x = round(scene_pos.x() / GRID) * GRID
            snap_y = round(scene_pos.y() / GRID) * GRID
            snap_pos = QPointF(snap_x, snap_y)

            self.wire_item.on_handle_dragged(self.handle_type, self.index, snap_pos)
            self.setPos(snap_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WireItem(QGraphicsPathItem):
    """
    Representa un conductor eléctrico en el esquema con propiedades físicas y normativas:
    - Ruteo flexible ortogonal con waypoints definidos por el usuario.
    - Soporte de bifurcaciones (T-junctions) con nodo de empalme visual.
    - Manejadores de control (handles) para mover segmentos y esquinas manteniendo fijos los anclajes.
    - Tipo y color configurado según normas IEC y CADe SIMU.
    """

    def __init__(
        self,
        terminal1=None,
        terminal2=None,
        pt1: Optional[QPointF] = None,
        pt2: Optional[QPointF] = None,
        wire_type: Any = 4000,
        color: Optional[str] = None,
        width: Optional[float] = None,
        style: Optional[Qt.PenStyle] = None,
        parent=None
    ):
        super().__init__(parent)
        self.terminal1 = terminal1
        self.terminal2 = terminal2
        self.pt1 = pt1
        self.pt2 = pt2
        self.edge_id = None  # ID de arista en CircuitGraph
        self.temp_end = None

        # Ruta flexible mediante waypoints intermedios
        self.waypoints: List[QPointF] = []
        self.route_offset_x: Optional[float] = None
        self.handles: List[WireHandleItem] = []

        # Puntos de bifurcación (empalme visual T)
        self.has_start_junction: bool = False
        self.has_end_junction: bool = False

        # Configuración técnica del conductor
        self.wire_type = 4000
        self.wire_color = QColor("#8B4513")
        self.wire_width = 2.0
        self.wire_style = Qt.SolidLine
        self.is_simulating = False
        self.sim_pen = None

        self.set_wire_type(wire_type, color=color, width=width, style=style)

        self.setZValue(5)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

        if terminal1 and not terminal2 and not pt2:
            self.temp_end = terminal1.get_scene_pos()
        elif pt1 and not pt2:
            self.temp_end = pt1

        self.update_path()

    def shape(self) -> QPainterPath:
        """Área de detección generosa de 14 px para facilitar clic, selección y arrastre táctil."""
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(self.path())

    # ── GESTIÓN DE WAYPOINTS Y RUTA FLEXIBLE ───────────────────────────────────

    def add_waypoint(self, pt: QPointF):
        """Añade un punto de paso/quiebre intermedio a la ruta del cable."""
        self.waypoints.append(QPointF(pt.x(), pt.y()))
        self.update_path()
        if self.isSelected():
            self.refresh_handles()

    def pop_waypoint(self) -> Optional[QPointF]:
        """Elimina el último waypoint de la ruta (deshacer paso)."""
        if self.waypoints:
            wp = self.waypoints.pop()
            self.update_path()
            if self.isSelected():
                self.refresh_handles()
            return wp
        return None

    def clear_waypoints(self):
        """Limpia todos los puntos intermedios volviendo al ruteo ortogonal directo."""
        self.waypoints.clear()
        self.route_offset_x = None
        self.update_path()
        if self.isSelected():
            self.refresh_handles()

    def set_wire_type(
        self,
        wire_type: Any,
        color: Optional[str] = None,
        width: Optional[float] = None,
        style: Optional[Qt.PenStyle] = None
    ):
        """Asigna el tipo normativo de cable, color, grosor y estilo."""
        info = get_wire_info(wire_type)
        self.wire_type = info["id"]

        chosen_color = color if color else info["color"]
        self.wire_color = QColor(chosen_color) if isinstance(chosen_color, str) else chosen_color
        self.wire_width = float(width) if width is not None else float(info.get("width", 2.0))
        self.wire_style = style if style is not None else info.get("style", Qt.SolidLine)

        self.apply_pen()
        self.update()

    def apply_pen(self):
        """Aplica la pluma visual del cable según su configuración activa."""
        if self.is_simulating and self.sim_pen:
            self.setPen(self.sim_pen)
        else:
            pen = QPen(self.wire_color, self.wire_width, self.wire_style)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            self.setPen(pen)

    def get_start_pos(self) -> QPointF:
        if self.terminal1:
            return self.terminal1.get_scene_pos()
        elif self.pt1:
            return self.pt1
        return QPointF(0, 0)

    def get_end_pos(self) -> QPointF:
        if self.terminal2:
            return self.terminal2.get_scene_pos()
        elif self.pt2:
            return self.pt2
        elif self.temp_end:
            return self.temp_end
        return self.get_start_pos()

    def update_path(self):
        """
        Calcula y actualiza la geometría del cable:
        - Si tiene waypoints manuales: traza ortogonalmente a través de cada vértice.
        - Si no tiene waypoints: realiza ruteo ortogonal Z con soporte para ajuste de desplazamiento (mid_x).
        """
        start = self.get_start_pos()
        end = self.get_end_pos()

        path = QPainterPath(start)

        if self.waypoints:
            curr = start
            for wp in self.waypoints:
                # Si no están alineados ortogonalmente, crear codo ortogonal
                if abs(curr.x() - wp.x()) > 0.5 and abs(curr.y() - wp.y()) > 0.5:
                    path.lineTo(wp.x(), curr.y())
                path.lineTo(wp)
                curr = wp

            # Conectar desde el último waypoint hasta el extremo final
            if abs(curr.x() - end.x()) > 0.5 and abs(curr.y() - end.y()) > 0.5:
                path.lineTo(end.x(), curr.y())
            path.lineTo(end)
        else:
            # Ruteo ortogonal clásico (inicio -> mid_x -> end)
            if self.route_offset_x is not None:
                mid_x = self.route_offset_x
            else:
                mid_x = (start.x() + end.x()) / 2.0

            path.lineTo(mid_x, start.y())
            path.lineTo(mid_x, end.y())
            path.lineTo(end)

        self.setPath(path)

        if self.isSelected():
            self.refresh_handles()

    def set_temp_end(self, pos: QPointF):
        self.temp_end = pos
        self.update_path()

    def update_positions(self):
        """Actualizar geometría cuando los componentes conectados se mueven."""
        self.update_path()

    # ── MANEJADORES INTERACTIVOS DE CABLES ENRUTADOS ──────────────────────────

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value:
                self.show_handles()
            else:
                self.hide_handles()
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if not self.scene():
                self.hide_handles()
        return super().itemChange(change, value)

    def show_handles(self):
        """Muestra manejadores interactivos en los vértices y segmentos del cable."""
        if not self.scene():
            return
        self.hide_handles()

        start = self.get_start_pos()
        end = self.get_end_pos()

        if self.waypoints:
            # Un handle en cada waypoint intermedio
            for i, wp in enumerate(self.waypoints):
                h = WireHandleItem(self, handle_type='waypoint', index=i)
                h.setPos(wp)
                self.scene().addItem(h)
                self.handles.append(h)
        else:
            # Un handle en el segmento intermedio para moverlo paralelamente
            if self.route_offset_x is not None:
                mid_x = self.route_offset_x
            else:
                mid_x = (start.x() + end.x()) / 2.0
            mid_y = (start.y() + end.y()) / 2.0

            h = WireHandleItem(self, handle_type='mid_x', index=0)
            h.setPos(mid_x, mid_y)
            self.scene().addItem(h)
            self.handles.append(h)

    def hide_handles(self):
        """Oculta y retira los manejadores de la escena."""
        for h in self.handles:
            if h.scene():
                h.scene().removeItem(h)
        self.handles.clear()

    def refresh_handles(self):
        """Actualiza la posición visual de los manejadores ya existentes."""
        start = self.get_start_pos()
        end = self.get_end_pos()

        if self.waypoints and len(self.handles) == len(self.waypoints):
            for i, wp in enumerate(self.waypoints):
                self.handles[i].setPos(wp)
        elif not self.waypoints and len(self.handles) == 1:
            mid_x = self.route_offset_x if self.route_offset_x is not None else (start.x() + end.x()) / 2.0
            mid_y = (start.y() + end.y()) / 2.0
            self.handles[0].setPos(mid_x, mid_y)
        else:
            self.show_handles()

    def on_handle_dragged(self, handle_type: str, index: int, new_pos: QPointF):
        """Responde al arrastre interactivo de un manejador de control."""
        if handle_type == 'mid_x':
            # Permite libertad total ortogonal 2D manteniendo anclajes de origen y destino
            self.waypoints = [new_pos]
            self.update_path()
            self.show_handles()
        elif handle_type == 'waypoint' and 0 <= index < len(self.waypoints):
            self.waypoints[index] = new_pos
            self.update_path()

    def insert_waypoint_at_pos(self, pt: QPointF):
        """Inserta un nuevo punto de quiebre/nodo en el segmento más cercano al punto."""
        points = [self.get_start_pos()] + list(self.waypoints) + [self.get_end_pos()]
        best_idx = 0
        min_dist = float('inf')

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            dist = self._dist_point_to_segment(pt, p1, p2)
            if dist < min_dist:
                min_dist = dist
                best_idx = i

        self.waypoints.insert(best_idx, QPointF(pt.x(), pt.y()))
        self.update_path()
        self.show_handles()

    def remove_waypoint_at_index(self, index: int):
        """Elimina el waypoint en el índice especificado."""
        if 0 <= index < len(self.waypoints):
            self.waypoints.pop(index)
            self.update_path()
            self.show_handles()

    @staticmethod
    def _dist_point_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
        px, py = p.x(), p.y()
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return ((px - ax)**2 + (py - ay)**2) ** 0.5
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        proj_x = ax + t * dx
        proj_y = ay + t * dy
        return ((px - proj_x)**2 + (py - proj_y)**2) ** 0.5

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSelected(True)
            self._is_dragging_wire = True
            self._drag_start_pos = event.scenePos()
            if not self.handles:
                self.show_handles()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging_wire', False):
            pos = event.scenePos()
            GRID = 20.0
            snap_x = round(pos.x() / GRID) * GRID
            snap_y = round(pos.y() / GRID) * GRID
            snap_pos = QPointF(snap_x, snap_y)

            if not self.waypoints:
                self.waypoints = [snap_pos]
                self.update_path()
                self.show_handles()
            else:
                closest_idx = 0
                min_d = float('inf')
                for i, wp in enumerate(self.waypoints):
                    d = (wp.x() - snap_pos.x())**2 + (wp.y() - snap_pos.y())**2
                    if d < min_d:
                        min_d = d
                        closest_idx = i
                self.waypoints[closest_idx] = snap_pos
                self.update_path()
                self.refresh_handles()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging_wire = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.scenePos()
            GRID = 20.0
            snap_x = round(pos.x() / GRID) * GRID
            snap_y = round(pos.y() / GRID) * GRID
            self.insert_waypoint_at_pos(QPointF(snap_x, snap_y))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ── RENDERIZADO VISUAL Y BIFURCACIONES ─────────────────────────────────────

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Indicador visual de selección: halo azul claro detrás del cable
        if self.isSelected():
            halo_pen = QPen(QColor(56, 189, 248, 180), self.wire_width + 4.0, Qt.SolidLine)
            halo_pen.setCapStyle(Qt.RoundCap)
            halo_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(halo_pen)
            painter.drawPath(self.path())

        # 2. Dibujar el cable con su pluma y color real configurado
        painter.setPen(self.pen())
        painter.drawPath(self.path())

        # 3. Puntos de bifurcación (nodo/empalme en T estilo CADe SIMU 4018)
        if self.has_start_junction:
            self._draw_junction_dot(painter, self.get_start_pos())
        if self.has_end_junction:
            self._draw_junction_dot(painter, self.get_end_pos())

        # 4. Si es cable trifásico (Manguera III), dibujar marcas de 3 conductores
        if self.wire_type == 4019 and not self.is_simulating:
            self._draw_three_phase_ticks(painter)

    def _draw_junction_dot(self, painter: QPainter, pos: QPointF):
        """Dibuja el punto de conexión (empalme normalizado) en la bifurcación."""
        painter.setBrush(QBrush(self.wire_color))
        painter.setPen(QPen(QColor("#0f172a"), 1))
        painter.drawEllipse(pos, 3.5, 3.5)

    def _draw_three_phase_ticks(self, painter: QPainter):
        """Dibuja marcas oblicuas que identifican manguera trifásica."""
        start = self.get_start_pos()
        end = self.get_end_pos()
        center_x = (start.x() + end.x()) / 2.0
        center_y = (start.y() + end.y()) / 2.0

        p = QPen(self.wire_color.darker(120), 1.5)
        painter.setPen(p)
        for offset in (-6, 0, 6):
            painter.drawLine(
                QPointF(center_x + offset - 4, center_y + 4),
                QPointF(center_x + offset + 4, center_y - 4)
            )

    def update_simulation_state(self, circuit_graph):
        """Actualizar visualización del cable según potenciales eléctricos en simulación."""
        if not self.edge_id or not circuit_graph:
            self.is_simulating = False
            self.sim_pen = None
            self.apply_pen()
            return

        edge = circuit_graph.edges.get(self.edge_id)
        if not edge:
            self.is_simulating = False
            self.sim_pen = None
            self.apply_pen()
            return

        n1 = circuit_graph.nodes.get(edge.node1_id)
        n2 = circuit_graph.nodes.get(edge.node2_id)

        is_live = (n1 and n1.is_energized()) or (n2 and n2.is_energized())
        is_neutral = False
        if not is_live:
            if (n1 and n1.potential_known and abs(n1.potential) < 1.0) or \
               (n2 and n2.potential_known and abs(n2.potential) < 1.0):
                is_neutral = True

        if is_live:
            # Energizado: Rojo brillante estilo CADe SIMU
            self.is_simulating = True
            pen = QPen(QColor(230, 20, 20), max(3.0, self.wire_width + 1.0))
            pen.setCapStyle(Qt.RoundCap)
            self.sim_pen = pen
            self.setPen(pen)
        elif is_neutral:
            # Neutro con tensión de retorno: Azul eléctrico
            self.is_simulating = True
            pen = QPen(QColor(30, 144, 255), max(2.5, self.wire_width + 0.5))
            pen.setCapStyle(Qt.RoundCap)
            self.sim_pen = pen
            self.setPen(pen)
        else:
            # Sin tensión / estado normal: Vuelve fielmente a su color y tipo configurado
            self.is_simulating = False
            self.sim_pen = None
            self.apply_pen()
