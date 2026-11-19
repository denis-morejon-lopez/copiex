#!/bin/bash
# Construye copiex_<versión>_<arquitectura>.deb en la raíz del proyecto.
#
# El .deb incluye:
#   · la aplicación en /opt/copiex y un lanzador /usr/bin/copiex;
#   · escritorio, iconos, servicio D-Bus y extensión de Nautilus;
#   · un repositorio APT local por versión de Ubuntu (por defecto 24.04 y
#     26.04) con los .deb de las dependencias necesarias. Al instalar se usa el
#     de la versión del sistema: el mismo paquete sirve en las dos.
#
# Uso:
#   ./packaging/build-deb.sh
#   COPIEX_DEPS_NIVEL=2 ./packaging/build-deb.sh    # 2 niveles (por defecto)
#   COPIEX_SUITES="noble" ./packaging/build-deb.sh  # solo una versión
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
CACHE="$AQUI/cache"
REPO="$CONSTRUIR/usr/share/copiex/offline"
SALIDA="$RAIZ/copiex_${VERSION}_${ARQ}.deb"

for orden in dpkg-deb dpkg-scanpackages apt-cache apt-get xz; do
    command -v "$orden" >/dev/null || {
        echo "ERROR: falta $orden (instala dpkg-dev)." >&2
        exit 1
    }
done

# Versiones de Ubuntu que lleva el paquete. Con COPIEX_SUITES se puede limitar
# la lista (construcción rápida o una arquitectura que la otra no publica).
# Por defecto van las dos LTS soportadas: la misma construcción sirve en ambas.
SUITES=${COPIEX_SUITES:-"noble resolute"}

version_de_suite() {
    case "$1" in
        jammy) echo 22.04 ;;
        noble) echo 24.04 ;;
        plucky) echo 25.04 ;;
        questing) echo 25.10 ;;
        resolute) echo 26.04 ;;
        *) echo "" ;;
    esac
}

# Configuración de apt aislada de la del sistema: cada suite tiene sus propias
# listas, así se resuelven y descargan los paquetes de esa versión de Ubuntu
# aunque la construcción se haga en otra.
preparar_apt() {
    suite=$1
    base="$CACHE/apt-$suite"
    mkdir -p "$base/lists" "$base/archivos"
    cat >"$base/sources.list" <<SOURCES
deb http://archive.ubuntu.com/ubuntu $suite main universe restricted multiverse
deb http://archive.ubuntu.com/ubuntu $suite-updates main universe restricted multiverse
deb http://security.ubuntu.com/ubuntu $suite-security main universe restricted multiverse
SOURCES
    cat >"$base/apt.conf" <<CONF
Dir::Etc::sourcelist "$base/sources.list";
Dir::Etc::sourceparts "-";
Dir::State::lists "$base/lists";
Dir::Cache::archives "$base/archivos";
APT::Get::List-Cleanup "0";
Acquire::Languages "none";
Acquire::Retries "3";
CONF
}

