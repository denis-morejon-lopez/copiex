# -*- coding: utf-8 -*-
"""Icono en la bandeja (esquina superior derecha) vía StatusNotifierItem + D-Bus.

GNOME no muestra iconos XEmbed: usa StatusNotifierItem (SNI) y el menú
dbusmenu, que es lo que la extensión «AppIndicator» de Ubuntu traduce al
icono de la bandeja. Todo se implementa aquí con Gio, sin dependencias.
"""

from __future__ import annotations

import os
import traceback

import gi

from .menu import idioma_actual, texto
from .util import ICONO_APP, icono_disponible

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
    <!-- IconPixmap es «a(iiay)»: una lista de mapas de bits, cada uno con su
         ancho, su alto y los bytes ARGB. Con «aa(iiay)» (un nivel de más) el
         panel no puede leer la propiedad. -->
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
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

# Tamaños del mapa de bits que se publica en IconPixmap. El panel elige el
# menor que llegue al tamaño que pide (con pantallas HiDPI pide 2× o 3×).
TAMANOS_PIXMAP = (16, 22, 24, 32, 48, 64)

OCULTAR_ID = 1
IDIOMA_ID = 2
ESPANOL_ID = 3
INGLES_ID = 4
SALIR_ID = 5


def _argb_premultiplicado(pixbuf) -> bytes:
    """Pixbuf de GdkPixbuf → ARGB32 tal y como lo pide StatusNotifierItem.

    El protocolo pide ARGB en orden de red (A, R, G, B por píxel) y con el alfa
    premultiplicado, que es lo que espera el panel (`Cogl.PixelFormat.ARGB_8888`).
    GdkPixbuf entrega RGBA en orden de memoria y sin premultiplicar.
    """
    ancho = pixbuf.get_width()
    alto = pixbuf.get_height()
    fila = pixbuf.get_rowstride()
    canales = pixbuf.get_n_channels()
    datos = pixbuf.get_pixels()
    salida = bytearray(ancho * alto * 4)
    destino = 0
    for y in range(alto):
        origen = y * fila
        for x in range(ancho):
            p = origen + x * canales
            alfa = datos[p + 3] if canales == 4 else 255
            salida[destino] = alfa
            salida[destino + 1] = datos[p] * alfa // 255
            salida[destino + 2] = datos[p + 1] * alfa // 255
            salida[destino + 3] = datos[p + 2] * alfa // 255
            destino += 4
    return bytes(salida)


