#!/usr/bin/env python3
"""
build_tile_map.py
Construye:
  data/mappings/tile_to_cad_id.json     -- mapa {bmp_id}_{row}_{col} -> CAD_ID + metadatos
  data/mappings/cad_id_to_component.json -- dispatch table CAD_ID -> componente SimuCraft
"""
import json, os, re
from pathlib import Path
from collections import defaultdict

BASE         = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE / 'data' / 'catalogs' / 'cadesimu_symbols_complete.json'
TILES_DIR    = BASE / 'cadesimu' / 'bmp_extract' / 'cadesimu_tiles'
OUT_TILE_MAP = BASE / 'data' / 'mappings' / 'tile_to_cad_id.json'
OUT_DISPATCH = BASE / 'data' / 'mappings' / 'cad_id_to_component.json'

# Qué categorías del catálogo viven en cada bitmap (orden de aparición en CADe SIMU)
BITMAP_CATEGORIES = {
    259: ['Contactos','Bobinas','Accionamientos','Senalizacion',
          'Protecciones','Logica','Ladder','GRAFCET'],
    262: ['Motores','Contactores','Alimentaciones','Cables','Potencia',
          'Detectores','Neumatica','PLC','Conexiones','2D_3D','Virtual_2D'],
}

# Dispatch manual: CAD_ID (str) -> component_key de SimuCraft
MANUAL_DISPATCH = {
    "7000":"contact_no","7001":"contact_nc","7002":"contact_no","7003":"contact_nc",
    "7004":"contact_no","7005":"contact_nc",
    "9000":"relay_coil","9001":"relay_coil","9003":"relay_coil",
    "9008":"pilot_lamp","9009":"pilot_lamp","9010":"pilot_lamp","9011":"pilot_lamp",
    "8000":"pushbutton_no","8001":"pushbutton_nc","8002":"pushbutton_no",
    "8003":"pushbutton_nc","8004":"pushbutton_no","8005":"pushbutton_nc",
    "8006":"emergency_stop","8010":"selector_2pos",
    "5000":"thermal_relay_3p","5001":"thermal_relay_3p",
    "5002":"breaker_3p","5003":"breaker_3p","5004":"breaker_3p",
    "6000":"fuse","6001":"fuse",
    "1000":"motor_3p","1001":"motor_3p","1002":"motor_1p",
    "1003":"motor_star_delta","1004":"motor_dahlander",
    "2000":"contactor_3p","2001":"contactor_3p","2002":"contactor_3p",
    "2003":"contactor_4p","2004":"contactor_2p",
    "3000":"power_l","3001":"power_n","3002":"power_l","3010":"power_l",
}


def main():
    print("[*] Cargando catalogo REA...")
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    print(f"    {len(catalog)} simbolos.")

    # Agrupar por categoria
    by_cat = defaultdict(list)
    for sym in sorted(catalog, key=lambda s: s['CAD_ID']):
        by_cat[sym['Categoria']].append(sym)

    # Leer tiles
    bmp_tiles = defaultdict(list)
    for fname in sorted(os.listdir(TILES_DIR)):
        m = re.match(r'(\d+)_(\d+)_(\d+)\.png', fname)
        if m:
            bmp_tiles[int(m.group(1))].append((int(m.group(2)), int(m.group(3))))
    for k in bmp_tiles: bmp_tiles[k].sort()
    total = sum(len(v) for v in bmp_tiles.values())
    print(f"    {total} tiles en bitmaps {sorted(bmp_tiles.keys())}")

    # Construir tile_map
    tile_map = {}
    for bmp_id, tiles in sorted(bmp_tiles.items()):
        cats = BITMAP_CATEGORIES.get(bmp_id, [])
        syms, used = [], set()
        for cat in cats:
            for sym in by_cat.get(cat, []):
                if sym['CAD_ID'] not in used:
                    syms.append(sym)
                    used.add(sym['CAD_ID'])
        for idx, (row, col) in enumerate(tiles):
            key = f"{bmp_id}_{row:02d}_{col:02d}"
            if idx < len(syms):
                s = syms[idx]
                tile_map[key] = {
                    "cad_id":   s['CAD_ID'],
                    "name":     s.get('Nombre_Original_EXE','') or s.get('Descripcion',''),
                    "category": s.get('Categoria',''),
                    "subtipo":  s.get('Subtipo',''),
                    "tags":     s.get('Tags',''),
                    "bitmap": bmp_id, "row": row, "col": col,
                }
            else:
                tile_map[key] = {
                    "cad_id": None, "name": f"?({bmp_id},{row},{col})",
                    "category":"Desconocido","subtipo":"","tags":"",
                    "bitmap": bmp_id, "row": row, "col": col,
                }

    assigned = sum(1 for v in tile_map.values() if v['cad_id'] is not None)
    print(f"    {assigned}/{len(tile_map)} tiles asignados.")
    OUT_TILE_MAP.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_TILE_MAP,'w',encoding='utf-8') as f:
        json.dump(tile_map, f, indent=2, ensure_ascii=False)
    print(f"    OK: {OUT_TILE_MAP}")

    # Dispatch table
    cat_by_id = {str(s['CAD_ID']): s for s in catalog}
    dispatch = {}
    for cid_str, comp_key in MANUAL_DISPATCH.items():
        s = cat_by_id.get(cid_str, {})
        dispatch[cid_str] = {
            "component_key": comp_key,
            "name": s.get('Nombre_Original_EXE','') or s.get('Descripcion', comp_key),
            "category": s.get('Categoria',''),
            "cad_id": int(cid_str),
        }
    with open(OUT_DISPATCH,'w',encoding='utf-8') as f:
        json.dump(dispatch, f, indent=2, ensure_ascii=False)
    print(f"    OK: {OUT_DISPATCH} ({len(dispatch)} entradas)")
    print("[OK] Completado.")

if __name__ == '__main__':
    main()
