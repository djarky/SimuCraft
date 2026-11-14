"""
Diálogo de propiedades avanzadas para edición geométrica y de estilo de primitivas vectoriales.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QColorDialog, QCheckBox, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QRectF, QLineF
from PySide6.QtGui import QColor, QPen, QBrush, QFont

from .graphic_primitives import (
    GraphicLineItem, GraphicRectItem,
    GraphicCircleItem, GraphicTextItem,
    GraphicArcItem, GraphicPolygonItem
)
from .terminal_handle import TerminalHandleItem
from .config import TERMINAL_TYPE_COLORS


class PrimitivePropertiesDialog(QDialog):
    """Diálogo modal para editar geometría, estilo, relleno y texto de un elemento."""

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Propiedades del Elemento")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # ── Color de trazo y grosor ──────────────────────────────────────────
        pen = getattr(item, 'pen', None)
        self.cur_stroke_color = pen().color() if pen else QColor("#ffffff")
        if isinstance(item, GraphicTextItem):
            self.cur_stroke_color = item.defaultTextColor()

        self.btn_stroke_color = QPushButton()
        self._update_color_button(self.btn_stroke_color, self.cur_stroke_color)
        self.btn_stroke_color.clicked.connect(self._pick_stroke_color)
        form.addRow("Color de trazo:", self.btn_stroke_color)

        if not isinstance(item, (GraphicTextItem, TerminalHandleItem)):
            self.spin_width = QDoubleSpinBox()
            self.spin_width.setRange(0.5, 12.0)
            self.spin_width.setSingleStep(0.2)
            self.spin_width.setValue(pen().widthF() if pen else 1.8)
            form.addRow("Grosor de línea:", self.spin_width)

            self.combo_style = QComboBox()
            self.combo_style.addItem("Sólido", Qt.SolidLine)
            self.combo_style.addItem("Discontinuo", Qt.DashLine)
            self.combo_style.addItem("Punteado", Qt.DotLine)
            if pen:
                idx = self.combo_style.findData(pen().style())
                if idx >= 0:
                    self.combo_style.setCurrentIndex(idx)
            form.addRow("Estilo de trazo:", self.combo_style)

        # ── Color de Relleno ─────────────────────────────────────────────────
        if isinstance(item, (GraphicRectItem, GraphicCircleItem, GraphicPolygonItem)):
            brush = item.brush()
            has_fill = brush.style() != Qt.NoBrush
            self.cur_fill_color = brush.color() if has_fill else QColor(0, 0, 0, 0)

            fill_row = QHBoxLayout()
            self.chk_fill = QCheckBox("Relleno activo")
            self.chk_fill.setChecked(has_fill)
            self.btn_fill_color = QPushButton()
            self._update_color_button(self.btn_fill_color, self.cur_fill_color if has_fill else QColor("#ffffff"))
            self.btn_fill_color.clicked.connect(self._pick_fill_color)
            self.btn_fill_color.setEnabled(has_fill)
            self.chk_fill.toggled.connect(self.btn_fill_color.setEnabled)

            fill_row.addWidget(self.chk_fill)
            fill_row.addWidget(self.btn_fill_color)
            form.addRow("Relleno:", fill_row)

        # ── Campos específicos por tipo de primitiva ─────────────────────────
        if isinstance(item, GraphicLineItem):
            line = item.line()
            self.spin_x1 = QDoubleSpinBox()
            self.spin_x1.setRange(-2000, 2000)
            self.spin_x1.setValue(line.x1())
            self.spin_y1 = QDoubleSpinBox()
            self.spin_y1.setRange(-2000, 2000)
            self.spin_y1.setValue(line.y1())
            form.addRow("X1 (Inicio):", self.spin_x1)
            form.addRow("Y1 (Inicio):", self.spin_y1)

            self.spin_x2 = QDoubleSpinBox()
            self.spin_x2.setRange(-2000, 2000)
            self.spin_x2.setValue(line.x2())
            self.spin_y2 = QDoubleSpinBox()
            self.spin_y2.setRange(-2000, 2000)
            self.spin_y2.setValue(line.y2())
            form.addRow("X2 (Fin):", self.spin_x2)
            form.addRow("Y2 (Fin):", self.spin_y2)

        elif isinstance(item, (GraphicRectItem, GraphicCircleItem)):
            r = item.rect()
            self.spin_x = QDoubleSpinBox()
            self.spin_x.setRange(-2000, 2000)
            self.spin_x.setValue(r.x())
            self.spin_y = QDoubleSpinBox()
            self.spin_y.setRange(-2000, 2000)
            self.spin_y.setValue(r.y())
            form.addRow("Posición X:", self.spin_x)
            form.addRow("Posición Y:", self.spin_y)

            self.spin_w = QDoubleSpinBox()
            self.spin_w.setRange(2, 2000)
            self.spin_w.setValue(r.width())
            self.spin_h = QDoubleSpinBox()
            self.spin_h.setRange(2, 2000)
            self.spin_h.setValue(r.height())
            form.addRow("Ancho:", self.spin_w)
            form.addRow("Alto:", self.spin_h)

            if isinstance(item, GraphicRectItem):
                self.spin_rx = QDoubleSpinBox()
                self.spin_rx.setRange(0, 100)
                self.spin_rx.setValue(item.rx)
                form.addRow("Radio esquinas:", self.spin_rx)

        elif isinstance(item, GraphicTextItem):
            self.input_text = QLineEdit(item.toPlainText())
            form.addRow("Texto:", self.input_text)

            font = item.font()
            self.spin_font_size = QSpinBox()
            self.spin_font_size.setRange(4, 72)
            self.spin_font_size.setValue(font.pointSize() if font.pointSize() > 0 else 9)
            form.addRow("Tamaño de letra:", self.spin_font_size)

            self.chk_bold = QCheckBox("Negrita")
            self.chk_bold.setChecked(font.bold())
            form.addRow("", self.chk_bold)

        elif isinstance(item, TerminalHandleItem):
            # Los datos del borne están en term_data (dict), no en atributos directos
            td = item.term_data
            self.input_tid = QLineEdit(str(td.get('id', '')))
            form.addRow("ID Borne:", self.input_tid)

            self.input_tname = QLineEdit(str(td.get('name', '')))
            form.addRow("Nombre/Etiqueta:", self.input_tname)

            self.combo_type = QComboBox()
            for t_k in TERMINAL_TYPE_COLORS.keys():
                self.combo_type.addItem(t_k, t_k)
            idx_t = self.combo_type.findData(td.get('type', 'generic'))
            if idx_t >= 0:
                self.combo_type.setCurrentIndex(idx_t)
            form.addRow("Tipo de borne:", self.combo_type)

            self.combo_ori = QComboBox()
            for o_k, o_lbl in [('n', 'Norte (Arriba)'), ('s', 'Sur (Abajo)'), ('e', 'Este (Derecha)'), ('w', 'Oeste (Izquierda)')]:
                self.combo_ori.addItem(o_lbl, o_k)
            idx_o = self.combo_ori.findData(td.get('orientation', 'n'))
            if idx_o >= 0:
                self.combo_ori.setCurrentIndex(idx_o)
            form.addRow("Orientación:", self.combo_ori)

        # Botones de diálogo
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.apply_changes)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_color_button(self, btn: QPushButton, color: QColor):
        btn.setStyleSheet(f"background-color: {color.name()}; min-width: 60px; min-height: 24px; border: 1px solid #555; border-radius: 3px;")
        btn.setText(color.name().upper())

    def _pick_stroke_color(self):
        c = QColorDialog.getColor(self.cur_stroke_color, self, "Seleccionar Color de Trazo")
        if c.isValid():
            self.cur_stroke_color = c
            self._update_color_button(self.btn_stroke_color, c)

    def _pick_fill_color(self):
        c = QColorDialog.getColor(self.cur_fill_color, self, "Seleccionar Color de Relleno")
        if c.isValid():
            self.cur_fill_color = c
            self._update_color_button(self.btn_fill_color, c)

    def apply_changes(self):
        """Aplica los cambios al objeto de escena."""
        pen = QPen(self.cur_stroke_color, getattr(self, 'spin_width', None).value() if hasattr(self, 'spin_width') else 1.8,
                   getattr(self, 'combo_style', None).currentData() if hasattr(self, 'combo_style') else Qt.SolidLine,
                   Qt.RoundCap)

        if isinstance(self.item, GraphicLineItem):
            self.item.setPen(pen)
            self.item.setLine(QLineF(self.spin_x1.value(), self.spin_y1.value(), self.spin_x2.value(), self.spin_y2.value()))

        elif isinstance(self.item, (GraphicRectItem, GraphicCircleItem)):
            self.item.setPen(pen)
            if hasattr(self, 'chk_fill') and self.chk_fill.isChecked():
                self.item.setBrush(QBrush(self.cur_fill_color))
            else:
                self.item.setBrush(Qt.NoBrush)

            self.item.setRect(QRectF(self.spin_x.value(), self.spin_y.value(), self.spin_w.value(), self.spin_h.value()))
            if isinstance(self.item, GraphicRectItem):
                self.item.rx = self.spin_rx.value()
                self.item.ry = self.spin_rx.value()

        elif isinstance(self.item, GraphicTextItem):
            self.item.setPlainText(self.input_text.text())
            self.item.setDefaultTextColor(self.cur_stroke_color)
            f = self.item.font()
            f.setPointSize(self.spin_font_size.value())
            f.setBold(self.chk_bold.isChecked())
            self.item.setFont(f)

        elif isinstance(self.item, TerminalHandleItem):
            td = self.item.term_data
            td['id'] = self.input_tid.text().strip()
            td['name'] = self.input_tname.text().strip()
            td['type'] = self.combo_type.currentData()
            td['orientation'] = self.combo_ori.currentData()
            self.item.update()

        self.item.update()
        self.accept()

