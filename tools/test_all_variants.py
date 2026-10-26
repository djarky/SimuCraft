from PySide6.QtWidgets import QApplication
import sys
sys.path.insert(0, '/home/vibecode/DevS/SimuCraft')

app = QApplication.instance() or QApplication(sys.argv)

from src.graphics import CircuitScene
from src.components.standard_components import STANDARD_COMPONENTS, create_standard_component
from src.graphics.component_item import ComponentItem
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import QRectF

scene = CircuitScene()

y = 0
x = 0
count = 0
for key in sorted(STANDARD_COMPONENTS.keys()):
    try:
        defn = create_standard_component(key)
        item = ComponentItem(defn)
        item.setPos(x * 160, y * 220)
        scene.addItem(item)
        scene.circuit_graph.add_component(item)
        count += 1
        x += 1
        if x > 7:
            x = 0
            y += 1
    except Exception as e:
        print(f"ERR {key}: {e}")

rect = scene.itemsBoundingRect().adjusted(-80,-80,80,80)
img = QPixmap(int(rect.width()), int(rect.height()))
img.fill()
painter = QPainter(img)
painter.setRenderHint(QPainter.Antialiasing)
scene.render(painter, QRectF(0,0,rect.width(),rect.height()), rect)
painter.end()
import os
out_dir = '/home/vibecode/DevS/SimuCraft/data/analysis/renders_check'
os.makedirs(out_dir, exist_ok=True)
img.save(os.path.join(out_dir, 'all_variants_test.png'))
print(f"ok {count}")
