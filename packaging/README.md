# Paquete .deb de Copiex

Genera `copiex_<versión>_<arquitectura>.deb` en la raíz del proyecto. El
artefacto y las carpetas `build/` y `cache/` están en `.gitignore`: se publica
el código del empaquetado, no el binario de 60 MB.

Estado actual (16/11/2026): el paquete y `upgrade.sh` están publicados en el
commit `ce8d9ee`; `install.sh` se retiró y `uninstall.sh` queda solo para
instalaciones antiguas de usuario.

```bash
./packaging/build-deb.sh
sudo apt install ./copiex_1.0.0_amd64.deb
```

## Qué instala

- `/opt/copiex`: la aplicación, `menu.yaml`, `sounds/` y el código Python.
- `menu.yaml` incluye español e inglés; la preferencia del usuario se guarda en
  `~/.config/copiex/language` y no forma parte del paquete.
- `/usr/bin/copiex`: lanzador para el escritorio y el servicio D-Bus.
- `/usr/share/applications/com.copiex.Manager.desktop`
- `/usr/share/dbus-1/services/com.copiex.Manager.service`
- `/usr/share/icons/hicolor/scalable/apps/com.copiex.Manager*.svg`
- `/usr/share/nautilus-python/extensions/copiex.py` (menú de Nautilus).
- `/usr/share/copiex/offline/`: repositorio APT local con los `.deb` de las
  dependencias (GNOME, Nautilus, MTP, sonido y sus dependencias).
- `/usr/bin/copiex-dependencias` y `/usr/lib/copiex/instalar-dependencias`.

## Instalación sin Internet

El paquete solo declara `Depends: python3`, así que `dpkg`/`apt` lo instalan
aunque falten GTK, libadwaita, Nautilus o gvfs. Al terminar, el `postinst` lanza
en segundo plano la instalación de las dependencias:

- sin red: desde el repositorio local incluido en el propio `.deb`;
- con red: pregunta si actualizar desde los repositorios de Ubuntu.

El progreso se escribe en `/var/log/copiex-dependencias.log`. Si algo falla:

```bash
sudo copiex-dependencias          # vuelve a usar el repositorio local
sudo copiex-dependencias online   # reintenta desde Internet
```

Se puede evitar la pregunta:

```bash
sudo COPIEX_ACTUALIZAR=si apt install ./copiex_1.0.0_amd64.deb
sudo COPIEX_ACTUALIZAR=no apt install ./copiex_1.0.0_amd64.deb
```

La pregunta solo aparece con terminal interactiva; desde un gestor gráfico se
usa el repositorio local.

## Construcción

Hace falta Internet **para construir** el paquete (se descargan los `.deb` de
las dependencias). El paquete resultante ya se puede instalar sin red.

- `COPIEX_DEPS_NIVEL=1|2|...`: niveles de dependencias a incluir (2 por
  defecto). El repositorio de 2 niveles ocupa unos 60 MB.
- `COPIEX_ARQ=amd64`: arquitectura, por defecto la del sistema.
- Los paquetes se descargan de la misma versión de Ubuntu en la que se
  construye; el repositorio está pensado para esa versión.

El paquete incluye la extensión de Nautilus para todos los usuarios y, al
instalarse, aparta una posible copia de `~/.local/share/nautilus-python/extensions/copiex.py`
(la de instalaciones antiguas con `install.sh`) para que no aparezcan menús
duplicados. Después hay que reiniciar Nautilus: `nautilus -q`.

## Actualizar Copiex y el paquete

Desde la raíz del proyecto, sin sudo:

```bash
./upgrade.sh
```

Actualiza las listas de Ubuntu, actualiza las dependencias directas y las
transitivas ya instaladas, reconstruye el `.deb` con las versiones actuales de
todas las dependencias y reinstala el paquete (incluido el caso en que la
versión de Copiex no cambie). No se ejecuta con `sudo`: el script lo pide solo
para `apt-get`.

Comprobado en la sesión del 16/11: sintaxis de los scripts, resolución de las
183 dependencias, simulaciones de `apt-get install --only-upgrade` y
`--reinstall`, y reconstrucción real del `.deb`. No se ejecutó `upgrade.sh`
completo (requiere root y modifica el sistema) ni se instaló el `.deb` en una
máquina limpia; eso queda pendiente de la prueba del usuario.

## Limitaciones

- El `.deb` es específico de la arquitectura y la versión de Ubuntu usadas al
  construirlo.
- La instalación de dependencias ocurre después de que `apt` termine (dpkg
  mantiene el candado durante el `postinst`); por eso es en segundo plano.
- `menu.yaml` instalado en `/opt` es gestionado por el paquete: una
  actualización puede reemplazarlo.
- `upgrade.sh` necesita Internet para actualizar los paquetes y reconstruir el
  `.deb`; sin red queda `sudo copiex-dependencias` para usar el repositorio
  offline ya instalado.
- La versión del paquete sigue siendo `1.0.0`; `upgrade.sh` usa `--reinstall`
  para aplicar cambios aunque no se haya incrementado.
