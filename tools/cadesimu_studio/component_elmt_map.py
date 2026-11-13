"""
Mapa de componentes internos de SimuCraft → archivos .elmt de QElectroTech.

Permite que el Symbol Studio cargue automáticamente las primitivas gráficas
vectoriales de cada componente estándar cuando no existe `elmt_path` en
STANDARD_COMPONENTS.

Rutas relativas a la raíz de la librería QET:
  /home/vibecode/DevS/qelectrotech-elements/elements/
"""
from pathlib import Path

# Raíz de la librería QET instalada
_QET_BASE = Path('/home/vibecode/DevS/qelectrotech-elements/elements')

_WEG = _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/comandos_eletricos'
_ALLPOLE = _QET_BASE / '10_electric/10_allpole'
_RGIE = _QET_BASE / '71_rgie/7110_schema'
_ENERGY = _QET_BASE / '60_energy/11_water/01_Termicas-Fluidos2_Rafa/Eficiencia'


def _p(*parts) -> str:
    """Construye una ruta absoluta y la devuelve como string si existe, si no devuelve ''."""
    path = Path(*parts)
    return str(path) if path.exists() else ''


# ─── Mapa: clave SimuCraft → ruta .elmt (primera existente) ──────────────────
#
# Cada valor es una lista de candidatos en orden de preferencia.
# Se usará el primero que exista en el sistema de archivos.
#
_CANDIDATES: dict = {

    # ── Pulsadores / Botones ──────────────────────────────────────────────────
    'pushbutton_no': [
        _WEG / '5.3_botoes/1.1/1.5_botao pulsador na.elmt',
        _WEG / '5.3_botoes/1.2/1.3_botoeira_simples/1.2_botao pulsador na.elmt',
    ],
    'pushbutton_nc': [
        _WEG / '5.3_botoes/1.1/1.4_botao pulsador nf.elmt',
        _WEG / '5.3_botoes/1.2/1.3_botoeira_simples/1.1_botao pulsador nf.elmt',
    ],
    'pushbutton_no_nc': [
        _WEG / '5.3_botoes/1.1/1.2_botao pulsador duplo 1na 1nf.elmt',
        _WEG / '5.3_botoes/1.2/1.2_botoeira_dupla_nao_luminoso/1.1_Botao Duplo 1na 1nf.elmt',
    ],
    'pushbutton_mushroom_na': [
        _WEG / '5.3_botoes/1.1/1.6_botao pulsador reset na.elmt',
        _WEG / '5.3_botoes/1.2/1.1_botoeira_emergencia_2nf/1.1_botao emergencia 2nf.elmt',
    ],
    'pushbutton_mushroom_nc': [
        _WEG / '5.3_botoes/1.2/1.1_botoeira_emergencia_2nf/1.3_botao emergencia 1nf.elmt',
        _WEG / '5.3_botoes/1.1/1.3_botao emergencia 1nf.elmt',
    ],
    'selector_switch': [
        _WEG / '5.3_botoes/1.1/1.7_botao pulsador retentivo.elmt',
    ],
    'limit_switch_no': [
        _WEG / '5.3_botoes/1.1/1.5_botao pulsador na.elmt',  # sustituto temporal
    ],
    'limit_switch_nc': [
        _WEG / '5.3_botoes/1.1/1.4_botao pulsador nf.elmt',  # sustituto temporal
    ],

    # ── Contactores / Contactor ───────────────────────────────────────────────
    'contactor_coil': [
        _WEG / '5.4_rele_acoplador/1.2_bobina_rele_acoplador/1.7_Bobina rele acoplador 220Vca.elmt',
    ],
    'contactor_coil_ac230': [
        _WEG / '5.4_rele_acoplador/1.2_bobina_rele_acoplador/1.7_Bobina rele acoplador 220Vca.elmt',
    ],
    'contactor_1p': [
        _WEG / '5.6_contator/1.1_contatos_auxiliares_contator/1.1_contatos_contator_auxiliar_na/1.1_Contato na  13_14.elmt',
    ],
    'contactor_2p': [
        _WEG / '5.6_contator/1.1_contatos_auxiliares_contator/1.1_contatos_contator_auxiliar_na/1.1_Contato na  23_24.elmt',
    ],
    'contactor_3p': [
        _WEG / '5.6_contator/1.2_contator_referencia/1.1_Contator Tripolar.elmt',
    ],
    'contactor_4p': [
        _WEG / '5.6_contator/1.2_contator_referencia/1.1_Contator Tripolar.elmt',  # sustituto temporal
    ],
    'contactor_contact_no': [
        _WEG / '5.6_contator/1.2_contator_referencia/1.2_Contato auxiliar  contator  na.elmt',
        _WEG / '5.4_rele_acoplador/1.1_contatos_na_nf_rele_acoplador/1.1_Contato aberto Na.elmt',
    ],
    'contactor_contact_nc': [
        _WEG / '5.6_contator/1.2_contator_referencia/1.3_ Contato auxiliar contator nf.elmt',
        _WEG / '5.4_rele_acoplador/1.1_contatos_na_nf_rele_acoplador/1.2_Contato fechado Nf.elmt',
    ],
    'contactor_contact_no_nc': [
        _WEG / '5.4_rele_acoplador/1.1_contatos_na_nf_rele_acoplador/3.1_Contato 11-14-12.elmt',
    ],

    # ── Lámparas Piloto ───────────────────────────────────────────────────────
    'pilot_lamp': [
        _WEG / 'predial/15_cargas/lampada.elmt' if (
            _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/predial/15_cargas/lampada.elmt'
        ).exists() else None,
        _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/predial/15_cargas/lampada.elmt',
    ],
    'pilot_lamp_red': [
        _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/predial/15_cargas/lampada.elmt',
    ],
    'pilot_lamp_green': [
        _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/predial/15_cargas/lampada.elmt',
    ],
    'pilot_lamp_amber': [
        _QET_BASE / '10_electric/biblioteca_qeletrotech_WEG/predial/15_cargas/lampada.elmt',
    ],

    # ── Relés Térmicos ────────────────────────────────────────────────────────
    'thermal_relay': [
        _WEG / '5.4_rele_acoplador/1.2_bobina_rele_acoplador/1.7_Bobina rele acoplador 220Vca.elmt',
    ],
    'thermal_relay_3p': [
        _WEG / '5.4_rele_acoplador/1.2_bobina_rele_acoplador/1.7_Bobina rele acoplador 220Vca.elmt',
    ],

    # ── Interruptores / Breakers ──────────────────────────────────────────────
    'breaker_1p': [
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',  # sustituto
    ],
    'breaker_1p_n': [
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',
    ],
    'breaker_2p': [
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',
    ],
    'breaker_3p': [
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',
    ],
    'breaker_3p_n': [
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',
    ],

    # ── Motores ───────────────────────────────────────────────────────────────
    'motor_3p': [
        _ALLPOLE / '391_consumers_actuators/10_engines/motor-ac-2dir-pe.elmt',
        _QET_BASE / '71_rgie/7110_schema/711072_g3_appareils_electromenagers/71107210_moteur.elmt',
        _ENERGY / 'motor-electr.elmt',
    ],
    'motor_3p_yd': [
        _ALLPOLE / '391_consumers_actuators/10_engines/motor-ac-2dir-pe.elmt',
    ],
    'motor_1p': [
        _ALLPOLE / '391_consumers_actuators/10_engines/motor-ac-2dir.elmt',
        _ENERGY / 'motor-electr.elmt',
    ],
    'motor_3p_n': [
        _ALLPOLE / '391_consumers_actuators/10_engines/motor-ac-2dir-pe.elmt',
    ],
    'motor_dahlander': [
        _ALLPOLE / '391_consumers_actuators/10_engines/motor-ac-2dir-pe.elmt',
    ],

    # ── Alimentación (sin gráfico propio, se dejan vacíos) ───────────────────
    'power_l':  [],
    'power_n':  [],
}


def resolve_elmt_for_component(comp_key: str) -> str:
    """
    Devuelve la ruta absoluta del primer archivo .elmt existente para el
    componente dado, o cadena vacía si ninguno está disponible.
    """
    candidates = _CANDIDATES.get(comp_key, [])
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return ''

