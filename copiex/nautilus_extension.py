# -*- coding: utf-8 -*-
"""Extensión de Nautilus para Copiex.

Añade cuatro entradas al menú contextual de Nautilus:

  * «Copiar con Copiex»           → sobre la selección (marca los orígenes)
  * «Cortar con Copiex»           → como copiar, pero los orígenes se borran
                                    cuando la copia termina en todos los destinos
  * «Pegar con Copiex»            → sobre la carpeta de destino (lanza la copia)
  * «Pegar con Copiex N destinos» → copia a esa carpeta y a otras elegidas

La extensión es solo un puente: envía {origen…, destino} por el socket UNIX
de Copiex y la copia (progreso, pausa, reanudación) la hace la aplicación.

Requiere python3-nautilus:  sudo apt install python3-nautilus
Instalación:  ./install.sh  (copia este fichero a
~/.local/share/nautilus-python/extensions/copiex.py)

Compatible con la API de Nautilus que traiga el sistema:
  * Ubuntu 24.04 (Nautilus 46): API 4.0
  * Ubuntu 26.04 (Nautilus 50): API 4.1
"""

from __future__ import annotations

import errno
import json
import os
import socket
import subprocess
import sys
import time

import gi
from gi.repository import Gio, GLib, GObject  # noqa: E402

# Orden de preferencia: primero la API más moderna y, si no está, la anterior.
VERSIONES_NAUTILUS = ("4.1", "4.0")


def _cargar_nautilus():
    """Devuelve (módulo Nautilus, versión de API) de la que haya instalada."""
    # Dentro de Nautilus, nautilus-python ya tiene cargada su typelib: se
    # reutiliza para no pedir require_version de una versión distinta.
    cargado = sys.modules.get("gi.repository.Nautilus")
    if cargado is not None:
        return cargado, getattr(cargado, "_version", "")

    for version in VERSIONES_NAUTILUS:
        try:
            gi.require_version("Nautilus", version)
            from gi.repository import Nautilus as modulo
        except (ValueError, ImportError):
            continue
        return modulo, version

    raise ImportError(
        "no se encontró la API de Nautilus (se probaron las versiones "
        + ", ".join(VERSIONES_NAUTILUS)
        + "); instala python3-nautilus: sudo apt install python3-nautilus"
    )


Nautilus, VERSION_NAUTILUS = _cargar_nautilus()

# Deja rastro de qué versión cargó Nautilus: si tras instalar no aparece esta
# línea en el registro, el gestor sigue con la extensión anterior en memoria.
print(f"Copiex: extensión de Nautilus cargada (API {VERSION_NAUTILUS})", flush=True)

try:  # Nautilus 46 (24.04) y Nautilus 50 (26.04) son GTK4
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk  # noqa: E402
except Exception:  # pragma: no cover - sólo defensivo
    Gdk = None

try:
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk  # noqa: E402
except Exception:  # pragma: no cover
    Gtk = None

DESKTOP_ID = "com.copiex.Manager.desktop"
APP_ID = "com.copiex.Manager"  # nombre que Copiex registra en el bus de sesión

# Formato real del portapapeles de Nautilus (GNOME Files): la primera línea
# lleva la acción y después una URI por línea.
#     copy\nfile:///home/ana/a.txt\nfile:///home/ana/b.txt
# Nautilus 46 y 50 publican además text/uri-list. «x-special/nautilus-clipboard»
# es el formato antiguo (Nautilus 3.x): se sigue aceptando al leer.
MIME_COPIADOS = "x-special/gnome-copied-files"
MIME_URIS = "text/uri-list"
MIME_ANTIGUO = "x-special/nautilus-clipboard"

# Orden en el que se piden los formatos al leer: primero el de Nautilus, para no
# acabar interpretando el texto suelto de text/plain (que solo trae nombres).
MIMES_LECTURA = (
    MIME_COPIADOS,
    MIME_URIS,
    MIME_ANTIGUO,
    "text/plain;charset=utf-8",
    "text/plain",
)
ACCIONES = ("copy", "cut")

