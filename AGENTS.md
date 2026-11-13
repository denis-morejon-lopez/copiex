# Copiex — instrucciones para agentes

Gestor de copias en Python + PyGObject (GTK 4 / libadwaita) para GNOME: icono de bandeja,
extensión de Nautilus, historial en SQLite, pausa/cancelación, continuación por byte y
reanudación automática. **Los ficheros y carpetas llevan nombres en inglés** (`sound.py`,
`watcher.py`, `nautilus_extension.py`, `copiex-launcher`, `sounds/`, `icons/`); las clases,
funciones y atributos internos siguen en español (`Vigilante`, `cargar()`, `texto()`).

**Antes de tocar nada, lee `TODO.md`** (estado real, requerimiento por requerimiento,
trampas y recetas de prueba) y `NOTES.md` (pliego vigente: 11 requerimientos y 4 errores;
los de workers se retiraron el 13/11).

## Trabajo pendiente

Los 11 requerimientos del pliego están hechos y el error 3 (muchos ficheros) está medido y
mejorado. Queda una mejora menor:

1. Tratar un «cortar» de Nautilus como mover, no como copiar.

## Reglas que no se negocian

- **Los textos de la interfaz viven en `menu.yaml`** (raíz), no en el código: nombres de
  opciones y textos de ventanas emergentes. Se leen con `texto("seccion.clave")` de
  `copiex/menu.py`; si añades una clave, añádela también a `_POR_DEFECTO` en ese módulo. Un
  cambio en el YAML exige **reiniciar la app**; la extensión (fichero suelto) lleva su
  propio lector de la sección `nautilus:` y exige `./install.sh` + `nautilus -q`.
- **Si el menú de Nautilus no hace nada:** mira `~/.local/share/copiex/extension.log`
  (traza de copiar/pegar, MIME leído y respuesta de la app); los `print` de la
  extensión se pierden.
- **No reintroduzcas los workers/hilos** (se retiraron del pliego el 13/11): se midieron, no mejoraban el
  tiempo y el usuario pidió retirarlos. Ver «3 quinquies» en `TODO.md`.
- Todo callback pasado a `GLib.idle_add` debe devolver `False`; si no, la acción se repite
  en bucle (ya pasó con las copias duplicadas).
- Nunca hagas `os.path.exists`/`isdir` sobre rutas de usuario en el hilo de GTK: un
  dispositivo que no responde congela la ventana. Esas comprobaciones van en el hilo de copia.
- No uses `pkill -f "python3 -m copiex"`: mata al propio shell. Localiza el PID con
  `ps -eo pid,args | grep "[p]ython3 -m copiex"` y mátalo por PID.
- Prueba siempre con base de datos y `XDG_CONFIG_HOME` temporales en `/tmp`; no toques el
  historial real de `~/.local/share/copiex/historial.db`.
- **Git:** el proyecto tiene repositorio (remoto `repo-copiex` en GitHub). **No hagas
  commit ni push** salvo que el usuario lo pida; y avísale de que la URL del remoto lleva un
  token incrustado en `.git/config`, que debería rotar.

## Diagnóstico

`~/.local/share/copiex/copiex.log` es el fichero que el usuario envía cuando algo falla:
se escribe en DEBUG, conserva **una semana** (poda al arrancar y cada hora, tope 32 MiB) e
incluye las acciones de Nautilus como `Nautilus: …`. `extension.log` solo recoge lo que
pasa cuando la aplicación no está arrancada. El diseño está en `copiex/logs.py` y en la
sección «3 octies» de `TODO.md`.

## Comandos

```bash
./copiex-launcher                      # abre la ventana
./copiex-launcher --bandeja            # solo bandeja (sin ventana)
./install.sh && nautilus -q            # instala/recarga la extensión de Nautilus
./uninstall.sh --simular              # qué borraría (no toca nada)
./uninstall.sh                        # desinstala todo (pregunta; --conservar-datos/--si)
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
- `icons/`: icono propio y variante simbólica. `brand/`: propuestas descartadas y la
  galería `preview.html` con la que se eligió.
- `copiex/window.py`: además del historial, la cabecera lleva el icono a 22 px justo
  después del título «Copiex» (`Gtk.Box` con `Adw.WindowTitle` + `Gtk.Image`).
- `copiex/util.py`: rutas y `icono_disponible()` (icono propio o `edit-copy`).
- `copiex/engine.py`: motor de copia (`Operacion`, `Motor`), bloques de 1 MiB con
  `os.copy_file_range` (reserva a lectura/escritura si el sistema de ficheros no lo
  admite), continuación por byte.
- `copiex/store.py`: SQLite del historial. `copiex/watcher.py`: reanudación automática cada 6 s.
- `copiex/app.py` + `copiex/window.py`: aplicación y ventana del historial.
- `icons/`: icono propio (`com.copiex.Manager.svg` y la variante `-symbolic` que usa la
  bandeja). Lo instala `./install.sh` en el tema `hicolor`; si no está, la bandeja cae en
  `edit-copy`. Las propuestas descartadas viven en `brand/`.
- `copiex/sound.py`: alerta de fin de copia. El audio está en `sounds/` (manda
  `copy-finished.*`; si no, el primer audio de la carpeta): para cambiar la alarma se
  sustituye ese fichero, no el código. «Eliminar» solo oculta la fila, nunca borra el
  historial.
- `copiex/tray.py`: icono de bandeja (StatusNotifierItem). `copiex/ipc.py`: socket Unix.
- `copiex/nautilus_extension.py`: extensión de Nautilus (menú, portapapeles, arranque).
