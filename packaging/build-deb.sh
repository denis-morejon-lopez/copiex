#!/bin/bash
# Construye copiex_<versión>_<arquitectura>.deb en la raíz del proyecto.
#
# El .deb incluye:
#   · la aplicación en /opt/copiex y un lanzador /usr/bin/copiex;
#   · escritorio, iconos, servicio D-Bus y extensión de Nautilus;
#   · un repositorio APT local con los .deb de las dependencias necesarias.
#
# Uso:
#   ./packaging/build-deb.sh
#   COPIEX_DEPS_NIVEL=2 ./packaging/build-deb.sh   # 2 niveles (por defecto)
#
# Para que el paquete pueda instalar dependencias sin red, los .deb incluidos se
# descargan al construir (hace falta Internet en ese momento).
set -euo pipefail

AQUI=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RAIZ=$(CDPATH= cd -- "$AQUI/.." && pwd)
VERSION=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import copiex; print(copiex.__version__)' "$RAIZ")
ARQ=${COPIEX_ARQ:-$(dpkg --print-architecture)}
NIVEL=${COPIEX_DEPS_NIVEL:-2}
CONSTRUIR="$AQUI/build"
CACHE="$AQUI/cache/debs-$ARQ"
REPO="$CONSTRUIR/usr/share/copiex/offline"
SALIDA="$RAIZ/copiex_${VERSION}_${ARQ}.deb"

for orden in dpkg-deb dpkg-scanpackages apt-cache apt-get; do
    command -v "$orden" >/dev/null || {
        echo "ERROR: falta $orden (instala dpkg-dev)." >&2
        exit 1
    }
done

echo "== 1/5 resolviendo dependencias =="
DIRECTAS=()
while IFS= read -r linea; do
    case "$linea" in ''|'#'*) continue ;; esac
    DIRECTAS+=("${linea%%#*}")
done <"$AQUI/deps.txt"
if [ "${#DIRECTAS[@]}" -eq 0 ]; then
    echo "ERROR: packaging/deps.txt está vacío." >&2
    exit 1
fi
mapfile -t PAQUETES < <(
    python3 "$AQUI/resolver.py" "$NIVEL" "${DIRECTAS[@]}"
)
if [ "${#PAQUETES[@]}" -eq 0 ]; then
    echo "ERROR: no se resolvió ningún paquete." >&2
    exit 1
fi
echo "   ${#PAQUETES[@]} paquetes (nivel $NIVEL)"

echo "== 2/5 descargando paquetes para el repositorio local =="
rm -rf "$CACHE" "$CONSTRUIR"
mkdir -p "$CACHE" "$REPO"
# Una sola llamada descarga todo; si algún nombre falla, se prueba uno a uno.
if ! (cd "$CACHE" && apt-get download "${PAQUETES[@]}"); then
    echo "   aviso: falló la descarga conjunta; se prueban uno a uno"
    for paquete in "${PAQUETES[@]}"; do
        (cd "$CACHE" && apt-get download "$paquete") || {
            echo "ERROR: no se pudo descargar $paquete" >&2
            exit 1
        }
    done
