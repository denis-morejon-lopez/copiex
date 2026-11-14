# Copiex — punto de retorno

Estado del trabajo al **14 de noviembre de 2026**, con los dos últimos arreglos ya
instalados y probados en banco: el destino que pierde su fichero durante una pausa y el
arranque de Copiex desde Nautilus (envío sin hilos y activación por D-Bus). Este fichero y
`NOTES.md` son todo lo que necesita una sesión nueva: el asistente no conserva memoria
entre chats, y este resumen evita tener que releer el historial de la conversación
anterior.

**Resumen en una línea:** Copiex está terminado: los 11 requerimientos del pliego y los 4
errores están resueltos (bandeja, extensión de Nautilus, historial SQLite con reanudación
automática, `menu.yaml` con todos los textos, «Acerca de», alerta sonora propia con botón
«Eliminar», icono propio y copia optimizada con `copy_file_range`), y además una copia
puede repartirse a varios destinos leyendo el origen una sola vez. El 14/11 se corrigieron
además los dos fallos de la prueba real: un destino cuyo fichero se borra durante la pausa
no infla el progreso y se reintenta solo; y la extensión ya no envía desde un hilo ni
lanza Copiex con `fork` desde Nautilus (lo arranca el bus de sesión), así que la petición
sale en milisegundos. Solo queda una mejora menor: tratar un «cortar» de Nautilus como
mover. Los requerimientos de workers se retiraron del pliego el 13/11 y su código se
eliminó (sección 3 quinquies).

---

## 1. Cómo retomar

Abre el proyecto en Freebuff y pega algo como:

> Lee `TODO.md` y `NOTES.md`. Los 11 requerimientos y los 4 errores del pliego ya están
> cerrados: no rehagas lo ya verificado y, si hay algo nuevo, sigue las reglas de
> `AGENTS.md` (textos en `menu.yaml`, nombres de fichero en inglés, sin workers, sin
> `pkill -f`). Antes de tocar el motor o la extensión, lee 3 ter y 3 quindecies: el 14/11
> se corrigieron el destino borrado durante la pausa y el arranque sin hilos por D-Bus.
> Lo único pendiente es la prueba real del menú de Nautilus y la sección 4. No hagas
> commit ni push sin pedírmelo.

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
| Arranque de Copiex al pulsar «Copiar con Copiex» | **Hecho el 12/11 y reforzado el 14/11.** Si no estaba en marcha, se arranca solo en la bandeja, sin abrir ventana. Desde el 14/11 lo pide al bus de sesión (servicio `com.copiex.Manager` que instala `install.sh`): **0,404 s** en frío. |
| Latencia al pegar | **Medida el 12/11; re-medida el 14/11.** Antes 1,57 s en frío y hasta ~4 s con los reintentos ciegos; ahora **0,003 s** con la app abierta y **0,404 s** en frío por D-Bus. Detalles en 3 ter. |
| Historial de la base de datos | 35 filas al 14/11 (27 `done`, 4 `error`, 4 `cancelled`) y 9 filas en `destinos`, todas copias reales del usuario. Columnas de `copias`: `id, origenes, destino, total_bytes, copiados_bytes, total_archivos, copiados_archivos, estado, error, creado, actualizado, pausa_manual`. Tabla `destinos` (desde el 13/11): una fila por carpeta destino con su progreso y estado; en `copias.destino` se guarda el primero. |
| «Acerca de» + `menu.yaml` (requerimientos 10 y 11) | **Hecho el 13/11.** Acción `app.acerca` con `Adw.AboutDialog` (versión de `copiex/__init__.py` y descripción de `menu.yaml`); menús de ventana, bandeja y Nautilus, y los diálogos de origen/destino, leen sus textos de `menu.yaml` mediante `copiex/menu.py` (lector YAML propio, con caché y valores por defecto). Detalles en 3 decies. |
| Alerta sonora y «Eliminar» (requerimiento 9) | **Hecho el 13/11.** `copiex/sound.py` reproduce el audio de `sounds/` (manda `copy-finished.*`) una sola vez por copia terminada; «Cancelar» deja paso a «Eliminar», que quita la fila sin borrar el historial. El usuario confirmó que la alarma suena. Detalles en 3 undecies. |
| Nombres de ficheros y carpetas en inglés | **Hecho el 13/11.** `sound.py`, `watcher.py`, `nautilus_extension.py`, `copiex-launcher`, `sounds/`, `TODO.md`, `NOTES.md`. Los identificadores internos (clases, funciones, atributos) siguen en español a propósito. |
| Error 3: copias de muchos ficheros | **Medido y mejorado el 13/11.** −20 % de tiempo y −22 % de CPU en 2 000 ficheros de 4 KiB, −14 % en un fichero de 256 MiB: `os.copy_file_range`, un `stat` por fichero al planificar y carpetas memorizadas. Detalles en 3 duodecies. |
| Bandeja sin ventana abierta | **Corregido el 13/11.** El icono ofrecía «Ocultar ventana» aunque la ventana no existiera; ahora dice «Mostrar ventana» y se refresca al abrir/ocultar. Detalles en 3 terdecies. |
| Icono propio y cabecera | **Hecho el 13/11.** «C» turquesa con barra de progreso (`icons/`), instalado en el tema `hicolor`; la bandeja usa la variante simbólica y la cabecera lo muestra a 22 px tras «Copiex». Detalles en 3 quaterdecies. |
| Copia a varios destinos | **Hecho el 13/11.** Una operación, varias carpetas destino y **una sola lectura** del origen: cada bloque se escribe en todos los destinos a la vez. Cada destino tiene su cola visible en la ventana, su progreso en la BD, y se reanuda solo si su carpeta desaparece. En Nautilus: «Pegar con Copiex N destinos». Detalles en 3 quindecies. |
| Destino borrado o truncado durante la pausa | **Corregido el 14/11.** Antes se seguía escribiendo en el inodo ya borrado: el progreso mentía y la operación quedaba en `running`. Ahora se comprueba el fichero antes de cada bloque, el progreso baja a lo que queda en disco (0 si se borró) y el destino se reintenta al terminar el resto; los botones pasan a «Eliminar» solo con todo completo. Detalles y pruebas en 3 quindecies. |
| Arranque desde Nautilus sin hilos | **Hecho el 14/11.** La extensión ya no envía desde un `threading.Thread` (se quedaba esperando el GIL) ni lanza Copiex con `subprocess.Popen` (fork desde Nautilus): `_Envio` usa callbacks de `GLib.io_add_watch` y el arranque lo hace el bus de sesión. Medido: 0,404 s en frío y 0,003 s con la app abierta. Detalles en 3 ter. |

