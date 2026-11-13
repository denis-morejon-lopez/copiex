# -*- coding: utf-8 -*-
"""Extensión de Nautilus para Copiex.

Añade dos entradas al menú contextual de Nautilus:

  * «Copiar con Copiex»      → sobre la selección (marca los orígenes)
  * «Pegar con Copiex»       → sobre la carpeta de destino (lanza la copia)

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

import json
import os
import socket
import subprocess
import sys
import threading
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

# Últimos elementos marcados con «Copiar con Copiex» (memoria de la extensión)
_seleccion: list = []

# Textos de los ítems del menú. Se leen de menu.yaml (requerimiento 11) a través
# de la ruta del lanzador que hay en el .desktop; si no se encuentra, se usan
# estos. La extensión se instala como fichero suelto, así que no puede importar
# el paquete copiex y repite el lector mínimo a propósito.
_TEXTO_DEFECTO = {
    "copiar": "Copiar con Copiex",
    "pegar": "Pegar con Copiex",
    "copiar_ayuda": "Marca estos elementos para copiarlos con Copiex",
    "pegar_ayuda": (
        "Copia aquí lo marcado con Copiex (o el portapapeles) con progreso, "
        "pausa y reanudación"
    ),
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
    """Arranca Copiex desde su fichero .desktop si aún no está en ejecución.

    Con oculto=True se inicia solo en la bandeja (esquina superior derecha), que
    es lo que se espera al pulsar «Copiar con Copiex»; sin ventana delante.
    """
    info = Gio.DesktopAppInfo.new(DESKTOP_ID)
    if info is None:
        return False
    try:
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
        try:
            info.launch([], None)
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
    limite = time.monotonic() + espera_total
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
            _traza(f"enviado {mensaje.get('cmd')} -> {respuesta}")
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


def _enviar_async(mensaje: dict, al_fallar=None):
    """Envía en segundo plano; si no se puede (o la app rechaza), avisa."""

    def trabajo():
        respuesta = _enviar(mensaje)
        if al_fallar is None:
            return
        if respuesta is None:
            GLib.idle_add(al_fallar, "No se pudo contactar con Copiex")
        elif respuesta.get("ok") is False:
            GLib.idle_add(
                al_fallar, respuesta.get("error") or "Copiex rechazó la operación"
            )

    threading.Thread(target=trabajo, name="copiex-ipc", daemon=True).start()


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
    uris = [l for l in lineas if l.startswith("file://")]
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
    global _seleccion
    _seleccion = list(uris)
    _traza(f"copiar con Copiex: {len(_seleccion)} elemento(s) {_seleccion[:3]}")
    _marcar_portapapeles(_seleccion)
    # Al copiar se deja Copiex en marcha en la bandeja (si no lo estaba).
    _enviar_async({"cmd": "ping"})


def _al_pegar(destino: str):
    """Lanza la copia con lo que haya en el portapapeles y, si la lectura no
    responde a tiempo, con lo último marcado con «Copiar con Copiex». Solo se
    envía una petición: los temporizadores y la lectura comparten el testigo."""
    estado = {"hecho": False}

    def enviar(uris):
        if estado["hecho"] or not uris:
            return
        estado["hecho"] = True
        _traza(f"pegar en {destino}: {len(uris)} origen(es) {uris[:3]}")

        def fallo(motivo):
            _traza(f"la aplicación rechazó la copia: {motivo}")
            _aviso("No se pudo copiar con Copiex", str(motivo))

        _enviar_async(
            {"cmd": "copy", "sources": uris, "dest": destino}, al_fallar=fallo
        )

    def con_portapapeles(texto, mime=""):
        if estado["hecho"]:
            return
        uris = _uris_del_portapapeles(texto, mime)
        _traza(f"portapapeles: mime={mime!r} uris={len(uris)}")
        enviar(uris or list(_seleccion))

    def con_lo_marcado():
        # La lectura del portapapeles no siempre contesta (Wayland, contenido
        # de otro proceso): sin este respaldo, «Pegar con Copiex» no hacía nada.
        if estado["hecho"] or not _seleccion:
            return False
        _traza("el portapapeles no respondió; se usa lo marcado con Copiex")
        enviar(list(_seleccion))
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
        return [item]

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
        return [item]

    # ------------------------------------------------------------------
    def _activar_copiar(self, menu, uris):
        _al_copiar(uris)

    def _activar_pegar(self, menu, destino):
        _al_pegar(destino)
