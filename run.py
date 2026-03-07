"""
Launcher para la aplicación AppKS
Ejecutar con: streamlit run run.py
"""
import sys
from pathlib import Path
import runpy

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Ejecutar la aplicación como módulo
runpy.run_module('app.main', run_name='__main__')
