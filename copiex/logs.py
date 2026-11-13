# -*- coding: utf-8 -*-
"""Registro persistente de Copiex: un único `copiex.log` con una semana.

Objetivo: si algo va mal, el usuario puede enviar el fichero entero y con él se
reconstruye qué pasó. Por eso:

* el fichero se escribe en nivel DEBUG (todo lo que hace el motor, el IPC, el
  vigilante y lo que cuenta la extensión de Nautilus);
* se conservan las entradas de los últimos `DIAS_RETENCION` días;
* si aun así crece demasiado, se descartan las más antiguas, así nunca llena el
  disco.

La poda se hace al arrancar y, como mucho, una vez por hora mientras la
aplicación está en marcha: no hay que reiniciar para que se cumpla la semana.
"""

from __future__ import annotations

import logging
import os
import time

from .util import data_dir

DIAS_RETENCION = 7
TAMANO_MAXIMO = 32 * 1024 * 1024  # 32 MiB: una semana muy movida cabe de sobra
TAMANO_CONSERVADO = 24 * 1024 * 1024  # a lo que se recorta si se pasa
INTERVALO_PODA = 3600.0  # segundos entre podas con la aplicación abierta

FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"
ANCHO_FECHA = 19  # "2026-11-13 11:47:58"


def _es_inicio(linea: str) -> bool:
    """¿La línea abre una entrada (empieza por fecha y hora)?"""
    return (
        len(linea) > ANCHO_FECHA
        and linea[4] == "-"
        and linea[7] == "-"
        and linea[10] == " "
        and linea[13] == ":"
        and linea[16] == ":"
    )


def _cuando(linea: str):
    """Segundos desde la época de la fecha que abre la línea, o None."""
    try:
        return time.mktime(time.strptime(linea[:ANCHO_FECHA], "%Y-%m-%d %H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _entradas(lineas):
    """Agrupa las líneas en entradas; las continuaciones van con la suya."""
    actual = []
    for linea in lineas:
        if _es_inicio(linea) and actual:
            yield actual
            actual = []
        actual.append(linea)
    if actual:
        yield actual


def podar(
    ruta: str,
    dias: int = DIAS_RETENCION,
    maximo: int = TAMANO_MAXIMO,
    conservado: int = TAMANO_CONSERVADO,
):
    """Descarta lo más antiguo que `dias` y recorta si no cabe.

    Devuelve (entradas descartadas, entradas conservadas). Reescribe el fichero
    de forma atómica: nunca se queda a medias.
    """
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fichero:
            lineas = fichero.readlines()
    except OSError:
        return (0, 0)
    if not lineas:
        return (0, 0)

    limite = time.time() - dias * 86400
    entradas = list(_entradas(lineas))
    conservar = []
    for entrada in entradas:
        cuando = _cuando(entrada[0])
        if cuando is None or cuando >= limite:
            conservar.append(entrada)
    descartadas = len(entradas) - len(conservar)

    def tamano(entrada) -> int:
        return len("".join(entrada).encode("utf-8"))

    total = sum(tamano(e) for e in conservar)
    recortadas = 0
    if total > maximo:
        while conservar and total > conservado:
            total -= tamano(conservar[0])
            del conservar[0]
            recortadas += 1

    nota = ""
    if descartadas or recortadas:
        motivos = []
        if descartadas:
            motivos.append(f"{descartadas} entrada(s) de más de {dias} días")
        if recortadas:
            motivos.append(f"{recortadas} entrada(s) descartadas por tamaño")
        nota = (
            time.strftime("%Y-%m-%d %H:%M:%S")
            + " INFO copiex.logs: poda: "
            + "; ".join(motivos)
            + "\n"
        )

    temporal = ruta + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as fichero:
            fichero.write(nota)
            for entrada in conservar:
                fichero.writelines(entrada)
        os.replace(temporal, ruta)
    except OSError:
        try:
            os.unlink(temporal)
        except OSError:
            pass
    return (descartadas, len(conservar))


class ManejadorSemanal(logging.FileHandler):
    """Escribe en `copiex.log` y lo poda sin necesidad de reiniciar."""

    def __init__(
        self,
        ruta: str,
        dias: int = DIAS_RETENCION,
        maximo: int = TAMANO_MAXIMO,
        conservado: int = TAMANO_CONSERVADO,
        intervalo: float = INTERVALO_PODA,
        nivel=logging.DEBUG,
    ):
        super().__init__(ruta, mode="a", encoding="utf-8", delay=True)
        self.dias = dias
        self.maximo = maximo
        self.conservado = conservado
        self.intervalo = intervalo
        self._ultima_poda = 0.0
        self.setLevel(nivel)
        self.setFormatter(logging.Formatter(FORMATO))
        self.podar_ahora()

    def podar_ahora(self) -> None:
        """Cierra el fichero, lo poda y deja que el siguiente aviso lo reabra."""
        self.acquire()
        try:
            if self.stream is not None:
                try:
                    self.stream.flush()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            podar(self.baseFilename, self.dias, self.maximo, self.conservado)
        finally:
            self._ultima_poda = time.monotonic()
            self.release()

    def emit(self, registro):  # noqa: D102 - heredado
        if (time.monotonic() - self._ultima_poda) > self.intervalo:
            self.podar_ahora()
        super().emit(registro)


def configurar_registro(ruta: str | None = None, nivel: int = logging.DEBUG) -> str:
    """Instala el registro de Copiex y devuelve la ruta del fichero.

    El fichero va en DEBUG (todo); la consola, en INFO, para no ensuciar el
    terminal. Se quitan los manejadores que hubiera: se llama una sola vez, al
    arrancar.
    """
    if ruta is None:
        ruta = os.path.join(data_dir(), "copiex.log")
    raiz = logging.getLogger()
    for manejador in list(raiz.handlers):
        raiz.removeHandler(manejador)
        try:
            manejador.close()
        except Exception:
            pass
    raiz.setLevel(nivel)

    fichero = ManejadorSemanal(ruta, nivel=nivel)
    raiz.addHandler(fichero)

    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(logging.Formatter(FORMATO))
    raiz.addHandler(consola)
    return ruta
