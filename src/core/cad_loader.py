"""
Cargador de esquemas de CADe SIMU (.cad) para SimuCraft
Convierte esquemas clásicos de CADe SIMU en grafos relacionales y gráficos interactivos
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from PySide6.QtCore import QPointF

from ..components.standard_components import create_standard_component, STANDARD_COMPONENTS
from ..graphics.component_item import ComponentItem
from ..graphics.terminal_item import TerminalItem
from ..graphics.wire_item import WireItem
from .graph import Node, Edge, NodeType
try:
    from ..qet import QETLoader
    _qet_loader = QETLoader()
    _qet_loader.add_directory(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'qet_symbols'))
    _qet_loader.add_directory('/home/vibecode/DevS/qelectrotech-elements/elements')
except Exception:
    _qet_loader = None


def parse_cad_raw(filepath: str) -> Dict[str, Any]:
    """Parseador robusto de archivos .cad"""
    with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
        data = f.read()
    
    parts = data.split('*')
    result = {
        'filename': os.path.basename(filepath),
        'symbols': [],
        'wires': []
    }
    
    i = 3
    while i < len(parts):
        p = parts[i]
        if not p or not p.strip():
            i += 1
            continue
            
        if '#' in p and p[0].isdigit():
            comp_type_id = p.split('#')[0]
            try:
                tid = int(comp_type_id)
            except ValueError:
                tid = -1
                
            comp = {
                'type_id': comp_type_id,
                'tid': tid,
                'raw_prefix': p,
                'params': []
            }
            j = i + 1
            while j < len(parts):
                np = parts[j]
                if not np or not np.strip():
                    j += 1
                    continue
                if '#' in np and np[0].isdigit():
                    break
                s = np.strip()
                try:
                    if s.lstrip('-').isdigit():
                        comp['params'].append(int(s))
                    else:
                        comp['params'].append(s)
                except Exception:
                    comp['params'].append(s)
                j += 1
                
            if tid in {4000, 4001, 4009, 4010, 4018, 4019, 4020} or (4000 <= tid <= 4025):
                result['wires'].append(comp)
            elif tid > 0:  # Todo ID positivo que no sea cable es un símbolo
                result['symbols'].append(comp)
            i = j
            continue
        i += 1
        
    return result


class CADLoader:
    """Carga esquemas .cad y los inserta en CircuitScene con bornes perfectamente alineados y conectados"""

    SCALE = 6.0  # Factor de escala exacto: 1 cuadrícula CAD = 6 píxeles

    # Dispatch table dinámica (cargada desde data/mappings/cad_id_to_component.json)
    # Se usa como FALLBACK cuando el ID no tiene mapeo hardcodeado en _create_component_for_symbol
    _dispatch_table: Dict[str, Dict] = {}
    _dispatch_loaded: bool = False

    @classmethod
    def _ensure_dispatch_table(cls):
        """Carga la dispatch table desde disco (una única vez)."""
        if cls._dispatch_loaded:
            return
        cls._dispatch_loaded = True
        # Buscar el archivo relativo a este módulo
        base = Path(__file__).resolve().parent.parent.parent
        dispatch_path = base / 'data' / 'mappings' / 'cad_id_to_component.json'
        if dispatch_path.exists():
            try:
                with open(dispatch_path, 'r', encoding='utf-8') as f:
                    cls._dispatch_table = json.load(f)
            except Exception:
                cls._dispatch_table = {}

    @classmethod
    def load_file(cls, filepath: str, scene) -> Dict[str, Any]:
        """Cargar un archivo .cad en la escena gráfica"""
        cls._ensure_dispatch_table()
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
            
        cad_data = parse_cad_raw(filepath)
        scene.clear_circuit()
        
        created_components = []
        created_wires = []
        
        # 1. Crear componentes de los símbolos eléctricos
        for sym in cad_data['symbols']:
            tid = sym['tid']
            parts = sym['raw_prefix'].split('#')
            tag = parts[1] if len(parts) > 1 and parts[1] else f"K{tid}"
            
            p = sym['params']
            gx = p[8] if len(p) > 8 and isinstance(p[8], (int, float)) else 0
            gy = p[9] if len(p) > 9 and isinstance(p[9], (int, float)) else 0
            
            pos_x = float(gx) * cls.SCALE
            pos_y = float(gy) * cls.SCALE
            
            comp_item = cls._create_component_for_symbol(tid, tag, parts)
            if comp_item:
                comp_item.setPos(pos_x, pos_y)
                scene.add_component(comp_item)
                created_components.append(comp_item)
                
        # 2. Filtrar cables válidos y extraer puntos de unión
        raw_wires = []
        all_junction_points: Set[Tuple[float, float]] = set()
        
        for w in cad_data['wires']:
            tid = w.get('tid', 4000)
            p = w['params']
            if len(p) >= 12:
                try:
                    x1 = float(p[8]) * cls.SCALE
                    y1 = float(p[9]) * cls.SCALE
                    x2 = float(p[10]) * cls.SCALE
                    y2 = float(p[11]) * cls.SCALE
                except (ValueError, TypeError):
                    continue
                    
                # Ignorar cables vacíos en (0, 0)
                if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
                    continue
                    
                all_junction_points.add((x1, y1))
                all_junction_points.add((x2, y2))
                
                if x1 != x2 or y1 != y2:
                    raw_wires.append((x1, y1, x2, y2, tid))
                    
        # 3. Detectar puntos de alimentación en el extremo superior de cables
        DEFAULT_L = (216.0, 288.0)
        DEFAULT_N = (252.0, 288.0)
        if all_junction_points:
            min_y = min(p[1] for p in all_junction_points)
            top_points = sorted(
                [pt for pt in all_junction_points if pt[1] == min_y],
                key=lambda p: p[0]
            )
        else:
            top_points = []

        feed_l_pt = top_points[0] if len(top_points) > 0 else DEFAULT_L
        feed_n_pt = top_points[1] if len(top_points) > 1 else (feed_l_pt[0] + 36.0, feed_l_pt[1])

        
        power_l_def = create_standard_component("power_l", "L1")
        power_l = ComponentItem(power_l_def)
        power_l.setPos(feed_l_pt[0], feed_l_pt[1])
        scene.add_component(power_l)
        created_components.append(power_l)
        
        power_n_def = create_standard_component("power_n", "N")
        power_n = ComponentItem(power_n_def)
        power_n.setPos(feed_n_pt[0], feed_n_pt[1])
        scene.add_component(power_n)
        created_components.append(power_n)
        
        # Mapear bornes por posición en escena
        terminals_by_pos = []
        for comp in created_components:
            for term in comp.terminals:
                term_pos = term.get_scene_pos()
                terminals_by_pos.append((term_pos, term))
                all_junction_points.add((round(term_pos.x(), 1), round(term_pos.y(), 1)))

        # 4. Crear cables subdividiendo en conexiones T intermedias conservando su tipo
        for x1, y1, x2, y2, tid in raw_wires:
            segments = cls._split_wire_at_junctions(x1, y1, x2, y2, all_junction_points)
            for sx1, sy1, sx2, sy2 in segments:
                pt1 = QPointF(sx1, sy1)
                pt2 = QPointF(sx2, sy2)
                
                t1 = cls._find_closest_terminal(pt1, terminals_by_pos, tolerance=8.0)
                t2 = cls._find_closest_terminal(pt2, terminals_by_pos, tolerance=8.0)
                
                wire_item = scene.create_wire_between_points(pt1, pt2, t1, t2, wire_type=tid)
                if wire_item:
                    created_wires.append(wire_item)
                    
        return {
            'filename': os.path.basename(filepath),
            'components_count': len(created_components),
            'wires_count': len(created_wires),
            'symbols_raw': len(cad_data['symbols'])
        }

    @classmethod
    def _split_wire_at_junctions(cls, x1: float, y1: float, x2: float, y2: float, points: Set[Tuple[float, float]]) -> List[Tuple[float, float, float, float]]:
        """Subdivide un tramo de cable si tiene empalmes intermedios en T"""
        intermediates = []
        if abs(x1 - x2) < 0.1:  # Cable vertical
            ymin, ymax = min(y1, y2), max(y1, y2)
            for px, py in points:
                if abs(px - x1) < 0.5 and ymin + 0.5 < py < ymax - 0.5:
                    intermediates.append((x1, py))
            intermediates.sort(key=lambda pt: pt[1], reverse=(y1 > y2))
        elif abs(y1 - y2) < 0.1:  # Cable horizontal
            xmin, xmax = min(x1, x2), max(x1, x2)
            for px, py in points:
                if abs(py - y1) < 0.5 and xmin + 0.5 < px < xmax - 0.5:
                    intermediates.append((px, y1))
            intermediates.sort(key=lambda pt: pt[0], reverse=(x1 > x2))
            
        all_pts = [(x1, y1)] + intermediates + [(x2, y2)]
        segs = []
        for i in range(len(all_pts) - 1):
            segs.append((all_pts[i][0], all_pts[i][1], all_pts[i+1][0], all_pts[i+1][1]))
        return segs

    @classmethod
    def _create_component_for_symbol(cls, tid: int, tag: str, raw_parts: list) -> Optional[ComponentItem]:
        """Mapear ID de símbolo CADe SIMU a componente SimuCraft.

        Tabla completa extraída con REA sobre CADe_SIMU_V4.2.exe y validada
        cruzadamente con los 18 esquemas de ejemplo (incluyendo all_simbol.cad,
        allpart2.cad, all4.cad, all5.cad).

        Correcciones clave (MAPEADO_FINAL.md):
          - 9000  → Bobina contactor/relé       (A1-A2), NO contacto
          - 7000  → Contacto aux NA             (13-14), NO borne
          - 9008  → Piloto señalización         (X1-X2), NO contacto aux
          - 6007  → Relé Térmico (bimetales)    (1-3-5/2-4-6), NO bobina
          - 6009  → Disyuntor IN (1P+N)
          - 6011  → Disyuntor III (3P guardamotor)
          - 2001  → Contactor III potencia      (1-3-5/2-4-6)
          - 1000  → Motor trifásico             (U1-V1-W1-PE)
          - 8000  → Pulsador NA marcha          (13-14)
          - 8001  → Pulsador NC paro            (11-12)
        """

        # ── ACCIONAMIENTOS (8000-8023) ────────────────────────────────────────
        if tid == 8000:                        # Pulsador NA (Marcha)
            defn = create_standard_component("pushbutton_no", tag)
        elif tid == 8001:                      # Pulsador NC (Paro)
            defn = create_standard_component("pushbutton_nc", tag)
        elif tid == 8002:                      # Pulsador NA-NC
            defn = create_standard_component("pushbutton_no_nc", tag)
        elif tid == 8003:                      # Pulsador CON (conmutador)
            defn = create_standard_component("pushbutton_no", tag)
            defn['name'] = f"Pulsador CON {tag}"
        elif tid == 8004:                      # Pulsador seta NA
            defn = create_standard_component("pushbutton_mushroom_na", tag)
        elif tid == 8005:                      # Pulsador seta NC
            defn = create_standard_component("pushbutton_mushroom_nc", tag)
        elif tid == 8006:                      # Pulsador seta NA-NC
            defn = create_standard_component("pushbutton_mushroom_na", tag)
            defn['name'] = f"Seta NA-NC {tag}"
        elif tid == 8007:                      # Pulsador seta CON
            defn = create_standard_component("pushbutton_mushroom_nc", tag)
            defn['name'] = f"Seta CON {tag}"
        elif tid in {8008, 8011}:             # Interruptor NA / CON
            defn = create_standard_component("selector_switch", tag)
        elif tid in {8009}:                    # Interruptor NC
            defn = create_standard_component("selector_switch", tag)
            defn['name'] = f"Interruptor NC {tag}"
        elif tid == 8010:                      # Interruptor NA-NC
            defn = create_standard_component("selector_switch", tag)
            defn['name'] = f"Interruptor NA-NC {tag}"
        elif tid == 8012:                      # Final de carrera NA
            defn = create_standard_component("limit_switch_no", tag)
        elif tid == 8013:                      # Final de carrera NC
            defn = create_standard_component("limit_switch_nc", tag)
        elif tid in {8014, 8015}:             # Final de carrera NA-NC / COM
            defn = create_standard_component("limit_switch_no", tag)
            defn['name'] = f"Final carrera NA-NC {tag}"
        elif tid == 8016:                      # Térmico NA (97-98, señalización)
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Térmico NA {tag}"
        elif tid == 8017:                      # Térmico NC (95-96, corte)
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Térmico NC {tag}"
        elif tid in {8018, 8019}:             # Térmico NA-NC / CON
            defn = create_standard_component("contactor_contact_no_nc", tag)
            defn['name'] = f"Térmico NA-NC {tag}"
        elif tid in {8020, 8021, 8022}:       # Conmutadores I-0-II, I-II-III, cruce
            defn = create_standard_component("selector_switch", tag)
        elif tid == 8023:                      # Botón pulsador (genérico)
            defn = create_standard_component("pushbutton_no", tag)

        # ── BOBINAS (9000-9016) ───────────────────────────────────────────────
        elif tid == 9000:                      # Bobina contactor/relé (A1-A2)
            defn = create_standard_component("contactor_coil", tag)
        elif tid == 9001:                      # Bobina biestable (set)
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Bobina SET {tag}"
        elif tid == 9002:                      # Telerruptor
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Telerruptor {tag}"
        elif tid == 9003:                      # Bobina electroválvula
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Electroválvula {tag}"
        elif tid == 9004:                      # Temporizado conexión (on-delay)
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Temp.Cnx {tag}"
        elif tid == 9005:                      # Temporizado desconexión (off-delay)
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Temp.Des {tag}"
        elif tid == 9006:                      # Temporizado cnx/des
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Temp.C/D {tag}"
        elif tid == 9007:                      # Relé intermitente
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Intermitente {tag}"

        # ── SEÑALIZACIÓN (9008-9013) ──────────────────────────────────────────
        elif tid == 9008:                      # Piloto de señalización (X1-X2)
            defn = create_standard_component("pilot_lamp", tag)
        elif tid == 9009:                      # Piloto intermitente
            defn = create_standard_component("pilot_lamp_amber", tag)
        elif tid == 9010:                      # Timbre
            defn = create_standard_component("pilot_lamp", tag)
            defn['name'] = f"Timbre {tag}"
        elif tid == 9011:                      # Zumbador
            defn = create_standard_component("pilot_lamp", tag)
            defn['name'] = f"Zumbador {tag}"
        elif tid in {9012, 9013}:             # Sirena / Bocina
            defn = create_standard_component("pilot_lamp_red", tag)
            defn['name'] = f"Alarma {tag}"
        elif tid in {9014, 9015, 9016}:       # Horario / Pulsos / Contador
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Contador {tag} (CAD {tid})"

        # ── CONTACTOS AUXILIARES (7000-7015) ─────────────────────────────────
        elif tid == 7000:                      # Contacto NA (13-14)
            defn = create_standard_component("contactor_contact_no", tag)
        elif tid == 7001:                      # Contacto NC (11-12)
            defn = create_standard_component("contactor_contact_nc", tag)
        elif tid in {7002, 7003}:             # Contacto NA+NC / CON
            defn = create_standard_component("contactor_contact_no_nc", tag)
        elif tid == 7004:                      # Con.Temporizado Cnx NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Temp.Cnx NA {tag}"
        elif tid == 7005:                      # Con.Temporizado Cnx NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Temp.Cnx NC {tag}"
        elif tid in {7006, 7007}:             # Con.Temp Cnx NA+NC / CON
            defn = create_standard_component("contactor_contact_no_nc", tag)
            defn['name'] = f"Temp.Cnx NA-NC {tag}"
        elif tid == 7008:                      # Con.Temporizado Des NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Temp.Des NA {tag}"
        elif tid == 7009:                      # Con.Temporizado Des NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Temp.Des NC {tag}"
        elif tid in {7010, 7011}:             # Con.Temp Des NA+NC / CON
            defn = create_standard_component("contactor_contact_no_nc", tag)
            defn['name'] = f"Temp.Des NA-NC {tag}"
        elif tid == 7013:                      # Con.Temp CnxDes NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Temp.C/D NA {tag}"
        elif tid == 7014:                      # Con.Temp CnxDes NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Temp.C/D NC {tag}"
        elif tid == 7015:                      # Con.Temp CnxDes NA+NC
            defn = create_standard_component("contactor_contact_no_nc", tag)
            defn['name'] = f"Temp.C/D NA-NC {tag}"

        # ── DETECTORES (7500-7600) ────────────────────────────────────────────
        elif tid in {7500, 7506, 7512}:       # Det. inductivo/capacitivo/magnético NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Detector NA {tag} (CAD {tid})"
        elif tid in {7520, 7526, 7532}:       # Det. inductivo/capacitivo/magnético NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Detector NC {tag} (CAD {tid})"
        elif tid in {7550, 7551, 7553, 7559}: # Barrera fotoeléctrica
            defn = create_standard_component("limit_switch_no", tag)
            defn['name'] = f"Barrera {tag} (CAD {tid})"
        elif tid in {7570, 7576}:             # Presostato/Vacuostato NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Presostato NA {tag}"
        elif tid in {7582, 7588}:             # Presostato/Vacuostato NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Presostato NC {tag}"
        elif tid in {7594}:                   # Termostato NA
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Termostato NA {tag}"
        elif tid in {7600}:                   # Termostato NC
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Termostato NC {tag}"

        # ── CONTACTORES / INTERRUPTORES DE POTENCIA (2000-2009) ──────────────
        elif tid == 2000:                      # Contactor II (2P)
            defn = create_standard_component("contactor_2p", tag)
        elif tid == 2001:                      # Contactor III (3P) - el más común
            defn = create_standard_component("contactor_3p", tag)
        elif tid == 2002:                      # Contactor IIII (4P)
            defn = create_standard_component("contactor_4p", tag)
        elif tid == 2003:                      # Interruptor II
            defn = create_standard_component("contactor_2p", tag)
            defn['name'] = f"Interruptor II {tag}"
        elif tid == 2004:                      # Interruptor III
            defn = create_standard_component("contactor_3p", tag)
            defn['name'] = f"Interruptor III {tag}"
        elif tid == 2005:                      # Interruptor IIII
            defn = create_standard_component("contactor_4p", tag)
            defn['name'] = f"Interruptor IIII {tag}"
        elif tid == 2006:                      # Contactor I (1P)
            defn = create_standard_component("contactor_1p", tag)
        elif tid == 2007:                      # Interruptor I (1P)
            defn = create_standard_component("contactor_1p", tag)
            defn['name'] = f"Interruptor I {tag}"
        elif tid == 2008:                      # Contactor III conmutador
            defn = create_standard_component("contactor_3p", tag)
            defn['name'] = f"Contactor Inv {tag}"
        elif tid == 2009:                      # Enclavamiento mecánico
            defn = create_standard_component("contactor_contact_nc", tag)
            defn['name'] = f"Enclavamiento {tag}"

        # ── PROTECCIONES: FUSIBLES (5000-5009) ───────────────────────────────
        elif tid == 5000:                      # Fusible I (1P)
            defn = create_standard_component("breaker_1p", tag)
            defn['name'] = f"Fusible I {tag}"
        elif tid == 5001:                      # Fusible IN (1P+N)
            defn = create_standard_component("breaker_1p_n", tag)
            defn['name'] = f"Fusible IN {tag}"
        elif tid == 5002:                      # Fusible II (2P)
            defn = create_standard_component("breaker_2p", tag)
            defn['name'] = f"Fusible II {tag}"
        elif tid == 5003:                      # Fusible III (3P)
            defn = create_standard_component("breaker_3p", tag)
            defn['name'] = f"Fusible III {tag}"
        elif tid == 5004:                      # Fusible IIIN (3P+N)
            defn = create_standard_component("breaker_3p_n", tag)
            defn['name'] = f"Fusible IIIN {tag}"
        elif tid in {5005, 5006, 5007, 5008, 5009}:  # Fusibles seccionables
            _map = {5005: "breaker_1p", 5006: "breaker_1p_n", 5007: "breaker_2p",
                    5008: "breaker_3p", 5009: "breaker_3p_n"}
            defn = create_standard_component(_map.get(tid, "breaker_3p"), tag)
            defn['name'] = f"Sec.Fusible {tag} (CAD {tid})"

        # ── PROTECCIONES: AUTOMÁTICOS Y DIFERENCIALES (6000-6014) ────────────
        elif tid == 6000:                      # Automático I (PIA 1P)
            defn = create_standard_component("breaker_1p", tag)
        elif tid == 6001:                      # Automático IN (PIA 1P+N)
            defn = create_standard_component("breaker_1p_n", tag)
        elif tid == 6002:                      # Automático II (PIA 2P)
            defn = create_standard_component("breaker_2p", tag)
        elif tid == 6003:                      # Automático III (PIA 3P)
            defn = create_standard_component("breaker_3p", tag)
        elif tid == 6004:                      # Automático IIIN (PIA 3P+N)
            defn = create_standard_component("breaker_3p_n", tag)
        elif tid in {6005, 6006}:             # Diferencial IN / IIIN
            defn = create_standard_component("breaker_1p_n" if tid == 6005 else "breaker_3p_n", tag)
            defn['name'] = f"Diferencial {tag}"
        elif tid == 6007:                      # Relé Térmico (bimetales, 3P potencia)
            defn = create_standard_component("thermal_relay_3p", tag)
        elif tid == 6008:                      # Disyuntor I (1P guardamotor)
            defn = create_standard_component("breaker_1p", tag)
        elif tid == 6009:                      # Disyuntor IN (1P+N)
            defn = create_standard_component("breaker_1p_n", tag)
        elif tid == 6010:                      # Disyuntor II (2P)
            defn = create_standard_component("breaker_2p", tag)
        elif tid == 6011:                      # Disyuntor III (3P guardamotor - EL más frecuente)
            defn = create_standard_component("breaker_3p", tag)
        elif tid == 6012:                      # Disyuntor IIIN (3P+N)
            defn = create_standard_component("breaker_3p_n", tag)
        elif tid in {6013, 6014}:             # Limitador sobretensiones
            defn = create_standard_component("breaker_1p_n" if tid == 6013 else "breaker_3p_n", tag)
            defn['name'] = f"Limitador {tag}"

        # ── MOTORES (1000-1012, 10550) ────────────────────────────────────────
        elif tid == 1000:                      # Motor trifásico (U1-V1-W1-PE)
            defn = create_standard_component("motor_3p", tag)
        elif tid == 1001:                      # Motor trifásico YD (6 bornes)
            defn = create_standard_component("motor_3p_n", tag)
            defn['name'] = f"Motor YD {tag}"
        elif tid == 1002:                      # Motor monofásico
            defn = create_standard_component("motor_1p", tag)
        elif tid == 1003:                      # Motor Dahlander (2 velocidades/polos)
            defn = create_standard_component("motor_dahlander", tag)
        elif tid in {1004}:                    # Motor rotor bobinado
            defn = create_standard_component("motor_3p", tag)
            defn['name'] = f"Motor Rotor Bob. {tag}"
        elif tid in {1005}:                    # Motor dos velocidades independientes
            defn = create_standard_component("motor_dahlander", tag)
            defn['name'] = f"Motor 2V {tag}"
        elif tid in {1006, 1007}:             # Motor cc imanes perm. / independiente
            defn = create_standard_component("motor_1p", tag)
            defn['name'] = f"Motor CC {tag}"
        elif tid == 1008:                      # Motor monofásico con condensador
            defn = create_standard_component("motor_1p", tag)
            defn['name'] = f"Motor 1F+C {tag}"
        elif tid == 1009:                      # Freno electromagnético
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Freno {tag}"
        elif tid == 1010:                      # Motor trifásico como monofásico (Steinmetz)
            defn = create_standard_component("motor_3p", tag)
            defn['name'] = f"Motor Steinmetz {tag}"
        elif tid in {1011, 1012}:             # Motor paso a paso
            defn = create_standard_component("motor_1p", tag)
            defn['name'] = f"Motor PAP {tag}"
        elif tid == 10550:                     # Actuador lineal eléctrico
            defn = create_standard_component("motor_1p", tag)
            defn['name'] = f"Actuador Lineal {tag}"

        # ── ALIMENTACIONES (3000-3020) ────────────────────────────────────────
        elif tid == 3000:                      # Fase L
            defn = create_standard_component("power_l", tag if tag else "L1")
        elif tid == 3001:                      # Neutro N
            defn = create_standard_component("power_n", tag if tag else "N")
        elif tid in {3002, 3015}:             # PE / Toma de tierra
            defn = create_standard_component("power_n", tag if tag else "PE")
            defn['name'] = "PE"
        elif tid == 3003:                      # Fase + Neutro (monofásico)
            defn = create_standard_component("power_l", tag if tag else "L")
            defn['name'] = "Alim. F+N"
        elif tid == 3004:                      # L1+L2+L3 (trifásico)
            defn = create_standard_component("power_l", tag if tag else "L1")
            defn['name'] = "Alim. 3F"
        elif tid in {3005, 3006, 3007, 3011}: # Variantes trifásicas con PE/N
            defn = create_standard_component("power_l", tag if tag else "L1")
            defn['name'] = f"Alim. {tag} (CAD {tid})"
        elif tid in {3008, 3010}:             # CC positivo / dual
            defn = create_standard_component("power_l", tag if tag else "+")
            defn['name'] = "Alim. CC+"
        elif tid == 3009:                      # CC negativo
            defn = create_standard_component("power_n", tag if tag else "-")
            defn['name'] = "Alim. CC-"
        elif tid in {3012, 3017}:             # Transformador 1P / 3P
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Transformador {tag}"
        elif tid == 3013:                      # Rectificador
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Rectificador {tag}"
        elif tid in {3014, 3018}:             # Fuente de alimentación 1P / 3P
            defn = create_standard_component("power_l", tag if tag else "V")
            defn['name'] = f"Fuente {tag}"
        elif tid == 3016:                      # Diodo
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Diodo {tag}"
        elif tid == 3019:                      # Batería
            defn = create_standard_component("power_l", tag if tag else "BAT")
            defn['name'] = f"Batería {tag}"
        elif tid == 3020:                      # Toma de corriente
            defn = create_standard_component("power_l", tag)
            defn['name'] = f"Toma {tag}"

        # ── PLCs (10200-10260, 10300-10380, 10400-10500) ─────────────────────
        elif 10200 <= tid <= 10260:            # LOGO! Siemens
            defn = create_standard_component("power_l", tag)
            defn['name'] = f"LOGO! {tag} (CAD {tid})"
        elif 10300 <= tid <= 10380:            # S7-1200 / S7-1500
            defn = create_standard_component("power_l", tag)
            defn['name'] = f"S7 PLC {tag} (CAD {tid})"
        elif 10400 <= tid <= 10500:            # ET-200 / Arduino / Variadores
            defn = create_standard_component("power_l", tag)
            defn['name'] = f"Módulo {tag} (CAD {tid})"

        # ── LÓGICA DIGITAL (10050-10100) ──────────────────────────────────────
        elif 10050 <= tid <= 10100:
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Lógica {tag} (CAD {tid})"

        # ── NEUMÁTICA / HIDRÁULICA (1050-1090) ───────────────────────────────
        elif 1050 <= tid <= 1090:
            defn = create_standard_component("contactor_coil", tag)
            defn['name'] = f"Electroválvula {tag} (CAD {tid})"

        # ── LADDER / GRAFCET (10000-10050) ───────────────────────────────────
        elif 10000 <= tid < 10050:
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Ladder {tag} (CAD {tid})"

        # ── VIRTUAL 2D / 3D (1 - 299, 10600-10900) ───────────────────────────
        elif 1 <= tid <= 299 or 10600 <= tid <= 10900:
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Virtual {tag} (CAD {tid})"

        # ── FALLBACK: consultar dispatch table dinámica ───────────────────────
        else:
            dispatch_entry = cls._dispatch_table.get(str(tid))
            if dispatch_entry:
                comp_key = dispatch_entry.get('component_key', 'contactor_contact_no')
                if comp_key in STANDARD_COMPONENTS:
                    defn = create_standard_component(comp_key, tag)
                    defn['name'] = f"{dispatch_entry.get('name', tag)} [{tag}]"
                else:
                    defn = create_standard_component('contactor_contact_no', tag)
                    defn['name'] = f"{tag} (CAD {tid})"
            else:
                defn = create_standard_component("contactor_contact_no", tag)
                defn['name'] = f"{tag} (CAD {tid})"

        return ComponentItem(defn)

    @classmethod
    def _find_closest_terminal(cls, pt: QPointF, terminals_by_pos: list, tolerance: float = 12.0):
        closest_term = None
        min_dist = tolerance
        for term_pos, term in terminals_by_pos:
            dx = term_pos.x() - pt.x()
            dy = term_pos.y() - pt.y()
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_term = term
        return closest_term
