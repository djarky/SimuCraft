"""
Item gráfico para componentes - renderiza símbolos vectoriales industriales y expone bornes lógicos
Soporta interacción interactiva (clic para pulsar botones), visualización de tags y estado de simulación
"""
import os
import uuid
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QRectF, QByteArray, QPointF
from PySide6.QtGui import QPainter, QFont, QPen, QBrush, QColor

from .terminal_item import TerminalItem
from ..components.power import PowerRail
from ..components.pushbutton import PushButton
from ..components.contactor import Contactor
from ..components.auxiliary import AuxiliaryContact, PilotLamp, ThermalRelay, Motor
from ..qet.parser import QETParser


class ComponentItem(QGraphicsSvgItem):
    """
    Componente visual que dibuja símbolos eléctricos normativos y gestiona bornes y lógica.
    """
    def __init__(self, component_def: dict, parent=None):
        super().__init__(parent)
        self.component_def = component_def
        self.id = component_def.get('id') or f"comp_{uuid.uuid4().hex[:6]}"
        self.component_type = component_def.get('type', 'generic')
        self.name = component_def.get('name', self.id)
        self.tag = component_def.get('tag', '')
        
        visual = component_def.get('visual', {})
        self.width = float(visual.get('width', 50.0))
        self.height = float(visual.get('height', 72.0))
        
        # Capa lógica
        self.logic_layer = component_def.get('logic', {})
        self.logic_instance = None
        self._init_logic()
        
        # Flags de interacción
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # Cargar renderer SVG si viene de QElectroTech
        self.renderer = None
        self._load_svg()
        
        # Bornes/terminales
        self.terminals = []
        self._setup_terminals(visual.get('terminals', []))
        
    def _load_svg(self):
        visual = self.component_def.get('visual', {})
        svg_content = visual.get('svg_content')
        
        if not svg_content and visual.get('elmt_path') and os.path.exists(visual.get('elmt_path')):
            parser = QETParser()
            svg_content = parser.elmt_to_svg(visual.get('elmt_path'))
            visual['svg_content'] = svg_content
            
        if svg_content and 'elmt_path' in visual:
            data = QByteArray(svg_content.encode('utf-8'))
            self.renderer = QSvgRenderer(data)
            if self.renderer.isValid():
                self.setSharedRenderer(self.renderer)

    def _init_logic(self):
        c_type = self.component_type
        if c_type == 'pushbutton':
            is_no = self.component_def.get('normally_open', True)
            self.logic_instance = PushButton(self, normally_open=is_no)
        elif c_type == 'contactor':
            self.logic_instance = Contactor(self)
        elif c_type in ('contact_no', 'contact'):
            self.logic_instance = AuxiliaryContact(self, normally_open=True)
        elif c_type == 'contact_nc':
            self.logic_instance = AuxiliaryContact(self, normally_open=False)
        elif c_type == 'lamp':
            self.logic_instance = PilotLamp(self)
        elif c_type == 'motor':
            self.logic_instance = Motor(self)
        elif c_type in ('power', 'neutral'):
            volts = self.component_def.get('voltage', 230.0 if c_type == 'power' else 0.0)
            self.logic_instance = PowerRail(self, voltage=volts)
        elif c_type in ('relay', 'breaker', 'breaker_3p'):
            self.logic_instance = ThermalRelay(self)
        elif c_type in ('contactor_power', 'contactor_3p'):
            self.logic_instance = AuxiliaryContact(self, normally_open=True)
        else:
            self.logic_instance = AuxiliaryContact(self, normally_open=True)

    def _setup_terminals(self, terminal_defs: list):
        for term_def in terminal_defs:
            term_item = TerminalItem(self, term_def)
            term_item.setPos(term_def.get('x', 0), term_def.get('y', 0))
            self.terminals.append(term_item)

    def boundingRect(self) -> QRectF:
        if self.renderer and self.renderer.isValid():
            base = super().boundingRect()
            return base.adjusted(-15, -15, 30, 20)
        if getattr(self, 'tag', '') == 'LOGO' or 'LOGO' in str(getattr(self, 'tag', '')):
            return QRectF(-60, -45, 120, 90)
        # Límites para símbolos nativos
        w = max(self.width, 50.0)
        h = max(self.height, 40.0)
        return QRectF(-25, -15, w + 35, h + 25)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 1. Si es símbolo QElectroTech externo cargado por SVG
        if self.renderer and self.renderer.isValid() and self.component_def.get('visual', {}).get('elmt_path'):
            if option is not None:
                super().paint(painter, option, widget)
            else:
                self.renderer.render(painter)
            self._draw_tag(painter)
            return

        # 2. Dibujo vectorial normalizado de componentes eléctricos
        c_type = self.component_type
        h = self.height
        
        if c_type == 'power':
            if getattr(self, 'tag', '') == 'LOGO' or 'LOGO' in str(getattr(self, 'tag', '')):
                self._draw_logo(painter)
            else:
                self._draw_power_l(painter)
        elif c_type == 'neutral':
            self._draw_power_n(painter)
        elif c_type == 'pushbutton':
            self._draw_pushbutton(painter, h)
        elif c_type == 'contactor':
            self._draw_contactor_coil(painter, h)
        elif c_type in ('contactor_power', 'contactor_3p'):
            self._draw_power_contactor(painter, h)
        elif c_type in ('contact_no', 'contact'):
            if getattr(self, 'tag', '') == 'LOGO' or 'LOGO' in str(getattr(self, 'tag', '')):
                self._draw_logo(painter)
            else:
                self._draw_contact_no(painter, h)
        elif c_type == 'contact_nc':
            self._draw_contact_nc(painter, h)
        elif c_type == 'relay':
            self._draw_thermal_relay(painter, h)
        elif c_type in ('breaker', 'breaker_3p'):
            self._draw_breaker(painter, h)
        elif c_type == 'lamp':
            self._draw_pilot_lamp(painter, h)
        elif c_type == 'motor':
            self._draw_motor(painter, h)
        else:
            self._draw_generic(painter, h)

        self._draw_tag(painter)
        
        # Indicador de selección
        if self.isSelected():
            painter.setPen(QPen(QColor(30, 144, 255), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(1, 1, -1, -1))

    def _draw_tag(self, painter: QPainter):
        """Dibujar identificador del componente (-S1, -KM1, etc.)"""
        display_tag = self.tag or self.name
        if display_tag:
            painter.setPen(QPen(QColor("#111111")))
            font = QFont("Sans Serif", 8, QFont.Bold)
            painter.setFont(font)
            # Dibujar a la derecha del símbolo
            right_x = max([t.x() for t in self.terminals], default=0) + 12
            painter.drawText(int(right_x), int(self.height / 2.0 + 3), display_tag)

    def _draw_power_l(self, p: QPainter):
        p.setPen(QPen(QColor("#B22222"), 3))
        p.drawLine(-25, 0, 25, 0)
        p.setBrush(QBrush(QColor("#B22222")))
        p.drawEllipse(-3, -3, 6, 6)
        p.setPen(QPen(QColor("#B22222")))
        p.setFont(QFont("Sans Serif", 8, QFont.Bold))
        p.drawText(-22, -8, "L (230V)")

    def _draw_power_n(self, p: QPainter):
        p.setPen(QPen(QColor("#1E90FF"), 3))
        p.drawLine(-25, 0, 25, 0)
        p.setBrush(QBrush(QColor("#1E90FF")))
        p.drawEllipse(-3, -3, 6, 6)
        p.setPen(QPen(QColor("#1E90FF")))
        p.setFont(QFont("Sans Serif", 8, QFont.Bold))
        p.drawText(-18, 14, "N (0V)")

    def _draw_pushbutton(self, p: QPainter, h: float):
        is_no = self.component_def.get('normally_open', True)
        is_pressed = False
        if self.logic_instance and hasattr(self.logic_instance, 'pressed'):
            is_pressed = self.logic_instance.pressed
            
        is_closed = is_pressed if is_no else (not is_pressed)
        
        # Conexiones verticales
        p.setPen(QPen(Qt.black, 2))
        p.drawLine(0, 0, 0, int(h / 2.0 - 7))
        p.drawLine(0, int(h / 2.0 + 7), 0, int(h))
        
        # Bornes circulares
        p.setBrush(Qt.black)
        p.drawEllipse(-2, int(h / 2.0 - 9), 4, 4)
        p.drawEllipse(-2, int(h / 2.0 + 5), 4, 4)
        
        # Cuchilla de contacto
        p.setPen(QPen(Qt.black, 2.2))
        if is_closed:
            p.drawLine(0, int(h / 2.0 - 7), 0, int(h / 2.0 + 7))
        else:
            p.drawLine(-8, int(h / 2.0 - 6), -1, int(h / 2.0 + 7))
            
        # Vástago y pulsador
        p.setPen(QPen(Qt.black, 1.2, Qt.DashLine))
        mid_y = int(h / 2.0)
        p.drawLine(-14, mid_y, -5, mid_y)
        cap_color = QColor("#2E8B57") if is_no else QColor("#DC143C")
        p.setBrush(QBrush(cap_color))
        p.setPen(QPen(Qt.black, 1))
        # Botón cap
        offset_press = 3 if is_pressed else 0
        p.drawRect(-17 + offset_press, mid_y - 6, 4, 12)
        
        # Etiquetas de bornes
        p.setPen(QPen(QColor("#555555")))
        p.setFont(QFont("Sans Serif", 7))
        lbl_top = "13" if is_no else "11"
        lbl_bot = "14" if is_no else "12"
        p.drawText(5, 12, lbl_top)
        p.drawText(5, int(h - 4), lbl_bot)

    def _draw_contactor_coil(self, p: QPainter, h: float):
        is_energized = False
        if self.logic_instance and getattr(self.logic_instance, 'energized', False):
            is_energized = True
        
        mid_y = h / 2.0
        w = 24
        r_w = 18
        r_h = 12
        
        # Estilo escalera vertical: líneas arriba/abajo
        p.setPen(QPen(Qt.black, 2))
        p.drawLine(0, 0, 0, mid_y - r_h)
        p.drawLine(0, mid_y + r_h, 0, h)
        
        if is_energized:
            p.setBrush(QBrush(QColor(100, 200, 255, 120)))
            p.setPen(QPen(Qt.blue, 2))
        else:
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.setPen(QPen(Qt.black, 2))
        
        # Rectángulo ovalado para bobina
        p.drawRoundedRect(-r_w, mid_y - r_h, r_w*2, r_h*2, 4, 4)
        p.setPen(Qt.black)
        p.setFont(QFont("Sans Serif", 8, QFont.Bold))
        tag = self.tag or "KM"
        fm = p.fontMetrics()
        p.drawText(int(-fm.horizontalAdvance(tag)/2), int(mid_y + 3), tag)

    def _draw_power_contactor(self, p: QPainter, h: float):
        is_closed = False
        if self.logic_instance and getattr(self.logic_instance, 'closed_by_contactor', False):
            is_closed = True

        mid_y = int(h / 2.0)
        poles = sorted(list(set(int(t.x()) for t in self.terminals)))
        if not poles:
            poles = [0, 36, 72]

        p.setPen(QPen(Qt.black, 2))
        for i, px in enumerate(poles):
            p.drawLine(px, 0, px, mid_y - 10)
            p.drawLine(px, mid_y + 10, px, int(h))

            p.setBrush(Qt.black)
            p.drawEllipse(px - 2, mid_y - 12, 4, 4)
            p.drawEllipse(px - 2, mid_y + 8, 4, 4)

            p.setPen(QPen(Qt.black, 2.2))
            if is_closed:
                p.drawLine(px, mid_y - 10, px, mid_y + 10)
            else:
                p.drawLine(px - 6, mid_y - 9, px, mid_y + 9)

            # Semicírculo IEC de potencia
            p.setPen(QPen(Qt.black, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawArc(px - 9, mid_y - 13, 6, 6, 0, 180 * 16)

            # Numeración de bornes (1-2, 3-4, 5-6, 7-8)
            p.setPen(QPen(QColor("#555555")))
            p.setFont(QFont("Sans Serif", 7))
            p.drawText(px + 4, 12, str(2 * i + 1))
            p.drawText(px + 4, int(h - 4), str(2 * i + 2))

        # Enlace mecánico horizontal
        if len(poles) > 1:
            p.setPen(QPen(QColor("#666666"), 1.2, Qt.DashLine))
            p.drawLine(min(poles) - 4, mid_y, max(poles) + 4, mid_y)

    def _draw_contact_no(self, p: QPainter, h: float):
        is_closed = False
        if self.logic_instance and getattr(self.logic_instance, 'closed_by_contactor', False):
            is_closed = True

        mid_y = int(h / 2.0)
        is_vertical = True
        if len(self.terminals) >= 2:
            t1, t2 = self.terminals[0], self.terminals[1]
            if abs(t1.y() - t2.y()) < 5:
                is_vertical = False

        p.setPen(QPen(Qt.black, 2))
        if is_vertical:
            p.drawLine(0, 0, 0, mid_y - 8)
            p.drawLine(0, mid_y + 8, 0, int(h))

            p.setBrush(Qt.black)
            p.drawEllipse(-2, mid_y - 10, 4, 4)
            p.drawEllipse(-2, mid_y + 6, 4, 4)

            p.setPen(QPen(Qt.black, 2.2))
            if is_closed:
                p.drawLine(0, mid_y - 8, 0, mid_y + 8)
            else:
                p.drawLine(-7, mid_y - 7, 0, mid_y + 8)

            p.setPen(QPen(QColor("#555555")))
            p.setFont(QFont("Sans Serif", 7))
            p.drawText(5, 12, "13")
            p.drawText(5, int(h - 4), "14")
        else:
            w = 36
            p.drawLine(-w, mid_y, -8, mid_y)
            p.drawLine(8, mid_y, w, mid_y)
            p.drawLine(-8, mid_y - 10, -8, mid_y + 10)
            p.drawLine(8, mid_y - 10, 8, mid_y + 10)
            if is_closed:
                p.drawLine(-8, mid_y, 8, mid_y)
            else:
                p.drawLine(-8, mid_y - 4, 4, mid_y + 10)

    def _draw_contact_nc(self, p: QPainter, h: float):
        is_closed = True
        if self.logic_instance and getattr(self.logic_instance, 'closed_by_contactor', False):
            is_closed = False

        mid_y = int(h / 2.0)
        is_vertical = True
        if len(self.terminals) >= 2:
            t1, t2 = self.terminals[0], self.terminals[1]
            if abs(t1.y() - t2.y()) < 5:
                is_vertical = False

        p.setPen(QPen(Qt.black, 2))
        if is_vertical:
            p.drawLine(0, 0, 0, mid_y - 8)
            p.drawLine(0, mid_y + 8, 0, int(h))

            p.setBrush(Qt.black)
            p.drawEllipse(-2, mid_y - 10, 4, 4)
            p.drawEllipse(-2, mid_y + 6, 4, 4)

            p.setPen(QPen(Qt.black, 2.2))
            if is_closed:
                p.drawLine(0, mid_y - 8, 0, mid_y + 8)
                p.drawLine(-6, mid_y - 6, 6, mid_y + 6)
            else:
                p.drawLine(-7, mid_y - 7, 0, mid_y + 8)
                p.drawLine(-9, mid_y - 5, -3, mid_y + 1)

            p.setPen(QPen(QColor("#555555")))
            p.setFont(QFont("Sans Serif", 7))
            p.drawText(5, 12, "21")
            p.drawText(5, int(h - 4), "22")
        else:
            w = 36
            p.drawLine(-w, mid_y, -6, mid_y)
            p.drawLine(6, mid_y, w, mid_y)
            p.drawLine(-6, mid_y - 10, -6, mid_y + 10)
            p.drawLine(6, mid_y - 10, 6, mid_y + 10)
            if is_closed:
                p.drawLine(-6, mid_y, 6, mid_y)
            else:
                p.drawLine(-6, mid_y - 2, 6, mid_y + 8)

    def _draw_thermal_relay(self, p: QPainter, h: float):
        mid_y = int(h / 2.0)
        p.setPen(QPen(Qt.black, 2))
        p.drawLine(0, 0, 0, mid_y - 7)
        p.drawLine(0, mid_y + 7, 0, int(h))
        
        p.setBrush(Qt.black)
        p.drawEllipse(-2, mid_y - 9, 4, 4)
        p.drawEllipse(-2, mid_y + 5, 4, 4)
        
        # Cuchilla NC
        p.setPen(QPen(Qt.black, 2.2))
        p.drawLine(0, mid_y - 7, 0, mid_y + 7)
        
        # Símbolo bimetal térmico
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(Qt.black, 1.2))
        p.drawRect(-7, mid_y - 4, 8, 8)
        
        p.setPen(QPen(QColor("#555555")))
        p.setFont(QFont("Sans Serif", 7))
        p.drawText(5, 12, "95")
        p.drawText(5, int(h - 4), "96")

    def _draw_breaker(self, p: QPainter, h: float):
        mid_y = int(h / 2.0)
        poles = sorted(set([t.x() for t in self.terminals if t.y() == 0]))
        if not poles:
            poles = [0, 24, 48] if self.component_type == 'breaker_3p' else [0]
        
        p.setPen(QPen(Qt.black, 2))
        p.setBrush(QBrush(QColor("#FFFACD")))
        # Caja del disyuntor
        left = min(poles) - 8
        right = max(poles) + 8
        p.drawRect(left, mid_y - 35, right - left, 70)
        
        for px in poles:
            p.setPen(QPen(Qt.black, 2))
            p.drawLine(int(px), 0, int(px), mid_y - 12)
            p.drawLine(int(px), mid_y + 12, int(px), int(h))
            
            p.setBrush(Qt.black)
            p.drawEllipse(int(px - 2), mid_y - 14, 4, 4)
            p.drawEllipse(int(px - 2), mid_y + 10, 4, 4)
            
            # Contacto abierto/cerrado tipo disyuntor
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(Qt.black, 2.5))
            p.drawLine(int(px - 6), mid_y - 10, int(px + 1), mid_y + 10)
            p.drawLine(int(px - 8), mid_y - 2, int(px - 4), mid_y + 2)
            p.drawLine(int(px - 4), mid_y - 2, int(px - 8), mid_y + 2)
        
        # Etiqueta
        p.setPen(Qt.black)
        p.setFont(QFont("Arial", 8, QFont.Bold))
        p.drawText(left + 2, mid_y - 20, self.tag or "Q")
        p.setFont(QFont("Arial", 7))
        if self.component_type == 'breaker_3p':
            p.drawText(left + 2, mid_y + 28, "3P")

    def _draw_pilot_lamp(self, p: QPainter, h: float):
        is_lit = False
        if self.logic_instance and getattr(self.logic_instance, 'lit', False):
            is_lit = True
            
        mid_y = int(h / 2.0)
        radius = 14
        
        p.setPen(QPen(Qt.black, 2))
        p.drawLine(0, 0, 0, mid_y - radius)
        p.drawLine(0, mid_y + radius, 0, int(h))
        
        if is_lit:
            p.setBrush(QBrush(QColor(255, 215, 0, 230)))
            p.setPen(QPen(QColor(255, 140, 0), 2.5))
        else:
            p.setBrush(QBrush(QColor("#FFFDF0")))
            p.setPen(QPen(Qt.black, 2))
            
        p.drawEllipse(QPointF(0, mid_y), radius, radius)
        # Cruz en el piloto
        diag = int(radius * 0.707)
        p.drawLine(-diag, mid_y - diag, diag, mid_y + diag)
        p.drawLine(-diag, mid_y + diag, diag, mid_y - diag)
        
        p.setPen(QPen(QColor("#555555")))
        p.setFont(QFont("Sans Serif", 7))
        p.drawText(5, 12, "X1")
        p.drawText(5, int(h - 4), "X2")

    def _draw_motor(self, p: QPainter, h: float):
        import math
        mid_y = int(h / 2.0)
        
        top_terms = [t for t in self.terminals if t.y() <= mid_y]
        bot_terms = [t for t in self.terminals if t.y() > mid_y]
        
        # Centro geométrico de las fases principales (U1, V1, W1 o L1, N)
        phase_terms = [t for t in top_terms if getattr(t, 'terminal_id', '') != 'PE']
        if not phase_terms:
            phase_terms = top_terms or self.terminals

        if phase_terms:
            center_x = sum(t.x() for t in phase_terms) / len(phase_terms)
        else:
            center_x = 36.0

        radius = 28
        
        is_running = False
        if self.logic_instance and getattr(self.logic_instance, 'running', False):
            is_running = True
        
        p.setPen(QPen(Qt.black, 2))
        
        # Conexiones superiores hacia el cuerpo del motor
        for t in top_terms:
            tx = int(t.x())
            dx = abs(tx - center_x)
            if dx <= radius:
                dy = math.sqrt(max(0.0, radius * radius - dx * dx))
                p.drawLine(tx, 0, tx, int(mid_y - dy))
            else:
                p.drawLine(tx, 0, tx, mid_y)
                p.drawLine(tx, mid_y, int(center_x + radius), mid_y)
                
            p.setPen(QPen(QColor("#555555")))
            p.setFont(QFont("Sans Serif", 6, QFont.Bold))
            p.drawText(tx - 6, 11, getattr(t, 'terminal_id', ''))
            p.setPen(QPen(Qt.black, 2))

        # Conexiones inferiores (e.g. Estrella-Triángulo U2, V2, W2 o Dahlander)
        for t in bot_terms:
            tx = int(t.x())
            dx = abs(tx - center_x)
            if dx <= radius:
                dy = math.sqrt(max(0.0, radius * radius - dx * dx))
                p.drawLine(tx, int(mid_y + dy), tx, int(h))
            else:
                p.drawLine(tx, int(h), tx, mid_y)
            p.setPen(QPen(QColor("#555555")))
            p.setFont(QFont("Sans Serif", 6, QFont.Bold))
            p.drawText(tx - 6, int(h - 4), getattr(t, 'terminal_id', ''))
            p.setPen(QPen(Qt.black, 2))

        # Cuerpo del motor (círculo)
        if is_running:
            p.setBrush(QBrush(QColor(46, 204, 113, 230)))
            p.setPen(QPen(QColor(39, 174, 96), 2.5))
        else:
            p.setBrush(QBrush(QColor("#F0F7FF")))
            p.setPen(QPen(Qt.black, 2))
        p.drawEllipse(QPointF(center_x, mid_y), radius, radius)
        
        # Letra M centrada
        p.setPen(QPen(Qt.black if not is_running else Qt.white))
        p.setFont(QFont("Arial", 14, QFont.Bold))
        fm = p.fontMetrics()
        m_w = fm.horizontalAdvance("M")
        p.drawText(int(center_x - m_w / 2), mid_y - 2, "M")

        # Subtexto de fases: 3~ o 1~
        p.setFont(QFont("Arial", 9, QFont.Bold))
        sub_text = "1~" if len(phase_terms) <= 2 else "3~"
        fm2 = p.fontMetrics()
        sub_w = fm2.horizontalAdvance(sub_text)
        p.drawText(int(center_x - sub_w / 2), mid_y + 16, sub_text)

    def _draw_logo(self, p: QPainter):
        # Siemens LOGO! style PLC block
        p.setPen(QPen(Qt.black, 2))
        p.setBrush(QBrush(QColor("#E8E8F0")))
        p.drawRect(-55, -40, 110, 80)
        # Top bar
        p.setBrush(QBrush(QColor("#1F1F1F")))
        p.drawRect(-55, -40, 110, 12)
        p.setPen(QPen(Qt.white))
        p.setFont(QFont("Arial", 7, QFont.Bold))
        p.drawText(-50, -31, "SIEMENS")
        p.setPen(Qt.black)
        p.setFont(QFont("Arial", 8, QFont.Bold))
        p.drawText(-28, -10, "LOGO!")
        p.setFont(QFont("Arial", 6))
        p.drawText(-35, 5, "6ED1 052-1FB00-0BA7")
        # Status LEDs
        p.setBrush(QBrush(QColor("#00FF00")))
        p.setPen(QPen(Qt.black, 1))
        p.drawEllipse(35, -38, 6, 6)
        # Terminals bottom
        p.setBrush(QBrush(QColor("#CCCCCC")))
        p.setPen(QPen(Qt.black, 1))
        for i in range(8):
            p.drawRect(-50 + i*14, 25, 10, 8)
        p.setFont(QFont("Arial", 5))
        for i in range(8):
            p.drawText(-48 + i*14, 42, f"I{i+1}")

    def _draw_generic(self, p: QPainter, h: float):
        p.setPen(QPen(Qt.black, 2))
        p.setBrush(QBrush(QColor("#F0F0F0")))
        p.drawRect(-15, 0, 30, int(h))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = self.pos()
            if self.component_type == 'pushbutton':
                if self.logic_instance and hasattr(self.logic_instance, 'pressed'):
                    if self.logic_instance.pressed:
                        self.logic_instance.release()
                    else:
                        self.logic_instance.press()
                    self.update_visual()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and hasattr(self, '_drag_start_pos'):
            old_pos = self._drag_start_pos
            new_pos = self.pos()
            delattr(self, '_drag_start_pos')
            if old_pos != new_pos:
                scene = self.scene()
                if scene:
                    main_win = scene.parent()
                    if not main_win:
                        views = scene.views()
                        if views:
                            main_win = views[0].window()
                    if main_win and hasattr(main_win, 'command_manager'):
                        from ..core.commands import MoveComponentCommand
                        cmd = MoveComponentCommand(self, old_pos, new_pos)
                        cmd.executed = True
                        main_win.command_manager.push(cmd)

    def update_visual(self):
        self.update()
        if self.scene():
            self.scene().update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            scene = self.scene()
            if scene and hasattr(scene, 'update_connected_wires'):
                scene.update_connected_wires(self)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        # Doble clic en pulsadores: abrir propiedades solo con Ctrl,
        # sin Ctrl simplemente pulsar/soltar
        if self.component_type == 'pushbutton' and not (event.modifiers() & Qt.ControlModifier):
            super().mouseDoubleClickEvent(event)
            return
        scene = self.scene()
        if scene and hasattr(scene, 'show_component_properties'):
            scene.show_component_properties(self)
        else:
            super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """Menú contextual con clic derecho — abre propiedades directamente"""
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background:#313244; color:#cdd6f4; border:1px solid #45475a; border-radius:5px; }
            QMenu::item { padding:5px 18px; }
            QMenu::item:selected { background:#45475a; }
            QMenu::separator { height:1px; background:#45475a; margin:3px 0; }
        """)
        act_props = menu.addAction("📝  Propiedades...")
        menu.addSeparator()
        if self.component_type == 'pushbutton':
            lbl = "Pulsar" if not getattr(self.logic_instance, 'pressed', False) else "Soltar"
            act_press = menu.addAction(f"\ud83d\udd18  {lbl} pulsador")
        else:
            act_press = None
        act_del = menu.addAction("❌  Eliminar componente")

        chosen = menu.exec(event.screenPos().toPoint())
        if chosen == act_props:
            scene = self.scene()
            if scene and hasattr(scene, 'show_component_properties'):
                scene.show_component_properties(self)
        elif act_press and chosen == act_press:
            if self.logic_instance and hasattr(self.logic_instance, 'pressed'):
                if self.logic_instance.pressed:
                    self.logic_instance.release()
                else:
                    self.logic_instance.press()
                self.update_visual()
        elif chosen == act_del:
            scene = self.scene()
            if scene:
                if hasattr(scene, 'remove_component_with_undo'):
                    scene.remove_component_with_undo(self)
                else:
                    scene.removeItem(self)

    def get_terminal_by_id(self, terminal_id: str) -> Optional[TerminalItem]:
        for term in self.terminals:
            if term.terminal_id == terminal_id:
                return term
        return None

    def is_conducting(self, terminal1_id: str, terminal2_id: str) -> bool:
        if self.logic_instance and hasattr(self.logic_instance, 'is_conducting'):
            return self.logic_instance.is_conducting(terminal1_id, terminal2_id)
        return False


    def update(self, delta_time: float = 0.01):
        if self.logic_instance and hasattr(self.logic_instance, 'update'):
            self.logic_instance.update(delta_time)
        try:
            super().update()
        except RuntimeError:
            # C++ ComponentItem already deleted by Qt scene — ignore silently
            pass
