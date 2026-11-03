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
        scene = self.scene()
        if scene and getattr(scene, 'placement_mode', False):
            event.ignore()
            return
        if getattr(self.component, 'is_preview', False):
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            if scene:
                # Si ya estamos en modo cableado y hay un terminal inicial diferente, finalizar aquí
                if getattr(scene, 'wiring_mode', False) and scene.start_terminal and scene.start_terminal != self:
                    scene.finish_wire(self)
                elif hasattr(scene, 'start_wire'):
                    self._drag_start_pos = event.scenePos()
                    self._is_dragging_wire = True
                    scene.start_wire(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging_wire', False):
            scene = self.scene()
            if scene and getattr(scene, 'wiring_mode', False):
                scene.update_wire_routing(event.scenePos())
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_is_dragging_wire', False):
            self._is_dragging_wire = False
            scene = self.scene()
            if scene and getattr(scene, 'wiring_mode', False):
                pos = event.scenePos()
                drag_dist = (pos - getattr(self, '_drag_start_pos', pos)).manhattanLength()
                if drag_dist > 10.0:
                    items = scene.items(pos)
                    # 1. ¿Soltó sobre otro terminal válido?
                    for item in items:
                        if isinstance(item, TerminalItem) and item != self:
                            scene.finish_wire(item)
                            event.accept()
                            return
                    # 2. ¿Soltó sobre el puntito de empalme activo?
                    if getattr(scene, '_hovered_join_info', None):
                        target_wire, j_pt = scene._hovered_join_info
                        scene.finish_wire_to_wire(target_wire, j_pt)
                        event.accept()
                        return
                event.accept()
                return
        super().mouseReleaseEvent(event)
        
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
