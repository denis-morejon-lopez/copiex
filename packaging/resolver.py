#!/usr/bin/env python3
"""Lista los paquetes que hay que incluir en el repositorio offline.

Uso: resolver.py [--archivo deps.txt] [--directas] [NIVEL] [paquete...]

  --archivo RUTA  lee las líneas de paquetes de ese fichero (admite comentarios)
  --directas      imprime solo los paquetes directos elegidos, sin el cierre

Con --archivo no hace falta pasar los paquetes como argumentos, y así no se
parten las alternativas «a | b» al expandir la lista en el shell.

Incluye los paquetes indicados y sus dependencias hasta NIVEL niveles (2 por
defecto). Se ignoran las alternativas virtuales (<...>): en un escritorio Ubuntu
siempre hay un proveedor instalado. No se incluyen recomendaciones ni sugerencias.

Cada argumento puede ser una alternativa «a | b»: se usa la primera que exista
en los repositorios de este sistema.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

LINEA = re.compile(r"^\s*\|?\s*(?:Depends|Depende):\s*(.+?)\s*$")
NOMBRE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


def apt_cache(*argumentos: str) -> str:
    """Ejecuta apt-cache en inglés: en español cambia las etiquetas
    («Candidato:») y el análisis de la salida falla."""
    entorno = dict(os.environ, LC_ALL="C", LANG="C")
    try:
        return subprocess.run(
            ["apt-cache", *argumentos],
            capture_output=True,
            text=True,
            check=False,
            env=entorno,
        ).stdout
    except OSError:
        return ""


def candidatos(nombres: list[str]) -> set[str]:
    """Paquetes de la lista que los repositorios de este sistema conocen.

    Una sola llamada a apt-cache policy: preguntar paquete a paquete hace que
    resolver el cierre tarde minutos.
    """
    unicos = sorted(set(nombres))
    if not unicos:
        return set()
    salida = apt_cache("policy", *unicos)
    disponibles: set[str] = set()
    actual = ""
    for linea in salida.splitlines():
        if not linea.strip():
            actual = ""
            continue
        if not linea[:1].isspace():
            actual = linea.strip().rstrip(":")
            continue
        texto = linea.strip()
        if actual and texto.startswith("Candidate:"):
            valor = texto.split(":", 1)[1].strip()
            if valor and valor != "(none)":
                disponibles.add(actual)
    return disponibles


def nombres_de(alternativas: str) -> list[str]:
    """Nombres válidos de una línea «a | b» de deps.txt, en orden."""
    nombres = []
    for alternativa in alternativas.split("|"):
        nombre = re.split(r"[ :(]", alternativa.strip())[0]
        if NOMBRE.match(nombre):
            nombres.append(nombre)
    return nombres


def elegir(alternativas: str, conocidos: set[str] | None = None) -> str:
    """Primera alternativa disponible de una línea «a | b» de deps.txt."""
    nombres = nombres_de(alternativas)
    if conocidos is None:
        conocidos = candidatos(nombres)
    for nombre in nombres:
        if nombre in conocidos:
            return nombre
    # Ninguna conocida: se devuelve la primera y que apt dé el error.
    return nombres[0] if nombres else ""


def dependencias(paquetes: list[str]) -> set[str]:
    """Dependencias de todos los paquetes de la lista, en una sola llamada."""
    if not paquetes:
        return set()
    salida = apt_cache(
        "depends",
        "--no-recommends",
        "--no-suggests",
        "--no-conflicts",
        "--no-breaks",
        "--no-replaces",
        "--no-enhances",
        *paquetes,
    )
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


def lineas_de(archivo: str) -> list[str]:
    try:
        with open(archivo, encoding="utf-8") as fichero:
            return [
                linea.split("#", 1)[0].strip()
                for linea in fichero
                if linea.split("#", 1)[0].strip()
            ]
    except OSError as error:
        print(f"ERROR: no se pudo leer {archivo}: {error}", file=sys.stderr)
        return []


def main(argv: list[str]) -> int:
    argumentos = argv[1:]
    solo_directas = False
    archivo = None
    nivel = None
    paquetes: list[str] = []
    i = 0
    while i < len(argumentos):
        argumento = argumentos[i]
        if argumento == "--directas":
            solo_directas = True
        elif argumento == "--archivo":
            i += 1
            if i >= len(argumentos):
                print("uso: resolver.py --archivo RUTA", file=sys.stderr)
                return 2
            archivo = argumentos[i]
        elif nivel is None and argumento.isdigit():
            nivel = int(argumento)
        else:
            paquetes.append(argumento)
        i += 1
    if archivo:
        paquetes.extend(lineas_de(archivo))
    if nivel is None:
        nivel = 2
    if not paquetes:
        print("uso: resolver.py [--archivo RUTA] [NIVEL] paquete...", file=sys.stderr)
        return 2
    nivel = max(0, nivel)
    lineas = [a for a in paquetes if a]
    conocidos = candidatos([n for linea in lineas for n in nombres_de(linea)])
    iniciales = [p for p in (elegir(a, conocidos) for a in lineas) if p]
    if solo_directas:
        for paquete in iniciales:
            print(paquete)
        return 0
    vistos = set(iniciales)
    frontera = set(iniciales)
    for _ in range(nivel):
        nuevos = dependencias(sorted(frontera))
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
