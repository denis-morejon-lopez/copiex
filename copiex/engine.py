# -*- coding: utf-8 -*-
"""Motor de copias: progreso, pausa, reanudación y cancelación.

Cada copia se ejecuta en su propio hilo. La pausa se frena en el límite de
cada bloque leído, así que reanudar continúa exactamente donde se quedó.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
import traceback

BLOQUE = 1024 * 1024  # 1 MiB
INTERVALO_AVISO = 0.12  # mínimo entre avisos a la interfaz
INTERVALO_GUARDADO = 0.5  # mínimo entre escrituras en SQLite


class ErrorCopia(Exception):
    """Error esperable (permisos, destino inexistente, etc.)."""


class Operacion:
    """Una copia en curso o ya finalizada."""

    def __init__(self, op_id, origenes, destino, store):
        self.id = op_id
        self.origenes = list(origenes)
        self.destino = destino
        self._store = store

        self.total_bytes = 0
        self.copiados = 0
        self.total_archivos = 0
        self.archivos_ok = 0
        self.estado = "running"  # running | paused | cancelled | done | error
        self.error = None
        self.creado = time.time()

        self.velocidad = 0.0  # media móvil exponencial de bytes/s
        self._bloqueando = False  # ¿está ahora mismo escrito en el destino?
        self._tramo = 0  # bytes escritos en el tramo actual (para la pausa limpia)

        self._corriendo = threading.Event()
        self._corriendo.set()
        self._cancelado = threading.Event()
        self._terminado = threading.Event()
        self._hilo = None

        self._oyentes = []
        self._ultimo_aviso = 0.0
        self._ultimo_guardado = 0.0
        self._v_bytes = 0
        self._v_tiempo = time.monotonic()

    # ------------------------------------------------------------------
    # control
    # ------------------------------------------------------------------
    def pausar(self):
        if self.estado != "running":
            return False
        self._corriendo.clear()
        self.estado = "paused"
        self._persistir_estado()
        self._aviso(force=True)
        return True

    def reanudar(self):
        if self.estado != "paused":
            return False
        self.estado = "running"
        self._v_bytes = self.copiados
        self._v_tiempo = time.monotonic()
        self._corriendo.set()
        self._persistir_estado()
        self._aviso(force=True)
        return True

    def cancelar(self):
        if self.estado in ("done", "cancelled"):
            return False
        self._cancelado.set()
        self._corriendo.set()  # despierta si estaba en pausa
        self.estado = "cancelled"
        self._persistir_estado()
        self._aviso(force=True)
        return True

    def _persistir_estado(self):
        """Deja el estado (y el progreso) en el historial de forma inmediata."""
        if self._store is None:
            return
        try:
            self._store.marcar(self.id, self.estado, self.error)
            self._store.actualizar(
                self.id,
                copiados=self.copiados,
                archivos=self.archivos_ok,
                total_bytes=self.total_bytes,
                total_archivos=self.total_archivos,
            )
        except Exception:
            traceback.print_exc()

    def unirse(self, tiempo=None):
        hilo = self._hilo
        if hilo is not None and hilo.is_alive():
            hilo.join(tiempo)
        return self._terminado.is_set()

    # ------------------------------------------------------------------
    # observadores (se ejecutan SIEMPRE en el hilo principal de GTK)
    # ------------------------------------------------------------------
    def agregar_oyente(self, funcion):
        if funcion not in self._oyentes:
            self._oyentes.append(funcion)

    def quitar_oyente(self, funcion):
        if funcion in self._oyentes:
            self._oyentes.remove(funcion)

    def _aviso(self, force: bool = False):
        ahora = time.monotonic()
        if not force and (ahora - self._ultimo_aviso) < INTERVALO_AVISO:
            return
        self._ultimo_aviso = ahora
        for funcion in list(self._oyentes):
            try:
                funcion(self)
            except Exception:
                traceback.print_exc()

    def _guardar(self, force: bool = False):
        if self._store is None:
            return
        ahora = time.monotonic()
        if not force and (ahora - self._ultimo_guardado) < INTERVALO_GUARDADO:
            return
        self._ultimo_guardado = ahora
        try:
            self._store.actualizar(
                self.id,
                copiados=self.copiados,
                archivos=self.archivos_ok,
                total_bytes=self.total_bytes,
                total_archivos=self.total_archivos,
            )
        except Exception:
            traceback.print_exc()

    # ------------------------------------------------------------------
    def _velocidad(self, ahora):
        transcurrido = ahora - self._v_tiempo
        if transcurrido >= 0.5:
            instantanea = (self.copiados - self._v_bytes) / transcurrido
            if instantanea >= 0:
                alfa = 0.4
                self.velocidad = (
                    instantanea
                    if self.velocidad <= 0
                    else (alfa * instantanea + (1 - alfa) * self.velocidad)
                )
            self._v_bytes = self.copiados
            self._v_tiempo = ahora
        return self.velocidad

    @property
    def fraccion(self) -> float:
        if self.total_bytes <= 0:
            return 1.0 if self.estado == "done" else 0.0
        return min(1.0, self.copiados / self.total_bytes)

    @property
    def restante(self) -> float | None:
        """Segundos restantes estimados, o None si no se puede estimar."""
        if self.estado != "running" or self.velocidad <= 0:
            return None
        falta = self.total_bytes - self.copiados
        if falta <= 0:
            return 0.0
        return falta / self.velocidad

    # ------------------------------------------------------------------
    # ejecución
    # ------------------------------------------------------------------
    def iniciar(self, reanudando=False):
        self._reanudando = reanudando
        self._hilo = threading.Thread(
            target=self._trabajar, name=f"copia-{self.id}", daemon=True
        )
        self._hilo.start()

    def _trabajar(self):
        try:
            self._trabajar_seguro()
        except Exception as exc:  # nunca debe morir sin avisar
            traceback.print_exc()
            self.estado = "error"
            self.error = str(exc)
        finally:
            if self.estado == "running":
                self.estado = "done"
            if self._store is not None:
                try:
                    self._store.marcar(self.id, self.estado, self.error)
                    self._store.actualizar(
                        self.id,
                        copiados=self.copiados,
                        archivos=self.archivos_ok,
                        total_bytes=self.total_bytes,
                        total_archivos=self.total_archivos,
                    )
                except Exception:
                    traceback.print_exc()
            self._terminado.set()
            self._aviso(force=True)

    def _trabajar_seguro(self):
        if not os.path.isdir(self.destino):
            raise ErrorCopia(f"El destino no es una carpeta: {self.destino}")
        plan = self._planificar()
        self._v_bytes = self.copiados
        self._v_tiempo = time.monotonic()

        for indice, (origen, destino) in enumerate(plan):
            if self._cancelado.is_set():
                break
            if not self._esperar_permiso():
                break  # cancelado mientras estaba en pausa

            try:
                if os.path.exists(destino) and os.path.getsize(destino) == os.path.getsize(origen):
                    # Ya estaba copiado (lo contó el planificador al reanudar):
                    # se marca hecho sin volver a sumar bytes
                    self.archivos_ok += 1
                    self._guardar()
                    self._aviso()
                    continue
                self._copiar_fichero(origen, destino)
            except ErrorCopia:
                raise
            except OSError as exc:
                raise ErrorCopia(f"{exc}") from exc

            self.archivos_ok += 1
            self._bloqueando = False
            self._guardar()
            self._aviso()

        if not self._cancelado.is_set():
            if self.archivos_ok < self.total_archivos:
                raise ErrorCopia(
                    f"Solo se pudieron copiar {self.archivos_ok} de "
                    f"{self.total_archivos} elementos"
                )
            if self.copiados < self.total_bytes:
                self.copiados = self.total_bytes

    def _esperar_permiso(self) -> bool:
        """Devuelve False si la operación fue cancelada mientras esperaba."""
        while not self._cancelado.is_set():
            if self._corriendo.is_set():
                return True
            self._corriendo.wait(0.2)
        return False

    def _planificar(self):
        """Lista de pares (origen, destino) y totales. También recalcula
        `copiados` con lo que ya existe completo en destino (reanudación)."""
        plan = []
        bytes_totales = 0
        for origen in self.origenes:
            origen = os.path.abspath(origen)
            if not os.path.exists(origen):
                raise ErrorCopia(f"No existe: {origen}")
            destino_raiz = os.path.join(self.destino, os.path.basename(origen.rstrip(os.sep)))
            if os.path.isdir(origen) and not os.path.islink(origen):
                for raiz, dirs, ficheros in os.walk(origen):
                    dirs.sort()
                    rel = os.path.relpath(raiz, origen)
                    base = destino_raiz if rel == "." else os.path.join(destino_raiz, rel)
                    for nombre in ficheros:
                        src = os.path.join(raiz, nombre)
                        dst = os.path.join(base, nombre)
                        if os.path.isdir(src):  # enlace roto a directorio
                            continue
                        plan.append((src, dst))
                        bytes_totales += _tamano(src)
            else:
                plan.append((origen, destino_raiz))
                bytes_totales += _tamano(origen)

        if not plan:
            raise ErrorCopia("No hay nada que copiar")

        copiados_previos = 0
        for src, dst in plan:
            try:
                if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
                    copiados_previos += os.path.getsize(src)
            except OSError:
                continue

        self.total_archivos = len(plan)
        self.total_bytes = bytes_totales
        self.copiados = copiados_previos
        self.archivos_ok = 0
        self._guardar(force=True)
        self._aviso(force=True)
        return plan

    def _copiar_fichero(self, origen, destino):
        carpeta = os.path.dirname(destino)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        self._bloqueando = True
        escritos = 0
        try:
            with open(origen, "rb") as fuente, open(destino, "wb") as salida:
                while True:
                    if self._cancelado.is_set():
                        break
                    if not self._corriendo.is_set():
                        if not self._esperar_permiso():
                            break
                    bloque = fuente.read(BLOQUE)
                    if not bloque:
                        break
                    salida.write(bloque)
                    escritos += len(bloque)
                    self.copiados += len(bloque)
                    self._tramo = escritos
                    ahora = time.monotonic()
                    self._velocidad(ahora)
                    self._aviso()
                    self._guardar()
        finally:
            self._bloqueando = False
            self._tramo = 0

        if self._cancelado.is_set():
            return

        try:
            shutil.copystat(origen, destino)
        except OSError:
            pass  # metadatos es lo de menos

    def estado_para_pausa(self) -> tuple[bool, int]:
        """¿Se puede pausar ahora mismo? Devuelve (bloqueando, bytes del tramo)."""
        return self._bloqueando, self._tramo


def _tamano(ruta: str) -> int:
    try:
        if os.path.isdir(ruta) and not os.path.islink(ruta):
            total = 0
            for raiz, dirs, ficheros in os.walk(ruta):
                for nombre in ficheros:
                    try:
                        total += os.path.getsize(os.path.join(raiz, nombre))
                    except OSError:
                        pass
            return total
        return os.path.getsize(ruta)
    except OSError:
        return 0


class Motor:
    """Administrador de todas las copias."""

    def __init__(self, store):
        self.store = store
        self._operaciones = {}
        self._lock = threading.RLock()
        self._oyentes = []

    # ------------------------------------------------------------------
    def agregar_oyente(self, funcion):
        if funcion not in self._oyentes:
            self._oyentes.append(funcion)

    def _nueva(self, op) -> None:
        self._operaciones[op.id] = op
        op.agregar_oyente(self._propagar)
        for oyente in self._oyentes:
            op.agregar_oyente(oyente)

    def _propagar(self, op):
        # ya está en el hilo principal de GTK (los oyentes se agregan ahí)
        pass

    def crear(self, origenes, destino) -> Operacion:
        origenes = [os.path.abspath(o) for o in origenes]
        if not origenes:
            raise ErrorCopia("No has indicado ningún origen")
        destino = os.path.abspath(destino)
        for origen in origenes:
            origen = os.path.abspath(origen)
            if _es_hijo(destino, origen):
                raise ErrorCopia(
                    f"El destino está dentro del origen ({short(destino)} ⊂ {short(origen)})"
                )
        if not os.path.isdir(destino):
            raise ErrorCopia(f"El destino no es una carpeta: {destino}")
        for origen in origenes:
            if not os.path.exists(origen):
                raise ErrorCopia(f"No existe: {origen}")

        op_id = self.store.crear(origenes, destino)
        op = Operacion(op_id, origenes, destino, self.store)
        self._nueva(op)
        op.iniciar()
        return op

    def obtener(self, op_id) -> Operacion | None:
        return self._operaciones.get(op_id)

    def todas(self):
        """Operaciones de esta sesión, las más recientes primero."""
        return sorted(self._operaciones.values(), key=lambda o: o.id, reverse=True)

    # ------------------------------------------------------------------
    def cargar_historial(self) -> list[Operacion]:
        """Recupera del historial las copias que quedaron a medias y las deja
        en pausa, listas para que el usuario las reanude."""
        with self._lock:
            for fila in self.store.pendientes():
                if fila["id"] in self._operaciones:
                    continue
                op = Operacion(fila["id"], fila["origenes"], fila["destino"], self.store)
                op.total_bytes = fila["total_bytes"]
                op.copiados = fila["copiados_bytes"]
                op.total_archivos = fila["total_archivos"]
                op.archivos_ok = fila["copiados_archivos"]
                op.estado = "paused"
                op.creado = fila["creado"]
                self._nueva(op)
                if fila["estado"] == "running":
                    self.store.marcar(op.id, "paused")
        return self.todas()

    def pausar(self, op_id):
        op = self.obtener(op_id)
        return op.pausar() if op else False

    def reanudar(self, op_id):
        op = self.obtener(op_id)
        if op is None:
            return False
        if op.estado == "paused":
            # Si estaba pausada de una sesión anterior, su hilo ya no existe
            if op._terminado.is_set() or op._hilo is None:
                op.estado = "running"
                op.error = None
                op._terminado.clear()
                op._cancelado.clear()
                op._corriendo.set()
                op.iniciar(reanudando=True)
                op._aviso(force=True)
                return True
            return op.reanudar()
        return False

    def cancelar(self, op_id):
        op = self.obtener(op_id)
        return op.cancelar() if op else False

    def activas(self) -> list[Operacion]:
        return [o for o in self.todas() if o.estado in ("running", "paused")]

    def pausar_todo(self) -> int:
        return sum(1 for o in self.todas() if o.pausar())

    def apagar(self, esperar=2.0):
        """Pausa todo y espera un poco para dejar el historial consistente."""
        self.pausar_todo()
        inicio = time.monotonic()
        for op in self.todas():
            restante = max(0.1, esperar - (time.monotonic() - inicio))
            op.unirse(restante)


def _es_hijo(posible_hijo: str, padre: str) -> bool:
    hijo = os.path.abspath(posible_hijo)
    padre = os.path.abspath(padre)
    return hijo == padre or hijo.startswith(padre.rstrip(os.sep) + os.sep)


def short(path: str) -> str:
    from .util import short_path

    return short_path(path)