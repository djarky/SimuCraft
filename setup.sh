#!/bin/bash

# SimuCraft Setup Script
VENV_DIR="venv"

echo "=========================================="
echo "  SimuCraft - Setup"
echo "=========================================="

# Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
else
    echo "[*] Entorno virtual ya existe"
fi

# Activar entorno virtual
echo "[*] Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# Actualizar pip
echo "[*] Actualizando pip..."
pip install --upgrade pip -q

# Instalar dependencias
echo "[*] Instalando dependencias..."
pip install -q PySide6>=6.6.0 pydantic>=2.0.0 lxml>=4.9.0 Pillow>=10.0.0 networkx>=3.0 numpy>=1.24.0 rich>=13.0.0 click>=8.1.0

echo ""
echo "=========================================="
echo "  Setup completado!"
echo "=========================================="
echo ""
echo "Para ejecutar: ./run.sh"
echo ""

deactivate
