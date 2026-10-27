"""
Item gráfico para cables dinámicos en el circuito eléctrico.
Se actualiza automáticamente al mover componentes, soporta tipos y colores normalizados
de conductores (Fase, Neutro, Tierra, Positivo, Negativo, etc.) y refleja estados eléctricos durante la simulación.
"""
from typing import Optional, Any
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem, QStyleOptionGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QPainterPath, QColor, QPainter

from ..components.wire_types import get_wire_info, WIRE_CATALOG


class WireItem(QGraphicsPathItem):
    """
    Representa un conductor eléctrico en el esquema con propiedades físicas y normativas:
    tipo de cable (Fase, Neutro, Tierra...), color configurado, calibre y comportamiento ortogonal.
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

        if terminal1 and not terminal2 and not pt2:
            self.temp_end = terminal1.get_scene_pos()
        elif pt1 and not pt2:
            self.temp_end = pt1

        self.update_path()

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
        """Ruteo ortogonal estilo CAD eléctrico."""
        start = self.get_start_pos()
        end = self.get_end_pos()

        path = QPainterPath(start)
        mid_x = (start.x() + end.x()) / 2.0
        path.lineTo(mid_x, start.y())
        path.lineTo(mid_x, end.y())
        path.lineTo(end)
        self.setPath(path)

    def set_temp_end(self, pos: QPointF):
        self.temp_end = pos
        self.update_path()

    def update_positions(self):
        """Actualizar geometría cuando los componentes conectados se mueven."""
        self.update_path()

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

        # 3. Si es cable trifásico (Manguera III), dibujar marcas de 3 conductores
        if self.wire_type == 4019 and not self.is_simulating:
            self._draw_three_phase_ticks(painter)

    def _draw_three_phase_ticks(self, painter: QPainter):
        """Dibuja marcas oblicuas que identifican manguera trifásica."""
        path = self.path()
        if path.elementCount() < 2:
            return
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
