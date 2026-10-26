"""
Motor de simulación en tiempo real
"""
from PySide6.QtCore import QObject, QTimer, Signal
from .solver import CircuitSolver
from ..graph import CircuitGraph
try:
    from shiboken6 import isValid as _shiboken_isValid
except ImportError:
    try:
        from shiboken2 import isValid as _shiboken_isValid
    except ImportError:
        def _shiboken_isValid(obj):
            """Fallback: assume valid unless we can prove otherwise"""
            return True


class Simulator(QObject):
    simulation_step = Signal()
    state_changed = Signal()
    
    def __init__(self, graph: CircuitGraph, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.solver = CircuitSolver(graph)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)
        
        self.timestep_ms = 10  # 100Hz
        self.running = False
        self.delta_time = self.timestep_ms / 1000.0
        
    def set_graph(self, graph: CircuitGraph):
        self.graph = graph
        self.solver = CircuitSolver(graph)
        
    def start(self):
        if not self.running:
            self.running = True
            self.timer.start(self.timestep_ms)
    
    def stop(self):
        if self.running:
            self.running = False
            self.timer.stop()
    
    def step(self):
        """Un paso de simulación con relajación iterativa para resolver dependencias y enclavamientos"""
        if not self.running:
            return

        # Detectar componentes cuyo objeto C++ Qt ya fue eliminado por la escena
        stale_keys = [
            k for k, c in self.graph.components.items()
            if not _shiboken_isValid(c)
        ]
        for k in stale_keys:
            del self.graph.components[k]

        # Relajación iterativa: resuelve grafo y actualiza componentes hasta estado estacionario
        for _ in range(3):
            self.solver.solve()
            changed = False
            for component in list(self.graph.components.values()):
                if not _shiboken_isValid(component):
                    continue  # objeto Qt ya eliminado, saltar
                if hasattr(component, 'update'):
                    prev_state = getattr(component.logic_instance, 'energized', None) if hasattr(component, 'logic_instance') and component.logic_instance else None
                    try:
                        component.update(self.delta_time)
                    except RuntimeError:
                        # C++ object deleted between the isValid check and the call
                        continue
                    new_state = getattr(component.logic_instance, 'energized', None) if hasattr(component, 'logic_instance') and component.logic_instance else None
                    if prev_state != new_state:
                        changed = True
            if not changed:
                break
        
        # Notificar cambio a la interfaz gráfica
        self.simulation_step.emit()
    
    def single_step(self):
        """Paso único para debug"""
        was_running = self.running
        if was_running:
            self.stop()
        self.step()
        if was_running:
            self.start()
    
    def set_timestep(self, ms: int):
        self.timestep_ms = ms
        self.delta_time = ms / 1000.0
        if self.running:
            self.timer.setInterval(ms)
