# Copiex — instrucciones para agentes

Gestor de copias en Python + PyGObject (GTK 4 / libadwaita) para GNOME: icono de bandeja,
extensión de Nautilus, historial en SQLite, pausa/cancelación, continuación por byte y
reanudación automática. Una copia puede repartirse a **varios destinos** leyendo el origen
una sola vez (`Operacion.destinos`, `_copiar_a_varios`). **Los ficheros y carpetas llevan
nombres en inglés** (`sound.py`, `watcher.py`, `nautilus_extension.py`, `copiex-launcher`,
`sounds/`, `icons/`); las clases, funciones y atributos internos siguen en español
(`Vigilante`, `cargar()`, `texto()`).

**Antes de tocar nada, lee `TODO.md`** (estado real, requerimiento por requerimiento,
trampas y recetas de prueba) y `NOTES.md` (pliego vigente: 16 requerimientos y 4 errores;
los de workers se retiraron el 13/11, el 12 (MTP) se añadió el 16/11, el 14 (idioma
inicial al instalar) el 18/11, el 15 (tiempo restante estable) el 23/11 y el 16 (mover
renombrando en la misma partición) el 23/11).

## Trabajo pendiente

Los 16 requerimientos del pliego están hechos (el 12 es MTP, añadido el 16/11; el 13 es
el selector de idioma, añadido el 17/11; el 14 es el idioma inicial según GNOME al
instalar el `.deb`, añadido el 18/11; el 15 es el tiempo restante realista y estable y el
16 es el «Cortar» instantáneo dentro de la misma partición, ambos del 23/11), el error 3
(muchos ficheros) está medido y
mejorado, y «Cortar con Copiex» mueve de verdad desde el 16/11. El empaquetado `.deb` y
`upgrade.sh` están terminados, publicados y documentados en `TODO.md` (3 undevicies y
3 vicies). El selector de idioma está en la sección 3 duovicies, el idioma inicial al
instalar en la 3 tervicies y el diálogo de varios destinos del botón «Nueva copia» en la
3 quatervicies. Todo está publicado en `repo-copiex/main` y el árbol queda limpio.

**Estado al 23/11/2026:** el **selector de idioma español/inglés** se publicó en
**`fc04da6`** «Idioma inglés» (`repo-copiex/main`). El aviso a Nautilus
(`Gio.FileMonitor` sobre `~/.config/copiex` + `emit_items_updated_signal()`) se publicó
en **`cca1b2c`**. El 23/11 se publicaron **`26a6873`** «Publicar el icono de la bandeja
como mapa de bits» (con `librsvg2-common`) y **`273ae03`** «Copiex 1.0.1: mover dentro de
la misma partición y arreglar el empaquetado» (requerimientos 15 y 16 y el arreglo del
`apt.conf` del build), y el árbol queda limpio. El proyecto es **GPL-3.0** desde ese día
(`LICENSE`, `517b76e`). El `.deb` (`copiex_1.0.1_amd64.deb`, 127 MB) está ignorado por Git.
La app **no está arrancada** al retomar: `./copiex-launcher --bandeja`.
Historial real: 43 filas y 21 en `destinos`. «Cortar» y el cambio de idioma en el menú real
de Nautilus están confirmados por el usuario; falta confirmar el icono verde en el panel.

## Reglas que no se negocian

- **Los textos de la interfaz viven en `menu.yaml`** (raíz), no en el código: nombres de
  opciones y textos de ventanas emergentes. Se leen con `texto("seccion.clave")` de
  `copiex/menu.py`; si añades una clave, añádela también a `_POR_DEFECTO` y
  `_POR_DEFECTO_EN` en ese módulo y a las dos secciones del YAML. Un cambio en el YAML exige
  **reiniciar la app**; la extensión (fichero suelto) lleva su propio lector de la sección
  `nautilus:` y de `en.nautilus:` y exige instalar el `.deb` (`./upgrade.sh`) + `nautilus -q`.
