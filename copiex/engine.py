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
MOTIVO_CAMBIO = "el fichero de destino cambió durante la copia"

log = logging.getLogger(__name__)  # mínimo entre avisos a la interfaz
INTERVALO_GUARDADO = 0.5  # mínimo entre escrituras en SQLite


class ErrorCopia(Exception):
    """Error esperable (permisos, destino inexistente, etc.)."""


class DestinoCopia:
    """Estado de una carpeta de destino dentro de una copia.

    Una copia puede repartirse a varias carpetas a la vez; cada una lleva su
    propio progreso, su estado y el motivo por el que espera. La operación los
    agrega: los bytes copiados son el mínimo de todos (lo que ya está en todos
    los destinos).
    """

    def __init__(self, ruta, orden=0):
        self.ruta = ruta
        self.orden = orden
        self.total_bytes = 0
        self.copiados = 0
        self.total_archivos = 0
        self.archivos_ok = 0
        # running | paused | done | error | cancelled
        self.estado = "running"
        self.error = None
        self.espera = ""
        # Carpetas creadas por esta copia en este destino (evita makedirs)
        self._dirs_creados = set()

    @property
    def fraccion(self) -> float:
        if self.total_bytes <= 0:
            return 1.0 if self.estado == "done" else 0.0
        return min(1.0, self.copiados / self.total_bytes)

    @property
    def terminado(self) -> bool:
        return self.estado in ("done", "error", "cancelled")


