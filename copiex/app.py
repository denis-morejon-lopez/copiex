# -*- coding: utf-8 -*-
"""Aplicación: une motor, historial, ventana, bandeja e IPC."""

from __future__ import annotations

import logging
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .engine import ErrorCopia, Motor  # noqa: E402
from . import __version__  # noqa: E402
from .ipc import ServidorIpc  # noqa: E402
from .menu import texto  # noqa: E402
from .sound import reproducir  # noqa: E402
from .logs import configurar_registro  # noqa: E402
from .store import Store  # noqa: E402
from .tray import Bandeja  # noqa: E402
from .util import APP_ID, APP_NAME, socket_path, uri_to_path  # noqa: E402
from .watcher import Vigilante  # noqa: E402
from .window import VentanaCopias  # noqa: E402

log = logging.getLogger(__name__)


class Aplicacion(Adw.Application):
    def __init__(self, *, application_id=APP_ID, db_ruta=None,
                 activar_bandeja=True, activar_ipc=True, iniciar_oculto=False):
        super().__init__(
            application_id=application_id, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.db_ruta = db_ruta
        self.activar_bandeja = activar_bandeja
        self.activar_ipc = activar_ipc
        # Arranque pedido desde Nautilus: solo bandeja, sin ventana delante.
        self._iniciar_oculto = iniciar_oculto
        self.store = None
        self.motor = None
        self.ventana = None
        self.ipc = None
        self.bandeja = None
        self.vigilante = None
        self._sonadas = set()  # copias cuyo final ya se ha avisado con sonido

    # ------------------------------------------------------------------
    def do_startup(self):
        Adw.Application.do_startup(self)
        self.hold()  # la app sigue viva con la ventana oculta

        self.store = Store(self.db_ruta)
        self.motor = Motor(self.store)
        self.motor.agregar_oyente(self._cambio_en_hilo_motor)
        recuperadas = self.motor.cargar_historial()
        if recuperadas:
            log.info("%d copia(s) en pausa recuperadas del historial", len(recuperadas))

        # Reanuda sola las copias que quedaron a medias o fallaron por un
        # dispositivo ausente (nunca las que el usuario pausó a mano).
        self.vigilante = Vigilante(
            self.motor, lambda op: GLib.idle_add(self._aplicar_reanudacion, op.id)
        )
        self.vigilante.start()

        for nombre, metodo in (
            ("nueva", self.pedir_nueva_copia),
            ("ocultar", self.ocultar_ventana),
            ("acerca", self.acerca),
            ("salir", self.salir),
        ):
            accion = Gio.SimpleAction.new(nombre, None)
            accion.connect("activate", lambda _a, _p, m=metodo: m())
            self.add_action(accion)

        if self.activar_ipc:
            self.ipc = ServidorIpc(socket_path(), self._mensaje_ipc)
            self.ipc.start()
            log.info("IPC escuchando en %s", socket_path())

        if self.activar_bandeja:
            try:
                self.bandeja = Bandeja(
                    al_pulsar=self.alternar_ventana,
                    al_ocultar=self.alternar_ventana,
                    al_salir=self.salir,
                )
                self._visibilidad_cambiada()  # aún sin ventana: «Mostrar ventana»
            except Exception:
                # Sin bandeja la app sigue siendo útil (ventana + historial)
                log.exception("No se pudo crear el icono de bandeja")
                self.bandeja = None

    def do_activate(self, *_args):
        if self._iniciar_oculto:
            self._iniciar_oculto = False
            log.info("Arranque en bandeja (sin ventana)")
            return
        if self.ventana is None:
            self.ventana = VentanaCopias(self)
            self.ventana.connect("notify::visible", self._visibilidad_cambiada)
            self.ventana.sincronizar(self.motor.todas())
        log.debug("ventana mostrada")
        self.ventana.present()
        self._visibilidad_cambiada()

    # ------------------------------------------------------------------
    # copias
    # ------------------------------------------------------------------
    def crear_copia(self, origenes, destino, mostrar=True):
        """Crea una copia. Se llama siempre desde el hilo principal."""
        try:
            op = self.motor.crear(origenes, destino)
        except ErrorCopia as exc:
            log.warning("No se pudo crear la copia: %s", exc)
            if self.ventana is not None:
                self.ventana.aviso(str(exc))
            return None
        log.info("Copia id=%s creada en la cola: %s -> %s", op.id, origenes, destino)
        if mostrar and self.ventana is None:
            self.do_activate()  # la tarea tiene que verse: se abre la ventana
        if self.ventana is not None:
            self.ventana.sincronizar(self.motor.todas())
            if mostrar:
                self.ventana.present()
        return op

    def pedir_nueva_copia(self):
        if self.ventana is None:
            self.do_activate()
        dialogo = Gtk.FileDialog(title=texto("dialogos.origen_titulo"))
        dialogo.open_multiple(self.ventana, None, self._origenes_elegidos)

    def _origenes_elegidos(self, dialogo, resultado, *_):
        try:
            lista = dialogo.open_multiple_finish(resultado)
        except GLib.Error:
            return  # cancelado por el usuario
        origenes = []
        for i in range(lista.get_n_items()):
            fichero = lista.get_item(i)
            ruta = fichero.get_path() if fichero is not None else None
            if ruta:
                origenes.append(ruta)
        if not origenes:
            return
        dialogo2 = Gtk.FileDialog(title=texto("dialogos.destino_titulo"))
        dialogo2.select_folder(
            self.ventana, None, lambda d, r, o=origenes: self._destino_elegido(o, d, r)
        )

    def _destino_elegido(self, origenes, dialogo, resultado, *_):
        try:
            carpeta = dialogo.select_folder_finish(resultado)
        except GLib.Error:
            return
        if carpeta is None or carpeta.get_path() is None:
            return
        self.crear_copia(origenes, carpeta.get_path())

    # ------------------------------------------------------------------
    def _cambio_en_hilo_motor(self, op):
        """Se ejecuta en un hilo del motor: se traslada al hilo de GTK."""
        GLib.idle_add(self._aplicar_cambio, op)

    def _aplicar_cambio(self, op):
        # Una sola alerta por copia, y solo al completarse (requerimiento 9)
        if op.estado == "done" and op.id not in self._sonadas:
            self._sonadas.add(op.id)
            reproducir()
        if self.ventana is not None:
            self.ventana.actualizar(op)
        return False  # no volver a invocar

    # ------------------------------------------------------------------
    # IPC con la extensión de Nautilus (se ejecuta en el hilo del socket)
    # ------------------------------------------------------------------
    def _mensaje_ipc(self, mensaje):
        comando = mensaje.get("cmd")
        if comando == "log":
            # La extensión de Nautilus no tiene dónde escribir: sus trazas se
            # recogen aquí para que todo quede en el mismo copiex.log.
            texto = str(mensaje.get("texto") or "").strip()[:1000]
            if texto:
                log.info("Nautilus: %s", texto)
            return {"ok": True}
        log.debug("IPC: %s", mensaje)
        if comando == "ping":
            return {"ok": True, "pid": os.getpid()}
        if comando == "show":
            GLib.idle_add(self.mostrar_ventana)
            return {"ok": True}
        if comando == "copy":
            log.info("Petición de copia desde Nautilus: %s", mensaje.get("sources"))
            try:
                origenes = [uri_to_path(u) for u in (mensaje.get("sources") or [])]
                destino = uri_to_path(mensaje.get("dest") or "")
                if not origenes:
                    raise ValueError("Nautilus no ha indicado ningún origen")
                for origen in origenes:
                    if not os.path.exists(origen):
                        raise ValueError(f"No existe: {origen}")
                if not os.path.isdir(destino):
                    raise ValueError(f"El destino no es una carpeta: {destino}")
            except Exception as exc:  # respuesta de error a la extensión
                log.warning("IPC copy rechazado: %s", exc)
                return {"ok": False, "error": str(exc)}
            GLib.idle_add(self._crear_copia_desde_ipc, origenes, destino)
            return {"ok": True}
        return {"ok": False, "error": f"comando desconocido: {comando}"}

    def _crear_copia_desde_ipc(self, origenes, destino):
        """Crea la copia pedida por la extensión. Devuelve False porque
        GLib.idle_add repetiría la llamada mientras el callback sea verdadero."""
        self.crear_copia(origenes, destino)
        return False

    # ------------------------------------------------------------------
    # reanudación automática
    # ------------------------------------------------------------------
    def _aplicar_reanudacion(self, op_id):
        """Reanuda en el hilo de GTK la copia que pide el vigilante."""
        if self.motor.reanudar(op_id):
            log.info("Copia %s reanudada automáticamente", op_id)
            if self.ventana is not None:
                self.ventana.sincronizar(self.motor.todas())
        return False

    # ------------------------------------------------------------------
    # ventana y bandeja
    # ------------------------------------------------------------------
    def mostrar_ventana(self):
        self.do_activate()
        return False

    def ocultar_ventana(self, *_args):
        if self.ventana is not None:
            self.ventana.hide()
        return False

    def acerca(self, *_args):
        """«Acerca de»: descripción corta y versión (requerimiento 10)."""
        dialogo = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon="edit-copy",
            version=__version__,
            comments=texto("aplicacion.descripcion"),
        )
        dialogo.present(self.ventana)
        log.debug("mostrado «Acerca de» (versión %s)", __version__)

    def alternar_ventana(self):
        if self.ventana is None or not self.ventana.get_visible():
            self.mostrar_ventana()
        else:
            self.ocultar_ventana()

    def _visibilidad_cambiada(self, *_args):
        # Sin ventana creada (arranque en bandeja) la opción correcta es
        # «Mostrar ventana»: la ventana no existe, así que no hay nada que ocultar.
        if self.bandeja is None:
            return
        visible = self.ventana is not None and self.ventana.get_visible()
        self.bandeja.cambiar_etiqueta(
            texto("menu.ocultar") if visible else texto("menu.mostrar")
        )

    # ------------------------------------------------------------------
    def salir(self, *_args):
        log.info("Saliendo: se pausan las copias en curso")
        try:
            if self.vigilante is not None:
                self.vigilante.detener()
            if self.motor is not None:
                self.motor.apagar(2.0)
            if self.ipc is not None:
                self.ipc.cerrar()
            if self.bandeja is not None:
                self.bandeja.destruir()
            if self.store is not None:
                self.store.cerrar()
        finally:
            self.quit()
        return False


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv)
    iniciar_oculto = "--bandeja" in argv
    argv = [a for a in argv if a != "--bandeja"]
    # Un único copiex.log en DEBUG con una semana de historial: es el fichero
    # que hay que enviar si algo va mal (poda y tamaño se cuidan en logs.py).
    try:
        ruta_log = configurar_registro()
    except Exception:  # sin registro se sigue funcionando igual
        logging.getLogger(__name__).warning("No se pudo abrir el registro en disco")
        ruta_log = "(sin fichero)"
    log.info(
        "Copiex %s arranca (pid %s, %s) — registro en %s",
        __version__,
        os.getpid(),
        "bandeja" if iniciar_oculto else "ventana",
        ruta_log,
    )
    app = Aplicacion(iniciar_oculto=iniciar_oculto)
    return app.run(argv or sys.argv)