- **Idioma inicial:** lo escribe el `postinst` del `.deb` con
  `packaging/initial-language` (instalado en `/usr/lib/copiex/initial-language`), una vez
  por cada carpeta de `/home`: `es` si la interfaz GNOME está en español (lo manda
  `Language=` de `AccountsService`, luego `user-dirs.locale`, el entorno y el idioma del
  sistema) y `en` en cualquier otro caso. **No pisa una elección previa** (si el fichero
  ya dice `es` o `en`, no lo toca), así que reinstalar con `./upgrade.sh` respeta lo que
  el usuario eligió. No metas ese valor por defecto en el código: sin fichero, `menu.py`
  sigue usando español.
- **Idioma:** el selector guarda `es`/`en` en `~/.config/copiex/language`; la extensión lee
  ese fichero al construir el menú y, como Nautilus solo pide los ítems al cambiar la
  selección o la vista, vigila esa carpeta con un `Gio.FileMonitor` y emite
  `emit_items_updated_signal()` para que los vuelva a pedir. Las etiquetas cambian en la
  siguiente apertura del menú, sin reiniciar Nautilus. No dupliques textos en el código:
  usa `texto()`/`formato()` y el YAML.
- **Nautilus carga la copia instalada, no el fichero del repo.** En este equipo (sin `.deb`)
  es `~/.local/share/nautilus-python/extensions/copiex.py`; con el `.deb`,
  `/usr/share/nautilus-python/extensions/copiex.py`. Si editas
  `copiex/nautilus_extension.py` y no actualizas esa copia, Nautilus sigue con la versión
  vieja y parece que el arreglo no funciona (pasó el 17/11 con el aviso de idioma):
  `cp copiex/nautilus_extension.py ~/.local/share/nautilus-python/extensions/copiex.py`,
  `nautilus -q` y comprueba con `md5sum` que coinciden. Basta borrar el `__pycache__`
  antiguo de esa carpeta si el módulo compilado es más nuevo.
- **Si el menú de Nautilus no hace nada:** mira `~/.local/share/copiex/extension.log`
  (traza de copiar/pegar, MIME leído y respuesta de la app); los `print` de la
  extensión se pierden.
- **No reintroduzcas los workers/hilos de copia** (se retiraron del pliego el 13/11): se
  midieron, no mejoraban el tiempo y el usuario pidió retirarlos. Ver «3 quinquies» en
  `TODO.md`. La extensión de Nautilus tampoco usa hilos desde el 14/11: envía con `_Envio`
  (callbacks de `GLib.io_add_watch`) y arranca la app por D-Bus. No vuelvas a un
  `threading.Thread` ni a `subprocess.Popen` desde el menú.
- Todo callback pasado a `GLib.idle_add` debe devolver `False`; si no, la acción se repite
  en bucle (ya pasó con las copias duplicadas).
- Nunca hagas `os.path.exists`/`isdir` sobre rutas de usuario en el hilo de GTK: un
  dispositivo que no responde congela la ventana. Esas comprobaciones van en el hilo de copia.
- No uses `pkill -f "python3 -m copiex"`: mata al propio shell. Localiza el PID con
  `ps -eo pid,args | grep "[p]ython3 -m copiex"` y mátalo por PID.
- Prueba siempre con base de datos y `XDG_CONFIG_HOME` temporales en `/tmp`; no toques el
  historial real de `~/.local/share/copiex/historial.db`.
- **Varios destinos:** la carpeta donde se pulsa «Pegar con Copiex N destinos» es siempre
  el primer destino; los demás se añaden en la ventana de selección. El progreso de la
  operación es el mínimo de los destinos (no la suma) y el de cada destino vive en la tabla
  `destinos`. Desde el 18/11 la ventana principal crea las mismas operaciones con el botón
  «Nueva copia»: la carpeta elegida en el selector es el primer destino y
  `copiex/destinations.py` añade los demás antes de empezar.
- **Licencia:** el proyecto es **GPL-3.0** desde el 23/11/2026 (`LICENSE`, añadido desde
  la web de GitHub en `517b76e`). No la cambies ni borres el fichero. El `copyright` que
  genera `build-deb.sh` aún dice «la misma licencia que el proyecto Copiex»; nombrar allí
  GPL-3.0 (y quizá incluir `LICENSE` en `/usr/share/doc/copiex/`) queda pendiente.
- **Git:** el proyecto tiene repositorio (remoto `repo-copiex` en GitHub). **No hagas
  commit ni push** salvo que el usuario lo pida; y avísale de que la URL del remoto lleva un
  token incrustado en `.git/config`, que debería rotar. Los `__pycache__/*.pyc` no se
  versionan (`.gitignore` los excluye desde el 18/11); no los vuelvas a añadir.

