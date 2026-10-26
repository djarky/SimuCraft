#!/usr/bin/env python3
import json
import glob
import os
from collections import Counter, defaultdict

def parse_cad_file(filepath):
    with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
        data = f.read()
    
    parts = data.split('*')
    result = {
        'filename': os.path.basename(filepath),
        'header': parts[0] if len(parts) > 0 else '',
        'version': parts[1] if len(parts) > 1 else '',
        'id': parts[2] if len(parts) > 2 else '',
        'raw_parts_count': len(parts),
        'components': [],
        'connections': []
    }
    
    i = 3
    comp_idx = 0
    while i < len(parts):
        p = parts[i]
        if not p:
            i += 1
            continue
        # Check if it's a component (starts with number followed by #)
        if '#' in p and p[0].isdigit():
            comp_type_id = p.split('#')[0]
            comp = {
                'index': comp_idx,
                'type_id': comp_type_id,
                'raw': p,
                'params': []
            }
            # Try to parse params after this
            j = i + 1
            # Read numeric params
            while j < len(parts) and len(comp['params']) < 30:
                np = parts[j]
                if not np:
                    j += 1
                    continue
                # If next component starts
                if '#' in np and np[0].isdigit():
                    break
                # Try to parse number
                try:
                    # Handle negative numbers
                    if np.replace('-', '').replace('.', '').isdigit():
                        comp['params'].append(int(np))
                    elif np.replace('-', '').replace('.', '').replace('e', '').replace('E', '').replace('+', '').isdigit():
                        comp['params'].append(float(np))
                    else:
                        comp['params'].append(np)
                except:
                    comp['params'].append(np)
                j += 1
            comp['next_idx'] = j
            result['components'].append(comp)
            comp_idx += 1
            i = j
            continue
        i += 1
    
    return result

def main():
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent
    examples_dir = BASE / 'cadesimu' / 'examples'
    files = sorted(glob.glob(str(examples_dir / '*.cad')))
    
    print(f"Analizando {len(files)} archivos .CAD\n")
    print("=" * 80)
    
    all_type_ids = Counter()
    file_summaries = []
    
    for filepath in files:
        try:
            parsed = parse_cad_file(filepath)
            type_counts = Counter(c['type_id'] for c in parsed['components'])
            all_type_ids.update(type_counts)
            file_summaries.append({
                'file': parsed['filename'],
                'components': len(parsed['components']),
                'types': dict(type_counts)
            })
            print(f"{parsed['filename']:30} | {len(parsed['components']):3} componentes | {dict(type_counts)}")
        except Exception as e:
            print(f"ERROR {filepath}: {e}")
    
    print("\n" + "=" * 80)
    print("\nTIPOS MÁS COMUNES EN TODOS LOS ARCHIVOS:")
    for tid, count in all_type_ids.most_common(30):
        print(f"  {tid:10} -> {count} ocurrencias")
    
    # Guardar análisis detallado
    detailed = []
    for filepath in files:
        try:
            detailed.append(parse_cad_file(filepath))
        except:
            pass
    
    out_dir = BASE / 'data' / 'analysis'
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / 'cad_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(detailed, f, indent=2, ensure_ascii=False)
    
    print(f"\n\nAnálisis guardado en {out_dir / 'cad_analysis.json'}")
    
    # Guardar resumen
    with open(out_dir / 'cad_summary.json', 'w', encoding='utf-8') as f:
        json.dump(file_summaries, f, indent=2, ensure_ascii=False)
    
    print(f"Resumen guardado en {out_dir / 'cad_summary.json'}")

if __name__ == '__main__':
    main()
