#!/bin/sh
# Instalación de Copiex en el usuario actual (sin privilegios):
#   · fichero .desktop para lanzarlo con doble clic
#   · extensión de Nautilus (copiar/pegar con Copiex)
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APLICACIONES="$HOME/.local/share/applications"
EXTENSIONES="$HOME/.local/share/nautilus-python/extensions"

# 0) el script tiene que seguir viviendo junto al proyecto
if [ ! -f "$DIR/copiex/nautilus_extension.py" ] || [ ! -f "$DIR/copiex-launcher" ]; then
    echo "ERROR: no encuentro el proyecto Copiex junto a este script." >&2
    echo "       Ejecútalo desde la carpeta del proyecto: ./install.sh" >&2
    exit 1
fi

# 0 bis) dependencias de ejecución: sin PyGObject, GTK 4 y libadwaita la
# aplicación no arranca, y es mejor decirlo aquí que al hacer doble clic.
FALTAN=$(
    python3 - 2>/dev/null <<'PY' || echo "python3"
import sys

paquetes = []
try:
    import gi
except Exception:
    print("python3-gi")
    sys.exit(0)

for espacio, version, paquete in (
    ("Gtk", "4.0", "gir1.2-gtk-4.0"),
    ("Adw", "1", "gir1.2-adw-1"),
):
    try:
        gi.require_version(espacio, version)
        __import__(f"gi.repository.{espacio}", fromlist=[espacio])
    except Exception:
        paquetes.append(paquete)
print(" ".join(paquetes))
PY
)
if [ -n "$FALTAN" ]; then
    echo "AVISO: faltan dependencias para ejecutar Copiex: $FALTAN" >&2
    echo "       Instálalas con:  sudo apt install $FALTAN" >&2
fi

mkdir -p "$APLICACIONES" "$EXTENSIONES"
chmod +x "$DIR/copiex-launcher"

# 1) entrada de escritorio con la ruta absoluta al lanzador
sed "s|@EJECUTABLE@|$DIR/copiex-launcher|" "$DIR/com.copiex.Manager.desktop.in" \
    > "$APLICACIONES/com.copiex.Manager.desktop"
chmod +x "$APLICACIONES/com.copiex.Manager.desktop"
command -v gio >/dev/null 2>&1 \
    && gio set "$APLICACIONES/com.copiex.Manager.desktop" metadata::trusted true \
        >/dev/null 2>&1 || true
command -v update-desktop-database >/dev/null 2>&1 \
    && update-desktop-database "$APLICACIONES" >/dev/null 2>&1 || true

# 2) extensión de Nautilus
cp "$DIR/copiex/nautilus_extension.py" "$EXTENSIONES/copiex.py"

if ! cmp -s "$DIR/copiex/nautilus_extension.py" "$EXTENSIONES/copiex.py"; then
    echo "ERROR: la extensión copiada no coincide con la del proyecto." >&2
    exit 1
fi

echo "Copiex instalado:"
echo "  lanzador:   $DIR/copiex-launcher"
echo "  escritorio: $APLICACIONES/com.copiex.Manager.desktop"
echo "  extensión:  $EXTENSIONES/copiex.py"

# 3) comprobación de la extensión de Nautilus (única dependencia de sistema).
#    Ubuntu 24.04 trae la API 4.0 (Nautilus 46) y Ubuntu 26.04 la 4.1
#    (Nautilus 50); se acepta cualquiera de las dos.
VERSION_NAUTILUS=$(
    python3 - 2>/dev/null <<'PY' || true
import gi

for version in ("4.1", "4.0"):
    try:
        gi.require_version("Nautilus", version)
        from gi.repository import Nautilus  # noqa: F401
    except Exception:
        continue
    print(version)
    break
PY
)

if [ -z "$VERSION_NAUTILUS" ]; then
    echo
    echo "AVISO: falta python3-nautilus, necesario para que aparezcan"
    echo "       «Copiar con Copiex» y «Pegar con Copiex» en Nautilus:"
    echo "           sudo apt install python3-nautilus"
    echo "       (en Ubuntu 24.04 y 26.04 el paquete se llama igual)"
    echo "       Después reinicia el gestor de archivos:  nautilus -q"
else
    echo
    echo "API de Nautilus disponible: $VERSION_NAUTILUS"
    echo "Reinicia Nautilus para cargar la extensión:  nautilus -q"
fi

# 4) si la aplicación ya estaba abierta, sigue con el código anterior en memoria
if ps -eo pid=,args= \
        | awk '$2=="python3" && $3=="-m" && $4=="copiex" {visto=1} END {exit !visto}'
then
    echo "Copiex está en marcha: ciérralo y vuelve a abrirlo para estrenar los cambios."
fi

echo
echo "Para desinstalarlo por completo:  ./uninstall.sh"
