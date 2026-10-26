"""
Diálogo de propiedades de componente - permite editar tag, nombre, estado manual, etc.
Se abre con doble clic sobre cualquier componente en el lienzo
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox,
    QFrame, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


COMPONENT_TYPE_LABELS = {
    'power':       '⚡ Línea L (Fase)',
    'neutral':     '⏚ Neutro N',
    'pushbutton':  '🔘 Pulsador',
    'contactor':   '🔲 Bobina Contactor',
    'contact_no':  '⎡ Contacto NA (normalmente abierto)',
    'contact':     '⎡ Contacto NA',
    'contact_nc':  '⎤ Contacto NC (normalmente cerrado)',
    'relay':       '🌡 Relé Térmico',
    'breaker':     '🔌 Disyuntor / Fusible',
    'breaker_3p':  '🔌 Disyuntor Trifásico 3P',
    'lamp':        '💡 Lámpara Piloto',
    'motor':       '⚙  Motor',
}

DIALOG_STYLE = """
QDialog {
    background: #1e1e2e;
    color: #cdd6f4;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
    color: #89b4fa;
    font-weight: bold;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLabel { color: #a6adc8; font-size: 12px; }
QLineEdit {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    color: #cdd6f4;
    padding: 5px 8px;
    font-size: 13px;
}
QLineEdit:focus { border-color: #89b4fa; }
QCheckBox { color: #cdd6f4; font-size: 12px; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #585b70;
    border-radius: 3px;
    background: #313244;
}
QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}
QPushButton {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    color: #cdd6f4;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton:hover { background: #45475a; border-color: #585b70; }
QPushButton#btn_ok {
    background: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
QPushButton#btn_ok:hover { background: #b4befe; }
QPushButton#btn_cancel { color: #f38ba8; border-color: #f38ba8; }
QPushButton#btn_cancel:hover { background: #3d2030; }
"""


class ComponentPropertiesDialog(QDialog):
    """
    Diálogo modal para editar las propiedades de un ComponentItem.
    Accesible con doble clic sobre el componente en el lienzo.
    """
    def __init__(self, component_item, parent=None):
        super().__init__(parent)
        self.component_item = component_item
        self.setWindowTitle("Propiedades del Componente")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)
        self._build_ui()
        self._load_values()

    # ---------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(14, 14, 14, 14)

        # Encabezado — tipo de componente
        self.lbl_type = QLabel()
        self.lbl_type.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        self.lbl_type.setFont(f)
        self.lbl_type.setStyleSheet("color: #cba6f7; margin-bottom: 2px;")
        root.addWidget(self.lbl_type)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #45475a;")
        root.addWidget(sep)

        # --- Identificación ---
        grp_id = QGroupBox("🏷  Identificación")
        form = QFormLayout(grp_id)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        self.edit_tag = QLineEdit()
        self.edit_tag.setPlaceholderText("Ej: -KM1, -S1, -K2, -F3...")
        form.addRow("Tag:", self.edit_tag)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Descripción del componente")
        form.addRow("Descripción:", self.edit_name)

        self.lbl_id = QLabel()
        self.lbl_id.setStyleSheet("color: #585b70; font-size: 10px;")
        form.addRow("ID interno:", self.lbl_id)

        root.addWidget(grp_id)

        # --- Estado de simulación ---
        grp_state = QGroupBox("⚙  Estado de simulación (forzado)")
        vstate = QVBoxLayout(grp_state)
        vstate.setSpacing(6)

        self.chk_force_open = QCheckBox("Forzar ABIERTO  (bloquea conducción)")
        self.chk_force_close = QCheckBox("Forzar CERRADO  (siempre conduce)")
        self.chk_tripped = QCheckBox("Disparado  (solo relés térmicos — abre NC)")

        vstate.addWidget(self.chk_force_open)
        vstate.addWidget(self.chk_force_close)
        vstate.addWidget(self.chk_tripped)

        # Mutuamente exclusivos: abierto / cerrado
        self.chk_force_open.toggled.connect(
            lambda v: self.chk_force_close.setChecked(False) if v else None)
        self.chk_force_close.toggled.connect(
            lambda v: self.chk_force_open.setChecked(False) if v else None)

        root.addWidget(grp_state)

        # --- Terminales ---
        grp_terms = QGroupBox("🔌 Terminales del componente")
        vterms = QVBoxLayout(grp_terms)
        self.lbl_terminals = QLabel()
        self.lbl_terminals.setWordWrap(True)
        self.lbl_terminals.setStyleSheet("color: #a6e3a1; font-size: 11px; font-family: monospace;")
        vterms.addWidget(self.lbl_terminals)
        root.addWidget(grp_terms)

        # --- Botones ---
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("✕  Cancelar")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("✓  Aplicar Cambios")
        self.btn_ok.setObjectName("btn_ok")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._apply)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_ok)
        root.addLayout(btn_row)

    # ---------------------------------------------------------------
    def _load_values(self):
        ci = self.component_item
        c_type = ci.component_type

        self.lbl_type.setText(COMPONENT_TYPE_LABELS.get(c_type, c_type))
        self.edit_tag.setText(ci.tag or '')
        self.edit_name.setText(ci.name or '')
        self.lbl_id.setText(ci.id)

        # Terminales
        lines = []
        for t in ci.terminals:
            connected = len(t.connected_wires)
            lines.append(f"  [{t.terminal_id}]  {t.terminal_type}  —  {connected} cable(s) conectado(s)")
        self.lbl_terminals.setText('\n'.join(lines) if lines else '(sin terminales definidos)')

        # Estado de simulación
        logic = ci.logic_instance
        if logic:
            self.chk_force_open.setChecked(getattr(logic, '_forced_open', False))
            self.chk_force_close.setChecked(getattr(logic, '_forced_close', False))
            has_tripped = hasattr(logic, 'tripped')
            self.chk_tripped.setEnabled(has_tripped)
            self.chk_tripped.setChecked(logic.tripped if has_tripped else False)
        else:
            self.chk_force_open.setEnabled(False)
            self.chk_force_close.setEnabled(False)
            self.chk_tripped.setEnabled(False)

        # Power/neutral: no tienen estados forzables
        if c_type in ('power', 'neutral'):
            self.chk_force_open.setEnabled(False)
            self.chk_force_close.setEnabled(False)

    # ---------------------------------------------------------------
    def _apply(self):
        ci = self.component_item
        logic = ci.logic_instance

        new_tag = self.edit_tag.text().strip()
        new_name = self.edit_name.text().strip()

        if new_tag:
            ci.tag = new_tag
            ci.component_def['tag'] = new_tag
        if new_name:
            ci.name = new_name
            ci.component_def['name'] = new_name

        if logic:
            logic._forced_open = self.chk_force_open.isChecked()
            logic._forced_close = self.chk_force_close.isChecked()
            if hasattr(logic, 'tripped'):
                logic.tripped = self.chk_tripped.isChecked()

        ci.update_visual()
        self.accept()
