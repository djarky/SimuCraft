# Mapeo IDs .CAD -> Componentes QElectroTech

Basado en análisis de 12 archivos .CAD

## Clasificación

| IDs | Categoría | Cantidad aprox | Notas |
|---|---|---|---|
| `0` | Nodos/Junctions | 855 | Puntos de conexión |
| `4000,4001,4009,4010,4018,4019` | Cables/Conexiones | ~342 | Líneas entre elementos |
| `6007,6009` | Símbolos anchos | ~25 | Probablemente BOBINAS/CONTACTORES |
| `7000` | Símbolos compactos | ~15 | Bornes/Terminales |
| `8000,8001` | Símbolos pequeños | ~26 | PULSADORES/CONTACTOS AUXILIARES NA/NC |
| `9000,9008` | Símbolos medios | ~36 | CONTACTOS/RELES |
| `1000-1999,20000+` | Auxiliares/Marcos | varios | Marcos, etiquetas, etc. |

## Símbolos prioritarios para SimuCraft

Para el circuito básico que pide el enunciado: "línea de alimentación, pulsador de marcha (NA), bobina de contactor con enclavamiento"

Necesitamos mapear:
- **Alimentación**: línea/bus L1,N o 3 fases
- **Pulsador NA**: buscar equivalente a 8000/8001
- **Contactor con bobina**: buscar equivalente a 6007/6009  
- **Contacto de enclavamiento**: contacto auxiliar NO del mismo contactor

## Parámetros típicos
Los símbolos 6000-9000 tienen ~22 parámetros. Típico:
`[flags..., x, y, ox, oy, w, h, ...]`

Coordenadas x,y van al inicio de la posición en el lienzo original.

## Próximos pasos
1. Cruzar con archivos .elmt que tenemos copiados
2. Buscar en qelectrotech-elements más símbolos para CADe SIMU style
3. Crear parser que lea .CAD y genere nuestro formato interno
4. Usar IDs mapeados para cargar símbolos QElectroTech correctos
