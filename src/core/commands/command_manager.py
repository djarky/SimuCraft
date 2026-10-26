"""
Gestor de comandos con QUndoStack
"""
from PySide6.QtGui import QUndoStack
from PySide6.QtCore import QObject


class CommandManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.undo_stack = QUndoStack(self)
        
    def push(self, command):
        self.undo_stack.push(command)
        
    def undo(self):
        if self.undo_stack.canUndo():
            self.undo_stack.undo()
        
    def redo(self):
        if self.undo_stack.canRedo():
            self.undo_stack.redo()
        
    def can_undo(self) -> bool:
        return self.undo_stack.canUndo()
        
    def can_redo(self) -> bool:
        return self.undo_stack.canRedo()
        
    def clear(self):
        self.undo_stack.clear()
        
    def set_clean(self):
        self.undo_stack.setClean()
        
    def is_clean(self) -> bool:
        return self.undo_stack.isClean()
