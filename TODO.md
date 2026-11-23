# Copiex — punto de retorno

Estado del trabajo al **17 de noviembre de 2026**: el 14/11 quedaron instalados el arreglo
del destino borrado durante una pausa y el arranque de Copiex desde Nautilus (envío sin
hilos y activación por D-Bus); el 16/11 se añadieron el **requerimiento 12 (MTP)**,
probado con un Android real en ambos sentidos, **«Cortar con Copiex»** (mover de verdad) y
el **icono a color en la bandeja** (la «C» blanca sobre verde). Este fichero y `NOTES.md`
son todo lo que necesita una sesión nueva: el asistente no conserva memoria entre chats, y
este resumen evita tener que releer el historial de la conversación anterior.

**Resumen en una línea:** Copiex está terminado: los 16 requerimientos del pliego y los 4
errores están resueltos (bandeja, extensión de Nautilus, historial SQLite con reanudación
automática, `menu.yaml` con todos los textos, «Acerca de», alerta sonora propia con botón
«Eliminar», icono propio, copia optimizada con `copy_file_range`, varios destinos con una
sola lectura, copia hacia/desde MTP, selector de idioma español/inglés, idioma inicial
tomado de GNOME al instalar el `.deb`, tiempo restante estimado y estable, y «Cortar» dentro
de la misma partición moviendo al instante sin copiar). El 14/11 se corrigieron los dos fallos de la prueba
real: un destino cuyo fichero se borra durante la pausa no infla el progreso y se
reintenta solo; y la extensión ya no envía desde un hilo ni lanza Copiex con `fork` desde
Nautilus (lo arranca el bus de sesión), así que la petición sale en milisegundos. El 16/11
se añadió además **«Cortar con Copiex»**: mueve de verdad (copia y borra los orígenes al
terminar), también con «Pegar con Copiex N destinos». Los requerimientos de workers se
retiraron del pliego el 13/11 y su código se eliminó (sección 3 quinquies).

El 16/11 se completó además el **empaquetado `.deb`** con las dependencias offline, se
retiró `install.sh`, se añadió `upgrade.sh` para actualizar dependencias y reconstruir el
paquete, y todo se publicó en el commit **`ce8d9ee`** (secciones 3 undevicies y 3 vicies).

El **17/11** se corrigió la reanudación automática de una copia a varios destinos que había
sido reanudada manualmente y luego recibió un kill: `Motor.reanudar()` no persistía que la
pausa manual ya estaba deshecha. El arreglo de `copiex/engine.py` se publicó en el commit
de esta corrección (sección 3 unvicies).

También el **17/11** se añadió el **selector de idioma español/inglés** en el menú del
Centinela y en el de la ventana. La preferencia se guarda en
`~/.config/copiex/language`; la extensión de Nautilus la lee al construir el menú y avisa
a Nautilus para que rehaga sus ítems, así que sus entradas cambian sin reiniciar el gestor.
Los textos viven en `menu.yaml` (sección 3 duovicies).

El **18/11** se añadió el **idioma inicial al instalar el `.deb`** (requerimiento 14): el
`postinst` escribe `~/.config/copiex/language` con `es` si la interfaz GNOME está en
español y con `en` en cualquier otro caso, sin pisar una elección previa. Está en
`packaging/initial-language` (sección 3 tervicies).

También el **18/11** la ventana principal permite repartir una copia a varias carpetas
sin pasar por Nautilus: «Nueva copia» abre, tras elegir la primera carpeta, el diálogo
«Destinos de la copia» (`copiex/destinations.py`, sección 3 quatervicies), que entrega la
lista completa al mismo motor de varios destinos.

---

## 1. Cómo retomar

Abre el proyecto en Freebuff y pega algo como:

> Lee `TODO.md` y `NOTES.md`. Los 16 requerimientos y los 4 errores del pliego ya están
> cerrados: no rehagas lo ya verificado y, si hay algo nuevo, sigue las reglas de
> `AGENTS.md` (textos en `menu.yaml`, nombres de fichero en inglés, sin workers, sin
> `pkill -f`). Antes de tocar el motor o la extensión, lee 3 ter, 3 quindecies y
> 3 septendecies: el 14/11 se corrigieron el destino borrado durante la pausa y el
> arranque sin hilos por D-Bus, y el 16/11 se añadieron MTP, «Cortar con Copiex» y el
> icono a color en la bandeja. El paquete `.deb`, `upgrade.sh`, la retirada de `install.sh`
> y la publicación están en las secciones 3 undevicies y 3 vicies. El selector de idioma
> está en la sección 3 duovicies, el idioma inicial al instalar en 3 tervicies y el
> diálogo de varios destinos del botón «Nueva copia» en 3 quatervicies, el tiempo restante
> del requerimiento 15 en 3 quinvices y el movimiento instantáneo dentro de la misma
> partición del requerimiento 16 en 3 sexvicies. No queda trabajo pendiente salvo tu prueba real del
> menú de Nautilus, del icono, del selector y del diálogo de destinos (sección 4). No hagas
> commit ni push sin pedírmelo.

La sesión nueva arrancará sabiendo el estado real sin repetir pruebas ya hechas.

### Estado actual al retomar (23/11/2026)

- **Git:** todo publicado hasta **`4ab3f99`** «Anotar el arreglo del icono de la bandeja
  en la documentación» (antes, `8c58d5a` «Copiex .deb preparado para Ubuntu 24.04 y
  26.04», `3793477`, `cca1b2c`, `8f7d8eb`, `fc04da6`, `09fb53f` y `ce8d9ee`). Hay cambios
  locales **sin publicar**: el arreglo de `IconPixmap` de `copiex/tray.py` con
  `librsvg2-common` en `packaging/deps.txt`, y los requerimientos 15 y 16 en
  `copiex/engine.py`. El `.deb` de 60 MB no se versiona, y desde el 18/11 tampoco los
  `__pycache__/*.pyc` (están en `.gitignore`).
- **En marcha:** al retomar, la app **no está arrancada**; se levanta con
  `./copiex-launcher --bandeja` (o se activa sola desde Nautilus). Nautilus tiene la
  extensión instalada idéntica a la fuente.
- **Historial real:** **43 filas** (32 `done`, 7 `cancelled`, 4 `error`) y 21 en
  `destinos`; la migración de la columna `mover` ya está aplicada. No se tocó ninguna fila
  en las pruebas (se usaron BD en `/tmp`).
- **Cerrado y probado:** MTP en ambos sentidos; «Cortar» a uno y a N destinos (motor, IPC y
  extensión), confirmado por el usuario; el icono de la bandeja anuncia
  `com.copiex.Manager` (color). El selector de idioma cambia la ventana, el menú del
  Centinela y las etiquetas de Nautilus.
- **Idioma:** español por defecto en el código; al instalar el `.deb`, el `postinst` elige
  español o inglés según la interfaz GNOME de cada usuario (requerimiento 14). La elección
  se guarda en `~/.config/copiex/language` (`COPIEX_LANGUAGE` permite forzarlo en pruebas). No hay que reiniciar Nautilus: al abrir
  de nuevo el menú contextual, «Copiar/Cortar/Pegar con Copiex» ya salen en el idioma
  elegido.
- **Confirmado por el usuario el 17/11:** «Cortar» y que, al cambiar de idioma en Copiex,
  el menú de Nautilus sale traducido sin reiniciarlo (basta reabrir el menú contextual).
- **Pendiente del usuario:** confirmar que en el panel ya se ve la «C» verde. Mover
  carpetas vacías ya funciona (requerimiento 16, 3 sexvicies); mover hacia/desde MTP sigue
  como mejora opcional.
- **Paquete .deb:** `copiex_1.0.1_amd64.deb` (60 MB) en la raíz, ignorado por Git, y el
  empaquetado en `packaging/` (sí versionado); `upgrade.sh` actualiza deps, reconstruye el
  `.deb` y reinstala. Todo está en `ce8d9ee`. Detalles y límites en 3 undevicies y 3 vicies.