## Diagnóstico

`~/.local/share/copiex/copiex.log` es el fichero que el usuario envía cuando algo falla:
se escribe en DEBUG, conserva **una semana** (poda al arrancar y cada hora, tope 32 MiB) e
incluye las acciones de Nautilus como `Nautilus: …`. `extension.log` solo recoge lo que
pasa cuando la aplicación no está arrancada. El envío sin hilos deja las etapas
`enviando <cmd>...`, `Copiex no está abierto; se pide al bus que lo arranque`,
`enviado <cmd> en X s -> {...}` o `sin contacto con Copiex (<cmd>): ...`. El diseño está en
`copiex/logs.py` y en la sección «3 octies» de `TODO.md`.

## Comandos

```bash
./copiex-launcher                      # abre la ventana
./copiex-launcher --bandeja            # solo bandeja (sin ventana)
./upgrade.sh                          # actualiza deps, reconstruye el .deb y reinstala Copiex
./packaging/build-deb.sh              # crea copiex_<versión>_<arq>.deb con deps offline
sudo apt remove copiex                 # desinstala el paquete .deb
./uninstall.sh --simular              # limpieza de una instalación antigua (simulación)
./uninstall.sh                        # limpieza de usuario antigua (pregunta; --conservar-datos/--si)
python3 -m py_compile copiex/*.py      # comprobación rápida
```

Lanzar la GUI desde un terminal sin bloquear:

```bash
( setsid nohup ./copiex-launcher >/tmp/copiex-app.log 2>&1 </dev/null & ) >/dev/null 2>&1
```

## Nombres

- **Centinela**: el icono de la esquina superior derecha (`copiex/tray.py`, clase `Bandeja`).
- **Vigilante**: el hilo que reanuda copias solo (`copiex/watcher.py`). No son lo mismo.

## Mapa rápido

- `menu.yaml` + `copiex/menu.py`: todos los textos de menús y ventanas emergentes en
  español (raíz) e inglés (`en:`), lector YAML propio con caché, reserva y preferencia en
  `~/.config/copiex/language`. Cambiar el YAML exige reiniciar la app; cambiar de idioma
  desde el menú es inmediato en Copiex y en la siguiente apertura del menú de Nautilus.
- `sounds/`: audio de la alarma (`copy-finished.*` manda) y `README.md` con las reglas;
  `copiex/sound.py` lo reproduce. Cambiar el sonido no exige reiniciar.
- `icons/`: icono propio a color (la «C» blanca sobre verde, que es el que usa también
  la bandeja) y variante simbólica. `brand/`: propuestas descartadas y la galería
  `preview.html` con la que se eligió.
- `copiex/window.py`: además del historial, la cabecera lleva el icono a 22 px justo
  después del título «Copiex» (`Gtk.Box` con `Adw.WindowTitle` + `Gtk.Image`).
- `copiex/destinations.py`: diálogo «Destinos de la copia» que abre el botón «Nueva copia»
  tras elegir la primera carpeta; añade más destinos y entrega la lista a
  `crear_copia` (mismo motor que «Pegar con Copiex N destinos» de Nautilus).
- `copiex/util.py`: rutas y `icono_disponible()` (icono propio o `edit-copy`).
  `uri_to_path()` acepta `file://` y `mtp://` (este último se resuelve con GIO a la ruta
  de gvfs-fuse); `es_mtp()` y `short_path()` muestran `mtp://…` en la interfaz.
- `copiex/engine.py`: motor de copia (`Operacion`, `Motor`, `DestinoCopia`), bloques de
  1 MiB con `os.copy_file_range` (reserva a lectura/escritura si el sistema de ficheros no
  lo admite), continuación por byte y reparto a varios destinos con una sola lectura. Con
  MTP no continúa por byte ni usa `copy_file_range`: rehace el fichero desde cero y
  descuenta el parcial del progreso. Requiere `gvfs-fuse` (paquete del sistema).
  `Operacion.mover` (un «Cortar») borra los orígenes en `_borrar_origenes()` solo cuando
  todos los destinos están `done`; la marca se guarda en la columna `mover`. Con un solo
  destino en la misma partición, `_mover_directo()` hace `os.rename()` al principio de
  `_trabajar_seguro()`: el movimiento es instantáneo y no copia datos (requerimiento 16).
  Si no puede, sigue el camino normal de copiar y borrar. La velocidad
  se mide sobre los últimos 15 s (`VENTANA_VELOCIDAD`) con un suavizado exponencial y el
  restante solo cambia cuando la diferencia supera 5 s o el 10 % (requerimiento 15).
