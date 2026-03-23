#!/usr/bin/env python3
"""
Genera un reporte rapido del estado de AppKS para compartir con un agente externo.

Uso:
  python generar_reporte_agente.py
  python generar_reporte_agente.py --salida "exports/reporte_agente.md"

Si no se pasa --salida, crea automaticamente un archivo en exports/ con timestamp.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as exc:  # pragma: no cover
        return 1, "", str(exc)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def parse_readme(readme: str) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {
        "titulo": "AppKS",
        "descripcion": "",
        "version": "No detectada",
        "estado": "No detectado",
        "modulos": [],
    }

    for raw_line in readme.splitlines():
        line = raw_line.lstrip("\ufeff").strip()
        if line.startswith("# "):
            data["titulo"] = line[2:].strip()
            break

    desc_match = re.search(r"^Sistema web interno.*$", readme, flags=re.MULTILINE)
    if desc_match:
        data["descripcion"] = desc_match.group(0).strip()

    version_match = re.search(r"\*\*(v[0-9]+\.[0-9]+\.[0-9]+)\*\*", readme)
    if version_match:
        data["version"] = version_match.group(1)

    estado_match = re.search(r"\*\*v[0-9]+\.[0-9]+\.[0-9]+\*\*\s*[-–]\s*(.+)", readme)
    if estado_match:
        data["estado"] = estado_match.group(1).strip()

    modulos: list[str] = []
    for line in readme.splitlines():
        if not line.startswith("| ") or "|" not in line:
            continue
        if "---" in line:
            continue

        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue

        if parts[0] in {"Módulo", "Modulo"}:
            continue

        modulos.append(f"{parts[0]} ({parts[1]}): {parts[2]}")
    data["modulos"] = modulos

    return data


def parse_requirements(req_text: str) -> list[str]:
    deps: list[str] = []
    for line in req_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        deps.append(line)
    return deps


def git_snapshot(root: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "repo": False,
        "branch": "",
        "status_lines": [],
        "staged": 0,
        "modified": 0,
        "untracked": 0,
        "recent_commits": [],
    }

    code, out, _ = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], root)
    if code != 0 or out.lower() != "true":
        return info

    info["repo"] = True

    _, branch, _ = run_cmd(["git", "branch", "--show-current"], root)
    info["branch"] = branch or "(sin branch)"

    _, status_out, _ = run_cmd(["git", "status", "--short"], root)
    status_lines = [ln for ln in status_out.splitlines() if ln.strip()]
    info["status_lines"] = status_lines

    staged = 0
    modified = 0
    untracked = 0
    for ln in status_lines:
        if ln.startswith("??"):
            untracked += 1
            continue

        x = ln[0] if len(ln) >= 1 else " "
        y = ln[1] if len(ln) >= 2 else " "
        if x != " " and x != "?":
            staged += 1
        if y != " " and y != "?":
            modified += 1

    info["staged"] = staged
    info["modified"] = modified
    info["untracked"] = untracked

    _, commits_out, _ = run_cmd(
        ["git", "log", "--oneline", "-5", "--decorate"],
        root,
    )
    info["recent_commits"] = [ln for ln in commits_out.splitlines() if ln.strip()]

    return info


def build_report(
    root: Path,
    readme_info: dict[str, str | list[str]],
    deps: list[str],
    git_info: dict[str, object],
) -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modulos = readme_info.get("modulos", [])
    if not isinstance(modulos, list):
        modulos = []

    status_lines = git_info.get("status_lines", [])
    if not isinstance(status_lines, list):
        status_lines = []

    recent_commits = git_info.get("recent_commits", [])
    if not isinstance(recent_commits, list):
        recent_commits = []

    lines: list[str] = []
    lines.append("# Reporte de estado para agente externo")
    lines.append("")
    lines.append(f"- Fecha reporte: {now}")
    lines.append(f"- Proyecto: {readme_info.get('titulo', 'AppKS')}")
    lines.append(f"- Ruta local: {root}")
    lines.append("")

    lines.append("## 1) Contexto funcional")
    descripcion = str(readme_info.get("descripcion", "")).strip()
    if descripcion:
        lines.append(f"- Descripcion: {descripcion}")
    lines.append(f"- Version declarada: {readme_info.get('version', 'No detectada')}")
    lines.append(f"- Estado declarado: {readme_info.get('estado', 'No detectado')}")
    lines.append("")

    lines.append("## 2) Modulos")
    if modulos:
        for m in modulos:
            lines.append(f"- {m}")
    else:
        lines.append("- No se detectaron modulos en README.")
    lines.append("")

    lines.append("## 3) Stack tecnico")
    if deps:
        lines.append(f"- Dependencias principales ({len(deps)}):")
        for dep in deps:
            lines.append(f"  - {dep}")
    else:
        lines.append("- No se encontro requirements.txt o esta vacio.")
    lines.append("")

    lines.append("## 4) Estado Git (sin commit)")
    if not git_info.get("repo", False):
        lines.append("- No es un repositorio Git o no fue posible leer el estado.")
    else:
        lines.append(f"- Branch actual: {git_info.get('branch', '')}")
        lines.append(f"- Cambios staged: {git_info.get('staged', 0)}")
        lines.append(f"- Cambios modificados (unstaged): {git_info.get('modified', 0)}")
        lines.append(f"- Archivos untracked: {git_info.get('untracked', 0)}")
        if status_lines:
            lines.append("- Detalle status --short:")
            for ln in status_lines:
                lines.append(f"  - {ln}")
        else:
            lines.append("- Working tree limpio.")

        if recent_commits:
            lines.append("- Ultimos commits:")
            for ln in recent_commits:
                lines.append(f"  - {ln}")
    lines.append("")

    lines.append("## 5) Prompt sugerido para agente externo")
    lines.append("Copia y pega este bloque tal cual:")
    lines.append("")
    lines.append("```text")
    lines.append("Eres un agente tecnico que debe continuar el trabajo en AppKS.")
    lines.append(
        "Usa este contexto para diagnosticar, priorizar y proponer siguientes pasos."
    )
    lines.append("")
    lines.append("Contexto del proyecto:")
    lines.append(f"- Nombre: {readme_info.get('titulo', 'AppKS')}")
    lines.append(
        f"- Estado: {readme_info.get('version', 'No detectada')} - {readme_info.get('estado', 'No detectado')}"
    )
    if descripcion:
        lines.append(f"- Descripcion: {descripcion}")
    lines.append("")
    lines.append("Estado Git actual:")
    lines.append(f"- Branch: {git_info.get('branch', '(sin branch)')}")
    lines.append(f"- Staged: {git_info.get('staged', 0)}")
    lines.append(f"- Unstaged: {git_info.get('modified', 0)}")
    lines.append(f"- Untracked: {git_info.get('untracked', 0)}")
    if status_lines:
        lines.append("- Archivos con cambios:")
        for ln in status_lines:
            lines.append(f"  - {ln}")
    lines.append("")
    lines.append("Tu tarea:")
    lines.append("1) Resume riesgos y estado real en maximo 8 bullets.")
    lines.append("2) Propone plan de accion priorizado (corto, mediano plazo).")
    lines.append("3) Sugiere validaciones tecnicas para asegurar estabilidad.")
    lines.append("4) No inventes datos: si falta contexto, declaralo explicitamente.")
    lines.append("```")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def resolve_output_path(root: Path, custom_output: str | None) -> Path:
    if custom_output:
        out = Path(custom_output)
        if not out.is_absolute():
            out = root / out
        return out

    exports_dir = root / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return exports_dir / f"reporte_agente_{stamp}.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera un reporte del estado actual para un agente externo."
    )
    parser.add_argument(
        "--salida",
        dest="salida",
        default=None,
        help="Ruta de salida .md (opcional).",
    )
    args = parser.parse_args()

    root = Path(os.path.dirname(os.path.abspath(__file__)))
    readme_text = read_text(root / "README.md")
    req_text = read_text(root / "requirements.txt")

    readme_info = parse_readme(readme_text)
    deps = parse_requirements(req_text)
    git_info = git_snapshot(root)

    report = build_report(root, readme_info, deps, git_info)
    output_path = resolve_output_path(root, args.salida)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"Reporte generado: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