- **Siguiente paso:** si no pide algo nuevo, no rehacer lo ya verificado ni hacer
  commit/push sin que lo pida.

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
| Arranque de Copiex al pulsar «Copiar con Copiex» | **Hecho el 12/11 y reforzado el 14/11.** Si no estaba en marcha, se arranca solo en la bandeja, sin abrir ventana. Desde el 14/11 lo pide al bus de sesión (servicio `com.copiex.Manager`, que instala el `.deb`): **0,404 s** en frío. |
| Latencia al pegar | **Medida el 12/11; re-medida el 14/11.** Antes 1,57 s en frío y hasta ~4 s con los reintentos ciegos; ahora **0,003 s** con la app abierta y **0,404 s** en frío por D-Bus. Detalles en 3 ter. |
| Historial de la base de datos | **43 filas al 17/11** (32 `done`, 7 `cancelled`, 4 `error`) y 21 filas en `destinos`, todas copias reales del usuario. Columnas de `copias`: `id, origenes, destino, total_bytes, copiados_bytes, total_archivos, copiados_archivos, estado, error, pausa_manual, mover, creado, actualizado` (`mover` se añadió el 16/11 con migración automática). Tabla `destinos` (desde el 13/11): una fila por carpeta destino con su progreso y estado; en `copias.destino` se guarda el primero. |
| «Acerca de» + `menu.yaml` (requerimientos 10 y 11) | **Hecho el 13/11.** Acción `app.acerca` con `Adw.AboutDialog` (versión de `copiex/__init__.py` y descripción de `menu.yaml`); menús de ventana, bandeja y Nautilus, y los diálogos de origen/destino, leen sus textos de `menu.yaml` mediante `copiex/menu.py` (lector YAML propio, con caché y valores por defecto). Detalles en 3 decies. |
| Alerta sonora y «Eliminar» (requerimiento 9) | **Hecho el 13/11.** `copiex/sound.py` reproduce el audio de `sounds/` (manda `copy-finished.*`) una sola vez por copia terminada; «Cancelar» deja paso a «Eliminar», que quita la fila sin borrar el historial. El usuario confirmó que la alarma suena. Detalles en 3 undecies. |
| Nombres de ficheros y carpetas en inglés | **Hecho el 13/11.** `sound.py`, `watcher.py`, `nautilus_extension.py`, `copiex-launcher`, `sounds/`, `TODO.md`, `NOTES.md`. Los identificadores internos (clases, funciones, atributos) siguen en español a propósito. |
| Error 3: copias de muchos ficheros | **Medido y mejorado el 13/11.** −20 % de tiempo y −22 % de CPU en 2 000 ficheros de 4 KiB, −14 % en un fichero de 256 MiB: `os.copy_file_range`, un `stat` por fichero al planificar y carpetas memorizadas. Detalles en 3 duodecies. |
| Bandeja sin ventana abierta | **Corregido el 13/11.** El icono ofrecía «Ocultar ventana» aunque la ventana no existiera; ahora dice «Mostrar ventana» y se refresca al abrir/ocultar. Detalles en 3 terdecies. |
| Icono propio y cabecera | **Hecho el 13/11; bandeja corregida el 16/11.** «C» turquesa con barra de progreso (`icons/`), instalado en el tema `hicolor`; la cabecera lo muestra a 22 px tras «Copiex». La bandeja usaba la variante simbólica y se veía como un punto con una barrita; desde el 16/11 usa el icono a color (`com.copiex.Manager`). Detalles en 3 quaterdecies. |
| Copia a varios destinos | **Hecho el 13/11.** Una operación, varias carpetas destino y **una sola lectura** del origen: cada bloque se escribe en todos los destinos a la vez. Cada destino tiene su cola visible en la ventana, su progreso en la BD, y se reanuda solo si su carpeta desaparece. En Nautilus: «Pegar con Copiex N destinos». Detalles en 3 quindecies. |
| Destino borrado o truncado durante la pausa | **Corregido el 14/11.** Antes se seguía escribiendo en el inodo ya borrado: el progreso mentía y la operación quedaba en `running`. Ahora se comprueba el fichero antes de cada bloque, el progreso baja a lo que queda en disco (0 si se borró) y el destino se reintenta al terminar el resto; los botones pasan a «Eliminar» solo con todo completo. Detalles y pruebas en 3 quindecies. |
| Arranque desde Nautilus sin hilos | **Hecho el 14/11.** La extensión ya no envía desde un `threading.Thread` (se quedaba esperando el GIL) ni lanza Copiex con `subprocess.Popen` (fork desde Nautilus): `_Envio` usa callbacks de `GLib.io_add_watch` y el arranque lo hace el bus de sesión. Medido: 0,404 s en frío y 0,003 s con la app abierta. Detalles en 3 ter. |
| MTP (requerimiento 12) | **Hecho y probado el 16/11.** Las URIs `mtp://` se resuelven con GIO a su montaje de gvfs-fuse y el motor trabaja con rutas normales; funciona en ambos sentidos, con varios destinos y una sola lectura, con pausa, cancelación y reanudación. Al escribir en MTP el fichero se rehace desde cero (MTP no admite continuación fiable). Detalles en 3 septendecies. |
| «Cortar» en la misma partición (requerimiento 16) | **Hecho y comprobado el 23/11.** Si origen y destino comparten `st_dev`, `Operacion._mover_directo()` usa `os.rename()` en vez de copiar: mover 512 MiB tardó 1 ms y el inodo no cambió. Con otra partición, MTP, varios destinos, un nombre ya ocupado o un renombrado que el sistema rechaza, cae al camino de copiar y borrar de siempre. Detalles en 3 sexvicies. |
| «Cortar con Copiex» (mover) | **Hecho y probado el 16/11.** Nueva entrada en el menú de Nautilus, también para «Pegar con Copiex N destinos»: copia primero y borra los orígenes cuando **todos** los destinos están completos; con cancelación, error o destino ausente los originales no se tocan. La marca `mover` se guarda en el historial y el portapapeles con cabecera `cut` también se mueve. Detalles en 3 octodecies. |

Lo único **no** comprobado visualmente es lo que exige un clic o mirar el panel: el menú
desplegado de Nautilus (Wayland sin `xdotool`/`ydotool`) y el aspecto del icono en el
panel, el dock, la cabecera y «Acerca de». En su lugar se verificó el código que devuelve
los ítems del menú y su activación, los nombres de icono que resuelve el tema y los que la
bandeja publica por D-Bus. Tampoco se ha visto con un clic real el ítem «Pegar con Copiex
N destinos» ni su ventana de selección: se comprobó que el menú devuelve la entrada con
sus textos y que la ventana se construye y se cierra. Tampoco se ha repetido la prueba
real de arranque con la app cerrada desde el menú; sí en banco, por D-Bus (0,404 s).

## 2 bis. Mapa del código (4 645 líneas al 16/11, sin contar `packaging/`)

