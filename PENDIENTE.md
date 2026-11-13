# Copiex — punto de retorno

Estado del trabajo al **13 de noviembre de 2026**. Este fichero y `Notas.md` son todo lo
que necesita una sesión nueva: el asistente no conserva memoria entre chats, y este
resumen evita tener que releer el historial de la conversación anterior.

**Resumen en una línea:** Copiex funciona de extremo a extremo (bandeja, Nautilus,
portapapeles, historial, pausa, cancelación, continuación por byte y reanudación
automática). Queda un requerimiento del pliego —la alerta sonora con el botón «Eliminar»
(nº 9)— y dos mejoras menores. Los requerimientos 10 y 11 (`menu.yaml` + «Acerca de»)
están hechos (sección 3 decies). Los requerimientos de workers se retiraron del pliego el
13/11 y su código se eliminó (sección 3 quinquies).

---

## 1. Cómo retomar

Abre el proyecto en Freebuff y pega algo como:

> Lee `PENDIENTE.md` y `Notas.md`. Sigue con el pendiente 1 (alerta sonora + «Eliminar»)
> y no cambies nada que ya esté marcado como verificado aquí. Los workers están
> descartados: no los reintroduzcas.

La sesión nueva arrancará sabiendo el estado real sin repetir pruebas ya hechas.

## 2. Qué está hecho y verificado

| Área | Estado |
|---|---|
| Compatibilidad Ubuntu 24.04 (Nautilus 46 / API 4.0) y 26.04 (Nautilus 50 / API 4.1) | Hecho. Cargador `_cargar_nautilus()` prueba 4.1 y luego 4.0, reutilizando el módulo si ya está importado. Probado con typelibs reales de ambas versiones. |
| `python3-nautilus` instalado en este equipo | Hecho (4.1.0-1build1 + gir1.2-nautilus-4.1). |
| Extensión cargada de verdad por Nautilus 50 | Verificado con una marca temporal en el log de Nautilus: «Copiex: extensión cargada con la API 4.1». La marca se retiró; la copia instalada es idéntica a la fuente. |
| «Copiar con Copiex» + «Pegar con Copiex» de extremo a extremo | Verificado emitiendo `activate` sobre los ítems reales del menú: IPC → app → copia realizada → fila en el historial. |
| Avisos de error en la extensión | `Gtk.AlertDialog` usaba `text=`; en GTK 4 se pasa `message` + `detail` y se muestra con `show(None)`. Corregido. |
| Bucle infinito de copias duplicadas | **Corregido.** Ver sección 3. |
| Portapapeles de Nautilus (Ctrl+C → «Pegar con Copiex») | **Hecho el 12/11.** Se lee `x-special/gnome-copied-files`, `text/uri-list` y el formato antiguo; se escribe con esos mismos MIME. Verificado con el portapapeles real y de extremo a extremo. Detalles en 3 bis. |
| Workers / hilos | **Retirado del pliego el 13/11** a petición del usuario: ya no son un requerimiento. Se midió 1 GB con 1/2/4/8 hilos → 0,58 / 0,39 / 0,41 / 0,43 s, sin ganancia real, y en USB o discos mecánicos suelen empeorar el tiempo. Se retiró también el código (tramos, fichero de estado, config y diálogo). |
| Reanudación automática (requerimiento 8, errores 1 y 2) | **Hecho el 12/11.** La copia continúa sola cuando vuelven origen y destino, también tras cerrar la aplicación; las pausas manuales se respetan y las filas con error se pueden reintentar o cancelar. Detalles en 3 quater. |
| Arranque de Copiex al pulsar «Copiar con Copiex» | **Hecho el 12/11.** Si no estaba en marcha, se lanza solo en la bandeja (`--bandeja`), sin abrir ventana, en ~0,6 s. |
| Latencia al pegar | **Medida el 12/11.** Antes 1,57 s en frío y hasta ~4 s con los reintentos ciegos; ahora 0,03 s con la app abierta y 0,49 s en frío. Detalles en 3 ter. |
| Historial de la base de datos | 23 filas al 13/11 (16 `done`, 4 `error`, 3 `cancelled`), todas copias reales del usuario. Columnas: `id, origenes, destino, total_bytes, copiados_bytes, total_archivos, copiados_archivos, estado, error, creado, actualizado, pausa_manual`. |

