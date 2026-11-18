# -*- coding: utf-8 -*-
"""Textos de la interfaz, leídos de `menu.yaml` (requerimientos 10 y 11).

El fichero manda: si una clave está en `menu.yaml`, se usa su texto. Si falta el
fichero, no se puede leer o la clave no existe, se recurre a los valores por
defecto de este módulo, así que la aplicación nunca se queda sin textos por un
error de formato.

El idioma se guarda en `~/.config/copiex/language` para que la extensión de
Nautilus (que se instala como fichero suelto) pueda leerlo sin importar este
paquete. Los textos españoles siguen en la raíz del YAML; los ingleses viven en
la sección `en:`.
"""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger(__name__)

IDIOMAS = ("es", "en")
_IDIOMA = None
_CACHE: dict = {}
_LOCK = threading.Lock()

_POR_DEFECTO = {
    "aplicacion": {
        "nombre": "Copiex",
        "descripcion": (
            "Copia ficheros y carpetas con cola propia, progreso, pausa y "
            "reanudación, integrada en Nautilus. Las copias siguen solas tras "
            "cerrar la aplicación o desconectar un dispositivo."
        ),
        "tooltip": "Copiex para Nautilus",
    },
    "menu": {
        "nueva": "Nueva copia",
        "ocultar": "Ocultar ventana",
        "mostrar": "Mostrar ventana",
        "idioma": "Idioma",
        "espanol": "Español",
        "ingles": "Inglés",
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
        "copia_varios": "Copia a {n} destinos",
        "de": "{hecho} de {total}",
        "progreso_destino": "{pct} % · {hecho} de {total}",
        "completado": "Completado · {bytes}",
        "en_pausa": "En pausa",
        "error": "Error: {detalle}",
        "fallo_desconocido": "fallo desconocido",
        "copiando": "Copiando · {detalle}",
        "quedan": "quedan {tiempo}",
        "elementos": "{hechos}/{total} elementos",
        "pausa_detalle": "{bytes} copiados ({hechos}/{total} elementos)",
        "destinos_completados": "{hechos} de {total} destinos completados · ",
        "completada": "Completada · {bytes} en {n} elementos",
        "cancelada": "Cancelada · {hecho} de {total}",
        "desde": "Desde {ruta}",
        "varios_origenes": "{n} elementos desde {carpeta}: {lista}",
        "y_mas": "y {n} más",
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
        "destinos_titulo": "Destinos de la copia",
        "destinos_ayuda": (
            "La primera carpeta ya está añadida. Añade más destinos si quieres "
            "repartir la copia; el origen se lee una sola vez."
        ),
        "anadir_destino": "Añadir otra carpeta",
        "empezar_copia": "Comenzar la copia",
        "elegir_destino_titulo": "¿Qué otra carpeta quieres como destino?",
        "quitar_destino": "Quitar este destino",
        "sin_destinos": "Añade al menos una carpeta de destino.",
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
        "error_copia": "No se pudo copiar con Copiex",
        "sin_nada_titulo": "No hay nada que pegar",
        "sin_nada_detalle": (
            "Selecciona los ficheros y usa «Copiar con Copiex» "
            "(o Ctrl+C en Nautilus) antes de pegarlos aquí."
        ),
        "ya_es_primera_titulo": "Esa ya es la primera carpeta",
        "ya_es_primera_detalle": "Elige otra ubicación para el segundo destino.",
        "sin_destinos_titulo": "No has añadido ningún destino",
        "sin_destinos_detalle": (
            "Cierra esta ventana y usa «Pegar con Copiex» para copiar "
            "solo en esta carpeta."
        ),
        "sin_gtk_titulo": "No se puede elegir varios destinos",
        "sin_gtk_detalle": "Falta GTK en Nautilus.",
        "contacto": "No se pudo contactar con Copiex",
        "rechazo": "Copiex rechazó la operación",
    },
    "errores": {
        "no_origenes": "Nautilus no ha indicado ningún origen",
        "no_destinos": "Nautilus no ha indicado ningún destino",
        "no_existe": "No existe: {ruta}",
        "destino_no_carpeta": "El destino no es una carpeta: {ruta}",
        "comando_desconocido": "comando desconocido: {comando}",
        "no_hay_nada": "No hay nada que copiar",
        "no_origen_indicado": "No has indicado ningún origen",
        "no_destino_indicado": "No has indicado ningún destino",
        "destino_dentro_origen": (
            "El destino está dentro del origen ({destino} ⊂ {origen})"
        ),
        "destino_igual_origen": (
            "El destino es la misma carpeta que el origen ({origen})"
        ),
        "todos_destinos": "No se pudo copiar a todos los destinos",
        "esperando_destino": "esperando la carpeta de destino {ruta}",
        "esperando_origen": "esperando a que aparezca {ruta}",
        "destino_cambio": "el fichero de destino cambió durante la copia",
        "copia_interrumpida": "copia interrumpida",
        "ruta_vacia": "Ruta vacía",
        "mtp_sin_gvfs": (
            "No se pudo acceder a «{uri}»: hace falta gvfs-fuse "
            "(sudo apt install gvfs-fuse) y el dispositivo montado"
        ),
        "solo_local": "Solo se admiten rutas locales o mtp://, no «{uri}»",
        "uri_invalida": "URI no válida: {uri}",
    },
}

