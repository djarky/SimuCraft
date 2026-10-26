"""
Pruebas unitarias para el motor de esquemas, cargador de CAD y lógica de simulación de SimuCraft
"""
import os
import sys
import unittest

from PySide6.QtWidgets import QApplication

from src.core.graph import CircuitGraph, Node, Edge, NodeType
from src.core.simulation.solver import CircuitSolver
from src.core.simulation.simulator import Simulator
from src.core.cad_loader import CADLoader, parse_cad_raw
from src.components.standard_components import create_standard_component, STANDARD_COMPONENTS
from src.components.pushbutton import PushButton
from src.components.contactor import Contactor
from src.qet.parser import QETParser
from src.graphics.scene import CircuitScene
from src.graphics.component_item import ComponentItem


class TestSchematics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_standard_components_definitions(self):
        """Verifica que todos los componentes estándar tengan bornes y dimensiones válidas"""
        for key in STANDARD_COMPONENTS:
            comp = create_standard_component(key)
            self.assertIsNotNone(comp['id'])
            self.assertIn('visual', comp)
            self.assertGreater(len(comp['visual']['terminals']), 0)
            self.assertIn('width', comp['visual'])
            self.assertIn('height', comp['visual'])

    def test_qet_parser_elmt_to_svg(self):
        """Verifica la conversión de archivos .elmt de QElectroTech a SVG"""
        parser = QETParser()
        sample_elmt = "assets/qet_symbols/71105013_bouton_poussoir.elmt"
        if os.path.exists(sample_elmt):
            parsed = parser.parse_symbol(sample_elmt)
            self.assertIn('svg_content', parsed)
            self.assertIn('<svg', parsed['svg_content'])
            self.assertEqual(len(parsed['terminals']), 2)

    def test_cad_file_parsing(self):
        """Verifica el parseo de esquemas CADe SIMU clásicos"""
        cad_path = "cadesimu/examples/Lab01.cad"
        self.assertTrue(os.path.exists(cad_path))
        data = parse_cad_raw(cad_path)
        self.assertGreater(len(data['symbols']), 0)
        self.assertGreater(len(data['wires']), 0)

    def test_cad_loader_into_scene(self):
        """Verifica la carga de un esquema CADe SIMU completo en CircuitScene"""
        scene = CircuitScene()
        cad_path = "cadesimu/examples/Lab01.cad"
        stats = CADLoader.load_file(cad_path, scene)
        self.assertGreater(stats['components_count'], 0)
        self.assertGreater(stats['wires_count'], 0)
        self.assertGreater(len(scene.items()), 0)

    def test_circuit_simulation_propagation(self):
        """Verifica la propagación lógica de potenciales por el grafo relacional"""
        graph = CircuitGraph()
        
        # 1. Fuente 230V
        n_source = Node(node_type=NodeType.POWER_RAIL, potential=230.0, potential_known=True)
        n1_id = graph.add_node(n_source)
        
        # 2. Terminal de entrada de pulsador
        n2 = Node(node_type=NodeType.TERMINAL)
        n2_id = graph.add_node(n2)
        
        # Cable entre fuente y terminal de entrada
        e1 = Edge(node1_id=n1_id, node2_id=n2_id)
        graph.add_edge(e1)
        
        # 3. Terminal de salida de pulsador
        n3 = Node(node_type=NodeType.TERMINAL)
        n3_id = graph.add_node(n3)
        
        # Interruptor con lógica PushButton
        btn = PushButton(normally_open=True)
        graph.components['btn1'] = btn
        e_btn = Edge(node1_id=n2_id, node2_id=n3_id, component_id='btn1', terminal1_id='13', terminal2_id='14')
        graph.add_edge(e_btn)
        
        solver = CircuitSolver(graph)
        
        # Con pulsador abierto: potencial no debe llegar a n3
        solver.solve()
        self.assertEqual(n2.potential, 230.0)
        self.assertFalse(n3.potential_known)
        
        # Pulsamos el botón: potencial debe propagarse a n3
        btn.press()
        solver.solve()
        self.assertEqual(n3.potential, 230.0)


if __name__ == '__main__':
    unittest.main()
