"""
Pruebas unitarias para las mejoras de la interfaz de usuario:
- Márgenes de la hoja de dibujo
- Previsualización y modo de inserción de componentes
- Cancelación del modo inserción con tecla ESC
- Selección de componentes con click simple
- Eliminación de componentes y cables con Undo/Redo
"""
import sys
import unittest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent

from src.graphics.scene import CircuitScene
from src.graphics.view import CircuitView
from src.graphics.component_item import ComponentItem
from src.components.standard_components import create_standard_component
from src.core.commands import CommandManager
from src.ui.main_window import MainWindow


class TestUIImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_drawing_sheet_margins(self):
        """Verifica que la hoja de dibujo tenga márgenes normalizados y área útil definida."""
        scene = CircuitScene()
        self.assertTrue(hasattr(scene, 'sheet_rect'))
        self.assertGreater(scene.sheet_rect.width(), 1000)
        self.assertGreater(scene.sheet_rect.height(), 1000)

        self.assertGreater(scene.margin_left, 0)
        self.assertGreater(scene.margin_top, 0)
        self.assertGreater(scene.margin_right, 0)
        self.assertGreater(scene.margin_bottom, 0)

        inner = scene.get_inner_drawing_rect()
        self.assertEqual(inner.left(), scene.sheet_rect.left() + scene.margin_left)
        self.assertEqual(inner.top(), scene.sheet_rect.top() + scene.margin_top)
        self.assertEqual(inner.right(), scene.sheet_rect.right() - scene.margin_right)
        self.assertEqual(inner.bottom(), scene.sheet_rect.bottom() - scene.margin_bottom)

    def test_component_placement_and_ghost_preview(self):
        """Verifica la activación del modo de inserción con previsualización fantasma."""
        scene = CircuitScene()
        defn = create_standard_component('pushbutton_no', 'S1')

        # Iniciar modo inserción
        scene.start_placement_mode(defn)
        self.assertTrue(scene.placement_mode)
        self.assertIsNotNone(scene.preview_item)
        self.assertTrue(getattr(scene.preview_item, 'is_preview', False))
        self.assertAlmostEqual(scene.preview_item.opacity(), 0.60, places=1)
        self.assertIn(scene.preview_item, scene.items())

        # El componente de preview NO debe estar registrado en el grafo aún
        self.assertNotIn(scene.preview_item.id, scene.circuit_graph.components)

        # Colocar el componente en una posición
        scene.place_current_component(QPointF(200.0, 300.0))

        # Ahora en el grafo debe existir 1 componente real
        self.assertEqual(len(scene.circuit_graph.components), 1)

    def test_cancel_placement_with_escape(self):
        """Verifica que la tecla ESC cancele el modo inserción y retire el preview fantasma."""
        scene = CircuitScene()
        defn = create_standard_component('contactor_coil', 'KM1')

        scene.start_placement_mode(defn)
        self.assertTrue(scene.placement_mode)
        preview_ref = scene.preview_item

        # Simular tecla ESC
        esc_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        scene.keyPressEvent(esc_event)

        # El modo inserción debe desactivarse y el preview retirarse
        self.assertFalse(scene.placement_mode)
        self.assertIsNone(scene.preview_item)
        self.assertNotIn(preview_ref, scene.items())

    def test_single_click_selection_signal(self):
        """Verifica que el widget de la biblioteca emita component_selected con un clic simple."""
        main_win = MainWindow()
        lib_widget = main_win.library_widget

        selected_defn = None

        def on_selected(defn):
            nonlocal selected_defn
            selected_defn = defn

        lib_widget.component_selected.connect(on_selected)

        # Simular clic en el primer item de la lista de componentes estándar
        if lib_widget.std_list.count() > 0:
            item = lib_widget.std_list.item(0)
            lib_widget._on_std_item_clicked(item)
            self.assertIsNotNone(selected_defn)
            # Debe haber activado el modo inserción en la ventana principal
            self.assertTrue(main_win.scene.placement_mode)
            self.assertIsNotNone(main_win.scene.preview_item)

        main_win.close()

    def test_atomic_deletion_and_undo(self):
        """Verifica la eliminación de componentes seleccionados y su restauración con Undo."""
        main_win = MainWindow()
        scene = main_win.scene
        scene.clear_circuit()

        # Añadir 2 componentes
        comp1 = ComponentItem(create_standard_component('power_l', 'L1'))
        comp1.setPos(100, 100)
        scene.add_component(comp1)

        comp2 = ComponentItem(create_standard_component('power_n', 'N'))
        comp2.setPos(200, 100)
        scene.add_component(comp2)

        self.assertEqual(len(scene.circuit_graph.components), 2)

        # Seleccionar ambos
        comp1.setSelected(True)
        comp2.setSelected(True)

        # Eliminar selección
        scene.delete_selected_items()
        self.assertEqual(len(scene.circuit_graph.components), 0)
        self.assertNotIn(comp1, scene.items())
        self.assertNotIn(comp2, scene.items())

        # Deshacer (Undo) con una sola llamada
        main_win.command_manager.undo()
        self.assertEqual(len(scene.circuit_graph.components), 2)
        self.assertIn(comp1, scene.items())
        self.assertIn(comp2, scene.items())

        main_win.close()

    def test_wire_type_and_color_selection(self):
        """Verifica que los cables adopten fielmente el tipo y color seleccionado."""
        scene = CircuitScene()
        from src.graphics.wire_item import WireItem
        from src.components.wire_types import WIRE_CATALOG

        # 1. Por defecto, tipo 4000 (Fase marrón)
        self.assertEqual(scene.current_wire_type, 4000)
        self.assertEqual(scene.current_wire_color.name().upper(), "#8B4513")

        # 2. Cambiar a Neutro (4001, azul)
        scene.set_current_wire_type(4001)
        self.assertEqual(scene.current_wire_type, 4001)
        self.assertEqual(scene.current_wire_color.name().upper(), "#0080FF")

        # 3. Crear un cable entre puntos y verificar su color
        wire = scene.create_wire_between_points(QPointF(10, 10), QPointF(100, 10))
        self.assertEqual(wire.wire_type, 4001)
        self.assertEqual(wire.wire_color.name().upper(), "#0080FF")
        self.assertEqual(wire.pen().color().name().upper(), "#0080FF")

        # 4. Cambiar tipo y color de cables seleccionados
        wire.setSelected(True)
        count = scene.set_current_wire_type(4002)  # Tierra PE (Verde)
        self.assertEqual(count, 1)
        self.assertEqual(wire.wire_type, 4002)
        self.assertEqual(wire.wire_color.name().upper(), "#16A34A")
        self.assertEqual(wire.pen().color().name().upper(), "#16A34A")

    def test_wire_palette_widget_interaction(self):
        """Verifica la paleta visual de colores de cables en MainWindow."""
        main_win = MainWindow()
        palette = main_win.wire_palette
        scene = main_win.scene

        self.assertIsNotNone(palette)
        self.assertIn(4000, palette._buttons)
        self.assertIn(4001, palette._buttons)
        self.assertIn(4002, palette._buttons)
        self.assertIn(4003, palette._buttons)

        # Simular clic en botón Positivo (+) (4003, Rojo)
        palette._buttons[4003].click()
        self.assertEqual(scene.current_wire_type, 4003)
        self.assertEqual(scene.current_wire_color.name().upper(), "#DC2626")

        main_win.close()

    def test_cad_loader_preserves_wire_types(self):
        """Verifica que el cargador CADe SIMU preserve los tipos de cable originales."""
        scene = CircuitScene()
        from src.core.cad_loader import CADLoader
        stats = CADLoader.load_file("cadesimu/examples/Lab01.cad", scene)
        self.assertGreater(stats['wires_count'], 0)

        # En Lab01 existen cables 4000 (Fase) y 4009 (Conexión)
        wire_types = {w.wire_type for w in scene.wires}
        self.assertTrue(len(wire_types) > 1, f"Tipos de cable detectados: {wire_types}")
        self.assertTrue(4000 in wire_types or 4009 in wire_types)


if __name__ == '__main__':
    unittest.main()

