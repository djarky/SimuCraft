"""
Nodo eléctrico en el grafo relacional
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any
import uuid


class NodeType(Enum):
    POWER_RAIL = "power_rail"
    NEUTRAL = "neutral"
    JUNCTION = "junction"
    TERMINAL = "terminal"


@dataclass
class Node:
    """
    Nodo que representa un punto eléctrico en el circuito.
    La conexión es lógica, no por coordenadas pixel.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: NodeType = NodeType.JUNCTION
    potential: float = 0.0  # Voltaje
    potential_known: bool = False
    connected_edges: List[str] = field(default_factory=list)
    component_terminals: List[tuple] = field(default_factory=list)  # (component_id, terminal_id)
    name: str = ""
    
    def set_potential(self, voltage: float, known: bool = True):
        self.potential = voltage
        self.potential_known = known
    
    def clear_potential(self):
        self.potential_known = False
        self.potential = 0.0
    
    def is_energized(self, threshold: float = 0.1) -> bool:
        return self.potential_known and abs(self.potential) > threshold
