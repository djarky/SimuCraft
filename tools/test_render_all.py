#!/usr/bin/env python3
import os
import sys
from collections import Counter

# Headless
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap, QPainter

from src.graphics import CircuitScene
from src.core.cad_loader import CADLoader

app = QApplication.instance() or QApplication(sys.argv)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

examples_dir = os.path.join(BASE, 'cadesimu', 'examples')
out_dir = os.path.join(BASE, 'data', 'analysis', 'renders_check')
os.makedirs(out_dir, exist_ok=True)

files = sorted([f for f in os.listdir(examples_dir) if f.endswith('.cad')])

print(f"Renderizando {len(files)} archivos...\n")
print(f"{'Archivo':30} | {'Comp':5} | {'Cables':7} | {'Term connected':14} | {'Tipos'}")
print("-" * 110)

for fname in files:
    fpath = os.path.join(examples_dir, fname)
    try:
        scene = CircuitScene()
        stats = CADLoader.load_file(fpath, scene)
        
        # Contar tipos
        types = Counter()
        for comp in scene.circuit_graph.components.values():
            ctype = getattr(comp, 'component_type', getattr(comp, 'name', 'unknown'))
            types[ctype] += 1
        
        # Contar terminales conectados
        connected_terms = 0
        total_terms = 0
        for comp in scene.circuit_graph.components.values():
            if hasattr(comp, 'terminals'):
                for t in comp.terminals:
                    total_terms += 1
                    if hasattr(t, 'connections') and t.connections:
                        connected_terms += 1
        
        # Render
        rect = scene.itemsBoundingRect()
        if rect.isNull() or rect.isEmpty():
            rect = QRectF(0, 0, 800, 600)
        else:
            rect = rect.adjusted(-80, -80, 80, 80)
        
        img = QPixmap(int(rect.width()), int(rect.height()))
        img.fill()
        painter = QPainter(img)
        scene.render(painter, QRectF(0,0,rect.width(),rect.height()), rect)
        painter.end()
        
        out = os.path.join(out_dir, fname.replace('.cad', '.png'))
        img.save(out)
        
        print(f"{fname:30} | {stats['components_count']:5} | {stats['wires_count']:7} | {connected_terms:3}/{total_terms:<3}({connected_terms/total_terms*100 if total_terms else 0:4.0f}%) | {dict(types.most_common(6))}")
    except Exception as e:
        print(f"{fname:30} | ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n\nCapturas guardadas en: {out_dir}/")
