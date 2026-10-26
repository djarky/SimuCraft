#!/usr/bin/env python3
"""
build_symbol_catalog.py
Extrae y cataloga todos los símbolos de CADe SIMU a partir de:
1. Recursos PE extraídos de CADe_SIMU_V4.2.exe (String Tables y Toolbars vía REA).
2. Todos los archivos .cad en cadesimu/examples/*.cad (343 type_ids / keycodes únicos).
"""

import glob
import os
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(__file__).resolve().parent.parent

def load_pe_strings_and_toolbars():
    pe_path = BASE / 'data' / 'analysis' / 'pe_resources.json'
    if not pe_path.exists():
        pe_path = BASE / 'pe_resources.json'
    with open(pe_path) as f:
        pe_data = json.load(f)

    exe_path = BASE / 'cadesimu' / 'CADe_SIMU V4.2' / 'CADe_SIMU_V4.2.exe'
    with open(exe_path, 'rb') as fp:
        exe_bytes = fp.read()

    norm = pe_data.get('normalized_result', {})
    resources = norm.get('resources', [])

    # Extraer String Table (Type 6)
    string_entries = {}
    for r in resources:
        if r.get('type', {}).get('id') == 6:
            block_id = r.get('name', {}).get('id')
            loc = r['payload']['location']
            offset = loc['offset']
            length = loc['bytes']
            block_data = exe_bytes[offset:offset+length]
            idx = 0
            for i in range(16):
                if idx + 2 > len(block_data):
                    break
                str_len = int.from_bytes(block_data[idx:idx+2], 'little')
                idx += 2
                if str_len > 0:
                    end = idx + str_len * 2
                    s = block_data[idx:end].decode('utf-16le', errors='ignore')
                    str_id = (block_id - 1) * 16 + i
                    string_entries[str_id] = s
                    idx = end

    # Extraer Toolbars (Type 241)
    toolbars = {}
    for r in resources:
        if r.get('type', {}).get('id') == 241:
            tb_id = r.get('name', {}).get('id')
            loc = r['payload']['location']
            offset = loc['offset']
            length = loc['bytes']
            tb_data = exe_bytes[offset:offset+length]
            count = int.from_bytes(tb_data[6:8], 'little')
            items = [int.from_bytes(tb_data[8+i*2:10+i*2], 'little') for i in range(count)]
            toolbars[tb_id] = items

    return string_entries, toolbars

def get_cad_stats():
    cad_stats = defaultdict(lambda: {
        'count': 0,
        'files': set(),
        'tags': Counter(),
        'terminals': set()
    })

    for fpath in sorted(glob.glob('cadesimu/examples/*.cad')):
        fname = os.path.basename(fpath)
        with open(fpath, 'r', encoding='latin-1', errors='ignore') as f:
            data = f.read()
        parts = data.split('*')
        for p in parts:
            if '#' in p:
                sub = p.split('#')
                tid_str = sub[0].strip()
                if not tid_str.isdigit():
                    continue
                tid = int(tid_str)
                tag = sub[1] if len(sub) > 1 else ''
                pins = tuple([x for x in sub[2:] if x])
                cad_stats[tid]['count'] += 1
                cad_stats[tid]['files'].add(fname)
                if tag:
                    cad_stats[tid]['tags'][tag] += 1
                if pins:
                    cad_stats[tid]['terminals'].add(pins)
    return cad_stats

