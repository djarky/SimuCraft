"""
Grafo relacional completo del circuito
"""
from typing import Dict, List, Optional, Set
from .node import Node, NodeType
from .edge import Edge


class CircuitGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.components: Dict[str, 'Component'] = {}
        
    def add_node(self, node: Node) -> str:
        self.nodes[node.id] = node
        return node.id
    
    def add_edge(self, edge: Edge) -> str:
        self.edges[edge.id] = edge
        # Actualizar nodos conectados
        if edge.node1_id in self.nodes:
            self.nodes[edge.node1_id].connected_edges.append(edge.id)
        if edge.node2_id in self.nodes:
            self.nodes[edge.node2_id].connected_edges.append(edge.id)
        return edge.id
    
    def remove_edge(self, edge_id: str):
        edge = self.edges.pop(edge_id, None)
        if edge:
            if edge.node1_id in self.nodes and edge_id in self.nodes[edge.node1_id].connected_edges:
                self.nodes[edge.node1_id].connected_edges.remove(edge_id)
            if edge.node2_id in self.nodes and edge_id in self.nodes[edge.node2_id].connected_edges:
                self.nodes[edge.node2_id].connected_edges.remove(edge_id)

    def remove_node(self, node_id: str):
        node = self.nodes.pop(node_id, None)
        if node:
            for edge_id in list(node.connected_edges):
                self.remove_edge(edge_id)

    def add_component(self, component: 'Component'):
        self.components[component.id] = component
        component.graph = self
        
    def remove_component(self, component_id: str):
        if component_id in self.components:
            del self.components[component_id]
        # Eliminar también las aristas internas asociadas a este componente
        internal_edges = [eid for eid, edge in self.edges.items() if edge.component_id == component_id]
        for eid in internal_edges:
            self.remove_edge(eid)
    
    def get_source_nodes(self) -> List[Node]:
        """Nodos fuente de alimentación y neutro"""
        sources = []
        for node in self.nodes.values():
            if node.node_type in [NodeType.POWER_RAIL, NodeType.NEUTRAL]:
                sources.append(node)
        return sources
    
    def find_connected_nodes(self, start_node_id: str) -> Set[str]:
        """Encontrar todos los nodos conectados por aristas (conectividad lógica)"""
        visited = set()
        stack = [start_node_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes.get(current)
            if not node:
                continue
            for edge_id in node.connected_edges:
                edge = self.edges.get(edge_id)
                if edge:
                    other = edge.other_node(current)
                    if other and other not in visited:
                        stack.append(other)
        return visited
    
    def get_node_edges(self, node_id: str) -> List[Edge]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.edges[eid] for eid in node.connected_edges if eid in self.edges]
    
    def clear_all_potentials(self):
        for node in self.nodes.values():
            if node.node_type not in [NodeType.POWER_RAIL, NodeType.NEUTRAL]:
                node.clear_potential()
    
    def to_dict(self) -> dict:
        return {
            'nodes': {k: {
                'id': v.id,
                'node_type': v.node_type.value,
                'potential': v.potential,
                'potential_known': v.potential_known,
                'name': v.name
            } for k, v in self.nodes.items()},
            'edges': {k: {
                'id': v.id,
                'node1_id': v.node1_id,
                'node2_id': v.node2_id,
                'component_id': v.component_id
            } for k, v in self.edges.items()},
            'component_ids': list(self.components.keys())
        }
