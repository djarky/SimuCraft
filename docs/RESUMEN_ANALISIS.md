# Resumen del análisis

## Archivos .CAD parseados
- 12 archivos analizados
- Formato: CADe_SIMU con separador *
- Nodos (0): 855, Cables (4000-4019): ~342, Símbolos (6000-9000): ~169

## Símbolos más comunes
8000,8001 - Pulsadores/contactos auxiliares
9000,9008 - Contactos/relés  
6007,6009 - Bobinas/contactores
7000 - Terminales/bornes

## Ejecutable analizado
CADe_SIMU_V4.2.exe (PE32 MFC)
Elementos encontrados: Contacto NA/NC, Contactor, Bobina, Temporizadores ON/OFF Delay, GRAFCET, etc.
Direcciones estilo PLC: I/Q

## SimuCraft creado
Estructura completa con PySide6, grafo relacional, QET parser, motor de simulación, undo/redo