Lo único **no** comprobado visualmente es el menú desplegado: la sesión es Wayland y no
hay `xdotool`/`ydotool`, así que no se puede sintetizar un clic derecho. En su lugar se
verificó el código que devuelve los ítems y su activación, que es lo que Nautilus ejecuta.

## 2 bis. Mapa del código (2 883 líneas al 13/11)

| Fichero | Líneas | Responsabilidad |
|---|---|---|
| `copiex/util.py` | 100 | Rutas (`runtime_dir`, `socket_path`, `data_dir`), URIs ↔ rutas, formatos de tamaño y tiempo, `APP_ID`/`APP_NAME`/`EXTENSION_NAME`. |
| `copiex/logs.py` | 203 | Registro único `copiex.log` en DEBUG con 7 días de retención: poda atómica por fecha y por tamaño (`podar`, `ManejadorSemanal`, `configurar_registro`). |
| `copiex/engine.py` | 653 | `Operacion` (hilo de copia, pausa, aviso, velocidad, persistencia) y `Motor` (crear, pausar, reanudar, cancelar, historial). Bloques de 1 MiB; `_copiar_fichero()` reanuda por byte; `_pares()` calcula origen→destino. |
| `copiex/store.py` | 163 | SQLite en `~/.local/share/copiex/historial.db`: alta, actualización, pendientes y migración de `pausa_manual`. |
| `copiex/vigilante.py` | 69 | Hilo cada 6 s que reanuda `paused`/`error` cuando origen y destino están disponibles; respeta `pausa_manual`. |
| `copiex/menu.py` | 164 | Textos de la interfaz: lector YAML mínimo de `menu.yaml`, con caché y textos por defecto; `texto("menu.nueva")`. |
| `copiex/app.py` | 300 | `Adw.Application`: une motor, ventana, bandeja e IPC; acciones `nueva`/`ocultar`/`acerca`/`salir`; argumento `--bandeja`. |
| `copiex/window.py` | 241 | Ventana del historial: fila por copia con barra, velocidad, estado, «Reintentar»/«Cancelar»; menú (ocultar/acerca/salir) y botón «Nueva copia». |
| `copiex/tray.py` | 319 | Icono de bandeja por StatusNotifierItem + D-Bus, sin dependencias; menú contextual. |
| `copiex/ipc.py` | 121 | Socket Unix `$XDG_RUNTIME_DIR/copiex-<uid>/copiex.sock`; JSON por línea (`ping`, `show`, `copy`). |
| `copiex/extencion_nautilus.py` | 540 | Extensión de Nautilus: menú contextual (etiquetas de `menu.yaml`), portapapeles, arranque en bandeja y envío por socket. |
| `menu.yaml` | 44 | Nombres de las opciones de menú y textos de las ventanas emergentes, incluida la descripción de «Acerca de». |
| `install.sh`, `uninstall.sh`, `copiex-lanzador`, `com.copiex.Manager.desktop.in` | — | Instalación y desinstalación completas (extensión, escritorio, datos), lanzador y entrada de escritorio. |

Puntos de entrada: `./copiex-lanzador` (ejecuta `PYTHONPATH=. python3 -m copiex`) y,
desde Nautilus, la extensión instalada en
`~/.local/share/nautilus-python/extensions/copiex.py`.

## 2 ter. Requerimientos del pliego, uno a uno

El pliego se renumeró el 13/11: al retirar los antiguos 9–11 (workers), «alerta sonora»,
«Acerca de» y `menu.yaml` pasaron a ser los requerimientos 9, 10 y 11.