class Operacion:
    """Una copia en curso o ya finalizada."""

    def __init__(self, op_id, origenes, destinos, store):
        if isinstance(destinos, str):
            destinos = [destinos]
        self.id = op_id
        self.origenes = list(origenes)
        self.destinos = [
            DestinoCopia(ruta, orden) for orden, ruta in enumerate(destinos)
        ]
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

        self._oyentes = []
        self._ultimo_aviso = 0.0
        self._ultimo_guardado = 0.0
        self._v_bytes = 0
        self._v_tiempo = time.monotonic()

    @property
    def destino(self) -> str:
        """Primer destino de la copia (compatibilidad con textos y registros)."""
        return self.destinos[0].ruta if self.destinos else ""

    # ------------------------------------------------------------------
    # control
    # ------------------------------------------------------------------
    def pausar(self, manual=True):
        if self.estado != "running":
            return False
        self.pausa_manual = manual
        self._corriendo.clear()
        self.estado = "paused"
        for destino in self.destinos:
            if destino.estado == "running":
                destino.estado = "paused"
                destino.espera = ""
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
        for destino in self.destinos:
            if destino.estado in ("paused", "error"):
                destino.estado = "running"
                destino.error = None
                destino.espera = ""
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
        for destino in self.destinos:
            destino.estado = "cancelled"
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
        for destino in self.destinos:
            for origen, ruta in _pares(self.origenes, destino.ruta):
                _borrar_si_incompleto(origen, ruta)

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
            self._persistir_destinos()
        except Exception:
            log.exception("copia %s: no se pudo guardar el estado", self.id)

    def _persistir_destinos(self):
        """Guarda el progreso y el estado de cada destino."""
        if self._store is None:
            return
        for destino in self.destinos:
            estado = destino.estado
            if self.estado == "cancelled":
                estado = "cancelled"
            self._store.actualizar_destino(
                self.id,
                destino.ruta,
                copiados=destino.copiados,
                archivos=destino.archivos_ok,
                total_bytes=destino.total_bytes,
                total_archivos=destino.total_archivos,
                estado=estado,
                error=destino.error or "",
            )

    def _recalcular(self):
        """Agrega el estado de los destinos en el de la operación.

        Los bytes copiados son el mínimo de los destinos: la barra solo avanza
        cuando el bloque ya está en todos. Una operación está en pausa cuando
        ningún destino avanza (todos esperan a su dispositivo) y en error
        cuando alguno falló.
        """
        if self._cancelado.is_set():
            self.estado = "cancelled"
            return
        if not self.destinos:
            return
        for d in self.destinos:
            # Un destino con todos sus ficheros y bytes ya está terminado aunque
            # el último bloque no haya pasado por el comprobador de estado.
            if (
                d.estado in ("running", "paused")
                and d.total_archivos > 0
                and d.archivos_ok >= d.total_archivos
                and d.copiados >= d.total_bytes
            ):
                d.estado = "done"
                d.error = None
                d.espera = ""
        self.copiados = min(d.copiados for d in self.destinos)
        self.archivos_ok = min(d.archivos_ok for d in self.destinos)
        if all(d.estado == "done" for d in self.destinos):
            self.estado = "done"
            self.error = None
            self.espera = ""
            return
        if any(d.estado == "running" for d in self.destinos):
            self.estado = "running"
            self.error = None
            self.espera = ""
            return
        esperas = [d.espera for d in self.destinos if d.estado == "paused" and d.espera]
        self.espera = "; ".join(esperas)
        fallos = [d for d in self.destinos if d.estado == "error"]
        if fallos:
            self.estado = "error"
            self.error = "; ".join(
                f"{short(d.ruta)}: {d.error or 'fallo desconocido'}" for d in fallos
            )
        elif any(d.estado == "paused" for d in self.destinos):
            self.estado = "paused"
            self.error = None
        else:
            self.estado = "paused"

    def _destino_espera(self, destino: DestinoCopia, motivo: str):
        """El destino no está disponible ahora mismo: se espera sin fallar."""
        if destino.estado != "paused" or destino.espera != motivo:
            log.info(
                "copia %s: destino %s espera: %s",
                self.id,
                short(destino.ruta),
                motivo,
            )
        destino.estado = "paused"
        destino.espera = motivo
        destino.error = None
        self._recalcular()
        self._aviso(force=True)

    def _destino_cambio(self, destino: DestinoCopia, ruta: str, escritos: int):
        """El fichero de destino desapareció o se truncó: se corrige el progreso.

        Se descuenta lo que esta copia contaba de ese fichero y se suma lo que
        de verdad hay en el disco (cero si lo borraron). El destino queda en
        pausa con un motivo que el reintento automático reconoce.
        """
        real = 0
        try:
            real = os.path.getsize(ruta)
        except OSError:
            real = 0
        destino.copiados = max(0, destino.copiados - escritos + real)
        destino.estado = "paused"
        destino.espera = MOTIVO_CAMBIO
        destino.error = None
        log.warning(
            "copia %s: %s cambió durante la copia (quedan %d bytes); se reintentará",
            self.id,
            short(ruta),
            real,
        )
        self._recalcular()
        self._aviso(force=True)

    def _fallo_destino(self, destino: DestinoCopia, exc: OSError):
        """Un destino falló mientras se escribía: los demás siguen."""
        if not os.path.isdir(destino.ruta):
            self._destino_espera(
                destino, f"esperando la carpeta de destino {short(destino.ruta)}"
            )
            return
        destino.estado = "error"
        destino.error = str(exc)
        destino.espera = ""
        log.warning(
            "copia %s: el destino %s falló: %s",
            self.id,
            short(destino.ruta),
            exc,
        )
        self._recalcular()
        self._aviso(force=True)

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
            self._persistir_destinos()
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
            # Si el hilo muere por un fallo inesperado, ningún destino puede
            # quedarse «copiando»: se cierra su estado junto con la operación.
            for destino in self.destinos:
                if destino.estado == "running":
                    destino.estado = "error" if self.estado == "error" else "paused"
                    destino.error = destino.error or self.error
                    destino.espera = ""
            if self.estado == "running":
                self._recalcular()
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
        for destino in self.destinos:
            if not os.path.isdir(destino.ruta):
                self._destino_espera(
                    destino,
                    f"esperando la carpeta de destino {short(destino.ruta)}",
                )
        for intento in range(3):
            plan, tamanos = self._planificar()
            log.info(
                "copia %s: %d archivo(s), %d bytes, %d destino(s)%s",
                self.id,
                len(plan),
                self.total_bytes,
                len(self.destinos),
                f" (reintento {intento})" if intento else "",
            )
            self._v_bytes = self.copiados
            self._v_tiempo = time.monotonic()
            self._ejecutar_plan(plan)
            if self._cancelado.is_set():
                break
            # Un destino cuyo fichero se borró o truncó a mitad se reintenta
            # aquí mismo, en cuanto el primer destino termina: la carpeta sigue
            # disponible y no hace falta esperar al vigilante.
            pendientes = [
                destino
                for destino in self.destinos
                if destino.estado == "paused"
                and destino.espera == MOTIVO_CAMBIO
                and os.path.isdir(destino.ruta)
            ]
            if not pendientes:
                break
            log.info(
                "copia %s: %d destino(s) cambiaron durante la copia; se reintentan",
                self.id,
                len(pendientes),
            )
            for destino in pendientes:
                destino.estado = "running"
                destino.espera = ""

        # Ningún destino puede quedarse «copiando» con el hilo ya terminado
        # (era lo que dejaba los botones sin cambiar al final de la prueba real).
        for destino in self.destinos:
            if destino.estado == "running":
                destino.estado = "paused"
                destino.espera = destino.espera or "copia interrumpida"
        if self._cancelado.is_set():
            self.estado = "cancelled"
        else:
            self._recalcular()
            if self.estado == "error" and not self.error:
                self.error = "No se pudo copiar a todos los destinos"

    def _ejecutar_plan(self, plan):
        for origen, rutas_destino, tam in plan:
            if self._cancelado.is_set():
                break
            if not self._esperar_permiso():
                break  # cancelado mientras estaba en pausa

            pares = []
            for destino, ruta in zip(self.destinos, rutas_destino):
                if destino.estado in ("done", "error", "cancelled"):
                    continue
                if not os.path.isdir(destino.ruta):
                    self._destino_espera(
                        destino,
                        f"esperando la carpeta de destino {short(destino.ruta)}",
                    )
                    continue
                if os.path.exists(ruta) and os.path.getsize(ruta) == tam:
                    # Ya estaba copiado: se contó al planificar y no se rehace
                    continue
                pares.append((destino, ruta))
            if not pares:
                continue

            try:
                if len(pares) == 1:
                    destino, ruta = pares[0]
                    self._copiar_fichero(origen, destino, ruta, tam)
                else:
                    self._copiar_a_varios(origen, pares, tam)
            except ErrorCopia:
                raise
            except OSError as exc:
                raise ErrorCopia(f"{exc}") from exc

            self._bloqueando = False
            self._recalcular()
            self._guardar(force=True)
            self._aviso()

    def _esperar_permiso(self) -> bool:
        """Devuelve False si la operación fue cancelada mientras esperaba."""
        while not self._cancelado.is_set():
            if self._corriendo.is_set():
                return True
            self._corriendo.wait(0.2)
        return False

    def _planificar(self):
        """Plan por fichero con una ruta por destino y totales por destino.

        El origen se recorre una sola vez (`_pares` con cada destino da el mismo
        orden), así que la lista es: (origen, [destino1, destino2, …], tamaño).
        """
        for origen in self.origenes:
            origen = os.path.abspath(origen)
            if not os.path.exists(origen):
                raise ErrorCopia(f"No existe: {origen}")

        planes = [_pares(self.origenes, destino.ruta) for destino in self.destinos]
        if not planes or not planes[0]:
            raise ErrorCopia("No hay nada que copiar")

        tamanos = {}
        plan = []
        for indice, (src, _dst) in enumerate(planes[0]):
            try:
                tam = os.stat(src).st_size
            except OSError:
                tam = 0
            tamanos[src] = tam
            plan.append((src, [pares[indice][1] for pares in planes], tam))
        bytes_totales = sum(tamanos.values())

        # Reanudación por destino: los ficheros completos cuentan enteros y los
        # que quedaron a medias, solo hasta donde llegaron.
        for destino, pares in zip(self.destinos, planes):
            destino.total_bytes = bytes_totales
            destino.total_archivos = len(pares)
            destino.copiados = 0
            destino.archivos_ok = 0
            for src, dst in pares:
                tam_src = tamanos.get(src, 0)
                try:
                    tam_dst = os.path.getsize(dst)
                except OSError:
                    continue
                if tam_dst == tam_src:
                    destino.copiados += tam_src
                    destino.archivos_ok += 1
                elif 0 < tam_dst < tam_src:
                    destino.copiados += tam_dst
            if destino.estado in ("paused", "error") and os.path.isdir(destino.ruta):
                destino.estado = "running"
                destino.error = None
                destino.espera = ""

        self.total_archivos = len(plan)
        self.total_bytes = bytes_totales
        self.copiados = min(d.copiados for d in self.destinos)
        self.archivos_ok = min(d.archivos_ok for d in self.destinos)
        self._guardar(force=True)
        self._aviso(force=True)
        return plan, tamanos

    def _asegurar_carpeta(self, destino: DestinoCopia, ruta: str):
        """Crea la carpeta de `ruta` una sola vez por destino."""
        carpeta = os.path.dirname(ruta)
        if not carpeta or carpeta in destino._dirs_creados:
            return
        os.makedirs(carpeta, exist_ok=True)
        destino._dirs_creados.add(carpeta)

    def _completar_destino(self, destino: DestinoCopia, origen, ruta, tam_origen):
        """Da por bueno el fichero en un destino si llegó entero."""
        try:
            if os.path.getsize(ruta) != tam_origen:
                return
        except OSError:
            return
        try:
            shutil.copystat(origen, ruta)
        except OSError:
            pass  # metadatos es lo de menos
        destino.archivos_ok += 1

    def _copiar_a_varios(self, origen, pares, tam_origen):
        """Copia un fichero a varios destinos leyendo el origen una sola vez.

        Cada bloque se lee una vez y se escribe en todos los destinos abiertos.
        El núcleo solapa las escrituras a dispositivos distintos, así que la
        lectura no se multiplica y el tiempo tiende a la suma de los destinos.
        Si un destino falla (por ejemplo, un USB desconectado), se aparta y el
        resto sigue; la copia se reanuda luego desde su tamaño actual.

        Antes de cada bloque se comprueba que el fichero de destino sigue en el
        disco con los bytes que llevamos: si lo borraron o truncaron durante una
        pausa, el descriptor escribiría en un inodo huérfano y el progreso
        mentiría. Ese destino se aparta y se reintenta después.
        """
        abiertos = []
        self._bloqueando = True
        try:
            with open(origen, "rb", buffering=0) as fuente:
                offsets = {}
                for destino, ruta in pares:
                    self._asegurar_carpeta(destino, ruta)
                    offset = 0
                    try:
                        tam_destino = os.stat(ruta).st_size
                        if 0 < tam_destino < tam_origen:
                            offset = tam_destino
                    except OSError:
                        offset = 0
                    offsets[id(destino)] = offset

                # Punto de partida común para poder leer una sola vez. Lo que un
                # destino tuviera de más se reescribe, así que no se cuenta dos
                # veces: se descuenta de su progreso antes de volver a escribir.
                base = min(offsets.values()) if offsets else 0
                for destino, ruta in pares:
                    extra = offsets[id(destino)] - base
                    if extra > 0:
                        destino.copiados = max(0, destino.copiados - extra)
                    try:
                        salida = open(ruta, "r+b" if base else "wb", buffering=0)
                        salida.seek(base)
                    except OSError as exc:
                        self._fallo_destino(destino, exc)
                        continue
                    # [destino, fichero, base, escritos, ruta]
                    abiertos.append([destino, salida, base, base, ruta])

                if base:
                    fuente.seek(base)
                while abiertos and not self._cancelado.is_set():
                    if not self._corriendo.is_set():
                        if not self._esperar_permiso():
                            break
                    bloque = fuente.read(BLOQUE)
                    if not bloque:
                        break
                    for item in list(abiertos):
                        destino, salida, _base, escritos, ruta = item
                        if not _intacto(ruta, escritos):
                            self._destino_cambio(destino, ruta, escritos)
                            try:
                                salida.close()
                            except OSError:
                                pass
                            abiertos.remove(item)
                            continue
                        try:
                            _escribir_todo(salida, bloque)
                        except OSError as exc:
                            self._fallo_destino(destino, exc)
                            try:
                                salida.close()
                            except OSError:
                                pass
                            abiertos.remove(item)
                            continue
                        item[3] = escritos + len(bloque)
                        destino.copiados += len(bloque)
                    self._recalcular()
                    self._tramo = max((i[3] for i in abiertos), default=0)
                    self._velocidad(time.monotonic())
                    self._aviso()
                    self._guardar()
        finally:
            for destino, salida, _base, escritos, ruta in abiertos:
                try:
                    salida.close()
                except OSError:
                    pass
                if not _intacto(ruta, escritos):
                    self._destino_cambio(destino, ruta, escritos)
                else:
                    self._completar_destino(destino, origen, ruta, tam_origen)
            self._bloqueando = False
            self._tramo = 0

    def _copiar_fichero(self, origen, destino: DestinoCopia, ruta, tam_origen=None):
        """Copia un fichero a un solo destino reanudando por byte.

        La escritura es secuencial, así que el tamaño del destino es un punto de
        continuación válido: tras un cierre brusco se sigue desde ahí en lugar de
        rehacer el fichero entero.

        Los datos se mueven con `os.copy_file_range` (copia dentro del núcleo,
        sin pasar por Python) cuando el sistema de ficheros lo admite; si no, se
        cae a lectura/escritura por bloques, con el mismo resultado.
        """
        self._asegurar_carpeta(destino, ruta)

        desplazamiento = 0
        modo = "wb"
        try:
            if tam_origen is None:
                tam_origen = os.stat(origen).st_size
            tam_destino = os.stat(ruta).st_size
            if 0 < tam_destino < tam_origen:
                desplazamiento = tam_destino
                modo = "r+b"
        except OSError:
            desplazamiento, modo = 0, "wb"

        log.debug(
            "copia %s: %s -> %s desde %d de %d bytes",
            self.id,
            short(origen),
            short(ruta),
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
                ruta, modo, buffering=0
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
                    if not _intacto(ruta, escritos):
                        # Borrado o truncado mientras estaba en pausa: no se
                        # sigue escribiendo en un inodo que ya no está.
                        self._destino_cambio(destino, ruta, escritos)
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
                    destino.copiados += leidos
                    self._recalcular()
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
            _borrar_si_incompleto(origen, ruta)
            log.debug("copia %s: %s cancelado a %d bytes", self.id, short(ruta), escritos)
            return

        log.debug("copia %s: %s completo (%d bytes)", self.id, short(ruta), escritos)
        self._completar_destino(destino, origen, ruta, tam_origen)

    def estado_para_pausa(self) -> tuple[bool, int]:
        """¿Se puede pausar ahora mismo? Devuelve (bloqueando, bytes del tramo)."""
        return self._bloqueando, self._tramo


def _intacto(ruta: str, escritos: int) -> bool:
    """¿Sigue el destino en el disco con los bytes que llevamos escritos?

    Sirve para detectar lo que pasó en la prueba real: borrar (o truncar) el
    fichero de un destino mientras la copia está en pausa. El descriptor sigue
    escribiendo en el inodo borrado y el progreso mentiría.
    """
    try:
        return os.path.getsize(ruta) == escritos
    except OSError:
        return False


def _escribir_todo(fichero, datos):
    """Escribe el bloque entero, aunque el sistema acepte menos de una vez."""
    vista = memoryview(datos)
    while vista:
        escritos = fichero.write(vista)
        if not escritos:
            raise OSError("escritura vacía")
        vista = vista[escritos:]


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

    def crear(self, origenes, destinos) -> Operacion:
        """Crea una copia hacia una o varias carpetas de destino.

        Con varios destinos se lee el origen una sola vez y se escribe en todos
        a la vez (ver `Operacion._copiar_a_varios`).
        """
        origenes = [os.path.abspath(o) for o in origenes]
        if not origenes:
            raise ErrorCopia("No has indicado ningún origen")
        if isinstance(destinos, str):
            destinos = [destinos]
        unicos = []
        for destino in destinos:
            ruta = os.path.abspath(destino)
            if ruta not in unicos:
                unicos.append(ruta)
        destinos = unicos
        if not destinos:
            raise ErrorCopia("No has indicado ningún destino")
        for destino in destinos:
            for origen in origenes:
                if _es_hijo(destino, origen):
                    raise ErrorCopia(
                        f"El destino está dentro del origen ({short(destino)} ⊂ {short(origen)})"
                    )
        # Las comprobaciones de disco (y su coste si un dispositivo no responde)
        # se hacen en el hilo de la copia: la tarea aparece al instante y, si la
        # ruta falla, la fila se marca con el error.
        log.debug(
            "copia nueva: %d origen(es) -> %d destino(s)",
            len(origenes),
            len(destinos),
        )
        op_id = self.store.crear(origenes, destinos)
        op = Operacion(op_id, origenes, destinos, self.store)
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
                datos_destinos = self.store.destinos_de(fila["id"])
                rutas = [d["ruta"] for d in datos_destinos] or [fila["destino"]]
                op = Operacion(fila["id"], fila["origenes"], rutas, self.store)
                op.total_bytes = fila["total_bytes"]
                op.copiados = fila["copiados_bytes"]
                op.total_archivos = fila["total_archivos"]
                op.archivos_ok = fila["copiados_archivos"]
                op.estado = "paused"
                op.pausa_manual = bool(fila.get("pausa_manual"))
                op.creado = fila["creado"]
                for destino, datos in zip(op.destinos, datos_destinos):
                    destino.total_bytes = datos["total_bytes"]
                    destino.copiados = datos["copiados_bytes"]
                    destino.total_archivos = datos["total_archivos"]
                    destino.archivos_ok = datos["copiados_archivos"]
                    destino.error = datos["error"] or None
                    destino.estado = "paused"
                if not datos_destinos and op.destinos:
                    op.destinos[0].total_bytes = fila["total_bytes"]
                    op.destinos[0].copiados = fila["copiados_bytes"]
                    op.destinos[0].total_archivos = fila["total_archivos"]
                    op.destinos[0].archivos_ok = fila["copiados_archivos"]
                    op.destinos[0].estado = "paused"
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