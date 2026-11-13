# -*- coding: utf-8 -*-
"""Ventana principal: historial de copias y sus progresos."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from .menu import texto
from .util import (
    APP_NAME,
    fmt_bytes,
    fmt_restante,
    fmt_velocidad,
    resumen_origenes,
    short_path,
)

ESTADOS_OK = ("running", "paused")


class VentanaCopias(Adw.ApplicationWindow):
    """Lista de copias: activas, en pausa y ya finalizadas."""

    def __init__(self, app):
        super().__init__(
            application=app,
            title=APP_NAME,
            default_width=820,
            default_height=560,
        )
        self._app = app
        self._filas = {}  # id de copia -> widgets

        self._overlay = Adw.ToastOverlay()
        self.set_content(self._overlay)

        vista = Adw.ToolbarView()
        self._overlay.set_child(vista)

        cabecera = Adw.HeaderBar()
        cabecera.set_title_widget(
            Adw.WindowTitle(title=APP_NAME, subtitle=texto("ventana.subtitulo"))
        )

        nueva = Gtk.Button(
            label=texto("menu.nueva"), css_classes=["suggested-action"]
        )
        nueva.connect("clicked", lambda *_: app.pedir_nueva_copia())
        cabecera.pack_start(nueva)

        menu = Gtk.MenuButton(icon_name="open-menu-symbolic")
        modelo = Gio.Menu()
        modelo.append(texto("menu.ocultar"), "app.ocultar")
        modelo.append(texto("menu.acerca"), "app.acerca")
        modelo.append(texto("menu.salir"), "app.salir")
        menu.set_menu_model(modelo)
        cabecera.pack_end(menu)
        vista.add_top_bar(cabecera)

        contenedor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for lado in ("top", "bottom", "start", "end"):
            getattr(contenedor, f"set_margin_{lado}")(12)

        self._vacio = Adw.StatusPage(
            icon_name="edit-copy",
            title=texto("ventana.vacio_titulo"),
            description=texto("ventana.vacio_descripcion"),
        )
        contenedor.append(self._vacio)

        self._lista = Gtk.ListBox(css_classes=["boxed-list"])
        self._lista.set_selection_mode(Gtk.SelectionMode.NONE)
        contenedor.append(self._lista)

        scroll = Gtk.ScrolledWindow(child=contenedor, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vista.set_content(scroll)

        self.connect("close-request", self._al_cerrar)

    # ------------------------------------------------------------------
    # acciones de la ventana
    # ------------------------------------------------------------------
    def _al_cerrar(self, *_args):
        # Cerrar la ventana solo la oculta: las copias siguen en segundo plano
        self.hide()
        return True

    def aviso(self, texto: str):
        self._overlay.add_toast(Adw.Toast(title=texto, timeout=5))

    # ------------------------------------------------------------------
    # filas
    # ------------------------------------------------------------------
    def sincronizar(self, operaciones):
        """Ajusta la lista al estado actual del motor."""
        ops = sorted(operaciones, key=lambda o: o.id, reverse=True)
        if {o.id for o in ops} != set(self._filas):
            self._reconstruir(ops)
        for op in ops:
            fila = self._filas.get(op.id)
            if fila is not None:
                self._actualizar(fila, op)
        self._vacio.set_visible(not ops)
        self._lista.set_visible(bool(ops))

    def actualizar(self, op):
        fila = self._filas.get(op.id)
        if fila is None:
            return  # aparecerá al sincronizar
        self._actualizar(fila, op)

    def _reconstruir(self, ops):
        while (fila := self._lista.get_row_at_index(0)) is not None:
            self._lista.remove(fila)
        self._filas = {}
        for op in ops:  # los más recientes primero
            self._fila_de(op)

    def _fila_de(self, op):
        row = Gtk.ListBoxRow()
        caja = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        caja.set_margin_top(14)
        caja.set_margin_bottom(14)
        caja.set_margin_start(16)
        caja.set_margin_end(16)

        datos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, hexpand=True)
        titulo = Gtk.Label(
            label=short_path(op.destino), xalign=0, css_classes=["heading"]
        )
        titulo.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        subtitulo = Gtk.Label(
            label=resumen_origenes(op.origenes),
            xalign=0,
            css_classes=["caption", "dim-label"],
        )
        subtitulo.set_ellipsize(Pango.EllipsizeMode.END)
        barra = Gtk.ProgressBar(show_text=True)
        estado = Gtk.Label(xalign=0, css_classes=["caption", "dim-label"])
        estado.set_wrap(True)
        for widget in (titulo, subtitulo, barra, estado):
            datos.append(widget)

        controles = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
        )
        btn_pausa = Gtk.Button(label=texto("acciones.pausar"))
        btn_pausa.connect("clicked", self._al_pausar, op.id)
        btn_cancelar = Gtk.Button(
            label=texto("acciones.cancelar"), css_classes=["destructive-action"]
        )
        btn_cancelar.connect("clicked", self._al_cancelar, op.id)
        controles.append(btn_pausa)
        controles.append(btn_cancelar)

        caja.append(datos)
        caja.append(controles)
        row.set_child(caja)
        self._lista.insert(row, 0)

        fila = {
            "row": row,
            "barra": barra,
            "estado": estado,
            "pausa": btn_pausa,
            "cancelar": btn_cancelar,
        }
        self._filas[op.id] = fila
        return fila

    def _actualizar(self, fila, op):
        fila["barra"].set_fraction(op.fraccion)
        if op.total_bytes > 0:
            fila["barra"].set_text(
                f"{fmt_bytes(op.copiados)} de {fmt_bytes(op.total_bytes)}"
            )
        else:
            fila["barra"].set_text("")

        etiqueta = fila["estado"]
        etiqueta.remove_css_class("error")

        # Los botones solo tienen sentido mientras la copia puede seguir
        accionable = op.estado in ("running", "paused", "error")
        fila["pausa"].set_visible(accionable)
        fila["cancelar"].set_visible(accionable)

        if op.estado == "running":
            partes = []
            if op.velocidad > 0:
                partes.append(fmt_velocidad(op.velocidad))
            restante = op.restante
            if restante is not None:
                partes.append(f"quedan {fmt_restante(restante)}")
            partes.append(f"{op.archivos_ok}/{op.total_archivos} elementos")
            etiqueta.set_text("Copiando · " + " · ".join(partes))
            fila["pausa"].set_label(texto("acciones.pausar"))
        elif op.estado == "paused":
            # `espera` explica por qué el vigilante aún no la ha reanudado
            detalle = op.espera or (
                f"{fmt_bytes(op.copiados)} copiados "
                f"({op.archivos_ok}/{op.total_archivos} elementos)"
            )
            etiqueta.set_text(f"En pausa · {detalle}")
            fila["pausa"].set_label(texto("acciones.reanudar"))
        elif op.estado == "error":
            detalle = op.error or "fallo desconocido"
            if op.espera:
                detalle += f" · {op.espera}"
            etiqueta.set_text(f"Error: {detalle}")
            etiqueta.add_css_class("error")
            fila["pausa"].set_label(texto("acciones.reintentar"))
        elif op.estado == "done":
            etiqueta.set_text(
                f"Completada · {fmt_bytes(op.total_bytes)} en "
                f"{op.total_archivos} elementos"
            )
        else:  # cancelled
            etiqueta.set_text(
                f"Cancelada · {fmt_bytes(op.copiados)} de {fmt_bytes(op.total_bytes)}"
            )

    # ------------------------------------------------------------------
    def _al_pausar(self, boton, op_id):
        op = self._app.motor.obtener(op_id)
        if op is None:
            return
        if op.estado == "running":
            self._app.motor.pausar(op_id)
        elif op.estado in ("paused", "error"):
            self._app.motor.reanudar(op_id)
        self.actualizar(op)

    def _al_cancelar(self, boton, op_id):
        self._app.motor.cancelar(op_id)
        op = self._app.motor.obtener(op_id)
        if op is not None:
            self.actualizar(op)
