#!/usr/bin/env python3
import json
import os
import sys
from xml.etree import ElementTree as ET

from pathlib import Path

# Cargar mapeo
BASE = Path(__file__).resolve().parent.parent
mapping_file = BASE / 'data' / 'mappings' / 'cad_qet_mapping.json'
if not mapping_file.exists():
    mapping_file = BASE / 'cad_qet_mapping.json'
with open(mapping_file) as f:
    mapping_data = json.load(f)
CAD_TO_QET = mapping_data['mappings']

class CadToInternalConverter:
    def __init__(self):
        self.circuit = {
            'name': '',
            'version': '1.0',
            'source_file': '',
            'nodes': [],
            'wires': [],
            'components': [],
            'metadata': {}
        }
    
    def parse_cad(self, filepath):
        with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
            data = f.read()
        
        parts = data.split('*')
        self.circuit['source_file'] = os.path.basename(filepath)
        self.circuit['name'] = os.path.splitext(os.path.basename(filepath))[0]
        self.circuit['metadata']['header'] = parts[0] if len(parts) > 0 else ''
        self.circuit['metadata']['version'] = parts[1] if len(parts) > 1 else ''
        
        i = 3
        node_counter = 0
        wire_counter = 0
        comp_counter = 0
        
        while i < len(parts):
            p = parts[i]
            if not p or p.strip() == '':
                i += 1
                continue
            if '#' in p and len(p) > 0 and p[0].isdigit():
                comp_type_id = p.split('#')[0]
                # Leer params
                params = []
                j = i + 1
                while j < len(parts):
                    np = parts[j]
                    if not np or np.strip() == '':
                        j += 1
                        continue
                    if '#' in np and np and np[0].isdigit():
                        break
                    s = np.strip()
                    if s.lstrip('-').isdigit():
                        params.append(int(s))
                    else:
                        params.append(s)
                    j += 1
                
                # Clasificar
                if comp_type_id == '0':
                    # Nodo
                    node = {
                        'id': f'node_{node_counter}',
                        'original_id': node_counter,
                        'type': 'junction',
                        'params': params
                    }
                    self.circuit['nodes'].append(node)
                    node_counter += 1
                elif 4000 <= int(comp_type_id) <= 4019:
                    # Cable
                    wire = {
                        'id': f'wire_{wire_counter}',
                        'type_id': comp_type_id,
                        'params': params
                    }
                    self.circuit['wires'].append(wire)
                    wire_counter += 1
                elif comp_type_id in CAD_TO_QET:
                    mapping = CAD_TO_QET[comp_type_id]
                    if mapping.get('type') != 'unknown' and mapping.get('type') != 'frame':
                        comp = {
                            'id': f'comp_{comp_counter}',
                            'type_id': comp_type_id,
                            'mapped_type': mapping['type'],
                            'subtype': mapping.get('subtype'),
                            'qet_file': mapping.get('qet_file'),
                            'name': mapping.get('name', comp_type_id),
                            'params': params
                        }
                        # Extraer coordenadas si las hay
                        if len(params) >= 16:
                            comp['position'] = {'x': params[8], 'y': params[9]}
                        self.circuit['components'].append(comp)
                        comp_counter += 1
                else:
                    # Desconocido pero guardar
                    pass
                
                i = j
                continue
            i += 1
        
        self.circuit['stats'] = {
            'nodes': len(self.circuit['nodes']),
            'wires': len(self.circuit['wires']),
            'components': len(self.circuit['components'])
        }
        return self.circuit
    
    def save(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.circuit, f, indent=2, ensure_ascii=False)
        print(f"Guardado: {output_path}")
        print(f"  Nodos: {self.circuit['stats']['nodes']}")
        print(f"  Cables: {self.circuit['stats']['wires']}")
        print(f"  Componentes: {self.circuit['stats']['components']}")

def main():
    if len(sys.argv) < 2:
        print("Uso: python cad_to_internal.py <archivo.cad> [salida.json]")
        print("\nArchivos disponibles:")
        for f in os.listdir('cadesimu/examples'):
            if f.endswith('.cad'):
                print(f"  {f}")
        return
    
    converter = CadToInternalConverter()
    circuit = converter.parse_cad(sys.argv[1])
    
    out = sys.argv[2] if len(sys.argv) > 2 else f"{os.path.splitext(sys.argv[1])[0]}_internal.json"
    converter.save(out)

if __name__ == '__main__':
    main()
