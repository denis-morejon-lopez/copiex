# Copiex — instrucciones para agentes

Gestor de copias en Python + PyGObject (GTK 4 / libadwaita) para GNOME: icono de bandeja,
extensión de Nautilus, historial en SQLite, pausa/cancelación, continuación por byte y
reanudación automática. Una copia puede repartirse a **varios destinos** leyendo el origen
una sola vez (`Operacion.destinos`, `_copiar_a_varios`). **Los ficheros y carpetas llevan
nombres en inglés** (`sound.py`, `watcher.py`, `nautilus_extension.py`, `copiex-launcher`,
`sounds/`, `icons/`); las clases, funciones y atributos internos siguen en español
(`Vigilante`, `cargar()`, `texto()`).

**Antes de tocar nada, lee `TODO.md`** (estado real, requerimiento por requerimiento,
trampas y recetas de prueba) y `NOTES.md` (pliego vigente: 12 requerimientos y 4 errores;
los de workers se retiraron el 13/11 y el 12, MTP, se añadió el 16/11).

## Trabajo pendiente

Los 12 requerimientos del pliego están hechos (el 12 es MTP, añadido el 16/11), el error 3
(muchos ficheros) está medido y mejorado, y «Cortar con Copiex» mueve de verdad desde el
16/11. El empaquetado `.deb` y `upgrade.sh` están terminados, publicados y documentados en
`TODO.md` (3 undevicies y 3 vicies). No hay trabajo pendiente del pliego.

**Estado al 16/11/2026:** último commit **`ce8d9ee`** «Empaquetar Copiex como .deb y
añadir upgrade.sh», ya publicado en `repo-copiex/main`. Incluye el paquete `.deb` en
`packaging/`, `upgrade.sh`, `.gitignore` y la retirada de `install.sh`. El `.deb`
(`copiex_1.0.0_amd64.deb`, 60 MB) está ignorado por Git. El 17/11 se corrigió en
`copiex/engine.py` la persistencia de `pausa_manual` al reanudar una copia recuperada; ese
arreglo y la documentación se publicaron en el commit de esta corrección. El usuario
confirmó el 17/11 que la reanudación automática a varios destinos ya funciona desde el
flujo real. La app **no está
arrancada** al retomar: `./copiex-launcher --bandeja`. Historial real: 38 filas. «Cortar»
está confirmado por el usuario; falta confirmar el icono verde en el panel.

## Reglas que no se negocian

- **Los textos de la interfaz viven en `menu.yaml`** (raíz), no en el código: nombres de
  opciones y textos de ventanas emergentes. Se leen con `texto("seccion.clave")` de
  `copiex/menu.py`; si añades una clave, añádela también a `_POR_DEFECTO` en ese módulo. Un
  cambio en el YAML exige **reiniciar la app**; la extensión (fichero suelto) lleva su
  propio lector de la sección `nautilus:` y exige instalar el `.deb` (`./upgrade.sh`) + `nautilus -q`.
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
  `destinos`.
- **Git:** el proyecto tiene repositorio (remoto `repo-copiex` en GitHub). **No hagas
  commit ni push** salvo que el usuario lo pida; y avísale de que la URL del remoto lleva un
  token incrustado en `.git/config`, que debería rotar.

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

- `menu.yaml` + `copiex/menu.py`: todos los textos de menús y ventanas emergentes (lector
  YAML propio con caché y reserva). Cambiar el YAML exige reiniciar la app.
- `sounds/`: audio de la alarma (`copy-finished.*` manda) y `README.md` con las reglas;
  `copiex/sound.py` lo reproduce. Cambiar el sonido no exige reiniciar.
- `icons/`: icono propio a color (la «C» blanca sobre verde, que es el que usa también
  la bandeja) y variante simbólica. `brand/`: propuestas descartadas y la galería
  `preview.html` con la que se eligió.
- `copiex/window.py`: además del historial, la cabecera lleva el icono a 22 px justo
  después del título «Copiex» (`Gtk.Box` con `Adw.WindowTitle` + `Gtk.Image`).
- `copiex/util.py`: rutas y `icono_disponible()` (icono propio o `edit-copy`).
  `uri_to_path()` acepta `file://` y `mtp://` (este último se resuelve con GIO a la ruta
  de gvfs-fuse); `es_mtp()` y `short_path()` muestran `mtp://…` en la interfaz.
- `copiex/engine.py`: motor de copia (`Operacion`, `Motor`, `DestinoCopia`), bloques de
  1 MiB con `os.copy_file_range` (reserva a lectura/escritura si el sistema de ficheros no
  lo admite), continuación por byte y reparto a varios destinos con una sola lectura. Con
  MTP no continúa por byte ni usa `copy_file_range`: rehace el fichero desde cero y
  descuenta el parcial del progreso. Requiere `gvfs-fuse` (paquete del sistema).
  `Operacion.mover` (un «Cortar») borra los orígenes en `_borrar_origenes()` solo cuando
  todos los destinos están `done`; la marca se guarda en la columna `mover`.
- `copiex/store.py`: historial SQLite, incluida la tabla `destinos` con la cola de cada
  carpeta destino. `copiex/watcher.py`: reanudación automática cada 6 s.
- `copiex/app.py` + `copiex/window.py`: aplicación y ventana del historial.
- `copiex/sound.py`: alerta de fin de copia. El audio está en `sounds/` (manda
  `copy-finished.*`; si no, el primer audio de la carpeta): para cambiar la alarma se
  sustituye ese fichero, no el código. «Eliminar» solo oculta la fila, nunca borra el
  historial.
- `copiex/tray.py`: icono de bandeja (StatusNotifierItem). `copiex/ipc.py`: socket Unix.
- `copiex/nautilus_extension.py`: extensión de Nautilus (menú con «Copiar» y «Cortar»,
  portapapeles con cabecera `copy`/`cut`, arranque y el ciclo de «Pegar con Copiex N
  destinos», clase `_SelectorDestinos`). Cortar añade `"move": true` al mensaje; el
  borrado de orígenes lo hace el motor al terminar. Las peticiones se envían **sin hilos**
  (  `_Envio`, callbacks de `GLib.io_add_watch`) y el arranque se pide por D-Bus al servicio
  `com.copiex.Manager`, que instala el paquete `.deb`
  (`/usr/share/dbus-1/services/com.copiex.Manager.service`; las instalaciones antiguas
  lo tenían en `~/.local/share/dbus-1/services`). En el `.deb` también busca `menu.yaml`
  en `/opt/copiex` y `/usr/share/copiex`.
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
