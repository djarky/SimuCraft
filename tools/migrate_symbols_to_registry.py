#!/usr/bin/env python3
"""Migra los símbolos actuales a ``data/symbols/``.

Uso:
    venv/bin/python tools/migrate_symbols_to_registry.py --dry-run
    venv/bin/python tools/migrate_symbols_to_registry.py --backup

El script es idempotente: si se ejecuta dos veces con los mismos datos de
entrada, produce los mismos registros. No modifica ``data/custom_symbols.json``;
lo usa como fuente legada.
"""
from __future__ import annotations

import argparse
import copy
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

# Debe fijarse antes de importar src.components: evita que el bootstrap escriba
# registros durante un --dry-run.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["SIMUCRAFT_SKIP_REGISTRY_BOOTSTRAP"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.components import standard_components as sc  # noqa: E402
from src.components import symbol_registry as reg  # noqa: E402

_QT_APP = None


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Fusiona ``override`` sobre ``base`` sin perder claves anidadas."""
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def render_canonical_svg(symbol: Dict[str, Any]) -> str:
    """Renderiza un símbolo procedural a SVG vectorial canónico.

    Se pinta directamente el ``ComponentItem`` (sin escena) porque
    ``QGraphicsScene.render`` rasteriza los ``QGraphicsSvgItem`` en un
    ``QSvgGenerator``. Los terminales interactivos se ocultan; las etiquetas
    internas del dibujo (U1, V1, M, etc.) se conservan.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtSvg import QSvgGenerator
    from PySide6.QtCore import QBuffer, QIODevice, QSize
    from PySide6.QtGui import QPainter

    from src.graphics.component_item import ComponentItem

    global _QT_APP
    _QT_APP = QApplication.instance() or QApplication(sys.argv)

    definition = copy.deepcopy(symbol)
    definition["tag"] = ""
    item = ComponentItem(definition)
    item.tag = ""
    item.name = ""
    for terminal in item.terminals:
        terminal.setVisible(False)

    rect = item.boundingRect()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)

    generator = QSvgGenerator()
    generator.setOutputDevice(buffer)
    generator.setResolution(96)
    generator.setSize(
        QSize(
            max(1, int(round(rect.width()))),
            max(1, int(round(rect.height()))),
        )
    )
    generator.setViewBox(rect)
    generator.setTitle(str(symbol.get("id", "symbol")))
    generator.setDescription("SimuCraft canonical symbol")

    painter = QPainter(generator)
    item.paint(painter, None)
    painter.end()
    buffer.close()
    return bytes(buffer.data()).decode("utf-8")


def build_registries(render_svg: bool = True) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, int]]:
    """Construye los diccionarios estándar y custom a partir de los datos actuales."""
    builtin_defaults = copy.deepcopy(sc._BUILTIN_DEFAULTS)
    existing_standard = copy.deepcopy(reg.load_standard_symbols())
    existing_custom = copy.deepcopy(reg.load_custom_symbols())
    legacy = copy.deepcopy(reg.read_legacy_custom_symbols())

    standard: Dict[str, Dict[str, Any]] = {}
    custom: Dict[str, Dict[str, Any]] = dict(existing_custom)
    stats = {"rendered": 0, "existing_svg": 0, "missing_svg": 0}

    # Un registro estándar solo debe contener builtins; lo demás pasa a custom.
    for key, symbol in existing_standard.items():
        if key not in builtin_defaults:
            custom[key] = copy.deepcopy(symbol)

    for key, default in builtin_defaults.items():
        base = copy.deepcopy(default)
        if key in legacy:
            base = _deep_merge(base, legacy[key])
        if key in existing_standard:
            # Las ediciones ya migradas tienen prioridad sobre el archivo legado.
            base = _deep_merge(base, existing_standard[key])
        base = reg.normalize_standard_symbol(base)
        base["id"] = key

        visual = base.setdefault("visual", {})
        if visual.get("svg_content"):
            stats["existing_svg"] += 1
        elif render_svg:
            visual["svg_content"] = render_canonical_svg(base)
            stats["rendered"] += 1
        else:
            stats["missing_svg"] += 1

        standard[key] = base

    # Migrar customs legados que aún no estén en el registro nuevo.
    for key, legacy_symbol in legacy.items():
        if key in builtin_defaults:
            continue
        base = copy.deepcopy(legacy_symbol)
        if key in existing_custom:
            base = _deep_merge(base, existing_custom[key])
        base = reg.normalize_custom_symbol(base)
        base["id"] = key
        visual = base.setdefault("visual", {})
        if not visual.get("svg_content") and not visual.get("elmt_path"):
            if render_svg:
                visual["svg_content"] = render_canonical_svg(base)
                stats["rendered"] += 1
            else:
                stats["missing_svg"] += 1
        custom[key] = base

    # Normalizar todos los customs y quitar builtins que se hayan colado.
    normalized_custom: Dict[str, Dict[str, Any]] = {}
    for key, symbol in custom.items():
        if key in builtin_defaults:
            continue
        normalized_custom[key] = reg.normalize_custom_symbol(symbol)

    return standard, normalized_custom, stats


def make_backup() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "backups" / f"phase1_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    legacy = PROJECT_ROOT / "data" / "custom_symbols.json"
    if legacy.exists():
        shutil.copy2(legacy, backup_dir / legacy.name)

    for rel in ("data/symbols", "data/mappings", "data/catalogs"):
        source = PROJECT_ROOT / rel
        if source.exists():
            shutil.copytree(source, backup_dir / source.name, dirs_exist_ok=True)

    return backup_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Migra los símbolos de SimuCraft al registro JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Calcula y muestra el resultado sin escribir.")
    parser.add_argument("--backup", action="store_true", help="Copia los datos actuales a backups/ antes de escribir.")
    args = parser.parse_args(argv)

    if args.backup and not args.dry_run:
        backup_dir = make_backup()
        print(f"Backup creado en: {backup_dir}")

    standard, custom, stats = build_registries(render_svg=not args.dry_run)

    print(f"Builtins: {len(sc._BUILTIN_DEFAULTS)}")
    print(f"Símbolos estándar: {len(standard)}")
    print(f"Símbolos CUSTOM: {len(custom)}")
    print(f"SVG canónicos renderizados: {stats['rendered']}")
    print(f"SVG ya existentes: {stats['existing_svg']}")
    if stats["missing_svg"]:
        print(f"SVG pendientes (dry-run): {stats['missing_svg']}")

    if args.dry_run:
        print("Dry-run: no se ha escrito ningún archivo.")
        return 0

    reg._write_symbol_map(reg.STANDARD_PATH, standard, "standard")
    reg._write_symbol_map(reg.CUSTOM_PATH, custom, "custom")
    print(f"Escrito: {reg.STANDARD_PATH}")
    print(f"Escrito: {reg.CUSTOM_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
