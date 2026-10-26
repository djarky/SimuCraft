# Convertidor CAD -> SimuCraft

## Uso

```bash
python cad_to_internal.py cadesimu/examples/Lab01.cad salida.json
```

## Funcionamiento

1. Lee archivo .CAD (separado por `*`)
2. Clasifica elementos:
   - `0` → Nodos/junctions
   - `4000-4019` → Cables
   - Símbolos → Mapeados según `cad_qet_mapping.json`
3. Extrae coordenadas y parámetros
4. Genera formato interno JSON para SimuCraft

## Formato salida
```json
{
  "name": "...",
  "nodes": [{"id": "node_0", "type": "junction", "params": [...]}],
  "wires": [{"id": "wire_0", "type_id": "4000", ...}],
  "components": [{
    "id": "comp_0",
    "mapped_type": "pushbutton",
    "qet_file": "...",
    "position": {"x": 36, "y": 108},
    ...
  }]
}
```

## Mapeo actual
Ver `cad_qet_mapping.json` para correspondencias CAD -> QElectroTech
Ver `MAPEADO_FINAL.md` para detalles
