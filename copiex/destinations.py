# -*- coding: utf-8 -*-
"""Diálogo de destinos de una copia lanzada desde la ventana principal.

Es el equivalente en la ventana de «Pegar con Copiex N destinos» de Nautilus:
acumula carpetas y las entrega todas juntas a `Aplicacion.crear_copia`, que lee
el origen una sola vez y escribe en cada destino.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

from .menu import texto  # noqa: E402
from .util import short_path  # noqa: E402

MAX_DESTINOS = 16  # mismo tope que la ventana de Nautilus
_ABIERTOS = set()  # mantiene viva la ventana modal mientras se usa


class DialogoDestinos(Adw.Window):
    """Acumula carpetas de destino para una copia desde la ventana principal.

    Se abre con la primera carpeta ya elegida (la del selector «¿Dónde quieres
    copiarlo?»); «Añadir otra carpeta» suma destinos y «Comenzar la copia» crea
    la operación con todos ellos. Cerrar la ventana cancela.
    """

    def __init__(self, padre, origenes, al_empezar, primer_destino=None):
        super().__init__(
            transient_for=padre,
            modal=True,
            title=texto("dialogos.destinos_titulo"),
            default_width=560,
            default_height=420,
        )
        self._origenes = list(origenes)
        self._al_empezar = al_empezar
        self._destinos = [primer_destino] if primer_destino else []

        vista = Adw.ToolbarView()
        cabecera = Adw.HeaderBar()
        cabecera.set_title_widget(
            Adw.WindowTitle(title=texto("dialogos.destinos_titulo"))
        )
        vista.add_top_bar(cabecera)

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for lado in ("top", "bottom", "start", "end"):
            getattr(caja, f"set_margin_{lado}")(16)

        ayuda = Gtk.Label(
            label=texto("dialogos.destinos_ayuda"),
            wrap=True,
            xalign=0,
            css_classes=["dim-label"],
        )
        caja.append(ayuda)

        self._lista = Gtk.ListBox(css_classes=["boxed-list"])
        self._lista.set_selection_mode(Gtk.SelectionMode.NONE)
        self._vacio = Gtk.Label(
            label=texto("dialogos.sin_destinos"),
            wrap=True,
            css_classes=["dim-label"],
        )
        self._vacio.set_margin_top(12)
        self._vacio.set_margin_bottom(12)
        self._lista.set_placeholder(self._vacio)

        scroll = Gtk.ScrolledWindow(child=self._lista, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        caja.append(scroll)

        botones = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            halign=Gtk.Align.END,
        )
        self._anadir = Gtk.Button(label=texto("dialogos.anadir_destino"))
        self._anadir.connect("clicked", self._al_anadir)
        self._empezar = Gtk.Button(
            label=texto("dialogos.empezar_copia"),
            css_classes=["suggested-action"],
        )
        self._empezar.connect("clicked", self._al_pulsar_empezar)
        botones.append(self._anadir)
        botones.append(self._empezar)
        caja.append(botones)

        vista.set_content(caja)
        self.set_content(vista)
        self.set_default_widget(self._empezar)
        self.connect("close-request", self._al_cerrar)
        _ABIERTOS.add(self)
        self._refrescar()

    # ------------------------------------------------------------------
    def _refrescar(self):
        while (fila := self._lista.get_row_at_index(0)) is not None:
            self._lista.remove(fila)
        for numero, ruta in enumerate(self._destinos, 1):
            etiqueta = Gtk.Label(
                label=f"{numero}. {short_path(ruta)}", xalign=0, hexpand=True
            )
            etiqueta.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            etiqueta.set_tooltip_text(ruta)
            quitar = Gtk.Button(
                icon_name="list-remove-symbolic",
                css_classes=["flat"],
                valign=Gtk.Align.CENTER,
            )
            quitar.set_tooltip_text(texto("dialogos.quitar_destino"))
            quitar.connect("clicked", self._al_quitar, ruta)
            caja = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            for lado in ("top", "bottom", "start", "end"):
                getattr(caja, f"set_margin_{lado}")(8)
            caja.append(etiqueta)
            caja.append(quitar)
            fila = Gtk.ListBoxRow()
            fila.set_child(caja)
            self._lista.append(fila)
        self._empezar.set_sensitive(bool(self._destinos))
        self._anadir.set_sensitive(len(self._destinos) < MAX_DESTINOS)

    def _al_anadir(self, *_args):
        dialogo = Gtk.FileDialog(title=texto("dialogos.elegir_destino_titulo"))
        dialogo.select_folder(self, None, self._carpeta_elegida)

    def _carpeta_elegida(self, dialogo, resultado, *_args):
        try:
            carpeta = dialogo.select_folder_finish(resultado)
        except GLib.Error:
            return  # cancelado: se queda como estaba
        ruta = carpeta.get_path() if carpeta is not None else None
        if not ruta or ruta in self._destinos:
            return  # ya estaba: no se repite
        self._destinos.append(ruta)
        self._refrescar()

    def _al_quitar(self, _boton, ruta):
        if ruta in self._destinos:
            self._destinos.remove(ruta)
            self._refrescar()

    # ------------------------------------------------------------------
    def _al_pulsar_empezar(self, *_args):
        if not self._destinos:
            return
        origenes = list(self._origenes)
        destinos = list(self._destinos)
        # Cerrar primero la ventana modal y crear la copia al volver al bucle
        # principal: así no queda ningún diálogo delante del historial.
        self.close()
        GLib.idle_add(self._lanzar, origenes, destinos)

    def _lanzar(self, origenes, destinos):
        """Crea la copia pedida por el diálogo. Devuelve False porque
        `GLib.idle_add` repetiría la llamada mientras el callback sea verdadero."""
        self._al_empezar(origenes, destinos)
        return False

    def _al_cerrar(self, *_args):
        _ABIERTOS.discard(self)
        return False  # GTK destruye la ventana
