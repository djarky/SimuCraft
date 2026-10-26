# SimuCraft

Clon moderno, mejorado y basado en PySide6 del software clásico "CADe SIMU" para simulación de automatismos electrotécnicos y neumática.

## Características principales

- **Grafo relacional**: Modelo basado en nodos y aristas, no en coordenadas de píxeles. Los cables mantienen conexiones lógicas al mover componentes.
- **Símbolos QElectroTech**: Usa la biblioteca de símbolos vectoriales XML/SVG de QElectroTech sin rediseñar iconos.
- **Motor de simulación en tiempo real**: Resuelve el grafo eléctrico en tiempo real con lógica temporal precisa.
- **Undo/Redo limpio**: Patrón Command con QUndoStack, sin nodos huérfanos o flotantes.
- **Tags inteligentes**: Autonumeración de contactores (KM1, KM2) y vinculación automática de contactos auxiliares.
- **Arquitectura modular**: Separación entre capa visual (SVG) y capa lógica (simulación).

## Estructura

Ver `PLAN_SIMUCRAFT.md` para detalles completos de arquitectura.

## Instalación

```bash
pip install -r requirements.txt
python -m src.main
```

## Ingeniería inversa

El proyecto incluye estrategia para extraer reglas de negocio del binario original `cadesimu/CADe_SIMU V4.2/CADe_SIMU_V4.2.exe` usando REA/Ghidra cuando estén disponibles.