| # | Requerimiento | Estado |
|---|---|---|
| 1 | Programado en Python | Hecho: Python 3 + PyGObject, sin dependencias externas. |
| 2 | Proceso en la esquina superior derecha | Hecho: `tray.py` con StatusNotifierItem. |
| 3 | Menú contextual en la bandeja | Hecho: mostrar/ocultar ventana y salir. |
| 4 | Elegir origen y destino con el gestor de GNOME | Hecho: vía Nautilus (copiar/pegar) y «Nueva copia» con diálogos GTK. |
| 5 | Detener y reanudar | Hecho y probado: progreso congelado y hash correcto al reanudar. |
| 6 | Copias visibles en la ventana principal | Hecho: historial con progreso, velocidad, estado y botones. |
| 7 | Tomar la copia de Nautilus | Hecho: «Copiar/Pegar con Copiex» y lectura del portapapeles real de Nautilus. |
| 8 | Estado en tiempo real y restauración automática | Hecho: SQLite + `vigilante.py` (sección 3 quater). |
| 9 | Alerta sonora y botón «Eliminar» al terminar | **Pendiente.** |
| 10 | «Acerca de» con descripción corta y versión, en `menu.yaml` | Hecho: `app.acerca` con `Adw.AboutDialog` (versión 1.0.0 y descripción del YAML); sección 3 decies. |
| 11 | `menu.yaml` con nombres de opciones y textos de ventanas | Hecho: menús de ventana, bandeja y Nautilus más diálogos leen `menu.yaml`; sección 3 decies. |
| E1 | No detecta copias de Nautilus estando activo | Corregido y verificado. |
| E2 | Error de E/S sin reanudar ni botón de cancelar | Corregido: vigilante + botones «Reintentar»/«Cancelar». |
| E3 | Varios ficheros se copian muy lentos | **Sin medir.** El bucle copia de uno en uno con bloques de 1 MiB; falta la prueba con muchos ficheros (pendiente 3). |
| E4 | «Copiar con Copiex» no arrancaba la app | Corregido: arranque en bandeja con `--bandeja` (~0,6 s). |

## 3. Fallo corregido que conviene no reintroducir

En `copiex/app.py`, la rama IPC hacía:

```python
GLib.idle_add(self.crear_copia, origenes, destino)
```

`GLib.idle_add` repite el callback mientras devuelva algo verdadero, y `crear_copia()`
devuelve la operación creada. Cada «Pegar con Copiex» lanzaba copias en bucle sin fin
(se llegaron a acumular cientos de filas y una tanda de errores `EIO` contra un USB).

Ahora se llama a `self._crear_copia_desde_ipc(...)`, que invoca `crear_copia()` y
devuelve `False`. **Regla:** cualquier callback pasado a `GLib.idle_add` debe devolver
`False`. `mostrar_ventana` y `_aplicar_cambio` ya lo cumplen.

## 3 bis. Portapapeles (resuelto el 12/11)

Lo que publica Nautilus al hacer Ctrl+C (MIME `x-special/gnome-copied-files`):

```
copy                 ← o «cut» si se cortó
file:///home/ana/a.txt
file:///home/ana/b.txt
```

- `_marcar_portapapeles()` publica ese MIME **y** `text/uri-list` y `text/plain`, así que
  tras «Copiar con Copiex» un Ctrl+V normal en Nautilus también funciona.
- `_leer_portapapeles()` pide los MIME en orden con `Gdk.Clipboard.read_async` y lee el
  flujo por trozos (`read_finish` + `read_bytes_async`). **No** volver a `read_text_async`:
  solo devuelve `text/plain`, que en Nautilus trae los nombres, no las rutas.
- `_uris_del_portapapeles()` acepta también el formato antiguo
  (`x-special/nautilus-clipboard`) y descarta texto plano que no sean URI, para no
  intentar copiar «uno.txt» como si fuese una ruta.
- Al pegar manda el portapapeles; la selección de «Copiar con Copiex» es solo el respaldo.
- En Wayland el portapapeles solo se puede leer desde un proceso con foco: por eso la
  lectura vive en la extensión (dentro de Nautilus) y no en la aplicación.
- **Cortar (`cut`) se trata como copiar**: el motor no mueve ficheros. Queda como mejora
  menor opcional.
- **Interceptar el Ctrl+V propio de Nautilus no es posible** con python3-nautilus: la API
  no expone ningún hook del pegado del gestor. La vía soportada es «Pegar con Copiex».

## 3 ter. Arranque y latencia (resuelto el 12/11)

Medido con `sqlite` como testigo (desde la activación del menú hasta que la fila existe):

| Situación | Antes | Ahora |
|---|---|---|
| Copiex ya abierto | 0,03 s | 0,03 s |
| Copiex cerrado | 1,57 s (y hasta ~4 s si el socket tarda) | 0,49 s |
| «Copiar con Copiex» con la app cerrada | no la arrancaba | 0,61 s, en bandeja |

Cambios:

