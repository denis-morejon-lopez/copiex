# -*- coding: utf-8 -*-
"""Rutas, URIs y formatos compartidos por todo el programa."""

from __future__ import annotations

import os
import tempfile
import urllib.parse

APP_ID = "com.copiex.Manager"
APP_NAME = "Copiex"
EXTENSION_NAME = "copiex.py"


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
    """Convierte una URI file:// (o una ruta) en una ruta local."""
    uri = (uri or "").strip()
    if not uri:
        raise ValueError("Ruta vacía")
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme == "":
        return os.path.abspath(os.path.expanduser(uri))
    if parsed.scheme != "file":
        raise ValueError(f"Solo se admiten rutas locales, no «{uri}»")
    path = urllib.parse.unquote(parsed.path)
    if parsed.netloc and parsed.netloc not in ("", "localhost"):
        path = f"//{parsed.netloc}{path}"
    if not path:
        raise ValueError(f"URI no válida: {uri}")
    return path


def path_to_uri(path: str) -> str:
    return "file://" + urllib.parse.quote(os.path.abspath(path))


def short_path(path: str) -> str:
    """Ruta abreviada mostrada en la interfaz («~/Descargas/...»)."""
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