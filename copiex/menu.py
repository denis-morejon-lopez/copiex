# -*- coding: utf-8 -*-
"""Textos de la interfaz, leídos de `menu.yaml` (requerimientos 10 y 11).

El fichero manda: si una clave está en `menu.yaml`, se usa su texto. Si falta el
fichero, no se puede leer o la clave no existe, se recurre a los valores por
defecto de este módulo, así que la aplicación nunca se queda sin textos por un
error de formato.

El lector es deliberadamente mínimo (YAML de mapas anidados, un valor por línea)
para no añadir dependencias. El resultado se guarda en memoria: para ver un
cambio en `menu.yaml` hay que reiniciar Copiex.
"""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger(__name__)

_POR_DEFECTO = {
    "aplicacion": {
        "nombre": "Copiex",
        "descripcion": (
            "Copia ficheros y carpetas con cola propia, progreso, pausa y "
            "reanudación, integrada en Nautilus. Las copias siguen solas tras "
            "cerrar la aplicación o desconectar un dispositivo."
        ),
    },
    "menu": {
        "nueva": "Nueva copia",
        "ocultar": "Ocultar ventana",
        "mostrar": "Mostrar ventana",
        "acerca": "Acerca de",
        "salir": "Salir",
    },
    "ventana": {
        "subtitulo": "Historial de copias",
        "vacio_titulo": "Todavía no hay copias",
        "vacio_descripcion": (
            "Pulsa «Nueva copia» aquí, o copia en Nautilus y usa "
            "«Pegar con Copiex» en la carpeta de destino."
        ),
    },
    "acciones": {
        "pausar": "Pausar",
        "reanudar": "Reanudar",
        "reintentar": "Reintentar",
        "cancelar": "Cancelar",
        "eliminar": "Eliminar",
    },
    "dialogos": {
        "origen_titulo": "¿Qué quieres copiar?",
        "destino_titulo": "¿Dónde quieres copiarlo?",
    },
    "nautilus": {
        "copiar": "Copiar con Copiex",
        "cortar": "Cortar con Copiex",
        "pegar": "Pegar con Copiex",
        "pegar_varios": "Pegar con Copiex N destinos",
        "copiar_ayuda": "Marca estos elementos para copiarlos con Copiex",
        "cortar_ayuda": (
            "Mueve estos elementos con Copiex: se copian y, al terminar, se "
            "borran los originales"
        ),
        "pegar_ayuda": (
            "Copia aquí lo marcado con Copiex (o el portapapeles) con "
            "progreso, pausa y reanudación"
        ),
        "pegar_varios_ayuda": (
            "Copia a esta carpeta y a otras que elijas, leyendo el origen "
            "una sola vez"
        ),
        "destinos_titulo": "Destinos de la copia",
        "destinos_ayuda": (
            "Esta carpeta es el primer destino. Añade los demás y pulsa "
            "«Finalizar selección»."
        ),
        "anadir_destino": "Añadir otro destino",
        "finalizar_seleccion": "Finalizar selección",
        "elegir_destino_titulo": "¿Qué otra carpeta quieres como destino?",
    },
}

_CACHE: dict = {}
_LOCK = threading.Lock()


def ruta_menu() -> str | None:
    """Ruta del `menu.yaml` en uso, o None si no hay ninguno."""
    candidatos = []
    elegido = os.environ.get("COPIEX_MENU")
    if elegido:
        candidatos.append(elegido)
    paquete = os.path.dirname(os.path.abspath(__file__))
    candidatos.append(os.path.join(os.path.dirname(paquete), "menu.yaml"))
    candidatos.append(os.path.join(paquete, "menu.yaml"))
    for ruta in candidatos:
        if os.path.isfile(ruta):
            return ruta
    return None


def _limpiar(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        return valor[1:-1]
    corte = valor.find(" #")
    return valor[:corte].rstrip() if corte != -1 else valor


def _leer(ruta: str) -> dict:
    """Interpreta el subconjunto de YAML que se usa en menu.yaml."""
    datos: dict = {}
    pila = [(-1, datos)]
    with open(ruta, encoding="utf-8") as fichero:
        for numero, linea in enumerate(fichero, 1):
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            sangria = len(linea) - len(linea.lstrip(" "))
            texto = linea.strip()
            if ":" not in texto:
                log.warning("menu.yaml línea %s: se ignora %r", numero, texto)
                continue
            clave, _, valor = texto.partition(":")
            clave = clave.strip()
            valor = valor.strip()
            while len(pila) > 1 and sangria <= pila[-1][0]:
                pila.pop()
            destino = pila[-1][1]
            if valor == "":
                hijo: dict = {}
                destino[clave] = hijo
                pila.append((sangria, hijo))
            else:
                destino[clave] = _limpiar(valor)
    return datos


def _cargar() -> dict:
    ruta = ruta_menu()
    if ruta is None:
        log.info("menu.yaml no encontrado: se usan los textos por defecto")
        return _POR_DEFECTO
    try:
        datos = _leer(ruta)
    except OSError as exc:
        log.warning("menu.yaml ilegible (%s): textos por defecto", exc)
        return _POR_DEFECTO
    log.debug("textos de la interfaz leídos de %s", ruta)
    return datos


def _buscar(datos: dict, clave: str) -> str | None:
    actual = datos
    for parte in clave.split("."):
        if not isinstance(actual, dict) or parte not in actual:
            return None
        actual = actual[parte]
    return actual if isinstance(actual, str) else None


def texto(clave: str) -> str:
    """Texto de la interfaz para `clave` (por ejemplo "menu.nueva")."""
    with _LOCK:
        datos = _CACHE.get("datos")
        if datos is None:
            datos = _cargar()
            _CACHE["datos"] = datos
    valor = _buscar(datos, clave)
    if valor:
        return valor
    valor = _buscar(_POR_DEFECTO, clave)
    return valor if valor is not None else clave


def olvidar_cache() -> None:
    """Descarta lo leído (pruebas y, si algún día hace falta, recarga en vivo)."""
    with _LOCK:
        _CACHE.clear()