# Mapeo exhaustivo curado de IDs conocido por ingeniería inversa
KNOWN_METADATA = {
    # 0: Nodo / Empalme
    0: ("Conexiones", "nodo_conexion", "Punto de conexión / Conexión eléctrica", "Punto de unión/nodo entre conductores"),
    
    # 1000 - 1012, 10550: Motores (TB 173)
    1000: ("Motores", "motor_trifasico", "Motor trifásico", "Motor trifásico estándar asíncrono (jaula de ardilla)"),
    1001: ("Motores", "motor_trifasico_yd", "Motor trifásico YD", "Motor trifásico estrella-triángulo (6 bornes U1,V1,W1,U2,V2,W2)"),
    1002: ("Motores", "motor_monofasico", "Motor monofásico", "Motor monofásico corriente alterna"),
    1003: ("Motores", "motor_dahlander", "Motor Dahalander", "Motor de dos velocidades por conmutación de polos (Dahlander)"),
    1004: ("Motores", "motor_rotor_bobinado", "Motor rotor bobinado", "Motor trifásico de rotor bobinado con anillos rozantes"),
    1005: ("Motores", "motor_dos_velocidades", "Motor Dos velocidades", "Motor de dos velocidades con devanados independientes"),
    1006: ("Motores", "motor_cc_iman", "Motor cc. Iman P.", "Motor de corriente continua de imanes permanentes"),
    1007: ("Motores", "motor_cc_indep", "Motor cc. Indep.", "Motor de corriente continua con excitación independiente"),
    1008: ("Motores", "motor_monofasico_cond", "Motor monofásico con condensador", "Motor monofásico con condensador de arranque y disyuntor centrífugo"),
    1009: ("Motores", "freno", "Freno", "Freno electromagnético para motor"),
    1010: ("Motores", "motor_trifasico_como_monofasico", "Motor trifásico como monofásico", "Conexión Steinmetz para motor trifásico en red monofásica"),
    1011: ("Motores", "motor_paso_paso_unipolar", "Motor paso a paso unipolar", "Motor paso a paso unipolar de 4/5 hilos"),
    1012: ("Motores", "motor_paso_paso_bipolar", "Motor paso a paso bipolar", "Motor paso a paso bipolar de 4 hilos"),
    10550: ("Motores", "actuador_lineal_electrico", "Actuador lineal eléctrico", "Cilindro / husillo actuador eléctrico lineal"),

    # 1050 - 1067: Neumática (TB 269)
    1050: ("Neumatica", "actuador_simple_efecto", "Actuador simple efecto", "Cilindro neumático de simple efecto con retorno por muelle"),
    1051: ("Neumatica", "actuador_doble_efecto", "Actuador doble efecto", "Cilindro neumático de doble efecto"),
    1052: ("Neumatica", "actuador_sin_vastago", "Actuador sin vástago", "Cilindro neumático lineal sin vástago"),
    1053: ("Neumatica", "actuador_sin_vastago_mag", "Actuador sin vástago magnético", "Cilindro sin vástago de arrastre magnético"),
    1054: ("Neumatica", "pinza_simple_efecto", "Pinza simple efecto", "Pinza neumática de agarre simple efecto"),
    1055: ("Neumatica", "pinza_doble_efecto", "Pinza doble efecto", "Pinza neumática de agarre doble efecto"),
    1056: ("Neumatica", "ventosa", "Ventosa", "Ventosa de vacío con eyector"),
    1057: ("Neumatica", "motor_neumatico", "Motor neumático", "Motor neumático unidireccional"),
    1058: ("Neumatica", "motor_neumatico_rev", "Motor neumático reversible", "Motor neumático bidireccional"),
    1059: ("Neumatica", "valvula_estranguladora", "Válvula estranguladora", "Válvula reguladora de caudal con antirretorno"),
    1060: ("Neumatica", "valvula_escape_rapido", "Válvula escape rápido", "Válvula de escape rápido para cilindros"),
    1061: ("Neumatica", "electrovalvula_distribuidora", "Electroválvula distribuidora", "Válvula distribuidora 5/2 o 3/2 accionamiento eléctrico"),
    1062: ("Neumatica", "actuador_giro", "Actuador giro", "Actuador rotativo / oscilante neumático"),
    1065: ("Neumatica", "final_carrera_neumatico", "Final de carrera neumático", "Válvula fin de carrera neumática con palpador"),
    1066: ("Neumatica", "pulsador_neumatico", "Pulsador neumático", "Válvula 3/2 accionada por pulsador manual"),
    1067: ("Neumatica", "unidad_mantenimiento", "Unidad mantenimiento FRL", "Unidad de mantenimiento de aire comprimido (Filtro, Regulador, Lubricador)"),

    # 1070 - 1075: Potencia electrónica / Variadores (TB 213)
    1070: ("Potencia", "resistencia_1p", "Resistencia I", "Banco de resistencia monofásica de frenado o calefactora"),
    1071: ("Potencia", "resistencia_3p", "Resistencia III", "Banco de resistencias trifásicas estatóricas/rotóricas"),
    1072: ("Potencia", "autotransformador_3p", "Autotransformador III", "Autotransformador trifásico para arranque a tensión reducida"),
    1073: ("Potencia", "arrancador_electronico_ca", "Arrancador electrónico c.a.", "Etapa de potencia de arrancador suave (Soft Starter)"),
    1074: ("Potencia", "variador_velocidad_cc_2p", "Variador velocidad c.c. II", "Variador de velocidad CC monofásico / bifásico"),
    1075: ("Potencia", "variador_velocidad_cc_3p", "Variador velocidad c.c. III", "Variador de velocidad CC trifásico"),
    1076: ("2D_3D", "rele_temporizado_zocalo", "Rele temporizado zócalo", "Relé temporizado enchufable sobre base octal/undecal"),

    # 2000 - 2009: Contactores e interruptores de potencia (TB 175)
    2000: ("Contactores", "contactor_2p", "Contactor II", "Contactor de potencia bipolar (2 polos de fuerza)"),
    2001: ("Contactores", "contactor_3p", "Contactor III", "Contactor de potencia tripolar (3 polos de fuerza)"),
    2002: ("Contactores", "contactor_4p", "Contactor IIII", "Contactor de potencia tetrapolar (4 polos de fuerza)"),
    2003: ("Contactores", "interruptor_potencia_2p", "Interruptor II", "Interruptor seccionador de carga bipolar"),
    2004: ("Contactores", "interruptor_potencia_3p", "Interruptor III", "Interruptor seccionador de carga tripolar"),
    2005: ("Contactores", "interruptor_potencia_4p", "Interruptor IIII", "Interruptor seccionador de carga tetrapolar"),
    2006: ("Contactores", "contactor_1p", "Contactor I", "Contactor de potencia unipolar (1 polo de fuerza)"),
    2007: ("Contactores", "interruptor_potencia_1p", "Interruptor I", "Interruptor seccionador unipolar"),
    2008: ("Contactores", "contactor_inversor_3p", "Contactor III conmutador", "Contactor inversor conmutado tripolar"),
    2009: ("Contactores", "enclavamiento_mecanico", "Enclavamiento", "Enclavamiento mecánico entre dos contactores"),

    # 3000 - 3020: Alimentaciones, transformadores y fuentes (TB 183)
    3000: ("Alimentaciones", "alimentacion_fase", "Alimentación Fase", "Borne de alimentación de Fase (L)"),
    3001: ("Alimentaciones", "alimentacion_neutro", "Alimentación Neutro", "Borne de alimentación de Neutro (N)"),
    3002: ("Alimentaciones", "alimentacion_proteccion", "Alimentación Protección", "Borne de toma de tierra / conductor de protección (PE)"),
    3003: ("Alimentaciones", "alimentacion_f_n", "Alimentación F+N", "Alimentación monofásica compuesta Fase + Neutro"),
    3004: ("Alimentaciones", "alimentacion_3p", "Alimentación L1+L2+L3", "Alimentación trifásica 3 líneas (L1, L2, L3)"),
    3005: ("Alimentaciones", "alimentacion_3p_pe", "Alimentación L1+L2+L3+PE", "Alimentación trifásica con tierra (L1, L2, L3 + PE)"),
    3006: ("Alimentaciones", "alimentacion_3p_n", "Alimentación L1+L2+L3+N", "Alimentación trifásica con neutro (L1, L2, L3 + N)"),
    3007: ("Alimentaciones", "alimentacion_3p_n_pe", "Alimentación L1+L2+L3+N+PE", "Alimentación trifásica completa con neutro y tierra"),
    3008: ("Alimentaciones", "alimentacion_positiva", "Alimentación +", "Borne de alimentación de corriente continua positiva (+)"),
    3009: ("Alimentaciones", "alimentacion_negativa", "Alimentación -", "Borne de alimentación de corriente continua negativa (-)"),
    3010: ("Alimentaciones", "alimentacion_dc_dual", "Alimentación +-", "Fuente de alimentación continua dual (+ -)"),
    3011: ("Alimentaciones", "alimentacion_f_n_pe", "Alimentación F+N+PE", "Alimentación monofásica con neutro y tierra"),
    3012: ("Alimentaciones", "transformador_1p", "Transformador", "Transformador monofásico reductor/elevador"),
    3013: ("Alimentaciones", "puente_rectificador", "Rectificador", "Puente rectificador de diodos monofásico de onda completa"),
    3014: ("Alimentaciones", "fuente_alimentacion_1p", "Fuente de alimentación", "Fuente conmutada / estabilizada monofásica CA/CC"),
    3015: ("Alimentaciones", "toma_tierra", "Alimentación Protección", "Símbolo de toma de tierra de protección"),
    3016: ("Alimentaciones", "diodo", "Diodo", "Diodo semiconductor / rectificador unipolar"),
    3017: ("Alimentaciones", "transformador_3p", "Transformador III", "Transformador trifásico de potencia"),
    3018: ("Alimentaciones", "fuente_alimentacion_3p", "Fuente de alimentación III", "Fuente de alimentación trifásica CA/CC"),
    3019: ("Alimentaciones", "bateria", "Bateria", "Batería / Acumulador de corriente continua"),
    3020: ("Alimentaciones", "toma_corriente", "Toma de corriente", "Base de enchufe / toma de corriente Schuko"),

    # 4000 - 4019: Conductores y cables (TB 187)
    4000: ("Cables", "cable_fase", "Cable fase", "Conductor de fase (marrón/negro/gris)"),
    4001: ("Cables", "cable_neutro", "Cable neutro", "Conductor de neutro (azul claro)"),
    4002: ("Cables", "cable_proteccion", "Cable protección", "Conductor de protección y tierra (verde-amarillo)"),
    4003: ("Cables", "cable_positivo", "Cable positivo", "Conductor de CC positivo (rojo)"),
    4004: ("Cables", "cable_negativo", "Cable negativo", "Conductor de CC negativo (azul oscuro / negro)"),
    4009: ("Cables", "cable_conexion", "Conexión", "Conductor auxiliar o de interconexión general"),
    4010: ("Cables", "manguera", "Manguera", "Manguera multiconductora"),
    4011: ("Cables", "cable_gris", "Cable color", "Conductor color especial gris"),
    4012: ("Cables", "cable_blanco", "Cable color", "Conductor color especial blanco"),
    4013: ("Cables", "cable_espesor_2", "Espedor 2", "Cable de sección reforzada calibre 2"),
    4014: ("Cables", "cable_espesor_3", "Espedor 3", "Cable de sección reforzada calibre 3"),
    4015: ("Cables", "cable_espesor_4", "Espedor 4", "Cable de sección reforzada calibre 4"),
    4016: ("Cables", "cable_violeta", "Cable color", "Conductor de señalización violeta"),
    4017: ("Cables", "cable_color_custom", "Cable color", "Conductor de control especial"),
    4018: ("Cables", "punto_conexion", "Conexión", "Punto de empalme o derivación de conductores"),
    4019: ("Cables", "manguera_trifasica", "Cable III", "Trazado simultáneo de 3 conductores trifásicos"),

    # 5000 - 5009: Fusibles y seccionadores fusibles (TB 177)
    5000: ("Protecciones", "fusible_1p", "Fusible I", "Fusible de protección unipolar (1P)"),
    5001: ("Protecciones", "fusible_1p_n", "Fusible IN", "Fusible unipolar más seccionador neutro (1P+N)"),
    5002: ("Protecciones", "fusible_2p", "Fusible II", "Fusibles bipolares (2P)"),
    5003: ("Protecciones", "fusible_3p", "Fusible III", "Fusibles tripolares de potencia (3P)"),
    5004: ("Protecciones", "fusible_3p_n", "Fusible IIIN", "Fusibles tripolares más neutro (3P+N)"),
    5005: ("Protecciones", "seccionador_fusible_1p", "Fusible seccionable I", "Seccionador portafusible unipolar"),
    5006: ("Protecciones", "seccionador_fusible_1p_n", "Fusible seccionable IN", "Seccionador portafusible 1P+N"),
    5007: ("Protecciones", "seccionador_fusible_2p", "Fusible seccionable II", "Seccionador portafusible bipolar (2P)"),
    5008: ("Protecciones", "seccionador_fusible_3p", "Fusible seccionable III", "Seccionador portafusible tripolar (3P)"),
    5009: ("Protecciones", "seccionador_fusible_3p_n", "Fusible seccionable IIIN", "Seccionador portafusible tetrapolar (3P+N)"),

    # 6000 - 6020: Automáticos, disyuntores, diferenciales y relés térmicos (TB 179, 301, 307)
    6000: ("Protecciones", "automatico_1p", "Automático I", "Interruptor magnetotérmico unipolar (PIA 1P)"),
    6001: ("Protecciones", "automatico_1p_n", "Automático IN", "Interruptor magnetotérmico 1P+N"),
    6002: ("Protecciones", "automatico_2p", "Automático II", "Interruptor magnetotérmico bipolar (PIA 2P)"),
    6003: ("Protecciones", "automatico_3p", "Automático III", "Interruptor magnetotérmico tripolar (PIA 3P)"),
    6004: ("Protecciones", "automatico_3p_n", "Automático IIIN", "Interruptor magnetotérmico tetrapolar (PIA 3P+N)"),
    6005: ("Protecciones", "diferencial_1p_n", "Diferencial IN", "Interruptor diferencial bipolar (ID 2P / 1P+N)"),
    6006: ("Protecciones", "diferencial_3p_n", "Diferencial IIIN", "Interruptor diferencial tetrapolar (ID 4P / 3P+N)"),
    6007: ("Protecciones", "rele_termico_potencia", "Relé Térmico", "Relé térmico bimetálico de potencia (bloque de 3 bimetales)"),
    6008: ("Protecciones", "disyuntor_1p", "Disyuntor I", "Disyuntor / Guardamotor unipolar"),
    6009: ("Protecciones", "disyuntor_1p_n", "Disyuntor IN", "Disyuntor / Guardamotor 1P+N"),
    6010: ("Protecciones", "disyuntor_2p", "Disyuntor II", "Disyuntor / Guardamotor bipolar"),
    6011: ("Protecciones", "disyuntor_3p", "Disyuntor III", "Disyuntor guardamotor magnetotérmico tripolar de motor"),
    6012: ("Protecciones", "disyuntor_3p_n", "Disyuntor IIIN", "Disyuntor tetrapolar 3P+N"),
    6013: ("Protecciones", "limitador_sobretensiones_1p_n", "Limitador sobretensiones IN", "Descargador de sobretensiones transitorias monofásico"),
    6014: ("Protecciones", "limitador_sobretensiones_3p_n", "Limitador sobretensiones IIIN", "Descargador de sobretensiones transitorias trifásico"),
    6015: ("2D_3D", "disyuntor_2d_3d", "Disyuntor", "Disyuntor de potencia en formato vista 2D/3D"),
    6016: ("2D_3D", "rele_termico_2d_3d", "Relé térmico", "Relé térmico en formato vista 2D/3D"),
    6017: ("2D_3D", "automatico_2d_3d", "Interruptor automático", "Interruptor automático magnetotérmico vista 2D/3D"),
    6018: ("2D_3D", "diferencial_2d_3d", "Interruptor diferencial", "Interruptor diferencial vista 2D/3D"),
    6019: ("2D_3D", "interruptor_2d_3d", "Interruptor", "Interruptor modular vista 2D/3D"),
    6020: ("2D_3D", "seccionador_2d_3d", "Seccionador", "Seccionador vista 2D/3D"),

    # 7000 - 7021: Contactos auxiliares y temporizados (TB 191, 301, 307)
    7000: ("Contactos", "contacto_aux_na", "Contacto NA", "Contacto auxiliar normalmente abierto (13-14 / 3-4)"),
    7001: ("Contactos", "contacto_aux_nc", "Contacto NC", "Contacto auxiliar normalmente cerrado (11-12 / 1-2)"),
    7002: ("Contactos", "contacto_aux_na_nc", "Contacto NA+NC", "Doble contacto auxiliar NA + NC"),
    7003: ("Contactos", "contacto_aux_con", "Contacto CON", "Contacto auxiliar conmutado (11-12-14)"),
    7004: ("Contactos", "contacto_temp_on_delay_na", "Con. Conexión NA", "Contacto temporizado al trabajo NA (ON Delay NO)"),
    7005: ("Contactos", "contacto_temp_on_delay_nc", "Con. Conexión NC", "Contacto temporizado al trabajo NC (ON Delay NC)"),
    7006: ("Contactos", "contacto_temp_on_delay_na_nc", "Con. Conexión NA+NC", "Contacto temporizado al trabajo NA + NC"),
    7007: ("Contactos", "contacto_temp_on_delay_con", "Con. Conexión CON", "Contacto temporizado al trabajo conmutado"),
    7008: ("Contactos", "contacto_temp_off_delay_na", "Con. Desconexión NA", "Contacto temporizado al reposo NA (OFF Delay NO)"),
    7009: ("Contactos", "contacto_temp_off_delay_nc", "Con. Desconexión NC", "Contacto temporizado al reposo NC (OFF Delay NC)"),
    7010: ("Contactos", "contacto_temp_off_delay_na_nc", "Con. Desconexión NA+NC", "Contacto temporizado al reposo NA + NC"),
    7011: ("Contactos", "contacto_temp_off_delay_con", "Con. Desconexión CON", "Contacto temporizado al reposo conmutado"),
    7013: ("Contactos", "contacto_temp_on_off_na", "Conexión Desconexión NA", "Contacto temporizado conexión-desconexión NA"),
    7014: ("Contactos", "contacto_temp_on_off_nc", "Conexión Desconexión NC", "Contacto temporizado conexión-desconexión NC"),
    7015: ("Contactos", "contacto_temp_on_off_na_nc", "Conexión Desconexión NA+NC", "Contacto temporizado conexión-desconexión NA+NC"),
    7016: ("2D_3D", "rele_zocalo_2d_3d", "Rele zócalo", "Base relé enchufable en vista 2D/3D"),
    7018: ("2D_3D", "contactor_2d_3d", "Contactor", "Contactor de potencia en vista 2D/3D"),
    7019: ("2D_3D", "contactos_auxiliares_2d_3d", "Contactos auxiliares", "Bloque contactos auxiliares frontal en 2D/3D"),
    7020: ("2D_3D", "contactos_aux_on_delay_2d_3d", "Contactos auxiliares ON delay", "Cámara temporizada neumática ON delay 2D/3D"),
    7021: ("2D_3D", "contactos_aux_off_delay_2d_3d", "Contactos auxiliares OFF delay", "Cámara temporizada neumática OFF delay 2D/3D"),

    # 7500 - 7600: Detectores y sensores (TB 215)
    7500: ("Detectores", "sensor_inductivo_na", "Det. inductivo NA", "Sensor de proximidad inductivo normalmente abierto"),
    7506: ("Detectores", "sensor_capacitivo_na", "Det. capacitivo NA", "Sensor de proximidad capacitivo normalmente abierto"),
    7512: ("Detectores", "sensor_magnetico_na", "Det. magnético NA", "Detector magnético / interruptor reed normalmente abierto"),
    7520: ("Detectores", "sensor_inductivo_nc", "Det. inductivo NC", "Sensor de proximidad inductivo normalmente cerrado"),
    7526: ("Detectores", "sensor_capacitivo_nc", "Det. capacitivo NC", "Sensor de proximidad capacitivo normalmente cerrado"),
    7532: ("Detectores", "sensor_magnetico_nc", "Det. magnético NC", "Detector magnético / interruptor reed normalmente cerrado"),
    7550: ("Detectores", "fotocelula_barrera", "Barrera fotoeléctrica", "Fotocélula / Sensor óptico completo"),
    7551: ("Detectores", "fotocelula_emisor", "Barrera emisor", "Emisor de barrera óptica"),
    7553: ("Detectores", "fotocelula_receptor_na", "Barrera receptor NA", "Receptor de barrera óptica NA"),
    7559: ("Detectores", "fotocelula_receptor_nc", "Barrera receptor NC", "Receptor de barrera óptica NC"),
    7570: ("Detectores", "presostato_na", "Presostato NA", "Sensor de presión / presostato contacto NA"),
    7576: ("Detectores", "vacuostato_na", "Vacuostato NA", "Sensor de vacío / vacuostato contacto NA"),
    7582: ("Detectores", "presostato_nc", "Presostato NC", "Sensor de presión / presostato contacto NC"),
    7588: ("Detectores", "vacuostato_nc", "Vacuostato NC", "Sensor de vacío / vacuostato contacto NC"),
    7594: ("Detectores", "termostato_na", "Termostato NA", "Sensor térmico / termostato de temperatura NA"),
    7600: ("Detectores", "termostato_nc", "Termostato NC", "Sensor térmico / termostato de temperatura NC"),

    # 8000 - 8023: Accionamientos (Pulsadores, interruptores, finales carrera, térmicos) (TB 189)
    8000: ("Accionamientos", "pulsador_na", "Pulsador NA", "Pulsador normalmente abierto (marcha)"),
    8001: ("Accionamientos", "pulsador_nc", "Pulsador NC", "Pulsador normalmente cerrado (paro)"),
    8002: ("Accionamientos", "pulsador_na_nc", "Pulsador NA-NC", "Pulsador de doble contacto NA + NC"),
    8003: ("Accionamientos", "pulsador_con", "Pulsador CON", "Pulsador con contacto conmutado"),
    8004: ("Accionamientos", "pulsador_seta_na", "Pulsador seta NA", "Pulsador de seta de emergencia NA"),
    8005: ("Accionamientos", "pulsador_seta_nc", "Pulsador seta NC", "Pulsador de seta con enclavamiento / parada de emergencia NC"),
    8006: ("Accionamientos", "pulsador_seta_na_nc", "Pulsador seta NA-NC", "Pulsador de seta de emergencia NA + NC"),
    8007: ("Accionamientos", "pulsador_seta_con", "Pulsador seta CON", "Pulsador de seta con contacto conmutado"),
    8008: ("Accionamientos", "interruptor_na", "Interruptor NA", "Interruptor mantenido NA"),
    8009: ("Accionamientos", "interruptor_nc", "Interruptor NC", "Interruptor mantenido NC"),
    8010: ("Accionamientos", "interruptor_na_nc", "Interruptor NA-NC", "Interruptor mantenido NA + NC"),
    8011: ("Accionamientos", "interruptor_con", "Interruptor CON", "Interruptor mantenido conmutado"),
    8012: ("Accionamientos", "final_carrera_na", "Final de carrera NA", "Interruptor de posición / fin de carrera mecánico NA"),
    8013: ("Accionamientos", "final_carrera_nc", "Final de carrera NC", "Interruptor de posición / fin de carrera mecánico NC"),
    8014: ("Accionamientos", "final_carrera_na_nc", "Final de carrera NA-NC", "Final de carrera con contacto NA + NC"),
    8015: ("Accionamientos", "final_carrera_com", "Final de carrera COM", "Final de carrera con contacto conmutado"),
    8016: ("Accionamientos", "contacto_termico_na", "Térmico NA", "Contacto auxiliar de relé térmico NA (97-98 señalización)"),
    8017: ("Accionamientos", "contacto_termico_nc", "Térmico NC", "Contacto auxiliar de relé térmico NC (95-96 disparo/paro)"),
    8018: ("Accionamientos", "contacto_termico_na_nc", "Térmico NA-NC", "Contactos auxiliares térmicos NA + NC (95-96 y 97-98)"),
    8019: ("Accionamientos", "contacto_termico_con", "Térmico CON", "Contacto auxiliar térmico conmutado (95-96-98)"),
    8020: ("Accionamientos", "conmutador_1_0_2", "Conmutador I-0-II", "Selector rotativo con posición cero central (1 - 0 - 2)"),
    8021: ("Accionamientos", "conmutador_1_2_3", "Conmutador I-II-III", "Selector rotativo de 3 posiciones"),
    8022: ("Accionamientos", "conmutador_cruce", "Conmutador cruce", "Conmutador de cruzamiento eléctrico"),
    8023: ("Accionamientos", "boton_pulsador", "Botón pulsador", "Pulsador electromecánico empotrado"),

    # 8100 - 8103: Elementos 2D/3D (TB 301, 307)
    8100: ("2D_3D", "pulsador_2d_3d", "Pulsador", "Pulsador de cuadro eléctrico en vista 2D/3D"),
    8101: ("2D_3D", "piloto_2d_3d", "Piloto", "Piloto de señalización luminoso en vista 2D/3D"),
    8102: ("2D_3D", "diodo_led_2d_3d", "Diodo LED", "Diodo LED indicador en vista 2D/3D"),
    8103: ("2D_3D", "borna_2d_3d", "Borna", "Borna de paso / conexión en vista 2D/3D"),

    # 9000 - 9045: Bobinas, temporizadores, señalizaciones y control (TB 193, 213)
    9000: ("Bobinas", "bobina_contactor", "Bobina", "Bobina monoestable estándar para contactor o relé (A1-A2)"),
    9001: ("Bobinas", "bobina_biestable", "Bobina biestable", "Bobina de relé biestable con doble devanado (Set/Reset)"),
    9002: ("Bobinas", "telerruptor", "Telerruptor", "Relé de impulsos telerruptor"),
    9003: ("Bobinas", "bobina_electrovalvula", "Bobina electroválvula", "Solenoide de electroválvula hidráulica o neumática"),
    9004: ("Bobinas", "temp_conexion_bobina", "Temp. conexión", "Bobina de relé temporizado a la conexión (ON Delay A1-A2)"),
    9005: ("Bobinas", "temp_desconexion_bobina", "Temp. desconexión", "Bobina de relé temporizado a la desconexión (OFF Delay A1-A2)"),
    9006: ("Bobinas", "temp_on_off_bobina", "Temp. conexión desconexión", "Bobina temporizada conexión-desconexión"),
    9007: ("Bobinas", "rele_intermitente", "Relé intermitente", "Relé intermitente de destellos cíclicos"),
    9008: ("Senalizacion", "piloto_senializacion", "Piloto señalización", "Lámpara piloto de señalización luminosa continua"),
    9009: ("Senalizacion", "piloto_intermitente", "Piloto intermitente", "Lámpara piloto con destello intermitente"),
    9010: ("Senalizacion", "timbre", "Timbre", "Avisador acústico timbre electromecánico"),
    9011: ("Senalizacion", "zumbador", "Zumbador", "Zumbador piezoeléctrico / buzzer acústico"),
    9012: ("Senalizacion", "sirena", "Sirena", "Sirena acústica de alarma"),
    9013: ("Senalizacion", "bocina", "Bocina", "Bocina o claxon acústico industrial"),
    9014: ("Bobinas", "interruptor_horario", "Interruptor horario", "Reloj programador horario diario/semanal"),
    9015: ("Bobinas", "generador_pulsos", "Generador de pulsos", "Generador de tren de pulsos periódicos"),
    9016: ("Bobinas", "contador_pulsos_bobina", "Contador de pulsos", "Bobina de avance de contador electromecánico"),
    9040: ("Potencia", "control_arrancador_suave", "Control arrancador electrónico c.a.", "Módulo de control para arrancador suave"),
    9041: ("Potencia", "control_inversor_electronico", "Control inversor electrónico c.a.", "Módulo de control de inversión electrónica"),
    9042: ("Potencia", "control_variador_ca", "Control Variador velocidad c.a.", "Módulo de maniobra de variador de frecuencia CA"),
    9043: ("Potencia", "control_variador_cc", "Control Variador velocidad c.c.", "Módulo de maniobra de regulador de velocidad CC"),
    9044: ("Potencia", "variador_potencia_ca_2p", "Variador velocidad c.a. II", "Etapa de potencia de variador CA monofásico"),
    9045: ("Potencia", "variador_potencia_ca_3p", "Variador velocidad c.a. III", "Etapa de potencia de variador CA trifásico"),

    # 10000 - 10083: Lógica digital (TB 226) & Ladder (TB 292)
    10000: ("Logica", "puerta_and", "AND", "Puerta lógica AND de 2 o más entradas"),
    10010: ("Logica", "puerta_or", "OR", "Puerta lógica OR de 2 o más entradas"),
    10020: ("Logica", "puerta_exor", "EXOR", "Puerta lógica XOR (Or exclusiva)"),
    10030: ("Logica", "puerta_nand", "NAND", "Puerta lógica NAND"),
    10040: ("Logica", "puerta_inv", "INV", "Puerta lógica inversora NOT"),
    10041: ("Logica", "puerta_buffer", "INV / Buffer", "Puerta lógica Buffer / inversora alternativa"),
    10050: ("Ladder", "ladder_contacto_na", "NA", "Contacto normalmente abierto en lenguaje Ladder (LD)"),
    10051: ("Ladder", "ladder_contacto_nc", "NC", "Contacto normalmente cerrado en lenguaje Ladder (LD)"),
    10052: ("Ladder", "ladder_flanco_ascendente", "Flanco ascendente", "Detector de flanco ascendente P_TRIG en Ladder"),
    10053: ("Ladder", "ladder_flanco_descendente", "Flanco descendente", "Detector de flanco descendente N_TRIG en Ladder"),
    10060: ("Ladder", "ladder_bobina_asignar", "Asignar", "Bobina de salida normal en Ladder ( )"),
    10061: ("Ladder", "ladder_bobina_set", "Set", "Bobina de activación enclavada (S) Set en Ladder"),
    10062: ("Ladder", "ladder_bobina_reset", "Reset", "Bobina de desactivación (R) Reset en Ladder"),
    10063: ("Logica", "generador_pulsos_logico", "Generatore di impulsi", "Generador de reloj de pulsos lógicos (Clock)"),
    10064: ("Logica", "puerta_nor", "NOR", "Puerta lógica NOR"),
    10065: ("Logica", "biestable_rs", "Biestable", "Biestable / Flip-Flop RS digital"),
    10066: ("Logica", "divisor_binario", "Divisor Binario", "Divisor de frecuencia binario digital (T-Flip Flop)"),
    10067: ("Logica", "temporizador_pulso_digital", "Temporizador pulso conexión", "Temporizador monostable de pulso digital"),
    10068: ("Logica", "temporizador_desconexion_digital", "Temporizador desconexión", "Temporizador digital a la desconexión (TOF)"),
    10069: ("Logica", "temporizador_intermitente_digital", "Temporizador intermitente", "Temporizador oscilador intermitente digital"),
    10070: ("Logica", "prueba_entrada_logica", "Prueba", "Sonda / interruptor de inyección de nivel lógico (0/1)"),
    10071: ("Logica", "visualiza_salida_logica", "Visualiza", "Sonda indicadora de estado lógico (LED digital)"),
    10072: ("Logica", "display_bcd", "Display BCD", "Display numérico digital decodificador BCD"),
    10073: ("Logica", "display_7_seg", "Display 7 Seg.", "Display visualizador de 7 segmentos"),
    10074: ("Logica", "preselector_digital", "Preselector", "Rueda preselectora BCD digital manual"),
    10075: ("Logica", "contador_digital", "Contador", "Contador digital de impulsos"),
    10076: ("Ladder", "ladder_first_scan", "First Scan", "Contacto especial de primer ciclo de scan en Ladder"),
    10077: ("Logica", "contador_asc_desc", "Contador ascendente-descendente", "Contador bidireccional digital (Up/Down)"),
    10078: ("Logica", "contador_4_bits", "Contador 4 bits", "Contador binario síncrono de 4 bits"),
    10080: ("Logica", "decodificador_7_seg", "Decodificador 7 segmentos", "Decodificador integrado BCD a 7 segmentos"),
    10081: ("Logica", "temporizador_conexion_digital", "Temporizador conexión", "Temporizador digital a la conexión (TON)"),
    10082: ("Logica", "contador_4_bits_decadas", "Contador 4 bits decadas", "Contador de décadas módulo 10"),
    10083: ("Logica", "contador_4_bits_asc_des", "Contador 4 bits ASC/DES", "Contador de 4 bits Up/Down configurable"),

    # 10100 - 10112: GRAFCET (TB 228)
    10100: ("GRAFCET", "grafcet_etapa_inicial", "Etapa inicial", "Etapa inicial doble cuadrado GRAFCET"),
    10101: ("GRAFCET", "grafcet_etapa", "Etapa", "Etapa simple numerada GRAFCET"),
    10102: ("GRAFCET", "grafcet_transicion", "Transición", "Barrera de transición con receptividad asociada"),
    10103: ("GRAFCET", "grafcet_accion", "Acción", "Bloque de acción asociada a etapa"),
    10104: ("GRAFCET", "grafcet_divergencia_o", "Divergencia en \"O\"", "Divergencia alternativa en OR"),
    10105: ("GRAFCET", "grafcet_convergencia_o", "Convergencia en \"O\"", "Convergencia alternativa en OR"),
    10106: ("GRAFCET", "grafcet_enlace_cero", "\"0\"", "Línea de enlace y sincronismo GRAFCET"),
    10107: ("GRAFCET", "grafcet_divergencia_y", "Divergencia en \"Y\"", "Divergencia simultánea en AND (doble barra)"),
    10108: ("GRAFCET", "grafcet_convergencia_y", "Convergencia en \"Y\"", "Convergencia simultánea en AND (doble barra)"),
    10111: ("GRAFCET", "grafcet_enlace_io", "Enlace de entrada / salida", "Enlace de salto entre etapas o páginas"),
    10112: ("GRAFCET", "grafcet_macro_etapa", "Macro etapa", "Macroetapa jerárquica encapsulada"),

    # 10200 - 10220: PLCs y autómatas (TB 242)
    10200: ("PLC", "intercambio_entradas_pc_simu", "Intercambio entradas PC_SIMU", "Tabla de comunicación de entradas para PC_SIMU"),
    10201: ("PLC", "intercambio_salidas_pc_simu", "Intercambio salidas PC_SIMU", "Tabla de comunicación de salidas para PC_SIMU"),
    10202: ("PLC", "modulo_logico_logo", "Módulo lógico", "Relé programable Siemens LOGO! (230RC / 24RC)"),
    10203: ("PLC", "plc_s7_1200", "PLC S7-1200", "Autómata programable Siemens SIMATIC S7-1200 (CPU 1214C)"),
    10204: ("PLC", "entrada_digital_plc", "Entrada digital PLC", "Borne de entrada digital individual PLC (%I0.x)"),
    10205: ("PLC", "salida_digital_plc", "Salida digital PLC", "Borne de salida digital individual PLC (%Q0.x)"),
    10206: ("PLC", "cpu_plc", "CPU PLC", "CPU genérica de autómata programable"),
    10207: ("PLC", "alimentacion_io_plc_pos", "Alimentación I/O digital PLC", "Borne de alimentación positiva para E/S PLC (1L / +24V)"),
    10208: ("PLC", "alimentacion_io_plc_neg", "Alimentación I/O digital PLC", "Borne de alimentación común / masa para E/S PLC (1M / 0V)"),
    10209: ("PLC", "plc_s7_1500", "PLC CPU S7-1500", "Autómata modular Siemens SIMATIC S7-1500"),
    10210: ("PLC", "modulo_s7_1500_dido", "S7-1500 DI/DO", "Módulo de entradas y salidas digitales S7-1500"),
    10212: ("PLC", "et_200", "ET-200", "Módulo cabecera de periferia distribuida Siemens ET-200"),
    10213: ("PLC", "et_200_8di", "ET-200 8DI", "Módulo de 8 entradas digitales para ET-200"),
    10214: ("PLC", "logo_4di_4do", "LOGO 4DI/4DO", "Módulo de expansión para Siemens LOGO! 4DI / 4DO"),
    10215: ("PLC", "s7_1200_8di_8do", "S7-1200 8DI/8DO", "Módulo de ampliación Siemens SM 1223 (8DI / 8DO)"),
    10220: ("PLC", "arduino_uno", "Arduino uno", "Placa microcontroladora Arduino UNO"),

    # 10500 - 10509: Maquetas y actuadores virtuales (TB 269 / 301 / Entorno virtual)
    10500: ("Virtual_2D", "actuador_lineal_v1", "Actuador lineal virtual", "Actuador o cilindro lineal en simulación virtual"),
    10501: ("Virtual_2D", "actuador_lineal_v2", "Actuador lineal virtual", "Actuador lineal con finales de carrera a0/a1"),
    10502: ("Virtual_2D", "actuador_lineal_v3", "Actuador lineal virtual", "Actuador lineal de doble vástago virtual"),
    10503: ("Virtual_2D", "actuador_lineal_v4", "Actuador lineal virtual", "Cilindro neumático simulado virtual"),
    10504: ("Virtual_2D", "cinta_transportadora_v1", "Cinta transportadora virtual", "Cinta de transporte con motor reversible"),
    10505: ("Virtual_2D", "cinta_transportadora_v2", "Cinta transportadora virtual", "Cinta de transporte con sensores de presencia"),
    10507: ("Virtual_2D", "valvula_cilindro_virtual", "Válvula virtual", "Válvula de control para maqueta virtual"),
    10508: ("Virtual_2D", "motor_virtual_1", "Motor maqueta virtual", "Motor de accionamiento maqueta"),
    10509: ("Virtual_2D", "motor_virtual_2", "Motor maqueta virtual", "Motor con encoder para simulación"),

    # 20000: Marco / Cajetín
    20000: ("Formato", "cajetin_rotulacion", "Cajetín", "Formato de lámina y cuadro de rotulación de plano normalizado"),
}

