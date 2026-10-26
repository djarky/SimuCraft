"""
Componentes auxiliares: Contactos auxiliares, Lámparas piloto y Relés térmicos
"""
from .base import BaseComponentLogic


class AuxiliaryContact(BaseComponentLogic):
    """Contacto auxiliar (NA o NC) asociado a un contactor por Tag (ej: -KM1)"""
    def __init__(self, component_item=None, normally_open=True):
        super().__init__(component_item)
        self.normally_open = normally_open
        self.closed_by_contactor = False
        
    def update(self, delta_time: float):
        # Buscar el contactor asociado por tag en el grafo
        if not self.component_item or not hasattr(self.component_item, 'scene'):
            return
        scene = self.component_item.scene()
        if not scene:
            return
        tag = getattr(self.component_item, 'tag', '')
        if not tag:
            return
            
        clean_tag = tag.lstrip('-').upper()
        # Buscar bobina de contactor con el mismo tag
        for comp in scene.circuit_graph.components.values():
            comp_type = getattr(comp, 'component_type', '')
            comp_tag = getattr(comp, 'tag', '').lstrip('-').upper()
            if comp_type == 'contactor' and comp_tag == clean_tag:
                if comp.logic_instance and hasattr(comp.logic_instance, 'energized'):
                    self.closed_by_contactor = comp.logic_instance.energized
                    break

    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        if self.normally_open:
            return self.closed_by_contactor
        else:
            return not self.closed_by_contactor


class PilotLamp(BaseComponentLogic):
    """Lámpara de señalización / Piloto luminoso"""
    def __init__(self, component_item=None):
        super().__init__(component_item)
        self.lit = False
        self.voltage = 0.0

    def update(self, delta_time: float):
        if not self.component_item:
            return
        # Usar los terminales del componente dinámicamente (X1/X2 o lo que tenga)
        terminals = getattr(self.component_item, 'terminals', [])
        if len(terminals) < 2 or not self.component_item.scene():
            return
        t1 = terminals[0]
        t2 = terminals[1]
            
        graph = self.component_item.scene().circuit_graph
        n1 = graph.nodes.get(t1.graph_node_id)
        n2 = graph.nodes.get(t2.graph_node_id)
        
        if n1 and n2 and n1.potential_known and n2.potential_known:
            diff = abs(n1.potential - n2.potential)
            self.lit = (diff > 50.0)
        else:
            self.lit = False

    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        # Carga eléctrica: no es un cortocircuito
        return False


class Motor(BaseComponentLogic):
    """Motor eléctrico - carga trifásica o monofásica"""
    def __init__(self, component_item=None):
        super().__init__(component_item)
        self.running = False
        self.lit = False  # compatibilidad con PilotLamp API
        self.voltage = 0.0

    def update(self, delta_time: float):
        if not self.component_item or not self.component_item.scene():
            return
        terminals = getattr(self.component_item, 'terminals', [])
        if not terminals:
            return
        graph = self.component_item.scene().circuit_graph
        # El motor corre si cualquiera de sus terminales de entrada recibe tensión
        energized = False
        for t in terminals:
            n = graph.nodes.get(t.graph_node_id)
            if n and n.is_energized():
                energized = True
                break
        self.running = energized
        # Para compatibilidad con código que revisa 'lit'
        self.lit = energized

    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        # Motor es carga, no conduce entre sus terminales
        return False


class ThermalRelay(BaseComponentLogic):
    """Relé térmico (normalmente cerrado 95-96)"""
    def __init__(self, component_item=None):
        super().__init__(component_item)
        self.tripped = False

    def trip(self):
        self.tripped = True

    def update(self, delta_time: float):
        pass

    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        return not self.tripped

    def reset(self):
        self.tripped = False
        super().reset()