- `copiex/store.py`: historial SQLite, incluida la tabla `destinos` con la cola de cada
  carpeta destino. `copiex/watcher.py`: reanudación automática cada 6 s.
- `packaging/initial-language`: idioma inicial del usuario al instalar el `.deb` (lee
  `AccountsService`, `user-dirs.locale`, el entorno y el idioma del sistema; escribe
  `~/.config/copiex/language`). Lo llama el `postinst`.
- `copiex/app.py` + `copiex/window.py`: aplicación y ventana del historial; acciones
  `idioma_es`/`idioma_en` y submenú «Idioma» en la ventana. Al cambiar de idioma se
  reconstruye la ventana visible y se refresca el menú del Centinela.
- `copiex/sound.py`: alerta de fin de copia. El audio está en `sounds/` (manda
  `copy-finished.*`; si no, el primer audio de la carpeta): para cambiar la alarma se
  sustituye ese fichero, no el código. «Eliminar» solo oculta la fila, nunca borra el
  historial.
- `copiex/tray.py`: icono de bandeja (StatusNotifierItem) con submenú de idioma.
  Publica `IconPixmap` (ARGB32, alfa premultiplicado) además de `IconName`, y deja el
  nombre vacío cuando hay mapa de bits: sin él, la extensión AppIndicator 57 de Ubuntu
  24.04 falla al resolver el icono por el tema (`iconCache.js` llama a `oldIcon.equals`,
  que no existe en `Gio.Icon`) y el panel muestra tres puntos (`image-loading-symbolic`).
  No quites el mapa de bits ni vuelvas a declarar `IconPixmap` como `aa(iiay)`: la spec
  de SNI y el panel esperan `a(iiay)`.
  `copiex/ipc.py`: socket Unix.
- `copiex/nautilus_extension.py`: extensión de Nautilus (menú con «Copiar» y «Cortar»,
  portapapeles con cabecera `copy`/`cut`, arranque y el ciclo de «Pegar con Copiex N
  destinos», clase `_SelectorDestinos`). Cortar añade `"move": true` al mensaje; el
  borrado de orígenes lo hace el motor al terminar. Las peticiones se envían **sin hilos**
  (  `_Envio`, callbacks de `GLib.io_add_watch`) y el arranque se pide por D-Bus al servicio
  `com.copiex.Manager`, que instala el paquete `.deb`
  (`/usr/share/dbus-1/services/com.copiex.Manager.service`; las instalaciones antiguas
  lo tenían en `~/.local/share/dbus-1/services`). En el `.deb` también busca `menu.yaml`
  en `/opt/copiex` y `/usr/share/copiex`. Lee el idioma y `menu.yaml` en cada construcción
  del menú y vigila `~/.config/copiex` con `Gio.FileMonitor` para pedir a Nautilus
  (`emit_items_updated_signal()`) que rehaga los ítems al cambiar de idioma.
- `packaging/`: `.deb` con la app en `/opt/copiex`, lanzador, escritorio, iconos,
  servicio D-Bus, extensión de Nautilus y repositorio APT local con las dependencias.
  El `postinst` solo depende de `python3`; un helper instala lo que falte en segundo
  plano (repositorio local sin red, o actualización desde Internet si se acepta). No lo
  conviertas en un paquete con `Depends:` de GTK: eso impediría la instalación offline.
- `upgrade.sh`: actualiza listas y dependencias (directas y transitivas instaladas),
  reconstruye el `.deb` con las versiones actuales y reinstala el paquete (aunque la
  versión no cambie). No se ejecuta con sudo.
- **Reanudar tras kill:** `Motor.reanudar()` debe persistir el estado también cuando la
  operación viene del historial (hilo nuevo); si no, `pausa_manual=1` sobrevive y el
  vigilante no la recupera. Ver «3 unvicies» en `TODO.md`.
