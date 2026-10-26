"""
Pulsador NA/NC
"""
from .base import BaseComponentLogic


class PushButton(BaseComponentLogic):
    def __init__(self, component_item=None, normally_open=True):
        super().__init__(component_item)
        self.normally_open = normally_open
        self.pressed = False
        
    def press(self):
        self.pressed = True
        
    def release(self):
        self.pressed = False
        
    def update(self, delta_time: float):
        pass
        
    def _conduct(self, terminal1_id: str, terminal2_id: str) -> bool:
        if self.normally_open:
            return self.pressed
        else:
            return not self.pressed
