import json
import os
from glob import glob

qet_base = '/home/vibecode/DevS/qelectrotech-elements/elements'
results = []

# Recorrer todas las carpetas
for root, dirs, files in os.walk(qet_base):
    for fn in files:
        if fn.endswith('.elmt'):
            full_path = os.path.join(root, fn)
            rel_path = os.path.relpath(full_path, qet_base)
            category = rel_path.split('/')[0] if '/' in rel_path else 'other'
            subcategory = '/'.join(rel_path.split('/')[:3])
            results.append({
                'filename': fn,
                'rel_path': rel_path,
                'category': category,
                'subcategory': subcategory,
                'full_path': full_path
            })

# Agrupar por palabras clave
keywords = ['motor', 'contactor', 'pulsador', 'disyuntor', 'rele', 'relé', 'bobina', 'piloto', 'lampara', 'termico', 'guardamotor', 'seccionador', 'interruptor', 'temporizador', 'final', 'carrera', 'logo', 'clp', 'plc', 'barra', 'borne', 'fusible']

grouped = {}
for r in results:
    name_lower = r['filename'].lower()
    matched = []
    for k in keywords:
        if k in name_lower:
            matched.append(k)
    r['keywords'] = matched
    for m in matched:
        if m not in grouped:
            grouped[m] = []
        grouped[m].append(r)

# Guardar todo
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
out_dir = base_dir / 'data' / 'catalogs'
out_dir.mkdir(parents=True, exist_ok=True)

with open(out_dir / 'qet_symbols_catalog.json', 'w', encoding='utf-8') as f:
    json.dump({
        'total': len(results),
        'all': results[:2000],  # limitar para no crear archivo gigante
        'grouped_by_keyword': grouped
    }, f, indent=2, ensure_ascii=False)

# CSV
import csv
with open(out_dir / 'qet_symbols_catalog.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['Filename', 'Rel_Path', 'Category', 'Subcategory', 'Keywords', 'Full_Path'])
    for r in results:
        w.writerow([r['filename'], r['rel_path'], r['category'], r['subcategory'], ','.join(r['keywords']), r['full_path']])

print(f"Total elmt: {len(results)}")
for k,v in grouped.items():
    print(f"{k}: {len(v)}")
