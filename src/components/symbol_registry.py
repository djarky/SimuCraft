"""Registro persistente de símbolos de SimuCraft.

Fuente de verdad:
- ``data/symbols/standard_symbols.json``: builtins editables.
- ``data/symbols/custom_symbols.json``: símbolos nuevos marcados como ``CUSTOM``.

``data/custom_symbols.json`` se mantiene como archivo legado de migración.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = PROJECT_ROOT / "data" / "symbols"
STANDARD_PATH = REGISTRY_DIR / "standard_symbols.json"
CUSTOM_PATH = REGISTRY_DIR / "custom_symbols.json"
LEGACY_CUSTOM_PATH = PROJECT_ROOT / "data" / "custom_symbols.json"

SCHEMA_VERSION = 1
CUSTOM_TAG = "CUSTOM"


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # pragma: no cover - aviso defensivo
        print(f"Aviso: no se pudo leer {path}: {exc}")
        return None


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, path)


def _read_symbol_map(path: Path) -> Dict[str, Dict[str, Any]]:
    data = _read_json(path)
    if not isinstance(data, dict):
        return {}
    symbols = data.get("symbols")
    if isinstance(symbols, dict):
        return {k: v for k, v in symbols.items() if isinstance(v, dict)}
    # Compatibilidad con el formato plano anterior.
    return {k: v for k, v in data.items() if isinstance(v, dict) and not k.startswith("_")}


def _write_symbol_map(path: Path, symbols: Dict[str, Dict[str, Any]], kind: str) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "symbols": symbols,
    }
    _atomic_write_json(path, payload)


def read_legacy_custom_symbols() -> Dict[str, Dict[str, Any]]:
    """Lee ``data/custom_symbols.json`` sin modificar su formato legado."""
    return _read_symbol_map(LEGACY_CUSTOM_PATH)


def _builtin_ids() -> set[str]:
    # Import perezoso para evitar el ciclo standard_components -> symbol_registry.
    from . import standard_components as sc

    return set(getattr(sc, "_BUILTIN_DEFAULTS", {}).keys())


def is_custom(symbol: Dict[str, Any]) -> bool:
    """Devuelve True si el símbolo es un CUSTOM y no un builtin."""
    if not isinstance(symbol, dict):
        return False
    tags = [str(t).upper() for t in symbol.get("tags", [])]
    return bool(symbol.get("custom")) or symbol.get("origin") == "custom" or CUSTOM_TAG in tags


def normalize_standard_symbol(symbol: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un builtin para que nunca lleve marcas de CUSTOM."""
    sym = copy.deepcopy(symbol)
    sym["origin"] = "builtin"
    sym.pop("custom", None)
    tags = sym.get("tags")
    if isinstance(tags, list):
        clean_tags = [t for t in tags if str(t).upper() != CUSTOM_TAG]
        if clean_tags:
            sym["tags"] = clean_tags
        else:
            sym.pop("tags", None)
    return sym


