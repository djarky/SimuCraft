"""
Clase base para lógica de componentes
"""
from abc import ABC, abstractmethod


class BaseComponentLogic(ABC):
    def __init__(self, component_item=None):
        self.component_item = component_item
        self.enabled = True
        # Flags de forzado desde el editor de propiedades
        self._forced_open = False   # True => nunca conduce
        self._forced_close = False  # True => siempre conduce

    @property
    def tag(self) -> str:
        return getattr(self.component_item, 'tag', '') if self.component_item else ""

    @abstractmethod
    def update(self, delta_time: float):
        pass

    def is_conducting(self, terminal1_id: str, terminal2_id: str) -> bool:
        """Wrapper que aplica los flags de forzado antes de delegar a _conduct."""
        if self._forced_open:
            return False
        if self._forced_close:
            return True
        return self._conduct(terminal1_id, terminal2_id)

    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        """Lógica de conducción interna — sobrescribir en subclases."""
        return True

    def reset(self):
        self._forced_open = False
        self._forced_close = False
