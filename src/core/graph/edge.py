"""
Arista (cable) entre nodos del grafo relacional
"""
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Edge:
    """
    Cable que conecta dos nodos lógicamente.
    Si el componente se mueve, solo cambia la ruta visual, no la lógica.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node1_id: str = ""
    node2_id: str = ""
    component_id: Optional[str] = None  # Componente que puede controlar la conducción
    terminal1_id: Optional[str] = None
    terminal2_id: Optional[str] = None
    wire_type: str = "solid"  # solid, dashed
    visible: bool = True
    
    def connects(self, node_id: str) -> bool:
        return self.node1_id == node_id or self.node2_id == node_id
    
    def other_node(self, node_id: str) -> Optional[str]:
        if self.node1_id == node_id:
            return self.node2_id
        elif self.node2_id == node_id:
            return self.node1_id
        return None