class Bandeja:
    """Icono de bandeja con menú contextual: ocultar ventana / salir."""

    # La bandeja usa el icono a color (la «C» blanca sobre verde). La variante
    # simbólica de una tinta se veía como un punto con una barra y no es la que
    # quiere el usuario.
    ICONO = ICONO_APP

    def __init__(self, al_pulsar, al_ocultar, al_salir, al_idioma=None,
                 titulo="Copiex"):
        self._al_pulsar = al_pulsar  # clic izquierdo: mostrar/ocultar
        self._al_ocultar = al_ocultar
        self._al_salir = al_salir
        self._al_idioma = al_idioma or (lambda _codigo: None)
        self._titulo = titulo
        # Al crearse la bandeja todavía no hay ventana: la opción es «Mostrar».
        self._etiqueta = texto("menu.mostrar")
        self._revision = 1
        # Icono propio si está instalado (paquete .deb); si no, el del tema.
        self._icono = self._elegir_icono()
        # Además del nombre se publica el mapa de bits ya rasterizado: con solo
        # IconName, la extensión AppIndicator de Ubuntu 24.04 falla al cargarlo
        # (iconCache.js llama a `oldIcon.equals`, que no existe en un Gio.Icon)
        # y deja el icono de reserva «image-loading-symbolic»: tres puntos.
        self._pixmaps = self._calcular_pixmaps()

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

    def _elegir_icono(self) -> str:
        """Icono de la bandeja: el de Copiex si está en el tema, si no el de reserva."""
        return icono_disponible(self.ICONO)

    # ------------------------------------------------------------------
    # mapa de bits del icono (IconPixmap)
    # ------------------------------------------------------------------
    def _rutas_icono(self) -> list[str]:
        """Rutas candidatas del fichero del icono, en orden de preferencia.

        Primero lo que resuelva el tema de iconos (vale para el .deb y para el
        icono de reserva) y después las rutas conocidas del proyecto y del
        paquete. No se comprueba con `os.path.exists`: si una ruta no sirve, la
        carga falla y se prueba la siguiente. Son rutas del sistema, no de
        dispositivos del usuario.
        """
        rutas: list[str] = []
        try:
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gdk, Gtk

            display = Gdk.Display.get_default()
            if display is not None:
                tema = Gtk.IconTheme.get_for_display(display)
                paintable = tema.lookup_icon(
                    self._icono,
                    48,
                    1,
                    Gtk.TextDirection.NONE,
                    Gtk.IconLookupFlags.FORCE_REGULAR,
                )
                fichero = paintable.get_file() if paintable is not None else None
                ruta = fichero.get_path() if fichero is not None else None
                if ruta:
                    rutas.append(ruta)
        except Exception:
            pass  # sin GTK o sin tema: se prueban las rutas de abajo

        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for ruta in (
            os.path.join(raiz, "icons", f"{self._icono}.svg"),
            f"/usr/share/icons/hicolor/scalable/apps/{self._icono}.svg",
            f"/opt/copiex/icons/{self._icono}.svg",
        ):
            if ruta not in rutas:
                rutas.append(ruta)
        return rutas

    def _calcular_pixmaps(self) -> list[tuple[int, int, bytes]]:
        """IconPixmap: el icono rasterizado a varios tamaños.

        Si no se puede rasterizar (no hay cargador de SVG ni fichero), queda
        vacío y la bandeja publica solo IconName, como antes.
        """
        for ruta in self._rutas_icono():
            try:
                return self._pixmaps_de(ruta)
            except Exception:
                continue
        return []

    def _pixmaps_de(self, ruta: str) -> list[tuple[int, int, bytes]]:
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf

        pixmaps = []
        for tamano in TAMANOS_PIXMAP:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(ruta, tamano, tamano)
            pixmaps.append((
                pixbuf.get_width(),
                pixbuf.get_height(),
                _argb_premultiplicado(pixbuf),
            ))
        return pixmaps

    # ------------------------------------------------------------------
    # org.kde.StatusNotifierItem
    # ------------------------------------------------------------------
    def _propiedad_sni(self, conn, sender, ruta, interfaz, nombre):
        valores = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", "copiex"),
            "Title": GLib.Variant("s", self._titulo),
            # Con el mapa de bits disponible se deja el nombre vacío: así el
            # panel no intenta resolverlo por el tema (que es donde falla la
            # extensión en 24.04) y usa directamente IconPixmap.
            "IconName": GLib.Variant("s", "" if self._pixmaps else self._icono),
            "IconThemePath": GLib.Variant("s", ""),
            "OverlayIconName": GLib.Variant("s", ""),
            "AttentionIconName": GLib.Variant("s", ""),
            "Status": GLib.Variant("s", "Active"),
            "WindowId": GLib.Variant("u", 0),
            "IconPixmap": GLib.Variant("a(iiay)", self._pixmaps),
            "AttentionIconPixmap": GLib.Variant("a(iiay)", []),
            "OverlayIconPixmap": GLib.Variant("a(iiay)", []),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", (
                self._icono, [], self._titulo, texto("aplicacion.tooltip")
            )),
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
        idioma = idioma_actual()
        return {
            OCULTAR_ID: {"label": GLib.Variant("s", self._etiqueta)},
            IDIOMA_ID: {
                "label": GLib.Variant("s", texto("menu.idioma")),
                "children-display": GLib.Variant("s", "submenu"),
            },
            ESPANOL_ID: {
                "label": GLib.Variant("s", texto("menu.espanol")),
                "toggle-type": GLib.Variant("s", "radio"),
                "toggle-state": GLib.Variant("i", 1 if idioma == "es" else 0),
            },
            INGLES_ID: {
                "label": GLib.Variant("s", texto("menu.ingles")),
                "toggle-type": GLib.Variant("s", "radio"),
                "toggle-state": GLib.Variant("i", 1 if idioma == "en" else 0),
            },
            SALIR_ID: {"label": GLib.Variant("s", texto("menu.salir"))},
        }

    def _estructura(self, item_id) -> tuple:
        """Nodo del menú como tupla plana (PyGObject exige tuplas para structs;
        solo a{sv} y av admiten GLib.Variant)."""
        if item_id == 0:
            hijos = [
                GLib.Variant("(ia{sv}av)", self._estructura(identificador))
                for identificador in (OCULTAR_ID, IDIOMA_ID, SALIR_ID)
            ]
            props = {"children-display": GLib.Variant("s", "submenu")}
        elif item_id == IDIOMA_ID:
            hijos = [
                GLib.Variant("(ia{sv}av)", self._estructura(identificador))
                for identificador in (ESPANOL_ID, INGLES_ID)
            ]
            props = self._items().get(item_id, {})
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
                    elif identificador == ESPANOL_ID:
                        self._al_idioma("es")
                    elif identificador == INGLES_ID:
                        self._al_idioma("en")
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
    def refrescar(self):
        """Avisa al panel de que cambien las etiquetas del menú (idioma)."""
        self._revision += 1
        try:
            self.conn.emit_signal(
                None,
                "/MenuBar",
                "com.canonical.dbusmenu",
                "LayoutUpdated",
                GLib.Variant("(ui)", (self._revision, 0)),
            )
        except Exception:
            traceback.print_exc()

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
