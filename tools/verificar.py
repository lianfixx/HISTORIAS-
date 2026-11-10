#!/usr/bin/env python3
"""Revisa que el repositorio sea coherente: enlaces, versión, puentes, archivos privados y pruebas.

  python3 tools/verificar.py            todo
  python3 tools/verificar.py --rapido   sin las pruebas del motor
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "historias-studio" / "SKILL.md"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True).stdout


def revisar() -> list[str]:
    fallos = []
    seguidos = [a for a in git("ls-files", "--cached", "--others", "--exclude-standard").split("\n") if a]
    # 1. Enlaces relativos de todos los Markdown
    for a in seguidos:
        if not a.endswith(".md"):
            continue
        f = RAIZ / a
        for destino in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", f.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", destino):
                continue
            if not (f.parent / destino).exists():
                fallos.append(f"{a}: enlace roto a {destino}")
    # 2. Versión de la skill anotada en el registro de cambios
    texto = SKILL.read_text(encoding="utf-8")
    version = re.search(r'version:\s*"([^"]+)"', texto)
    if not version:
        fallos.append("SKILL.md sin versión")
    elif f"## {version.group(1)} " not in (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"):
        fallos.append(f"CHANGELOG.md no tiene la versión {version.group(1)}")
    # 3. Cabecera válida y puentes con la misma descripción
    m = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: \"([^\"\n]+)\"\n", texto)
    if not m:
        fallos.append("SKILL.md: cabecera inválida (name y description entre comillas, en una línea)")
    else:
        if len(m.group(2)) > 1024:
            fallos.append("SKILL.md: la descripción pasa de 1024 caracteres")
        for puente in (".claude", ".agents"):
            p = RAIZ / puente / "skills" / m.group(1) / "SKILL.md"
            if not p.exists() or f'description: "{m.group(2)}"' not in p.read_text(encoding="utf-8"):
                fallos.append(f"{puente}/skills/{m.group(1)}/SKILL.md no coincide con la skill canónica")
    if len(texto.splitlines()) > 500:
        fallos.append("SKILL.md pasa de 500 líneas: mover detalle a references/")
    # 4. Comandos citados en la documentación existen en el motor
    motor = (SKILL.parent / "scripts" / "historias.py").read_text(encoding="utf-8")
    comandos = set(re.findall(r'add_parser\("([a-z]+)"\)', motor))
    for a in seguidos:
        if a.endswith(".md"):
            for c in re.findall(r"(?:\$H|historias\.py) ([a-z]+)", (RAIZ / a).read_text(encoding="utf-8")):
                if c not in comandos:
                    fallos.append(f"{a}: cita el comando inexistente «{c}»")
    # 5. Nada privado ni pesado en git
    for a in git("ls-files").split("\n"):
        if a.startswith(("producciones/", "fotos/")) or a.endswith((".env", ".heic", ".mp4")):
            fallos.append(f"archivo privado en git: {a}")
        elif a and (RAIZ / a).is_file() and (RAIZ / a).stat().st_size > 1_500_000:
            fallos.append(f"archivo de más de 1.5 MB en git: {a}")
    # 6. Cada espacio tiene sus archivos y cada tipografía su licencia
    for perfil in sorted((RAIZ / "espacios").glob("*/perfil.json")):
        for n in ("MARCA.md", "NICHO.md", "aprendizajes.md", "ideas.md"):
            if not (perfil.parent / n).exists():
                fallos.append(f"{perfil.parent.name}: falta {n}")
    fuentes = SKILL.parent / "fuentes"
    for ttf in fuentes.glob("*.ttf"):
        if not (fuentes / f"OFL-{ttf.stem.split('-')[0]}.txt").exists():
            fallos.append(f"fuentes/{ttf.name} sin su licencia")
    return fallos


def main() -> int:
    fallos = revisar()
    if "--rapido" not in sys.argv:
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "skills/historias-studio/scripts"],
                           cwd=RAIZ, capture_output=True, text=True)
        if r.returncode:
            fallos.append("pruebas del motor:\n" + r.stderr[-1500:])
    for f in fallos:
        print("FALLA:", f)
    print("Verificación " + ("con fallas." if fallos else "correcta."))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
