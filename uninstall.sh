#!/bin/sh
# Desinstalación completa de Copiex en el usuario actual (sin privilegios).
#
# Quita:
#   · la extensión de Nautilus (menús «Copiar con Copiex» y «Pegar con Copiex»)
#   · la entrada de escritorio y su registro en el sistema
#   · la aplicación en marcha y su socket
#   · los datos (historial y registros), salvo con --conservar-datos
#
# Uso:
#   ./uninstall.sh                    pregunta antes de borrar
#   ./uninstall.sh --si               sin preguntar
#   ./uninstall.sh --conservar-datos  deja ~/.local/share/copiex (historial y logs)
#   ./uninstall.sh --simular          enseña lo que borraría, sin tocar nada
set -eu

SI=0
CONSERVAR=0
SIMULAR=0

for arg in "$@"; do
    case "$arg" in
        --si|-y) SI=1 ;;
        --conservar-datos) CONSERVAR=1 ;;
        --simular|-n) SIMULAR=1 ;;
        -h|--ayuda)
            sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Opción desconocida: $arg (usa --ayuda)" >&2
            exit 2
            ;;
    esac
done

EXTENSIONES="$HOME/.local/share/nautilus-python/extensions"
APLICACIONES="$HOME/.local/share/applications"
ICONOS="$HOME/.local/share/icons/hicolor/scalable/apps"
DATOS="$HOME/.local/share/copiex"
CONFIG="$HOME/.config/copiex"
AUTOSTART="$HOME/.config/autostart/com.copiex.Manager.desktop"
RUNTIME="${XDG_RUNTIME_DIR:-/tmp}/copiex-$(id -u)"

borrar() {
    # borrar RUTA: informa y elimina (o simula)
    if [ ! -e "$1" ] && [ ! -L "$1" ]; then
        return 0
    fi
    if [ "$SIMULAR" -eq 1 ]; then
        echo "  (simulado) borraría $1"
        return 0
    fi
    rm -rf -- "$1"
    echo "  borrado: $1"
}

parar_aplicacion() {
    # Se buscan procesos python3 -m copiex por campos exactos: nunca se usa
    # pkill -f, que también casaría con la línea de comandos de este script.
    pids=$(ps -eo pid=,args= | awk '$2=="python3" && $3=="-m" && $4=="copiex" {print $1}')
    [ -n "$pids" ] || return 0
    if [ "$SIMULAR" -eq 1 ]; then
        echo "  (simulado) cerraría Copiex (pid $(echo $pids))"
        return 0
    fi
    echo "  cerrando Copiex (pid $(echo $pids))"
    kill $pids 2>/dev/null || true
    i=0
    while [ "$i" -lt 30 ]; do
        vivos=""
        for pid in $pids; do
            kill -0 "$pid" 2>/dev/null && vivos="$vivos $pid"
        done
        [ -z "$vivos" ] && return 0
        sleep 0.1
        i=$((i + 1))
    done
    for pid in $pids; do
        kill -9 "$pid" 2>/dev/null || true
    done
}

echo "Se va a desinstalar Copiex:"
echo "  extensión:  $EXTENSIONES/copiex.py"
echo "  escritorio: $APLICACIONES/com.copiex.Manager.desktop"
echo "  iconos:     $ICONOS/com.copiex.Manager.svg"
echo "  socket:     $RUNTIME"
if [ "$CONSERVAR" -eq 1 ]; then
    echo "  datos:      se CONSERVAN ($DATOS)"
else
    echo "  datos:      $DATOS (historial y registros)"
fi
[ "$SIMULAR" -eq 1 ] && echo "  modo:       simulación (no se borra nada)"

if [ "$SI" -eq 0 ] && [ "$SIMULAR" -eq 0 ]; then
    printf '¿Continuar? [s/N] '
    respuesta=""
    read -r respuesta || true
    case "$respuesta" in
        s|S|si|Si|SI|y|Y) ;;
        *)
            echo "Cancelado: no se ha tocado nada."
            exit 1
            ;;
    esac
fi

parar_aplicacion
borrar "$EXTENSIONES/copiex.py"
for pyc in "$EXTENSIONES"/__pycache__/copiex.*.pyc; do
    [ -e "$pyc" ] || continue
    borrar "$pyc"
done
if [ "$SIMULAR" -eq 0 ]; then
    rmdir "$EXTENSIONES/__pycache__" 2>/dev/null || true
fi
borrar "$APLICACIONES/com.copiex.Manager.desktop"
borrar "$ICONOS/com.copiex.Manager.svg"
borrar "$ICONOS/com.copiex.Manager-symbolic.svg"
borrar "$AUTOSTART"
borrar "$RUNTIME"
if [ "$CONSERVAR" -eq 1 ]; then
    echo "  conservado: $DATOS"
else
    borrar "$DATOS"
fi
borrar "$CONFIG"

if [ "$SIMULAR" -eq 0 ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APLICACIONES" >/dev/null 2>&1 || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" \
            >/dev/null 2>&1 || true
    fi
    # Nautilus guarda las extensiones en memoria: sin reiniciarlo, los menús
    # «Copiar/Pegar con Copiex» seguirían apareciendo hasta cerrar el gestor.
    if command -v nautilus >/dev/null 2>&1; then
        echo "  reiniciando Nautilus para retirar las entradas del menú…"
        nautilus -q >/dev/null 2>&1 || true
    fi
fi

if [ "$SIMULAR" -eq 1 ]; then
    echo "Simulación terminada: no se ha borrado nada."
    exit 0
fi

restos=""
for ruta in "$EXTENSIONES/copiex.py" \
            "$APLICACIONES/com.copiex.Manager.desktop" \
            "$RUNTIME"; do
    [ -e "$ruta" ] && restos="$restos $ruta"
done
if [ -n "$restos" ]; then
    echo "AVISO: no se pudieron borrar:$restos" >&2
    exit 1
fi

echo
echo "Copiex desinstalado."
echo "  · El paquete de sistema python3-nautilus NO se toca (lo pueden usar"
echo "    otras extensiones); si quieres quitarlo: sudo apt remove python3-nautilus"
if [ "$CONSERVAR" -eq 1 ]; then
    echo "  · Datos conservados en $DATOS (borra esa carpeta para eliminarlos)."
fi
