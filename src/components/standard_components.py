"""
Biblioteca de componentes estándar de automatismos eléctricos para SimuCraft
Contiene definiciones geométricas, bornes normalizados y lógica de simulación
"""
from typing import Dict, Any
import uuid

# Alturas normalizadas en píxeles (basadas en 12 y 21 unidades de cuadrícula x 6px)
CONTROL_H = 72.0
BREAKER_H = 126.0

STANDARD_COMPONENTS: Dict[str, Dict[str, Any]] = {
    "power_l": {
        "id": "power_l",
        "type": "power",
        "name": "Línea L (230V)",
        "tag_prefix": "L1",
        "voltage": 230.0,
        "visual": {
            "width": 60,
            "height": 30,
            "terminals": [
                {"id": "L", "name": "L", "x": 0, "y": 0, "orientation": "s", "type": "power_out"}
            ]
        },
        "logic": {
            "class": "PowerRail",
            "behavior": "source",
            "voltage": 230.0
        }
    },
    
    "power_n": {
        "id": "power_n",
        "type": "neutral",
        "name": "Neutro N (0V)",
        "tag_prefix": "N",
        "voltage": 0.0,
        "visual": {
            "width": 60,
            "height": 30,
            "terminals": [
                {"id": "N", "name": "N", "x": 0, "y": 0, "orientation": "n", "type": "neutral"}
            ]
        },
        "logic": {
            "class": "PowerRail",
            "behavior": "neutral",
            "voltage": 0.0
        }
    },
    
    "pushbutton_no": {
        "id": "pushbutton_no",
        "type": "pushbutton",
        "name": "Pulsador NA (Marcha)",
        "tag_prefix": "-S",
        "normally_open": True,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": True,
            "internal_connections": [("13", "14")]
        }
    },
    
    "pushbutton_nc": {
        "id": "pushbutton_nc",
        "type": "pushbutton",
        "name": "Pulsador NC (Paro)",
        "tag_prefix": "-S",
        "normally_open": False,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "11", "name": "11", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "12", "name": "12", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": False,
            "internal_connections": [("11", "12")]
        }
    },

    "pushbutton_no_nc": {
        "id": "pushbutton_no_nc",
        "type": "pushbutton",
        "name": "Pulsador NA+NC Conmutado",
        "tag_prefix": "-S",
        "normally_open": True,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "21", "name": "21", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "22", "name": "22", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": True,
            "internal_connections": [("13", "14")]
        }
    },

    "pushbutton_mushroom_na": {
        "id": "pushbutton_mushroom_na",
        "type": "pushbutton",
        "name": "Pulsador Seta NA",
        "tag_prefix": "-S",
        "normally_open": True,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": True,
            "internal_connections": [("13", "14")]
        }
    },

    "pushbutton_mushroom_nc": {
        "id": "pushbutton_mushroom_nc",
        "type": "pushbutton",
        "name": "Pulsador Seta NC",
        "tag_prefix": "-S",
        "normally_open": False,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "11", "name": "11", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "12", "name": "12", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": False,
            "internal_connections": [("11", "12")]
        }
    },

    "selector_switch": {
        "id": "selector_switch",
        "type": "pushbutton",
        "name": "Interruptor Selector",
        "tag_prefix": "-S",
        "normally_open": True,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "maintained",
            "normally_open": True,
            "internal_connections": [("1", "2")]
        }
    },

    "limit_switch_no": {
        "id": "limit_switch_no",
        "type": "pushbutton",
        "name": "Final de Carrera NA",
        "tag_prefix": "-B",
        "normally_open": True,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": True,
            "internal_connections": [("13", "14")]
        }
    },

    "limit_switch_nc": {
        "id": "limit_switch_nc",
        "type": "pushbutton",
        "name": "Final de Carrera NC",
        "tag_prefix": "-B",
        "normally_open": False,
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "11", "name": "11", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "12", "name": "12", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "PushButton",
            "behavior": "momentary",
            "normally_open": False,
            "internal_connections": [("11", "12")]
        }
    },
    
    "contactor_coil": {
        "id": "contactor_coil",
        "type": "contactor",
        "name": "Bobina Contactor KM",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "A1", "name": "A1", "x": 0, "y": 0, "orientation": "n", "type": "coil_in"},
                {"id": "A2", "name": "A2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "coil_out"}
            ]
        },
        "logic": {
            "class": "Contactor",
            "behavior": "electromagnetic",
            "internal_connections": [("A1", "A2")]
        }
    },

    "contactor_coil_ac230": {
        "id": "contactor_coil_ac230",
        "type": "contactor",
        "name": "Bobina Contactor KM 230VAC",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "A1", "name": "A1", "x": 0, "y": 0, "orientation": "n", "type": "coil_in"},
                {"id": "A2", "name": "A2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "coil_out"}
            ]
        },
        "logic": {
            "class": "Contactor",
            "behavior": "electromagnetic",
            "internal_connections": [("A1", "A2")]
        }
    },

    "contactor_1p": {
        "id": "contactor_1p",
        "type": "contactor_power",
        "name": "Contactor de Potencia 1P",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "power_contact",
            "internal_connections": [("1", "2")]
        }
    },

    "contactor_2p": {
        "id": "contactor_2p",
        "type": "contactor_power",
        "name": "Contactor de Potencia 2P",
        "tag_prefix": "-KM",
        "visual": {
            "width": 70,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "power_contact",
            "internal_connections": [("1", "2"), ("3", "4")]
        }
    },

    "contactor_3p": {
        "id": "contactor_3p",
        "type": "contactor_power",
        "name": "Contactor de Potencia 3P",
        "tag_prefix": "-KM",
        "visual": {
            "width": 90,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "5", "name": "5", "x": 72, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "6", "name": "6", "x": 72, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "power_contact",
            "internal_connections": [("1", "2"), ("3", "4"), ("5", "6")]
        }
    },

    "contactor_4p": {
        "id": "contactor_4p",
        "type": "contactor_power",
        "name": "Contactor de Potencia 4P",
        "tag_prefix": "-KM",
        "visual": {
            "width": 126,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "5", "name": "5", "x": 72, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "7", "name": "7", "x": 108, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "6", "name": "6", "x": 72, "y": CONTROL_H, "orientation": "s", "type": "contact"},
                {"id": "8", "name": "8", "x": 108, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "power_contact",
            "internal_connections": [("1", "2"), ("3", "4"), ("5", "6"), ("7", "8")]
        }
    },
    
    "contactor_contact_no": {
        "id": "contactor_contact_no",
        "type": "contact_no",
        "name": "Contacto NA KM (Enclavamiento)",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "no_contact",
            "internal_connections": [("13", "14")]
        }
    },

    "contactor_contact_nc": {
        "id": "contactor_contact_nc",
        "type": "contact_nc",
        "name": "Contacto NC KM",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "21", "name": "21", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "22", "name": "22", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "nc_contact",
            "internal_connections": [("21", "22")]
        }
    },

    "contactor_contact_no_nc": {
        "id": "contactor_contact_no_nc",
        "type": "contact_no",
        "name": "Contacto NA+NC KM",
        "tag_prefix": "-KM",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "13", "name": "13", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "14", "name": "14", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "AuxiliaryContact",
            "behavior": "no_contact",
            "internal_connections": [("13", "14")]
        }
    },
    
    "pilot_lamp": {
        "id": "pilot_lamp",
        "type": "lamp",
        "name": "Lámpara Piloto H1",
        "tag_prefix": "-H",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "X1", "name": "X1", "x": 0, "y": 0, "orientation": "n", "type": "lamp_in"},
                {"id": "X2", "name": "X2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "lamp_out"}
            ]
        },
        "logic": {
            "class": "PilotLamp",
            "behavior": "indicator",
            "internal_connections": [("X1", "X2")]
        }
    },

    "pilot_lamp_red": {
        "id": "pilot_lamp_red",
        "type": "lamp",
        "name": "Piloto Rojo H1",
        "tag_prefix": "-H",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "X1", "name": "X1", "x": 0, "y": 0, "orientation": "n", "type": "lamp_in"},
                {"id": "X2", "name": "X2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "lamp_out"}
            ]
        },
        "logic": {
            "class": "PilotLamp",
            "behavior": "indicator",
            "internal_connections": [("X1", "X2")]
        }
    },

    "pilot_lamp_green": {
        "id": "pilot_lamp_green",
        "type": "lamp",
        "name": "Piloto Verde H2",
        "tag_prefix": "-H",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "X1", "name": "X1", "x": 0, "y": 0, "orientation": "n", "type": "lamp_in"},
                {"id": "X2", "name": "X2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "lamp_out"}
            ]
        },
        "logic": {
            "class": "PilotLamp",
            "behavior": "indicator",
            "internal_connections": [("X1", "X2")]
        }
    },

    "pilot_lamp_amber": {
        "id": "pilot_lamp_amber",
        "type": "lamp",
        "name": "Piloto Ámbar H3",
        "tag_prefix": "-H",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "X1", "name": "X1", "x": 0, "y": 0, "orientation": "n", "type": "lamp_in"},
                {"id": "X2", "name": "X2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "lamp_out"}
            ]
        },
        "logic": {
            "class": "PilotLamp",
            "behavior": "indicator",
            "internal_connections": [("X1", "X2")]
        }
    },
    
    "thermal_relay": {
        "id": "thermal_relay",
        "type": "relay",
        "name": "Relé Térmico F (95-96)",
        "tag_prefix": "-F",
        "visual": {
            "width": 50,
            "height": CONTROL_H,
            "terminals": [
                {"id": "95", "name": "95", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "96", "name": "96", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "nc_contact",
            "internal_connections": [("95", "96")]
        }
    },

    "thermal_relay_3p": {
        "id": "thermal_relay_3p",
        "type": "relay",
        "name": "Relé Térmico 3P (95-96)",
        "tag_prefix": "-F",
        "visual": {
            "width": 90,
            "height": CONTROL_H,
            "terminals": [
                {"id": "95", "name": "95", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "96", "name": "96", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "nc_contact",
            "internal_connections": [("95", "96")]
        }
    },

    "breaker_1p": {
        "id": "breaker_1p",
        "type": "breaker",
        "name": "Magnetotérmico 1P",
        "tag_prefix": "-Q",
        "visual": {
            "width": 50,
            "height": BREAKER_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": BREAKER_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "breaker",
            "internal_connections": [("1", "2")]
        }
    },

    "breaker_1p_n": {
        "id": "breaker_1p_n",
        "type": "breaker_3p",
        "name": "Magnetotérmico 1P+N",
        "tag_prefix": "-Q",
        "visual": {
            "width": 90,
            "height": BREAKER_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "N", "x": 36, "y": 0, "orientation": "n", "type": "neutral"},
                {"id": "2", "name": "2", "x": 0, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "N", "x": 36, "y": BREAKER_H, "orientation": "s", "type": "neutral"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "breaker",
            "internal_connections": [("1", "2")]
        }
    },

    "breaker_2p": {
        "id": "breaker_2p",
        "type": "breaker_3p",
        "name": "Magnetotérmico 2P",
        "tag_prefix": "-Q",
        "visual": {
            "width": 90,
            "height": BREAKER_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": BREAKER_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "breaker",
            "internal_connections": [("1", "2"), ("3", "4")]
        }
    },

    "breaker_3p": {
        "id": "breaker_3p",
        "type": "breaker_3p",
        "name": "Disyuntor Trifásico 3P",
        "tag_prefix": "-Q",
        "visual": {
            "width": 90,
            "height": BREAKER_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "5", "name": "5", "x": 72, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "2", "name": "2", "x": 0, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "6", "name": "6", "x": 72, "y": BREAKER_H, "orientation": "s", "type": "contact"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "breaker",
            "internal_connections": [("1", "2"), ("3", "4"), ("5", "6")]
        }
    },

    "breaker_3p_n": {
        "id": "breaker_3p_n",
        "type": "breaker_3p",
        "name": "Disyuntor Trifásico 3P+N",
        "tag_prefix": "-Q",
        "visual": {
            "width": 126,
            "height": BREAKER_H,
            "terminals": [
                {"id": "1", "name": "1", "x": 0, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "3", "name": "3", "x": 36, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "5", "name": "5", "x": 72, "y": 0, "orientation": "n", "type": "contact"},
                {"id": "N", "name": "N", "x": 108, "y": 0, "orientation": "n", "type": "neutral"},
                {"id": "2", "name": "2", "x": 0, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "4", "name": "4", "x": 36, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "6", "name": "6", "x": 72, "y": BREAKER_H, "orientation": "s", "type": "contact"},
                {"id": "N2", "name": "N", "x": 108, "y": BREAKER_H, "orientation": "s", "type": "neutral"}
            ]
        },
        "logic": {
            "class": "ThermalRelay",
            "behavior": "breaker",
            "internal_connections": [("1", "2"), ("3", "4"), ("5", "6")]
        }
    },
    
    "motor_3p": {
        "id": "motor_3p",
        "type": "motor",
        "name": "Motor Trifásico M1",
        "tag_prefix": "-M",
        "visual": {
            "width": 90,
            "height": CONTROL_H,
            "terminals": [
                {"id": "U1", "name": "U1", "x": 0, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "V1", "name": "V1", "x": 36, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "W1", "name": "W1", "x": 72, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "PE", "name": "PE", "x": 108, "y": 0, "orientation": "n", "type": "earth"}
            ]
        },
        "logic": {
            "class": "Motor",
            "behavior": "load",
            "internal_connections": [("U1", "V1"), ("V1", "W1")]
        }
    },

    "motor_3p_yd": {
        "id": "motor_3p_yd",
        "type": "motor",
        "name": "Motor Trifásico Estrella-Triángulo (6 bornes)",
        "tag_prefix": "-M",
        "visual": {
            "width": 90,
            "height": CONTROL_H,
            "terminals": [
                {"id": "U1", "name": "U1", "x": 0, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "V1", "name": "V1", "x": 36, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "W1", "name": "W1", "x": 72, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "W2", "name": "W2", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "U2", "name": "U2", "x": 36, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "V2", "name": "V2", "x": 72, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "PE", "name": "PE", "x": 108, "y": 0, "orientation": "n", "type": "earth"}
            ]
        },
        "logic": {
            "class": "Motor",
            "behavior": "load",
            "internal_connections": [("U1", "U2"), ("V1", "V2"), ("W1", "W2")]
        }
    },

    "motor_1p": {
        "id": "motor_1p",
        "type": "motor",
        "name": "Motor Monofásico M1",
        "tag_prefix": "-M",
        "visual": {
            "width": 70,
            "height": CONTROL_H,
            "terminals": [
                {"id": "L1", "name": "L1", "x": 0, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "N", "name": "N", "x": 36, "y": 0, "orientation": "n", "type": "neutral"},
                {"id": "PE", "name": "PE", "x": 72, "y": 0, "orientation": "n", "type": "earth"}
            ]
        },
        "logic": {
            "class": "Motor",
            "behavior": "load",
            "internal_connections": [("L1", "N")]
        }
    },

    "motor_3p_n": {
        "id": "motor_3p_n",
        "type": "motor",
        "name": "Motor Trifásico + Neutro M1",
        "tag_prefix": "-M",
        "visual": {
            "width": 126,
            "height": CONTROL_H,
            "terminals": [
                {"id": "U1", "name": "U1", "x": 0, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "V1", "name": "V1", "x": 36, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "W1", "name": "W1", "x": 72, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "N", "name": "N", "x": 108, "y": 0, "orientation": "n", "type": "neutral"},
                {"id": "PE", "name": "PE", "x": 144, "y": 0, "orientation": "n", "type": "earth"}
            ]
        },
        "logic": {
            "class": "Motor",
            "behavior": "load",
            "internal_connections": [("U1", "V1"), ("V1", "W1")]
        }
    },

    "motor_dahlander": {
        "id": "motor_dahlander",
        "type": "motor",
        "name": "Motor Dahlander 2 Velocidades",
        "tag_prefix": "-M",
        "visual": {
            "width": 90,
            "height": CONTROL_H,
            "terminals": [
                {"id": "1U", "name": "1U", "x": 0, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "1V", "name": "1V", "x": 36, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "1W", "name": "1W", "x": 72, "y": 0, "orientation": "n", "type": "motor_in"},
                {"id": "2U", "name": "2U", "x": 0, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "2V", "name": "2V", "x": 36, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "2W", "name": "2W", "x": 72, "y": CONTROL_H, "orientation": "s", "type": "motor_in"},
                {"id": "PE", "name": "PE", "x": 108, "y": 0, "orientation": "n", "type": "earth"}
            ]
        },
        "logic": {
            "class": "Motor",
            "behavior": "load",
            "internal_connections": [("1U", "1V"), ("1V", "1W")]
        }
    },
}


# Cargar símbolos personalizados definidos por el usuario desde custom_symbols.json
def reload_custom_symbols():
    from pathlib import Path
    import json
    root = Path(__file__).resolve().parent.parent.parent
    custom_path = root / "data" / "custom_symbols.json"
    if not custom_path.exists():
        custom_path = root / "custom_symbols.json"
    if custom_path.exists():
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
                if isinstance(custom_data, dict):
                    STANDARD_COMPONENTS.update(custom_data)
        except Exception as e:
            print(f"Aviso: no se pudo cargar custom_symbols.json: {e}")

reload_custom_symbols()


def create_standard_component(comp_key: str, tag: str = None) -> Dict[str, Any]:
    """Crea una copia fresca de un componente estándar con ID único"""
    if comp_key not in STANDARD_COMPONENTS:
        reload_custom_symbols()
    if comp_key not in STANDARD_COMPONENTS:
        raise ValueError(f"Componente estándar '{comp_key}' no encontrado")
        
    base = STANDARD_COMPONENTS[comp_key]
    unique_id = f"{comp_key}_{uuid.uuid4().hex[:6]}"
    
    defn = {
        "id": unique_id,
        "type": base["type"],
        "name": base["name"],
        "tag": tag or base.get("tag_prefix", "K"),
        "voltage": base.get("voltage", 0.0),
        "normally_open": base.get("normally_open", True),
        "visual": dict(base["visual"]),
        "logic": dict(base["logic"]),
        "tags": {
            "auto_name_prefix": base.get("tag_prefix", "K"),
            "can_auto_name": True
        }
    }
    return defn
