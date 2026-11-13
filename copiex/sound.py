# -*- coding: utf-8 -*-
"""Alerta sonora al terminar una copia (requerimiento 9).

El sonido vive en la carpeta `sounds/` del proyecto: se reproduce el primer
fichero de audio que haya allí, con preferencia por `copy-finished.*`. Así se
cambia la alarma descargando otro fichero y dejándolo en esa carpeta, sin tocar
el código. Si no hay ninguno, se usa el sonido «Complete» del sistema y, como
último recurso, el pitido del servidor gráfico.

Nunca bloquea: el reproductor se lanza en segundo plano y no se espera su salida.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from urllib.parse import quote

log = logging.getLogger(__name__)

# Formatos que pueden aparecer en sounds/. OGG y WAV son los más seguros:
# canberra y paplay los reproducen sin más; el resto necesita gst-launch.
_EXTENSIONES = (".oga", ".ogg", ".wav", ".flac", ".mp3", ".opus", ".m4a", ".aac")
_NOMBRE_PREFERIDO = "copy-finished"

_AVISADO = False


def carpeta() -> str:
    """Carpeta de sonidos del proyecto (o la de COPIEX_SOUNDS, para pruebas)."""
    elegida = os.environ.get("COPIEX_SOUNDS")
    if elegida:
        return elegida
    paquete = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(paquete), "sounds")


def fichero() -> str | None:
    """Fichero de audio que se usará como alarma, o None si no hay ninguno."""
    directorio = carpeta()
    try:
        nombres = sorted(os.listdir(directorio))
    except OSError:
        return None
    candidatos = [n for n in nombres if n.lower().endswith(_EXTENSIONES)]
    if not candidatos:
        return None
    for nombre in candidatos:
        if os.path.splitext(nombre)[0].lower() == _NOMBRE_PREFERIDO:
            return os.path.join(directorio, nombre)
    return os.path.join(directorio, candidatos[0])


def _ordenes(ruta: str | None) -> list[tuple[str, ...]]:
    ordenes: list[tuple[str, ...]] = []
    if ruta:
        ruta_abs = os.path.abspath(ruta)
        ordenes.append(("canberra-gtk-play", "-f", ruta_abs))
        ordenes.append(("paplay", ruta_abs))
        ordenes.append(
            ("gst-launch-1.0", "-q", "playbin", f"uri=file://{quote(ruta_abs)}")
        )
    # Sonido del tema del sistema, si no hay fichero propio o no se puede usar
    ordenes.append(("canberra-gtk-play", "--id=complete"))
    ordenes.append(
        ("paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga")
    )
    return ordenes


def reproducir() -> bool:
    """Emite la alerta de fin de copia. Devuelve True si algo la reprodujo."""
    global _AVISADO
    ruta = fichero()
    if ruta and not _AVISADO:
        _AVISADO = True
        log.info("alerta sonora: %s", ruta)
    for orden in _ordenes(ruta):
        if shutil.which(orden[0]) is None:
            continue
        try:
            subprocess.Popen(
                orden,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            log.debug("alerta sonora con %s", orden[0])
            return True
        except OSError as exc:
            log.debug("no se pudo usar %s: %s", orden[0], exc)
    try:
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is not None:
            display.beep()
            log.debug("alerta sonora con el aviso del servidor gráfico")
            return True
    except Exception as exc:
        log.debug("sin alerta sonora: %s", exc)
    return False
