"""
AppKS - Launcher / Auto-Bootstrapper
Detecta si existe el entorno virtual; si no, lo crea e instala dependencias
automáticamente antes de lanzar la app Streamlit.

Uso directo:   python start_app.py
Como exe:      pyinstaller --onefile start_app.py --name AppKS
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Número máximo de intentos para instalar dependencias
MAX_INSTALL_RETRIES = 2

# Versiones de Python a buscar en rutas absolutas de Windows (sin PATH)
_WIN_PYTHON_VERSIONS = ["313", "312", "311", "310", "39", "38"]


# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------


def print_step(msg: str) -> None:
    """Imprime un mensaje de progreso en consola con separador visual."""
    print(f"\n  >>> {msg}", flush=True)


def print_info(msg: str) -> None:
    """Imprime una línea informativa secundaria."""
    print(f"      {msg}", flush=True)


def show_error_dialog(msg: str) -> None:
    """
    Muestra un diálogo de error gráfico usando tkinter.
    Fallback silencioso si tkinter no está disponible (ej. servidor headless).
    """
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("AppKS - Error", msg)
        root.destroy()
    except Exception:
        pass  # Sin entorno gráfico: el mensaje de consola es suficiente


def wait_for_enter() -> None:
    """Espera ENTER del usuario; silencioso si no hay stdin (modo .exe sin consola)."""
    try:
        input("\n  Presiona ENTER para cerrar...")
    except (EOFError, OSError):
        pass


def fatal(msg: str) -> None:
    """
    Muestra error en consola y diálogo gráfico, espera ENTER y termina el proceso.
    Mantiene la ventana abierta para que el usuario pueda leer el error.
    """
    separator = "-" * 50
    print(f"\n{separator}", flush=True)
    print(f"  [ERROR]\n", flush=True)
    # Indentar cada línea del mensaje para mejor legibilidad
    for line in msg.splitlines():
        print(f"  {line}", flush=True)
    print(f"{separator}", flush=True)
    show_error_dialog(msg)
    wait_for_enter()
    sys.exit(1)


# ---------------------------------------------------------------------------
# Resolución de ruta base (compatible con PyInstaller --onefile)
# ---------------------------------------------------------------------------


def get_base_dir() -> Path:
    """
    Devuelve el directorio raíz del proyecto de forma robusta.

    Casos cubiertos:
    - Script .py normal        → directorio del archivo .py
    - PyInstaller --onefile    → sys._MEIPASS es el directorio temporal donde
                                 PyInstaller extrae los recursos; el .exe real
                                 está en sys.executable y vive en la raíz del
                                 proyecto, que es lo que necesitamos.
    - PyInstaller --onedir     → misma lógica que --onefile

    NOTA: sys._MEIPASS apunta a un directorio TEMPORAL interno de PyInstaller
    donde se extraen los archivos empaquetados. NO es la carpeta del proyecto.
    La carpeta del proyecto es siempre el directorio padre del .exe.
    """
    if getattr(sys, "frozen", False):
        # Compilado: la raíz del proyecto es donde vive el .exe
        return Path(sys.executable).resolve().parent
    # Script directo: la raíz es donde vive este .py
    return Path(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Validaciones previas
# ---------------------------------------------------------------------------


def check_run_py(base_dir: Path) -> Path:
    """Verifica que run.py existe en la raíz del proyecto."""
    run_py = base_dir / "run.py"
    if not run_py.exists():
        fatal(
            f"No se encontró run.py en:\n{base_dir}\n\n"
            "Asegúrate de que AppKS.exe esté en la carpeta raíz del proyecto."
        )
    return run_py


def check_requirements(base_dir: Path) -> Path:
    """Verifica que requirements.txt existe en la raíz del proyecto."""
    req = base_dir / "requirements.txt"
    if not req.exists():
        fatal(
            f"No se encontró requirements.txt en:\n{base_dir}\n\n"
            "El archivo es necesario para instalar dependencias automáticamente."
        )
    return req


# ---------------------------------------------------------------------------
# Detección de Python del sistema
# ---------------------------------------------------------------------------


def _test_python_candidate(candidate: str) -> bool:
    """
    Ejecuta `candidate --version` y retorna True si el proceso responde OK.
    Captura stdout/stderr para no contaminar la consola del usuario.
    """
    try:
        result = subprocess.run(
            [candidate, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version_line = (result.stdout or result.stderr).strip()
            print_info(f"Encontrado: {candidate}  ({version_line})")
            return True
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        pass
    return False


def find_system_python() -> str:
    """
    Localiza el ejecutable de Python del sistema (para crear el venv).

    Orden de búsqueda:
      1. El intérprete que ejecuta este script (sys.executable)
         — útil cuando se corre como .py desde una instalación conocida
      2. "python"   — en PATH (instalación estándar)
      3. "py"       — Python Launcher para Windows (instalado con Python 3.3+)
      4. "python3"  — habitual en sistemas tipo Unix / WSL
      5. Rutas absolutas comunes en Windows para las versiones más recientes

    Si ningún candidato responde, termina con un mensaje claro.
    """
    print_step("Buscando Python en el sistema...")

    # Candidatos genéricos (dependen de PATH)
    candidates: list[str] = [sys.executable, "python", "py", "python3"]

    # Rutas absolutas de Windows para instalaciones sin PATH configurado
    win_absolute: list[str] = []
    for ver in _WIN_PYTHON_VERSIONS:
        # Instalaciones en C:\PythonXXX
        win_absolute.append(rf"C:\Python{ver}\python.exe")
        # Instalaciones en %LOCALAPPDATA%\Programs\Python\PythonXXX
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            win_absolute.append(
                os.path.join(
                    local_app, "Programs", "Python", f"Python{ver}", "python.exe"
                )
            )

    all_candidates = candidates + win_absolute

    for candidate in all_candidates:
        if _test_python_candidate(candidate):
            return candidate

    # Ningún candidato funcionó
    fatal(
        "Python no está instalado en el sistema o no está en PATH.\n\n"
        "Solución:\n"
        "  1. Descarga Python desde https://python.org/downloads\n"
        "  2. Durante la instalación, marca 'Add Python to PATH'\n"
        "  3. Vuelve a ejecutar AppKS\n\n"
        "Versión mínima recomendada: Python 3.9"
    )
    return ""  # Nunca se alcanza; fatal() termina el proceso


# ---------------------------------------------------------------------------
# Bootstrap: creación de venv
# ---------------------------------------------------------------------------


def create_venv(base_dir: Path, system_python: str) -> None:
    """
    Crea el entorno virtual en base_dir/venv usando el Python del sistema.
    Usa listas en subprocess para manejar correctamente paths con espacios.
    """
    print_step("Creando entorno virtual...")
    venv_dir = base_dir / "venv"
    print_info(f"Destino: {venv_dir}")

    result: subprocess.CompletedProcess[str] | None = None
    try:
        result = subprocess.run(
            [system_python, "-m", "venv", str(venv_dir)],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError) as exc:
        fatal(
            f"No se pudo ejecutar Python para crear el entorno virtual.\nDetalle: {exc}"
        )

    if result is None or result.returncode != 0:
        detail = ((result.stderr or result.stdout or "").strip()) if result else ""
        fatal(
            "No se pudo crear el entorno virtual.\n\n"
            "Posibles causas:\n"
            "  - El módulo 'venv' no está disponible en esta instalación de Python\n"
            "  - Permisos insuficientes en la carpeta del proyecto\n"
            "  - Ruta del proyecto contiene caracteres especiales\n\n"
            + (f"Detalle:\n{detail}\n\n" if detail else "")
            + f"Carpeta destino: {venv_dir}"
        )

    print_info("Entorno virtual creado correctamente.")


# ---------------------------------------------------------------------------
# Bootstrap: instalación de dependencias con reintentos
# ---------------------------------------------------------------------------


def _run_pip(
    venv_python: Path, args: list[str], base_dir: Path
) -> subprocess.CompletedProcess[str]:
    """
    Ejecuta pip dentro del venv con los argumentos dados.
    Retorna el objeto CompletedProcess para que el llamador evalúe el resultado.
    Muestra la salida directamente en consola (sin --quiet) para feedback real.
    """
    cmd = [str(venv_python), "-m", "pip"] + args
    return subprocess.run(
        cmd,
        cwd=str(base_dir),
        text=True,
        # No capturamos stdout/stderr: se imprime en tiempo real en la consola,
        # dando la sensación de actividad y evitando que parezca congelado.
    )


def _upgrade_pip(venv_python: Path, base_dir: Path) -> None:
    """Actualiza pip dentro del venv para evitar warnings de versión obsoleta."""
    print_info("Actualizando pip...")
    _run_pip(venv_python, ["install", "--upgrade", "pip", "--quiet"], base_dir)


def install_dependencies(venv_python: Path, requirements: Path, base_dir: Path) -> None:
    """
    Instala las dependencias de requirements.txt dentro del venv.

    - Primero actualiza pip (silencioso).
    - Luego instala requirements con salida visible (feedback real-time).
    - Reintenta hasta MAX_INSTALL_RETRIES veces si falla.
    """
    print_step("Instalando dependencias (puede tardar varios minutos)...")
    print_info("Por favor, no cierres esta ventana.")
    print_info(f"Leyendo: {requirements}\n")

    # Actualizar pip antes de instalar para reducir warnings
    _upgrade_pip(venv_python, base_dir)

    last_returncode = 1
    for attempt in range(1, MAX_INSTALL_RETRIES + 1):
        if attempt > 1:
            print_info(
                f"Reintentando instalación (intento {attempt}/{MAX_INSTALL_RETRIES})..."
            )
            time.sleep(2)  # Pequeña pausa antes del reintento

        result = _run_pip(
            venv_python,
            ["install", "-r", str(requirements)],
            base_dir,
        )
        last_returncode = result.returncode

        if last_returncode == 0:
            print_info("Dependencias instaladas correctamente.")
            return  # Éxito

        print_info(f"Intento {attempt} fallido (código de salida: {last_returncode}).")

    # Todos los intentos fallaron
    fatal(
        f"Falló la instalación de dependencias tras {MAX_INSTALL_RETRIES} intentos.\n\n"
        "Posibles causas:\n"
        "  - Sin conexión a internet\n"
        "  - Repositorio PyPI no disponible temporalmente\n"
        "  - Versión de Python incompatible con algún paquete\n\n"
        "Sugerencia manual:\n"
        "  1. Abre una terminal (cmd o PowerShell)\n"
        "  2. Navega a la carpeta del proyecto\n"
        "  3. Ejecuta:\n"
        "       venv\\Scripts\\activate\n"
        "       pip install -r requirements.txt"
    )


def validate_streamlit(venv_python: Path) -> None:
    """
    Verifica que streamlit quedó instalado e importable en el venv.
    Si falla, indica al usuario que elimine el venv y reintente.
    """
    print_info("Verificando instalación de Streamlit...")
    result = subprocess.run(
        [str(venv_python), "-c", "import streamlit; print(streamlit.__version__)"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fatal(
            "La instalación pareció completar, pero 'streamlit' no es importable.\n\n"
            "Solución:\n"
            "  1. Elimina la carpeta 'venv' del proyecto\n"
            "  2. Ejecuta AppKS nuevamente para reinstalar"
        )
    version = result.stdout.strip()
    print_info(f"Streamlit {version} listo.")


# ---------------------------------------------------------------------------
# Lanzamiento de Streamlit
# ---------------------------------------------------------------------------


def launch_app(venv_python: Path, run_py: Path, base_dir: Path) -> None:
    """
    Arranca Streamlit usando el Python del venv.
    Abre el navegador SOLO si el proceso sigue corriendo tras el arranque.

    Usa `python -m streamlit run` (no streamlit.exe) para máxima portabilidad.
    """
    print_step("Iniciando aplicación...")
    print_info("Comando: python -m streamlit run run.py")

    cmd = [str(venv_python), "-m", "streamlit", "run", str(run_py)]

    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Sin shell=True: rutas con espacios se manejan con listas
        )
    except (FileNotFoundError, OSError, PermissionError) as exc:
        fatal(f"No se pudo iniciar Streamlit:\n{exc}")

    # Guard: satisface al analizador de tipos (fatal() ya termina el proceso)
    if proc is None:
        fatal("No se pudo crear el proceso de Streamlit.")
        return

    # Esperar a que Streamlit levante el servidor HTTP
    print("      Esperando que Streamlit arranque", end="", flush=True)
    for _ in range(3):
        time.sleep(1)
        print(".", end="", flush=True)
    print(" listo.", flush=True)

    # Verificar que el proceso no murió durante el arranque
    if proc.poll() is not None:
        stderr_output = ""
        try:
            _, stderr_bytes = proc.communicate(timeout=3)
            stderr_output = stderr_bytes.decode(errors="replace").strip()
        except Exception:
            pass
        fatal(
            "Streamlit arrancó pero se cerró inesperadamente.\n\n"
            + (
                f"Detalle:\n{stderr_output}"
                if stderr_output
                else "Revisa que las dependencias estén correctamente instaladas en venv."
            )
        )

    # Solo abrir navegador si el proceso está activo
    url = "http://localhost:8501"
    webbrowser.open(url)
    print(f"\n  AppKS está corriendo en {url}", flush=True)
    print(
        "  Cierra esta ventana (o presiona Ctrl+C) para detener la aplicación.\n",
        flush=True,
    )

    # Mantener el launcher activo hasta que Streamlit termine
    try:
        proc.wait()
    except KeyboardInterrupt:
        print_step("Deteniendo AppKS...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# Punto de entrada principal
# ---------------------------------------------------------------------------


def main() -> None:
    separator = "=" * 50
    print(f"\n{separator}")
    print("  Inicializando AppKS...")
    print(f"{separator}\n")

    # 1. Resolver ruta base del proyecto (robusta: script y .exe compilado)
    base_dir = get_base_dir()
    print_info(f"Directorio del proyecto: {base_dir}")
    os.chdir(base_dir)  # Normaliza el CWD para rutas relativas internas

    # 2. Verificar archivos esenciales
    run_py = check_run_py(base_dir)
    requirements = check_requirements(base_dir)

    # 3. Ruta al Python del entorno virtual (Windows: Scripts/python.exe)
    venv_python = base_dir / "venv" / "Scripts" / "python.exe"

    # 4. Bootstrap automático si el venv no existe
    if not venv_python.exists():
        print_step("Preparando entorno por primera vez...")
        print_info("(Este proceso solo ocurre una vez en este equipo)\n")

        system_python = find_system_python()
        create_venv(base_dir, system_python)

        # Verificación post-creación
        if not venv_python.exists():
            fatal(
                "El entorno virtual fue creado pero no se encontró python.exe.\n\n"
                f"Ruta esperada:\n  {venv_python}\n\n"
                "Intenta crear el entorno manualmente:\n"
                "  python -m venv venv"
            )

        install_dependencies(venv_python, requirements, base_dir)
        validate_streamlit(venv_python)
        print_step("Entorno listo.")
    else:
        print_info("Entorno virtual encontrado. Saltando instalación.")

    # 5. Lanzar la app
    launch_app(venv_python, run_py, base_dir)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # Relanzar sys.exit() sin capturarlo (fatal() ya manejó el mensaje)
        raise
    except Exception as exc:
        # Captura cualquier error inesperado no manejado
        import traceback

        separator = "=" * 50
        print(f"\n{separator}", flush=True)
        print("  Error inesperado en AppKS Launcher\n", flush=True)
        traceback.print_exc()
        print(f"\n{separator}", flush=True)
        show_error_dialog(
            f"Error inesperado:\n{exc}\n\nRevisa la consola para más detalles."
        )
        wait_for_enter()
        sys.exit(1)
