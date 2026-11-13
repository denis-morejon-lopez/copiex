# Copiex — punto de retorno

Estado del trabajo al 9 de noviembre de 2026. Este fichero y `Notas.md` son todo lo
que necesita una sesión nueva: el asistente no conserva memoria entre chats, pero el
historial de la conversación anterior sigue disponible en Freebuff y este resumen
evita tener que releerlo.

---

## 1. Cómo retomar

Abre el proyecto en Freebuff y pega algo como:

> Lee `PENDIENTE.md` y `Notas.md`. Sigue con el pendiente 1 (portapapeles de Nautilus)
> y no cambies nada que ya esté marcado como verificado aquí.

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
| Historial de la base de datos | Limpio: 12 filas (las 11 históricas + 1 registro del fallo de la unidad CANTEY). |

Lo único **no** comprobado visualmente es el menú desplegado: la sesión es Wayland y no
hay `xdotool`/`ydotool`, así que no se puede sintetizar un clic derecho. En su lugar se
verificó el código que devuelve los ítems y su activación, que es lo que Nautilus ejecuta.

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

## 4. Pendientes, por orden sugerido

1. **Portapapeles de Nautilus** (requerimiento 7, y error 1 de `Notas.md`).
   Que «Ctrl+C en Nautilus → Pegar con Copiex» funcione y que Copiex intercepte la copia
   para hacerla él. Hay que comprobar el formato real: Nautilus publica
   `x-special/gnome-copied-files` además de `text/uri-list`; la extensión solo contempla
   `x-special/nautilus-clipboard` y `text/uri-list`.
2. **Reanudación automática** (requerimientos 8, y errores 1 y 2). Guardar estado ya se
   hace en tiempo real; falta el vigilante que reintente al volver origen/destino.
3. **Workers configurables** (requerimientos 9, 10, 11 y error 3). Número máximo por
   usuario, por defecto mayor que 1, y reparto de un fichero grande entre ellos.
4. **`menu.yaml`** (requerimientos 13 y 14): nombres de opciones y textos de las ventanas
   emergentes, incluida «Acerca de».
5. **«Acerca de»** con descripción reducida y versión.
6. **Alerta sonora al terminar** y **botón «Eliminar»** sustituyendo a «Cancelar»
   (requerimiento 12).
7. **Botón de cancelar durante un fallo de E/S** (error 2).

## 5. Trampas del entorno (ahorran media hora cada una)

- **Arrancar la app:** `./copiex-lanzador` o `PYTHONPATH=. python3 -m copiex`.
  Para lanzarla desde un terminal sin que el tool espere 60 s:
  `( setsid nohup ./copiex-lanzador >/tmp/copiex-app.log 2>&1 </dev/null & ) >/dev/null 2>&1`
- **Nunca** uses `pkill -f "python3 -m copiex"`: la propia línea de comandos del shell
  contiene ese texto y el comando se mata a sí mismo (pasó en noviembre). Localiza el PID
  con `ps -eo pid,cmd | grep "[p]ython3 -m copiex"` y mátalo por PID.
- **Rutas:** socket `$XDG_RUNTIME_DIR/copiex-1000/copiex.sock`
  (`/run/user/1000/...`); base de datos
  `~/.local/share/copiex/historial.db`, tabla `copias`.
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