| Fichero | Líneas | Responsabilidad |
|---|---|---|
| `copiex/util.py` | 172 | Rutas (`runtime_dir`, `socket_path`, `data_dir`), URIs ↔ rutas (`uri_to_path` acepta `file:` y `mtp:`, `es_mtp`, `ruta_a_uri`, `short_path` muestra `mtp://…`), formatos de tamaño y tiempo, `APP_ID`/`APP_NAME`/`EXTENSION_NAME`. |
| `copiex/logs.py` | 203 | Registro único `copiex.log` en DEBUG con 7 días de retención: poda atómica por fecha y por tamaño (`podar`, `ManejadorSemanal`, `configurar_registro`). |
| `copiex/engine.py` | 1419 | `Operacion` (hilo de copia, pausa, aviso, velocidad, persistencia), `DestinoCopia` (estado por destino) y `Motor` (crear, pausar, reanudar, cancelar, historial). Un «Cortar» con un solo destino en la misma partición se hace con `os.rename()` en `_mover_directo()` (instantáneo, sin copiar); si no se puede, sigue el camino de copia y borrado. Bloques de 1 MiB; un solo destino con `os.copy_file_range` (reserva a lectura/escritura) y varios con `_copiar_a_varios()` (una lectura, escritura a todos); un `stat` por fichero y carpetas memorizadas; `_copiar_fichero()` reanuda por byte; `_pares()` calcula origen→destino. `_intacto()`/`_destino_cambio()` detectan un destino borrado o truncado; `_ejecutar_plan()` y hasta 3 pasadas en `_trabajar_seguro()` reintentan esos destinos; el `finally` de `_trabajar` no deja ninguno en `running`. Con MTP (`es_mtp`) no usa `copy_file_range` y rehace el fichero en vez de continuarlo por byte, descontando del progreso el parcial anterior. `Operacion.mover` (un «cortar») borra los orígenes en `_borrar_origenes()` solo con todos los destinos en `done`; la marca se persiste en la columna `mover`. |
| `copiex/store.py` | 248 | SQLite en `~/.local/share/copiex/historial.db`: alta, actualización, pendientes, migración de `pausa_manual` y tabla `destinos` (`crear` acepta lista, `actualizar_destino`, `destinos_de`). |
| `copiex/watcher.py` | 75 | Hilo cada 6 s que reanuda `paused`/`error` cuando origen y **todas** las carpetas destino están disponibles; respeta `pausa_manual`. |
| `copiex/menu.py` | 455 | Textos de la interfaz: lector YAML mínimo de `menu.yaml`, textos por defecto en español e inglés, elección persistida en `~/.config/copiex/language` y `texto("menu.nueva")`/`formato(clave, …)`. |
| `copiex/sound.py` | 105 | Alerta de fin de copia: reproduce el audio de `sounds/` (o el del sistema) con `canberra-gtk-play`, `paplay` o `gst-launch-1.0`, en segundo plano. |
| `sounds/` | — | `copy-finished.wav` (alarma por defecto, sustituible) y `README.md` con las reglas de elección del fichero. |
| `copiex/app.py` | 381 | `Adw.Application`: une motor, ventana, bandeja e IPC; acciones `nueva`/`ocultar`/`idioma_es`/`idioma_en`/`acerca`/`salir`; sonido una vez por copia terminada; argumento `--bandeja`; IPC con `dest` o `dests`. |
| `copiex/window.py` | 353 | Ventana del historial: fila por copia con barra, velocidad, estado, «Reintentar»/«Cancelar»/«Eliminar» y, si hay varios destinos, una línea de cola por destino; menú (ocultar/idioma/acerca/salir) y botón «Nueva copia». |
| `copiex/tray.py` | 360 | Icono de bandeja por StatusNotifierItem + D-Bus, sin dependencias; menú contextual con submenú de idioma (radio Español/Inglés; Spanish/English en inglés). |
| `copiex/ipc.py` | 126 | Socket Unix `$XDG_RUNTIME_DIR/copiex-<uid>/copiex.sock`; JSON por línea (`ping`, `show`, `copy`); cada conexión se atiende en un hilo propio (`listen(32)`) para que una colgada no retrase la siguiente. |
| `copiex/nautilus_extension.py` | 1091 | Extensión de Nautilus: menú contextual (etiquetas de `menu.yaml` en español o inglés), «Copiar» y «Cortar» (portapapeles con cabecera `copy`/`cut`, acepta `file://` y `mtp://`), envío por socket (`move: true` para cortar) y ciclo «Pegar con Copiex N destinos» (`_SelectorDestinos`, que muestra la URI MTP sin `%20`). `_Envio` hace connect/send/recv no bloqueantes con `GLib.io_add_watch` (sin hilos); `_arrancar_app()` usa el servicio D-Bus y deja `_arrancar_app_directo()` como respaldo. |
| `icons/` | — | Icono propio: `com.copiex.Manager.svg` (color) y `com.copiex.Manager-symbolic.svg` (una tinta, para la bandeja). |
| `brand/` | — | Propuestas de logo descartadas y `preview.html`, la galería con la que se eligió el icono. |
| `menu.yaml` | 230 | Textos en español (raíz) e inglés (`en:`): opciones de menú, ventanas emergentes, estado de las copias, errores y selección de varios destinos. |
| `uninstall.sh`, `copiex-launcher`, `com.copiex.Manager.desktop.in`, `com.copiex.Manager.service.in` | — | Limpieza de instalaciones antiguas de usuario (extensión, escritorio, servicio D-Bus, iconos, datos), lanzador, entrada de escritorio y plantilla del servicio `com.copiex.Manager` que usa la extensión para arrancar la app sin `fork`. |
| `packaging/`, `upgrade.sh` | — | Empaquetado `.deb`: `build-deb.sh`, `resolver.py`, `deps.txt`, `postinst`, `postrm` y los helpers `instalar-dependencias`/`copiex-dependencias`. Genera un repositorio APT local con los `.deb` de las dependencias para instalar sin red. `upgrade.sh` actualiza las dependencias, reconstruye el `.deb` con las versiones actuales y reinstala Copiex. |

Puntos de entrada: `./copiex-launcher` (ejecuta `PYTHONPATH=. python3 -m copiex`) y,
desde Nautilus, la extensión instalada en
`~/.local/share/nautilus-python/extensions/copiex.py`.

## 2 ter. Requerimientos del pliego, uno a uno

El pliego se renumeró el 13/11: al retirar los antiguos 9–11 (workers), «alerta sonora»,
«Acerca de» y `menu.yaml` pasaron a ser los requerimientos 9, 10 y 11. El 16/11 se añadió
el 12 (MTP), el 17/11 el 13 (selector de idioma), el 18/11 el 14 (idioma inicial al
instalar el `.deb`) y el 23/11 el 15 (tiempo restante realista y estable).

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
| 10 | «Acerca de» con descripción corta y versión, en `menu.yaml` | Hecho: `app.acerca` con `Adw.AboutDialog` (versión 1.0.1 y descripción del YAML); sección 3 decies. |
| 11 | `menu.yaml` con nombres de opciones y textos de ventanas | Hecho: menús de ventana, bandeja y Nautilus más diálogos leen `menu.yaml`; sección 3 decies. |
| 12 | Copiar hacia o desde dispositivos `mtp://` | Hecho y probado el 16/11 con un Android real: ambos sentidos, varios destinos, pausa, cancelación y reanudación; sección 3 septendecies. |
| 13 | Cambiar toda la interfaz entre español e inglés | Hecho el 17/11: selector en el menú del Centinela y de la ventana, preferencia persistida y etiquetas de Nautilus actualizadas sin reiniciar; sección 3 duovicies. |
| 14 | Idioma inicial según GNOME al instalar el `.deb` | Hecho el 18/11: `packaging/initial-language` y `postinst`, sin pisar la elección del usuario; sección 3 tervicies. |
| 15 | Tiempo restante realista y que no cambie continuamente | Hecho el 23/11: velocidad de los últimos 15 s con suavizado y actualización con histéresis; sección 3 quinvices. |
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
- **Cortar (`cut`) mueve**: desde el 16/11 la cabecera `cut` (de Nautilus o de «Cortar con
  Copiex») hace que, tras copiar a todos los destinos, se borren los orígenes. Detalles en
  3 octodecies.
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
  el `.deb` instala `/usr/share/dbus-1/services/com.copiex.Manager.service`
  (`Exec=… --gapplication-service`; antes lo hacía `install.sh` en el usuario). Así el
  fork lo hace el bus y no Nautilus. Si el bus
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
un bus D-Bus privado (línea «Copiex 1.0.1 arranca (pid …, bandeja)»), y una sesión con una
copia de 2 GB pausada, reanudada, cancelada a 406 MB y un origen inexistente: el fichero
cuenta la historia completa. Tras el cambio hay que **reiniciar la app** para que use este
registro (hecho: instancia reiniciada en bandeja).

## 3 nonies. Instalación y desinstalación completas (13/11; `install.sh` retirado el 16/11)

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
(`__version__` = «1.0.1»), no del YAML, para que haya una sola fuente.

**Extensión de Nautilus**: se instala como fichero suelto y no puede importar el paquete,
así que repite un lector mínimo para la sección `nautilus:`. Encuentra `menu.yaml` a partir
de la ruta del lanzador del `.desktop` (mismo directorio) y, si no está, usa las etiquetas
de siempre (`_TEXTO_DEFECTO`). Estrena los cambios con `./upgrade.sh` + `nautilus -q`.

Comprobado: compilación de todo el paquete; textos del fichero real; con un `menu.yaml`
temporal (`COPIEX_MENU`) cambian las etiquetas de la ventana («Copiar ahora», «Sobre
Copiex», subtítulo «Copias de prueba») y las claves ausentes caen en su valor por defecto;
`app.acerca()` construye y presenta el diálogo sin errores; la extensión devuelve las
cuatro cadenas de `menu.yaml`; entonces `./install.sh` copiaba la extensión idéntica. La ventana de
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
- `icons/com.copiex.Manager-symbolic.svg`: versión de una tinta (16×16). Se instala,
  pero **la bandeja ya no la usa**: el 16/11 se cambió a la variante a color porque la
  simbólica se veía como un punto con una barrita. `Bandeja.ICONO` apunta a
  `com.copiex.Manager`; si el tema no lo tiene, cae en `edit-copy` y nunca queda un hueco.
- El `.deb` los instala en `/usr/share/icons/hicolor/scalable/apps` y refresca
  `gtk-update-icon-cache` en el `postinst`; antes `install.sh` los copiaba a
  `~/.local/share/icons`. `uninstall.sh` limpia la copia de usuario antigua (comprobado
  con `--simular`).
