"""
AppKS - Launcher
Ejecuta la app Streamlit usando la instalación Python del proyecto.

Uso directo:   python start_app.py
Como exe:      pyinstaller --onefile --noconsole start_app.py --name AppKS
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def show_error(msg: str) -> None:
    """Muestra un diálogo de error (funciona sin consola ni stdin)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("AppKS - Error", msg)
        root.destroy()
    except Exception:
        pass


def main():
    # Directorio raíz del proyecto (donde está el exe o el script)
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent

    os.chdir(base_dir)

    run_py = base_dir / "run.py"
    if not run_py.exists():
        show_error(f"No se encontró run.py en:\n{base_dir}\n\nAsegúrate de que AppKS.exe esté en la carpeta raíz del proyecto.")
        sys.exit(1)

    # Buscar el ejecutable de streamlit: venv local → PATH
    venv_streamlit = base_dir / "venv" / "Scripts" / "streamlit.exe"
    venv_python    = base_dir / "venv" / "Scripts" / "python.exe"

    if venv_streamlit.exists():
        cmd = [str(venv_streamlit), "run", str(run_py)]
    elif venv_python.exists():
        cmd = [str(venv_python), "-m", "streamlit", "run", str(run_py)]
    else:
        show_error("No se encontró streamlit ni Python en la carpeta venv\\.\n\nInstala las dependencias con:\n  pip install -r requirements.txt")
        sys.exit(1)

    proc = subprocess.Popen(cmd)

    # Dar tiempo a que Streamlit arranque y abrir el navegador
    time.sleep(4)
    webbrowser.open("http://localhost:8501")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
