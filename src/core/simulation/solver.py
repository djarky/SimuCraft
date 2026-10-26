"""
Solver para resolver estados eléctricos del circuito
"""
from typing import List
from ..graph import CircuitGraph


class CircuitSolver:
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        
    def solve(self, max_iterations: int = 100):
        """
        Resolver potenciales en el grafo.
        Usa conectividad lógica, NO coordenadas.
        """
        self.graph.clear_all_potentials()
        
        # Propagar desde fuentes
        sources = self.graph.get_source_nodes()
        for source in sources:
            from ..graph.node import NodeType
            if source.node_type == NodeType.POWER_RAIL:
                source.set_potential(source.potential if source.potential != 0 else 230.0, True)
            elif source.node_type == NodeType.NEUTRAL:
                source.set_potential(0.0, True)
        
        # Propagación iterativa
        changed = True
        iterations = 0
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for edge in self.graph.edges.values():
                node1 = self.graph.nodes.get(edge.node1_id)
                node2 = self.graph.nodes.get(edge.node2_id)
                if not node1 or not node2:
                    continue
                
                # Verificar si puede conducir
                if not self._can_conduct(edge):
                    continue
                
                # Propagar potencial
                if node1.potential_known and not node2.potential_known:
                    node2.set_potential(node1.potential, True)
                    changed = True
                elif node2.potential_known and not node1.potential_known:
                    node1.set_potential(node2.potential, True)
                    changed = True
        
        return iterations
    
    def _can_conduct(self, edge) -> bool:
        """Verificar si la arista permite conducción"""
        if not edge.component_id:
            # Cable directo
            return True
        
        component = self.graph.components.get(edge.component_id)
        if not component:
            return True
        
        # Delegar al componente
        if hasattr(component, 'is_conducting'):
            return component.is_conducting(edge.terminal1_id, edge.terminal2_id)
        
        return True