- `_enviar()` sondea el socket cada 150 ms (hasta 12 s) en vez de dormir 1,5 s a ciegas
  entre tres intentos: el mensaje sale en cuanto la aplicación abre el socket.
- `_al_copiar()` manda un `ping` en segundo plano, que arranca Copiex si no está.
- `_arrancar_app()` lee el `Exec` del `.desktop` y añade `--bandeja`; la app consume ese
  argumento en `main()`, no abre ventana en el primer `activate` y queda solo en la bandeja.
- Al crear una copia, si la ventana no existe se abre (`crear_copia` → `do_activate`), así
  la tarea siempre se ve aunque la app estuviera solo en la bandeja.
- `Motor.crear()` ya **no** comprueba el disco: crear la fila es solo SQLite (0,4 ms).
  Las validaciones (`No existe: …`, `El destino no es una carpeta: …`) las hace el hilo de
  la copia y el fallo se muestra en la fila. Nunca metas `os.path.exists`/`isdir` de rutas
  de usuario en el hilo de GTK: un dispositivo que no responde congela la ventana.
- Los `ErrorCopia` esperados ya no imprimen traza completa; van al campo `error` de la fila.

Diagnóstico de extensiones obsoletas: al cargarse, la extensión imprime
`Copiex: extensión de Nautilus cargada (API 4.1)` (o 4.0). Si tras instalar no
aparece esa línea en el registro de Nautilus, el gestor sigue con la versión anterior en
memoria: hay que reiniciarlo (`nautilus -q`). Comprobación de fechas equivalente:
`ps -o lstart= -p $(pgrep -f nautilus)` frente a la fecha de
`~/.local/share/nautilus-python/extensions/copiex.py`.

## 3 quater. Reanudación automática (resuelto el 12/11)

`copiex/vigilante.py` (hilo propio, cada 6 s) revisa las copias en `paused` y `error` y las
reanuda cuando el destino existe y todos los orígenes se pueden leer. Mientras no sea así,
apunta el motivo con `Operacion.anotar_espera()` y la ventana lo muestra
(«En pausa · esperando la carpeta de destino ~/ISOs»).

Piezas clave:

- **Pausa manual vs. pausa por cierre.** `Operacion.pausar(manual=False)` es la que usa
  `Motor.apagar()`; la del usuario es `manual=True`. La marca se guarda en la columna
  `pausa_manual` del historial (migración automática con `ALTER TABLE`), así que una pausa
  manual sigue respetándose después de cerrar y reabrir la aplicación.
- **Errores.** Una copia en `error` se reintenta en cada pasada (6 s) mientras el origen y
  el destino estén disponibles; si el fallo era por un dispositivo ausente, espera sin
  intentar nada. Sin contadores ni espera exponencial: el intervalo es la espera y el
  vigilante no guarda estado propio (cada pasada mira lo que hay).
- **Ventana.** Las filas con error muestran «Reintentar» y «Cancelar» (antes no había
  ningún botón, que era el error 2 del pliego).
- **Cancelar es definitivo y deja el destino limpio.** El vigilante ignora las copias
  `cancelled`, `Motor.reanudar()` las rechaza y `cargar_historial()` no las recupera. Al
  cancelar se borran los destinos incompletos de esa copia (`_borrar_si_incompleto()`),
  así que una copia posterior del mismo fichero empieza de cero; los ficheros que ya
  estaban completos no se tocan. Pueden quedar carpetas vacías que creó la copia.
- El vigilante se detiene en `salir()` y llama a `motor.reanudar()` a través de
  `GLib.idle_add`: nunca toca GTK desde su hilo.
- **Continuación por byte, no solo por operación.** `_copiar_fichero()` abre el destino en
  `r+b` y salta a su tamaño actual cuando `0 < tamaño_destino < tamaño_origen`: tras un
  cierre brusco (`kill`, corte de luz) el fichero que estaba a medias sigue donde iba, no
  desde el principio. `_planificar()` cuenta esos bytes parciales en `copiados`, así que la
  barra arranca donde se quedó. Es válido porque la escritura es secuencial en bloques:
  el tamaño del destino es siempre un punto de continuación limpio. Casos límite: si el
  destino es mayor que el origen se rehace; se asume que un destino parcial pertenece a
  esa misma copia (no se comparan contenidos).

## 3 quinquies. Workers: retirados del pliego y del código (13/11)

