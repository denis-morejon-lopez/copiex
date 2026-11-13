# -*- coding: utf-8 -*-
"""Motor de copias: progreso, pausa, reanudación y cancelación.

Cada copia se ejecuta en su propio hilo. La pausa se frena en el límite de
cada bloque leído, así que reanudar continúa exactamente donde se quedó.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
import traceback

BLOQUE = 1024 * 1024  # 1 MiB
INTERVALO_AVISO = 0.12

log = logging.getLogger(__name__)  # mínimo entre avisos a la interfaz
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
        # Pausa pedida por el usuario: el vigilante no la reanuda sola.
        self.pausa_manual = False
        # Motivo por el que el vigilante espera (dispositivo ausente, etc.).
        self.espera = ""

        self.velocidad = 0.0  # media móvil exponencial de bytes/s
        self._bloqueando = False  # ¿está ahora mismo escrito en el destino?
        self._tramo = 0  # bytes escritos en el tramo actual (para la pausa limpia)

        self._corriendo = threading.Event()
        self._corriendo.set()
        self._cancelado = threading.Event()
        self._terminado = threading.Event()
        self._hilo = None

        # Carpetas ya creadas por esta copia: evita un makedirs por fichero
        self._dirs_creados = set()

        self._oyentes = []
        self._ultimo_aviso = 0.0
        self._ultimo_guardado = 0.0
        self._v_bytes = 0
        self._v_tiempo = time.monotonic()

    # ------------------------------------------------------------------
    # control
    # ------------------------------------------------------------------
    def pausar(self, manual=True):
        if self.estado != "running":
            return False
        self.pausa_manual = manual
        self._corriendo.clear()
        self.estado = "paused"
        self._persistir_estado()
        self._aviso(force=True)
        log.info(
            "copia %s: en pausa (%s) en %d de %d bytes",
            self.id,
            "manual" if manual else "por cierre",
            self.copiados,
            self.total_bytes,
        )
        return True

    def reanudar(self):
        if self.estado not in ("paused", "error"):
            return False
        self.pausa_manual = False
        self.espera = ""
        self.estado = "running"
        self._v_bytes = self.copiados
        self._v_tiempo = time.monotonic()
        self._corriendo.set()
        self._persistir_estado()
        self._aviso(force=True)
        log.info(
            "copia %s: reanudada en %d de %d bytes",
            self.id,
            self.copiados,
            self.total_bytes,
        )
        return True

    def cancelar(self):
        if self.estado in ("done", "cancelled"):
            return False
        self._cancelado.set()
        self._corriendo.set()  # despierta si estaba en pausa
        self.estado = "cancelled"
        self._persistir_estado()
        self._aviso(force=True)
        self._limpiar_parciales()
        log.info(
            "copia %s: cancelada; se borran los destinos incompletos", self.id
        )
        return True

    def _limpiar_parciales(self):
        """Borra lo que esta copia dejó a medias en el destino.

        Cancelar deja el destino limpio: los ficheros incompletos desaparecen y
        una copia posterior empieza de cero. Los que ya estaban completos no se
        tocan.
        """
        for origen, destino in _pares(self.origenes, self.destino):
            _borrar_si_incompleto(origen, destino)

    def anotar_espera(self, motivo: str) -> bool:
        """Motivo por el que el vigilante aún no puede continuar ('' = listo).

        Se puede llamar desde el hilo del vigilante: los oyentes ya se encargan
        de pasar el aviso al hilo de GTK. Devuelve True si el motivo cambió, que
        es cuando merece la pena anotarlo también en el registro (si no, una
        copia esperando un dispositivo escribiría una línea cada 6 segundos).
        """
        if self.espera == motivo:
            return False
        self.espera = motivo
        self._aviso(force=True)
        return True

    def _persistir_estado(self):
        """Deja el estado (y el progreso) en el historial de forma inmediata."""
        if self._store is None:
            return
        try:
            self._store.marcar(
                self.id, self.estado, self.error, manual=self.pausa_manual
            )
            self._store.actualizar(
                self.id,
                copiados=self.copiados,
                archivos=self.archivos_ok,
                total_bytes=self.total_bytes,
                total_archivos=self.total_archivos,
            )
        except Exception:
            log.exception("copia %s: no se pudo guardar el estado", self.id)

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
                log.exception("copia %s: un observador falló", self.id)

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
            log.exception("copia %s: no se pudo actualizar el progreso", self.id)

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
        log.debug("copia %s: hilo de copia arrancado", self.id)
        try:
            self._trabajar_seguro()
        except ErrorCopia as exc:
            # Error esperado (ruta inexistente, permiso, E/S): va a la fila, sin traza
            self.estado = "error"
            self.error = str(exc)
            log.warning("copia %s: error: %s", self.id, exc)
        except Exception as exc:  # nunca debe morir sin avisar
            log.exception("copia %s: fallo inesperado", self.id)
            self.estado = "error"
            self.error = str(exc)
        finally:
            if self.estado == "running":
                self.estado = "done"
            if self._store is not None:
                try:
                    self._store.marcar(
                self.id, self.estado, self.error, manual=self.pausa_manual
            )
                    self._store.actualizar(
                        self.id,
                        copiados=self.copiados,
                        archivos=self.archivos_ok,
                        total_bytes=self.total_bytes,
                        total_archivos=self.total_archivos,
                    )
                except Exception:
                    log.exception("copia %s: no se pudo cerrar el historial", self.id)
            self._terminado.set()
            self._aviso(force=True)
            log.info(
                "copia %s: %s (%d de %d bytes, %d de %d archivos)%s",
                self.id,
                self.estado,
                self.copiados,
                self.total_bytes,
                self.archivos_ok,
                self.total_archivos,
                f" — {self.error}" if self.error else "",
            )

    def _trabajar_seguro(self):
        if not os.path.isdir(self.destino):
            raise ErrorCopia(f"El destino no es una carpeta: {self.destino}")
        plan, tamanos = self._planificar()
        log.info(
            "copia %s: %d archivo(s), %d bytes, %d ya presentes en destino",
            self.id,
            len(plan),
            self.total_bytes,
            self.copiados,
        )
        self._v_bytes = self.copiados
        self._v_tiempo = time.monotonic()

        for indice, (origen, destino) in enumerate(plan):
            if self._cancelado.is_set():
                break
            if not self._esperar_permiso():
                break  # cancelado mientras estaba en pausa

            try:
                if os.path.exists(destino) and os.path.getsize(destino) == tamanos[origen]:
                    # Ya estaba copiado (lo contó el planificador al reanudar):
                    # se marca hecho sin volver a sumar bytes
                    self.archivos_ok += 1
                    log.debug("copia %s: %s ya estaba completo, se salta", self.id, short(destino))
                    self._guardar()
                    self._aviso()
                    continue
                self._copiar_fichero(origen, destino, tamanos[origen])
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
        `copiados` con lo que ya existe en destino (reanudación)."""
        for origen in self.origenes:
            origen = os.path.abspath(origen)
            if not os.path.exists(origen):
                raise ErrorCopia(f"No existe: {origen}")

        plan = _pares(self.origenes, self.destino)
        if not plan:
            raise ErrorCopia("No hay nada que copiar")
        # Un solo stat por fichero: el tamaño se guarda para la suma y para no
        # volver a preguntarlo al copiar (con miles de ficheros se nota).
        tamanos = {}
        bytes_totales = 0
        for src, _dst in plan:
            try:
                tam = os.stat(src).st_size
            except OSError:
                tam = 0
            tamanos[src] = tam
            bytes_totales += tam

        # Lo que ya está en destino cuenta como copiado: los ficheros completos
        # enteros y los que quedaron a medias solo hasta donde llegaron.
        copiados_previos = 0
        for src, dst in plan:
            try:
                if not os.path.exists(dst):
                    continue
                tam_src = os.path.getsize(src)
                tam_dst = os.path.getsize(dst)
            except OSError:
                continue
            if tam_dst == tam_src:
                copiados_previos += tam_src  # completo: se saltará
            elif 0 < tam_dst < tam_src:
                copiados_previos += tam_dst  # a medias: se continúa desde ahí

        self.total_archivos = len(plan)
        self.total_bytes = bytes_totales
        self.copiados = copiados_previos
        self.archivos_ok = 0
        self._guardar(force=True)
        self._aviso(force=True)
        return plan, tamanos

    def _asegurar_carpeta(self, destino):
        """Crea la carpeta del destino una sola vez por copia."""
        carpeta = os.path.dirname(destino)
        if not carpeta or carpeta in self._dirs_creados:
            return
        os.makedirs(carpeta, exist_ok=True)
        self._dirs_creados.add(carpeta)

    def _copiar_fichero(self, origen, destino, tam_origen=None):
        """Copia un fichero reanudando por byte.

        La escritura es secuencial, así que el tamaño del destino es un punto de
        continuación válido: tras un cierre brusco se sigue desde ahí en lugar de
        rehacer el fichero entero.

        Los datos se mueven con `os.copy_file_range` (copia dentro del núcleo,
        sin pasar por Python) cuando el sistema de ficheros lo admite; si no, se
        cae a lectura/escritura por bloques, con el mismo resultado.
        """
        self._asegurar_carpeta(destino)

        desplazamiento = 0
        modo = "wb"
        try:
            if tam_origen is None:
                tam_origen = os.stat(origen).st_size
            tam_destino = os.stat(destino).st_size
            if 0 < tam_destino < tam_origen:
                desplazamiento = tam_destino
                modo = "r+b"
        except OSError:
            desplazamiento, modo = 0, "wb"

        log.debug(
            "copia %s: %s -> %s desde %d de %d bytes",
            self.id,
            short(origen),
            short(destino),
            desplazamiento,
            tam_origen,
        )
        self._bloqueando = True
        escritos = desplazamiento
        try:
            # Sin búfer de Python: los descriptores se usan tal cual y las
            # posiciones las lleva el núcleo, igual con copy_file_range que
            # con read/write.
            with open(origen, "rb", buffering=0) as fuente, open(
                destino, modo, buffering=0
            ) as salida:
                if desplazamiento:
                    fuente.seek(desplazamiento)
                    salida.seek(desplazamiento)
                usar_rango = hasattr(os, "copy_file_range")
                while True:
                    if self._cancelado.is_set():
                        break
                    if not self._corriendo.is_set():
                        if not self._esperar_permiso():
                            break
                    if usar_rango:
                        try:
                            leidos = os.copy_file_range(
                                fuente.fileno(), salida.fileno(), BLOQUE
                            )
                        except OSError as exc:
                            # EXDEV (otro sistema de ficheros), EOPNOTSUPP…:
                            # el resto del fichero se copia a mano.
                            log.debug(
                                "copia %s: copy_file_range no sirve aquí (%s); "
                                "se sigue con lectura/escritura",
                                self.id,
                                exc,
                            )
                            usar_rango = False
                            continue
                        if leidos == 0:
                            break
                    else:
                        bloque = fuente.read(BLOQUE)
                        if not bloque:
                            break
                        salida.write(bloque)
                        leidos = len(bloque)
                    escritos += leidos
                    self.copiados += leidos
                    self._tramo = escritos
                    ahora = time.monotonic()
                    self._velocidad(ahora)
                    self._aviso()
                    self._guardar()
        finally:
            self._bloqueando = False
            self._tramo = 0

        if self._cancelado.is_set():
            # Si el cancelar llegó justo al abrir el fichero, tampoco se deja resto
            _borrar_si_incompleto(origen, destino)
            log.debug("copia %s: %s cancelado a %d bytes", self.id, short(destino), escritos)
            return

        log.debug("copia %s: %s completo (%d bytes)", self.id, short(destino), escritos)
        try:
            shutil.copystat(origen, destino)
        except OSError:
            pass  # metadatos es lo de menos

    def estado_para_pausa(self) -> tuple[bool, int]:
        """¿Se puede pausar ahora mismo? Devuelve (bloqueando, bytes del tramo)."""
        return self._bloqueando, self._tramo


