#!/usr/bin/env python3
import json
import os
import glob
from xml.etree import ElementTree as ET

from pathlib import Path
BASE = Path(__file__).resolve().parent.parent

# Cargar mapeo de símbolos CAD
sym_path = BASE / 'data' / 'analysis' / 'cad_symbol_map.json'
if not sym_path.exists():
    sym_path = BASE / 'cad_symbol_map.json'
with open(sym_path) as f:
    cad_symbols = json.load(f)

# Buscar símbolos .elmt
elmt_files = []
for root_dir in ['/home/vibecode/DevS/SimuCraft/assets/qet_symbols', 
                  '/home/vibecode/DevS/qelectrotech-elements/elements']:
    for f in glob.glob(os.path.join(root_dir, '**/*.elmt'), recursive=True):
        elmt_files.append(f)

print(f"Encontrados {len(elmt_files)} archivos .elmt")

# Analizar cada uno
elmt_info = []
for ef in elmt_files:
    try:
        tree = ET.parse(ef)
        root = tree.getroot()
        names = {}
        names_elem = root.find('names')
        if names_elem is not None:
            for name in names_elem:
                lang = name.attrib.get('lang', 'en')
                if name.text:
                    names[lang] = name.text.strip()
        terminals = root.findall('.//terminal')
        elmt_info.append({
            'path': ef,
            'basename': os.path.basename(ef),
            'names': names,
            'term_count': len(terminals),
            'uuid': root.attrib.get('uuid', '')
        })
    except:
        pass

# Guardar
out_file = BASE / 'data' / 'catalogs' / 'qet_elmt_catalog.json'
out_file.parent.mkdir(parents=True, exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(elmt_info, f, indent=2, ensure_ascii=False)

print(f"Catálogo guardado en {out_file}")
