# -*- coding: utf-8 -*-
"""Icono en la bandeja (esquina superior derecha) vía StatusNotifierItem + D-Bus.

GNOME no muestra iconos XEmbed: usa StatusNotifierItem (SNI) y el menú
dbusmenu, que es lo que la extensión «AppIndicator» de Ubuntu traduce al
icono de la bandeja. Todo se implementa aquí con Gio, sin dependencias.
"""

from __future__ import annotations

import os
import traceback

from .menu import texto

from gi.repository import Gio, GLib

SNI_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="u" access="read"/>
    <property name="IconPixmap" type="aa(iiay)" access="read"/>
    <property name="AttentionIconPixmap" type="aa(iiay)" access="read"/>
    <property name="OverlayIconPixmap" type="aa(iiay)" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ContextMenu" type="o" access="read"/>
    <method name="Activate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="Scroll">
      <arg type="i" name="delta" direction="in"/>
      <arg type="s" name="orientation" direction="in"/>
    </method>
  </interface>
</node>
"""

DBUSMENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
  </interface>
</node>
"""

OCULTAR_ID = 1
SALIR_ID = 2


class Bandeja:
    """Icono de bandeja con menú contextual: ocultar ventana / salir."""

    def __init__(self, al_pulsar, al_ocultar, al_salir, titulo="Copiex"):
        self._al_pulsar = al_pulsar  # clic izquierdo: mostrar/ocultar
        self._al_ocultar = al_ocultar
        self._al_salir = al_salir
        self._titulo = titulo
        # Al crearse la bandeja todavía no hay ventana: la opción es «Mostrar».
        self._etiqueta = texto("menu.mostrar")
        self._revision = 1

        self.conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._nombre = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
        self._registrado = False

        sni = Gio.DBusNodeInfo.new_for_xml(SNI_XML).interfaces[0]
        menu = Gio.DBusNodeInfo.new_for_xml(DBUSMENU_XML).interfaces[0]
        self._ids = [
            self.conn.register_object(
                "/StatusNotifierItem", sni, self._metodo_sni, self._propiedad_sni, None
            ),
            self.conn.register_object(
                "/MenuBar", menu, self._metodo_menu, self._propiedad_menu, None
            ),
        ]

        # El icono solo aparece si la extensión de AppIndicator/StatusNotifier
        # está presente; si aparece más tarde, nos registramos entonces.
        Gio.bus_watch_name(
            Gio.BusType.SESSION,
            "org.kde.StatusNotifierWatcher",
            Gio.BusNameWatcherFlags.NONE,
            self._watcher_presente,
            None,
        )
        Gio.bus_own_name(
            Gio.BusType.SESSION,
            self._nombre,
            Gio.BusNameOwnerFlags.NONE,
            None,
            self._nombre_adquirido,
            None,
        )

    # ------------------------------------------------------------------
    # registro
    # ------------------------------------------------------------------
    def _nombre_adquirido(self, conn, nombre):
        self._registrar()

    def _watcher_presente(self, conn, nombre, duenio):
        self._registrar()

    def _registrar(self):
        try:
            proxy = Gio.DBusProxy.new_sync(
                self.conn,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                None,
            )
            proxy.call_sync(
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (self._nombre,)),
                Gio.DBusCallFlags.NONE,
                5000,
                None,
            )
            self._registrado = True
        except Exception:
            traceback.print_exc()

    # ------------------------------------------------------------------
    # org.kde.StatusNotifierItem
    # ------------------------------------------------------------------
    def _propiedad_sni(self, conn, sender, ruta, interfaz, nombre):
        valores = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "copiex"),
            "Title": GLib.Variant("s", self._titulo),
            "IconName": GLib.Variant("s", "edit-copy"),
            "IconThemePath": GLib.Variant("s", ""),
            "OverlayIconName": GLib.Variant("s", ""),
            "AttentionIconName": GLib.Variant("s", ""),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("u", 0),
            "IconPixmap": GLib.Variant("aa(iiay)", []),
            "AttentionIconPixmap": GLib.Variant("aa(iiay)", []),
            "OverlayIconPixmap": GLib.Variant("aa(iiay)", []),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", ("edit-copy", [], self._titulo,
                                                      "Copiex para Nautilus")),
            "Menu": GLib.Variant("o", "/MenuBar"),
            "ContextMenu": GLib.Variant("o", "/MenuBar"),
        }
        return valores.get(nombre)

    def _metodo_sni(self, conn, sender, ruta, interfaz, metodo, parametros, invocacion):
        try:
            if metodo in ("Activate", "SecondaryActivate", "ContextMenu"):
                self._al_pulsar()
            invocacion.return_value(None)
        except Exception:
            traceback.print_exc()
            invocacion.return_value(None)

    # ------------------------------------------------------------------
    # com.canonical.dbusmenu
    # ------------------------------------------------------------------
    def _items(self):
        return {
            OCULTAR_ID: {"label": GLib.Variant("s", self._etiqueta)},
            SALIR_ID: {"label": GLib.Variant("s", texto("menu.salir"))},
        }

    def _estructura(self, item_id) -> tuple:
        """Nodo del menú como tupla plana (PyGObject exige tuplas para structs;
        solo a{sv} y av admiten GLib.Variant)."""
        if item_id == 0:
            hijos = [
                GLib.Variant("(ia{sv}av)", self._estructura(identificador))
                for identificador in (OCULTAR_ID, SALIR_ID)
            ]
            props = {"children-display": GLib.Variant("s", "submenu")}
        else:
            hijos = []
            props = self._items().get(item_id, {})
        return (item_id, props, hijos)

    def _propiedad_menu(self, conn, sender, ruta, interfaz, nombre):
        valores = {
            "Version": GLib.Variant("u", 3),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status": GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return valores.get(nombre)

    def _metodo_menu(self, conn, sender, ruta, interfaz, metodo, parametros, invocacion):
        try:
            if metodo == "GetLayout":
                self._revision += 1
                invocacion.return_value(
                    GLib.Variant("(u(ia{sv}av))", (self._revision, self._estructura(0)))
                )
            elif metodo == "GetGroupProperties":
                ids, _nombres = parametros.unpack()
                props = self._items()
                salida = [(i, props.get(i, {})) for i in ids]
                invocacion.return_value(GLib.Variant("(a(ia{sv}))", (salida,)))
            elif metodo == "GetProperty":
                # no hay propiedades por ítem: se responde con cadena vacía
                invocacion.return_value(GLib.Variant("(v)", (GLib.Variant("s", ""),)))
            elif metodo == "Event":
                identificador, evento, _datos, _ts = parametros.unpack()
                if evento in ("clicked", "activation"):
                    if identificador == OCULTAR_ID:
                        self._al_ocultar()
                    elif identificador == SALIR_ID:
                        self._al_salir()
                invocacion.return_value(None)
            elif metodo == "EventGroup":
                invocacion.return_value(GLib.Variant("(ai)", ([],)))
            elif metodo == "AboutToShow":
                invocacion.return_value(GLib.Variant("(b)", (False,)))
            elif metodo == "AboutToShowGroup":
                invocacion.return_value(GLib.Variant("(ai(ai))", ([], [])))
            else:
                raise ValueError(f"Método desconocido: {metodo}")
        except Exception:
            traceback.print_exc()
            try:
                invocacion.return_value(None)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def cambiar_etiqueta(self, etiqueta: str):
        """Cambia el texto de la entrada «Mostrar/Ocultar ventana»."""
        if etiqueta == self._etiqueta:
            return
        self._etiqueta = etiqueta
        try:
            self.conn.emit_signal(
                None,
                "/MenuBar",
                "com.canonical.dbusmenu",
                "ItemsPropertiesUpdated",
                GLib.Variant(
                    "(a(ia{sv})a(ias))",
                    ([(OCULTAR_ID, {"label": GLib.Variant("s", etiqueta)})], []),
                ),
            )
        except Exception:
            traceback.print_exc()

    def destruir(self):
        for identificador in self._ids:
            try:
                self.conn.unregister_object(identificador)
            except Exception:
                pass
        self._ids = []