- La ventana fija `set_icon_name("com.copiex.Manager")`, muestra el icono (22 px) dentro de
  la cabecera **justo después del título «Copiex»** (un `Gtk.Image` añadido al
  `Adw.WindowTitle` dentro de un `Gtk.Box`), «Acerca de» usa el mismo nombre y la bandeja
  también (antes usaba la variante simbólica).
- `util.icono_disponible()` centraliza la elección con reserva a `edit-copy`; lo usan la
  cabecera, la bandeja y «Acerca de».

Comprobado: la cabecera muestra `com.copiex.Manager` a 22 px tras «Copiex» y, con
`XDG_DATA_HOME` temporal (sin los iconos instalados), cae en `edit-copy`; el tema de iconos
encuentra los dos nombres (`has_icon`). Hasta el 16/11 el `IconName` que la bandeja
publicaba por D-Bus era `com.copiex.Manager-symbolic` y el usuario veía un punto con una
barrita; ahora `Bandeja.ICONO` es `com.copiex.Manager` y la consulta D-Bus devuelve el
icono a color (tooltip incluido). La app rearrancada en bandeja no da errores. El aspecto
en el panel y en el dock no se ha podido ver desde aquí (Wayland): lo mira el usuario.

### Los tres puntos en Ubuntu 24.04 (19/11)

En 24.04 el panel mostraba **tres puntos** en lugar del icono. Son
`image-loading-symbolic`, el icono de reserva de la extensión AppIndicator 57, que fallaba
al cargar el nuestro:

```
copiex unable to update icon: TypeError: oldIcon.equals is not a function
  add@…/iconCache.js:52 ← _cacheOrCreateIconByName ← _createIcon ← _createAndSetIcon
```

`Gio.Icon` expone `equal()`, no `equals()`: el fallo salta cuando se pide el mismo icono
dos veces mientras se carga, y nuestro SVG se resuelve de forma asíncrona, así que da
tiempo a la segunda petición. El icono y el tema estaban bien
(`has_icon("com.copiex.Manager")` es True e `IconName` se publicaba correcto).

**Arreglo (`copiex/tray.py`):** la bandeja publica también `IconPixmap`, el icono
rasterizado con GdkPixbuf a 16/22/24/32/48/64 px en ARGB32 de orden de red y alfa
premultiplicado, que es lo que espera el panel (`Cogl.PixelFormat.ARGB_8888`). Cuando hay
mapas de bits, `IconName` va **vacío a propósito** para que el panel no pase por la caché
defectuosa; si no se puede rasterizar (falta el cargador de SVG) se publica solo el
nombre, como antes. Cuesta ~8 ms al crear la bandeja y no añade dependencias:
`gir1.2-gdkpixbuf-2.0` ya viene con `gir1.2-gtk-4.0`. A `packaging/deps.txt` sí se añadió
`librsvg2-common`, que es el cargador de SVG, para que el repositorio offline lo traiga.

También se corrigió el XML de la interfaz: `IconPixmap`, `AttentionIconPixmap` y
`OverlayIconPixmap` declaraban `aa(iiay)` (un nivel de más) y la spec de SNI espera
`a(iiay)`; con el tipo equivocado el panel respondía «No se pudo obtener la propiedad».

Comprobado el 19/11 en 24.04 con la app en bandeja: `IconName` = `''`, `IconPixmap`
devuelve los seis tamaños con sus bytes, el registro de GNOME Shell ya no muestra
`unable to update icon` ni `Impossible to create image from data`, y el mapa de bits
reconstruido a PNG sale con la «C» blanca sobre verde (verde `#34a37e`). **Falta la
confirmación visual del usuario en el panel.**

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
    el `.deb` instala `/usr/share/dbus-1/services/com.copiex.Manager.service`
    (`Exec=… --gapplication-service`; antes `install.sh`, en el usuario). Si el bus no
    pudiera, se recurre al lanzamiento
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

## 3 octodecies. «Cortar con Copiex»: mover de verdad (16/11)

El pendiente menor del pliego ya está hecho: el menú contextual de Nautilus ofrece
**«Copiar con Copiex»** y **«Cortar con Copiex»**. Cortar no cambia el motor de copia:
copia igual que siempre y, **solo cuando todos los destinos están en `done`**, borra los
orígenes. Así vale para «Pegar con Copiex» y para «Pegar con Copiex N destinos» sin
duplicar lógica.

- **Extensión.** `_al_cortar()` marca la selección con la cabecera `cut` del portapapeles
  de Nautilus (`x-special/gnome-copied-files`), así que un Ctrl+V normal del gestor
  también movería. Al pegar, `_con_origenes()` lee la acción (`_accion_del_portapapeles`) y
  añade `"move": true` al mensaje; si el portapapeles no contesta o el formato no trae
  cabecera pero son los mismos elementos, usa la última marca (`_seleccion_accion`). «N destinos» guarda el modo en `_SelectorDestinos` y lo manda al
  finalizar. Un Ctrl+X de Nautilus también se interpreta como mover.
- **Aplicación.** `crear_copia(..., mover=True)` → `Motor.crear(..., mover=True)`;
  `Operacion.mover` viaja a la columna nueva `mover` de `copias` (migración automática), y
  `cargar_historial()` la recupera: si la app se cierra a mitad, al reanudar sigue siendo
  un movimiento.
- **Borrado.** `_borrar_origenes()` se ejecuta al final de `_trabajar_seguro`, después de
  `_recalcular()` y solo con `estado == "done"` y sin cancelación. Borra ficheros y
  carpetas de dentro hacia fuera (`_borrar_arbol`) y es mejor esfuerzo: si un origen no se
  puede borrar, la copia sigue `done` y queda un aviso en el registro. Nunca borra nada
  antes de tener los datos en **todos** los destinos.
- **Misma carpeta.** `Motor.crear()` rechaza que el destino sea la carpeta del propio
  origen («El destino es la misma carpeta que el origen»); antes se habría escrito sobre
  el origen y un cortar lo habría perdido.
- **Textos.** `nautilus.cortar` y `nautilus.cortar_ayuda` en `menu.yaml` (y en
  `_TEXTO_DEFECTO` de la extensión / `_POR_DEFECTO` de `menu.py`).

**Comprobado el 16/11** con base de datos y carpetas temporales en `/tmp`:

- Mover un fichero de 4 MiB: `done`, hash idéntico, origen borrado y `mover = 1` en la BD.
- Mover una carpeta con subcarpeta: se copia el árbol, hashes correctos y desaparece la
  carpeta origen.
- Mover 8 MiB a **dos destinos**: los dos hashes correctos y el origen se borra una sola
  vez al final.
- Destino ausente (simulado con un fichero en su ruta): la copia queda en pausa y el
  origen sigue; cancelar tampoco lo borra.
- Cancelar a mitad de 200 MB: origen intacto y sin parcial en el destino.
- La marca `mover` se recupera con `cargar_historial()` tras reabrir el historial.
- Pegar en la misma carpeta se rechaza sin tocar el origen.
- Si el destino ya tenía el fichero completo, el movimiento lo da por bueno y borra el
  origen.
- IPC real (`"move": true`) con app aislada: un origen a 1 destino y otro a 2 destinos,
  ambos `done`, hashes correctos y los dos orígenes borrados.
- Extensión: el portapapeles distingue `cut`/`copy`, «Cortar con Copiex» recuerda la
  acción, tanto el pegado simple como el de N destinos envían `move`, y el menú devuelve
  las etiquetas «Copiar con Copiex» y «Cortar con Copiex».
- Migración sobre una copia del historial real: la columna `mover` se añade y todas las
  filas existentes se conservan.

No probado: mover desde/hacia MTP (no había móvil conectado al terminar) ni el clic real
en el menú de Nautilus (Wayland). Limitación heredada: una carpeta **vacía** sigue dando
«No hay nada que copiar», también al cortar.

## 3 septendecies. MTP: copiar hacia o desde el móvil (requerimiento 12, 16/11)

**Cómo se resolvió.** GIO ya monta los dispositivos MTP con `gvfsd-mtp` y, si está
`gvfs-fuse`, les da una ruta local. `util.uri_to_path()` acepta ahora `mtp://` y usa
`Gio.File.new_for_uri(uri).get_path()`; el resto del programa (motor, historial, ventana,
vigilante) sigue trabajando con rutas, sin reescribir el motor para GIO.

- **Ambos sentidos.** Origen MTP → destino local y origen local → destino MTP, también
  con MTP como uno de varios destinos (una sola lectura). La extensión de Nautilus acepta
  `mtp://` en el portapapeles y en la carpeta de destino; los diálogos de «Nueva copia»
  también ven los montajes MTP del selector de GTK.
