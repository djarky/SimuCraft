"""
Comandos concretos para el patrón Undo/Redo en SimuCraft.
Cubren las acciones principales del editor: añadir, mover y eliminar componentes y cables.
"""
from PySide6.QtCore import QPointF
from .base_command import BaseCommand


class AddComponentCommand(BaseCommand):
    """Añadir un componente a la escena — deshacer lo elimina."""

    def __init__(self, scene, component_item, text: str = "Añadir componente"):
        super().__init__(text)
        self.scene = scene
        self.component_item = component_item

    def execute(self):
        self.scene.add_component(self.component_item)

    def _redo(self):
        self.scene.add_component(self.component_item)

    def _undo(self):
        self.scene.removeItem(self.component_item)
        self.scene.circuit_graph.remove_component(self.component_item.id)


class RemoveComponentCommand(BaseCommand):
    """Eliminar un componente de la escena y sus cables — deshacer los restaura."""

    def __init__(self, scene, component_item, text: str = "Eliminar componente"):
        super().__init__(text)
        self.scene = scene
        self.component_item = component_item
        self._pos = component_item.pos()
        # Recopilar cables conectados para restaurarlos en undo
        self._connected_wires = []
        for term in getattr(component_item, 'terminals', []):
            for w in list(getattr(term, 'connected_wires', [])):
                if w not in [item[0] for item in self._connected_wires]:
                    edge = self.scene.circuit_graph.edges.get(w.edge_id)
                    self._connected_wires.append((w, edge, w.terminal1, w.terminal2))

    def execute(self):
        # 1. Quitar cables conectados
        for w, edge, t1, t2 in self._connected_wires:
            if w in self.scene.wires:
                self.scene.wires.remove(w)
            if w.scene() == self.scene:
                self.scene.removeItem(w)
            if t1 and w in getattr(t1, 'connected_wires', []):
                t1.connected_wires.remove(w)
            if t2 and w in getattr(t2, 'connected_wires', []):
                t2.connected_wires.remove(w)
            if edge:
                self.scene.circuit_graph.remove_edge(edge.id)
        # 2. Quitar componente
        if self.component_item.scene() == self.scene:
            self.scene.removeItem(self.component_item)
        self.scene.circuit_graph.remove_component(self.component_item.id)

    def _redo(self):
        self.execute()

    def _undo(self):
        # 1. Restaurar componente
        self.component_item.setPos(self._pos)
        self.scene.add_component(self.component_item)
        # 2. Restaurar cables conectados
        for w, edge, t1, t2 in self._connected_wires:
            if edge:
                self.scene.circuit_graph.add_edge(edge)
            self.scene.addItem(w)
            if w not in self.scene.wires:
                self.scene.wires.append(w)
            if t1 and w not in getattr(t1, 'connected_wires', []):
                t1.connected_wires.append(w)
            if t2 and w not in getattr(t2, 'connected_wires', []):
                t2.connected_wires.append(w)
            if hasattr(w, 'update_path'):
                w.update_path()


class MoveComponentCommand(BaseCommand):
    """Mover un componente — deshacer restaura la posición anterior."""

    def __init__(self, component_item, old_pos: QPointF, new_pos: QPointF,
                 text: str = "Mover componente"):
        super().__init__(text)
        self.component_item = component_item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def execute(self):
        self.component_item.setPos(self.new_pos)

    def _redo(self):
        self.component_item.setPos(self.new_pos)
        scene = self.component_item.scene()
        if scene and hasattr(scene, 'update_connected_wires'):
            scene.update_connected_wires(self.component_item)

    def _undo(self):
        self.component_item.setPos(self.old_pos)
        scene = self.component_item.scene()
        if scene and hasattr(scene, 'update_connected_wires'):
            scene.update_connected_wires(self.component_item)

    COMMAND_ID = 1001

    def mergeWith(self, other) -> bool:
        """Fusionar movimientos consecutivos del mismo componente en un solo comando."""
        if isinstance(other, MoveComponentCommand) and \
                other.component_item is self.component_item:
            self.new_pos = other.new_pos
            return True
        return False

    def id(self) -> int:
        return self.COMMAND_ID


class AddWireCommand(BaseCommand):
    """Añadir un cable entre dos terminales — deshacer lo elimina."""

    def __init__(self, scene, wire_item, edge,
                 start_terminal, end_terminal, text: str = "Cablear terminales"):
        super().__init__(text)
        self.scene = scene
        self.wire_item = wire_item
        self.edge = edge
        self.start_terminal = start_terminal
        self.end_terminal = end_terminal

    def execute(self):
        pass  # El wire ya fue añadido interactivamente

    def _redo(self):
        if self.edge:
            self.scene.circuit_graph.add_edge(self.edge)
        self.scene.addItem(self.wire_item)
        if self.wire_item not in self.scene.wires:
            self.scene.wires.append(self.wire_item)
        if self.start_terminal and self.wire_item not in self.start_terminal.connected_wires:
            self.start_terminal.connected_wires.append(self.wire_item)
        if self.end_terminal and self.wire_item not in self.end_terminal.connected_wires:
            self.end_terminal.connected_wires.append(self.wire_item)
        if hasattr(self.wire_item, 'update_path'):
            self.wire_item.update_path()

    def _undo(self):
        self.scene.removeItem(self.wire_item)
        if self.wire_item in self.scene.wires:
            self.scene.wires.remove(self.wire_item)
        if self.start_terminal and self.wire_item in self.start_terminal.connected_wires:
            self.start_terminal.connected_wires.remove(self.wire_item)
        if self.end_terminal and self.wire_item in self.end_terminal.connected_wires:
            self.end_terminal.connected_wires.remove(self.wire_item)
        if self.edge:
            self.scene.circuit_graph.remove_edge(self.edge.id)


class RemoveWireCommand(BaseCommand):
    """Eliminar un cable — deshacer lo restaura."""

    def __init__(self, scene, wire_item, text: str = "Eliminar cable"):
        super().__init__(text)
        self.scene = scene
        self.wire_item = wire_item
        self.edge = self.scene.circuit_graph.edges.get(wire_item.edge_id)
        self.start_terminal = wire_item.terminal1
        self.end_terminal = wire_item.terminal2

    def execute(self):
        self.scene.removeItem(self.wire_item)
        if self.wire_item in self.scene.wires:
            self.scene.wires.remove(self.wire_item)
        if self.start_terminal and self.wire_item in getattr(self.start_terminal, 'connected_wires', []):
            self.start_terminal.connected_wires.remove(self.wire_item)
        if self.end_terminal and self.wire_item in getattr(self.end_terminal, 'connected_wires', []):
            self.end_terminal.connected_wires.remove(self.wire_item)
        if self.edge:
            self.scene.circuit_graph.remove_edge(self.edge.id)

    def _redo(self):
        self.execute()

    def _undo(self):
        if self.edge:
            self.scene.circuit_graph.add_edge(self.edge)
        self.scene.addItem(self.wire_item)
        if self.wire_item not in self.scene.wires:
            self.scene.wires.append(self.wire_item)
        if self.start_terminal and self.wire_item not in getattr(self.start_terminal, 'connected_wires', []):
            self.start_terminal.connected_wires.append(self.wire_item)
        if self.end_terminal and self.wire_item not in getattr(self.end_terminal, 'connected_wires', []):
            self.end_terminal.connected_wires.append(self.wire_item)
        if hasattr(self.wire_item, 'update_path'):
            self.wire_item.update_path()
