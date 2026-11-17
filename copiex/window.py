# -*- coding: utf-8 -*-
"""Ventana principal: historial de copias y sus progresos."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from .engine import texto_espera
from .menu import formato, texto
from .util import (
    APP_NAME,
    ICONO_APP,
    fmt_bytes,
    fmt_restante,
    fmt_velocidad,
    icono_disponible,
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
        self.set_icon_name("com.copiex.Manager")
        self._filas = {}  # id de copia -> widgets
        self._eliminadas = set()  # copias quitadas de la pantalla con «Eliminar»

        self._overlay = Adw.ToastOverlay()
        self.set_content(self._overlay)

        vista = Adw.ToolbarView()
        self._overlay.set_child(vista)

        cabecera = Adw.HeaderBar()
        # Título con el icono de Copiex justo después, como pide el usuario.
        titulo = Adw.WindowTitle(
            title=APP_NAME, subtitle=texto("ventana.subtitulo")
        )
        icono = Gtk.Image(icon_name=icono_disponible(ICONO_APP), pixel_size=22)
        icono.set_valign(Gtk.Align.CENTER)
        bloque_titulo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bloque_titulo.append(titulo)
        bloque_titulo.append(icono)
        cabecera.set_title_widget(bloque_titulo)

        nueva = Gtk.Button(
            label=texto("menu.nueva"), css_classes=["suggested-action"]
        )
        nueva.connect("clicked", lambda *_: app.pedir_nueva_copia())
        cabecera.pack_start(nueva)

        menu = Gtk.MenuButton(icon_name="open-menu-symbolic")
        modelo = Gio.Menu()
        modelo.append(texto("menu.ocultar"), "app.ocultar")
        idiomas = Gio.Menu()
        idiomas.append(texto("menu.espanol"), "app.idioma_es")
        idiomas.append(texto("menu.ingles"), "app.idioma_en")
        modelo.append_submenu(texto("menu.idioma"), idiomas)
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
        ops = sorted(
            (o for o in operaciones if o.id not in self._eliminadas),
            key=lambda o: o.id,
            reverse=True,
        )
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
        varios = len(op.destinos) > 1
        titulo = Gtk.Label(
            label=(formato("ventana.copia_varios", n=len(op.destinos)) if varios
                   else short_path(op.destino)),
            xalign=0,
            css_classes=["heading"],
        )
        titulo.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        subtitulo = Gtk.Label(
            label=resumen_origenes(op.origenes),
            xalign=0,
            css_classes=["caption", "dim-label"],
        )
        subtitulo.set_ellipsize(Pango.EllipsizeMode.END)

        # Con varios destinos, una línea por destino: cada cola se ve aparte.
        etiquetas_destino = []
        caja_destinos = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=1
        )
        if varios:
            for destino in op.destinos:
                linea = Gtk.Label(xalign=0, css_classes=["caption", "dim-label"])
                linea.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                caja_destinos.append(linea)
                etiquetas_destino.append(linea)

        barra = Gtk.ProgressBar(show_text=True)
        estado = Gtk.Label(xalign=0, css_classes=["caption", "dim-label"])
        estado.set_wrap(True)
        for widget in (titulo, subtitulo, caja_destinos, barra, estado):
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
        # Al terminar, «Cancelar» deja paso a «Eliminar»: quita la fila de la
        # pantalla (el historial de la base de datos se conserva).
        btn_eliminar = Gtk.Button(label=texto("acciones.eliminar"))
        btn_eliminar.connect("clicked", self._al_eliminar, op.id)
        controles.append(btn_pausa)
        controles.append(btn_cancelar)
        controles.append(btn_eliminar)

        caja.append(datos)
        caja.append(controles)
        row.set_child(caja)
        self._lista.insert(row, 0)

        fila = {
            "row": row,
            "barra": barra,
            "estado": estado,
            "destinos": etiquetas_destino,
            "pausa": btn_pausa,
            "cancelar": btn_cancelar,
            "eliminar": btn_eliminar,
        }
        self._filas[op.id] = fila
        return fila

    def _actualizar(self, fila, op):
        fila["barra"].set_fraction(op.fraccion)
        if op.total_bytes > 0:
            fila["barra"].set_text(
                formato(
                    "ventana.de",
                    hecho=fmt_bytes(op.copiados),
                    total=fmt_bytes(op.total_bytes),
                )
            )
        else:
            fila["barra"].set_text("")

        for linea, destino in zip(fila.get("destinos") or [], op.destinos):
            linea.remove_css_class("error")
            if destino.estado == "done":
                detalle = formato(
                    "ventana.completado", bytes=fmt_bytes(destino.total_bytes)
                )
            elif destino.estado == "paused":
                detalle = texto("ventana.en_pausa")
                if destino.espera:
                    detalle += f" · {texto_espera(destino.espera)}"
            elif destino.estado == "error":
                detalle = formato(
                    "ventana.error",
                    detalle=destino.error or texto("ventana.fallo_desconocido"),
                )
                linea.add_css_class("error")
            else:
                detalle = formato(
                    "ventana.progreso_destino",
                    pct=int(destino.fraccion * 100),
                    hecho=fmt_bytes(destino.copiados),
                    total=fmt_bytes(destino.total_bytes),
                )
            linea.set_text(f"• {short_path(destino.ruta)} · {detalle}")

        etiqueta = fila["estado"]
        etiqueta.remove_css_class("error")

        # Los botones solo tienen sentido mientras la copia puede seguir
        accionable = op.estado in ("running", "paused", "error")
        fila["pausa"].set_visible(accionable)
        fila["cancelar"].set_visible(accionable)
        fila["eliminar"].set_visible(not accionable)

        if op.estado == "running":
            partes = []
            if op.velocidad > 0:
                partes.append(fmt_velocidad(op.velocidad))
            restante = op.restante
            if restante is not None:
                partes.append(
                    formato("ventana.quedan", tiempo=fmt_restante(restante))
                )
            partes.append(
                formato(
                    "ventana.elementos",
                    hechos=op.archivos_ok,
                    total=op.total_archivos,
                )
            )
            etiqueta.set_text(
                formato("ventana.copiando", detalle=" · ".join(partes))
            )
            fila["pausa"].set_label(texto("acciones.pausar"))
        elif op.estado == "paused":
            # `espera` explica por qué el vigilante aún no la ha reanudado
            detalle = op.espera or formato(
                "ventana.pausa_detalle",
                bytes=fmt_bytes(op.copiados),
                hechos=op.archivos_ok,
                total=op.total_archivos,
            )
            hechos = sum(1 for d in op.destinos if d.estado == "done")
            if len(op.destinos) > 1 and hechos:
                detalle = (
                    formato(
                        "ventana.destinos_completados",
                        hechos=hechos,
                        total=len(op.destinos),
                    )
                    + detalle
                )
            etiqueta.set_text(f"{texto('ventana.en_pausa')} · {detalle}")
            fila["pausa"].set_label(texto("acciones.reanudar"))
        elif op.estado == "error":
            detalle = op.error or texto("ventana.fallo_desconocido")
            if op.espera:
                detalle += f" · {op.espera}"
            etiqueta.set_text(formato("ventana.error", detalle=detalle))
            etiqueta.add_css_class("error")
            fila["pausa"].set_label(texto("acciones.reintentar"))
        elif op.estado == "done":
            etiqueta.set_text(
                formato(
                    "ventana.completada",
                    bytes=fmt_bytes(op.total_bytes),
                    n=op.total_archivos,
                )
            )
        else:  # cancelled
            etiqueta.set_text(
                formato(
                    "ventana.cancelada",
                    hecho=fmt_bytes(op.copiados),
                    total=fmt_bytes(op.total_bytes),
                )
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

    def _al_eliminar(self, boton, op_id):
        """Quita la copia terminada de la pantalla, sin borrar el historial."""
        self._eliminadas.add(op_id)
        fila = self._filas.pop(op_id, None)
        if fila is not None:
            self._lista.remove(fila["row"])
        self._vacio.set_visible(not self._filas)
        self._lista.set_visible(bool(self._filas))
