# Plan SimuCraft - Clon Moderno de CADe SIMU con PySide6

## Objetivo
Desarrollar un clon moderno, robusto y de código abierto de CADe SIMU (simulador de automatismos eléctricos y neumática), utilizando:
- **Python + PySide6 (Qt6)** con QGraphicsView/QGraphicsScene
- **Símbolos vectoriales de QElectroTech** (XML/SVG) - sin rediseñar iconos desde cero
- **Grafo relacional** (nodos/aristas) en lugar de coordenadas píxel-rígidas
- **Motor de simulación** basado en reglas extraídas de CADe SIMU (mediante ingeniería inversa con REA cuando disponible)
- **Patrón Command + QUndoStack** para Ctrl+Z/Ctrl+Y sin nodos huérfanos
- **Tags inteligentes** auto-generados

## Estrategia con REA (Ingeniería Inversa)
Aunque los proveedores de análisis profundo (Ghidra/Hopper/IDA/Kuna) no están configurados en este entorno, la estrategia con REA sería:

1. **Abrir el binario**: `tools.rea.open_binary` con `CADe_SIMU_V4.2.exe`
2. **Inspección estática**: Buscar strings relacionados con lógica (`TIMER`, `COIL`, `CONTACT`, `RELAY`, `K*M`, temporizadores) con `search_strings`
3. **Análisis de funciones**: Identificar funciones relacionadas con el motor de simulación usando `analyze_function` 
4. **Extracción de reglas**: Documentar ecuaciones de estado, lógica de temporizadores, flujo de corriente por nodos
5. **Cierre**: `close_binary` al terminar

*En este entorno, REA solo puede hacer `inspect_pe_resources` (que ya vimos) pero no análisis profundo sin proveedores configurados.*

## Estructura del Proyecto

```
SimuCraft/
├── src/
│   ├── core/                    # Núcleo del sistema
│   │   ├── graph/              # Modelo de grafo relacional
│   │   │   ├── node.py         # Nodo eléctrico/lógico
│   │   │   ├── edge.py         # Arista/cable
│   │   │   └── circuit_graph.py # Grafo completo
│   │   ├── simulation/         # Motor de simulación
│   │   │   ├── simulator.py    # Bucle principal
│   │   │   └── solver.py       # Resolución de estados
│   │   └── commands/           # Patrón Command para undo/redo
│   │       ├── base_command.py
│   │       └── command_manager.py
│   ├── graphics/               # Capa gráfica Qt
│   │   ├── scene.py            # QGraphicsScene personalizado
│   │   ├── view.py             # QGraphicsView con zoom/pan
│   │   ├── component_item.py   # QGraphicsItem base para componentes
│   │   ├── terminal_item.py    # Bornes/terminales visuales
│   │   └── wire_item.py        # Cables dinámicos
│   ├── qet/                    # Integración QElectroTech
│   │   ├── parser.py           # Parser XML/SVG de QElectroTech
│   │   ├── loader.py           # Carga y cache de símbolos
│   │   └── symbol_registry.py  # Registro de símbolos
│   ├── components/             # Componentes lógicos
│   │   ├── base.py             # Clase base Component
│   │   ├── power.py            # Líneas de alimentación
│   │   ├── pushbutton.py       # Pulsadores NA/NC
│   │   ├── contactor.py        # Contactores con bobina
│   │   ├── timer.py            # Temporizadores
│   │   └── circuit_breaker.py  # Disyuntores
│   ├── ui/                     # Interfaz de usuario
│   │   ├── main_window.py
│   │   ├── library_panel.py
│   │   └── properties_panel.py
│   └── main.py
├── assets/
│   ├── qet_symbols/            # Símbolos XML/SVG de QElectroTech
│   └── icons/
├── data/
│   └── component_definitions.json # Definiciones de componentes
├── tests/
└── requirements.txt
```

## 1. Clase `Componente` que hereda de `QGraphicsItem`

```python
from PySide6.QtWidgets import QGraphicsItem, QGraphicsSvgItem
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QPainter

class Componente(QGraphicsSvgItem):
    """
    Componente base que carga SVG de QElectroTech y expone bornes lógicos.
    Hereda de QGraphicsSvgItem para renderizar SVG directamente.
    """
    def __init__(self, symbol_path: str, definition: dict, parent=None):
        super().__init__(parent)
        self.definition = definition  # Definición con capa visual y lógica
        self.renderer = QSvgRenderer(symbol_path)
        self.setSharedRenderer(self.renderer)
        
        # Capa lógica
        self.logic_layer = definition['logic']
        self.state = {}  # Estado interno del componente
        self.terminals = []  # Lista de TerminalItem (bornes)
        
        # Grafo
        self.node_id = None  # ID del nodo en el grafo relacional
        self.graph_node = None
        
        # Configurar bornes desde definición
        self._setup_terminals()
        
    def _setup_terminals(self):
        """Crea TerminalItem para cada borne definido en el XML/SVG"""
        for term_def in self.definition['visual']['terminals']:
            term = TerminalItem(self, term_def)
            self.terminals.append(term)
            term.setPos(term_def['x'], term_def['y'])
    
    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        # Opcional: dibujar bornes en modo edición
```

## 2. Estructura de datos (JSON/Dict) para componente