def normalize_custom_symbol(symbol: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza un símbolo nuevo con ``custom``, ``origin`` y etiqueta ``CUSTOM``."""
    sym = copy.deepcopy(symbol)
    sym["custom"] = True
    sym["origin"] = "custom"
    tags = [str(t) for t in sym.get("tags", []) if str(t).strip()]
    if not any(t.upper() == CUSTOM_TAG for t in tags):
        tags.append(CUSTOM_TAG)
    sym["tags"] = tags
    return sym


def validate_symbol(symbol: Dict[str, Any]) -> List[str]:
    """Valida el esquema mínimo de un símbolo y sus terminales."""
    errors: List[str] = []
    if not isinstance(symbol, dict):
        return ["El símbolo debe ser un objeto JSON"]

    if not isinstance(symbol.get("id"), str) or not symbol.get("id", "").strip():
        errors.append("Falta 'id' o no es texto")
    if not isinstance(symbol.get("type"), str) or not symbol.get("type", "").strip():
        errors.append("Falta 'type' o no es texto")
    if not isinstance(symbol.get("name"), str) or not symbol.get("name", "").strip():
        errors.append("Falta 'name' o no es texto")

    visual = symbol.get("visual")
    if not isinstance(visual, dict):
        errors.append("Falta 'visual' o no es un objeto")
    else:
        for key in ("width", "height"):
            try:
                value = float(visual.get(key))
            except (TypeError, ValueError):
                errors.append(f"'visual.{key}' no es numérico")
            else:
                if value <= 0:
                    errors.append(f"'visual.{key}' debe ser mayor que cero")

        terminals = visual.get("terminals")
        if not isinstance(terminals, list):
            errors.append("'visual.terminals' debe ser una lista")
        else:
            for index, terminal in enumerate(terminals):
                if not isinstance(terminal, dict):
                    errors.append(f"'visual.terminals[{index}]' no es un objeto")
                    continue
                for key in ("id", "name", "orientation"):
                    if not str(terminal.get(key, "")).strip():
                        errors.append(f"'visual.terminals[{index}].{key}' está vacío")
                for key in ("x", "y"):
                    try:
                        float(terminal.get(key))
                    except (TypeError, ValueError):
                        errors.append(f"'visual.terminals[{index}].{key}' no es numérico")

    logic = symbol.get("logic")
    if logic is not None and not isinstance(logic, dict):
        errors.append("'logic' debe ser un objeto")

    if symbol.get("custom") is True:
        tags = [str(t).upper() for t in symbol.get("tags", [])]
        if CUSTOM_TAG not in tags:
            errors.append("Un símbolo custom debe tener la etiqueta 'CUSTOM'")
        if symbol.get("origin") != "custom":
            errors.append("Un símbolo custom debe tener origin='custom'")

    return errors


def load_standard_symbols() -> Dict[str, Dict[str, Any]]:
    """Carga los builtins editables desde el registro estándar."""
    return _read_symbol_map(STANDARD_PATH)


def load_custom_symbols() -> Dict[str, Dict[str, Any]]:
    """Carga los símbolos nuevos desde el registro CUSTOM."""
    symbols = _read_symbol_map(CUSTOM_PATH)
    return {key: normalize_custom_symbol(sym) for key, sym in symbols.items()}


def load_all_symbols() -> Dict[str, Dict[str, Any]]:
    """Carga estándar + custom, sin permitir que un custom pise un builtin."""
    standard = load_standard_symbols()
    merged: Dict[str, Dict[str, Any]] = dict(standard)
    builtin_ids = _builtin_ids()
    for key, sym in load_custom_symbols().items():
        if key in builtin_ids or key in merged:
            continue
        merged[key] = sym
    return merged


def save_standard_symbol(symbol: Dict[str, Any]) -> None:
    """Guarda/sobrescribe un builtin en ``standard_symbols.json``."""
    if is_custom(symbol):
        raise ValueError(
            "Un símbolo estándar no puede tener custom=True ni la etiqueta CUSTOM"
        )
    sym = normalize_standard_symbol(symbol)
    symbol_id = sym.get("id")
    if not symbol_id:
        raise ValueError("El símbolo no tiene 'id'")
    builtin_ids = _builtin_ids()
    if builtin_ids and symbol_id not in builtin_ids:
        raise ValueError(
            f"'{symbol_id}' no es un símbolo estándar. Usa save_custom_symbol() para crear un CUSTOM."
        )
    errors = validate_symbol(sym)
    if errors:
        raise ValueError("; ".join(errors))

    symbols = load_standard_symbols()
    symbols[symbol_id] = sym
    _write_symbol_map(STANDARD_PATH, symbols, "standard")
    merge_into_standard_components()


def save_custom_symbol(symbol: Dict[str, Any]) -> None:
    """Guarda/sobrescribe un símbolo nuevo en ``custom_symbols.json``."""
    sym = normalize_custom_symbol(symbol)
    symbol_id = sym.get("id")
    if not symbol_id:
        raise ValueError("El símbolo no tiene 'id'")
    if symbol_id in _builtin_ids():
        raise ValueError(
            f"'{symbol_id}' es un builtin. Usa save_standard_symbol() para editarlo."
        )
    errors = validate_symbol(sym)
    if errors:
        raise ValueError("; ".join(errors))

    symbols = load_custom_symbols()
    symbols[symbol_id] = sym
    _write_symbol_map(CUSTOM_PATH, symbols, "custom")
    merge_into_standard_components()


def merge_into_standard_components() -> None:
    """Vuelca el registro en ``standard_components.STANDARD_COMPONENTS``."""
    from . import standard_components as sc

    merged: Dict[str, Dict[str, Any]] = {
        key: normalize_standard_symbol(value)
        for key, value in copy.deepcopy(sc._BUILTIN_DEFAULTS).items()
    }

    for key, symbol in load_standard_symbols().items():
        merged[key] = normalize_standard_symbol(symbol)

    for key, symbol in load_custom_symbols().items():
        if key in sc._BUILTIN_COMPONENTS:
            print(f"Aviso: el símbolo custom '{key}' colisiona con un builtin; se ignora")
            continue
        merged[key] = normalize_custom_symbol(symbol)

    sc.STANDARD_COMPONENTS.clear()
    sc.STANDARD_COMPONENTS.update(merged)


def _legacy_standard_overrides(builtin_defaults: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    overrides: Dict[str, Dict[str, Any]] = {}
    for key, symbol in read_legacy_custom_symbols().items():
        if key in builtin_defaults:
            overrides[key] = copy.deepcopy(symbol)
    return overrides


def _legacy_customs(builtin_defaults: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    customs: Dict[str, Dict[str, Any]] = {}
    for key, symbol in read_legacy_custom_symbols().items():
        if key in builtin_defaults:
            continue
        customs[key] = normalize_custom_symbol(symbol)
    return customs


def ensure_registry(builtin_defaults: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Crea los registros si no existen (bootstrap).

    No renderiza SVG: eso lo hace ``tools/migrate_symbols_to_registry.py``.
    """
    if builtin_defaults is None:
        from . import standard_components as sc

        builtin_defaults = sc._BUILTIN_DEFAULTS

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    standard = load_standard_symbols()
    if not standard:
        standard = {
            key: normalize_standard_symbol(symbol)
            for key, symbol in copy.deepcopy(builtin_defaults).items()
        }
        for key, override in _legacy_standard_overrides(builtin_defaults).items():
            standard[key] = normalize_standard_symbol(override)
        _write_symbol_map(STANDARD_PATH, standard, "standard")
    else:
        changed = False
        for key, symbol in builtin_defaults.items():
            if key not in standard:
                standard[key] = normalize_standard_symbol(symbol)
                changed = True
        if changed:
            _write_symbol_map(STANDARD_PATH, standard, "standard")

    custom = load_custom_symbols()
    if not custom:
        custom = _legacy_customs(builtin_defaults)
        _write_symbol_map(CUSTOM_PATH, custom, "custom")
