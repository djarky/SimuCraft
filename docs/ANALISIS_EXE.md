# Análisis del ejecutable CADe_SIMU_V4.2.exe

## Información general
- Archivo: `cadesimu/CADe_SIMU V4.2/CADe_SIMU_V4.2.exe`
- Formato: PE32 (i386), Win32
- Tamaño: ~40MB
- Compilado con MFC42D (Microsoft Foundation Classes)
- Usa libnodave.dll (comunicación con Siemens PLC)
- Muchas secciones, muchos recursos (.rsrc 30MB+)

## Strings encontrados relacionados con el motor

### Elementos del esquema
- Contacto NA/NC, Contacto final de carrera, Contacto interruptor/pulsador
- Contactor, Relé, Bobina monoestable/biestable
- Temporizadores: "Temporizador a la conexión", "Temporizador a la desconexión", "Temporizador intermitente"
- Contacts ON Delay / OFF Delay
- Disyuntor, Relé térmico
- Lógicas: AND, OR, NAND, NOR, EXOR, INV
- Contadores, GRAFCET

### Direcciones/Tags estilo PLC
- Entradas: I0.0, I1.0, ..., Q0.0 (salidas estilo S7)
- "Q1234 RUN", referencias a bornes

### Clases MFC detectadas
- `CCADe_SIMUDoc` - Documento
- `CCADe_SIMUView` - Vista

## Hipótesis sobre arquitectura
1. **Basado en MFC Document/View** - típico de apps Windows antiguas
2. **Motor de simulación separado** - probablemente en clases custom no con nombres obvios
3. **Usa lista/array para elementos** - MFC CList/CArray común
4. **Sin strings obvias de "Scan"** - puede estar ofuscado o con nombres cortos
5. **Recursos enormes** - iconos, bitmaps, menús

## Resultados de extracción con REA (Reverse Engineer Anything)
Mediante la herramienta `rea inspect-pe-resources` se inspeccionaron los recursos del ejecutable PE32:
- **String Tables (RT_STRING / ID 6)**: 153 bloques de strings UTF-16LE extraídos con todos los tooltips, textos de estado y nombres de comandos MFC (rango `32770` a `33500`).
- **Toolbars (RT_TOOLBAR / ID 241)**: 65 barras de herramientas que agrupan los botones de cada familia:
- Toolbar 173: Motores (14 botones)
- Toolbar 175: Contactores e interruptores de potencia (10 botones)
- Toolbar 177: Fusibles y seccionadores fusibles (10 botones)
- Toolbar 179: Automáticos, disyuntores y diferenciales (15 botones)
- Toolbar 183: Alimentaciones, transformadores y rectificadores (21 botones)
- Toolbar 187: Conductores, cables y conexiones (25 botones)
- Toolbar 189: Accionamientos: pulsadores, interruptores, finales de carrera (24 botones)
- Toolbar 191: Contactos auxiliares y temporizados (16 botones)
- Toolbar 193: Bobinas, temporizadores y señalización luminosa/acústica (17 botones)
- Toolbar 213: Potencia electrónica, arrancadores, variadores y paso a paso (17 botones)
- Toolbar 215: Sensores y detectores inductivos, capacitivos, ópticos, presión (16 botones)
- Toolbar 226: Lógica digital (27 botones)
- Toolbar 228: GRAFCET (14 botones)
- Toolbar 242: E/S digitales y PLCs (17 botones)
- Toolbar 269: Actuadores neumáticos (10 botones)
- Toolbar 291: Relés electrónicos y protección de fase (12 botones)
- Toolbar 292: Ladder (21 botones)
- Toolbar 301 / 307: Símbolos 2D y 3D (23 botones c/u)
### Correlación 1:1 con archivos .CAD de ejemplo
Al comparar la secuencia de comandos en las toolbars con los esquemas completos (`all_simbol.cad`, `allpart2.cad`, `all4.cad`, `all5.cad`, etc.), se descubrió una correlación 1:1 exacta en el orden de colocación:
- `3000..3020` -> Toolbar 183 (Alimentaciones)
- `5000..5009` -> Toolbar 177 (Fusibles)
- `6000..6014` -> Toolbar 179 (Automáticos / Disyuntores)
- `2000..2009` -> Toolbar 175 (Contactores)
- `1000..1012, 10550` -> Toolbar 173 (Motores)
- `1050..1067` -> Toolbar 269 (Neumática)
- `7000..7015` -> Toolbar 191 (Contactos)
- `8000..8023` -> Toolbar 189 (Accionamientos)
- `7500..7600` -> Toolbar 215 (Detectores)
- `9000..9016` -> Toolbar 193 (Bobinas y Señalización)
- `1070..1075, 9040..9045` -> Toolbar 213 (Potencia y Control Variadores)
- `10000..10083` -> Toolbar 226 & 292 (Lógica digital y Ladder)
- `10100..10112` -> Toolbar 228 (GRAFCET)
- `10200..10220` -> Toolbar 242 (PLCs: LOGO, S7-1200, S7-1500, ET-200, Arduino)
- `20000` -> Cajetín / Rotulación
Catálogo maestro exportado en:
- `TABLA_SIMBOLOS_CADESIMU.md`
- `cadesimu_symbols_complete.csv`
- `cadesimu_symbols_complete.json`
- `cadesimu_symbol_catalog_detailed.json`
## Comparación con lo que queremos hacer
El original tiene fallas que queremos evitar:
- Conexiones por coordenadas pixel (queremos grafo relacional)
- Tags manuales (queremos auto-nombrado)
- Undo corrompe (queremos Command pattern)
Nuestro enfoque con QElectroTech + grafo relacional es correcto.