- **Sin continuación por byte en MTP.** MTP no admite escritura aleatoria fiable, así que
  si hay un extremo MTP el fichero se rehace desde cero: se descuenta del progreso el
  parcial que hubiera (la barra no engaña) y se escribe con `wb`. Tampoco se usa
  `copy_file_range`; va por bloques de 1 MiB (lectura/escritura).
- **Rutas y textos.** La base de datos guarda la ruta de gvfs-fuse; `util.short_path()`
  la muestra como `mtp://Android_…/Almacenamiento interno compartido/…` (sin `%20`) en la
  ventana y en el vigilante. `es_mtp()` detecta esos montajes por `/gvfs/mtp:host=`.
- **Desconexión.** Si se va el teléfono, la ruta deja de existir: el destino queda en
  pausa «esperando la carpeta…» y el vigilante lo reanuda al volver, igual que un USB.
- **Requisito del sistema:** `gvfs-fuse` (paquete del mismo nombre, presente en Ubuntu).
  Sin él, `get_path()` devuelve `None` y el IPC responde con un error que lo explica.

**Comprobado el 16/11** con un Android conectado (`mtp://Android_Android_3a3f845/`),
base de datos y carpetas temporales en `/tmp`, en la carpeta `Copiex-prueba` del almacén
interno (creada para la prueba y borrada después):

- 4 MiB local → MTP: `done` en 0,9 s, tamaño correcto y SHA-256 idéntico; 4 MiB MTP →
  local: `done` en 0,5 s y hash idéntico.
- 5 MiB a dos destinos (local + MTP): `done`, los dos hashes correctos y `rchar` de
  5 242 985 bytes para 5 242 880 (una sola lectura).
- Pausa a 3 MiB escribiendo en MTP y reanudación: `done`, hash correcto.
- Cancelar a 1 MiB escribiendo en MTP: no queda el parcial.
- Origen MTP con un destino local parcial de 1 KiB: se rehace desde cero y el hash es
  correcto.
- Carpeta con subcarpeta (`carpeta/uno.bin` y `carpeta/sub/dos.bin`) en ambos sentidos:
  `done`, se crean las carpetas en MTP y los cuatro hashes coinciden.
- IPC completo (`copy` con `sources` MTP y destino `file://`): `{'ok': True}`, operación
  `done` y hash idéntico; el portapapeles de la extensión devuelve juntas las URIs
  `file://` y `mtp://`.

No probado con el cable desconectado físicamente (el vigilante usa la misma comprobación
que con un USB), con varios destinos MTP a la vez ni con el clic real en el menú de
Nautilus sobre una carpeta del teléfono; eso queda para la prueba del usuario.

## 3 undevicies. Paquete .deb con dependencias offline (16/11)

En `packaging/` hay un empaquetado completo que genera
`copiex_1.0.1_amd64.deb` en la raíz del proyecto (unos 122 MB: trae las
dependencias de Ubuntu 24.04 y de Ubuntu 26.04).

- **Instalación:** el `.deb` solo declara `Depends: python3`, así que `apt`/`dpkg`
  instalan Copiex aunque falten GTK, libadwaita, Nautilus o gvfs. La aplicación queda en
  `/opt/copiex`, con lanzador `/usr/bin/copiex`, escritorio, iconos, servicio D-Bus y
  extensión de Nautilus en `/usr/share/nautilus-python/extensions/copiex.py`.
- **Dependencias:** `packaging/deps.txt` lista los paquetes necesarios (con alternativas
  «a | b» para lo que cambia de nombre entre versiones, como
  `gir1.2-nautilus-4.1 | gir1.2-nautilus-4.0`); `resolver.py` calcula sus dependencias
  (2 niveles por defecto) y `build-deb.sh` descarga los `.deb` de **cada** versión de
  Ubuntu y deja un repositorio APT por versión en `/usr/share/copiex/offline/ubuntu-24.04`
  y `…/ubuntu-26.04` (182 y 183 paquetes, ~64 y ~60 MB). `COPIEX_SUITES="noble
  resolute"` elige qué suites se descargan (por defecto las dos LTS).
- **Versión de Ubuntu:** `packaging/plataforma.sh` (instalado en
  `/usr/lib/copiex/plataforma.sh`) detecta el sistema y lo usan el `postinst` y
  `instalar-dependencias`: 24.04 → repositorio de 24.04 y typelib
  `gir1.2-nautilus-4.0` (Nautilus 46, GTK 4.14, libadwaita 1.5); 26.04 →
  repositorio de 26.04 y typelib `gir1.2-nautilus-4.1` (Nautilus 50, GTK 4.22,
  libadwaita 1.8); otra versión → sin repositorio incluido, se resuelve por
  Internet con la typelib que ofrezca apt. Al terminar se comprueba la typelib y
  la versión de Nautilus, y queda en `/var/lib/copiex/entorno`. La detección se
  prueba con `COPIEX_OS_RELEASE=<fichero os-release>`.
- **Sin Internet:** el `postinst` lanza `/usr/lib/copiex/instalar-dependencias` en segundo
  plano (durante el postinst dpkg mantiene el candado), que añade una fuente temporal
  `file:/usr/share/copiex/offline/ubuntu-<versión del sistema>`, actualiza solo sus listas
  y instala lo que falte. Queda en `/var/log/copiex-dependencias.log`;
  `sudo copiex-dependencias` reintenta. Si el paquete no trae el repositorio de esa
  versión de Ubuntu, lo dice y remite a `sudo copiex-dependencias online`.
- **Con Internet:** si hay terminal interactiva y conexión, el `postinst` pregunta
  «¿Actualizar los paquetes necesarios desde Internet…? [S/n]». Si se acepta, el helper
  hace `apt-get update` e instala/actualiza los paquetes **directos** de `deps.txt`,
  dejando que apt los resuelva con los repositorios de la versión instalada (la lista
  completa incrustada es de otra serie y pediría paquetes incompatibles); si falla, cae al
  repositorio local. `COPIEX_ACTUALIZAR=si|no` evita la pregunta.
- **Migración:** si existía la extensión de usuario de `install.sh`, el `postinst` la
  renombra a `.guardada-por-copiex-deb` para que Nautilus no cargue dos Copiex y muestre
  el menú duplicado.
- **Actualizar:** `./upgrade.sh` actualiza las listas, actualiza las dependencias
  directas y las transitivas ya instaladas, reconstruye el `.deb` (descargando las
  versiones actuales de las 183 dependencias) y reinstala Copiex con `apt-get --reinstall`,
  aunque la versión no cambie. No se ejecuta con sudo. Después hay que reiniciar Nautilus
  (`nautilus -q`).
- **Construcción:** `./packaging/build-deb.sh` (necesita Internet y `dpkg-dev`).
  `COPIEX_DEPS_NIVEL`, `COPIEX_ARQ` y `COPIEX_SUITES` permiten cambiar niveles,
  arquitectura y versiones de Ubuntu incluidas. Cada suite usa listas de apt propias
  (`packaging/cache/apt-<suite>`), así se puede construir en 24.04 un paquete que sirve
  también en 26.04.
- **`install.sh` retirado:** el `.deb` cubre la instalación y `upgrade.sh` la actualización.
  `uninstall.sh` queda solo para limpiar instalaciones antiguas de usuario.

Comprobado el 16/11: `dpkg-deb -I` (control, `Depends: python3`, 183 `.deb`),
`apt-get -s install ./copiex_1.0.1_amd64.deb` (solo Copiex como paquete nuevo), la
importación del código extraído y `menu.yaml` desde `/opt/copiex`, y una simulación de
`apt-get update`/`install` contra el repositorio local. También se comprobó la sintaxis de
`upgrade.sh`/`uninstall.sh`/`build-deb.sh`, la resolución de las 183 dependencias,
`apt-get -s install --only-upgrade` y `--reinstall` del `.deb`, y se reconstruyó el paquete
real (60 MB, sha256 `f26bf90e…`). **No** se ha instalado de verdad (hace falta root) ni
probado en una máquina sin las dependencias; la pregunta interactiva tampoco se ha podido
ver con un `apt install` real. `upgrade.sh` no se ha ejecutado de extremo a extremo porque
actualiza paquetes del sistema y requiere root.

Limitaciones: el repositorio es específico de la arquitectura; lleva dependencias offline
de Ubuntu 24.04 y 26.04, y en otra versión de Ubuntu el paquete se instala pero resuelve
sus dependencias por Internet. `menu.yaml` en `/opt` lo gestiona el paquete y una
actualización puede reemplazarlo.