def main():
    print("Iniciando generación de catálogo completo...")
    string_entries, toolbars = load_pe_strings_and_toolbars()
    cad_stats = get_cad_stats()

    all_tids = sorted(cad_stats.keys())
    print(f"Total de type_ids encontrados en ejemplos: {len(all_tids)}")

    catalog = []
    for tid in all_tids:
        info = cad_stats[tid]
        top_tags = [t for t, c in info['tags'].most_common(5)]
        tags_str = ",".join(top_tags)
        
        # terminales
        terms_list = []
        for term_tuple in sorted(info['terminals'], key=lambda x: len(x), reverse=True):
            terms_list.append("-".join(term_tuple))
        term_str = "; ".join(terms_list[:3])

        if tid in KNOWN_METADATA:
            cat, subtype, nombre_orig, desc = KNOWN_METADATA[tid]
        elif 1 <= tid < 1000:
            cat = "Virtual_2D"
            subtype = f"objeto_virtual_{tid}"
            nombre_orig = f"Componente Virtual / Bitmap {tid}"
            desc = f"Elemento gráfico / interactivo de laboratorio virtual (bitmap_{tid})"
        else:
            cat = "Desconocido"
            subtype = f"simbolo_{tid}"
            nombre_orig = f"Símbolo {tid}"
            desc = f"Símbolo técnico código {tid}"

        catalog.append({
            'CAD_ID': tid,
            'Categoria': cat,
            'Subtipo': subtype,
            'Nombre_Original_EXE': nombre_orig,
            'Descripcion': desc,
            'Tags': tags_str,
            'Terminales': term_str,
            'Veces_Usado': info['count'],
            'Archivos_Usado': len(info['files']),
            'Archivos_Lista': sorted(list(info['files']))
        })

    out_dir = BASE / 'data' / 'catalogs'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Guardar en cadesimu_symbols_complete.json
    with open(out_dir / 'cadesimu_symbols_complete.json', 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Guardado: {out_dir / 'cadesimu_symbols_complete.json'}")

    # Guardar en cadesimu_symbol_catalog_detailed.json
    with open(out_dir / 'cadesimu_symbol_catalog_detailed.json', 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Guardado: {out_dir / 'cadesimu_symbol_catalog_detailed.json'}")

    # Guardar en cadesimu_symbols_complete.csv
    with open(out_dir / 'cadesimu_symbols_complete.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['CAD_ID', 'Categoria', 'Subtipo', 'Nombre_Original_EXE', 'Descripcion', 'Tags', 'Terminales', 'Veces_Usado', 'Archivos_Usado'])
        for item in catalog:
            writer.writerow([
                item['CAD_ID'],
                item['Categoria'],
                item['Subtipo'],
                item['Nombre_Original_EXE'],
                item['Descripcion'],
                item['Tags'],
                item['Terminales'],
                item['Veces_Usado'],
                item['Archivos_Usado']
            ])
    print(f"Guardado: {out_dir / 'cadesimu_symbols_complete.csv'}")

    # Guardar tabla en Markdown
    with open('TABLA_SIMBOLOS_CADESIMU.md', 'w', encoding='utf-8') as f:
        f.write("# Catálogo Maestro de Símbolos y Keycodes CADe SIMU\n\n")
        f.write("Extracción exhaustiva realizada mediante ingeniería inversa vía **REA** (Resource Extraction & Binary Analysis) sobre el ejecutable original `CADe_SIMU_V4.2.exe` y análisis de los 18 esquemas `.cad` de ejemplo (incluyendo `all_simbol.cad`, `allpart2.cad`, `all4.cad`, `all5.cad`, `2D.cad`, `3D.cad` y laboratorios virtuales).\n\n")
        f.write(f"- **Total de Keycodes / Type IDs únicos detectados**: {len(catalog)}\n")
        f.write("- **Familias cubiertas**: Alimentaciones, Motores, Contactores, Protecciones, Contactos Auxiliares y Temporizados, Accionamientos, Detectores, Bobinas y Señalización, Lógica Digital, Ladder, GRAFCET, PLCs (LOGO!, S7-1200, S7-1500, ET-200, Arduino), Actuadores Neumáticos, Cables, 2D/3D y Maquetas Virtuales.\n\n")
        
        # Agrupar por categoría
        cats = defaultdict(list)
        for item in catalog:
            cats[item['Categoria']].append(item)

        order_cats = [
            "Alimentaciones", "Motores", "Contactores", "Protecciones",
            "Contactos", "Accionamientos", "Detectores", "Bobinas",
            "Senalizacion", "Potencia", "Logica", "Ladder",
            "GRAFCET", "PLC", "Neumatica", "Cables", "Conexiones",
            "2D_3D", "Formato", "Virtual_2D", "Desconocido"
        ]

        for cat_name in order_cats:
            items = cats.get(cat_name, [])
            if not items:
                continue
            f.write(f"## {cat_name} ({len(items)} componentes)\n\n")
            f.write("| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for it in items:
                f.write(f"| `{it['CAD_ID']}` | **{it['Nombre_Original_EXE']}** | `{it['Subtipo']}` | `{it['Tags'] or '-'}` | `{it['Terminales'] or '-'}` | {it['Veces_Usado']} veces ({it['Archivos_Usado']} files) | {it['Descripcion']} |\n")
            f.write("\n")

    print("Guardado: TABLA_SIMBOLOS_CADESIMU.md")

if __name__ == '__main__':
    main()