Lo único **no** comprobado visualmente es lo que exige un clic o mirar el panel: el menú
desplegado de Nautilus (Wayland sin `xdotool`/`ydotool`) y el aspecto del icono en el
panel, el dock, la cabecera y «Acerca de». En su lugar se verificó el código que devuelve
los ítems del menú y su activación, los nombres de icono que resuelve el tema y los que la
bandeja publica por D-Bus. Tampoco se ha visto con un clic real el ítem «Pegar con Copiex
N destinos» ni su ventana de selección: se comprobó que el menú devuelve la entrada con
sus textos y que la ventana se construye y se cierra. Tampoco se ha repetido la prueba
real de arranque con la app cerrada desde el menú; sí en banco, por D-Bus (0,404 s).

## 2 bis. Mapa del código (4 416 líneas al 14/11, con scripts y plantillas)

| Fichero | Líneas | Responsabilidad |
|---|---|---|
| `copiex/util.py` | 126 | Rutas (`runtime_dir`, `socket_path`, `data_dir`), URIs ↔ rutas, formatos de tamaño y tiempo, `APP_ID`/`APP_NAME`/`EXTENSION_NAME`. |
| `copiex/logs.py` | 203 | Registro único `copiex.log` en DEBUG con 7 días de retención: poda atómica por fecha y por tamaño (`podar`, `ManejadorSemanal`, `configurar_registro`). |
| `copiex/engine.py` | 1100 | `Operacion` (hilo de copia, pausa, aviso, velocidad, persistencia), `DestinoCopia` (estado por destino) y `Motor` (crear, pausar, reanudar, cancelar, historial). Bloques de 1 MiB; un solo destino con `os.copy_file_range` (reserva a lectura/escritura) y varios con `_copiar_a_varios()` (una lectura, escritura a todos); un `stat` por fichero y carpetas memorizadas; `_copiar_fichero()` reanuda por byte; `_pares()` calcula origen→destino. `_intacto()`/`_destino_cambio()` detectan un destino borrado o truncado; `_ejecutar_plan()` y hasta 3 pasadas en `_trabajar_seguro()` reintentan esos destinos; el `finally` de `_trabajar` no deja ninguno en `running`. |
| `copiex/store.py` | 232 | SQLite en `~/.local/share/copiex/historial.db`: alta, actualización, pendientes, migración de `pausa_manual` y tabla `destinos` (`crear` acepta lista, `actualizar_destino`, `destinos_de`). |
| `copiex/watcher.py` | 75 | Hilo cada 6 s que reanuda `paused`/`error` cuando origen y **todas** las carpetas destino están disponibles; respeta `pausa_manual`. |
| `copiex/menu.py` | 176 | Textos de la interfaz: lector YAML mínimo de `menu.yaml`, con caché y textos por defecto; `texto("menu.nueva")`. |
| `copiex/sound.py` | 105 | Alerta de fin de copia: reproduce el audio de `sounds/` (o el del sistema) con `canberra-gtk-play`, `paplay` o `gst-launch-1.0`, en segundo plano. |
| `sounds/` | — | `copy-finished.wav` (alarma por defecto, sustituible) y `README.md` con las reglas de elección del fichero. |
| `copiex/app.py` | 331 | `Adw.Application`: une motor, ventana, bandeja e IPC; acciones `nueva`/`ocultar`/`acerca`/`salir`; sonido una vez por copia terminada; argumento `--bandeja`; IPC con `dest` o `dests`. |
| `copiex/window.py` | 314 | Ventana del historial: fila por copia con barra, velocidad, estado, «Reintentar»/«Cancelar»/«Eliminar» y, si hay varios destinos, una línea de cola por destino; menú (ocultar/acerca/salir) y botón «Nueva copia». |
| `copiex/tray.py` | 331 | Icono de bandeja por StatusNotifierItem + D-Bus, sin dependencias; menú contextual. |
| `copiex/ipc.py` | 126 | Socket Unix `$XDG_RUNTIME_DIR/copiex-<uid>/copiex.sock`; JSON por línea (`ping`, `show`, `copy`); cada conexión se atiende en un hilo propio (`listen(32)`) para que una colgada no retrase la siguiente. |
| `copiex/nautilus_extension.py` | 913 | Extensión de Nautilus: menú contextual (etiquetas de `menu.yaml`), portapapeles, envío por socket y ciclo «Pegar con Copiex N destinos» (`_SelectorDestinos`). `_Envio` hace connect/send/recv no bloqueantes con `GLib.io_add_watch` (sin hilos); `_arrancar_app()` usa el servicio D-Bus y deja `_arrancar_app_directo()` como respaldo. |
| `icons/` | — | Icono propio: `com.copiex.Manager.svg` (color) y `com.copiex.Manager-symbolic.svg` (una tinta, para la bandeja). |
| `brand/` | — | Propuestas de logo descartadas y `preview.html`, la galería con la que se eligió el icono. |
| `menu.yaml` | 50 | Nombres de las opciones de menú y textos de las ventanas emergentes, incluida la descripción de «Acerca de» y los de la selección de varios destinos. |
| `install.sh`, `uninstall.sh`, `copiex-launcher`, `com.copiex.Manager.desktop.in`, `com.copiex.Manager.service.in` | — | Instalación y desinstalación completas (extensión, escritorio, servicio D-Bus, iconos, datos), lanzador, entrada de escritorio y plantilla del servicio `com.copiex.Manager` que usa la extensión para arrancar la app sin `fork`. |