## 3 vicies. `upgrade.sh`, `.gitignore` y publicación (16/11)

Se retiró `install.sh`: el `.deb` es ahora la única instalación soportada. `uninstall.sh`
se conserva para limpiar instalaciones antiguas de usuario; avisa si detecta el paquete
`.deb` y recuerda que se quita con `sudo apt remove copiex`.

**`upgrade.sh`** (raíz, ejecutable, sin `sudo`):

1. `apt-get update` con `DEBIAN_FRONTEND=noninteractive`;
2. resuelve el cierre de dependencias (`resolver.py`, 2 niveles por defecto) y ejecuta
   `apt-get install --only-upgrade` sobre las ya instaladas; después instala/actualiza las
   directas de `packaging/deps.txt`;
3. ejecuta `packaging/build-deb.sh`, que descarga las versiones actuales de las 183
   dependencias y reconstruye `copiex_1.0.1_amd64.deb`;
4. instala el `.deb` con `--reinstall` si ya estaba instalado (la versión no cambia), con
   `COPIEX_ACTUALIZAR=no` para que el `postinst` no vuelva a preguntar;
5. avisa si Copiex está abierto y de que hay que reiniciar Nautilus (`nautilus -q`).

Se creó **`.gitignore`** con `copiex_*.deb`, `packaging/build/` y `packaging/cache/`,
para no versionar el binario de 60 MB ni las descargas temporales. Comprobado con
`git check-ignore`.

Publicación: commit **`ce8d9ee`** «Empaquetar Copiex como .deb y añadir upgrade.sh»,
push correcto `ff317f2..ce8d9ee` a `repo-copiex/main`. Se comprobó la sintaxis de los
scripts, la resolución de 183 paquetes, las simulaciones de `apt-get install
--only-upgrade` y `--reinstall`, y la reconstrucción real del `.deb`. No se ejecutó
`upgrade.sh` completo (root + cambios en el sistema) ni se probó la instalación real del
`.deb`.

## 3 unvicies. Reanudación de N destinos tras un kill (17/11)

**Síntoma.** Una copia a un solo destino se reanudaba sola al volver a arrancar Copiex
tras un kill; una copia a varios destinos no.

**Causa.** Cuando una copia venía del historial (su hilo ya no existía), `Motor.reanudar()`
entraba en la rama que arranca un hilo nuevo, pero **no llamaba a `_persistir_estado()`**.
Si el usuario reanudaba manualmente esa copia y luego mataba Copiex, SQLite conservaba
`pausa_manual=1` aunque la pausa ya se había deshecho. Al siguiente arranque el vigilante
la ignoraba (`op.pausa_manual`), así que no se reanudaba; en el caso de un solo destino
esa combinación no se había dado.

**Arreglo** (`copiex/engine.py`, `Motor.reanudar`): antes de `op.iniciar(reanudando=True)`
se llama a `op._persistir_estado()`, que guarda `estado=running`, `pausa_manual=0` y el
estado de cada destino. Así un kill posterior deja el historial en un estado que el
vigilante puede recuperar.

**Comprobado** con base de datos y carpetas temporales (sin tocar el historial real):

- Copia de 2 GB a **dos destinos**, pausa manual y `kill -9`.
- Arranque nuevo: recuperada en `paused`, `pausa_manual=1`.
- `Motor.reanudar()`: la fila pasa a `running` y `pausa_manual=0` inmediatamente.
- Segundo `kill -9`; nuevo arranque: recuperada en `paused`, `pausa_manual=False`, dos
destinos y `Vigilante._motivo_espera()` devuelve `''` (puede continuar).
- `Motor.reanudar()` vuelve a arrancar la copia.
- También se repitió el caso de kill directo (sin pausa manual) con dos destinos: sigue
  reanudándose automáticamente y termina con los dos destinos en `done`.

**Confirmado por el usuario** el 17/11 desde el flujo real de Nautilus: el pegado a varios
destinos se reanuda automáticamente tras matar y volver a arrancar Copiex. Se publicó en
el commit de esta corrección.

## 3 duovicies. Selector de idioma español/inglés (17/11)

Nuevo requerimiento 13: toda la interfaz debe poder cambiar entre español e inglés,
incluidas las entradas de Copiex en el menú de Nautilus.

- **Selector:** submenú «Idioma» → «Español» / «Inglés» en español, o «Language» →
  «Spanish» / «English» en inglés, en el menú del Centinela y en el menú de tres rayas de
  la ventana. En la bandeja se marcan con radio; en la ventana son dos acciones
  (`app.idioma_es` y `app.idioma_en`).
- **Persistencia:** `copiex/menu.py` guarda la elección en
  `~/.config/copiex/language` (texto `es` o `en`) mediante fichero temporal +
  `os.replace`; `COPIEX_LANGUAGE` la fuerza en pruebas. Si no existe, se usa español.
- **Textos:** `menu.yaml` conserva el español en la raíz y añade la sección `en:` con las
  mismas claves; `texto()` busca primero inglés y cae al español si falta una traducción.
  `formato()` rellena los placeholders del estado (progreso, pausa, completada, etc.).
- **Nautilus:** la extensión no puede importar el paquete, así que duplica un lector mínimo
  de `menu.yaml` y lee `~/.config/copiex/language` **cada vez que construye el menú**. Como
  Nautilus solo pide los ítems cuando cambia la selección o la vista (no al abrir el menú),
  la extensión vigila la carpeta de configuración con un `Gio.FileMonitor` y, cuando el
  idioma cambia de verdad, llama a `emit_items_updated_signal()` para que Nautilus vuelva a
  pedirlos: la **siguiente** apertura del menú contextual ya sale traducida, sin reiniciar
  el gestor. El menú que esté abierto en ese momento no se reconstruye (Nautilus no expone
  API para eso). Si no existe la preferencia, usa español.
- **Ventana:** al cambiar de idioma se destruye y reconstruye la ventana para refrescar
  también las filas y los botones; si estaba oculta, se descarta y se crea de nuevo al
  mostrarla. El menú del Centinela se refresca con `LayoutUpdated`.

**Comprobado** el 17/11 con datos y configuración temporales:

- `menu.yaml` tiene todas las claves en español e inglés; `texto("menu.nueva")` pasa de
  «Nueva copia» a «New copy» y `nautilus.copiar` a «Copy with Copiex».
- La ventana GTK real arranca en español, se cambia a inglés, se reconstruye y contiene
  «New copy» y «Copy history».
- El menú D-Bus del Centinela devuelve el submenú `Idioma` con `Español`/`Inglés` y el
  estado radio correcto.
- La extensión de Nautilus lee el fichero de idioma y devuelve «Copy with Copiex» y
  «Paste with Copiex to N destinations» sin variables de entorno.
- El monitor de la extensión emite «items-updated» una sola vez al pasar de `es` a `en`
  (y otra al volver), no al reescribir el mismo idioma; con él, las etiquetas pasan de
  «Copy with Copiex» a «Copiar con Copiex» sin reiniciar Nautilus.

**Confirmado por el usuario** el 17/11 desde Nautilus: tras cambiar el idioma en Copiex, el
menú contextual sale en el idioma elegido en la siguiente apertura, sin reiniciar el gestor.

El motivo de que antes «no llegara» el cambio era que Nautilus cargaba una copia **antigua**
de la extensión en `~/.local/share/nautilus-python/extensions/copiex.py` (35 299 B, MD5
`54118ea3…`, sin el monitor de idioma). Se sustituyó por la del repositorio (MD5
`91d1929c699b48c35b3522649672763a`) y desde entonces ambos ficheros coinciden; conviene
comprobarlo con `md5sum` cada vez que se toque `copiex/nautilus_extension.py`. No se ha
hecho clic real en el submenú de idioma del panel (Wayland).

## 3 tervicies. Idioma inicial detectado al instalar el .deb (18/11)

Nuevo requerimiento 14: al instalarse, la aplicación debe tomar el idioma de la interfaz
GNOME — español si GNOME está en español, inglés si está en cualquier otro idioma — y el
usuario lo puede cambiar después desde el menú «Idioma», como ya funcionaba.

- **Helper:** `packaging/initial-language <casa>` (se instala en
  `/usr/lib/copiex/initial-language`). Si el fichero `~/.config/copiex/language` ya existe
  con `es` o `en`, **sale sin tocar nada** (reinstalar con `./upgrade.sh` no pisa la
  elección del usuario); si existe con otra cosa, lo reescribe. Escribe el fichero con
  `es`/`en` y lo deja del dueño de la casa (`chown`), porque el `postinst` corre como root.
