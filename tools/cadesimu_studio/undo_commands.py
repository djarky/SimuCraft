"""
Comandos de Deshacer / Rehacer (QUndoCommand) para el editor de símbolos SimuCraft.
"""
from typing import List, Tuple
from PySide6.QtGui import QUndoCommand
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene


class AddItemsCommand(QUndoCommand):
    """Comando para añadir uno o varios elementos a la escena."""

    def __init__(self, scene: QGraphicsScene, items: List[QGraphicsItem], text: str = "Añadir elemento"):
        super().__init__(text)
        self.scene = scene
        self.items = list(items)

    def undo(self):
        for it in self.items:
            if it.scene() == self.scene:
                self.scene.removeItem(it)
        if hasattr(self.scene, 'on_item_changed_callback') and self.scene.on_item_changed_callback:
            self.scene.on_item_changed_callback()

    def redo(self):
        for it in self.items:
            if it.scene() != self.scene:
                self.scene.addItem(it)
        if hasattr(self.scene, 'on_item_changed_callback') and self.scene.on_item_changed_callback:
            self.scene.on_item_changed_callback()


class DeleteItemsCommand(QUndoCommand):
    """Comando para eliminar uno o varios elementos de la escena."""

    def __init__(self, scene: QGraphicsScene, items: List[QGraphicsItem], text: str = "Eliminar elemento"):
        super().__init__(text)
        self.scene = scene
        self.items = list(items)

    def undo(self):
        for it in self.items:
            if it.scene() != self.scene:
                self.scene.addItem(it)
        if hasattr(self.scene, 'on_item_changed_callback') and self.scene.on_item_changed_callback:
            self.scene.on_item_changed_callback()

    def redo(self):
        for it in self.items:
            if it.scene() == self.scene:
                self.scene.removeItem(it)
        if hasattr(self.scene, 'on_item_changed_callback') and self.scene.on_item_changed_callback:
            self.scene.on_item_changed_callback()


class MoveItemsCommand(QUndoCommand):
    """Comando para registrar el desplazamiento de elementos."""

    def __init__(self, items: List[QGraphicsItem], old_positions: List[QPointF], new_positions: List[QPointF], text: str = "Mover elemento"):
        super().__init__(text)
        self.items = list(items)
        self.old_positions = list(old_positions)
        self.new_positions = list(new_positions)

    def undo(self):
        for it, pos in zip(self.items, self.old_positions):
            it.setPos(pos)
        if self.items and self.items[0].scene() and hasattr(self.items[0].scene(), 'on_item_changed_callback'):
            cb = self.items[0].scene().on_item_changed_callback
            if cb:
                cb()

    def redo(self):
        for it, pos in zip(self.items, self.new_positions):
            it.setPos(pos)
        if self.items and self.items[0].scene() and hasattr(self.items[0].scene(), 'on_item_changed_callback'):
            cb = self.items[0].scene().on_item_changed_callback
            if cb:
                cb()