Puntos de entrada: `./copiex-launcher` (ejecuta `PYTHONPATH=. python3 -m copiex`) y,
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
| 8 | Estado en tiempo real y restauración automática | Hecho: SQLite + `watcher.py` (sección 3 quater). |
| 9 | Alerta sonora y botón «Eliminar» al terminar | Hecho: `copiex/sound.py` una vez por copia y «Eliminar» en lugar de «Cancelar» (sección 3 undecies). |
| 10 | «Acerca de» con descripción corta y versión, en `menu.yaml` | Hecho: `app.acerca` con `Adw.AboutDialog` (versión 1.0.0 y descripción del YAML); sección 3 decies. |
| 11 | `menu.yaml` con nombres de opciones y textos de ventanas | Hecho: menús de ventana, bandeja y Nautilus más diálogos leen `menu.yaml`; sección 3 decies. |
| E1 | No detecta copias de Nautilus estando activo | Corregido y verificado. |
| E2 | Error de E/S sin reanudar ni botón de cancelar | Corregido: vigilante + botones «Reintentar»/«Cancelar». |
| E3 | Varios ficheros se copian muy lentos | Medido y mejorado: −20 % de tiempo y −22 % de CPU en 2 000 ficheros pequeños, −14 % en un fichero de 256 MiB (`copy_file_range`, un `stat` por fichero, carpetas memorizadas); sección 3 duodecies. |
| E4 | «Copiar con Copiex» no arrancaba la app | Corregido: arranque en bandeja; desde el 14/11 lo activa el bus de sesión por D-Bus (~0,4 s). |

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

## 3 ter. Arranque y latencia (resuelto el 12/11 y revisado el 14/11)

Medido con `sqlite` como testigo (desde la activación del menú hasta que la fila existe):

| Situación | Antes | Ahora |
|---|---|---|
| Copiex ya abierto | 0,03 s | 0,003 s |
| Copiex cerrado | 1,57 s (y hasta ~4 s si el socket tarda) | 0,404 s (14/11, por D-Bus) |
| «Copiar con Copiex» con la app cerrada | no la arrancaba | 0,404 s, en bandeja |

Cambios:

- `_Envio` (14/11) hace connect/send/recv no bloqueantes con `GLib.io_add_watch` en el
  bucle principal de Nautilus, con 20 s de límite, reintento de conexión cada 200 ms y
  trazas por etapa. Sustituye al hilo `copiex-ipc`, que podía quedarse esperando el GIL y
  no llegaba ni a conectar. Una petición ya enviada no se reenvía (duplicaría la copia).
- `_arrancar_app()` pide al bus de sesión `StartServiceByName` de `com.copiex.Manager`;
  `install.sh` instala `~/.local/share/dbus-1/services/com.copiex.Manager.service`
  (`Exec=… --gapplication-service`). Así el fork lo hace el bus y no Nautilus. Si el bus
  no pudiera, `_arrancar_app_directo()` lee el `Exec` del `.desktop`, añade `--bandeja` y
  lanza desde el bucle principal (respaldo, no el camino normal).
- `_enviar()` sigue existiendo solo para pruebas síncronas; la producción pasa por
  `_enviar_async()`, que crea un `_Envio`.
- `_al_copiar()` manda un `ping`, que arranca Copiex si no está.
- La app consume `--bandeja` en `main()`, no abre ventana en el primer `activate` y queda
  solo en la bandeja (con `--gapplication-service` tampoco se activa al arrancar).
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

`copiex/watcher.py` (hilo propio, cada 6 s) revisa las copias en `paused` y `error` y las
reanuda cuando existen todas las carpetas destino (con varios destinos espera a que vuelvan
todas; ver 3 quindecies) y todos los orígenes se pueden leer. Mientras no sea así,
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