Los antiguos requerimientos 9–11 ya **no están en `Notas.md`** (el pliego pasó entonces a
11 requerimientos). Se llegó a implementar la copia por tramos de 64 MiB con hasta 16
hilos, fichero `.copiex-parte` + `.copiex-estado` para reanudar por tramos, ajuste
persistente en `~/.config/copiex/config.json` y diálogo «Número de workers…». **Se retiró
entero** a petición del usuario tras medir un fichero de 1 GB:

| Hilos | Tiempo |
|---|---|
| 1 | 0,58 s |
| 2 | 0,39 s |
| 4 | 0,41 s |
| 8 | 0,43 s |

Conclusión: una sola secuencia ya satura el dispositivo; a partir de 2 hilos no hay
ganancia y en USB o discos mecánicos los hilos suelen empeorar el tiempo porque compiten
por el mismo cabezal y el mismo bus. El rendimiento real se atacaría con
`os.copy_file_range` (copia dentro del núcleo; reflink instantáneo en btrfs/XFS), no con
hilos. **No reintroducir los workers sin que el usuario lo pida.**

Estado del código tras la retirada: `_copiar_fichero()` único y secuencial, sin
constantes `TROZO_*`/`SUFIJO_*`, sin fichero de configuración, sin acción `workers` y sin
entrada de menú. Lo demás (pausa, cancelación, continuación por byte, vigilante) nunca
dependió de los workers y sigue igual.

## 3 sexies. Descartado: arrastrar y soltar (13/11)

Se evaluó que, con el centinela en marcha, arrastrar un fichero hasta la carpeta de
destino lo copiase Copiex. **No es posible con una extensión**: la API `Nautilus-4.1`
(Nautilus 50.2.2) solo expone `ColumnProvider`, `InfoProvider`, `MenuProvider` y
`PropertiesModelProvider`; `MenuProvider` únicamente tiene `get_file_items()` y
`get_background_items()`, y desde la API 4.0 no hay widgets ni `LocationWidgetProvider`.
No existe hook de arrastre, de soltado ni de operación de copia. Se descartó como
requerimiento el 13/11 y no se implementa: las únicas vías serían parchear Nautilus (C) o
una zona de arrastre propia en una ventana de Copiex.

## 3 septies. «Pegar con Copiex» no hacía nada (corregido el 13/11)

Síntoma: «Copiar con Copiex» arrancaba el centinela, pero al pulsar «Pegar con Copiex» en
la carpeta de destino no aparecía la ventana ni empezaba la copia. El log de la
aplicación no registraba ninguna petición: el mensaje no llegaba a salir de Nautilus.

Causa: la extensión dependía por completo de la lectura asíncrona del portapapeles
(`Gdk.Clipboard.read_async`). Si esa lectura no contesta (Wayland, contenido servido por
otro proceso), el callback no se ejecuta y no había respaldo: `_al_pegar()` terminaba sin
enviar nada y sin avisar. Además la respuesta de la aplicación se descartaba, así que un
rechazo (por ejemplo «El destino no es una carpeta») tampoco se veía.

Arreglos en `copiex/extencion_nautilus.py`:

- `_al_pegar()` usa un testigo (`estado["hecho"]`) y dos temporizadores: a los 1,5 s, si
  el portapapeles no ha contestado y hay algo marcado con «Copiar con Copiex», se usa eso;
  a los 6 s, si no hay nada, se muestra «No hay nada que pegar». Solo se envía una vez.
- `_enviar()` devuelve la respuesta y `_enviar_async()` la revisa: sin contacto o con
  `{"ok": false}` sale un `Gtk.AlertDialog` con el motivo, en vez de silencio.
- Traza propia en `~/.local/share/copiex/extension.log`: cada copiar/pegar, el MIME y el
  número de URIs leídas y la respuesta de la app. Los `print` de la extensión no llegan a
  ningún sitio, así que este es el fichero donde mirar si el menú falla.

Comprobado con un banco aislado (app propia en `/tmp`, id de aplicación distinto para no
fusionarse con la instancia real): pegado normal crea la copia y copia el fichero; con la
lectura del portapapeles anulada, el respaldo de 1,5 s la crea igualmente; un destino
inválido ahora produce aviso visible en vez de nada.

## 3 octies. Un copiex.log con una semana de historial (13/11)