fi
if ! ls "$CACHE"/*.deb >/dev/null 2>&1; then
    echo "ERROR: no se descargó ningún .deb." >&2
    exit 1
fi
cp "$CACHE"/*.deb "$REPO/"
(cd "$REPO" && dpkg-scanpackages -m . /dev/null >Packages 2>/dev/null)
gzip -9c "$REPO/Packages" >"$REPO/Packages.gz"
echo "   repositorio local: $(du -sh "$REPO" | cut -f1)"

echo "== 3/5 copiando la aplicación =="
mkdir -p \
    "$CONSTRUIR/DEBIAN" \
    "$CONSTRUIR/opt/copiex" \
    "$CONSTRUIR/usr/bin" \
    "$CONSTRUIR/usr/lib/copiex" \
    "$CONSTRUIR/usr/share/applications" \
    "$CONSTRUIR/usr/share/dbus-1/services" \
    "$CONSTRUIR/usr/share/icons/hicolor/scalable/apps" \
    "$CONSTRUIR/usr/share/nautilus-python/extensions" \
    "$CONSTRUIR/usr/share/doc/copiex"

cp -a "$RAIZ/copiex" "$CONSTRUIR/opt/copiex/copiex"
find "$CONSTRUIR/opt/copiex" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$CONSTRUIR/opt/copiex" -name '*.pyc' -delete
cp "$RAIZ/menu.yaml" "$CONSTRUIR/opt/copiex/"
cp -a "$RAIZ/sounds" "$CONSTRUIR/opt/copiex/sounds"
cp -a "$RAIZ/icons/." "$CONSTRUIR/usr/share/icons/hicolor/scalable/apps/"
cp "$RAIZ/copiex/nautilus_extension.py" "$CONSTRUIR/usr/share/nautilus-python/extensions/copiex.py"
sed 's|@EJECUTABLE@|/usr/bin/copiex|' "$RAIZ/com.copiex.Manager.desktop.in" \
    >"$CONSTRUIR/usr/share/applications/com.copiex.Manager.desktop"
sed 's|@EJECUTABLE@|/usr/bin/copiex|' "$RAIZ/com.copiex.Manager.service.in" \
    >"$CONSTRUIR/usr/share/dbus-1/services/com.copiex.Manager.service"

cat >"$CONSTRUIR/usr/bin/copiex" <<'LAUNCHER'
#!/bin/sh
# Lanzador instalado por el paquete .deb.
export PYTHONPATH="/opt/copiex${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m copiex "$@"
LAUNCHER
chmod 755 "$CONSTRUIR/usr/bin/copiex"
install -m 755 "$AQUI/copiex-dependencias" "$CONSTRUIR/usr/bin/copiex-dependencias"
install -m 755 "$AQUI/instalar-dependencias" "$CONSTRUIR/usr/lib/copiex/instalar-dependencias"
install -m 755 "$AQUI/initial-language" "$CONSTRUIR/usr/lib/copiex/initial-language"
printf '%s\n' "${PAQUETES[@]}" >"$CONSTRUIR/usr/share/copiex/paquetes.txt"

echo "== 4/5 metadatos y scripts =="
cat >"$CONSTRUIR/DEBIAN/control" <<CONTROL
Package: copiex
Version: $VERSION
Architecture: $ARQ
Maintainer: Copiex <copiex@localhost>
Installed-Size: $(du -sk "$CONSTRUIR" | cut -f1)
Depends: python3
Section: utils
Priority: optional
Description: gestor de copias con cola, pausa y reanudación para GNOME
 Copiex copia ficheros y carpetas desde Nautilus o desde su propia ventana,
 con progreso, pausa, reanudación automática, varios destinos y soporte de
 dispositivos mtp://. Incluye «Cortar con Copiex» para mover ficheros.
 .
 El paquete trae las dependencias de GNOME, Nautilus, MTP y sonido en un
 repositorio APT local, para poder instalarlas sin conexión. Si hay Internet,
 el instalador pregunta si se quieren actualizar desde Ubuntu.
CONTROL

cat >"$CONSTRUIR/usr/share/doc/copiex/README.Debian" <<'README'
Copiex en un paquete .deb
=========================

El paquete instala la aplicación en /opt/copiex, el lanzador en
/usr/bin/copiex, el menú de Nautilus en /usr/share/nautilus-python/extensions
y las dependencias de GNOME/Nautilus/MTP/sonido en un repositorio APT local
(/usr/share/copiex/offline).

Al instalar
-----------

Las dependencias se preparan en segundo plano después de que dpkg termine,
porque durante el postinst el candado de dpkg sigue tomado. El progreso queda
en /var/log/copiex-dependencias.log.

  · Con Internet y una terminal interactiva, la instalación pregunta si se
    quieren actualizar los paquetes desde los repositorios de Ubuntu.
  · Sin Internet, o si se responde que no, se instalan las versiones incluidas
    en el paquete.

Se puede forzar el modo sin preguntar:

    sudo COPIEX_ACTUALIZAR=si  apt install ./copiex_1.0.0_amd64.deb
    sudo COPIEX_ACTUALIZAR=no  apt install ./copiex_1.0.0_amd64.deb

Si algo falla o se quiere reintentar:

    sudo copiex-dependencias          # repositorio incluido, sin red
    sudo copiex-dependencias online   # actualizar desde Internet

Idioma
------

Al instalar, el postinst mira el idioma de la interfaz GNOME de cada usuario
(Ajustes -> Region e idioma, y como respaldo el idioma de la sesión y del
sistema) y escribe ~/.config/copiex/language: `es` si esta en espanol y `en` en
cualquier otro caso. Si el fichero ya existe no se toca, asi que reinstalar o
actualizar el paquete respeta el idioma elegido. Despues se puede cambiar con
el menu Idioma -> Espanol/Ingles.

Si tenias una instalacion antigua de usuario con ./install.sh, el postinst aparta la copia
de ~/.local/share/nautilus-python/extensions/copiex.py (la renombra a
.guardada-por-copiex-deb) para que Nautilus no cargue dos Copiex y muestre el
menú duplicado.

Después de instalar o actualizar, reinicia Nautilus para cargar el menú:

    nautilus -q

Nota: el repositorio local contiene paquetes de la versión de Ubuntu con la que
se construyó el .deb. Está pensado para instalar sin red en esa misma versión.
README

install -m 755 "$AQUI/postinst" "$CONSTRUIR/DEBIAN/postinst"
install -m 755 "$AQUI/postrm" "$CONSTRUIR/DEBIAN/postrm"
cat >"$CONSTRUIR/usr/share/doc/copiex/copyright" <<'COPYRIGHT'
Copiex
Copyright (C) 2026
Este paquete se distribuye con la misma licencia que el proyecto Copiex.
COPYRIGHT

echo "== 5/5 generando $SALIDA =="
dpkg-deb --build --root-owner-group "$CONSTRUIR" "$SALIDA" >/dev/null
echo
echo "Paquete creado: $SALIDA ($(du -h "$SALIDA" | cut -f1))"
echo "Instalación:    sudo apt install \"$SALIDA\""
