"""
Configuraciones, rutas base y constantes para CADe SIMU Studio & Mapper.
"""
from pathlib import Path
from PySide6.QtGui import QColor

# Ruta raíz del proyecto SimuCraft
BASE_PATH = Path('/home/vibecode/DevS/SimuCraft')

# Directorio de recursos BMP de CADe SIMU
BMP_RESOURCE_DIR = BASE_PATH / 'cadesimu' / 'bmp_extract' / 'cadesimu_resources'

# Rutas de catálogos y mapeos
CATALOG_COMPLETE_PATH = BASE_PATH / 'data' / 'catalogs' / 'cadesimu_symbols_complete.json'
QET_CATALOG_CSV_PATH = BASE_PATH / 'data' / 'catalogs' / 'qet_symbols_catalog.csv'
MANUAL_MAPPING_PATH = BASE_PATH / 'data' / 'mappings' / 'symbol_mapping_manual.json'
CAD_QET_MAPPING_PATH = BASE_PATH / 'data' / 'mappings' / 'cad_qet_mapping.json'
TILE_TO_CAD_PATH = BASE_PATH / 'data' / 'mappings' / 'tile_to_cad_id.json'
DISPATCH_TABLE_PATH = BASE_PATH / 'data' / 'mappings' / 'cad_id_to_component.json'
CUSTOM_SYMBOLS_PATH = BASE_PATH / 'data' / 'catalogs' / 'custom_symbols.json'

# Colores según el tipo de borne/terminal eléctrico
TERMINAL_TYPE_COLORS = {
    'motor_in': QColor('#e67e22'),   # Naranja
    'power_in': QColor('#e74c3c'),   # Rojo
    'neutral':  QColor('#3498db'),   # Azul
    'earth':    QColor('#2ecc71'),   # Verde
    'contact':  QColor('#9b59b6'),   # Púrpura
    'coil_in':  QColor('#00bcd4'),   # Cian
    'coil_out': QColor('#0097a7'),   # Cian oscuro
    'lamp_in':  QColor('#f1c40f'),   # Amarillo
    'lamp_out': QColor('#f39c12'),   # Ámbar
    'generic':  QColor('#bdc3c7')    # Gris
}

# Bitmaps de PLC / Láminas complejas con identificadores conocidos
KNOWN_BMP_IDS = {
    'bitmap_259.bmp': 259,
    'bitmap_262.bmp': 262,
    'bitmap_263.bmp': None,
    'bitmap_265.bmp': None,
    'bitmap_266.bmp': None,
}

# Descripciones de referencia
BMP_DESCRIPTIONS = {
    'bitmap_207.bmp': 'Pantalla de Inicio / Splash 4.2',
    'bitmap_250.bmp': 'Splash CADe SIMU',
    'bitmap_251.bmp': 'Splash CADe SIMU',
    'bitmap_252.bmp': 'Splash CADe SIMU',
    'bitmap_258.bmp': 'Splash CADe SIMU',
    'bitmap_259.bmp': 'Contactos / Bobinas / Pulsadores / Lógica / Siemens LOGO!',
    'bitmap_262.bmp': 'Alimentaciones / Barras / Motores / Contactores / S7-1200',
    'bitmap_263.bmp': 'PLC S7-1200 (esquemático CAD)',
    'bitmap_265.bmp': 'Sensores / Detectores adicionales',
    'bitmap_266.bmp': 'PLC SIMATIC S7-1200 (foto carátula)',
}

SPLASH_FILES = {
    'bitmap_207.bmp', 'bitmap_250.bmp', 'bitmap_251.bmp',
    'bitmap_252.bmp', 'bitmap_258.bmp'
}

# Configuración de tiles
DEFAULT_TILE_SIZE = 24
DEFAULT_SCALE = 2

# Mapeo de equivalencias entre nombres de componentes en dispatch table y SimuCraft
CAD_TO_SIMUCRAFT_ALIASES = {
    'contact_no': 'contactor_contact_no',
    'contact_nc': 'contactor_contact_nc',
    'relay_coil': 'contactor_coil',
    'emergency_stop': 'pushbutton_mushroom_nc',
    'selector_2pos': 'selector_switch',
    'motor_star_delta': 'motor_3p_yd',
    'fuse': 'breaker_1p',
}

SIMUCRAFT_TO_CAD_ALIASES = {
    'contactor_contact_no': 'contact_no',
    'contactor_contact_nc': 'contact_nc',
    'contactor_coil': 'relay_coil',
    'contactor_coil_ac230': 'relay_coil',
    'pushbutton_mushroom_nc': 'emergency_stop',
    'pushbutton_mushroom_na': 'pushbutton_no',
    'selector_switch': 'selector_2pos',
    'motor_3p_yd': 'motor_star_delta',
    'breaker_1p': 'fuse',
    'breaker_1p_n': 'fuse',
    'breaker_2p': 'fuse',
    'breaker_3p': 'breaker_3p',
    'breaker_3p_n': 'breaker_3p',
    'thermal_relay': 'thermal_relay_3p',
}


