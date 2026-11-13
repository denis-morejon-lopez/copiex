# -*- coding: utf-8 -*-
"""Servidor IPC por socket UNIX: es el puente con la extensión de Nautilus."""

from __future__ import annotations

import json
import os
import socket
import threading
import traceback

MAX_LINEA = 1 << 20  # 1 MiB por mensaje


class ServidorIpc(threading.Thread):
    """Escucha mensajes JSON línea a línea en el socket del usuario.

    Mensajes admitidos:
        {"cmd": "copy", "sources": ["file:///a", ...], "dest": "file:///b"}
        {"cmd": "show"}
        {"cmd": "ping"}
    """

    def __init__(self, ruta, manejador):
        super().__init__(name="ipc", daemon=True)
        self.ruta = ruta
        self.manejador = manejador  # callable(dict) -> dict (respuesta)
        self._stop = threading.Event()
        self._servidor = None

    # ------------------------------------------------------------------
    def run(self):
        try:
            if os.path.exists(self.ruta):
                try:
                    os.unlink(self.ruta)
                except OSError:
                    pass
            self._servidor = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._servidor.bind(self.ruta)
            os.chmod(self.ruta, 0o600)  # solo el usuario
            self._servidor.listen(8)
            self._servidor.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    conexion, _ = self._servidor.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                self._atender(conexion)
        except Exception:
            traceback.print_exc()
        finally:
            self.cerrar()

    def _atender(self, conexion: socket.socket):
        with conexion:
            try:
                conexion.settimeout(5)
                datos = b""
                while b"\n" not in datos and len(datos) < MAX_LINEA:
                    trozo = conexion.recv(4096)
                    if not trozo:
                        break
                    datos += trozo
                texto = datos.split(b"\n", 1)[0].decode("utf-8", "replace").strip()
                if not texto:
                    return
                mensaje = json.loads(texto)
                if not isinstance(mensaje, dict):
                    raise ValueError("mensaje no es un objeto JSON")
                respuesta = self.manejador(mensaje) or {"ok": True}
            except Exception as exc:
                traceback.print_exc()
                respuesta = {"ok": False, "error": str(exc)}
            try:
                conexion.sendall(
                    (json.dumps(respuesta, ensure_ascii=False) + "\n").encode("utf-8")
                )
            except OSError:
                pass

    # ------------------------------------------------------------------
    def cerrar(self):
        self._stop.set()
        if self._servidor is not None:
            try:
                self._servidor.close()
            except OSError:
                pass
            self._servidor = None
        try:
            if os.path.exists(self.ruta):
                os.unlink(self.ruta)
        except OSError:
            pass


def enviar(mensaje: dict, ruta: str | None = None, espera: float = 3.0) -> dict:
    """Cliente: usado por la extensión de Nautilus y por las pruebas."""
    if ruta is None:
        from .util import socket_path

        ruta = socket_path()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(espera)
        sock.connect(ruta)
        sock.sendall(
            (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")
        )
        datos = b""
        while b"\n" not in datos:
            trozo = sock.recv(4096)
            if not trozo:
                break
            datos += trozo
    texto = datos.split(b"\n", 1)[0].decode("utf-8", "replace")
    return json.loads(texto) if texto else {"ok": True}