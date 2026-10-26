"""
Item gráfico para cables dinámicos en el circuito
Se actualiza automáticamente al mover componentes y refleja estados eléctricos durante la simulación
"""
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QPainterPath, QColor


class WireItem(QGraphicsPathItem):
    def __init__(self, terminal1=None, terminal2=None, pt1: QPointF = None, pt2: QPointF = None, parent=None):
        super().__init__(parent)
        self.terminal1 = terminal1
        self.terminal2 = terminal2
        self.pt1 = pt1
        self.pt2 = pt2
        self.edge_id = None  # ID de arista en CircuitGraph
        self.temp_end = None
        
        self.setPen(QPen(Qt.black, 2))
        self.setZValue(5)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        if terminal1 and not terminal2 and not pt2:
            self.temp_end = terminal1.get_scene_pos()
        elif pt1 and not pt2:
            self.temp_end = pt1
            
        self.update_path()
        
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
        start = self.get_start_pos()
        end = self.get_end_pos()
            
        path = QPainterPath(start)
        # Ruteo ortogonal estilo CAD eléctrico
        mid_x = (start.x() + end.x()) / 2.0
        path.lineTo(mid_x, start.y())
        path.lineTo(mid_x, end.y())
        path.lineTo(end)
        self.setPath(path)
        
    def set_temp_end(self, pos: QPointF):
        self.temp_end = pos
        self.update_path()
        
    def update_positions(self):
        """Actualizar geometría cuando los componentes se mueven"""
        self.update_path()
        
    def update_simulation_state(self, circuit_graph):
        """Actualizar color del cable según potenciales eléctricos"""
        if not self.edge_id or not circuit_graph:
            self.setPen(QPen(Qt.black, 2))
            return
            
        edge = circuit_graph.edges.get(self.edge_id)
        if not edge:
            self.setPen(QPen(Qt.black, 2))
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
            self.setPen(QPen(QColor(230, 20, 20), 3))
        elif is_neutral:
            # Neutro: Azul eléctrico
            self.setPen(QPen(QColor(30, 144, 255), 2))
        else:
            # Sin tensión: Negro
            self.setPen(QPen(Qt.black, 2))