# Últimos elementos marcados con «Copiar/Cortar con Copiex» (memoria de la
# extensión) y qué hacer con ellos si el portapapeles no contesta.
_seleccion: list = []
_seleccion_accion = "copy"  # copy | cut

# Textos de los ítems del menú. Se leen de menu.yaml (requerimiento 11) a través
# de la ruta del lanzador que hay en el .desktop; si no se encuentra, se usan
# estos. La extensión se instala como fichero suelto, así que no puede importar
# el paquete copiex y repite el lector mínimo a propósito.
_TEXTO_DEFECTO = {
    "copiar": "Copiar con Copiex",
    "cortar": "Cortar con Copiex",
    "pegar": "Pegar con Copiex",
    "pegar_varios": "Pegar con Copiex N destinos",
    "copiar_ayuda": "Marca estos elementos para copiarlos con Copiex",
    "cortar_ayuda": (
        "Mueve estos elementos con Copiex: se copian y, al terminar, se "
        "borran los originales"
    ),
    "pegar_ayuda": (
        "Copia aquí lo marcado con Copiex (o el portapapeles) con progreso, "
        "pausa y reanudación"
    ),
    "pegar_varios_ayuda": (
        "Copia a esta carpeta y a otras que elijas, leyendo el origen una sola vez"
    ),
    "destinos_titulo": "Destinos de la copia",
    "destinos_ayuda": (
        "Esta carpeta es el primer destino. Añade los demás y pulsa «Finalizar selección»."
    ),
    "anadir_destino": "Añadir otro destino",
    "finalizar_seleccion": "Finalizar selección",
    "elegir_destino_titulo": "¿Qué otra carpeta quieres como destino?",
}
_textos_menu = None


def _leer_seccion_nautilus(ruta: str) -> dict:
    """Valores de la sección `nautilus:` de menu.yaml (subconjunto de YAML)."""
    valores = {}
    dentro = False
    with open(ruta, encoding="utf-8") as fichero:
        for linea in fichero:
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            sangria = len(linea) - len(linea.lstrip(" "))
            contenido = linea.strip()
            if sangria == 0:
                dentro = contenido.rstrip(":") == "nautilus"
                continue
            if dentro and ":" in contenido:
                clave, _, valor = contenido.partition(":")
                valor = valor.strip()
                if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                    valor = valor[1:-1]
                if valor:
                    valores[clave.strip()] = valor
    return valores


def _textos() -> dict:
    """Textos del menú, con los del fichero por delante de los de reserva."""
    global _textos_menu
    if _textos_menu is not None:
        return _textos_menu
    textos = dict(_TEXTO_DEFECTO)
    try:
        info = Gio.DesktopAppInfo.new(DESKTOP_ID)
        linea = info.get_commandline() if info is not None else ""
        argv = list(GLib.shell_parse_argv(linea)[1]) if linea else []
        if argv:
            ruta = os.path.join(os.path.dirname(os.path.abspath(argv[0])), "menu.yaml")
            if os.path.isfile(ruta):
                textos.update(_leer_seccion_nautilus(ruta))
    except Exception:
        pass  # sin menu.yaml se usan los textos de reserva
    _textos_menu = textos
    return textos

# Copiex arranca desde Nautilus con la salida descartada: los `print` de la
# extensión no llegan a ningún sitio, así que lo que importa se anota aquí.
# Es un fichero independiente del log de la aplicación.
def _traza(texto: str) -> None:
    try:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        carpeta = os.path.join(base, "copiex")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, "extension.log")
        if os.path.exists(ruta) and os.path.getsize(ruta) > 200_000:
            os.replace(ruta, ruta + ".1")
        with open(ruta, "a", encoding="utf-8") as fichero:
            fichero.write(time.strftime("%Y-%m-%d %H:%M:%S ") + texto + "\n")
        _traza_en_app(texto)
    except Exception:
        pass  # la traza nunca debe romper una acción del menú


