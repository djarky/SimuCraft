"""
Comando base para patrón Command con undo/redo
"""
from PySide6.QtGui import QUndoCommand


class BaseCommand(QUndoCommand):
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.executed = False
        
    def redo(self):
        if not self.executed:
            self.execute()
            self.executed = True
        else:
            self._redo()
    
    def undo(self):
        self._undo()
    
    def execute(self):
        """Ejecutar por primera vez"""
        pass
    
    def _redo(self):
        """Rehacer después de undo"""
        pass
    
    def _undo(self):
        """Deshacer"""
        pass
