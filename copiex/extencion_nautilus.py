# -*- coding: utf-8 -*-
"""Extensión de Nautilus para Copiex.

Añade dos entradas al menú contextual de Nautilus:

  * «Copiar con Copiex»      → sobre la selección (marca los orígenes)
  * «Pegar con Copiex»       → sobre la carpeta de destino (lanza la copia)

La extensión es solo un puente: envía {origen…, destino} por el socket UNIX
de Copiex y la copia (progreso, pausa, reanudación) la hace la aplicación.

Requiere python3-nautilus:  sudo apt install python3-nautilus
Instalación:  ./install.sh  (copia este fichero a
~/.local/share/nautilus-python/extensions/copiex.py)

Compatible con la API de Nautilus que traiga el sistema:
  * Ubuntu 24.04 (Nautilus 46): API 4.0
  * Ubuntu 26.04 (Nautilus 50): API 4.1
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time

import gi
from gi.repository import Gio, GLib, GObject  # noqa: E402

# Orden de preferencia: primero la API más moderna y, si no está, la anterior.
VERSIONES_NAUTILUS = ("4.1", "4.0")


def _cargar_nautilus():
    """Devuelve (módulo Nautilus, versión de API) de la que haya instalada."""
    # Dentro de Nautilus, nautilus-python ya tiene cargada su typelib: se
    # reutiliza para no pedir require_version de una versión distinta.
    cargado = sys.modules.get("gi.repository.Nautilus")
    if cargado is not None:
        return cargado, getattr(cargado, "_version", "")

    for version in VERSIONES_NAUTILUS:
        try:
            gi.require_version("Nautilus", version)
            from gi.repository import Nautilus as modulo
        except (ValueError, ImportError):
            continue
        return modulo, version

    raise ImportError(
        "no se encontró la API de Nautilus (se probaron las versiones "
        + ", ".join(VERSIONES_NAUTILUS)
        + "); instala python3-nautilus: sudo apt install python3-nautilus"
    )


Nautilus, VERSION_NAUTILUS = _cargar_nautilus()

try:  # Nautilus 46 (24.04) y Nautilus 50 (26.04) son GTK4
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk  # noqa: E402
except Exception:  # pragma: no cover - sólo defensivo
    Gdk = None

try:
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk  # noqa: E402
except Exception:  # pragma: no cover
    Gtk = None

DESKTOP_ID = "com.copiex.Manager.desktop"
CABECERA_CLIPBOARD = "x-special/nautilus-clipboard"

# Últimos elementos marcados con «Copiar con Copiex» (memoria de la extensión)
_seleccion: list = []


# ----------------------------------------------------------------------
# comunicación con la aplicación
# ----------------------------------------------------------------------
def _ruta_socket() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(base, f"copiex-{os.getuid()}", "copiex.sock")


def _arrancar_app():
    """Arranca Copiex desde su fichero .desktop si aún no está en ejecución."""
    try:
        info = Gio.DesktopAppInfo.new(DESKTOP_ID)
        if info is not None:
            info.launch([], None)
            return True
    except Exception:
        pass
    return False


def _enviar(mensaje: dict) -> bool:
    ruta = _ruta_socket()
    ultimo_error = None
    for intento in range(3):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(4.0)
                sock.connect(ruta)
                sock.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
                sock.recv(4096)  # respuesta de la aplicación
            return True
        except OSError as exc:
            ultimo_error = exc
            if intento == 0:
                _arrancar_app()
            time.sleep(1.5)
    print(f"Copiex: no se pudo contactar con la aplicación: {ultimo_error}")
    return False


def _enviar_async(mensaje: dict):
    threading.Thread(
        target=_enviar, args=(mensaje,), name="copiex-ipc", daemon=True
    ).start()


# ----------------------------------------------------------------------
# portapapeles (formato nativo de Nautilus)
# ----------------------------------------------------------------------
def _marcar_portapapeles(uris: list):
    """Copia la selección al portapapeles con el formato de Nautilus, para que
    un posterior Ctrl+V normal también funcione. Mejor esfuerzo."""
    if Gdk is None or not uris:
        return
    try:
        texto = CABECERA_CLIPBOARD + "\ncopy\n" + "\n".join(uris)
        proveedor = Gdk.ContentProvider.new_union(
            [
                Gdk.ContentProvider.new_for_bytes(
                    CABECERA_CLIPBOARD, GLib.Bytes.new(texto.encode("utf-8"))
                ),
                Gdk.ContentProvider.new_for_bytes(
                    "text/plain;charset=utf-8",
                    GLib.Bytes.new("\n".join(uris).encode("utf-8")),
                ),
            ]
        )
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set_content(proveedor)
    except Exception:
        pass


def _del_portapapeles(texto: str) -> list:
    if not texto:
        return []
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if not lineas or not lineas[0].startswith(CABECERA_CLIPBOARD):
        return []
    return [l for l in lineas[2:] if l.startswith("file://")]


def _leer_portapapeles(callback):
    """Lee el portapapeles de forma asíncrona (GdkClipboard) y pasa el texto."""
    if Gdk is None:
        callback("")
        return
    try:
        display = Gdk.Display.get_default()
        if display is None:
            callback("")
            return
        display.get_clipboard().read_text_async(None, _portapapeles_leido, callback)
    except Exception:
        callback("")


def _portapapeles_leido(origen, resultado, callback):
    try:
        texto = origen.read_text_finish(resultado)
    except Exception:
        texto = ""
    callback(texto or "")


# ----------------------------------------------------------------------
# avisos
# ----------------------------------------------------------------------
def _aviso(texto: str, detalle: str = ""):
    if Gtk is None:
        print(f"Copiex: {texto} {detalle}")
        return
    try:
        alerta = Gtk.AlertDialog(message=texto)
        if detalle:
            alerta.set_detail(detalle)
        alerta.show(None)
    except Exception:
        print(f"Copiex: {texto} {detalle}")


# ----------------------------------------------------------------------
# acciones del menú
# ----------------------------------------------------------------------
def _al_copiar(uris: list):
    global _seleccion
    _seleccion = list(uris)
    _marcar_portapapeles(_seleccion)


def _al_pegar(destino: str):
    uris = list(_seleccion)
    if uris:
        _enviar_async({"cmd": "copy", "sources": uris, "dest": destino})
        return

    def con_portapapeles(texto):
        uris_clip = _del_portapapeles(texto)
        if not uris_clip:
            _aviso(
                "No hay nada que pegar",
                "Selecciona los ficheros y usa «Copiar con Copiex» "
                "(o Ctrl+C en Nautilus) antes de pegarlos aquí.",
            )
            return
        _enviar_async({"cmd": "copy", "sources": uris_clip, "dest": destino})

    _leer_portapapeles(con_portapapeles)


# ----------------------------------------------------------------------
# proveedor de menús de Nautilus
# ----------------------------------------------------------------------
class ExtencionCopiex(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, files):
        uris = [f.get_uri() for f in files if f is not None and f.get_uri()]
        if not uris:
            return []
        item = Nautilus.MenuItem(
            name="Copiex::copiar",
            label="Copiar con Copiex",
            tip="Marca estos elementos para copiarlos con Copiex",
        )
        item.connect("activate", self._activar_copiar, uris)
        return [item]

    def get_background_items(self, current_folder):
        if current_folder is None or not current_folder.get_uri():
            return []
        destino = current_folder.get_uri()
        item = Nautilus.MenuItem(
            name="Copiex::pegar",
            label="Pegar con Copiex",
            tip="Copia aquí lo marcado con Copiex (o el portapapeles) "
            "con progreso, pausa y reanudación",
        )
        item.connect("activate", self._activar_pegar, destino)
        return [item]

    # ------------------------------------------------------------------
    def _activar_copiar(self, menu, uris):
        _al_copiar(uris)

    def _activar_pegar(self, menu, destino):
        _al_pegar(destino)