Los antiguos requerimientos 9–11 ya **no están en `NOTES.md`** (el pliego pasó entonces a
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

Arreglos en `copiex/nautilus_extension.py`:

- `_al_pegar()` usa un testigo (`estado["hecho"]`) y dos temporizadores: a los 1,5 s, si
  el portapapeles no ha contestado y hay algo marcado con «Copiar con Copiex», se usa eso;
  a los 6 s, si no hay nada, se muestra «No hay nada que pegar». Solo se envía una vez.
- `_enviar()` devuelve la respuesta y `_Envio` (antes `_enviar_async()`) la revisa: sin
  contacto o con `{"ok": false}` sale un `Gtk.AlertDialog` con el motivo, en vez de
  silencio.
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
escritorio, **instala el servicio D-Bus** `com.copiex.Manager.service` (plantilla
`com.copiex.Manager.service.in`, con la ruta absoluta del lanzador) y avisa si Copiex está
en marcha (seguiría con el código anterior en memoria). Termina recordando `nautilus -q` y
`./uninstall.sh`.

**`uninstall.sh`** (nuevo): deja el sistema como si Copiex nunca se hubiera instalado.

- Cierra la aplicación en marcha buscando `python3 -m copiex` **por campos exactos** (nunca
  `pkill -f`, que mataría al propio script) y espera hasta 3 s antes de forzar.
- Borra la extensión de Nautilus (`extensions/copiex.py` y sus `copiex.*.pyc`, incluidas
  las variantes de varias versiones de Python), la entrada de escritorio, el servicio
  D-Bus (`dbus-1/services/com.copiex.Manager.service`), un posible autostart, el socket y
  **los datos** (`~/.local/share/copiex`: historial y registros) y `~/.config/copiex`.
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

`menu.yaml` (raíz del proyecto, 50 líneas) reúne los nombres de las opciones de menú y los
textos de las ventanas emergentes, incluida la descripción de «Acerca de». Secciones:
`aplicacion` (nombre y descripción), `menu` (nueva, ocultar, mostrar, acerca, salir),
`ventana` (subtítulo del historial y estado vacío), `acciones` (pausar, reanudar,
reintentar, cancelar), `dialogos` (títulos de los diálogos de origen y destino) y
`nautilus` (copiar, pegar y sus consejos).

**`copiex/menu.py`** (nuevo, 176 líneas) lo lee sin dependencias: YAML mínimo de mapas
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

## 3 undecies. Alerta sonora y «Eliminar» (requerimiento 9, 13/11)

**Sonido:** la alarma es un fichero de la carpeta **`sounds/`** del proyecto, para poder
cambiarla descargando otro audio sin tocar código. `copiex/sound.py` reproduce el primer
fichero de audio de esa carpeta, con preferencia por `copy-finished.*`; si no hay ninguno,
usa el «Complete» del sistema. `sounds/README.md` lo explica y `sounds/copy-finished.wav`
es un tono propio de medio segundo (dos notas ascendentes, generado para el proyecto, sin
derechos de terceros), sustituible por otro OGG/WAV/MP3… El fichero se busca **en cada
reproducción**, así que un cambio de sonido no exige reiniciar Copiex.

Reproductores, por orden: `canberra-gtk-play -f <fichero>`, `paplay <fichero>`,
`gst-launch-1.0 playbin` (formatos que no entienden los dos primeros), y solo después el
sonido del sistema (`canberra-gtk-play --id=complete`, `paplay` del `.oga` de freedesktop)
y el pitido del servidor gráfico (`Gdk.Display.beep`). Todo en segundo plano (`Popen`, sin
esperar su salida), así que no congela la ventana. `COPIEX_SONIDOS` permite apuntar a otra
carpeta en las pruebas.
`Aplicacion._aplicar_cambio` lo llama cuando una copia queda en `done`, con un conjunto
`_sonadas` para que suene **una sola vez por copia** aunque el motor siga avisando; las
canceladas y las que fallan no suenan.

**«Eliminar»:** cada fila tiene un tercer botón, oculto mientras la copia es accionable
(`running`/`paused`/`error`). Al terminar (`done` o `cancelled`) se ocultan «Pausar» y
«Cancelar» y aparece «Eliminar», que quita la fila de la pantalla. El id queda en
`VentanaCopias._eliminadas` para que `sincronizar()` no la vuelva a pintar; **el historial
de SQLite se conserva** (no se borra nada). El texto sale de `acciones.eliminar` de
`menu.yaml`.

Comprobado con una app aislada (id propio y `XDG_DATA_HOME`/`XDG_RUNTIME_DIR` temporales,
3 MiB de origen): la copia termina, `reproducir()` se llama exactamente una vez (repetir
`_aplicar_cambio` no vuelve a sonar), «Eliminar» está visible y «Cancelar»/«Pausar» no; al
pulsarlo la lista queda vacía y se ve el estado vacío; `sincronizar()` no la resucita; una
segunda copia aparece como única fila sin traer de vuelta la eliminada; una copia
cancelada no emite sonido; `store.obtener()` confirma que la fila sigue en el historial.
`reproducir()` real devuelve True y lanza `canberra-gtk-play` (el usuario confirmó que la
alarma suena). Selección del fichero probada con carpetas temporales: único fichero con
otro nombre (se usa), `copy-finished.ogg` frente a `alarm.wav` (gana el primero), solo
texto (se usa el sonido del sistema) y carpeta inexistente (igual, sin fallos).

## 3 duodecies. Error 3: copias de muchos ficheros (medido y mejorado, 13/11)

**Medición**: datos sintéticos dentro del proyecto (disco NVMe real, no tmpfs), 5
repeticiones con `os.sync()` antes de cada una y mediana; se comparó el motor de `HEAD`
con el actual en el mismo equipo, el mismo proceso y los mismos datos.

| Caso | Antes | Después | Mejora |
|---|---|---|---|
| 2 000 ficheros de 4 KiB | 0,257 s · 121 µs de CPU/fichero | 0,206 s · 94 µs | −20 % de tiempo, −22 % de CPU |
| 400 ficheros de 256 KiB | 0,087 s · 83 ms de CPU | 0,076 s · 71 ms | −13 %, −14 % |
| 1 fichero de 256 MiB | 0,111 s · 102 ms | 0,095 s · 87 ms | −14 %, −15 % |

Los tiempos absolutos los domina la caché de página (la escritura va a ~1,6 GB/s en el
caso grande); lo que vale es la comparación, tomada con el mismo origen y destino vacío.

**Medidas aplicadas** (todas en `copiex/engine.py`):

1. **`os.copy_file_range`** por bloques de 1 MiB en lugar de `read`/`write` de Python: el
   núcleo copia de descriptor a descriptor sin pasar los datos por memoria de usuario. Si
   el sistema de ficheros no lo admite (`EXDEV` al cruzar dispositivos, `EOPNOTSUPP`,
   `ENOSYS`…), se cae en caliente a lectura/escritura desde el byte en el que iba, sin
   duplicar ni perder nada (probado cruzando `/tmp` con `$HOME`: el registro anota
   «copy_file_range no sirve aquí (Errno 18)» y el hash coincide).
2. **Un solo `stat` por fichero al planificar**: antes se recorría el árbol dos veces
   (`_pares` y `_tamano`, ya eliminada) y luego se volvía a preguntar el tamaño al copiar.
   Ahora `_planificar()` devuelve `(plan, tamaños)` y el bucle reutiliza esos datos.
3. **Carpetas memorizadas por copia** (`_dirs_creados`): un `makedirs` por carpeta, no por
   fichero.
4. Descriptores **sin búfer** para que las posiciones las lleve el núcleo, igual con
   `copy_file_range` que con `read`/`write`.

`BLOQUE` sigue en 1 MiB: con `copy_file_range` cada bloque es una sola llamada al sistema
(y 4 MiB no mejoró la medición), así que la pausa y el progreso quedan finos.

**Corrección comprobada** con el motor real (sin GTK): reanudar desde un destino a medias
(1 MiB de 3 MiB) deja el fichero idéntico (SHA-256) y conserva la fecha; cancelar una
operación arrancada en pausa deja el destino vacío; una carpeta con subcarpetas y un
fichero vacío se copia entera; pausar 400 MiB recién creados y reanudar da el mismo hash.

## 3 terdecies. La bandeja decía «Ocultar ventana» sin ventana (13/11)

Con la app arrancada en bandeja (`--bandeja`), la ventana no existe hasta que se pide,
pero el menú del icono ofrecía «Ocultar ventana»: `Aplicacion._visibilidad_cambiada()` se
salía en cuanto `self.ventana` era `None`, así que se quedaba la etiqueta inicial.

Corregido en dos puntos: `_visibilidad_cambiada()` ya no exige que exista la ventana (sin
ella, o si está oculta, pone «Mostrar ventana»), y `Bandeja` nace con «Mostrar ventana»
porque ese es su estado real al crearse; `Aplicacion.do_startup` refresca la etiqueta en
cuanto crea el icono.

Comprobado con una app aislada y contra la instancia real por D-Bus (`GetLayout` del
`dbusmenu`): sin ventana, «Mostrar ventana»; al activar el icono, «Ocultar ventana»; al
volver a ocultarla, «Mostrar ventana».

## 3 quaterdecies. Icono propio (13/11)

Se eligió la propuesta 3 de la galería `brand/preview.html`: una «C» de Copiex sobre fondo
turquesa con una barra de progreso debajo. Quedó instalado así:

- `icons/com.copiex.Manager.svg`: icono de color, con el mismo nombre que el `application_id`
  para que lo encuentre el escritorio, el dock y «Acerca de» (`application_icon`).
- `icons/com.copiex.Manager-symbolic.svg`: versión de una tinta (16×16) para la bandeja.
  `Bandeja._elegir_icono()` lo usa solo si el tema lo tiene (tras `./install.sh`); si no,
  cae en `edit-copy` y el icono nunca desaparece.
- `install.sh` los copia a `~/.local/share/icons/hicolor/scalable/apps`, refresca
  `gtk-update-icon-cache` y la entrada de escritorio pasa a `Icon=com.copiex.Manager`.
  `uninstall.sh` los borra y refresca la caché (comprobado con `--simular`).
- La ventana fija `set_icon_name("com.copiex.Manager")`, muestra el icono (22 px) dentro de
  la cabecera **justo después del título «Copiex»** (un `Gtk.Image` añadido al
  `Adw.WindowTitle` dentro de un `Gtk.Box`) y «Acerca de» usa el mismo nombre.
- `util.icono_disponible()` centraliza la elección con reserva a `edit-copy`; lo usan la
  cabecera, la bandeja y «Acerca de».

Comprobado: la cabecera muestra `com.copiex.Manager` a 22 px tras «Copiex» y, con
`XDG_DATA_HOME` temporal (sin los iconos instalados), cae en `edit-copy`; el tema de iconos
encuentra los dos nombres (`has_icon`), el `IconName` que
publica la bandeja por D-Bus es `com.copiex.Manager-symbolic` (tooltip incluido), y la app
rearrancada en bandeja no da errores. El aspecto en el panel y en el dock no se ha podido
ver desde aquí (Wayland): lo mira el usuario.

## 3 quindecies. Copia a varios destinos en una sola lectura (13/11)

Una copia puede repartirse a varias carpetas destino **leyendo el origen una vez**. Sigue
siendo una sola operación (una fila con su barra) y cada destino lleva su propia cola de
progreso.

- **Motor.** `Operacion.destinos` es una lista de `DestinoCopia` (ruta, bytes, archivos,
  estado y motivo de espera). `_copiar_a_varios()` lee cada bloque de 1 MiB una vez y lo
  escribe en todos los descriptores abiertos; el núcleo solapa las escrituras a
  dispositivos distintos. `copiados` es el **mínimo** de los destinos, así la barra solo
  avanza lo que ya está en todos; `total_bytes` es el tamaño del origen, no ×N.
- **Reanudación.** Cada destino continúa desde su tamaño actual. Si van desfasados se toma
  el mínimo como punto común, se descuenta de su progreso lo que se reescribe y no se
  cuenta dos veces. Un destino cuya carpeta desaparece queda en `paused` («esperando la
  carpeta de destino …») mientras los demás terminan; el vigilante espera a que vuelvan
  **todos** y reanuda la operación entera, igual que con un solo destino.
- **Fallos.** Un error de escritura marca solo ese destino (`error`) y no detiene a los
  demás; «Reintentar» reanuda desde su tamaño actual.
- **Un solo destino** sigue usando `os.copy_file_range` (la ruta rápida del error 3).
- **Persistencia.** Tabla nueva `destinos` (`copia_id, ruta, orden, …`) con migración
  automática; `Store.crear()` acepta lista y guarda una fila por destino;
  `actualizar_destino()` y `destinos_de()` mantienen el progreso por destino tras
  reiniciar. Las filas antiguas (sin filas en `destinos`) se leen con su único destino.
- **Ventana.** El título pasa a «Copia a N destinos» y debajo aparecen las colas separadas
  («• /media/x · 45 % · …»), con «En pausa · esperando …» o «Error: …» cuando toca.
- **Nautilus.** Nueva entrada «Pegar con Copiex N destinos» (textos en `menu.yaml`). La
  carpeta donde se pulsa es siempre el primer destino; la ventana «Destinos de la copia»
  acumula carpetas con «Añadir otro destino» (selector de carpetas) hasta «Finalizar
  selección», que manda `{"cmd":"copy","sources":[…],"dests":[…]}`. Cerrar esa ventana
  cancela; no se repiten carpetas y el primer destino no se puede volver a elegir.
- **IPC.** `dests` es una lista; `dest` se sigue aceptando para no romper nada.

Comprobado con base de datos y carpetas temporales en `/tmp`:

- 1 origen de 15,7 MB → 3 destinos: SHA-256 idéntico en los tres, `rchar` del proceso
  15 728 746 bytes (≈ una sola lectura; secuencial serían ~47 MB) y las tres filas de la
  BD en `done`.
- Cancelar: los tres destinos quedan sin restos.
- Destino 2 convertido en un fichero (simula un USB ausente): los otros dos terminan y la
  operación queda «En pausa · esperando la carpeta de destino …/r2»; al recrear la carpeta
  y reanudar, los tres acaban con el hash correcto.
- Un solo destino: sigue funcionando la ruta de `copy_file_range`.
- IPC con `dests` de 3 carpetas: operación creada, ventana con «Copia a 3 destinos» y tres
  líneas de cola; el menú de Nautilus devuelve las dos entradas con los textos del YAML.

### Prueba real con un ISO (14/11)

Prueba del usuario: ISO de 12 GB (`DriverPack Solution 18.2.1 DVD9.iso`) desde un USB a
`/home/denis/ISOs/dir1` y `dir2` con «Pegar con Copiex N destinos». La copia terminó bien
(11 984 101 376 bytes, 2 min 10 s, alarma final) y quedó **una sola** operación, como está
diseñado.

Fallos vistos en esa prueba y corregidos ese día:

- **Retraso de ~2 min** entre «Finalizar selección» y el comienzo de la copia (visto el
  14/11 a las 17:25 y otra vez a las 18:35, esta con Copiex cerrado). Diagnóstico final:
  - La extensión enviaba cada petición desde un hilo propio (`threading.Thread`). En el
    registro, el hilo `copiex-ipc` de Nautilus se quedó en `futex_do_wait` (esperando el
    GIL) justo después de escribir `enviando copy...`: la petición no llegó ni a conectar
    con el socket, que estaba sano (la app respondía `log` en 1 ms). Además, cuando
    Copiex no estaba abierto, ese hilo lo lanzaba con `subprocess.Popen` (fork desde
    Nautilus): el ping tardó 9,9 s y la copia fue acumulando lanzamientos (dos «ventana
    mostrada» en la app), que es lo que sumaba los dos minutos.
  - Ahora el envío **no usa hilos**: la clase `_Envio` hace connect/send/recv no
    bloqueantes con `GLib.io_add_watch` en el bucle principal de Nautilus, con 20 s de
    límite, reintento de conexión cada 200 ms y trazas por etapa. El arranque se pide al
    bus de sesión (`StartServiceByName`), que hace el fork fuera de Nautilus;
    `install.sh` instala `~/.local/share/dbus-1/services/com.copiex.Manager.service`
    (`Exec=… --gapplication-service`). Si el bus no pudiera, se recurre al lanzamiento
    directo desde el bucle principal. Una vez enviada, la petición **no se reenvía**
    (reenviar un `copy` duplicaría la copia): si no hay respuesta, se avisa.
  - Se mantienen los arreglos anteriores (enviar antes de cerrar la modal, cierre
    diferido con `GLib.idle_add`, servidor IPC con un hilo por conexión y `listen(32)`).
    `_enviar` sigue en el módulo para las pruebas síncronas.

  Comprobado: con Copiex cerrado, `_Envio({"cmd":"ping"})` lo arranca por D-Bus y
  responde en **0,404 s** (antes 8-10 s o colgado); con la app abierta, una copia a 2
  destinos por `_Envio` responde en **0,010 s** y los dos ficheros quedan idénticos.
  Falta repetir la prueba real desde el menú de Nautilus.
- **La ventana no salía al frente** y parecía que no copiaba: la app solo hacía `present()`
  sobre una ventana ya creada (Wayland no garantiza el foco). Ahora, si estaba oculta se
  vuelve a mostrar, se hace `present()` y se registra «ventana al frente para la copia N».
  El foco en Wayland lo decide el compositor; el contenido ya está visible.
- **Un destino terminado con otro esperando** se veía como un simple «En pausa». Ahora la
  fila dice «1 de 2 destinos completados · esperando la carpeta …», que es lo que ocurre:
  el destino disponible termina y el que falta se reanuda al volver.
- **Borrar el trozo copiado en un destino durante la pausa** (segunda prueba del usuario,
  14/11): el descriptor seguía abierto, así que se escribía en el inodo ya borrado. El
  progreso del destino subía como el del otro, al final parecía completa y los botones no
  cambiaban a «Eliminar» (la operación se quedaba en `running` con el hilo muerto). Ahora:
  - Antes de cada bloque se comprueba que el fichero de destino sigue en el disco con los
    bytes escritos (`_intacto`). Si no, se descuenta del progreso lo que esta copia contaba
    de ese fichero y se suma lo que de verdad queda (`_destino_cambio`: 0 si lo borraron);
    el destino pasa a `paused` con el motivo «el fichero de destino cambió durante la
    copia».
  - Al terminar el resto, `_trabajar_seguro` hace hasta 3 pasadas: si la carpeta del
    destino sigue disponible, lo reintenta en el acto desde su tamaño real (sin esperar
    al vigilante). Si la carpeta no está, queda en pausa y lo reanuda el vigilante.
  - En el `finally` de `_trabajar` ningún destino puede quedarse en `running`, y
    `_recalcular` solo marca `done` con los ficheros completos. Así los botones pasan a
    «Eliminar» solo cuando de verdad está todo.

  Comprobado en banco: 256 MB a 2 destinos con borrado del segundo durante la pausa → su
  progreso baja a 0, el primero termina, el segundo se reintenta y acaba con el mismo
  SHA-256 (operación `done`, ambos destinos `done`); 128 MB a 1 destino, igual; y en la
  ventana, al terminar, «Eliminar» visible y «Cancelar» oculto.

No comprobado todavía: el ciclo completo desde el menú real de Nautilus con la app cerrada
a propósito (hay que repetirlo) ni el rendimiento con varios USB físicos.

## 3 sexdecies. GNOME Notes (bijiben) lento: investigado, sin relación (14/11)

El usuario comentó que abrir un fichero de texto con «gnote» tarda ~30 s. En este equipo
es **GNOME Notes / bijiben 40.2** (`org.gnome.Notes`; Gnote no está instalado), que usa
WebKitGTK y Tracker. Medido el 14/11: ventana de Notes en **0,24-0,27 s** (perfil real y
con un fichero de texto en un perfil temporal), WebKitGTK cargando `about:blank` en 0,3 s,
`fc-list`/`fc-match` en 0,013 s y Copiex por D-Bus en 0,4 s. No se reprodujo el retraso ni
hay un atasco común de GTK/D-Bus/fuentes, así que **no es la causa** de los retrasos de
Copiex (3 ter y 3 quindecies). Si reaparece, anotar la hora y ejecutar
`journalctl --user -f | grep -iE "tracker|localsearch|bijiben|evolution"`; la caché de
Tracker tiene 214 MB y el proveedor de búsqueda de Notes reindexa notas al arrancar, el
sospechoso si solo pasa la primera vez tras iniciar sesión.

## 4. Pendientes, por orden sugerido

1. *(menor)* Tratar el pegado de un «cortar» (`cut`) como mover, no como copiar.

## 5. Trampas del entorno (ahorran media hora cada una)

- **Si algo va mal:** `~/.local/share/copiex/copiex.log` tiene todo en DEBUG con una
  semana de historial, incluidas las acciones de Nautilus (`Nautilus: …`). Si la app no
  estaba arrancada, la traza de la extensión queda en `extension.log`. Los `print` de la
  extensión se pierden.
- **Nombres:** el «centinela» de la esquina superior derecha es el icono de bandeja
  (`copiex/tray.py`, clase `Bandeja`). No confundirlo con el **vigilante**
  (`copiex/watcher.py`), que es el hilo que reanuda copias automáticamente.
- **Arrancar la app:** `./copiex-launcher` o `PYTHONPATH=. python3 -m copiex`.
  Para lanzarla desde un terminal sin que el tool espere 60 s:
  `( setsid nohup ./copiex-launcher >/tmp/copiex-app.log 2>&1 </dev/null & ) >/dev/null 2>&1`
- **Nombres en inglés:** los ficheros y carpetas del proyecto van en inglés (`sound.py`,
  `watcher.py`, `nautilus_extension.py`, `copiex-launcher`, `sounds/`); las clases y
  funciones siguen en español (`Vigilante`, `cargar()`, …). No introduzcas nombres nuevos
  en español.
- **Nunca** uses `pkill -f "python3 -m copiex"`: la propia línea de comandos del shell
  contiene ese texto y el comando se mata a sí mismo (pasó en noviembre). Localiza el PID
  con `ps -eo pid,cmd | grep "[p]ython3 -m copiex"` y mátalo por PID.
- **Rutas:** socket `$XDG_RUNTIME_DIR/copiex-1000/copiex.sock`
  (`/run/user/1000/...`); base de datos
  `~/.local/share/copiex/historial.db`, tabla `copias`.
- **Desinstalar:** `./uninstall.sh` (pregunta; `--simular` para ver antes lo que
  borraría, `--conservar-datos` para quedarse con historial y registros).
- **Instalar cambios de la extensión:** `./install.sh` copia
  `copiex/nautilus_extension.py` a `~/.local/share/nautilus-python/extensions/copiex.py`.
  Después hay que reiniciar Nautilus (`nautilus -q`) o no se recarga.
- **Servicio D-Bus:** `./install.sh` instala
  `~/.local/share/dbus-1/services/com.copiex.Manager.service`; es lo que permite que la
  extensión arranque Copiex sin hacer `fork` desde Nautilus. Si falta, el arranque en frío
  cae en `_arrancar_app_directo()` (más lento y frágil). Comprobar con
  `busctl --user list | grep copiex` y `cat` del `.service`.
- **Probar el arranque en frío:** no cambies `XDG_DATA_HOME` en esa prueba: el bus busca el
  `.service` en el `XDG_DATA_HOME` del demonio y el `.desktop` en el mismo sitio, así que
  la activación no encuentra Copiex. Para pruebas con BD temporal, arranca la app a mano
  con ese entorno y envía con `_Envio` usando el `XDG_RUNTIME_DIR` temporal; para probar
  D-Bus, usa el entorno real y una petición `ping` (no crea historial).
- **Una sola instancia:** GApplication registra `com.copiex.Manager` en el bus de sesión;
  si ya hay una app real en marcha, una app de prueba con otro `XDG_DATA_HOME` solo
  activa la real y sale. Para pruebas aisladas, para la real antes (por PID).
- **Varios destinos, no es un fallo:** la barra de una copia repartida avanza con el
  **mínimo** de los destinos, así que se queda quieta si un USB va por detrás o está
  ausente; las líneas «• …» de la fila dicen cuál. El estado de cada destino vive en la
  tabla `destinos`, no en `copias`.
- **Protocolo IPC:** `{"cmd":"copy","sources":[uri,...],"dest":uri}` o, para varios
  destinos, `"dests":[uri,...]` (`dest` se sigue aceptando); además de `ping` y `show`.
- **Probar sin clic derecho:** importar `copiex.nautilus_extension`, instanciar
  `ExtencionCopiex()` y emitir `activate` sobre los ítems de `get_file_items()` /
  `get_background_items()`. Es exactamente lo que hace Nautilus.
- **Alerta sonora:** `python3 -c "from copiex.sound import fichero, reproducir;
  print(fichero(), reproducir())"` (suena de verdad). `COPIEX_SOUNDS=/ruta` apunta a otra
  carpeta de sonidos.
- **Icono:** `Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon(...)` para
  comprobar que el tema lo ve, y `gdbus call --session --dest
  org.kde.StatusNotifierItem-<pid>-1 --object-path /StatusNotifierItem --method
  org.freedesktop.DBus.Properties.Get org.kde.StatusNotifierItem IconName` para la
  bandeja.
- **Sesión Wayland** con GNOME 50: no hay `xdotool`, `wmctrl` ni `ydotool`; solo `grim`
  para capturas. Para comprobar el menú hace falta un clic derecho humano.

## 6. Estado del sistema donde se probó

Ubuntu 26.04 «resolute», GNOME 50.1, Nautilus 50.2.2, GTK 4.22.4, PyGObject 3.56.2,
Wayland. El proyecto **es un repositorio git** (rama `main`; último commit `c78d28e`
«Ajustes generales»; remoto `repo-copiex` en GitHub). **Todo el trabajo del 13 y 14/11
está sin commitear**: motor de varios destinos y sus arreglos (`engine`), `store`,
`window`, `app`, `ipc`, `menu`, extensión reescrita sin hilos, `install.sh`,
`uninstall.sh`, `com.copiex.Manager.service.in` (nuevo), `menu.yaml`, `TODO.md`,
`AGENTS.md` y varios `.pyc` de `copiex/__pycache__/` que no conviene commitear.
Historial real al cerrar la sesión: 35 filas (27 `done`, 4 `error`, 4 `cancelled`) y 9
filas en `destinos`. La app quedó en marcha (el PID cambia; comprobar con
`ps -eo pid,args | grep "[p]ython3 -m copiex"`). **Aviso de seguridad:** la URL del remoto guarda
un token de GitHub incrustado en `.git/config`; conviene rotarlo y usar un ayudante de
credenciales. No hagas commit ni push sin que el usuario lo pida.

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
- **Varios destinos:** `m.crear([origen], [d1, d2, d3])`; comprobar el SHA-256 en los tres
  y que `op.copiados` sea el mínimo de los destinos. Para simular un destino ausente, crear
  un fichero con la ruta del destino: la operación queda en pausa mientras los demás
  copian; al recrear la carpeta, `m.reanudar(op.id)`.
- **Destino borrado durante la pausa:** copiar 256 MB a 2 destinos, pausar, borrar el
  fichero del segundo y reanudar; su progreso debe bajar a 0 (no avanzar), el primero debe
  terminar, el segundo reintentarse solo y ambos acabar en `done` con el mismo SHA-256.
- **Arranque en frío por D-Bus:** con Copiex cerrado, importar la extensión instalada y
  usar `_Envio({"cmd": "ping"})` dentro de un `GLib.MainLoop` con el entorno real; debe
  responder en ~0,4 s y dejar rastro en `copiex.log`. Con la app abierta, ~0,003 s.
  (Con `XDG_DATA_HOME` temporal, el bus no encuentra el servicio; ver sección 5.)
- **Regla de oro:** cualquier callback pasado a `GLib.idle_add` debe devolver `False`
  (ver sección 3).
