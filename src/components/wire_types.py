"""
Catálogo y definiciones técnicas de conductores y cables según CADe SIMU y normas IEC/UNE.
Proporciona colores normalizados, grosores, estilos de línea y utilidades de renderizado.
"""
from typing import Dict, Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen, QPixmap, QPainter, QBrush, QIcon


WIRE_CATALOG: Dict[int, Dict[str, Any]] = {
    4000: {
        "id": 4000,
        "key": "cable_fase",
        "name": "Fase (L1)",
        "full_name": "Cable Fase (Marrón)",
        "color": "#8B4513",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor de fase principal marrón (L1)",
        "tag": "L1",
        "category": "Potencia CA"
    },
    4001: {
        "id": 4001,
        "key": "cable_neutro",
        "name": "Neutro (N)",
        "full_name": "Cable Neutro (Azul)",
        "color": "#0080FF",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor de neutro reglamentario azul claro",
        "tag": "N",
        "category": "Potencia CA"
    },
    4002: {
        "id": 4002,
        "key": "cable_proteccion",
        "name": "Tierra (PE)",
        "full_name": "Cable Protección / Tierra",
        "color": "#16A34A",
        "width": 2.0,
        "style": Qt.DashLine,
        "description": "Conductor de protección equipotencial y tierra",
        "tag": "PE",
        "category": "Protección"
    },
    4003: {
        "id": 4003,
        "key": "cable_positivo",
        "name": "Positivo (+)",
        "full_name": "Cable Positivo CC (Rojo)",
        "color": "#DC2626",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor de polaridad positiva en corriente continua",
        "tag": "+",
        "category": "Control CC"
    },
    4004: {
        "id": 4004,
        "key": "cable_negativo",
        "name": "Negativo (-)",
        "full_name": "Cable Negativo CC (Azul Oscuro)",
        "color": "#1E3A8A",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor de polaridad negativa en corriente continua",
        "tag": "-",
        "category": "Control CC"
    },
    4009: {
        "id": 4009,
        "key": "cable_conexion",
        "name": "Maniobra (Negro)",
        "full_name": "Cable Auxiliar / Conexión",
        "color": "#18181B",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor auxiliar de mando y maniobra estándar",
        "tag": "AUX",
        "category": "Maniobra"
    },
    4011: {
        "id": 4011,
        "key": "cable_gris",
        "name": "Fase L2 / Gris",
        "full_name": "Cable Fase Gris (L2/L3)",
        "color": "#6B7280",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor de fase L2/L3 o interconexión gris",
        "tag": "L2",
        "category": "Potencia CA"
    },
    4016: {
        "id": 4016,
        "key": "cable_violeta",
        "name": "Señal (Violeta)",
        "full_name": "Cable Señalización Violeta",
        "color": "#9333EA",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Conductor para circuitos de señalización o autómatas",
        "tag": "SIG",
        "category": "Señal"
    },
    4017: {
        "id": 4017,
        "key": "cable_naranja",
        "name": "Enclave (Naranja)",
        "full_name": "Cable Enclavamiento / Tensión Externa",
        "color": "#EA580C",
        "width": 2.0,
        "style": Qt.SolidLine,
        "description": "Circuitos con tensión externa o enclavamientos de seguridad",
        "tag": "ENC",
        "category": "Seguridad"
    },
    4010: {
        "id": 4010,
        "key": "manguera",
        "name": "Manguera",
        "full_name": "Manguera Multiconductora",
        "color": "#475569",
        "width": 3.2,
        "style": Qt.SolidLine,
        "description": "Manguera reforzada con múltiples conductores",
        "tag": "MANG",
        "category": "Mangueras"
    },
    4019: {
        "id": 4019,
        "key": "manguera_trifasica",
        "name": "Trifásico III",
        "full_name": "Manguera Trifásica (L1-L2-L3)",
        "color": "#854D0E",
        "width": 3.5,
        "style": Qt.SolidLine,
        "description": "Trazado multilínea trifásico industrial",
        "tag": "3F",
        "category": "Potencia CA"
    }
}

KEY_TO_ID: Dict[str, int] = {info["key"]: tid for tid, info in WIRE_CATALOG.items()}


def get_wire_info(type_id_or_key: Any) -> Dict[str, Any]:
    """Obtiene la configuración de un cable por su ID numérico (4000) o clave ('cable_fase')."""
    if isinstance(type_id_or_key, int):
        return WIRE_CATALOG.get(type_id_or_key, WIRE_CATALOG[4000])
    if isinstance(type_id_or_key, str):
        if type_id_or_key.isdigit():
            tid = int(type_id_or_key)
            return WIRE_CATALOG.get(tid, WIRE_CATALOG[4000])
        tid = KEY_TO_ID.get(type_id_or_key)
        if tid and tid in WIRE_CATALOG:
            return WIRE_CATALOG[tid]
    return WIRE_CATALOG[4000]


def create_wire_icon(color_hex: str, width: float = 2.0, style: Qt.PenStyle = Qt.SolidLine, size: int = 24) -> QIcon:
    """Genera un icono visual nítido representando la línea y el color del conductor."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    # Fondo redondeado suave
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#24273a")))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 4, 4)

    # Línea del cable en diagonal o transversal
    color = QColor(color_hex)
    pen = QPen(color, max(2.5, width), style)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(4, size - 5, size - 4, 5)

    # Punto terminal en el extremo
    p.setBrush(QBrush(color.lighter(130)))
    p.setPen(QPen(QColor("#11111b"), 1))
    p.drawEllipse(size - 7, 3, 4, 4)
    p.drawEllipse(3, size - 7, 4, 4)

    p.end()
    return QIcon(pix)
