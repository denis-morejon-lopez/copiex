# Entorno de Ubuntu donde se instala Copiex.
#
# Lo leen el postinst y /usr/lib/copiex/instalar-dependencias para decidir qué
# hacer en cada versión de Ubuntu. Define:
#
#   COPIEX_ID              ubuntu (o el ID de /etc/os-release)
#   COPIEX_VERSION_UBUNTU  24.04, 26.04, o la que haya
#   COPIEX_SUITE           noble, resolute, o vacío
#   COPIEX_NAUTILUS_API    4.0 en 24.04 y 4.1 en 26.04 ("" si no se reconoce)
#   COPIEX_NAUTILUS_MIN    Nautilus de esa Ubuntu (46, 50)
#   COPIEX_GTK_MIN         GTK 4 de esa Ubuntu (4.14, 4.22)
#   COPIEX_ADW_MIN         libadwaita de esa Ubuntu (1.5, 1.8)
#   COPIEX_REPO_OFFLINE    /usr/share/copiex/offline/ubuntu-<versión>
#   COPIEX_TRAE_REPO       si/no: ¿el paquete trae el repositorio de esta versión?
#
# Para probar la detección de otra versión sin tenerla:
#
#   COPIEX_OS_RELEASE=/tmp/os-release-26.04 sh -c '. plataforma.sh; echo $COPIEX_SUITE'
COPIEX_OS_RELEASE=${COPIEX_OS_RELEASE:-/etc/os-release}

_copiex_campos=$(
    # shellcheck disable=SC1090
    . "$COPIEX_OS_RELEASE" >/dev/null 2>&1 || exit 0
    printf '%s\n%s\n' "${ID:-}" "${VERSION_ID:-}"
)
COPIEX_ID=$(printf '%s\n' "$_copiex_campos" | sed -n 1p)
COPIEX_VERSION_UBUNTU=$(printf '%s\n' "$_copiex_campos" | sed -n 2p)
unset _copiex_campos

COPIEX_SUITE=""
COPIEX_NAUTILUS_API=""
COPIEX_NAUTILUS_MIN=""
COPIEX_GTK_MIN=""
COPIEX_ADW_MIN=""

# Lo que cambia entre versiones de Ubuntu. Nautilus 46 (24.04) usa la typelib
# 4.0 y Nautilus 50 (26.04) la 4.1; GTK y libadwaita también suben de versión.
case "$COPIEX_VERSION_UBUNTU" in
    24.04)
        COPIEX_SUITE=noble
        COPIEX_NAUTILUS_API=4.0
        COPIEX_NAUTILUS_MIN=46
        COPIEX_GTK_MIN=4.14
        COPIEX_ADW_MIN=1.5
        ;;
    26.04)
        COPIEX_SUITE=resolute
        COPIEX_NAUTILUS_API=4.1
        COPIEX_NAUTILUS_MIN=50
        COPIEX_GTK_MIN=4.22
        COPIEX_ADW_MIN=1.8
        ;;
esac

COPIEX_REPO_OFFLINE=/usr/share/copiex/offline/ubuntu-${COPIEX_VERSION_UBUNTU}
if [ -n "$COPIEX_VERSION_UBUNTU" ] && [ -d "$COPIEX_REPO_OFFLINE" ]; then
    COPIEX_TRAE_REPO=si
else
    COPIEX_TRAE_REPO=no
fi

# Una línea para el registro con lo detectado y lo que se va a hacer.
copiex_describe_plataforma() {
    if [ -n "$COPIEX_NAUTILUS_API" ]; then
        incluido=no
        [ "$COPIEX_TRAE_REPO" = si ] && incluido=si
        printf '%s %s (%s): dependencias offline incluidas: %s; extensión de Nautilus para la API %s (Nautilus %s, GTK %s, libadwaita %s)\n' \
            "${COPIEX_ID:-linux}" "$COPIEX_VERSION_UBUNTU" "$COPIEX_SUITE" "$incluido" \
            "$COPIEX_NAUTILUS_API" "$COPIEX_NAUTILUS_MIN" \
            "$COPIEX_GTK_MIN" "$COPIEX_ADW_MIN"
    else
        incluido=no
        [ "$COPIEX_TRAE_REPO" = si ] && incluido=si
        printf '%s %s: versión no reconocida; dependencias offline incluidas: %s\n' \
            "${COPIEX_ID:-linux}" "${COPIEX_VERSION_UBUNTU:-desconocida}" "$incluido"
    fi
}