_POR_DEFECTO_EN = {
    "aplicacion": {
        "nombre": "Copiex",
        "descripcion": (
            "Copy files and folders with its own queue, progress, pause and "
            "resume, integrated into Nautilus. Copies keep going after the "
            "application closes or a device is disconnected."
        ),
        "tooltip": "Copiex for Nautilus",
    },
    "menu": {
        "nueva": "New copy",
        "ocultar": "Hide window",
        "mostrar": "Show window",
        "idioma": "Language",
        "espanol": "Spanish",
        "ingles": "English",
        "acerca": "About",
        "salir": "Quit",
    },
    "ventana": {
        "subtitulo": "Copy history",
        "vacio_titulo": "No copies yet",
        "vacio_descripcion": (
            "Click «New copy» here, or copy in Nautilus and use "
            "«Paste with Copiex» in the destination folder."
        ),
        "copia_varios": "Copy to {n} destinations",
        "de": "{hecho} of {total}",
        "progreso_destino": "{pct} % · {hecho} of {total}",
        "completado": "Completed · {bytes}",
        "en_pausa": "Paused",
        "error": "Error: {detalle}",
        "fallo_desconocido": "unknown failure",
        "copiando": "Copying · {detalle}",
        "quedan": "{tiempo} left",
        "elementos": "{hechos}/{total} items",
        "pausa_detalle": "{bytes} copied ({hechos}/{total} items)",
        "destinos_completados": "{hechos} of {total} destinations completed · ",
        "completada": "Completed · {bytes} in {n} items",
        "cancelada": "Cancelled · {hecho} of {total}",
        "desde": "From {ruta}",
        "varios_origenes": "{n} items from {carpeta}: {lista}",
        "y_mas": "and {n} more",
    },
    "acciones": {
        "pausar": "Pause",
        "reanudar": "Resume",
        "reintentar": "Retry",
        "cancelar": "Cancel",
        "eliminar": "Delete",
    },
    "dialogos": {
        "origen_titulo": "What do you want to copy?",
        "destino_titulo": "Where do you want to copy it?",
        "destinos_titulo": "Copy destinations",
        "destinos_ayuda": (
            "The first folder is already added. Add more destinations if you "
            "want to split the copy; the source is read only once."
        ),
        "anadir_destino": "Add another folder",
        "empezar_copia": "Start copying",
        "elegir_destino_titulo": "What other folder do you want as destination?",
        "quitar_destino": "Remove this destination",
        "sin_destinos": "Add at least one destination folder.",
    },
    "nautilus": {
        "copiar": "Copy with Copiex",
        "cortar": "Cut with Copiex",
        "pegar": "Paste with Copiex",
        "pegar_varios": "Paste with Copiex to N destinations",
        "copiar_ayuda": "Mark these items to copy them with Copiex",
        "cortar_ayuda": (
            "Move these items with Copiex: they are copied and the originals "
            "are deleted when the copy finishes"
        ),
        "pegar_ayuda": (
            "Copy here what was marked with Copiex (or the clipboard) with "
            "progress, pause and resume"
        ),
        "pegar_varios_ayuda": (
            "Copy to this folder and others you choose, reading the source "
            "only once"
        ),
        "destinos_titulo": "Copy destinations",
        "destinos_ayuda": (
            "This folder is the first destination. Add the others and click "
            "«Finish selection»."
        ),
        "anadir_destino": "Add another destination",
        "finalizar_seleccion": "Finish selection",
        "elegir_destino_titulo": "What other folder do you want as destination?",
        "error_copia": "Could not copy with Copiex",
        "sin_nada_titulo": "There is nothing to paste",
        "sin_nada_detalle": (
            "Select the files and use «Copy with Copiex» (or Ctrl+C in "
            "Nautilus) before pasting them here."
        ),
        "ya_es_primera_titulo": "That is already the first folder",
        "ya_es_primera_detalle": "Choose another location for the second destination.",
        "sin_destinos_titulo": "You have not added any destination",
        "sin_destinos_detalle": (
            "Close this window and use «Paste with Copiex» to copy only into "
            "this folder."
        ),
        "sin_gtk_titulo": "Cannot choose multiple destinations",
        "sin_gtk_detalle": "GTK is missing in Nautilus.",
        "contacto": "Could not contact Copiex",
        "rechazo": "Copiex rejected the operation",
    },
    "errores": {
        "no_origenes": "Nautilus did not provide any source",
        "no_destinos": "Nautilus did not provide any destination",
        "no_existe": "Does not exist: {ruta}",
        "destino_no_carpeta": "The destination is not a folder: {ruta}",
        "comando_desconocido": "unknown command: {comando}",
        "no_hay_nada": "There is nothing to copy",
        "no_origen_indicado": "No source was provided",
        "no_destino_indicado": "No destination was provided",
        "destino_dentro_origen": (
            "The destination is inside the source ({destino} ⊂ {origen})"
        ),
        "destino_igual_origen": (
            "The destination is the same folder as the source ({origen})"
        ),
        "todos_destinos": "Could not copy to all destinations",
        "esperando_destino": "waiting for the destination folder {ruta}",
        "esperando_origen": "waiting for {ruta} to appear",
        "destino_cambio": "the destination file changed during the copy",
        "copia_interrumpida": "copy interrupted",
        "ruta_vacia": "Empty path",
        "mtp_sin_gvfs": (
            "Could not access «{uri}»: gvfs-fuse is required "
            "(sudo apt install gvfs-fuse) and the device must be mounted"
        ),
        "solo_local": "Only local paths or mtp:// are supported, not «{uri}»",
        "uri_invalida": "Invalid URI: {uri}",
    },
}


