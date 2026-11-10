#!/usr/bin/env python3
"""Empaqueta la skill en dist/historias-studio.zip para subirla a una IA que acepte skills en ZIP."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "historias-studio"


def main() -> int:
    destino = RAIZ / "dist" / "historias-studio.zip"
    destino.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SKILL.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and not f.name.startswith("test_"):
                z.write(f, Path("historias-studio") / f.relative_to(SKILL))
        # Los espacios viajan con la skill para que funcione fuera del repositorio.
        for f in sorted((RAIZ / "espacios").rglob("*")):
            if f.is_file():
                z.write(f, Path("historias-studio") / "espacios" / f.relative_to(RAIZ / "espacios"))
    print(f"{destino} ({destino.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