`copiex/logs.py` instala el registro al arrancar (`configurar_registro()`, llamada desde
`app.main()`):

- **Un solo fichero**: `~/.local/share/copiex/copiex.log`, escrito en **DEBUG**; la consola
  se queda en INFO para no ensuciar el terminal.
- **Ventana de 7 días** (`DIAS_RETENCION`): al arrancar y, como mucho, una vez por hora
  (`ManejadorSemanal`) se descartan las entradas más antiguas. La poda (`podar()`) reescribe
  el fichero de forma atómica, conserva las líneas de continuación de una traza y deja una
  nota «poda: N entrada(s)…» cuando quita algo.
- **Tope de tamaño**: 32 MiB; si aun así se supera (una semana muy movida), se recortan las
  más antiguas hasta 24 MiB, así nunca llena el disco.
- **La extensión de Nautilus escribe en el mismo fichero**: `_traza()` envía cada línea por
  IPC (`{"cmd": "log"}`) y la app la registra como `Nautilus: …`. Si la app no está
  arrancada, queda en `extension.log` como respaldo.
- **Qué queda registrado**: arranque (versión, PID, modo, ruta del registro), IPC recibido,
  cada copia creada (orígenes y destino), el plan (archivos, bytes, ya presentes), fichero a
  fichero con desplazamiento y bytes, pausa/reanudación/cancelación con el byte exacto,
  resultado final, errores con traza completa, decisiones del vigilante y las acciones de
  Nautilus (copiar/pegar, MIME leído y respuesta de la app).
- **Sin ruido**: una copia esperando un dispositivo ausente anota el motivo **solo cuando
  cambia** (`anotar_espera()` devuelve si hubo cambio), no cada 6 segundos; así una espera
  larga no desplaza el resto del historial por tamaño.

Comprobado: poda por fecha (descarta entradas de 8 y 10 días, conserva las de 3 días y de
ahora, incluidas sus continuaciones), poda por tamaño (respeta el tope), arranque real con
un bus D-Bus privado (línea «Copiex 1.0.0 arranca (pid …, bandeja)»), y una sesión con una
copia de 2 GB pausada, reanudada, cancelada a 406 MB y un origen inexistente: el fichero
cuenta la historia completa. Tras el cambio hay que **reiniciar la app** para que use este
registro (hecho: instancia reiniciada en bandeja).

## 3 nonies. Instalación y desinstalación completas (13/11)

**`install.sh`** (revisado): comprueba que se ejecuta junto al proyecto, avisa si faltan
`python3-gi`, `gir1.2-gtk-4.0` o `gir1.2-adw-1` (con el `apt install` exacto), copia la
extensión y verifica con `cmp` que la copia es idéntica, refresca la base de datos de
escritorio y avisa si Copiex está en marcha (seguiría con el código anterior en memoria).
Termina recordando `nautilus -q` y `./uninstall.sh`.

**`uninstall.sh`** (nuevo): deja el sistema como si Copiex nunca se hubiera instalado.

- Cierra la aplicación en marcha buscando `python3 -m copiex` **por campos exactos** (nunca
  `pkill -f`, que mataría al propio script) y espera hasta 3 s antes de forzar.
- Borra la extensión de Nautilus (`extensions/copiex.py` y sus `copiex.*.pyc`, incluidas
  las variantes de varias versiones de Python), la entrada de escritorio, un posible
  autostart, el socket y **los datos** (`~/.local/share/copiex`: historial y registros) y
  `~/.config/copiex`.
- Refresca `update-desktop-database` y reinicia Nautilus (`nautilus -q`), que es lo que
  hace desaparecer «Copiar con Copiex» y «Pegar con Copiex» del menú contextual.
- Verifica al final que no quedan restos y sale con código 1 si algo no se pudo borrar.
- Opciones: `--si` (sin preguntar), `--conservar-datos` (deja historial y logs),
  `--simular` (enseña lo que borraría sin tocar nada) y `--ayuda`.
- No toca `python3-nautilus`, que es un paquete de sistema que pueden usar otras
  extensiones; sugiere `sudo apt remove python3-nautilus` al terminar.

Comprobado en un HOME falso: borra solo lo de Copiex (deja otra extensión y su `.pyc`,
`otra.desktop`), respeta `--conservar-datos`, `--simular` no borra nada, cancelar con «n»
no toca nada, confirmar con «s» desinstala, y una segunda pasada no falla. `--simular`
sobre el HOME real lista exactamente lo que quitaría y no modifica nada.

