"""
Fuente de alimentación
"""
from .base import BaseComponentLogic


class PowerRail(BaseComponentLogic):
    def __init__(self, component_item=None, voltage=230.0):
        super().__init__(component_item)
        self.voltage = voltage
        self.phases = 1
        
    def update(self, delta_time: float):
        if not self.component_item:
            return
        scene = self.component_item.scene()
        if not scene or not hasattr(scene, 'circuit_graph'):
            return
        tag = (self.tag or "").upper()
        # Neutro / Tierra = 0V, Línea/Fase = self.voltage
        v = 0.0 if ('N' in tag or 'PE' in tag or 'GND' in tag) else self.voltage
        for term in getattr(self.component_item, 'terminals', []):
            if term.graph_node_id and term.graph_node_id in scene.circuit_graph.nodes:
                node = scene.circuit_graph.nodes[term.graph_node_id]
                node.potential = v
                node.potential_known = True
        
    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        return True