- **Pistas, en orden:** `Language=` de `AccountsService`
  (`/var/lib/AccountsService/users/<usuario>`, lo que se elige en Ajustes → Región e
  idioma), `~/.config/user-dirs.locale`, `LC_ALL`/`LC_MESSAGES`/`LANG`/`LANGUAGE` del
  proceso (descartando `C`, `POSIX` y `C.UTF-8`, que `apt` arrastra aunque la sesión esté
  en español), `/etc/default/locale`, `/etc/locale.conf` y `localectl status`. Cuenta como
  español cualquier código que empiece por `es` (`es`, `es_ES.UTF-8`, `es-MX`); sin pistas
  se pone `en`. `COPIEX_ACCOUNTS_DIR` permite apuntar a otra carpeta de cuentas en pruebas.
- **`postinst`:** recorre `/home/*` (el mismo bucle que aparta la extensión antigua) y
  escribe una línea con el idioma elegido por usuario.
- **`build-deb.sh`:** instala el helper junto a `instalar-dependencias` y el
  `README.Debian` explica el comportamiento.
- **Diseño:** no se cambió el valor por defecto del código (`menu.py` sigue usando español
  cuando no hay fichero), porque el requisito es del proceso de instalación; un arranque
  desde el repositorio (sin `.deb`) se comporta como antes.

**Comprobado** el 18/11 con casas temporales en `/tmp` (nada del sistema modificado):

- Sin `AccountsService`, `LANG=de_DE.UTF-8` → `en`; `LANG=es_ES.UTF-8`, `es_MX.UTF-8` y
  `LANGUAGE=es:en` → `es`.
- `AccountsService` manda sobre el entorno: `Language=es_ES.UTF-8` con `LANG=en_US.UTF-8`
  → `es`; `Language=en_GB.UTF-8` o `fr_FR.UTF-8` con `LANG=es_ES.UTF-8` → `en`.
- `~/.config/user-dirs.locale` con `es_ES` → `es` cuando no hay cuentas.
- Fichero ya elegido (`en` con sistema en español, `es` con sistema en inglés): no se
  reescribe y el helper no imprime nada.
- Fichero con contenido inválido (`xx`) → se reescribe con el idioma detectado.
- Casa inexistente → sale con 0 y sin escribir. Propietario del fichero correcto.
- `sh -n` del helper y del `postinst`, `bash -n` de `build-deb.sh` y `git diff --check`.

**No probado:** no se reconstruyó el `.deb` (descarga 60 MB de dependencias) ni se realizó
una instalación real con `apt`; `upgrade.sh` hará esa comprobación cuando el usuario lo
ejecute. En este equipo no hay `.deb` instalado, así que el idioma real no cambió.

## 3 quatervicies. Varios destinos desde la ventana principal (18/11)

«Pegar con Copiex N destinos» ya no exige Nautilus: el botón «Nueva copia» de la
ventana abre, después del selector de carpeta, el diálogo «Destinos de la copia».

- **Flujo.** «Nueva copia» → orígenes (selección múltiple) → carpeta de destino (selector
  nativo; es el primer destino) → diálogo con la lista de destinos, «Añadir otra carpeta»
  (selector nativo por cada una; no repite carpetas) y «Comenzar la copia». Cerrar el
  diálogo cancela y «Comenzar la copia» queda desactivado si se quitan todas las carpetas.
- **Mismo motor.** El diálogo entrega la lista completa a `Aplicacion.crear_copia`, así que
  la copia lee el origen una sola vez, la ventana muestra una línea por destino y
  pausar/cancelar/reanudar valen para todos. No hay ninguna ruta nueva en `engine.py`.
- **Código.** `copiex/destinations.py` (`DialogoDestinos`, `Adw.Window` modal transient de
  la ventana principal, tope de 16 destinos como en Nautilus, quitar con el botón de la
  fila). En `copiex/app.py` solo cambia `_destino_elegido`, que ahora abre el diálogo en
  vez de llamar a `crear_copia` con una carpeta. El diálogo se guarda en `_ABIERTOS`
  (module-level) mientras está abierto, para que el recolector no lo destruya.
- **Textos.** Claves nuevas en la sección `dialogos` de `menu.yaml` (y en
  `_POR_DEFECTO`/`_POR_DEFECTO_EN`): `destinos_titulo`, `destinos_ayuda`,
  `anadir_destino`, `empezar_copia`, `elegir_destino_titulo`, `quitar_destino`,
  `sin_destinos`.

**Comprobado** el 18/11 con `XDG_CONFIG_HOME` temporal, `python3 -m py_compile
copiex/*.py` y una instancia del diálogo creada sobre el backend X11 **sin presentar la
ventana** (no se abrió nada en el escritorio del usuario):

- Diálogo con la primera carpeta: título «Destinos de la copia», `modal=True`, «Comenzar
  la copia» activo y etiquetas leídas del YAML («Comenzar la copia» / «Añadir otra
  carpeta»).
- Añadir y quitar: dos destinos → dos filas; quitar el último → 0 filas, aviso «Añade al
  menos una carpeta de destino» visible y «Comenzar la copia» desactivado.
- Pulsar «Comenzar la copia» cierra el diálogo y llama al callback con los orígenes y la
  lista completa de destinos.
- Textos en inglés con `language` = `en` («Copy destinations», «Start copying», …).

**No probado:** no se ha recorrido a mano el diálogo real (selectores nativos de carpeta,
botones con ratón) ni se ha lanzado una copia real a dos carpetas desde la ventana; el
motor de varios destinos sí estaba probado desde el 13/11 (3 quindecies).

## 3 quinvices. Tiempo restante realista y estable (requerimiento 15, 23/11)

Antes, cada refresco hacía `falta / velocidad` con una media exponencial de alfa 0,4 que se
recalculaba cada 0,5 s: un bloque lento, un pico de caché o una espera corta del disco
movían la velocidad y la cifra «quedan …» cambiaba de un refresco a otro (cientos de veces
en una copia larga).

- **Velocidad por ventana.** `Operacion._velocidad()` guarda muestras
  `(instante, copiados)` y mide los bytes/s sobre los últimos `VENTANA_VELOCIDAD = 15 s`;
  después suaviza esa medida con una media exponencial de constante
  `SUAVIZADO_VELOCIDAD = 15 s`. Los picos se reparten en vez de marcar el ritmo.
- **Sin estimación prematura.** No hay restante hasta tener `MINIMO_MUESTRA_VELOCIDAD = 4 s`
  de historia. Si el progreso baja (un destino borrado y reintentado) la medida se
  reinicia, y si hay un hueco mayor que la ventana (el dispositivo dejó de responder)
  también, en vez de arrastrar segundos sin copiar.
- **Histéresis.** `Operacion.restante` solo acepta una cifra nueva si se separa de la
  mostrada al menos `CAMBIO_MINIMO_RESTANTE = 5 s` o el 10 %, y como mucho una vez cada
  `INTERVALO_MINIMO_RESTANTE = 3 s`; además se refresca sola cada
  `REFRESCO_MAXIMO_RESTANTE = 30 s` para no quedarse obsoleta. Reanudar llama a
  `_reiniciar_medida()`: una pausa larga no contamina la media.
- **Sin cambios de interfaz.** Se sigue mostrando «quedan …» con `ventana.quedan` y
  `fmt_restante`; no hay claves nuevas en `menu.yaml`.

**Comprobado el 23/11** con un banco del motor sin GTK, reloj simulado y una copia de
100 MiB repartida en 30 s, con dos patrones de velocidad (seno de ±25 % cada 2 s y paseo
aleatorio de ±3 % cada 0,1 s):

- El cálculo anterior (media exponencial de alfa 0,4) cambiaba la cifra **232 veces** en
  30 s; el actual, **7** con el seno y **6** con el paseo aleatorio.
- El mayor salto entre dos cifras mostradas baja a unos 11 s (seno) y 6 s (paseo), y no
  hay estimación durante los primeros 4 s (aparece en cuanto la ventana se llena, en
  torno a los 4-5 s).
- Reanudar deja el restante en `None`, la velocidad a 0 y la ventana vacía.
- `python3 -m py_compile copiex/*.py` sin errores.

**No probado:** una copia real con el reloj de verdad no llega a mostrar el restante en
este equipo (el NVMe copia más rápido que la ventana mínima de 4 s); la comprobación es
del cálculo con reloj simulado, no de una copia lenta real.

## 3 sexvicies. «Cortar» dentro de la misma partición: renombrar (requerimiento 16, 23/11)