## 3 decies. `menu.yaml` y «Acerca de» (requerimientos 10 y 11, 13/11)

`menu.yaml` (raíz del proyecto, 44 líneas) reúne los nombres de las opciones de menú y los
textos de las ventanas emergentes, incluida la descripción de «Acerca de». Secciones:
`aplicacion` (nombre y descripción), `menu` (nueva, ocultar, mostrar, acerca, salir),
`ventana` (subtítulo del historial y estado vacío), `acciones` (pausar, reanudar,
reintentar, cancelar), `dialogos` (títulos de los diálogos de origen y destino) y
`nautilus` (copiar, pegar y sus consejos).

**`copiex/menu.py`** (nuevo, 164 líneas) lo lee sin dependencias: YAML mínimo de mapas
anidados por sangría, un valor por línea, comillas opcionales y comentarios `#`. `texto()`
cachea el resultado y, si falta el fichero, no se puede leer o la clave no existe, devuelve
el valor por defecto del propio módulo (los mismos textos están duplicados ahí como red de
seguridad). `COPIEX_MENU` permite apuntar a otro fichero (lo usan las pruebas). Se busca en
la raíz del proyecto y, como respaldo, dentro del paquete. **Un cambio en `menu.yaml`
necesita reiniciar la aplicación** (la caché dura toda la sesión).

**«Acerca de»**: acción `app.acerca`, entrada en el menú de tres rayas de la ventana entre
«Ocultar ventana» y «Salir». Usa `Adw.AboutDialog` con el nombre, el icono, la versión y la
descripción de `aplicacion.descripcion`. La versión sale de `copiex/__init__.py`
(`__version__` = «1.0.0»), no del YAML, para que haya una sola fuente.

**Extensión de Nautilus**: se instala como fichero suelto y no puede importar el paquete,
así que repite un lector mínimo para la sección `nautilus:`. Encuentra `menu.yaml` a partir
de la ruta del lanzador del `.desktop` (mismo directorio) y, si no está, usa las etiquetas
de siempre (`_TEXTO_DEFECTO`). Estrena los cambios con `./install.sh` + `nautilus -q`.

Comprobado: compilación de todo el paquete; textos del fichero real; con un `menu.yaml`
temporal (`COPIEX_MENU`) cambian las etiquetas de la ventana («Copiar ahora», «Sobre
Copiex», subtítulo «Copias de prueba») y las claves ausentes caen en su valor por defecto;
`app.acerca()` construye y presenta el diálogo sin errores; la extensión devuelve las
cuatro cadenas de `menu.yaml`; `./install.sh` copia la extensión idéntica. La ventana de
«Acerca de» y el menú de Nautilus no se han visto con los ojos (Wayland), pero se
construyen sin error: falta el clic real del usuario.

## 4. Pendientes, por orden sugerido

1. **Alerta sonora + botón «Eliminar»** (requerimiento 9). Al pasar a `done`, emitir un
   sonido una sola vez por copia (GSound, `canberra-gtk-play` o similar) y poner
   «Eliminar» en lugar de «Cancelar», quitando la fila de la pantalla sin borrar el
   historial. Ojo: `window.py` decide los botones por fila según el estado y hoy
   «Cancelar» y «Reintentar» comparten la lógica de `accionable`.
2. **Medir el caso de muchos ficheros** (error 3 del pliego): copiar una carpeta con
   cientos de ficheros y anotar tiempo y tamaño de bloque. Si sale mal, subir `BLOQUE`
   (hoy 1 MiB) o pasar a `copy_file_range`.
3. *(menor)* Tratar el pegado de un «cortar» (`cut`) como mover, no como copiar.

## 5. Trampas del entorno (ahorran media hora cada una)

- **Si algo va mal:** `~/.local/share/copiex/copiex.log` tiene todo en DEBUG con una
  semana de historial, incluidas las acciones de Nautilus (`Nautilus: …`). Si la app no
  estaba arrancada, la traza de la extensión queda en `extension.log`. Los `print` de la
  extensión se pierden.
- **Nombres:** el «centinela» de la esquina superior derecha es el icono de bandeja
  (`copiex/tray.py`, clase `Bandeja`). No confundirlo con el **vigilante**
  (`copiex/vigilante.py`), que es el hilo que reanuda copias automáticamente.