def _traza_en_app(texto: str) -> None:
    """Manda la traza al copiex.log de la aplicación, sin arrancarla.

    Así un solo fichero cuenta la historia completa: lo que hace Nautilus y lo
    que hace Copiex. Si la aplicación no está, la traza queda en extension.log.
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            sock.connect(_ruta_socket())
            sock.sendall(
                (json.dumps({"cmd": "log", "texto": texto}) + "\n").encode("utf-8")
            )
    except OSError:
        pass


# ----------------------------------------------------------------------
# comunicación con la aplicación
# ----------------------------------------------------------------------
def _ruta_socket() -> str:
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(base, f"copiex-{os.getuid()}", "copiex.sock")


def _arrancar_app(oculto: bool = True) -> bool:
    """Pide al bus de sesión que arranque Copiex.

    Antes se lanzaba con subprocess desde el hilo que enviaba la petición. En
    Nautilus ese fork puede tardar muchos segundos (o quedarse esperando), y
    con él la copia no llega a empezar. Arrancándolo por D-Bus el fork lo hace
    el bus, que es pequeño y de un solo hilo, y la llamada no bloquea.

    Hace falta el servicio `com.copiex.Manager.service`, que instala
    install.sh. Si no está, se recurre al lanzamiento directo.
    """
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "StartServiceByName",
            GLib.Variant("(su)", (APP_ID, 0)),
            None,
            Gio.DBusCallFlags.NONE,
            3000,
            None,
            _arranque_contestado,
            None,
        )
        return True
    except Exception:
        return _arrancar_app_directo(oculto)


def _arranque_contestado(bus, resultado, _datos=None):
    try:
        bus.call_finish(resultado)
    except GLib.Error as exc:
        _traza(f"el bus no arrancó Copiex ({exc.message}); se lanza directamente")
        GLib.idle_add(_arrancar_app_directo)
    return False


def _arrancar_app_directo(oculto: bool = True) -> bool:
    """Respaldo sin D-Bus: lanza el .desktop desde el bucle principal."""
    try:
        info = Gio.DesktopAppInfo.new(DESKTOP_ID)
        if info is None:
            return False
        linea = info.get_commandline() or info.get_string("Exec") or ""
        argv = list(GLib.shell_parse_argv(linea)[1]) if linea else []
        argv = [a for a in argv if a and not a.startswith("%")]
        if not argv:
            info.launch([], None)
            return True
        if oculto:
            argv.append("--bandeja")
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False


def _enviar(mensaje: dict, espera_total: float = 12.0):
    """Envía el mensaje y devuelve la respuesta (None si no hubo contacto).

    Si Copiex no está abierto se arranca y se sondea el socket cada 150 ms: el
    mensaje sale en cuanto la aplicación abre el socket.
    """
    ruta = _ruta_socket()
    ultimo_error = None
    arrancada = False
    inicio = time.monotonic()
    limite = inicio + espera_total
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(4.0)
                sock.connect(ruta)
                sock.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
                datos = b""
                while b"\n" not in datos and len(datos) < 65536:
                    trozo = sock.recv(4096)
                    if not trozo:
                        break
                    datos += trozo
            texto = datos.split(b"\n", 1)[0].decode("utf-8", "replace").strip()
            try:
                respuesta = json.loads(texto) if texto else {}
            except ValueError:
                respuesta = {}
            if not isinstance(respuesta, dict):
                respuesta = {}
            _traza(
                f"enviado {mensaje.get('cmd')} en "
                f"{time.monotonic() - inicio:.3f}s -> {respuesta}"
            )
            return respuesta
        except OSError as exc:
            ultimo_error = exc
            if not arrancada:
                arrancada = True
                _arrancar_app()
            if time.monotonic() >= limite:
                break
            time.sleep(0.15)
    _traza(f"sin contacto con Copiex: {ultimo_error}")
    return None


class _Envio:
    """Una petición al socket de Copiex, sin bloquear ni usar hilos.

    Antes cada envío corría en un hilo propio y, cuando Copiex no estaba
    abierto, ese hilo lanzaba la aplicación con subprocess (fork desde
    Nautilus). En Nautilus ese hilo podía quedarse esperando el GIL o el fork
    durante minutos, y la copia no llegaba a empezar. Ahora todo son callbacks
    del bucle principal: el socket es no bloqueante y el arranque lo hace el
    bus de sesión.
    """

    ESPERA_MS = 20000
    REINTENTO_MS = 200

    def __init__(self, mensaje: dict, al_fallar=None):
        self.cmd = mensaje.get("cmd")
        self.al_fallar = al_fallar
        self.inicio = time.monotonic()
        self.sock = None
        self.fuente = 0
        self.reloj = 0
        self.reintento = 0
        self.hecho = False
        self.lanzada = False
        self.enviado = False
        self.por_enviar = (json.dumps(mensaje) + "\n").encode("utf-8")
        self.datos = b""
        self.ultimo_error = None

    # ------------------------------------------------------------------
    def empezar(self):
        _traza(f"enviando {self.cmd}...")
        self.reloj = GLib.timeout_add(self.ESPERA_MS, self._agotado)
        self._intentar()

    def _intentar(self):
        if self.hecho:
            return False
        self.reintento = 0
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.setblocking(False)
            codigo = sock.connect_ex(_ruta_socket())
        except OSError as exc:
            self.ultimo_error = exc
            sock = None
            codigo = -1
        if codigo in (0, errno.EINPROGRESS, errno.EAGAIN):
            self.sock = sock
            self.fuente = GLib.io_add_watch(sock, GLib.IO_OUT, self._escribible)
            return False
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if not self.lanzada:
            self.lanzada = True
            _traza("Copiex no está abierto; se pide al bus que lo arranque")
            _arrancar_app()
        self.reintento = GLib.timeout_add(self.REINTENTO_MS, self._intentar)
        return False

    def _escribible(self, sock, _condicion):
        if self.hecho:
            return False
        try:
            escritos = sock.send(self.por_enviar)
        except BlockingIOError:
            return True
        except OSError as exc:
            self._terminar(error=exc)
            return False
        self.por_enviar = self.por_enviar[escritos:]
        if self.por_enviar:
            return True
        self.enviado = True
        self._quitar_fuente()
        self.fuente = GLib.io_add_watch(
            sock, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self._leible
        )
        return False

    def _leible(self, sock, _condicion):
        if self.hecho:
            return False
        try:
            trozo = sock.recv(4096)
        except BlockingIOError:
            return True
        except OSError as exc:
            self._terminar(error=exc)
            return False
        if not trozo:
            if b"\n" in self.datos:
                self._terminar(texto=self.datos.split(b"\n", 1)[0])
            else:
                self._terminar(error="la conexión se cerró sin respuesta")
            return False
        self.datos += trozo
        if b"\n" in self.datos:
            self._terminar(texto=self.datos.split(b"\n", 1)[0])
            return False
        return True

    def _agotado(self):
        self.reloj = 0
        if self.hecho:
            return False
        if self.enviado:
            self._terminar(error="Copiex no respondió a tiempo")
        else:
            self._terminar(
                error=f"no se pudo contactar ({self.ultimo_error or 'sin socket'})"
            )
        return False

    # ------------------------------------------------------------------
    def _quitar_fuente(self):
        if self.fuente:
            GLib.source_remove(self.fuente)
            self.fuente = 0

    def _terminar(self, texto=None, error=None):
        if self.hecho:
            return
        self.hecho = True
        self._quitar_fuente()
        for nombre in ("reintento", "reloj"):
            fuente = getattr(self, nombre)
            if fuente:
                GLib.source_remove(fuente)
                setattr(self, nombre, 0)
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        respuesta = {}
        if texto:
            try:
                respuesta = json.loads(texto)
            except ValueError:
                respuesta = {}
            if not isinstance(respuesta, dict):
                respuesta = {}
        if error is None:
            _traza(
                f"enviado {self.cmd} en "
                f"{time.monotonic() - self.inicio:.3f}s -> {respuesta}"
            )
            if self.al_fallar is not None and respuesta.get("ok") is False:
                self.al_fallar(
                    respuesta.get("error") or "Copiex rechazó la operación"
                )
            return
        _traza(f"sin contacto con Copiex ({self.cmd}): {error}")
        if self.al_fallar is not None:
            self.al_fallar("No se pudo contactar con Copiex")


def _enviar_async(mensaje: dict, al_fallar=None):
    """Envía la petición sin bloquear el bucle principal (ni usar hilos)."""
    _Envio(mensaje, al_fallar).empezar()


# ----------------------------------------------------------------------
# portapapeles (formato nativo de Nautilus)
# ----------------------------------------------------------------------
def _marcar_portapapeles(uris: list, accion: str = "copy"):
    """Deja la selección en el portapapeles con el formato de Nautilus, para que
    un Ctrl+V normal en el gestor de archivos también funcione. Mejor esfuerzo."""
    if Gdk is None or not uris:
        return
    if accion not in ACCIONES:
        accion = "copy"
    try:
        texto_gnome = accion + "\n" + "\n".join(uris)
        texto_uris = "\r\n".join(uris) + "\r\n"
        texto_plano = "\n".join(uris)
        proveedor = Gdk.ContentProvider.new_union(
            [
                Gdk.ContentProvider.new_for_bytes(
                    MIME_COPIADOS, GLib.Bytes.new(texto_gnome.encode("utf-8"))
                ),
                Gdk.ContentProvider.new_for_bytes(
                    MIME_URIS, GLib.Bytes.new(texto_uris.encode("utf-8"))
                ),
                Gdk.ContentProvider.new_for_bytes(
                    "text/plain;charset=utf-8",
                    GLib.Bytes.new(texto_plano.encode("utf-8")),
                ),
            ]
        )
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set_content(proveedor)
    except Exception:
        pass


def _accion_del_portapapeles(texto: str, mime: str = "") -> str:
    """Devuelve «cut» o «copy» según la cabecera del portapapeles de Nautilus.

    Ctrl+X publica `cut` en la primera línea; el resto de formatos (uri-list,
    texto plano) no distinguen, así que se tratan como copia.
    """
    if not texto or (mime or "").lower() not in (MIME_COPIADOS, MIME_ANTIGUO):
        return "copy"
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        return "cut" if linea.lower() == "cut" else "copy"
    return "copy"


def _uris_del_portapapeles(texto: str, mime: str = "") -> list:
    """Extrae las URI file:// del contenido del portapapeles, sea cual sea el
    formato en que llegue (gnome-copied-files, uri-list o texto plano).

    Se descarta lo que no sea una copia de ficheros: text/plain de Nautilus
    trae solo los nombres, así que se acepta únicamente si todo son URI.
    """
    if not texto:
        return []
    lineas = [
        l.strip()
        for l in texto.splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    mime = (mime or "").lower()
    if lineas and lineas[0].lower() in ACCIONES + (MIME_ANTIGUO,):
        lineas = lineas[1:]  # cabecera de acción
    uris = [l for l in lineas if l.lower().startswith(("file://", "mtp://"))]
    if mime in (MIME_COPIADOS, MIME_URIS, MIME_ANTIGUO):
        return uris
    # texto plano: solo vale si no sobra nada (una ruta suelta no es una copia)
    return uris if uris and len(uris) == len(lineas) else []


def _leer_portapapeles(callback):
    """Lee el portapapeles de forma asíncrona y llama a callback(texto, mime)."""
    if Gdk is None:
        callback("", "")
        return
    try:
        display = Gdk.Display.get_default()
        if display is None:
            callback("", "")
            return
        display.get_clipboard().read_async(
            list(MIMES_LECTURA),
            GLib.PRIORITY_DEFAULT,
            None,
            _portapapeles_leido,
            callback,
        )
    except Exception:
        callback("", "")


def _portapapeles_leido(clipboard, resultado, callback):
    try:
        flujo, mime = clipboard.read_finish(resultado)
    except Exception:
        callback("", "")
        return
    if flujo is None:
        callback("", mime or "")
        return
    _leer_flujo(flujo, mime or "", callback)


def _leer_flujo(flujo, mime, callback, trozos=None, limite=1 << 20):
    """Acumula el flujo del portapapeles por trozos (no hay lectura síncrona)."""
    if trozos is None:
        trozos = []
    try:
        flujo.read_bytes_async(
            65536,
            GLib.PRIORITY_DEFAULT,
            None,
            _trozo_leido,
            (flujo, mime, callback, trozos, limite),
        )
    except Exception:
        callback("", mime)


def _trozo_leido(flujo, resultado, estado):
    flujo, mime, callback, trozos, limite = estado
    try:
        datos = flujo.read_bytes_finish(resultado)
    except Exception:
        callback("".join(trozos), mime)
        return
    if datos is None or datos.get_size() == 0:
        callback("".join(trozos), mime)
        return
    trozos.append(bytes(datos.get_data()).decode("utf-8", "replace"))
    if sum(len(t) for t in trozos) >= limite:
        callback("".join(trozos), mime)
        return
    _leer_flujo(flujo, mime, callback, trozos, limite)


# ----------------------------------------------------------------------
# avisos
# ----------------------------------------------------------------------
def _aviso(texto: str, detalle: str = ""):
    if Gtk is None:
        print(f"Copiex: {texto} {detalle}")
        return
    try:
        alerta = Gtk.AlertDialog(message=texto)
        if detalle:
            alerta.set_detail(detalle)
        alerta.show(None)
    except Exception:
        print(f"Copiex: {texto} {detalle}")


# ----------------------------------------------------------------------
# acciones del menú
# ----------------------------------------------------------------------
def _al_copiar(uris: list):
    global _seleccion, _seleccion_accion
    _seleccion = list(uris)
    _seleccion_accion = "copy"
    _traza(f"copiar con Copiex: {len(_seleccion)} elemento(s) {_seleccion[:3]}")
    _marcar_portapapeles(_seleccion, "copy")
    # Al copiar se deja Copiex en marcha en la bandeja (si no lo estaba).
    _enviar_async({"cmd": "ping"})


def _al_cortar(uris: list):
    """Marca la selección como «cortar»: al pegar se copia y se borra el origen."""
    global _seleccion, _seleccion_accion
    _seleccion = list(uris)
    _seleccion_accion = "cut"
    _traza(f"cortar con Copiex: {len(_seleccion)} elemento(s) {_seleccion[:3]}")
    # También con la cabecera «cut»: un Ctrl+V normal de Nautilus movería.
    _marcar_portapapeles(_seleccion, "cut")
    _enviar_async({"cmd": "ping"})


def _con_origenes(accion):
    """Averigua qué pegar y llama a `accion(uris, modo)`.

    `modo` es «copy» o «cut»: se lee de la cabecera del portapapeles (así un
    Ctrl+X de Nautilus también se mueve) y, si no hay nada, de la última marca
    de «Copiar/Cortar con Copiex». Solo se entrega una vez: los temporizadores y
    la lectura comparten el testigo.
    """
    estado = {"hecho": False}

    def entregar(uris, modo):
        if estado["hecho"] or not uris:
            return
        estado["hecho"] = True
        accion(uris, modo)

    def con_portapapeles(texto, mime=""):
        if estado["hecho"]:
            return
        uris = _uris_del_portapapeles(texto, mime)
        if not uris:
            modo = _seleccion_accion
        elif (mime or "").lower() not in (MIME_COPIADOS, MIME_ANTIGUO):
            # El formato no dice si fue copiar o cortar: si son los mismos
            # elementos que se marcaron, vale la última acción de Copiex.
            modo = _seleccion_accion if uris == list(_seleccion) else "copy"
        else:
            modo = _accion_del_portapapeles(texto, mime)
        _traza(f"portapapeles: mime={mime!r} uris={len(uris)} modo={modo}")
        entregar(uris or list(_seleccion), modo)

    def con_lo_marcado():
        # La lectura del portapapeles no siempre contesta (Wayland, contenido
        # de otro proceso): sin este respaldo, «Pegar con Copiex» no hacía nada.
        if estado["hecho"] or not _seleccion:
            return False
        _traza("el portapapeles no respondió; se usa lo marcado con Copiex")
        entregar(list(_seleccion), _seleccion_accion)
        return False

    def sin_nada():
        if estado["hecho"]:
            return False
        estado["hecho"] = True
        _traza("pegar sin orígenes: no hay nada utilizable")
        _aviso(
            "No hay nada que pegar",
            "Selecciona los ficheros y usa «Copiar con Copiex» "
            "(o Ctrl+C en Nautilus) antes de pegarlos aquí.",
        )
        return False

    _leer_portapapeles(con_portapapeles)
    GLib.timeout_add(1500, con_lo_marcado)
    GLib.timeout_add(6000, sin_nada)


def _al_pegar(destino: str):
    """Pega en una sola carpeta (copia o movimiento, según la marca)."""

    def pegar(uris, modo):
        _traza(
            f"pegar en {destino}: {len(uris)} origen(es) {uris[:3]} modo={modo}"
        )

        def fallo(motivo):
            _traza(f"la aplicación rechazó la copia: {motivo}")
            _aviso("No se pudo copiar con Copiex", str(motivo))

        mensaje = {"cmd": "copy", "sources": uris, "dest": destino}
        if modo == "cut":
            mensaje["move"] = True
        _enviar_async(mensaje, al_fallar=fallo)

    _con_origenes(pegar)


# ----------------------------------------------------------------------
# varios destinos: ciclo de selección
# ----------------------------------------------------------------------
_SELECTORES = set()  # mantiene viva la ventana mientras se usa


def _lanzar_copia_varios(uris, destinos, modo="copy"):
    """Pide a Copiex una copia (o movimiento) a varias carpetas a la vez."""
    _traza(
        f"pegar en {len(destinos)} destinos: {len(uris)} origen(es) {uris[:3]} "
        f"modo={modo}"
    )

    def fallo(motivo):
        _traza(f"la aplicación rechazó la copia a varios destinos: {motivo}")
        _aviso("No se pudo copiar con Copiex", str(motivo))

    mensaje = {"cmd": "copy", "sources": uris, "dests": list(destinos)}
    if modo == "cut":
        mensaje["move"] = True
    _enviar_async(mensaje, al_fallar=fallo)


class _SelectorDestinos:
    """Acumula destinos: la carpeta pulsada es siempre el primero.

    «Añadir otro destino» abre el selector de carpetas y, al elegir, vuelve
    aquí; «Finalizar selección» lanza la copia. Cerrar la ventana cancela.
    """

    def __init__(self, primer_destino, uris, modo="copy"):
        self._uris = list(uris)
        self._modo = modo
        self._destinos = [primer_destino]
        textos = _textos()
        self._ventana = Gtk.Window(
            title=textos.get("destinos_titulo", "Destinos de la copia")
        )
        self._ventana.set_default_size(520, 340)
        self._ventana.set_modal(True)

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for lado in ("top", "bottom", "start", "end"):
            getattr(caja, f"set_margin_{lado}")(16)
        ayuda = Gtk.Label(
            label=textos.get("destinos_ayuda", ""), wrap=True, xalign=0
        )
        caja.append(ayuda)

        self._lista = Gtk.ListBox(css_classes=["boxed-list"])
        self._lista.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow(child=self._lista, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        caja.append(scroll)

        botones = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            halign=Gtk.Align.END,
        )
        self._anadir = Gtk.Button(
            label=textos.get("anadir_destino", "Añadir otro destino")
        )
        self._anadir.connect("clicked", self._al_anadir)
        finalizar = Gtk.Button(
            label=textos.get("finalizar_seleccion", "Finalizar selección"),
            css_classes=["suggested-action"],
        )
        finalizar.connect("clicked", self._al_finalizar)
        botones.append(self._anadir)
        botones.append(finalizar)
        caja.append(botones)

        self._ventana.set_child(caja)
        self._ventana.connect("close-request", self._al_cerrar)
        _SELECTORES.add(self)
        self._refrescar()
        self._ventana.present()

    # ------------------------------------------------------------------
    def _refrescar(self):
        while (fila := self._lista.get_row_at_index(0)) is not None:
            self._lista.remove(fila)
        for numero, uri in enumerate(self._destinos, 1):
            fichero = Gio.File.new_for_uri(uri)
            if uri.lower().startswith("mtp://"):
                # La ruta de gvfs-fuse no dice nada; la URI, sin %20, sí.
                ruta = fichero.get_parse_name()
            else:
                ruta = fichero.get_path() or uri
            etiqueta = Gtk.Label(label=f"{numero}. {ruta}", xalign=0)
            etiqueta.set_wrap(True)
            fila = Gtk.ListBoxRow()
            fila.set_child(etiqueta)
            self._lista.append(fila)
        self._anadir.set_sensitive(len(self._destinos) < 16)

    def _al_anadir(self, *_):
        textos = _textos()
        dialogo = Gtk.FileDialog(
            title=textos.get("elegir_destino_titulo", "Elige otra carpeta")
        )
        dialogo.select_folder(self._ventana, None, self._elegida)

    def _elegida(self, dialogo, resultado, *_):
        try:
            carpeta = dialogo.select_folder_finish(resultado)
        except GLib.Error:
            return  # cancelado: se queda como estaba
        uri = carpeta.get_uri() if carpeta is not None else None
        if not uri:
            return
        if uri == self._destinos[0]:
            _aviso(
                "Esa ya es la primera carpeta",
                "Elige otra ubicación para el segundo destino.",
            )
            return
        if uri in self._destinos:
            return  # ya estaba: no se repite
        self._destinos.append(uri)
        self._refrescar()

    def _al_finalizar(self, *_):
        if len(self._destinos) < 2:
            _aviso(
                "No has añadido ningún destino",
                "Cierra esta ventana y usa «Pegar con Copiex» para copiar "
                "solo en esta carpeta.",
            )
            return
        destinos = list(self._destinos)
        uris = list(self._uris)
        # Se envía antes de cerrar la ventana: la petición sale ya y no queda
        # detrás de la destrucción de la ventana modal.
        _lanzar_copia_varios(uris, destinos, self._modo)
        self._cerrar()

    def _al_cerrar(self, *_):
        self._cerrar()
        return True  # la ventana ya está destruida

    def _cerrar(self):
        _SELECTORES.discard(self)
        ventana = self._ventana
        # Destruir en cuanto vuelva el bucle principal: cerrar una ventana
        # modal no debe retener al manejador que acaba de lanzar la copia.
        GLib.idle_add(ventana.destroy)


def _al_pegar_varios(destino: str):
    """Abre el ciclo de selección de destinos para la carpeta pulsada."""
    if Gtk is None:
        _aviso("No se puede elegir varios destinos", "Falta GTK en Nautilus.")
        return

    def abrir(uris, modo):
        _SelectorDestinos(destino, uris, modo)

    _con_origenes(abrir)


# ----------------------------------------------------------------------
# proveedor de menús de Nautilus
# ----------------------------------------------------------------------
class ExtencionCopiex(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, files):
        uris = [f.get_uri() for f in files if f is not None and f.get_uri()]
        if not uris:
            return []
        textos = _textos()
        item = Nautilus.MenuItem(
            name="Copiex::copiar",
            label=textos["copiar"],
            tip=textos["copiar_ayuda"],
        )
        item.connect("activate", self._activar_copiar, uris)
        cortar = Nautilus.MenuItem(
            name="Copiex::cortar",
            label=textos.get("cortar", "Cortar con Copiex"),
            tip=textos.get("cortar_ayuda", ""),
        )
        cortar.connect("activate", self._activar_cortar, uris)
        return [item, cortar]

    def get_background_items(self, current_folder):
        if current_folder is None or not current_folder.get_uri():
            return []
        destino = current_folder.get_uri()
        textos = _textos()
        item = Nautilus.MenuItem(
            name="Copiex::pegar",
            label=textos["pegar"],
            tip=textos["pegar_ayuda"],
        )
        item.connect("activate", self._activar_pegar, destino)
        varios = Nautilus.MenuItem(
            name="Copiex::pegar_varios",
            label=textos.get("pegar_varios", "Pegar con Copiex N destinos"),
            tip=textos.get("pegar_varios_ayuda", ""),
        )
        varios.connect("activate", self._activar_pegar_varios, destino)
        return [item, varios]

    # ------------------------------------------------------------------
    def _activar_copiar(self, menu, uris):
        _al_copiar(uris)

    def _activar_cortar(self, menu, uris):
        _al_cortar(uris)

    def _activar_pegar(self, menu, destino):
        _al_pegar(destino)

    def _activar_pegar_varios(self, menu, destino):
        _al_pegar_varios(destino)
