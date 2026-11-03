"""
Solver para resolver estados eléctricos del circuito y detección de cortocircuitos.
"""
from typing import List, Dict, Set, Optional, Any
from ..graph import CircuitGraph
from ..graph.node import Node, NodeType
from ..graph.edge import Edge


class CircuitSolver:
    def __init__(self, graph: CircuitGraph):
        self.graph = graph
        self.short_circuits: List[Dict[str, Any]] = []
        self.tripped_devices: List[str] = []

    def solve(self, max_iterations: int = 100) -> int:
        """
        Resolver potenciales en el grafo relacional y detectar cortocircuitos.
        Usa conectividad lógica de nodos y aristas conductoras.
        """
        self.short_circuits.clear()
        self.tripped_devices.clear()
        self.graph.clear_all_potentials()

        # 1. Identificar y energizar nodos fuente (Fase, Neutro, Tierra, DC)
        sources = self.graph.get_source_nodes()
        for source in sources:
            if source.node_type == NodeType.POWER_RAIL:
                v = source.potential if source.potential != 0 else 230.0
                source.set_potential(v, True)
                source.source_phase = self._determine_source_phase(source)
                source.source_id = source.id
            elif source.node_type == NodeType.NEUTRAL:
                source.set_potential(0.0, True)
                source.source_phase = "N"
                source.source_id = source.id

        # 2. Propagación iterativa con detección de colisiones de potencial
        changed = True
        iterations = 0
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for edge in list(self.graph.edges.values()):
                node1 = self.graph.nodes.get(edge.node1_id)
                node2 = self.graph.nodes.get(edge.node2_id)
                if not node1 or not node2:
                    continue

                # Verificar si la arista puede conducir (cables, contactos cerrados, disyuntores armados)
                if not self._can_conduct(edge):
                    continue

                # Propagación directa de potencial
                if node1.potential_known and not node2.potential_known:
                    node2.set_potential(node1.potential, True)
                    node2.source_phase = node1.source_phase
                    node2.source_id = node1.source_id
                    changed = True
                elif node2.potential_known and not node1.potential_known:
                    node1.set_potential(node2.potential, True)
                    node1.source_phase = node2.source_phase
                    node1.source_id = node2.source_id
                    changed = True
                elif node1.potential_known and node2.potential_known:
                    # Ambos nodos con potencial conocido conectados por una vía conductora sin carga:
                    # Verificar si existe incompatibilidad de fases o diferencia de tensión (CORTOCIRCUITO)
                    if self._is_short_circuit_collision(node1, node2):
                        sc_info = self._record_short_circuit(edge, node1, node2)
                        # Si hay un disyuntor en la ruta, dispararlo para proteger la instalación
                        if self._trip_protection_devices(sc_info):
                            # Al abrirse el disyuntor, forzar re-evaluación del circuito
                            changed = True

        return iterations

    def _determine_source_phase(self, node: Node) -> str:
        """Determina la fase o tipo de riel de alimentación a partir de su nombre o tag."""
        name = (node.name or "").upper()
        if "PE" in name or "GND" in name or "TIERRA" in name:
            return "PE"
        if "L1" in name:
            return "L1"
        if "L2" in name:
            return "L2"
        if "L3" in name:
            return "L3"
        if "+" in name or "POS" in name:
            return "+"
        if "-" in name or "NEG" in name:
            return "-"
        if "N" in name:
            return "N"
        if "L" in name:
            return "L"
        return f"SRC_{node.id[:6]}"

    def _is_short_circuit_collision(self, node1: Node, node2: Node) -> bool:
        """
        Determina si dos nodos conductores en contacto directo presentan
        un cortocircuito por incompatibilidad de potencial o fases.
        """
        if not node1.potential_known or not node2.potential_known:
            return False

        # Si provienen exactamente de la misma fuente raíz con idéntico potencial: es un bucle normal
        if node1.source_id == node2.source_id and abs(node1.potential - node2.potential) < 1.0:
            return False

        p1 = (node1.source_phase or "").upper()
        p2 = (node2.source_phase or "").upper()
        v_diff = abs(node1.potential - node2.potential)

        phases = {"L", "L1", "L2", "L3"}
        neutrals = {"N", "PE", "GND", "TIERRA"}

        # 1. Fase con Neutro o Tierra
        if (p1 in phases and p2 in neutrals) or (p2 in phases and p1 in neutrals):
            return True

        # 2. Fase con Fase distinta (ej: L1 con L2, L2 con L3)
        if p1 in ("L1", "L2", "L3") and p2 in ("L1", "L2", "L3") and p1 != p2:
            return True

        # 3. DC: Positivo (+) con Negativo (-)
        if (p1 == "+" and p2 == "-") or (p1 == "-" and p2 == "+"):
            return True

        # 4. Diferencia de tensión significativa entre fuentes distintas
        if v_diff >= 1.0 and node1.source_id != node2.source_id:
            return True

        return False

    def _find_conducting_path(self, start_node_id: str, end_node_id: str) -> List[Edge]:
        """Encuentra la cadena de aristas conductoras entre dos nodos mediante BFS."""
        if start_node_id == end_node_id:
            return []
        visited = {start_node_id}
        queue = [(start_node_id, [])]
        while queue:
            curr_node_id, path_edges = queue.pop(0)
            node = self.graph.nodes.get(curr_node_id)
            if not node:
                continue
            for edge_id in node.connected_edges:
                edge = self.graph.edges.get(edge_id)
                if not edge or not self._can_conduct(edge):
                    continue
                other_id = edge.other_node(curr_node_id)
                if other_id == end_node_id:
                    return path_edges + [edge]
                if other_id and other_id not in visited:
                    visited.add(other_id)
                    queue.append((other_id, path_edges + [edge]))
        return []

    def _record_short_circuit(self, edge: Edge, node1: Node, node2: Node) -> Dict[str, Any]:
        """Registra los detalles técnicos de un cortocircuito detectado."""
        p1 = (node1.source_phase or "L").upper()
        p2 = (node2.source_phase or "N").upper()
        phases = {"L", "L1", "L2", "L3"}
        neutrals = {"N", "PE", "GND", "TIERRA"}

        if (p1 in phases and p2 in neutrals) or (p2 in phases and p1 in neutrals):
            sc_type = "Fase - Neutro" if "N" in (p1, p2) else "Fase - Tierra (Falla a Tierra)"
        elif p1 in ("L1", "L2", "L3") and p2 in ("L1", "L2", "L3") and p1 != p2:
            sc_type = "Fase - Fase"
        elif (p1 == "+" and p2 == "-") or (p1 == "-" and p2 == "+"):
            sc_type = "Positivo - Negativo (DC)"
        else:
            sc_type = "Cortocircuito Directo"

        v_diff = abs(node1.potential - node2.potential)
        if sc_type == "Fase - Fase" and v_diff < 1.0:
            v_diff = max(node1.potential, node2.potential) * 1.732  # Tensión de línea trifásica

        # Trazar la cadena completa de conductores en corto
        path1 = self._find_conducting_path(node1.source_id, node1.id) if node1.source_id else []
        path2 = self._find_conducting_path(node2.id, node2.source_id) if node2.source_id else []
        all_edges = path1 + [edge] + path2
        involved_edge_ids = list(dict.fromkeys([e.id for e in all_edges]))
        involved_node_ids = list(dict.fromkeys(
            [e.node1_id for e in all_edges] + [e.node2_id for e in all_edges]
        ))

        comp = self.graph.components.get(edge.component_id) if edge.component_id else None
        loc_str = f" en '{comp.tag or comp.name}'" if comp else ""

        src1_name = self.graph.nodes[node1.source_id].name if (node1.source_id and node1.source_id in self.graph.nodes) else p1
        src2_name = self.graph.nodes[node2.source_id].name if (node2.source_id and node2.source_id in self.graph.nodes) else p2

        sc_info = {
            "type": sc_type,
            "edge_id": edge.id,
            "component_id": edge.component_id,
            "component_name": comp.name if comp else None,
            "component_tag": getattr(comp, 'tag', '') if comp else None,
            "source1_name": src1_name,
            "source2_name": src2_name,
            "potential1": node1.potential,
            "potential2": node2.potential,
            "voltage_diff": v_diff,
            "description": f"Cortocircuito {sc_type} ({v_diff:.0f}V){loc_str} entre {src1_name} y {src2_name}",
            "involved_edge_ids": involved_edge_ids,
            "involved_node_ids": involved_node_ids,
            "tripped_breakers": []
        }

        # Evitar duplicar el mismo evento en la misma pasada
        for existing in self.short_circuits:
            if existing["edge_id"] == edge.id:
                return existing

        self.short_circuits.append(sc_info)
        return sc_info

    def _trip_protection_devices(self, sc_info: Dict[str, Any]) -> bool:
        """
        Dispara disyuntores magnetotérmicos o fusibles presentes en la ruta
        del cortocircuito para abrir el circuito y proteger la instalación.
        """
        any_tripped = False
        involved_edges = sc_info.get("involved_edge_ids", [])
        for eid in involved_edges:
            edge = self.graph.edges.get(eid)
            if not edge or not edge.component_id:
                continue
            comp = self.graph.components.get(edge.component_id)
            if not comp:
                continue

            logic = getattr(comp, 'logic_instance', None)
            if logic and hasattr(logic, 'trip') and hasattr(logic, 'tripped'):
                if not logic.tripped:
                    logic.trip()
                    any_tripped = True
                    tag = getattr(comp, 'tag', '') or getattr(comp, 'name', '') or comp.id
                    if tag not in self.tripped_devices:
                        self.tripped_devices.append(tag)
                    if tag not in sc_info["tripped_breakers"]:
                        sc_info["tripped_breakers"].append(tag)
                    if hasattr(comp, 'update_visual'):
                        comp.update_visual()

        return any_tripped

    def has_short_circuit(self) -> bool:
        """Indica si existe al menos un cortocircuito activo sin despejar."""
        return len(self.short_circuits) > 0

    def get_short_circuits(self) -> List[Dict[str, Any]]:
        return self.short_circuits

    def get_short_circuit_edges(self) -> Set[str]:
        """Devuelve el conjunto de IDs de todas las aristas involucradas en cortocircuitos."""
        edges = set()
        for sc in self.short_circuits:
            edges.update(sc.get("involved_edge_ids", []))
            if sc.get("edge_id"):
                edges.add(sc["edge_id"])
        return edges

    def _can_conduct(self, edge: Edge) -> bool:
        """Verificar si la arista permite conducción (cables, contactos cerrados, disyuntores armados)."""
        if not edge.component_id:
            # Cable directo sin componente
            return True

        component = self.graph.components.get(edge.component_id)
        if not component:
            return True

        # Delegar al componente (las bobinas, lámparas y motores devuelven False para sus bornes de carga)
        if hasattr(component, 'is_conducting'):
            return component.is_conducting(edge.terminal1_id, edge.terminal2_id)

        return True