- **Arrancar la app:** `./copiex-lanzador` o `PYTHONPATH=. python3 -m copiex`.
  Para lanzarla desde un terminal sin que el tool espere 60 s:
  `( setsid nohup ./copiex-lanzador >/tmp/copiex-app.log 2>&1 </dev/null & ) >/dev/null 2>&1`
- **Nunca** uses `pkill -f "python3 -m copiex"`: la propia línea de comandos del shell
  contiene ese texto y el comando se mata a sí mismo (pasó en noviembre). Localiza el PID
  con `ps -eo pid,cmd | grep "[p]ython3 -m copiex"` y mátalo por PID.
- **Rutas:** socket `$XDG_RUNTIME_DIR/copiex-1000/copiex.sock`
  (`/run/user/1000/...`); base de datos
  `~/.local/share/copiex/historial.db`, tabla `copias`.
- **Desinstalar:** `./uninstall.sh` (pregunta; `--simular` para ver antes lo que
  borraría, `--conservar-datos` para quedarse con historial y registros).
- **Instalar cambios de la extensión:** `./install.sh` copia
  `copiex/extencion_nautilus.py` a `~/.local/share/nautilus-python/extensions/copiex.py`.
  Después hay que reiniciar Nautilus (`nautilus -q`) o no se recarga.
- **Protocolo IPC:** `{"cmd":"copy","sources":[uri,...],"dest":uri}`, además de `ping` y `show`.
- **Probar sin clic derecho:** importar `copiex.extencion_nautilus`, instanciar
  `ExtencionCopiex()` y emitir `activate` sobre los ítems de `get_file_items()` /
  `get_background_items()`. Es exactamente lo que hace Nautilus.
- **Sesión Wayland** con GNOME 50: no hay `xdotool`, `wmctrl` ni `ydotool`; solo `grim`
  para capturas. Para comprobar el menú hace falta un clic derecho humano.

## 6. Estado del sistema donde se probó

Ubuntu 26.04 «resolute», GNOME 50.1, Nautilus 50.2.2, GTK 4.22.4, PyGObject 3.56.2,
Wayland. El proyecto **no es un repositorio git**: no hay historial de cambios ni
posibilidad de revertir, así que conviene copiar los ficheros antes de cambios grandes
(o plantearse `git init`).

## 7. Recetas de verificación (las que ya se usaron)

Todas las pruebas se hacen con base de datos y `XDG_CONFIG_HOME` temporales en `/tmp`
para no tocar el historial real:

```python
import sys; sys.path.insert(0, "/home/denis/programacion/proyectos/copiex")
from copiex.store import Store
from copiex.engine import Motor
s = Store("/tmp/prueba/h.db"); m = Motor(s)
op = m.crear(["/tmp/prueba/origen.bin"], "/tmp/prueba/destino")
```

- **Copia correcta:** esperar a `done` y comparar `hashlib.sha256` de origen y destino.
- **Pausa:** `m.pausar(op.id)`; `op.copiados` debe quedarse quieto ~0,4 s; luego
  `m.reanudar(op.id)` y comprobar el hash.
- **Cancelar:** `m.cancelar(op.id)`; el destino no debe existir y la carpeta debe quedar
  vacía (los ficheros que ya estaban completos no se tocan).
- **Continuación por byte:** copia en un proceso aparte, `kill -9` a mitad, anotar
  `stat -c%s` del destino, reabrir con `m.cargar_historial()` + `m.reanudar()`, muestrear
  `op.copiados` (nunca por debajo del parcial) y comprobar el hash final. En `/tmp`
  (memoria) un fichero de 400 MB se copia antes de que dé tiempo a matarlo: usar 2 GB.
- **UI sin clic derecho:** `Aplicacion(application_id="…", db_ruta=<temporal>,
  activar_ipc=False, activar_bandeja=False)`, conectar `activate` y comprobar dentro de
  `app.run([])`. Sin `run()` no se ejecuta `do_startup` y `app.motor` es `None`, así que
  llamar a métodos como `guardar_*` desde fuera falla con `AttributeError`.
- **Regla de oro:** cualquier callback pasado a `GLib.idle_add` debe devolver `False`
  (ver sección 3).
