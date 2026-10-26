"""
Cargador mejorado de esquemas de CADe SIMU (.cad) para SimuCraft
Usa mapeo completo CAD -> QElectroTech
"""
import os
import json
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QPointF

from ..components.standard_components import create_standard_component
from ..graphics.component_item import ComponentItem
from ..qet import QETParser
from .graph import Node, Edge, NodeType


# Cargar mapeo
MAPPING_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cad_qet_mapping.json')
try:
    with open(MAPPING_PATH) as f:
        CAD_QET_MAP = json.load(f)['mappings']
except Exception:
    CAD_QET_MAP = {}


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
            elif tid >= 5000 or tid in {0, 8000, 8001, 9000, 9008, 6007, 6009, 7000}:
                if tid != 0:  # Skip junction nodes, handled differently
                    result['symbols'].append(comp)
            i = j
            continue
        i += 1
        
    return result


class CADLoader:
    """Carga esquemas .cad y los inserta en CircuitScene"""
    
    SCALE = 7.0
    
    @classmethod
    def load_file(cls, filepath: str, scene) -> Dict[str, Any]:
        """Cargar un archivo .cad en la escena gráfica"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
            
        cad_data = parse_cad_raw(filepath)
        scene.clear_circuit()
        
        created_components = []
        created_wires = []
        
        # 1. Crear componentes de los símbolos
        for sym in cad_data['symbols']:
            tid = sym['tid']
            tid_str = sym['type_id']
            parts = sym['raw_prefix'].split('#')
            tag = parts[1] if len(parts) > 1 and parts[1] else f"K{tid}"
            
            p = sym['params']
            gx = p[8] if len(p) > 8 and isinstance(p[8], (int, float)) else 0
            gy = p[9] if len(p) > 9 and isinstance(p[9], (int, float)) else 0
            
            pos_x = float(gx) * cls.SCALE
            pos_y = float(gy) * cls.SCALE
            
            comp_item = cls._create_component_for_symbol(tid_str, tag, parts)
            if comp_item:
                comp_item.setPos(pos_x, pos_y)
                scene.add_component(comp_item)
                created_components.append(comp_item)
                
        # 2. Añadir líneas de alimentación por defecto
        if created_components:
            min_x = min([c.x() for c in created_components], default=200)
            max_x = max([c.x() for c in created_components], default=600)
            min_y = min([c.y() for c in created_components], default=100)
            max_y = max([c.y() for c in created_components], default=800)
            
            try:
                power_l_def = create_standard_component("power_l", "L1")
                power_l = ComponentItem(power_l_def)
                power_l.setPos(min_x - 50, min_y - 60)
                scene.add_component(power_l)
                created_components.append(power_l)
                
                power_n_def = create_standard_component("power_n", "N")
                power_n = ComponentItem(power_n_def)
                power_n.setPos(min_x - 50, max_y + 60)
                scene.add_component(power_n)
                created_components.append(power_n)
            except Exception as e:
                print(f"[CADLoaderImproved] Advertencia fuentes L/N: {e}")
        
        # 3. Crear cables
        terminals_by_pos = []
        for comp in created_components:
            for term in comp.terminals:
                try:
                    term_pos = term.get_scene_pos()
                    terminals_by_pos.append((term_pos, term))
                except Exception:
                    continue
                
        for w in cad_data['wires']:
            p = w['params']
            if len(p) >= 12:
                try:
                    x1 = float(p[8]) * cls.SCALE
                    y1 = float(p[9]) * cls.SCALE
                    x2 = float(p[10]) * cls.SCALE
                    y2 = float(p[11]) * cls.SCALE
                except (ValueError, TypeError):
                    continue
                    
                pt1 = QPointF(x1, y1)
                pt2 = QPointF(x2, y2)
                
                t1 = cls._find_closest_terminal(pt1, terminals_by_pos, tolerance=30.0)
                t2 = cls._find_closest_terminal(pt2, terminals_by_pos, tolerance=30.0)
                
                wire_item = scene.create_wire_between_points(pt1, pt2, t1, t2)
                if wire_item:
                    created_wires.append(wire_item)
                    
        return {
            'filename': os.path.basename(filepath),
            'components_count': len(created_components),
            'wires_count': len(created_wires),
            'symbols_raw': len(cad_data['symbols'])
        }

    @classmethod
    def _create_component_for_symbol(cls, tid_str: str, tag: str, raw_parts: list) -> Optional[ComponentItem]:
        """Mapear ID de símbolo CADe SIMU a componente SimuCraft con mejor mapeo"""
        mapping = CAD_QET_MAP.get(tid_str)
        
        # Pulsadores NA/NC
        if tid_str in {'8000', '8002'}:
            defn = create_standard_component("pushbutton_no", tag)
            return ComponentItem(defn)
        elif tid_str == '8001':
            defn = create_standard_component("pushbutton_nc", tag)
            return ComponentItem(defn)
        elif tid_str in {'8005'}:
            defn = create_standard_component("pushbutton_no", tag)
            return ComponentItem(defn)
            
        # Contactores / Relés - bobinas
        elif tid_str in {'6007', '6009', '6002'}:
            defn = create_standard_component("contactor_coil", tag)
            return ComponentItem(defn)
        elif tid_str == '6008':
            defn = create_standard_component("contactor_coil", tag)
            return ComponentItem(defn)
        elif tid_str == '6010':
            defn = create_standard_component("contactor_coil", tag)
            return ComponentItem(defn)
            
        # Contactos principales/auxiliares
        elif tid_str in {'9000', '9004'}:
            defn = create_standard_component("contactor_contact_no", tag)
            return ComponentItem(defn)
        elif tid_str == '9008':
            defn = create_standard_component("contactor_contact_no", tag)
            # Intentar asociar con contactor si hay tag
            return ComponentItem(defn)
            
        # Bornes/Terminales
        elif tid_str in {'7000', '7001', '7004'}:
            # No crear componente visual extra, son puntos de conexión
            return None
            
        # Relé térmico / guardamotor
        elif tid_str == '8017':
            defn = create_standard_component("thermal_relay", tag)
            return ComponentItem(defn)
        elif tid_str in {'8016', '8018', '8019'}:
            defn = create_standard_component("thermal_relay", tag)
            return ComponentItem(defn)
            
        # Motores
        elif tid_str in {'10050', '10051', '10060'}:
            defn = create_standard_component("motor_3p", tag)
            return ComponentItem(defn)
            
        # Otros casos
        elif tid_str == '20000':
            return None  # Marco/etiqueta, ignorar
        elif tid_str == '10202':
            return None
            
        # Por defecto, intentar crear contacto auxiliar
        else:
            # Si empieza con 8xxx puede ser pulsador/contacto
            try:
                tid_int = int(tid_str)
                if 8000 <= tid_int < 9000:
                    defn = create_standard_component("pushbutton_no", tag)
                    defn['name'] = f"Pulsador {tag} (CAD {tid_str})"
                    return ComponentItem(defn)
                elif 9000 <= tid_int < 10000:
                    defn = create_standard_component("contactor_contact_no", tag)
                    defn['name'] = f"Contacto {tag} (CAD {tid_str})"
                    return ComponentItem(defn)
                elif 6000 <= tid_int < 7000:
                    defn = create_standard_component("contactor_coil", tag)
                    defn['name'] = f"Bobina {tag} (CAD {tid_str})"
                    return ComponentItem(defn)
            except Exception as e:
                print(f"[CADLoaderImproved] Fallback para TID {tid_str}: {e}")
            defn = create_standard_component("contactor_contact_no", tag)
            defn['name'] = f"Elemento {tag} (CAD {tid_str})"
            return ComponentItem(defn)

    @classmethod
    def _find_closest_terminal(cls, pt: QPointF, terminals_by_pos: list, tolerance: float = 20.0):
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
