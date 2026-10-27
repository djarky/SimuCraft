"""
Vista del circuito con zoom, pan, mouse tracking y atajos integrados
"""
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QWheelEvent, QPainter, QKeyEvent, QMouseEvent


class CircuitView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        
        self.setStyleSheet("""
            QGraphicsView {
                background: #181825;
                border: none;
            }
        """)

        self._pan = False
        self._pan_start = QPoint()

    def wheelEvent(self, event: QWheelEvent):
        # Zoom con rueda del ratón
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent):
        # Si la escena está en modo inserción o cableado, no activar la caja elástica de selección
        scene = self.scene()
        if scene and (getattr(scene, 'placement_mode', False) or getattr(scene, 'wiring_mode', False)):
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag)

        if event.button() == Qt.MiddleButton:
            self._pan = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._pan:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self._pan = False
            scene = self.scene()
            if scene and getattr(scene, 'placement_mode', False):
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        scene = self.scene()
        # Si se pulsa ESC: cancelar inserción o cableado
        if event.key() == Qt.Key_Escape:
            if scene:
                if getattr(scene, 'placement_mode', False):
                    scene.cancel_placement()
                    event.accept()
                    return
                if getattr(scene, 'wiring_mode', False):
                    scene.cancel_wire()
                    event.accept()
                    return

        # Si se pulsa Supr o Backspace: eliminar elementos seleccionados
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if scene and hasattr(scene, 'delete_selected_items'):
                scene.delete_selected_items()
                event.accept()
                return

        super().keyPressEvent(event)

    def fit_in_view(self):
        scene = self.scene()
        if not scene:
            return
        # Ajustar a la hoja de dibujo o a los componentes presentes
        items_rect = scene.itemsBoundingRect()
        if hasattr(scene, 'sheet_rect') and not items_rect.isEmpty():
            target_rect = items_rect.united(scene.sheet_rect)
        elif hasattr(scene, 'sheet_rect'):
            target_rect = scene.sheet_rect
        else:
            target_rect = scene.sceneRect()
        self.fitInView(target_rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)

    def reset_view(self):
        self.resetTransform()