# Descarga el cierre de dependencias de una versión de Ubuntu en
# $REPO/ubuntu-<versión>/ (los .deb, el índice Packages y la lista usada).
descargar_suite() {
    suite=$1
    version=$(version_de_suite "$suite")
    if [ -z "$version" ]; then
        echo "ERROR: no sé qué versión de Ubuntu es «$suite»." >&2
        return 1
    fi
    base="$CACHE/apt-$suite"
    debs="$CACHE/debs-$suite"
    reposuite="$REPO/ubuntu-$version"
    rm -rf "$debs" "$reposuite"
    mkdir -p "$debs" "$reposuite"
    preparar_apt "$suite"

    echo "-- Ubuntu $version ($suite): actualizando listas de paquetes"
    (cd "$debs" && APT_CONFIG="$base/apt.conf" apt-get update >/dev/null) || {
        echo "ERROR: no se pudieron actualizar las listas de $suite." >&2
        return 1
    }

    mapfile -t paquetes < <(
        APT_CONFIG="$base/apt.conf" python3 "$AQUI/resolver.py" --archivo "$AQUI/deps.txt" "$NIVEL"
    )
    if [ "${#paquetes[@]}" -eq 0 ]; then
        echo "ERROR: no se resolvió ningún paquete para $suite." >&2
        return 1
    fi
    echo "-- Ubuntu $version ($suite): ${#paquetes[@]} paquetes"

    # Una sola llamada descarga todo; si algún nombre falla, se prueba uno a uno.
    if ! (cd "$debs" && APT_CONFIG="$base/apt.conf" apt-get download "${paquetes[@]}"); then
        echo "   aviso: falló la descarga conjunta; se prueban uno a uno"
        for paquete in "${paquetes[@]}"; do
            (cd "$debs" && APT_CONFIG="$base/apt.conf" apt-get download "$paquete") || {
                echo "ERROR: no se pudo descargar $paquete ($suite)" >&2
                return 1
            }
        done
    fi
    if ! ls "$debs"/*.deb >/dev/null 2>&1; then
        echo "ERROR: no se descargó ningún .deb de $suite." >&2
        return 1
    fi
    cp "$debs"/*.deb "$reposuite/"
    (cd "$reposuite" && dpkg-scanpackages -m . /dev/null >Packages 2>/dev/null)
    gzip -9c "$reposuite/Packages" >"$reposuite/Packages.gz"
    # apt sondea primero Packages.xz y, si no está, deja tres «Err: Method
    # gave a blank filename» en el registro antes de usar el Packages suelto.
    xz -9 -c "$reposuite/Packages" >"$reposuite/Packages.xz"
    printf '%s\n' "${paquetes[@]}" >"$reposuite/paquetes.txt"
    echo "   repositorio $suite: $(du -sh "$reposuite" | cut -f1)"
}

echo "== 1/4 preparando los repositorios offline ($SUITES) =="
rm -rf "$CONSTRUIR"
mkdir -p "$REPO"
for suite in $SUITES; do
    descargar_suite "$suite"
done

echo "== 2/4 copiando la aplicación =="
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
install -m 644 "$AQUI/plataforma.sh" "$CONSTRUIR/usr/lib/copiex/plataforma.sh"
# Lista directa: el modo con Internet deja que apt la resuelva con los
# repositorios de la versión de Ubuntu donde se instala.
install -m 644 "$AQUI/deps.txt" "$CONSTRUIR/usr/share/copiex/deps.txt"
# Qué versiones de Ubuntu trae el paquete («24.04 noble»), para diagnóstico.
: >"$CONSTRUIR/usr/share/copiex/suites"
for suite in $SUITES; do
    printf '%s %s\n' "$(version_de_suite "$suite")" "$suite" >>"$CONSTRUIR/usr/share/copiex/suites"
done

echo "== 3/4 metadatos y scripts =="
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
 repositorio APT local por versión de Ubuntu (24.04 y 26.04), para poder
 instalarlas sin conexión. Si hay Internet, el instalador pregunta si se
 quieren actualizar desde Ubuntu.
CONTROL

cat >"$CONSTRUIR/usr/share/doc/copiex/README.Debian" <<'README'
Copiex en un paquete .deb
=========================

El paquete instala la aplicación en /opt/copiex, el lanzador en
/usr/bin/copiex, el menú de Nautilus en /usr/share/nautilus-python/extensions
y las dependencias de GNOME/Nautilus/MTP/sonido en repositorios APT locales
(/usr/share/copiex/offline/ubuntu-<versión>).

El mismo paquete sirve para Ubuntu 24.04 y 26.04: al instalar se usa el
repositorio de la versión del sistema. Si esa versión no está incluida, las
dependencias se resuelven con los repositorios de Ubuntu (hace falta Internet).

Al instalar
-----------

Las dependencias se preparan en segundo plano después de que dpkg termine,
porque durante el postinst el candado de dpkg sigue tomado. El progreso queda
en /var/log/copiex-dependencias.log.

  · Con Internet y una terminal interactiva, la instalación pregunta si se
    quieren actualizar los paquetes desde los repositorios de Ubuntu.
  · Sin Internet, o si se responde que no, se instalan las versiones incluidas
    en el paquete para esa versión de Ubuntu.

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
README

install -m 755 "$AQUI/postinst" "$CONSTRUIR/DEBIAN/postinst"
install -m 755 "$AQUI/postrm" "$CONSTRUIR/DEBIAN/postrm"
cat >"$CONSTRUIR/usr/share/doc/copiex/copyright" <<'COPYRIGHT'
Copiex
Copyright (C) 2026
Este paquete se distribuye con la misma licencia que el proyecto Copiex.
COPYRIGHT

echo "== 4/4 generando $SALIDA =="
dpkg-deb --build --root-owner-group "$CONSTRUIR" "$SALIDA" >/dev/null
echo
echo "Paquete creado: $SALIDA ($(du -h "$SALIDA" | cut -f1))"
echo "Versiones de Ubuntu incluidas: $SUITES"
echo "Instalación:    sudo apt install \"$SALIDA\""
