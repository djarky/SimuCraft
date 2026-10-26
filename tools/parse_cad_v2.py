#!/usr/bin/env python3
import json
import glob
import os
from collections import Counter, defaultdict

# Clasificación tentativa por ID
WIRE_IDS = {4000, 4001, 4009, 4010, 4018, 4019, 4020}
NODE_IDS = {0}
SYMBOL_IDS_HINTS = {
    # rangos típicos de símbolos en CADe SIMU
}

def classify_type_id(tid_str):
    try:
        tid = int(tid_str)
    except:
        return 'unknown', tid_str
    
    if tid == 0:
        return 'node', tid
    if tid in WIRE_IDS or 4000 <= tid <= 4025:
        return 'wire', tid
    if 1000 <= tid <= 1999:
        return 'connection_block', tid
    if 2000 <= tid <= 2999:
        return 'misc', tid
    if 3000 <= tid <= 3999:
        return 'frame/text', tid
    if 5000 <= tid <= 5999:
        return 'aux', tid
    if 6000 <= tid <= 6999:
        return 'symbol', tid
    if 7000 <= tid <= 7999:
        return 'symbol', tid
    if 8000 <= tid <= 8999:
        return 'symbol', tid
    if 9000 <= tid <= 9999:
        return 'symbol', tid
    if tid >= 10000:
        return 'symbol/extended', tid
    return 'other', tid

def parse_cad_file(filepath):
    with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
        data = f.read()
    
    parts = data.split('*')
    result = {
        'filename': os.path.basename(filepath),
        'header': parts[0] if len(parts) > 0 else '',
        'version': parts[1] if len(parts) > 1 else '',
        'id_header': parts[2] if len(parts) > 2 else '',
        'raw_parts_count': len(parts),
        'nodes': [],
        'wires': [],
        'symbols': [],
        'others': []
    }
    
    i = 3
    while i < len(parts):
        p = parts[i]
        if not p or p.strip() == '':
            i += 1
            continue
        if '#' in p and p[0].isdigit():
            comp_type_id = p.split('#')[0]
            cat, tid_int = classify_type_id(comp_type_id)
            comp = {
                'type_id': comp_type_id,
                'type_id_int': tid_int,
                'category': cat,
                'raw_prefix': p,
                'params': []
            }
            j = i + 1
            # leer params hasta siguiente componente
            while j < len(parts):
                np = parts[j]
                if not np or np.strip() == '':
                    j += 1
                    continue
                if '#' in np and np and np[0].isdigit():
                    break
                # parsear numero
                s = np.strip()
                try:
                    # intentar int
                    if s.lstrip('-').isdigit():
                        comp['params'].append(int(s))
                        j += 1
                        continue
                    # float/simple
                    comp['params'].append(s)
                    j += 1
                    continue
                except:
                    comp['params'].append(s)
                    j += 1
                    continue
            comp['param_count'] = len(comp['params'])
            # guardar por categoría
            if cat == 'node':
                result['nodes'].append(comp)
            elif cat == 'wire':
                result['wires'].append(comp)
            elif cat == 'symbol' or cat == 'symbol/extended':
                result['symbols'].append(comp)
            else:
                result['others'].append(comp)
            i = j
            continue
        i += 1
    
    result['stats'] = {
        'nodes': len(result['nodes']),
        'wires': len(result['wires']),
        'symbols': len(result['symbols']),
        'others': len(result['others'])
    }
    return result

def main():
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    examples_dir = BASE / 'cadesimu' / 'examples'
    files = sorted(glob.glob(str(examples_dir / '*.cad')))
    
    print(f"Parseando {len(files)} archivos con clasificación\n")
    print("=" * 100)
    print(f"{'ARCHIVO':35} | {'NODOS':6} | {'CABLES':6} | {'SIMBOLOS':8} | {'OTROS':6}")
    print("=" * 100)
    
    all_symbols = Counter()
    symbol_details = defaultdict(list)
    
    for filepath in files:
        try:
            parsed = parse_cad_file(filepath)
            print(f"{parsed['filename']:35} | {parsed['stats']['nodes']:6} | {parsed['stats']['wires']:6} | {parsed['stats']['symbols']:8} | {parsed['stats']['others']:6}")
            for s in parsed['symbols']:
                all_symbols[s['type_id']] += 1
                symbol_details[s['type_id']].append({
                    'file': parsed['filename'],
                    'params': s['params'][:16]
                })
        except Exception as e:
            print(f"ERROR {filepath}: {e}")
    
    print("=" * 100)
    print("\nSÍMBOLOS MÁS FRECUENTES (6xxx-9xxx+):")
    for tid, count in all_symbols.most_common(40):
        print(f"  {tid:10} -> {count} veces")
    
    # Guardar
    detailed = []
    for filepath in files:
        try:
            detailed.append(parse_cad_file(filepath))
        except:
            pass
    
    out_dir = BASE / 'data' / 'analysis'
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / 'cad_analysis_v2.json', 'w', encoding='utf-8') as f:
        json.dump(detailed, f, indent=2, ensure_ascii=False)
    
    with open(out_dir / 'cad_symbol_map.json', 'w', encoding='utf-8') as f:
        json.dump(dict(symbol_details), f, indent=2, ensure_ascii=False)
    
    print(f"\nGuardado: {out_dir / 'cad_analysis_v2.json'}, {out_dir / 'cad_symbol_map.json'}")

if __name__ == '__main__':
    main()