```json
{
  "id": "contactor_km",
  "type": "contactor",
  "name": "Contactor",
  "qet_symbol": "contacts/power_contact.svg",
  
  "visual": {
    "layer": "svg",
    "svg_path": "assets/qet_symbols/contactor/contactor.svg",
    "terminals": [
      {
        "id": "1",
        "name": "L1",
        "type": "power_in",
        "x": 0,
        "y": 30,
        "orientation": "left"
      },
      {
        "id": "2", 
        "name": "T1",
        "type": "power_out",
        "x": 40,
        "y": 30,
        "orientation": "right"
      },
      {
        "id": "A1",
        "name": "A1",
        "type": "coil",
        "x": 10,
        "y": 0,
        "orientation": "top"
      },
      {
        "id": "A2",
        "name": "A2", 
        "type": "coil",
        "x": 30,
        "y": 0,
        "orientation": "top"
      }
    ],
    "bounds": {"x": 0, "y": 0, "width": 40, "height": 60}
  },
  
  "logic": {
    "layer": "simulation",
    "class": "ContactorLogic",
    "behavior": "electromagnetic",
    "coil": {
      "voltage": "24V",
      "pick_up_time_ms": 50,
      "drop_out_time_ms": 30
    },
    "contacts": [
      {"terminal_pair": ["1", "2"], "type": "NO", "controlled_by_coil": true},
      {"terminal_pair": ["A1", "A2"], "type": "coil_circuit", "is_coil": true}
    ],
    "states": ["DE_ENERGIZED", "ENERGIZED"],
    "initial_state": "DE_ENERGIZED"
  },
  
  "tags": {
    "auto_name_prefix": "KM",
    "associated_contacts_prefix": "KM"
  }
}
```

## 3. Motor de simulación en tiempo real

El bucle de simulación debe resolver el grafo relacional iterativamente:

```python
from PySide6.QtCore import QTimer

class Simulator:
    def __init__(self, circuit_graph):
        self.graph = circuit_graph
        self.timer = QTimer()
        self.timer.timeout.connect(self.step)
        self.timestep_ms = 10  # 100Hz
        self.running = False
        
    def start(self):
        self.running = True
        self.timer.start(self.timestep_ms)
        
    def step(self):
        """Un paso de simulación"""
        if not self.running:
            return
            
        # 1. Propagar voltaje desde fuentes
        self._propagate_sources()
        
        # 2. Resolver nodos eléctricos (ley de Kirchhoff)
        self._solve_nodes()
        
        # 3. Actualizar componentes (bobinas, contactos, temporizadores)
        self._update_components()
        
        # 4. Actualizar visualización si hay cambios
        self._update_visuals()
    
    def _propagate_sources(self):
        """Fuentes de alimentación establecen potencial en nodos"""
        for node in self.graph.get_source_nodes():
            node.potential = node.source_voltage
            node.visited = False
    
    def _solve_nodes(self):
        """Resolver potenciales usando búsqueda por conectividad"""
        # BFS/DFS por aristas (cables) - NO por coordenadas
        changed = True
        iterations = 0
        while changed and iterations < 100:  # Max iterations para evitar loops
            changed = False
            iterations += 1
            for edge in self.graph.edges:
                # Si un extremo tiene potencial y el otro no, propagar
                if edge.node1.potential_known() and not edge.node2.potential_known():
                    if self._can_conduct(edge):
                        edge.node2.potential = edge.node1.potential
                        changed = True
                elif edge.node2.potential_known() and not edge.node1.potential_known():
                    if self._can_conduct(edge):
                        edge.node1.potential = edge.node2.potential
                        changed = True
    
    def _can_conduct(self, edge):
        """Verificar si un componente permite conducción"""
        component = edge.component
        if not component:
            # Cable directo - siempre conduce si hay potencial
            return True
        return component.is_conducting(edge.terminal1, edge.terminal2)
    
    def _update_components(self):
        """Actualizar estado de componentes con lógica temporal"""
        for comp in self.graph.components:
            comp.update(self.timestep_ms / 1000.0)  # delta time en segundos
```

## Parser QElectroTech

```python
from xml.etree import ElementTree as ET

class QETParser:
    """Parser para archivos XML/SVG de QElectroTech"""
    
    def parse_symbol(self, filepath: str) -> dict:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        terminals = []
        # Buscar elementos <terminal> o puntos de conexión
        for term in root.iter('terminal'):
            terminals.append({
                'id': term.attrib.get('name', term.attrib.get('id')),
                'x': float(term.attrib.get('x', 0)),
                'y': float(term.attrib.get('y', 0)),
                'orientation': term.attrib.get('orientation', 'unknown')
            })
        
        return {
            'svg_content': open(filepath).read(),
            'terminals': terminals,
            'viewBox': root.attrib.get('viewBox')
        }
```

## Próximos pasos

1. **Fase 1**: Configurar proyecto PySide6 básico con estructura de carpetas
2. **Fase 2**: Implementar grafo relacional (Node, Edge, CircuitGraph)
3. **Fase 3**: Parser QElectroTech para extraer bornes
4. **Fase 4**: Clase Componente con QGraphicsSvgItem
5. **Fase 5**: Motor de simulación básico
6. **Fase 6**: Integración con símbolos QElectroTech reales (buscar en el sistema)
7. **Fase 7**: Ingeniería inversa con REA cuando proveedores estén disponibles

## Notas importantes

- **Grafo sobre píxeles**: Los cables se conectan a `TerminalItem` por ID, no por coordenadas. Al mover componente, solo se recalculan rutas visuales.
- **Command Pattern**: Todas las acciones van por `QUndoCommand` con `undo()/redo()` que actualizan el grafo.
- **Tags inteligentes**: Al añadir contactor, el `TagManager` asigna KM1, KM2 automáticamente y enlaza contactos.
- **Sin heredar fallas**: El modelo es puramente relacional, el undo es atómico, los tags son automáticos.
