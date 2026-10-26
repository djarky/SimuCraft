"""
Contactor con bobina y contactos auxiliares
"""
from .base import BaseComponentLogic
import time


class Contactor(BaseComponentLogic):
    def __init__(self, component_item=None):
        super().__init__(component_item)
        self.energized = False
        self.coil_voltage = 0.0
        self.pickup_voltage = 0.7  # 70% del nominal
        self.pickup_time_ms = 50
        self.dropout_time_ms = 30
        
        self._state = "OFF"
        self._timer = 0.0
        self._target_state = False
        
    def update(self, delta_time: float):
        # Verificar tensión de bobina
        coil_energized = self._check_coil()
        self._target_state = coil_energized
        
        if self._target_state != self.energized:
            if self._target_state:
                # Energizar con retardo
                self._timer += delta_time * 1000
                if self._timer >= self.pickup_time_ms:
                    self.energized = True
                    self._state = "ON"
                    self._timer = 0.0
            else:
                # Desenergizar con retardo
                self._timer += delta_time * 1000
                if self._timer >= self.dropout_time_ms:
                    self.energized = False
                    self._state = "OFF"
                    self._timer = 0.0
        else:
            self._timer = 0.0
            
    def _check_coil(self) -> bool:
        """Verificar si la bobina está energizada en el grafo relacional"""
        if not self.component_item or not hasattr(self.component_item, 'scene'):
            return self.coil_voltage > 20.0
        scene = self.component_item.scene()
        if not scene:
            return self.coil_voltage > 20.0
        t1 = self.component_item.get_terminal_by_id("A1")
        t2 = self.component_item.get_terminal_by_id("A2")
        if not t1 or not t2:
            return self.coil_voltage > 20.0
        graph = scene.circuit_graph
        n1 = graph.nodes.get(t1.graph_node_id)
        n2 = graph.nodes.get(t2.graph_node_id)
        if n1 and n2 and n1.potential_known and n2.potential_known:
            diff = abs(n1.potential - n2.potential)
            return diff > 50.0
        return False
        
    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        """Los contactos conducen si está energizado; la bobina A1-A2 es una carga (aislada)"""
        t1 = str(terminal1_id).upper()
        t2 = str(terminal2_id).upper()
        if (t1 in ('A1', 'A2')) and (t2 in ('A1', 'A2')):
            # La bobina es una carga, no un puente conductor
            return False
        return self.energized
        
    def get_auxiliary_contacts(self):
        """Obtener contactos auxiliares asociados que comparten el mismo tag"""
        if not self.component_item:
            return []
        scene = self.component_item.scene()
        if not scene or not hasattr(scene, 'circuit_graph'):
            return []
        my_tag = (self.tag or "").strip()
        if not my_tag:
            return []
        matching = []
        for comp in scene.circuit_graph.components.values():
            if comp is self.component_item:
                continue
            if (getattr(comp, 'tag', '') or '').strip() == my_tag:
                matching.append(comp)
        return matching