def _borrar_si_incompleto(origen: str, destino: str) -> None:
    """Elimina el destino si quedó a medias (más pequeño que su origen)."""
    try:
        if os.path.exists(destino) and os.path.getsize(destino) < os.path.getsize(origen):
            os.unlink(destino)
    except OSError:
        pass  # mejor esfuerzo: cancelar nunca debe fallar por esto


def _pares(origenes, destino) -> list[tuple[str, str]]:
    """Pares (origen, destino) que supone copiar `origenes` dentro de `destino`.

    No comprueba que el origen exista: de eso se encarga quien la llama (el
    planificador) o se salta el par (la limpieza al cancelar).
    """
    pares = []
    for origen in origenes:
        origen = os.path.abspath(origen)
        destino_raiz = os.path.join(destino, os.path.basename(origen.rstrip(os.sep)))
        if os.path.isdir(origen) and not os.path.islink(origen):
            for raiz, dirs, ficheros in os.walk(origen):
                dirs.sort()
                rel = os.path.relpath(raiz, origen)
                base = destino_raiz if rel == "." else os.path.join(destino_raiz, rel)
                for nombre in ficheros:
                    src = os.path.join(raiz, nombre)
                    if os.path.isdir(src):  # enlace roto a directorio
                        continue
                    pares.append((src, os.path.join(base, nombre)))
        else:
            pares.append((origen, destino_raiz))
    return pares


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
        # Las comprobaciones de disco (y su coste si un dispositivo no responde)
        # se hacen en el hilo de la copia: la tarea aparece al instante y, si la
        # ruta falla, la fila se marca con el error.
        log.debug("copia nueva: %d origen(es) -> %s", len(origenes), short(destino))
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
                op = Operacion(
                    fila["id"], fila["origenes"], fila["destino"], self.store
                )
                op.total_bytes = fila["total_bytes"]
                op.copiados = fila["copiados_bytes"]
                op.total_archivos = fila["total_archivos"]
                op.archivos_ok = fila["copiados_archivos"]
                op.estado = "paused"
                op.pausa_manual = bool(fila.get("pausa_manual"))
                op.creado = fila["creado"]
                log.debug(
                    "copia %s: recuperada del historial en estado %s (%d de %d bytes)",
                    op.id,
                    fila["estado"],
                    op.copiados,
                    op.total_bytes,
                )
                self._nueva(op)
                if fila["estado"] == "running":
                    self.store.marcar(op.id, "paused")
        return self.todas()

    def pausar(self, op_id, manual=True):
        op = self.obtener(op_id)
        return op.pausar(manual=manual) if op else False

    def reanudar(self, op_id):
        """Reanuda una copia en pausa o con error.

        Una copia cancelada es definitiva: ni esta llamada ni el vigilante la
        reanudan, tampoco al reabrir la aplicación (`cargar_historial` solo
        recupera las que estaban en marcha o en pausa).
        """
        op = self.obtener(op_id)
        if op is None:
            return False
        if op.estado in ("paused", "error"):
            # Si el hilo ya murió (sesión anterior o fallo), se arranca otro
            if op._terminado.is_set() or op._hilo is None:
                op.estado = "running"
                op.error = None
                op.espera = ""
                op.pausa_manual = False
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
        """Pausa por cierre de la aplicación: son reanudables automáticamente."""
        return sum(1 for o in self.todas() if o.pausar(manual=False))

    def apagar(self, esperar=2.0):
        """Pausa todo y espera un poco para dejar el historial consistente."""
        pausadas = self.pausar_todo()
        if pausadas:
            log.info("apagando: %d copia(s) en pausa", pausadas)
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