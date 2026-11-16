# -*- coding: utf-8 -*-
"""Rutas, URIs y formatos compartidos por todo el programa."""

from __future__ import annotations

import os
import tempfile
import urllib.parse

APP_ID = "com.copiex.Manager"
APP_NAME = "Copiex"
EXTENSION_NAME = "copiex.py"

ICONO_APP = "com.copiex.Manager"
ICONO_BANDEJA = "com.copiex.Manager-symbolic"
ICONO_RESERVA = "edit-copy"


def icono_disponible(nombre: str) -> str:
    """Devuelve `nombre` si el tema de iconos lo tiene; si no, el de reserva.

    Los iconos propios los instala el paquete .deb en /usr/share/icons (antes
    ./install.sh en ~/.local/share/icons). Si la app se ejecuta sin instalar, se
    usa el icono genérico del tema y no queda un hueco vacío.
    """
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gdk, Gtk

        display = Gdk.Display.get_default()
        if display is not None:
            if Gtk.IconTheme.get_for_display(display).has_icon(nombre):
                return nombre
    except Exception:
        pass  # sin GTK o sin tema, se usa el de reserva
    return ICONO_RESERVA


def runtime_dir() -> str:
    """Directorio privado del usuario para el socket IPC."""
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    path = os.path.join(base, f"copiex-{os.getuid()}")
    try:
        os.makedirs(path, exist_ok=True)
        os.chmod(path, 0o700)
    except OSError:
        path = tempfile.gettempdir()
    return path


def socket_path() -> str:
    return os.path.join(runtime_dir(), "copiex.sock")


def data_dir() -> str:
    """Directorio de datos persistentes (~/.local/share/copiex)."""
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "copiex")
    os.makedirs(path, exist_ok=True)
    return path


def uri_to_path(uri: str) -> str:
    """Convierte una URI en ruta local.

    Acepta rutas locales, `file://` y `mtp://` (móviles y cámaras). MTP se
    resuelve a su punto de montaje de gvfs-fuse, así el motor sigue trabajando
    con rutas normales; sin gvfs-fuse no hay ruta y se avisa con claridad.
    """
    uri = (uri or "").strip()
    if not uri:
        raise ValueError("Ruta vacía")
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme == "":
        return os.path.abspath(os.path.expanduser(uri))
    if parsed.scheme == "mtp":
        path = _ruta_gvfs(uri)
        if not path:
            raise ValueError(
                f"No se pudo acceder a «{uri}»: hace falta gvfs-fuse "
                "(sudo apt install gvfs-fuse) y el dispositivo montado"
            )
        return path
    if parsed.scheme != "file":
        raise ValueError(f"Solo se admiten rutas locales o mtp://, no «{uri}»")
    path = urllib.parse.unquote(parsed.path)
    if parsed.netloc and parsed.netloc not in ("", "localhost"):
        path = f"//{parsed.netloc}{path}"
    if not path:
        raise ValueError(f"URI no válida: {uri}")
    return path


def _ruta_gvfs(uri: str) -> str | None:
    """Ruta de gvfs-fuse para una URI de gvfs (None si no está disponible)."""
    try:
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio

        return Gio.File.new_for_uri(uri).get_path()
    except Exception:
        return None


def es_mtp(ruta: str) -> bool:
    """¿La ruta es un montaje MTP a través de gvfs-fuse?"""
    return bool(ruta) and "/gvfs/mtp:host=" in os.path.abspath(ruta)


def ruta_a_uri(ruta: str) -> str:
    """URI mostrable de una ruta: `mtp://…` si es un montaje MTP."""
    ruta = os.path.abspath(ruta)
    marca = "/gvfs/mtp:host="
    if marca in ruta:
        host, _, resto = ruta.split(marca, 1)[1].partition("/")
        return "mtp://" + urllib.parse.quote(host, safe="") + "/" + urllib.parse.quote(
            resto, safe="/"
        )
    return path_to_uri(ruta)


def path_to_uri(path: str) -> str:
    return "file://" + urllib.parse.quote(os.path.abspath(path))


def short_path(path: str) -> str:
    """Ruta abreviada mostrada en la interfaz («~/Descargas/...», `mtp://…`)."""
    if es_mtp(path):
        # La URI va percent-encoded, pero en una etiqueta se lee mejor sin eso.
        return urllib.parse.unquote(ruta_a_uri(path))
    home = os.path.expanduser("~")
    path = os.path.abspath(path)
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def fmt_bytes(cantidad: float) -> str:
    from gi.repository import GLib  # import perezoso: el motor no necesita gi

    return GLib.format_size(int(max(0, cantidad)))


def fmt_velocidad(bps: float) -> str:
    return f"{fmt_bytes(bps)}/s"


def fmt_restante(segundos: float) -> str:
    seg = int(max(0, segundos))
    if seg < 60:
        return f"{seg} s"
    if seg < 3600:
        return f"{seg // 60} min {seg % 60} s"
    return f"{seg // 3600} h {(seg % 3600) // 60} min"


def resumen_origenes(origenes, maximo: int = 3) -> str:
    """Texto corto con los orígenes de una copia."""
    if not origenes:
        return ""
    if len(origenes) == 1:
        return f"Desde {short_path(origenes[0])}"
    lista = ", ".join(short_path(p) for p in origenes[:maximo])
    extra = len(origenes) - maximo
    if extra > 0:
        lista += f" y {extra} más"
    return f"{len(origenes)} elementos desde {os.path.dirname(short_path(origenes[0]))}: {lista}"