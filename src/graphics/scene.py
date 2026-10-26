"""
Escena gráfica del circuito eléctrico
Gestiona la colocación de componentes, cableado interactivo y sincronización con el grafo relacional
"""
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor

from ..core.graph import CircuitGraph, Node, Edge, NodeType
from .wire_item import WireItem


class CircuitScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.circuit_graph = CircuitGraph()
        self.wiring_mode = False
        self.temp_wire = None
        self.start_terminal = None
        self.wires = []
        self.junction_nodes = {}
        
        # Tamaño amplio del lienzo con fondo tipo cuadrícula
        self.setSceneRect(0, 0, 3000, 2000)
        self.setBackgroundBrush(QColor("#FAFAFA"))
        
    def set_wiring_mode(self, enabled: bool):
        self.wiring_mode = enabled
        if not enabled:
            self.cancel_wire()
            
    def start_wire(self, terminal):
        self.wiring_mode = True
        self.start_terminal = terminal
        self.temp_wire = WireItem(terminal1=terminal)
        self.addItem(self.temp_wire)
        
    def mouseMoveEvent(self, event):
        if self.wiring_mode and self.temp_wire and self.start_terminal:
            self.temp_wire.set_temp_end(event.scenePos())
        super().mouseMoveEvent(event)
        
    def mousePressEvent(self, event):
        if self.wiring_mode and event.button() == Qt.LeftButton:
            items = self.items(event.scenePos())
            for item in items:
                from .terminal_item import TerminalItem
                if isinstance(item, TerminalItem) and item != self.start_terminal:
                    self.finish_wire(item)
                    return
            self.cancel_wire()
            return
        elif event.button() == Qt.RightButton:
            if self.wiring_mode:
                self.cancel_wire()
                return
        super().mousePressEvent(event)
        
    def finish_wire(self, end_terminal):
        """Finalizar cableado creando nodo y arista en el grafo relacional"""
        if not self.start_terminal or not end_terminal:
            self.cancel_wire()
            return
            
        # Asegurar nodos en el grafo
        if not self.start_terminal.graph_node_id:
            node = Node(node_type=NodeType.TERMINAL)
            self.circuit_graph.add_node(node)
            self.start_terminal.graph_node_id = node.id
            
        if not end_terminal.graph_node_id:
            node = Node(node_type=NodeType.TERMINAL)
            self.circuit_graph.add_node(node)
            end_terminal.graph_node_id = node.id
            
        # Crear arista conductora (cable exterior)
        edge = Edge(
            node1_id=self.start_terminal.graph_node_id,
            node2_id=end_terminal.graph_node_id,
            terminal1_id=self.start_terminal.terminal_id,
            terminal2_id=end_terminal.terminal_id,
            component_id=None  # Cable exterior directo
        )
        self.circuit_graph.add_edge(edge)
        
        # Crear wire visual
        wire = WireItem(terminal1=self.start_terminal, terminal2=end_terminal)
        wire.edge_id = edge.id
        
        if self.temp_wire and self.temp_wire.scene() == self:
            self.removeItem(self.temp_wire)
        self.temp_wire = None
        
        start_t = self.start_terminal
        self.start_terminal = None
        
        # Registrar en CommandManager si está disponible
        main_win = self.parent()
        if not main_win:
            views = self.views()
            if views:
                main_win = views[0].window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import AddWireCommand
            cmd = AddWireCommand(self, wire, edge, start_t, end_terminal)
            cmd.executed = True
            main_win.command_manager.push(cmd)
        return wire
        
    def create_wire_between_points(self, pt1: QPointF, pt2: QPointF, t1=None, t2=None) -> WireItem:
        """Crear cable entre dos puntos o bornes (usado por el cargador de CAD)"""
        k1 = (round(pt1.x(), 1), round(pt1.y(), 1))
        k2 = (round(pt2.x(), 1), round(pt2.y(), 1))
        
        # Obtener o crear nodo 1
        if t1 and t1.graph_node_id:
            n1_id = t1.graph_node_id
            self.junction_nodes[k1] = n1_id
        elif k1 in self.junction_nodes:
            n1_id = self.junction_nodes[k1]
            if t1:
                t1.graph_node_id = n1_id
        else:
            n1 = Node(node_type=NodeType.JUNCTION)
            n1_id = self.circuit_graph.add_node(n1)
            self.junction_nodes[k1] = n1_id
            if t1:
                t1.graph_node_id = n1_id
                
        # Obtener o crear nodo 2
        if t2 and t2.graph_node_id:
            n2_id = t2.graph_node_id
            self.junction_nodes[k2] = n2_id
        elif k2 in self.junction_nodes:
            n2_id = self.junction_nodes[k2]
            if t2:
                t2.graph_node_id = n2_id
        else:
            n2 = Node(node_type=NodeType.JUNCTION)
            n2_id = self.circuit_graph.add_node(n2)
            self.junction_nodes[k2] = n2_id
            if t2:
                t2.graph_node_id = n2_id
                
        edge = Edge(
            node1_id=n1_id,
            node2_id=n2_id,
            terminal1_id=t1.terminal_id if t1 else None,
            terminal2_id=t2.terminal_id if t2 else None,
            component_id=None
        )
        self.circuit_graph.add_edge(edge)
        
        wire = WireItem(terminal1=t1, terminal2=t2, pt1=pt1, pt2=pt2)
        wire.edge_id = edge.id
        self.addItem(wire)
        self.wires.append(wire)
        
        if t1:
            t1.connected_wires.append(wire)
        if t2:
            t2.connected_wires.append(wire)
            
        return wire

    def cancel_wire(self):
        if self.temp_wire and self.temp_wire.scene() == self:
            self.removeItem(self.temp_wire)
        self.temp_wire = None
        self.start_terminal = None
        self.wiring_mode = False

    def update_connected_wires(self, component):
        """Actualizar geometría de cables conectados al mover un componente"""
        for term in component.terminals:
            for wire in term.connected_wires:
                wire.update_positions()

    def add_component(self, component_item):
        """Añadir componente a la escena y configurar sus nodos/aristas en el grafo relacional"""
        self.addItem(component_item)
        self.circuit_graph.add_component(component_item)
        
        # 1. Crear nodos en el grafo para cada terminal
        is_power = (component_item.component_type == 'power')
        is_neutral = (component_item.component_type == 'neutral')
        
        for term in component_item.terminals:
            if is_power:
                node = Node(
                    node_type=NodeType.POWER_RAIL,
                    potential=230.0,
                    potential_known=True,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )
            elif is_neutral:
                node = Node(
                    node_type=NodeType.NEUTRAL,
                    potential=0.0,
                    potential_known=True,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )
            else:
                node = Node(
                    node_type=NodeType.TERMINAL,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )
                
            node_id = self.circuit_graph.add_node(node)
            term.graph_node_id = node_id
            
        # 2. Conectar internamente bornes con lógica de componente
        logic = component_item.component_def.get('logic', {})
        internal_conns = logic.get('internal_connections', [])
        
        # Por defecto si tiene 2 terminales y es interruptor/contacto/pulsador/bobina/lámpara
        if not internal_conns and len(component_item.terminals) == 2 and component_item.component_type != 'power':
            t1 = component_item.terminals[0].terminal_id
            t2 = component_item.terminals[1].terminal_id
            internal_conns = [(t1, t2)]
            
        for t1_id, t2_id in internal_conns:
            term1 = component_item.get_terminal_by_id(t1_id)
            term2 = component_item.get_terminal_by_id(t2_id)
            if term1 and term2 and term1.graph_node_id and term2.graph_node_id:
                edge = Edge(
                    node1_id=term1.graph_node_id,
                    node2_id=term2.graph_node_id,
                    terminal1_id=t1_id,
                    terminal2_id=t2_id,
                    component_id=component_item.id
                )
                self.circuit_graph.add_edge(edge)

    def update_simulation_visuals(self):
        """Actualizar el color de los cables y el estado de componentes durante la simulación"""
        for wire in self.wires:
            wire.update_simulation_state(self.circuit_graph)
        for comp in self.circuit_graph.components.values():
            if hasattr(comp, 'update_visual'):
                comp.update_visual()

    def clear_circuit(self):
        """Limpiar completamente la escena y el grafo"""
        self.cancel_wire()
        self.clear()
        self.wires.clear()
        self.junction_nodes.clear()
        self.circuit_graph = CircuitGraph()

    def show_component_properties(self, component):
        """Abrir el diálogo de edición de propiedades del componente"""
        from ..ui.component_properties_dialog import ComponentPropertiesDialog
        # Buscar ventana padre (MainWindow)
        parent = None
        views = self.views()
        if views:
            parent = views[0].window()
        dlg = ComponentPropertiesDialog(component, parent)
        dlg.exec()

    def connect_terminals(self, t1, t2) -> WireItem:
        """Conectar dos bornes directamente y crear su wire y arista"""
        self.start_terminal = t1
        return self.finish_wire(t2)

    def remove_component_with_undo(self, comp):
        """Eliminar un componente con registro en el CommandManager para Undo"""
        main_win = self.parent()
        if not main_win:
            views = self.views()
            if views:
                main_win = views[0].window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import RemoveComponentCommand
            cmd = RemoveComponentCommand(self, comp)
            main_win.command_manager.push(cmd)
        else:
            self.removeItem(comp)
            self.circuit_graph.remove_component(comp.id)

    def remove_wire_with_undo(self, wire):
        """Eliminar un cable con registro en el CommandManager para Undo"""
        main_win = self.parent()
        if not main_win:
            views = self.views()
            if views:
                main_win = views[0].window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import RemoveWireCommand
            cmd = RemoveWireCommand(self, wire)
            main_win.command_manager.push(cmd)
        else:
            self.removeItem(wire)
            if wire in self.wires:
                self.wires.remove(wire)
            if wire.edge_id:
                self.circuit_graph.remove_edge(wire.edge_id)

    def keyPressEvent(self, event):
        """Manejar teclas de eliminación (Supr/Backspace) en la escena"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected = list(self.selectedItems())
            from .component_item import ComponentItem
            from .wire_item import WireItem
            # Primero componentes, luego cables independientes
            for item in selected:
                if isinstance(item, ComponentItem):
                    self.remove_component_with_undo(item)
            for item in selected:
                if isinstance(item, WireItem):
                    self.remove_wire_with_undo(item)
            event.accept()
            return
        super().keyPressEvent(event)
