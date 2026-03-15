"""
AppKS - Launcher
Ejecuta la app Streamlit usando el intérprete Python del entorno virtual del proyecto.

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
    # Directorio raíz del proyecto (donde está el .exe o el script)
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent

    os.chdir(base_dir)

    # Verificar que run.py existe
    run_py = base_dir / "run.py"
    if not run_py.exists():
        show_error(
            f"No se encontró run.py en:\n{base_dir}\n\n"
            "Asegúrate de que AppKS.exe esté en la carpeta raíz del proyecto."
        )
        sys.exit(1)

    # Verificar que el entorno virtual existe
    venv_python = base_dir / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        show_error(
            f"No se encontró el entorno virtual en:\n{base_dir / 'venv'}\n\n"
            "Crea el entorno e instala las dependencias con:\n"
            "  python -m venv venv\n"
            "  venv\\Scripts\\activate\n"
            "  pip install -r requirements.txt"
        )
        sys.exit(1)

    # Lanzar: venv\Scripts\python.exe -m streamlit run run.py
    cmd = [str(venv_python), "-m", "streamlit", "run", str(run_py)]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        show_error(f"No se pudo iniciar Streamlit:\n{e}")
        sys.exit(1)

    # Esperar a que Streamlit arranque
    time.sleep(4)

    # Verificar que el proceso sigue en pie antes de abrir el navegador
    if proc.poll() is not None:
        stderr_output = ""
        try:
            _, stderr_bytes = proc.communicate(timeout=2)
            stderr_output = stderr_bytes.decode(errors="replace")
        except Exception:
            pass
        show_error(
            "Streamlit no pudo iniciar.\n\n"
            + (
                f"Detalle:\n{stderr_output}"
                if stderr_output
                else "Revisa que las dependencias estén instaladas en venv\\."
            )
        )
        sys.exit(1)

    webbrowser.open("http://localhost:8501")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
