# -*- coding: utf-8 -*-
"""Vigilante: reanuda las copias cuando el origen y el destino vuelven a estar.

Cubre el requerimiento 8 (continuar tras cerrar la aplicación) y el error 2
(reintentar cuando un dispositivo desconectado reaparece). Nunca toca las
copias que el usuario pausó a mano: esa marca vive en el historial
(`pausa_manual`) y sobrevive al reinicio.

Deliberadamente no guarda estado propio: cada pasada mira lo que hay y decide.
El propio intervalo entre pasadas es la espera antes de reintentar un fallo.
"""

from __future__ import annotations

import logging
import os
import threading

from .util import short_path

INTERVALO = 6.0  # segundos entre revisiones

log = logging.getLogger(__name__)


class Vigilante(threading.Thread):
    """Revisa las copias en pausa o con error y las reanuda cuando se puede."""

    def __init__(self, motor, al_reanudar, intervalo=INTERVALO):
        super().__init__(name="vigilante", daemon=True)
        self.motor = motor
        self.al_reanudar = al_reanudar  # callable(operacion), se pasa al hilo de GTK
        self.intervalo = intervalo
        self._parar = threading.Event()

    def detener(self):
        self._parar.set()

    def run(self):
        while not self._parar.wait(self.intervalo):
            try:
                self._revisar()
            except Exception:
                log.exception("vigilante: fallo en la revisión")

    def _revisar(self):
        for op in self.motor.todas():
            if op.estado not in ("paused", "error") or op.pausa_manual:
                continue
            motivo = self._motivo_espera(op)
            cambio = op.anotar_espera(motivo)  # la ventana muestra por qué espera
            if motivo:
                if cambio:  # una vez por motivo, no cada 6 segundos
                    log.info("vigilante: copia %s espera: %s", op.id, motivo)
            else:
                log.info("vigilante: copia %s puede continuar", op.id)
                self.al_reanudar(op)

    @staticmethod
    def _motivo_espera(op) -> str:
        """Cadena vacía si la copia puede continuar; si no, el motivo.

        Basta con que falte una de las carpetas de destino para esperar: así
        una copia a varios USB se reanuda entera cuando vuelven todos, igual
        que cuando solo había un destino.
        """
        for destino in getattr(op, "destinos", []):
            if destino.estado != "done" and not os.path.isdir(destino.ruta):
                return f"esperando la carpeta de destino {short_path(destino.ruta)}"
        for origen in op.origenes:
            try:
                os.stat(origen)
            except OSError:  # no existe, o el dispositivo no responde
                return f"esperando a que aparezca {short_path(origen)}"
        return ""
