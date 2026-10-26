"""
Item gráfico para bornes/terminales de componentes
Permite iniciar y finalizar cableado dinámico en el lienzo
"""
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QBrush, QPen, QColor


class TerminalItem(QGraphicsEllipseItem):
    def __init__(self, parent_component, terminal_def: dict):
        super().__init__(parent_component)
        self.component = parent_component
        self.terminal_def = terminal_def
        self.terminal_id = str(terminal_def.get('id', ''))
        self.terminal_name = str(terminal_def.get('name', self.terminal_id))
        self.terminal_type = terminal_def.get('type', 'Generic')
        self.orientation = terminal_def.get('orientation', 'unknown')
        
        # ID de nodo en el grafo relacional
        self.graph_node_id = None
        
        # Visual
        self.setRect(QRectF(-4, -4, 8, 8))
        self.setBrush(QBrush(QColor("#FFA500")))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(20)
        
        # Conexiones
        self.connected_wires = []
        self.highlighted = False
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#FF4500")))
        self.setRect(QRectF(-6, -6, 12, 12))
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        if not self.highlighted:
            color = QColor("#32CD32") if self.connected_wires else QColor("#FFA500")
            self.setBrush(QBrush(color))
            self.setRect(QRectF(-4, -4, 8, 8))
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene = self.scene()
            if scene:
                # Si ya estamos en modo cableado y hay un terminal inicial, finalizar aquí
                if getattr(scene, 'wiring_mode', False) and scene.start_terminal and scene.start_terminal != self:
                    scene.finish_wire(self)
                elif hasattr(scene, 'start_wire'):
                    scene.start_wire(self)
            event.accept()
        else:
            super().mousePressEvent(event)
        
    def highlight(self, on: bool = True):
        self.highlighted = on
        if on:
            self.setBrush(QBrush(QColor("#00FF00")))
            self.setRect(QRectF(-6, -6, 12, 12))
        else:
            color = QColor("#32CD32") if self.connected_wires else QColor("#FFA500")
            self.setBrush(QBrush(color))
            self.setRect(QRectF(-4, -4, 8, 8))
        
    def get_scene_pos(self) -> QPointF:
        """Devuelve la posición absoluta del centro del borne en la escena"""
        return self.mapToScene(QPointF(0, 0))
