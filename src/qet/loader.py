"""
Cargador de símbolos QElectroTech
"""
import os
from typing import Dict, Optional
from .parser import QETParser


class QETLoader:
    def __init__(self, symbol_dirs: list = None):
        self.symbol_dirs = symbol_dirs or []
        self.cache: Dict[str, dict] = {}
        self.parser = QETParser()
        
    def add_directory(self, directory: str):
        if os.path.isdir(directory) and directory not in self.symbol_dirs:
            self.symbol_dirs.append(directory)
            
    def load_symbol(self, name: str) -> Optional[dict]:
        if name in self.cache:
            return self.cache[name]
        
        for symbol_dir in self.symbol_dirs:
            # Buscar por nombre exacto
            path = os.path.join(symbol_dir, f"{name}.elmt")
            if os.path.exists(path):
                defn = self.parser.create_component_definition(path)
                self.cache[name] = defn
                return defn
            
            # Buscar recursivamente
            for root, dirs, files in os.walk(symbol_dir):
                for f in files:
                    if f == f"{name}.elmt" or f.endswith(f"{name}.elmt"):
                        path = os.path.join(root, f)
                        defn = self.parser.create_component_definition(path)
                        self.cache[name] = defn
                        return defn
        
        return None
    
    def scan_available(self) -> list:
        """Escanear símbolos disponibles"""
        available = []
        for symbol_dir in self.symbol_dirs:
            if not os.path.isdir(symbol_dir):
                continue
            for root, dirs, files in os.walk(symbol_dir):
                for f in files:
                    if f.endswith('.elmt'):
                        rel = os.path.relpath(os.path.join(root, f), symbol_dir)
                        available.append(rel.replace('.elmt', ''))
        return sorted(set(available))
