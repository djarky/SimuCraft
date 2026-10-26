# Mapeo CAD -> SimuCraft / QElectroTech (Definitivo)

Extracción y verificación realizada con **REA** sobre `CADe_SIMU_V4.2.exe` y validación cruzada con todos los esquemas `.cad` de ejemplo en `cadesimu/examples/`.

> [!IMPORTANT]
> **Correcciones clave respecto a la hipótesis inicial provisional:**
> - `9000` **NO** es contacto: es la **Bobina de contactor/relé** (`A1-A2`).
> - `7000` **NO** es borne: es el **Contacto auxiliar normalmente abierto (NA)** (`13-14`).
> - `9008` **NO** es contacto auxiliar: es la **Lámpara piloto de señalización** (`X1-X2`).
> - `6007` **NO** es bobina: es el bloque de potencia del **Relé Térmico** (3 bimetales).
> - `6009` / `6011`: es el **Disyuntor / Guardamotor magnetotérmico de potencia** (`1-3-5 / 2-4-6`).
> - `2001`: es el **Contactor de potencia tripolar** (`1-3-5 / 2-4-6`).
> - `1000`: es el **Motor trifásico** (`U1-V1-W1-PE`).
> - `8000`: es el **Pulsador NA** (`13-14` / marcha).
> - `8001`: es el **Pulsador NC** (`11-12` / paro).
> - `8016` / `8017`: Contactos auxiliares de disparo del relé térmico (`97-98` NA señalización y `95-96` NC corte).

---

## Componentes Clave del Circuito Básico de Arranque y Maniobra

| ID CAD | Nombre Original CADe SIMU | Función Real | Tag Típico | Bornes / Terminales | Candidato QElectroTech | Estado en SimuCraft |
|---|---|---|---|---|---|---|
| **3004** | Alimentación L1+L2+L3 | Alimentación trifásica | `-X` | `L1, L2, L3` | `source/tri.elmt` | Listo |
| **3003** | Alimentación F+N | Alimentación monofásica | `-X` | `L, N` | `source/mono.elmt` | Listo |
| **3002** | Alimentación Protección | Borne tierra / PE | `-X` | `PE` | `borne-terre.elmt` | Listo |
| **6011** / **6009** | Disyuntor III | Guardamotor / Disyuntor | `-Q` | `1, 3, 5, 2, 4, 6` | `disjoncteur_moteur.elmt` | Mapeado |
| **2001** | Contactor III | Contactos principales potencia | `-KM` | `1, 3, 5, 2, 4, 6` | `contacteur_puissance.elmt` | Listo |
| **6007** | Relé Térmico | Bimetales térmicos potencia | `-F` | `1, 3, 5, 2, 4, 6` | `relais_thermique.elmt` | Mapeado |
| **1000** | Motor trifásico | Motor asíncrono trifásico | `-M` | `U1, V1, W1, PE` | `moteur_tri.elmt` | Listo |
| **8001** | Pulsador NC | Pulsador de Paro (NC) | `-S` | `11, 12` | `bouton_poussoir.elmt` (NC) | Listo |
| **8000** | Pulsador NA | Pulsador de Marcha (NA) | `-S` | `13, 14` | `71105013_bouton_poussoir.elmt` | Listo |
| **7000** | Contacto NA | Contacto enclavamiento NO | `-KM` | `13, 14` | `contact_simple_na.elmt` | Listo |
| **7001** | Contacto NC | Contacto auxiliar NC | `-KM` | `11, 12` | `contact_simple_nc.elmt` | Listo |
| **9000** | Bobina | Bobina relé/contactor | `-KM` | `A1, A2` | `bobine_relais.elmt` | Listo |
| **9008** | Piloto señalización | Lámpara señalización | `-H` | `X1, X2` | `voyant.elmt` | Listo |
| **8017** | Térmico NC | Contacto paro disparo térmico | `-F` | `95, 96` | `contact_thermique_nc.elmt` | Listo |
| **8016** | Térmico NA | Contacto alarma disparo térmico| `-F` | `97, 98` | `contact_thermique_na.elmt` | Listo |
| **4000** / **4018** | Cable fase / Conexión | Conductor y nodo unión | - | - | Cableado interno | Listo |

---

## Archivos de Catálogo Generados
- Tabla completa y detallada por familias: [TABLA_SIMBOLOS_CADESIMU.md](file:///home/vibecode/DevS/SimuCraft/TABLA_SIMBOLOS_CADESIMU.md)
- Catálogo en CSV: [cadesimu_symbols_complete.csv](file:///home/vibecode/DevS/SimuCraft/cadesimu_symbols_complete.csv)
- Catálogo en JSON: [cadesimu_symbols_complete.json](file:///home/vibecode/DevS/SimuCraft/cadesimu_symbols_complete.json)
