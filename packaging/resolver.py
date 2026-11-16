#!/usr/bin/env python3
"""Lista los paquetes que hay que incluir en el repositorio offline.

Uso: resolver.py NIVEL paquete1 paquete2 ...

Incluye los paquetes indicados y sus dependencias hasta NIVEL niveles (2 por
defecto). Se ignoran las alternativas virtuales (<...>): en un escritorio Ubuntu
siempre hay un proveedor instalado. No se incluyen recomendaciones ni sugerencias.
"""

from __future__ import annotations

import re
import subprocess
import sys

LINEA = re.compile(r"^\s*\|?\s*(?:Depends|Depende):\s*(.+?)\s*$")
NOMBRE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


def dependencias(paquete: str) -> set[str]:
    try:
        salida = subprocess.run(
            [
                "apt-cache",
                "depends",
                "--no-recommends",
                "--no-suggests",
                "--no-conflicts",
                "--no-breaks",
                "--no-replaces",
                "--no-enhances",
                paquete,
            ],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return set()
    encontradas = set()
    for linea in salida.splitlines():
        coincidencia = LINEA.match(linea)
        if not coincidencia:
            continue
        valor = coincidencia.group(1).split("|")[0].strip()
        if valor.startswith("<"):
            continue
        # Quita ":any", ":amd64" y restricciones de versión.
        valor = re.split(r"[ :(]", valor)[0]
        if NOMBRE.match(valor):
            encontradas.add(valor)
    return encontradas


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("uso: resolver.py NIVEL paquete...", file=sys.stderr)
        return 2
    try:
        nivel = max(0, int(argv[1]))
    except ValueError:
        nivel = 2
    iniciales = [p for p in argv[2:] if p]
    vistos = set(iniciales)
    frontera = set(iniciales)
    for _ in range(nivel):
        nuevos: set[str] = set()
        for paquete in sorted(frontera):
            nuevos |= dependencias(paquete)
        nuevos -= vistos
        if not nuevos:
            break
        vistos |= nuevos
        frontera = nuevos
    for paquete in sorted(vistos):
        print(paquete)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