«Cortar con Copiex» copiaba siempre, y solo al terminar borraba los orígenes. Dentro de la
misma partición eso era trabajo inútil: mover un fichero en su propio sistema de ficheros
es cambiar el nombre de su entrada en el directorio, algo instantáneo aunque el fichero
pese gigabytes.

- **Dónde.** `Operacion._mover_directo()` se ejecuta al principio de `_trabajar_seguro()`,
  antes de `_planificar()`, y hace `os.rename()` de cada origen.
- **Cuándo.** Solo con `mover=True`, **un** destino, sin MTP, con todos los orígenes
  presentes, en el mismo `st_dev` que la carpeta destino y sin que exista ya algo con ese
  nombre en el destino. Si algo no se cumple, devuelve `False` y la operación sigue igual
  que antes: copia y borra.
- **Todo o nada.** Las condiciones se comprueban antes de tocar nada. Si un `os.rename`
  falla a mitad (permisos, por ejemplo) se deshace lo ya renombrado y se pasa al camino de
  copia; si ni siquiera se puede deshacer, la fila queda en `error` con el motivo.
- **Progreso e historial.** Antes de renombrar se miden bytes y ficheros de los orígenes
  (`_medir_origen()`, un `os.walk` con `lstat`, sin leer datos) para que la fila y la tabla
  `destinos` queden completas (`done`, `copiados == total`). Suena la alerta como en
  cualquier copia terminada.
- **Enlaces simbólicos.** Se mira `os.lstat()`, que da el dispositivo de la carpeta que
  contiene el enlace: `os.rename` mueve el enlace, no su destino.
- **Carpetas vacías.** Un «Cortar» de una carpeta vacía ahora funciona al instante; antes
  daba «No hay nada que copiar», porque el plan de copia no tenía ficheros.
- **Sin cambios de interfaz.** No hay textos nuevos: se reutilizan los estados de siempre.

**Comprobado el 23/11** con base de datos y carpetas temporales en `/tmp` (misma partición)
y en `/dev/shm` (otra):

- Mover un fichero de **512 MiB** en la misma partición: `done` en **0,001 s**, **mismo
  inodo** en el destino, origen borrado, `mover = 1` y el destino `done` con
  `copiados == total_bytes` en la BD.
- Mover una carpeta con subcarpeta: mismo inodo, contenido intacto y origen borrado.
- Nombre ya ocupado en el destino: cae al camino de copia (inodo distinto), hash correcto y
  origen borrado.
- Origen en `/tmp` y destino en `/dev/shm` (dispositivos distintos): copia normal, hash
  correcto, inodo distinto y origen borrado.
- Carpeta vacía: se mueve al instante y desaparece el origen.
- Copia normal (`mover=False`): el origen sigue y el hash coincide, sin cambios.
- `python3 -m py_compile copiex/*.py` sin errores.

**Limitaciones conocidas:** con un nombre ya ocupado se conserva el comportamiento viejo
(si el fichero del destino es más corto, la copia continúa desde su tamaño, como cualquier
reanudación); y mover hacia/desde MTP o a varios destinos sigue copiando, porque ahí no
hay un único renombrado posible.

## 4. Pendientes, por orden sugerido

No hay trabajo pendiente del pliego. Los requerimientos 15 (tiempo restante) y 16 (mover
renombrando en la misma partición) quedaron implementados y comprobados en banco el 23/11
(3 quinvices y 3 sexvicies). El usuario confirmó el 17/11 el
menú real de Nautilus
(cortar a uno y a varios destinos y cambio de idioma); queda confirmar que el icono del
panel se ve bien en 24.04 (los tres puntos se arreglaron el 19/11 con `IconPixmap`, ver el
final de 3 quaterdecies), probar el idioma inicial con una instalación real del `.deb` (3
tervicies) y, si se quiere afinar, mover carpetas vacías y mover hacia/desde MTP.

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
- **Desinstalar:** el `.deb` con `sudo apt remove copiex`; una instalación antigua de
  usuario con `./uninstall.sh` (pregunta; `--simular` para ver antes lo que borraría,
  `--conservar-datos` para quedarse con historial y registros).
- **Instalar cambios de la extensión:** `./upgrade.sh` reconstruye e instala el `.deb`
  (copia la extensión a `/usr/share/nautilus-python/extensions/copiex.py`). Después hay
  que reiniciar Nautilus (`nautilus -q`) o no se recarga.
- **Sin `.deb` (este equipo):** la extensión que carga Nautilus es la copia de usuario
  `~/.local/share/nautilus-python/extensions/copiex.py`, no la del repositorio. Tras editar
  `copiex/nautilus_extension.py`, cópiala a mano con `cp`, borra el `__pycache__` de esa
  carpeta, `nautilus -q` y compara `md5sum` de los dos ficheros. Una copia vieja ahí fue la
  causa de que el cambio de idioma pareciera no funcionar el 17/11.
- **Servicio D-Bus:** lo instala el `.deb` en
  `/usr/share/dbus-1/services/com.copiex.Manager.service`; es lo que permite que la
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
  Las URIs pueden ser `file://` o `mtp://`.
- **MTP:** depende de `gvfs-fuse`; comprobar con `ls /run/user/1000/gvfs` y
  `gio mount -l`. La ruta `/run/user/<uid>/gvfs/mtp:host=…` es la que usa el motor, pero
  en la interfaz se muestra como `mtp://…`. No intentes reanudar por byte un fichero en
  MTP: el motor lo rehace a propósito. Si el móvil se desconecta, la carpeta desaparece y
  la copia queda en pausa esperando, como un USB.
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
Wayland. El 16/11 había un Android montado por MTP (`gvfsd-mtp` y `gvfs-fuse` 1.60). El proyecto **es un repositorio git** (rama `main`; último commit publicado **`4ab3f99`**
«Anotar el arreglo del icono de la bandeja en la documentación»; remoto `repo-copiex` en
GitHub). Los commits incluyen el trabajo del 13,
14, 16 y 17/11 (motor de varios destinos, MTP, «Cortar», icono de bandeja, extensión sin
hilos, `menu.yaml`, `upgrade.sh`, `.gitignore`, la retirada de `install.sh`, el arreglo de
reanudación y el selector de idioma). El aviso a Nautilus del cambio de idioma va en el
commit de esta corrección; el `.deb` no se versiona.
Historial real al retomar: **43 filas** y 21 filas en `destinos`. La app **no está en
marcha**; se arranca con `./copiex-launcher --bandeja` (o la activa Nautilus) y el PID
cambia, comprobar con `ps -eo pid,args | grep "[p]ython3 -m copiex"`. Nautilus está
recargado (`nautilus -q`) con la extensión idéntica a la fuente. Los `.pyc` de
`copiex/__pycache__/` se colaron en el commit `ee884ac`; no aportan nada y conviene
sacarlos del control de versiones. **Aviso de seguridad:** la URL del remoto guarda un
token de GitHub incrustado en `.git/config`; conviene rotarlo y usar un ayudante de
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
- **Cortar (mover):** `Motor.crear(origenes, destinos, mover=True)` copia y borra los
  orígenes al terminar; comprobar que el destino tiene el SHA-256 correcto, que el origen
  ya no existe y que `store.obtener(op.id)["mover"] == 1`. Con dos destinos, el origen
  debe desaparecer solo cuando ambos estén `done`. Cancelar o simular un destino ausente
  debe dejar el origen intacto. Por IPC: `{"cmd":"copy","sources":[…],"dests":[…],"move":true}`.
- **Cortar en la misma partición (renombrado):** anotar `os.stat(origen).st_ino`, mover un
  fichero grande de `/tmp/a` a `/tmp/b` con `mover=True` y comprobar que termina en
  milisegundos, que el inodo del destino es el mismo, que el origen ya no existe y que
  `copiados == total_bytes`. Para ver el camino de copia, repetir con el destino en
  `/dev/shm`: el inodo cambia y el SHA-256 debe coincidir. Si el destino ya tiene un
  fichero con ese nombre, también se copia (y se borra el origen) en vez de renombrar.
- **MTP:** `uri_to_path("mtp://…")` da la ruta de gvfs-fuse; con un Android conectado,
  crear una carpeta temporal en `Almacenamiento interno compartido` (o similar), copiar
  en ambos sentidos con `Motor.crear`, comprobar SHA-256 y borrarla al terminar. MTP no
  continúa parciales: pausar y reanudar debe rehacer el fichero y acabar con el hash
  correcto. Para el IPC, `{"sources": ["mtp://…"], "dests": ["file:///tmp/…"]}`.
- **Regla de oro:** cualquier callback pasado a `GLib.idle_add` debe devolver `False`
  (ver sección 3).
