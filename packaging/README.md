# Paquete .deb de Copiex

Genera `copiex_<versión>_<arquitectura>.deb` en la raíz del proyecto. El
artefacto y las carpetas `build/` y `cache/` están en `.gitignore`: se publica
el código del empaquetado, no el binario de 122 MB.

El mismo `.deb` sirve en Ubuntu 24.04 y 26.04: lleva el repositorio de
dependencias de cada una.

Estado actual (17/11/2026): el paquete y `upgrade.sh` están publicados en el
commit `ce8d9ee`; `install.sh` se retiró y `uninstall.sh` queda solo para
instalaciones antiguas de usuario. El 17/11 se publicó en `fc04da6` «Idioma
inglés» el selector de idioma; el paquete ya incluye `menu.yaml` bilingüe.

```bash
./packaging/build-deb.sh
sudo apt install ./copiex_1.0.1_amd64.deb
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
- `/usr/share/copiex/offline/ubuntu-<versión>/`: un repositorio APT local por
  versión de Ubuntu (24.04 y 26.04) con los `.deb` de las dependencias (GNOME,
  Nautilus, MTP, sonido y sus dependencias) y su `paquetes.txt`.
- `/usr/bin/copiex-dependencias`, `/usr/lib/copiex/instalar-dependencias` y
  `/usr/lib/copiex/plataforma.sh` (detección de la versión de Ubuntu).
- `/usr/lib/copiex/initial-language`: elige el idioma inicial de cada usuario al
  instalar (lo llama el `postinst`; ver «Idioma inicial»).

## Idioma inicial

Al instalar, el `postinst` recorre `/home/*` y ejecuta `initial-language <casa>`, que
escribe `~/.config/copiex/language` con `es` si la interfaz GNOME de ese usuario está en
español y con `en` en cualquier otro caso. El orden de las pistas es:

1. `Language=` del usuario en `/var/lib/AccountsService/users/<usuario>` (lo que se elige
   en Ajustes → Región e idioma; es el dato real de GNOME);
2. `~/.config/user-dirs.locale`;
3. `LC_ALL`/`LC_MESSAGES`/`LANG`/`LANGUAGE` del proceso (`C`, `POSIX` y `C.UTF-8` no
   cuentan: un `postinst` lanzado por `apt` suele arrastrarlos aunque la sesión esté en
   español);
4. `/etc/default/locale`, `/etc/locale.conf` y `localectl status`.

Basta con que el código empiece por `es` (`es`, `es_ES.UTF-8`, `es-AR`, `LANGUAGE=es:en`).
Si el fichero de idioma ya existe y contiene `es` o `en`, **no se toca**: reinstalar o
actualizar el paquete (`./upgrade.sh`) respeta lo que el usuario eligió en el menú. Si no
hay ninguna pista, se pone inglés. Después se cambia con «Idioma» → «Español»/«Inglés»,
como siempre, y Nautilus lo adopta sin reiniciar.

Se puede probar sin instalar nada (usa una carpeta temporal como casa):

```bash
COPIEX_ACCOUNTS_DIR=/tmp/cuentas ./packaging/initial-language /tmp/casa
```

## Versiones de Ubuntu

El `postinst` y el instalador de dependencias leen la versión del sistema con
`/usr/lib/copiex/plataforma.sh`, que decide **qué hacer en cada una**:

| Versión | Repositorio offline | Typelib de Nautilus | GTK / libadwaita |
| --- | --- | --- | --- |
| Ubuntu 24.04 (noble) | `offline/ubuntu-24.04` | `gir1.2-nautilus-4.0` (Nautilus 46) | 4.14 / 1.5 |
| Ubuntu 26.04 (resolute) | `offline/ubuntu-26.04` | `gir1.2-nautilus-4.1` (Nautilus 50) | 4.22 / 1.8 |
| Otra | no hay: se resuelve por Internet | la que ofrezca apt | — |

En modo con Internet se pide además la typelib que corresponde a esa versión,
y al terminar queda en `/var/log/copiex-dependencias.log` una comprobación de
lo que hay instalado (typelib y versión de Nautilus) y en
`/var/lib/copiex/entorno` la versión detectada. La detección se puede probar sin
tener esa Ubuntu:

```bash
COPIEX_OS_RELEASE=/tmp/os-release-26.04 sh -c '. packaging/plataforma.sh; copiex_describe_plataforma'
```

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
sudo COPIEX_ACTUALIZAR=si apt install ./copiex_1.0.1_amd64.deb
sudo COPIEX_ACTUALIZAR=no apt install ./copiex_1.0.1_amd64.deb
```

La pregunta solo aparece con terminal interactiva; desde un gestor gráfico se
usa el repositorio local.

El `.deb` trae **un repositorio por versión de Ubuntu**
(`/usr/share/copiex/offline/ubuntu-24.04`, `…/ubuntu-26.04`) y al instalar se
usa el de la versión del sistema. Así el mismo paquete se instala sin red en
24.04 y en 26.04. Si se instala en una versión que el paquete no trae (por
ejemplo 25.10), el `postinst` lo detecta y resuelve las dependencias con los
repositorios de Ubuntu, sin preguntar; sin red en ese caso la instalación de
dependencias falla con un aviso claro en el registro.

## Construcción

Hace falta Internet **para construir** el paquete (se descargan los `.deb` de
las dependencias). El paquete resultante ya se puede instalar sin red.

- `COPIEX_DEPS_NIVEL=1|2|...`: niveles de dependencias a incluir (2 por
  defecto). Cada repositorio de 2 niveles ocupa unos 60 MB.
- `COPIEX_ARQ=amd64`: arquitectura, por defecto la del sistema.
- `COPIEX_SUITES="noble resolute"`: versiones de Ubuntu que se incluyen, por
  defecto las dos LTS (`noble` = 24.04, `resolute` = 26.04), así que el `.deb`
  ocupa unos 130 MB. Se pueden descargar las dos aunque se construya en una
  sola: cada suite usa listas de apt propias (`packaging/cache/apt-<suite>`).
  Con `COPIEX_SUITES=noble` se obtiene un paquete de la mitad de tamaño que
  solo funciona sin red en 24.04.
- `deps.txt` admite alternativas con `|` (`gir1.2-nautilus-4.1 |
gir1.2-nautilus-4.0`): se usa la primera que exista en el sistema donde se
  construye o donde se instala. En el `.deb` van dos listas: `paquetes.txt` (el
  cierre resuelto, para el repositorio offline) y `deps.txt` (solo las directas,
  para que apt resuelva con los paquetes de la versión destino).

El paquete incluye la extensión de Nautilus para todos los usuarios y, al
instalarse, aparta una posible copia de `~/.local/share/nautilus-python/extensions/copiex.py`
(la de instalaciones antiguas con `install.sh`) para que no aparezcan menús
duplicados. Después hay que reiniciar Nautilus: `nautilus -q`.

Mientras el `.deb` no esté instalado, la extensión que carga Nautilus es esa copia
de usuario: tras tocar `copiex/nautilus_extension.py` hay que copiarla a mano
(`cp copiex/nautilus_extension.py ~/.local/share/nautilus-python/extensions/copiex.py`),
borrar el `__pycache__` de esa carpeta y reiniciar Nautilus. Comprueba con `md5sum`
que ambos ficheros coinciden; una copia vieja fue la causa de que el cambio de
idioma pareciera no aplicarse el 17/11.

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

- El `.deb` es específico de la arquitectura. Lleva dependencias offline de
  Ubuntu 24.04 y 26.04; en otra versión de Ubuntu se instala, pero sus
  dependencias solo se pueden resolver con Internet
  (`sudo copiex-dependencias online`).
- Construir el paquete con las dos suites necesita descargar unos 130 MB.
- La instalación de dependencias ocurre después de que `apt` termine (dpkg
  mantiene el candado durante el `postinst`); por eso es en segundo plano.
- `menu.yaml` instalado en `/opt` es gestionado por el paquete: una
  actualización puede reemplazarlo.
- `upgrade.sh` necesita Internet para actualizar los paquetes y reconstruir el
  `.deb`; sin red queda `sudo copiex-dependencias` para usar el repositorio
  offline ya instalado.
- La versión del paquete es `1.0.1`; `upgrade.sh` usa `--reinstall` para
  aplicar cambios aunque no se haya incrementado la versión.
- Para descargar las dependencias de la suite empaquetada, `build-deb.sh` aísla
  también `Dir::State::status` (`/dev/null`). Sin eso, al construir en una
  versión de Ubuntu más nueva que la empaquetada apt toma como candidatas las
  versiones instaladas en el equipo y la descarga falla con «No se puede
  encontrar una fuente para descargar la versión …».
- La licencia del proyecto es **GPL-3.0** (`LICENSE` en la raíz, añadido el 23/11). El
  `copyright` que escribe `build-deb.sh` en `/usr/share/doc/copiex/copyright` dice «la
  misma licencia que el proyecto Copiex»; nombrar allí GPL-3.0 y quizá incluir el fichero
  `LICENSE` completo queda pendiente.
