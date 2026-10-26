"""
Vista del circuito con zoom y pan
"""
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QWheelEvent, QPainter


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
        
        self._pan = False
        self._pan_start = QPoint()
        
    def wheelEvent(self, event: QWheelEvent):
        # Zoom con rueda
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self._pan:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
        
    def fit_in_view(self):
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        
    def reset_view(self):
        self.resetTransform()
