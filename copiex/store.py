# -*- coding: utf-8 -*-
"""Historial persistente de copias (SQLite)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

ESTADOS = ("running", "paused", "cancelled", "done", "error")

ESTADO_ES = {
    "running": "Copiando",
    "paused": "En pausa",
    "cancelled": "Cancelada",
    "done": "Completada",
    "error": "Error",
}

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS copias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    origenes        TEXT    NOT NULL,
    destino         TEXT    NOT NULL,
    total_bytes     INTEGER NOT NULL DEFAULT 0,
    copiados_bytes  INTEGER NOT NULL DEFAULT 0,
    total_archivos  INTEGER NOT NULL DEFAULT 0,
    copiados_archivos INTEGER NOT NULL DEFAULT 0,
    estado          TEXT    NOT NULL,
    error           TEXT,
    pausa_manual    INTEGER NOT NULL DEFAULT 0,
    creado          REAL    NOT NULL,
    actualizado     REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_copias_estado ON copias(estado);
CREATE TABLE IF NOT EXISTS destinos (
    copia_id          INTEGER NOT NULL,
    ruta              TEXT    NOT NULL,
    orden             INTEGER NOT NULL DEFAULT 0,
    total_bytes       INTEGER NOT NULL DEFAULT 0,
    copiados_bytes    INTEGER NOT NULL DEFAULT 0,
    total_archivos    INTEGER NOT NULL DEFAULT 0,
    copiados_archivos INTEGER NOT NULL DEFAULT 0,
    estado            TEXT    NOT NULL DEFAULT 'running',
    error             TEXT,
    actualizado       REAL    NOT NULL,
    PRIMARY KEY (copia_id, ruta)
);
"""


class Store:
    """Acceso al historial. Un único hilo escribe: se protege con un candado."""

    def __init__(self, ruta=None):
        if ruta is None:
            from .util import data_dir

            ruta = os.path.join(data_dir(), "historial.db")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self.ruta = ruta
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(ruta, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.executescript(_ESQUEMA)
            self._migrar()
            self._conn.commit()

    def _migrar(self):
        """Añade columnas nuevas a historiales creados por versiones anteriores."""
        columnas = {f[1] for f in self._conn.execute("PRAGMA table_info(copias)")}
        if "pausa_manual" not in columnas:
            self._conn.execute(
                "ALTER TABLE copias ADD COLUMN pausa_manual INTEGER NOT NULL DEFAULT 0"
            )

    # ------------------------------------------------------------------
    def crear(self, origenes, destinos) -> int:
        """Crea la copia y sus destinos (una fila por carpeta de destino)."""
        if isinstance(destinos, str):
            destinos = [destinos]
        destinos = list(destinos)
        if not destinos:
            raise ValueError("La copia necesita al menos un destino")
        ahora = time.time()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO copias (origenes, destino, estado, creado, actualizado)"
                " VALUES (?, ?, 'running', ?, ?)",
                (json.dumps(list(origenes)), destinos[0], ahora, ahora),
            )
            op_id = int(cur.lastrowid)
            self._conn.executemany(
                "INSERT INTO destinos (copia_id, ruta, orden, estado, actualizado)"
                " VALUES (?, ?, ?, 'running', ?)",
                [(op_id, ruta, orden, ahora) for orden, ruta in enumerate(destinos)],
            )
            self._conn.commit()
            return op_id

    def actualizar(self, op_id, *, copiados=None, archivos=None,
                   total_bytes=None, total_archivos=None):
        campos, valores = [], []
        if copiados is not None:
            campos.append("copiados_bytes = ?")
            valores.append(int(copiados))
        if archivos is not None:
            campos.append("copiados_archivos = ?")
            valores.append(int(archivos))
        if total_bytes is not None:
            campos.append("total_bytes = ?")
            valores.append(int(total_bytes))
        if total_archivos is not None:
            campos.append("total_archivos = ?")
            valores.append(int(total_archivos))
        if not campos:
            return
        campos.append("actualizado = ?")
        valores.append(time.time())
        valores.append(op_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE copias SET {', '.join(campos)} WHERE id = ?", valores
            )
            self._conn.commit()

    def actualizar_destino(self, op_id, ruta, *, copiados=None, archivos=None,
                          total_bytes=None, total_archivos=None, estado=None,
                          error=None):
        campos, valores = [], []
        if copiados is not None:
            campos.append("copiados_bytes = ?")
            valores.append(int(copiados))
        if archivos is not None:
            campos.append("copiados_archivos = ?")
            valores.append(int(archivos))
        if total_bytes is not None:
            campos.append("total_bytes = ?")
            valores.append(int(total_bytes))
        if total_archivos is not None:
            campos.append("total_archivos = ?")
            valores.append(int(total_archivos))
        if estado is not None:
            campos.append("estado = ?")
            valores.append(estado)
        if error is not None:
            campos.append("error = ?")
            valores.append(error)
        if not campos:
            return
        campos.append("actualizado = ?")
        valores.append(time.time())
        valores.extend((op_id, ruta))
        with self._lock:
            self._conn.execute(
                f"UPDATE destinos SET {', '.join(campos)}"
                " WHERE copia_id = ? AND ruta = ?",
                valores,
            )
            self._conn.commit()

    def destinos_de(self, op_id):
        """Destinos de una copia, en el orden en que se eligieron."""
        with self._lock:
            filas = self._conn.execute(
                "SELECT * FROM destinos WHERE copia_id = ? ORDER BY orden, ruta",
                (op_id,),
            ).fetchall()
        return [dict(f) for f in filas]

    def marcar(self, op_id, estado, error=None, manual=None):
        """Actualiza el estado. Con `manual` se guarda si la pausa la pidió el
        usuario (no debe reanudarse sola) o si vino de un cierre o un fallo."""
        if estado not in ESTADOS:
            raise ValueError(f"Estado desconocido: {estado}")
        campos = ["estado = ?", "error = ?", "actualizado = ?"]
        valores = [estado, error, time.time()]
        if manual is not None:
            campos.append("pausa_manual = ?")
            valores.append(1 if manual else 0)
        valores.append(op_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE copias SET {', '.join(campos)} WHERE id = ?", valores
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    def obtener(self, op_id):
        with self._lock:
            fila = self._conn.execute(
                "SELECT * FROM copias WHERE id = ?", (op_id,)
            ).fetchone()
        return _a_dict(fila)

    def listar(self, limite=500):
        with self._lock:
            filas = self._conn.execute(
                "SELECT * FROM copias ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
        return [_a_dict(f) for f in filas]

    def pendientes(self):
        """Copias que estaban en marcha o en pausa al último cierre."""
        with self._lock:
            filas = self._conn.execute(
                "SELECT * FROM copias WHERE estado IN ('running', 'paused')"
                " ORDER BY id DESC"
            ).fetchall()
        return [_a_dict(f) for f in filas]

    def cerrar(self):
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass


def _a_dict(fila) -> dict:
    if fila is None:
        return None
    d = dict(fila)
    try:
        d["origenes"] = json.loads(d["origenes"])
    except (TypeError, ValueError):
        d["origenes"] = []
    return d