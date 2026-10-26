#!/bin/bash

# SimuCraft Run Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"

echo "=========================================="
echo "  SimuCraft v0.1.0 (CADe SIMU Clone)"
echo "=========================================="

# Crear venv si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Entorno virtual no encontrado. Ejecutando setup..."
    ./setup.sh
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# Configurar PYTHONPATH para importaciones de módulos
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Configurar plataforma Qt por defecto si no está definida
if [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi

# Ejecutar aplicación
echo "[*] Iniciando SimuCraft..."
exec python -m src.main "$@"
