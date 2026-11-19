#!/bin/sh
# Actualiza Copiex y sus dependencias.
#
#   1. actualiza las listas de paquetes de Ubuntu;
#   2. actualiza las dependencias directas y las transitivas ya instaladas;
#   3. reconstruye copiex_<versión>_<arq>.deb descargando las versiones
#      actuales de todas las dependencias para el repositorio offline;
#   4. reinstala el .deb para aplicar el código y las dependencias nuevas.
#
# Uso:
#   ./upgrade.sh
#
# No se ejecuta con sudo: el script pide permiso solo para apt y el resto lo
# hace como tu usuario, para que el .deb y la caché no queden de root.
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: ejecútalo como tu usuario normal, sin sudo:  ./upgrade.sh" >&2
    echo "       El script pedirá permiso para actualizar los paquetes." >&2
    exit 1
fi

for orden in sudo apt-get python3 dpkg; do
    command -v "$orden" >/dev/null 2>&1 || {
        echo "ERROR: falta el comando $orden." >&2
        exit 1
    }
done

if [ ! -f "$DIR/packaging/deps.txt" ] || [ ! -x "$DIR/packaging/build-deb.sh" ]; then
    echo "ERROR: no encuentro el empaquetado de Copiex en $DIR/packaging." >&2
    exit 1
fi

DEPS="$DIR/packaging/deps.txt"

export LC_ALL=C.UTF-8

echo "== 1/4 actualizando las listas de paquetes =="
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get update; then
    echo "ERROR: no se pudieron actualizar las listas (¿hay Internet?)." >&2
    echo "       Sin red puedes seguir usando: sudo copiex-dependencias" >&2
    exit 1
fi

echo "== 2/4 actualizando las dependencias de Copiex =="
NIVEL=${COPIEX_DEPS_NIVEL:-2}
# El cierre completo es el mismo que acaba en el repositorio offline del .deb:
# se actualizan las que ya están instaladas y luego se asegura que las directas
# estén presentes (apt instala las que falten con sus dependencias).
# Se lee el fichero desde resolver.py: así las alternativas «a | b» de una línea
# no se parten al expandir la lista en el shell, y cada paquete se resuelve con
# los repositorios de esta versión de Ubuntu.
PAQUETES=$(python3 "$DIR/packaging/resolver.py" --archivo "$DEPS" "$NIVEL")
DIRECTAS=$(python3 "$DIR/packaging/resolver.py" --archivo "$DEPS" --directas)
if [ -z "$PAQUETES" ] || [ -z "$DIRECTAS" ]; then
    echo "ERROR: no se pudieron resolver las dependencias ($DEPS)." >&2
    exit 1
fi
# shellcheck disable=SC2086
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends --only-upgrade $PAQUETES; then
    echo "ERROR: no se pudieron actualizar las dependencias." >&2
    exit 1
fi
# shellcheck disable=SC2086
if ! sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends $DIRECTAS; then
    echo "ERROR: no se pudieron instalar las dependencias directas." >&2
    exit 1
fi

echo "== 3/4 reconstruyendo el .deb con las versiones actuales =="
"$DIR/packaging/build-deb.sh"

ARQ=${COPIEX_ARQ:-$(dpkg --print-architecture)}
VERSION=$(PYTHONPATH="$DIR" python3 -c \
    'import copiex; print(copiex.__version__)')
DEB="$DIR/copiex_${VERSION}_${ARQ}.deb"
if [ ! -f "$DEB" ]; then
    echo "ERROR: el empaquetado terminó pero no encuentro $DEB." >&2
    exit 1
fi

echo "== 4/4 instalando Copiex desde el .deb =="
# --reinstall aplica también el código nuevo cuando la versión del paquete no
# cambia; si aún no estaba instalado, se instala normal. COPIEX_ACTUALIZAR=no
# evita la pregunta del postinst: las dependencias ya se han actualizado aquí y
# el helper solo comprobará lo que falte.
REINSTALAR=""
if dpkg-query -W -f='${Status}' copiex 2>/dev/null \
        | grep -q "install ok installed"; then
    REINSTALAR="--reinstall"
fi
# shellcheck disable=SC2086
if ! sudo env DEBIAN_FRONTEND=noninteractive COPIEX_ACTUALIZAR=no \
        apt-get install -y $REINSTALAR "$DEB"; then
    echo "ERROR: no se pudo instalar $DEB." >&2
    exit 1
fi

echo
echo "Copiex actualizado:"
echo "  paquete: $DEB"
echo "  registro de dependencias: /var/log/copiex-dependencias.log"

if ps -eo pid=,args= \
        | awk '$2=="python3" && $3=="-m" && $4=="copiex" {visto=1} END {exit !visto}'
then
    echo
    echo "Copiex está abierto: ciérralo y vuelve a abrirlo para usar el código nuevo."
fi

if command -v nautilus >/dev/null 2>&1; then
    echo "Reinicia Nautilus para recargar la extensión:  nautilus -q"
fi
