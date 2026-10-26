"""
Parser para archivos .elmt de QElectroTech
Convierte XML (.elmt) a especificación con bornes y SVG estándar
"""
from xml.etree import ElementTree as ET
from typing import Dict, List, Any
import os
import math


class QETParser:
    """
    Convierte archivos XML/SVG de QElectroTech a estructura con bornes lógicos
    y genera SVG renderizable por Qt.
    """
    
    @staticmethod
    def parse_style(style_str: str) -> str:
        """Convierte estilo QET en atributos SVG"""
        styles = {}
        if not style_str:
            return 'stroke="black" stroke-width="1.5" fill="none"'
        for part in style_str.split(';'):
            if ':' in part:
                k, v = part.split(':', 1)
                styles[k.strip()] = v.strip()
        
        stroke = styles.get('color', 'black')
        fill = styles.get('filling', 'none')
        if fill == 'none':
            fill_attr = 'fill="none"'
        else:
            fill_attr = f'fill="{fill}"'
            
        weight = styles.get('line-weight', 'normal')
        sw = '1.5'
        if weight == 'thin':
            sw = '0.75'
        elif weight == 'normal':
            sw = '1.5'
        elif weight in ('hight', 'bold'):
            sw = '2.5'
            
        dash_attr = ''
        line_style = styles.get('line-style', 'normal')
        if line_style == 'dashed':
            dash_attr = 'stroke-dasharray="4,3"'
        elif line_style == 'dotted':
            dash_attr = 'stroke-dasharray="2,2"'
            
        return f'stroke="{stroke}" stroke-width="{sw}" {fill_attr} {dash_attr}'.strip()

    def elmt_to_svg(self, filepath: str) -> str:
        """Convierte el contenido gráfico de un .elmt a SVG estándar"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
        except Exception:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="none" stroke="black"/></svg>'

        hx = float(root.attrib.get('hotspot_x', 0))
        hy = float(root.attrib.get('hotspot_y', 0))
        w = float(root.attrib.get('width', 40))
        h = float(root.attrib.get('height', 40))
        
        vx = -hx
        vy = -hy
        svg_elements = []
        
        desc = root.find('description')
        if desc is not None:
            for el in desc:
                tag = el.tag
                style = self.parse_style(el.attrib.get('style', ''))
                
                if tag == 'rect':
                    x = el.attrib.get('x', '0')
                    y = el.attrib.get('y', '0')
                    rw = el.attrib.get('width', '10')
                    rh = el.attrib.get('height', '10')
                    rx = el.attrib.get('rx', '0')
                    ry = el.attrib.get('ry', '0')
                    svg_elements.append(f'<rect x="{x}" y="{y}" width="{rw}" height="{rh}" rx="{rx}" ry="{ry}" {style}/>')
                    
                elif tag == 'circle':
                    x = float(el.attrib.get('x', 0))
                    y = float(el.attrib.get('y', 0))
                    d = float(el.attrib.get('diameter', 10))
                    r = d / 2.0
                    cx = x + r
                    cy = y + r
                    svg_elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" {style}/>')
                    
                elif tag == 'ellipse':
                    x = float(el.attrib.get('x', 0))
                    y = float(el.attrib.get('y', 0))
                    ew = float(el.attrib.get('width', 10))
                    eh = float(el.attrib.get('height', 10))
                    cx = x + ew / 2.0
                    cy = y + eh / 2.0
                    rx = ew / 2.0
                    ry = eh / 2.0
                    svg_elements.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {style}/>')
                    
                elif tag == 'line':
                    x1 = el.attrib.get('x1', '0')
                    y1 = el.attrib.get('y1', '0')
                    x2 = el.attrib.get('x2', '0')
                    y2 = el.attrib.get('y2', '0')
                    svg_elements.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {style}/>')
                    
                elif tag == 'polygon':
                    # Puntos x1, y1, x2, y2...
                    pts = []
                    idx = 1
                    while f'x{idx}' in el.attrib and f'y{idx}' in el.attrib:
                        pts.append(f"{el.attrib[f'x{idx}']},{el.attrib[f'y{idx}']}")
                        idx += 1
                    if pts:
                        svg_elements.append(f'<polygon points="{" ".join(pts)}" {style}/>')
                        
                elif tag == 'arc':
                    # Arco aproximado en SVG
                    ax = float(el.attrib.get('x', 0))
                    ay = float(el.attrib.get('y', 0))
                    aw = float(el.attrib.get('width', 10))
                    ah = float(el.attrib.get('height', 10))
                    start = float(el.attrib.get('start', 0))
                    angle = float(el.attrib.get('angle', 180))
                    # Convertir a path
                    rad_s = math.radians(start)
                    rad_e = math.radians(start + angle)
                    cx = ax + aw / 2.0
                    cy = ay + ah / 2.0
                    rx = aw / 2.0
                    ry = ah / 2.0
                    x1 = cx + rx * math.cos(rad_s)
                    y1 = cy - ry * math.sin(rad_s)
                    x2 = cx + rx * math.cos(rad_e)
                    y2 = cy - ry * math.sin(rad_e)
                    large = 1 if abs(angle) > 180 else 0
                    sweep = 0 if angle > 0 else 1
                    d = f"M {x1} {y1} A {rx} {ry} 0 {large} {sweep} {x2} {y2}"
                    svg_elements.append(f'<path d="{d}" {style}/>')
                    
                elif tag == 'text':
                    x = el.attrib.get('x', '0')
                    y = el.attrib.get('y', '0')
                    txt = el.attrib.get('text', '')
                    # Escapar xml
                    txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    svg_elements.append(f'<text x="{x}" y="{y}" font-size="7" font-family="sans-serif" fill="black">{txt}</text>')
                    
                elif tag == 'dynamic_text':
                    t_elem = el.find('text')
                    if t_elem is not None and t_elem.text:
                        x = el.attrib.get('x', '0')
                        y = el.attrib.get('y', '0')
                        txt = t_elem.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        svg_elements.append(f'<text x="{x}" y="{y}" font-size="7" font-family="sans-serif" fill="black">{txt}</text>')
        
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx} {vy} {w} {h}" width="{w}" height="{h}">\n'
            + '\n'.join(svg_elements)
            + '\n</svg>'
        )
        return svg

    def parse_symbol(self, filepath: str) -> Dict[str, Any]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Extraer información
        definition = {
            'uuid': root.attrib.get('uuid', ''),
            'names': {},
            'terminals': [],
            'width': float(root.attrib.get('width', 40)),
            'height': float(root.attrib.get('height', 40)),
            'hotspot_x': float(root.attrib.get('hotspot_x', 0)),
            'hotspot_y': float(root.attrib.get('hotspot_y', 0)),
            'viewBox': None
        }
        
        # Extraer nombres
        names_elem = root.find('names')
        if names_elem is not None:
            for name in names_elem:
                lang = name.attrib.get('lang', 'en')
                definition['names'][lang] = name.text or ''
        
        # Extraer terminales/bornes
        terminals = root.findall('.//terminal')
        for idx, term in enumerate(terminals):
            term_data = {
                'id': term.attrib.get('name') or term.attrib.get('uuid') or f'term_{idx}',
                'uuid': term.attrib.get('uuid', ''),
                'x': float(term.attrib.get('x', 0)),
                'y': float(term.attrib.get('y', 0)),
                'orientation': term.attrib.get('orientation', 'unknown'),
                'type': term.attrib.get('type', 'Generic')
            }
            definition['terminals'].append(term_data)
            
        definition['svg_content'] = self.elmt_to_svg(filepath)
        return definition
    
    def create_component_definition(self, elmt_path: str, component_type: str = "generic") -> Dict[str, Any]:
        """
        Crear definición completa de componente con capas visual y lógica
        """
        parsed = self.parse_symbol(elmt_path)
        
        # Deducir tipo según nombre si es generic
        name_lower = (parsed['names'].get('es') or parsed['names'].get('en') or parsed['names'].get('fr') or '').lower()
        if 'poussoir' in name_lower or 'pulsador' in name_lower or 'bouton' in name_lower:
            component_type = 'pushbutton'
        elif 'contacteur' in name_lower or 'contactor' in name_lower:
            component_type = 'contactor'
        elif 'relais' in name_lower or 'relay' in name_lower or 'rele' in name_lower:
            component_type = 'relay'
        elif 'moteur' in name_lower or 'motor' in name_lower:
            component_type = 'motor'
            
        prefix = 'K'
        if component_type == 'pushbutton':
            prefix = 'S'
        elif component_type == 'contactor':
            prefix = 'KM'
        elif component_type == 'motor':
            prefix = 'M'
            
        return {
            'id': os.path.basename(elmt_path).replace('.elmt', ''),
            'type': component_type,
            'name': parsed['names'].get('es') or parsed['names'].get('en') or parsed['names'].get('fr') or os.path.basename(elmt_path),
            'qet_uuid': parsed['uuid'],
            'visual': {
                'layer': 'svg',
                'elmt_path': elmt_path,
                'terminals': parsed['terminals'],
                'render_mode': 'svg',
                'svg_content': parsed.get('svg_content', ''),
                'width': parsed.get('width', 40),
                'height': parsed.get('height', 40),
                'hotspot_x': parsed.get('hotspot_x', 0),
                'hotspot_y': parsed.get('hotspot_y', 0)
            },
            'logic': {
                'layer': 'simulation',
                'class': f'{component_type.capitalize()}Logic',
                'behavior': 'passive',
                'states': [],
                'initial_state': None
            },
            'tags': {
                'auto_name_prefix': prefix,
                'can_auto_name': True
            }
        }
