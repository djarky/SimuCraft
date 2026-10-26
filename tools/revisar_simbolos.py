#!/usr/bin/env python3
from xml.etree import ElementTree as ET
import json

simbolos = [
    'assets/qet_symbols/71105013_bouton_poussoir.elmt',
    'assets/qet_symbols/km_tri.elmt',
    'assets/qet_symbols/412500-contacteur_sil_230v_2p_250v_25a_opf.elmt',
    'assets/qet_symbols/412429-aux-sig-telerupteur-contacteur-no-nf.elmt',
]

for f in simbolos:
    print(f"\n{'='*60}")
    print(f"ARCHIVO: {f}")
    print('='*60)
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        
        # Nombres
        names = root.find('names')
        if names is not None:
            for n in names:
                print(f"Nombre [{n.attrib.get('lang','')}]: {n.text}")
        
        # Terminales
        terminals = root.findall('.//terminal')
        print(f"\nTerminales: {len(terminals)}")
        for i, t in enumerate(terminals):
            print(f"  T{i+1}: x={t.attrib.get('x')}, y={t.attrib.get('y')}, orient={t.attrib.get('orientation')}, name={t.attrib.get('name')}")
        
        # Ver si tiene estados (para interruptores/contactores con 2 estados)
        drawing = root.find('drawing')
        if drawing is not None:
            print(f"\nTiene elemento <drawing> - OK para renderizado")
            # Buscar elementos dinámicos
            for child in drawing:
                print(f"  Drawing child: {child.tag}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("REVISIÓN COMPLETADA")
print("="*60)