def ruta_idioma() -> str:
    """Fichero donde se guarda el idioma elegido."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "copiex", "language")


def _leer_idioma() -> str:
    elegido = os.environ.get("COPIEX_LANGUAGE", "").strip().lower()
    if elegido in IDIOMAS:
        return elegido
    try:
        with open(ruta_idioma(), encoding="utf-8") as fichero:
            elegido = fichero.read().strip().lower()
    except OSError:
        return "es"
    return elegido if elegido in IDIOMAS else "es"


def idioma_actual() -> str:
    """Idioma activo: `es` o `en`."""
    global _IDIOMA
    elegido = os.environ.get("COPIEX_LANGUAGE", "").strip().lower()
    if elegido in IDIOMAS:
        return elegido
    with _LOCK:
        if _IDIOMA is None:
            _IDIOMA = _leer_idioma()
        return _IDIOMA


def cambiar_idioma(codigo: str) -> bool:
    """Guarda el idioma y descarta los textos cacheados."""
    global _IDIOMA
    codigo = (codigo or "").strip().lower()
    if codigo not in IDIOMAS:
        return False
    with _LOCK:
        _IDIOMA = codigo
        _CACHE.clear()
        ruta = ruta_idioma()
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            temporal = ruta + ".tmp"
            with open(temporal, "w", encoding="utf-8") as fichero:
                fichero.write(codigo + "\n")
            os.replace(temporal, ruta)
        except OSError as exc:
            log.warning("no se pudo guardar el idioma en %s: %s", ruta, exc)
    log.info("idioma de la interfaz: %s", codigo)
    return True


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
        return {}
    try:
        datos = _leer(ruta)
    except OSError as exc:
        log.warning("menu.yaml ilegible (%s): textos por defecto", exc)
        return {}
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
    idioma = idioma_actual()
    valor = None
    if idioma != "es":
        seccion = datos.get(idioma)
        if isinstance(seccion, dict):
            valor = _buscar(seccion, clave)
    if valor is None:
        # Una traducción incompleta no debe dejar la clave técnica: se usa el
        # texto español del propio menu.yaml y, después, el de reserva.
        valor = _buscar(datos, clave)
    if valor:
        return valor
    defecto = _POR_DEFECTO_EN if idioma == "en" else _POR_DEFECTO
    valor = _buscar(defecto, clave)
    if valor is None:
        valor = _buscar(_POR_DEFECTO, clave)
    return valor if valor is not None else clave


def formato(clave: str, **valores) -> str:
    """Texto con placeholders, sin romperse si falta un valor."""
    plantilla = texto(clave)
    try:
        return plantilla.format(**valores)
    except (KeyError, ValueError, IndexError):
        return plantilla


def olvidar_cache() -> None:
    """Descarta lo leído (pruebas y, si algún día hace falta, recarga en vivo)."""
    global _IDIOMA
    with _LOCK:
        _CACHE.clear()
        _IDIOMA = None
