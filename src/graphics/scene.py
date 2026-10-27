"""
Escena gráfica del circuito eléctrico
Gestiona la colocación de componentes, cableado interactivo, márgenes de hoja de dibujo,
previsualización interactiva (ghost preview) y sincronización con el grafo relacional.
"""
from typing import Optional, List, Set, Tuple

from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPen, QColor, QBrush, QFont, QPainter

from ..core.graph import CircuitGraph, Node, Edge, NodeType
from .wire_item import WireItem


class CircuitScene(QGraphicsScene):
    """
    Escena interactiva del esquema eléctrico con hoja de dibujo normalizada,
    márgenes técnicos, rejilla de alineación, modo de inserción con previsualización
    y soporte completo para cableado y eliminación con Undo/Redo.
    """

    cursor_moved = Signal(float, float)
    placement_changed = Signal(bool, str)
    wire_type_changed = Signal(int, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.circuit_graph = CircuitGraph()
        self.wiring_mode = False
        self.temp_wire = None
        self.start_terminal = None
        self.wires: List[WireItem] = []
        self.junction_nodes = {}

        # Configuración del tipo y color de cable activo
        self.current_wire_type = 4000
        self.current_wire_color = QColor("#8B4513")
        self.current_wire_width = 2.0
        self.current_wire_style = Qt.SolidLine

        # Estado de inserción de componentes con previsualización
        self.placement_mode: bool = False
        self.placement_defn: Optional[dict] = None
        self.preview_item = None

        # Hoja de dibujo normalizada con márgenes estilo CAD (CADe SIMU / QElectroTech)
        # Tamaño de hoja amplio para soportar circuitos industriales grandes
        self.sheet_rect = QRectF(40.0, 40.0, 2400.0, 3000.0)
        self.margin_left = 45.0   # Margen de encuadernación / archivo
        self.margin_top = 30.0    # Margen superior
        self.margin_right = 30.0  # Margen derecho
        self.margin_bottom = 30.0 # Margen inferior

        # Área total de la escena incluyendo el espacio exterior de mesa de trabajo
        self.setSceneRect(0, 0, 2480, 3080)

    # ── MÁRGENES Y FONDO DE LA HOJA DE DIBUJO ─────────────────────────────────

    def get_inner_drawing_rect(self) -> QRectF:
        """Devuelve el rectángulo útil interior de dibujo delimitado por los márgenes."""
        sx = self.sheet_rect.x()
        sy = self.sheet_rect.y()
        sw = self.sheet_rect.width()
        sh = self.sheet_rect.height()
        return QRectF(
            sx + self.margin_left,
            sy + self.margin_top,
            sw - (self.margin_left + self.margin_right),
            sh - (self.margin_top + self.margin_bottom)
        )

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """
        Dibuja la mesa de trabajo, la sombra de la hoja, el papel blanco,
        los márgenes técnicos con referencias alfanuméricas, la cuadrícula y el cajetín.
        """
        painter.setRenderHint(QPainter.Antialiasing, False)

        # 1. Fondo de la mesa de trabajo (gris técnico moderno)
        painter.fillRect(rect, QColor("#1e1e2e"))

        # Si el área visible no interseca con la hoja, no dibujamos más
        if not rect.intersects(self.sheet_rect.adjusted(-20, -20, 30, 30)):
            return

        # 2. Sombra proyectada de la hoja (drop shadow suave)
        shadow_rect = self.sheet_rect.translated(8, 8)
        painter.fillRect(shadow_rect, QColor(10, 10, 18, 140))

        # 3. Folio de la hoja de dibujo (blanco técnico nítido)
        painter.fillRect(self.sheet_rect, QColor("#ffffff"))

        # Borde exterior de la hoja de papel
        painter.setPen(QPen(QColor("#94a3b8"), 1.0))
        painter.drawRect(self.sheet_rect)

        # 4. Marco exterior del plano (a 12 px dentro del papel)
        border_rect = self.sheet_rect.adjusted(12, 12, -12, -12)
        painter.setPen(QPen(QColor("#334155"), 1.5))
        painter.drawRect(border_rect)

        # 5. Marco interior del plano (márgenes técnicos de trabajo)
        inner_rect = self.get_inner_drawing_rect()
        painter.setPen(QPen(QColor("#0f172a"), 1.5))
        painter.drawRect(inner_rect)

        # 6. Cuadrícula técnica (grid) en el área útil de dibujo
        self._draw_grid(painter, inner_rect, rect)

        # 7. Coordenadas y divisiones en los márgenes (A..L y 1..12)
        self._draw_margin_coordinates(painter, border_rect, inner_rect)

        # 8. Cajetín técnico en la esquina inferior derecha
        self._draw_title_block(painter, inner_rect)

    def _draw_grid(self, painter: QPainter, inner_rect: QRectF, clip_rect: QRectF):
        """Dibuja la cuadrícula técnica de 20 px con guías cada 100 px."""
        grid_step = 20.0
        major_step = 100.0

        intersect_rect = inner_rect.intersected(clip_rect)
        if intersect_rect.isEmpty():
            return

        start_x = int((intersect_rect.left() - inner_rect.left()) / grid_step) * grid_step + inner_rect.left()
        start_y = int((intersect_rect.top() - inner_rect.top()) / grid_step) * grid_step + inner_rect.top()

        end_x = min(intersect_rect.right(), inner_rect.right())
        end_y = min(intersect_rect.bottom(), inner_rect.bottom())

        # Líneas finas menores
        pen_minor = QPen(QColor("#edf2f7"), 0.8, Qt.DotLine)
        # Líneas mayores
        pen_major = QPen(QColor("#cbd5e1"), 1.0, Qt.SolidLine)

        x = start_x
        while x <= end_x:
            is_major = (round(x - inner_rect.left()) % int(major_step)) == 0
            painter.setPen(pen_major if is_major else pen_minor)
            painter.drawLine(QPointF(x, intersect_rect.top()), QPointF(x, intersect_rect.bottom()))
            x += grid_step

        y = start_y
        while y <= end_y:
            is_major = (round(y - inner_rect.top()) % int(major_step)) == 0
            painter.setPen(pen_major if is_major else pen_minor)
            painter.drawLine(QPointF(intersect_rect.left(), y), QPointF(intersect_rect.right(), y))
            y += grid_step

    def _draw_margin_coordinates(self, painter: QPainter, border_rect: QRectF, inner_rect: QRectF):
        """Dibuja las marcas y letras/números de coordenadas de plano en los márgenes."""
        painter.setRenderHint(QPainter.Antialiasing, True)
        font = QFont("Sans Serif", 7, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#475569")))

        # Columnas numéricas (1, 2, 3...) a lo largo del ancho
        num_cols = 12
        col_w = inner_rect.width() / num_cols
        for i in range(num_cols):
            cx = inner_rect.left() + i * col_w
            num_str = str(i + 1)
            # Marcas de división
            painter.drawLine(QPointF(cx, border_rect.top()), QPointF(cx, inner_rect.top()))
            painter.drawLine(QPointF(cx, inner_rect.bottom()), QPointF(cx, border_rect.bottom()))
            # Números
            painter.drawText(QRectF(cx, border_rect.top(), col_w, inner_rect.top() - border_rect.top()),
                             Qt.AlignCenter, num_str)
            painter.drawText(QRectF(cx, inner_rect.bottom(), col_w, border_rect.bottom() - inner_rect.bottom()),
                             Qt.AlignCenter, num_str)

        # Filas con letras (A, B, C...) a lo largo de la altura
        row_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]
        num_rows = len(row_letters)
        row_h = inner_rect.height() / num_rows
        for i in range(num_rows):
            cy = inner_rect.top() + i * row_h
            let_str = row_letters[i]
            # Marcas de división
            painter.drawLine(QPointF(border_rect.left(), cy), QPointF(inner_rect.left(), cy))
            painter.drawLine(QPointF(inner_rect.right(), cy), QPointF(border_rect.right(), cy))
            # Letras
            painter.drawText(QRectF(border_rect.left(), cy, inner_rect.left() - border_rect.left(), row_h),
                             Qt.AlignCenter, let_str)
            painter.drawText(QRectF(inner_rect.right(), cy, border_rect.right() - inner_rect.right(), row_h),
                             Qt.AlignCenter, let_str)

    def _draw_title_block(self, painter: QPainter, inner_rect: QRectF):
        """Dibuja el cajetín de rotulación técnica en la esquina inferior derecha."""
        box_w = 360.0
        box_h = 70.0
        bx = inner_rect.right() - box_w
        by = inner_rect.bottom() - box_h

        # Fondo blanco del cajetín
        painter.fillRect(QRectF(bx, by, box_w, box_h), QColor("#ffffff"))

        # Marco del cajetín
        painter.setPen(QPen(QColor("#0f172a"), 1.5))
        painter.drawRect(QRectF(bx, by, box_w, box_h))

        # Divisiones horizontales
        painter.drawLine(QPointF(bx, by + 24), QPointF(bx + box_w, by + 24))
        painter.drawLine(QPointF(bx, by + 48), QPointF(bx + box_w, by + 48))

        # Divisiones verticales
        painter.drawLine(QPointF(bx + 230, by), QPointF(bx + 230, by + box_h))
        painter.drawLine(QPointF(bx + 115, by + 48), QPointF(bx + 115, by + box_h))

        # Textos técnicos
        painter.setFont(QFont("Sans Serif", 7, QFont.Normal))
        painter.setPen(QColor("#64748b"))
        painter.drawText(int(bx + 6), int(by + 11), "PROYECTO:")
        painter.drawText(int(bx + 6), int(by + 35), "ESQUEMA:")
        painter.drawText(int(bx + 6), int(by + 59), "FECHA:")
        painter.drawText(int(bx + 122), int(by + 59), "HOJA:")
        painter.drawText(int(bx + 236), int(by + 14), "SISTEMA:")

        painter.setFont(QFont("Sans Serif", 8, QFont.Bold))
        painter.setPen(QColor("#0f172a"))
        painter.drawText(int(bx + 68), int(by + 16), "Automatismos SimuCraft")
        painter.drawText(int(bx + 68), int(by + 40), "Esquema Eléctrico Principal")
        painter.drawText(int(bx + 48), int(by + 64), "2026")
        painter.drawText(int(bx + 162), int(by + 64), "1 / 1")

        painter.setFont(QFont("Sans Serif", 9, QFont.Bold))
        painter.setPen(QColor("#2563eb"))
        painter.drawText(int(bx + 236), int(by + 42), "SimuCraft")
        painter.setFont(QFont("Sans Serif", 7, QFont.Normal))
        painter.setPen(QColor("#64748b"))
        painter.drawText(int(bx + 236), int(by + 58), "CADe SIMU Compatible")

    # ── MODO DE INSERCIÓN Y PREVISUALIZACIÓN (GHOST PREVIEW) ───────────────────

    def start_placement_mode(self, defn: dict):
        """
        Activar el modo de inserción con previsualización flotante (ghost preview)
        que acompaña al cursor del ratón hasta hacer clic para colocarlo.
        """
        # Cancelar cableado si estuviera en curso
        if self.wiring_mode:
            self.cancel_wire()

        # Limpiar preview previo si existiera
        self._remove_preview_item()

        from .component_item import ComponentItem
        self.placement_defn = defn
        self.placement_mode = True

        # Crear el item visual de previsualización
        self.preview_item = ComponentItem(defn)
        self.preview_item.setOpacity(0.60)
        self.preview_item.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.preview_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.preview_item.setAcceptedMouseButtons(Qt.NoButton)
        self.preview_item.is_preview = True

        self.addItem(self.preview_item)

        # Actualizar cursor de las vistas a cruz de precisión
        for view in self.views():
            view.setCursor(Qt.CrossCursor)

        name = defn.get('name', 'Componente')
        self.placement_changed.emit(True, name)

    def cancel_placement(self):
        """Cancelar el modo de inserción y retirar la previsualización."""
        self._remove_preview_item()
        self.placement_mode = False
        self.placement_defn = None

        # Restaurar cursor normal en vistas
        for view in self.views():
            view.setCursor(Qt.ArrowCursor)

        self.placement_changed.emit(False, "")

    def _remove_preview_item(self):
        if self.preview_item:
            if self.preview_item.scene() == self:
                self.removeItem(self.preview_item)
            self.preview_item = None

    def place_current_component(self, scene_pos: QPointF):
        """Estampar el componente actual en la posición indicada con registro en Undo/Redo."""
        if not self.placement_defn:
            return

        from .component_item import ComponentItem
        # Snap a la cuadrícula de 20 px para alineación perfecta
        GRID = 20.0
        snap_x = round(scene_pos.x() / GRID) * GRID
        snap_y = round(scene_pos.y() / GRID) * GRID

        # Crear componente definitivo
        real_item = ComponentItem(self.placement_defn)
        real_item.setPos(snap_x, snap_y)

        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import AddComponentCommand
            cmd = AddComponentCommand(self, real_item, f"Añadir {real_item.name}")
            main_win.command_manager.push(cmd)
        else:
            self.add_component(real_item)

        if main_win and hasattr(main_win, 'statusBar'):
            main_win.statusBar().showMessage(
                f"✔ Componente '{real_item.name}' colocado en ({int(snap_x)}, {int(snap_y)}) — "
                f"Clic para colocar otro o ESC para salir."
            )

    # ── MODO CABLEAR ──────────────────────────────────────────────────────────

    def set_wiring_mode(self, enabled: bool):
        self.wiring_mode = enabled
        if not enabled:
            self.cancel_wire()
        else:
            if self.placement_mode:
                self.cancel_placement()

    def set_current_wire_type(self, type_id_or_key: Any, color: Optional[str] = None) -> int:
        """
        Establece el tipo y color de cable activo para nuevas conexiones.
        Si hay cables seleccionados en el esquema, actualiza su tipo y color inmediatamente.
        Devuelve la cantidad de cables seleccionados actualizados.
        """
        from ..components.wire_types import get_wire_info
        info = get_wire_info(type_id_or_key)
        self.current_wire_type = info["id"]
        chosen_color = color if color else info["color"]
        self.current_wire_color = QColor(chosen_color) if isinstance(chosen_color, str) else chosen_color
        self.current_wire_width = info.get("width", 2.0)
        self.current_wire_style = info.get("style", Qt.SolidLine)

        # 1. Si hay un cable temporal en curso, actualizarlo
        if self.temp_wire:
            self.temp_wire.set_wire_type(
                self.current_wire_type,
                color=self.current_wire_color,
                width=self.current_wire_width,
                style=self.current_wire_style
            )

        # 2. Si hay cables seleccionados en la escena, cambiar su color y tipo
        selected_wires = [item for item in self.selectedItems() if isinstance(item, WireItem)]
        for w in selected_wires:
            w.set_wire_type(
                self.current_wire_type,
                color=self.current_wire_color,
                width=self.current_wire_width,
                style=self.current_wire_style
            )

        self.wire_type_changed.emit(self.current_wire_type, info["name"], self.current_wire_color.name())
        return len(selected_wires)

    def start_wire(self, terminal):
        self.wiring_mode = True
        self.start_terminal = terminal
        self.temp_wire = WireItem(
            terminal1=terminal,
            wire_type=self.current_wire_type,
            color=self.current_wire_color,
            width=self.current_wire_width,
            style=self.current_wire_style
        )
        self.addItem(self.temp_wire)

    def cancel_wire(self):
        if self.temp_wire and self.temp_wire.scene() == self:
            self.removeItem(self.temp_wire)
        self.temp_wire = None
        self.start_terminal = None
        self.wiring_mode = False

    def finish_wire(self, end_terminal):
        """Finalizar cableado creando nodo y arista en el grafo relacional conservando waypoints"""
        if not self.start_terminal or not end_terminal:
            self.cancel_wire()
            return

        if not self.start_terminal.graph_node_id:
            node = Node(node_type=NodeType.TERMINAL)
            self.circuit_graph.add_node(node)
            self.start_terminal.graph_node_id = node.id

        if not end_terminal.graph_node_id:
            node = Node(node_type=NodeType.TERMINAL)
            self.circuit_graph.add_node(node)
            end_terminal.graph_node_id = node.id

        edge = Edge(
            node1_id=self.start_terminal.graph_node_id,
            node2_id=end_terminal.graph_node_id,
            terminal1_id=self.start_terminal.terminal_id,
            terminal2_id=end_terminal.terminal_id,
            component_id=None
        )
        self.circuit_graph.add_edge(edge)

        captured_waypoints = list(self.temp_wire.waypoints) if self.temp_wire else []

        wire = WireItem(
            terminal1=self.start_terminal,
            terminal2=end_terminal,
            wire_type=self.current_wire_type,
            color=self.current_wire_color,
            width=self.current_wire_width,
            style=self.current_wire_style
        )
        wire.waypoints = captured_waypoints
        wire.update_path()
        wire.edge_id = edge.id

        if self.temp_wire and self.temp_wire.scene() == self:
            self.removeItem(self.temp_wire)
        self.temp_wire = None

        self.addItem(wire)
        self.wires.append(wire)

        start_t = self.start_terminal
        if start_t:
            start_t.connected_wires.append(wire)
        if end_terminal:
            end_terminal.connected_wires.append(wire)

        self.start_terminal = None
        self.wiring_mode = False

        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import AddWireCommand
            cmd = AddWireCommand(self, wire, edge, start_t, end_terminal)
            main_win.command_manager.push(cmd)
        if main_win and hasattr(main_win, 'statusBar'):
            main_win.statusBar().showMessage("✔ Cable enrutado y conectado con éxito.")
        return wire

    def finish_wire_to_wire(self, target_wire, junction_pt: QPointF):
        """Finalizar cableado creando una derivación / bifurcación en T hacia otro conductor existente"""
        if not self.start_terminal:
            self.cancel_wire()
            return None

        # 1. Asegurar nodo inicial en el grafo
        if not self.start_terminal.graph_node_id:
            node = Node(node_type=NodeType.TERMINAL)
            self.circuit_graph.add_node(node)
            self.start_terminal.graph_node_id = node.id

        # 2. Obtener o crear nodo de bifurcación
        k = (round(junction_pt.x(), 1), round(junction_pt.y(), 1))
        if k in self.junction_nodes:
            junction_node_id = self.junction_nodes[k]
        else:
            j_node = Node(node_type=NodeType.JUNCTION)
            junction_node_id = self.circuit_graph.add_node(j_node)
            self.junction_nodes[k] = junction_node_id

        # 3. Conectar el cable existente al nodo de bifurcación si tiene edge_id
        if target_wire.edge_id:
            target_edge = self.circuit_graph.edges.get(target_wire.edge_id)
            if target_edge:
                edge_bif = Edge(
                    node1_id=target_edge.node1_id,
                    node2_id=junction_node_id,
                    component_id=None
                )
                self.circuit_graph.add_edge(edge_bif)

        # 4. Crear arista para el nuevo cable de derivación
        edge = Edge(
            node1_id=self.start_terminal.graph_node_id,
            node2_id=junction_node_id,
            terminal1_id=self.start_terminal.terminal_id,
            terminal2_id=None,
            component_id=None
        )
        self.circuit_graph.add_edge(edge)

        captured_waypoints = list(self.temp_wire.waypoints) if self.temp_wire else []
        wire = WireItem(
            terminal1=self.start_terminal,
            terminal2=None,
            pt2=junction_pt,
            wire_type=self.current_wire_type,
            color=self.current_wire_color,
            width=self.current_wire_width,
            style=self.current_wire_style
        )
        wire.waypoints = captured_waypoints
        wire.has_end_junction = True  # Punto de empalme normalizado (●)
        wire.update_path()
        wire.edge_id = edge.id

        if self.temp_wire and self.temp_wire.scene() == self:
            self.removeItem(self.temp_wire)
        self.temp_wire = None

        self.addItem(wire)
        self.wires.append(wire)

        start_t = self.start_terminal
        if start_t:
            start_t.connected_wires.append(wire)

        self.start_terminal = None
        self.wiring_mode = False

        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import AddWireCommand
            cmd = AddWireCommand(self, wire, edge, start_t, None)
            main_win.command_manager.push(cmd)
        if main_win and hasattr(main_win, 'statusBar'):
            main_win.statusBar().showMessage(
                f"✔ Bifurcación en T creada en ({int(junction_pt.x())}, {int(junction_pt.y())})"
            )
        return wire

    def create_wire_between_points(
        self,
        pt1: QPointF,
        pt2: QPointF,
        t1=None,
        t2=None,
        wire_type: Any = None,
        color: Optional[str] = None
    ) -> WireItem:
        """Crear cable entre dos puntos o bornes con tipo y color técnico específico"""
        k1 = (round(pt1.x(), 1), round(pt1.y(), 1))
        k2 = (round(pt2.x(), 1), round(pt2.y(), 1))

        if t1 and t1.graph_node_id:
            n1_id = t1.graph_node_id
            self.junction_nodes[k1] = n1_id
        elif k1 in self.junction_nodes:
            n1_id = self.junction_nodes[k1]
            if t1:
                t1.graph_node_id = n1_id
        else:
            n1 = Node(node_type=NodeType.JUNCTION)
            n1_id = self.circuit_graph.add_node(n1)
            self.junction_nodes[k1] = n1_id
            if t1:
                t1.graph_node_id = n1_id

        if t2 and t2.graph_node_id:
            n2_id = t2.graph_node_id
            self.junction_nodes[k2] = n2_id
        elif k2 in self.junction_nodes:
            n2_id = self.junction_nodes[k2]
            if t2:
                t2.graph_node_id = n2_id
        else:
            n2 = Node(node_type=NodeType.JUNCTION)
            n2_id = self.circuit_graph.add_node(n2)
            self.junction_nodes[k2] = n2_id
            if t2:
                t2.graph_node_id = n2_id

        edge = Edge(
            node1_id=n1_id,
            node2_id=n2_id,
            terminal1_id=t1.terminal_id if t1 else None,
            terminal2_id=t2.terminal_id if t2 else None,
            component_id=None
        )
        self.circuit_graph.add_edge(edge)

        wt = wire_type if wire_type is not None else self.current_wire_type
        wc = color if color is not None else (self.current_wire_color if wire_type is None else None)

        wire = WireItem(terminal1=t1, terminal2=t2, pt1=pt1, pt2=pt2, wire_type=wt, color=wc)
        wire.edge_id = edge.id
        self.addItem(wire)
        self.wires.append(wire)

        if t1:
            t1.connected_wires.append(wire)
        if t2:
            t2.connected_wires.append(wire)

        return wire

    # ── GESTIÓN DE EVENTOS DE RATÓN Y TECLADO ─────────────────────────────────

    def mouseMoveEvent(self, event):
        pos = event.scenePos()
        self.cursor_moved.emit(pos.x(), pos.y())

        # 1. Modo inserción: actualizar la posición del componente fantasma
        if self.placement_mode and self.preview_item:
            GRID = 20.0
            snap_x = round(pos.x() / GRID) * GRID
            snap_y = round(pos.y() / GRID) * GRID
            self.preview_item.setPos(snap_x, snap_y)

        # 2. Modo cablear: actualizar extremo dinámico del cable
        if self.wiring_mode and self.temp_wire and self.start_terminal:
            self.temp_wire.set_temp_end(pos)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        # 1. Modo inserción activo
        if self.placement_mode:
            if event.button() == Qt.LeftButton:
                self.place_current_component(event.scenePos())
                event.accept()
                return
            elif event.button() == Qt.RightButton:
                self.cancel_placement()
                event.accept()
                return

        # 2. Modo cablear activo
        if self.wiring_mode:
            GRID = 20.0
            pos = event.scenePos()
            snap_x = round(pos.x() / GRID) * GRID
            snap_y = round(pos.y() / GRID) * GRID
            snap_pt = QPointF(snap_x, snap_y)

            if event.button() == Qt.LeftButton:
                items = self.items(pos)

                # A) Clic sobre un borne / terminal de destino válido
                for item in items:
                    from .terminal_item import TerminalItem
                    if isinstance(item, TerminalItem) and item != self.start_terminal:
                        self.finish_wire(item)
                        event.accept()
                        return

                # B) Clic sobre otro cable existente para crear una bifurcación / derivación en T
                for item in items:
                    from .wire_item import WireItem
                    if isinstance(item, WireItem) and item != self.temp_wire:
                        self.finish_wire_to_wire(item, snap_pt)
                        event.accept()
                        return

                # C) Clic en el lienzo libre: AGREGAR NODO / WAYPOINT DE PASO INTERMEDIO
                if self.temp_wire:
                    self.temp_wire.add_waypoint(snap_pt)
                    main_win = self._get_main_window()
                    if main_win and hasattr(main_win, 'statusBar'):
                        wp_count = len(self.temp_wire.waypoints)
                        main_win.statusBar().showMessage(
                            f"📍 Nodo {wp_count} fijado en ({int(snap_x)}, {int(snap_y)}). "
                            f"Haga clic en otro punto para continuar la ruta, en un borne o cable para finalizar | ESC/Clic der. para deshacer nodo."
                        )
                    event.accept()
                    return

            elif event.button() == Qt.RightButton:
                # Clic derecho: Deshacer último waypoint o cancelar cableado
                if self.temp_wire and self.temp_wire.waypoints:
                    self.temp_wire.pop_waypoint()
                    main_win = self._get_main_window()
                    if main_win and hasattr(main_win, 'statusBar'):
                        main_win.statusBar().showMessage("↩ Último nodo de cable deshecho.")
                    event.accept()
                    return
                else:
                    self.cancel_wire()
                    event.accept()
                    return

        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """
        Manejar teclas de navegación y control:
        - ESC: Salir del modo de inserción o deshacer nodo de cableado.
        - Delete / Backspace: Eliminar elementos seleccionados.
        """
        if event.key() == Qt.Key_Escape:
            if self.placement_mode:
                self.cancel_placement()
                event.accept()
                return
            if self.wiring_mode:
                if self.temp_wire and self.temp_wire.waypoints:
                    self.temp_wire.pop_waypoint()
                    main_win = self._get_main_window()
                    if main_win and hasattr(main_win, 'statusBar'):
                        main_win.statusBar().showMessage("↩ Último nodo de cable deshecho (ESC).")
                    event.accept()
                    return
                self.cancel_wire()
                event.accept()
                return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected_items()
            event.accept()
            return

        super().keyPressEvent(event)

    # ── ELIMINACIÓN DE COMPONENTES Y CABLES ────────────────────────────────────

    def delete_selected_items(self):
        """Elimina todos los componentes y cables seleccionados con registro atómico en Undo/Redo."""
        selected = list(self.selectedItems())
        if not selected:
            return

        from .component_item import ComponentItem
        from .wire_item import WireItem

        components = [item for item in selected if isinstance(item, ComponentItem) and not getattr(item, 'is_preview', False)]
        wires = [item for item in selected if isinstance(item, WireItem)]

        if not components and not wires:
            return

        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import RemoveMultipleItemsCommand
            cmd = RemoveMultipleItemsCommand(self, components, wires)
            main_win.command_manager.push(cmd)
        else:
            for c in components:
                self.remove_component_with_undo(c)
            for w in wires:
                self.remove_wire_with_undo(w)

        if main_win and hasattr(main_win, 'statusBar'):
            main_win.statusBar().showMessage(
                f"Eliminados {len(components)} componentes y {len(wires)} cables. (Ctrl+Z para deshacer)"
            )

    def remove_component_with_undo(self, comp):
        """Eliminar un componente con registro en el CommandManager para Undo"""
        if getattr(comp, 'is_preview', False):
            self.removeItem(comp)
            return

        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import RemoveComponentCommand
            cmd = RemoveComponentCommand(self, comp)
            main_win.command_manager.push(cmd)
        else:
            self.removeItem(comp)
            self.circuit_graph.remove_component(comp.id)

    def remove_wire_with_undo(self, wire):
        """Eliminar un cable con registro en el CommandManager para Undo"""
        main_win = self._get_main_window()
        if main_win and hasattr(main_win, 'command_manager'):
            from ..core.commands import RemoveWireCommand
            cmd = RemoveWireCommand(self, wire)
            main_win.command_manager.push(cmd)
        else:
            self.removeItem(wire)
            if wire in self.wires:
                self.wires.remove(wire)
            if wire.edge_id:
                self.circuit_graph.remove_edge(wire.edge_id)

    # ── MÉTODOS AUXILIARES Y COMPONENTES ──────────────────────────────────────

    def _get_main_window(self):
        """Localizar la ventana principal MainWindow."""
        main_win = self.parent()
        if not main_win:
            views = self.views()
            if views:
                main_win = views[0].window()
        return main_win

    def update_connected_wires(self, component):
        """Actualizar geometría de cables conectados al mover un componente"""
        for term in getattr(component, 'terminals', []):
            for wire in getattr(term, 'connected_wires', []):
                wire.update_positions()

    def add_component(self, component_item):
        """Añadir componente a la escena y configurar sus nodos/aristas en el grafo relacional"""
        if component_item.scene() != self:
            self.addItem(component_item)
        self.circuit_graph.add_component(component_item)

        is_power = (component_item.component_type == 'power')
        is_neutral = (component_item.component_type == 'neutral')

        for term in component_item.terminals:
            if is_power:
                node = Node(
                    node_type=NodeType.POWER_RAIL,
                    potential=230.0,
                    potential_known=True,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )
            elif is_neutral:
                node = Node(
                    node_type=NodeType.NEUTRAL,
                    potential=0.0,
                    potential_known=True,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )
            else:
                node = Node(
                    node_type=NodeType.TERMINAL,
                    name=f"{component_item.tag}:{term.terminal_id}"
                )

            node_id = self.circuit_graph.add_node(node)
            term.graph_node_id = node_id

        logic = component_item.component_def.get('logic', {})
        internal_conns = logic.get('internal_connections', [])

        if not internal_conns and len(component_item.terminals) == 2 and component_item.component_type != 'power':
            t1 = component_item.terminals[0].terminal_id
            t2 = component_item.terminals[1].terminal_id
            internal_conns = [(t1, t2)]

        for t1_id, t2_id in internal_conns:
            term1 = component_item.get_terminal_by_id(t1_id)
            term2 = component_item.get_terminal_by_id(t2_id)
            if term1 and term2 and term1.graph_node_id and term2.graph_node_id:
                edge = Edge(
                    node1_id=term1.graph_node_id,
                    node2_id=term2.graph_node_id,
                    terminal1_id=t1_id,
                    terminal2_id=t2_id,
                    component_id=component_item.id
                )
                self.circuit_graph.add_edge(edge)

    def update_simulation_visuals(self):
        """Actualizar el color de los cables y el estado de componentes durante la simulación"""
        for wire in self.wires:
            wire.update_simulation_state(self.circuit_graph)
        for comp in self.circuit_graph.components.values():
            if hasattr(comp, 'update_visual'):
                comp.update_visual()

    def clear_circuit(self):
        """Limpiar completamente la escena y el grafo"""
        self.cancel_placement()
        self.cancel_wire()
        self.clear()
        self.wires.clear()
        self.junction_nodes.clear()
        self.circuit_graph = CircuitGraph()

    def show_component_properties(self, component):
        """Abrir el diálogo de edición de propiedades del componente"""
        from ..ui.component_properties_dialog import ComponentPropertiesDialog
        parent = self._get_main_window()
        dlg = ComponentPropertiesDialog(component, parent)
        dlg.exec()

    def connect_terminals(self, t1, t2) -> WireItem:
        """Conectar dos bornes directamente y crear su wire y arista"""
        self.start_terminal = t1
        return self.finish_wire(t2)
