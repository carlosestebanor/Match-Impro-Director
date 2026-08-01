#!/usr/bin/env bash
#
# MATCH IMPRO DIRECTOR · Despliegue del tablero web en Hostinger
# -----------------------------------------------------------------------------
# Sube la carpeta `web/` a tu hosting por SSH. Ejecútalo DESDE TU COMPUTADOR,
# no desde el servidor.
#
#   ./desplegar.sh                 → simulacro: enseña qué haría, sin tocar nada
#   ./desplegar.sh --aplicar       → sube los archivos de verdad
#   ./desplegar.sh --empaquetar    → genera un ZIP para subir a mano por hPanel
#
# Configuración (sácala de hPanel → Avanzado → Acceso SSH):
#
#   export HOSTINGER_USUARIO=u123456789
#   export HOSTINGER_SERVIDOR=193.203.xxx.xxx
#   export HOSTINGER_PUERTO=65002
#   export HOSTINGER_DESTINO=domains/accionimpro.com.co/public_html/tablero
#
# Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODO="simulacro"

for arg in "$@"; do
  case "$arg" in
    --aplicar)    MODO="aplicar" ;;
    --empaquetar) MODO="empaquetar" ;;
    -h|--help)    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción desconocida: $arg (usa --help)" >&2; exit 2 ;;
  esac
done

# Solo estos archivos forman la aplicación. Cualquier otra cosa que haya en la
# carpeta (capturas, notas, este mismo script) se queda fuera del despliegue.
ARCHIVOS=(
  index.html
  tablero.html
  .htaccess
  css/estilos.css
  js/estado.js
  js/tablero.js
  js/panel.js
  js/almacen.js
)

comprobar_archivos() {
  local faltan=0
  for f in "${ARCHIVOS[@]}"; do
    if [[ ! -f "$AQUI/$f" ]]; then
      echo "  ✗ falta $f" >&2
      faltan=1
    fi
  done
  [[ $faltan -eq 0 ]] || { echo "Despliegue abortado: faltan archivos." >&2; exit 1; }
  echo "  ✓ los ${#ARCHIVOS[@]} archivos de la aplicación están presentes"
}

# ---------------------------------------------------------------- empaquetar
if [[ "$MODO" == "empaquetar" ]]; then
  echo "Empaquetando el tablero web…"
  comprobar_archivos
  DESTINO="$AQUI/../tablero-web.zip"
  rm -f "$DESTINO"
  (cd "$AQUI" && zip -q -r "$DESTINO" "${ARCHIVOS[@]}")
  echo
  echo "Listo: $(cd "$(dirname "$DESTINO")" && pwd)/tablero-web.zip"
  echo
  echo "Para subirlo a mano:"
  echo "  1. hPanel → Archivos → Administrador de archivos"
  echo "  2. Entra en public_html y crea la carpeta 'tablero'"
  echo "  3. Sube el ZIP dentro y usa «Extraer»"
  echo "  4. Borra el ZIP del servidor"
  exit 0
fi

# ------------------------------------------------------------- comprobaciones
: "${HOSTINGER_USUARIO:?Define HOSTINGER_USUARIO (ej. u123456789)}"
: "${HOSTINGER_SERVIDOR:?Define HOSTINGER_SERVIDOR (IP o dominio del hosting)}"
PUERTO="${HOSTINGER_PUERTO:-65002}"
: "${HOSTINGER_DESTINO:?Define HOSTINGER_DESTINO (ruta remota que terminará en /tablero)}"

# Salvaguarda: nunca sincronizar contra la raíz del sitio. Este script usa
# --delete, así que apuntar a public_html borraría WordPress entero.
case "$HOSTINGER_DESTINO" in
  */public_html|*/public_html/|public_html|public_html/|/|"")
    echo "ERROR: HOSTINGER_DESTINO apunta a la raíz del sitio ($HOSTINGER_DESTINO)." >&2
    echo "       Debe ser una subcarpeta propia, por ejemplo .../public_html/tablero" >&2
    exit 1 ;;
esac
if [[ "$HOSTINGER_DESTINO" != */tablero* ]]; then
  echo "AVISO: la ruta de destino no contiene 'tablero'. Revísala con calma:" >&2
  echo "       $HOSTINGER_DESTINO" >&2
  read -r -p "¿Continuar de todos modos? [s/N] " respuesta
  [[ "$respuesta" == "s" || "$respuesta" == "S" ]] || exit 1
fi

command -v rsync >/dev/null || { echo "Falta rsync. Instálalo o usa --empaquetar." >&2; exit 1; }

echo "Destino : $HOSTINGER_USUARIO@$HOSTINGER_SERVIDOR:$HOSTINGER_DESTINO (puerto $PUERTO)"
echo "Origen  : $AQUI"
echo
comprobar_archivos
echo

OPCIONES=(-avz --delete --chmod=D755,F644 -e "ssh -p $PUERTO")
if [[ "$MODO" == "simulacro" ]]; then
  OPCIONES+=(--dry-run)
  echo "MODO SIMULACRO — no se modifica nada. Añade --aplicar para subir de verdad."
  echo
else
  echo "MODO REAL — se sincronizará la carpeta remota (los archivos sobrantes se borrarán)."
  read -r -p "¿Confirmas el despliegue? [s/N] " respuesta
  [[ "$respuesta" == "s" || "$respuesta" == "S" ]] || { echo "Cancelado."; exit 0; }
  echo
fi

# Crea la carpeta remota si aún no existe (inofensivo si ya está).
if [[ "$MODO" == "aplicar" ]]; then
  ssh -p "$PUERTO" "$HOSTINGER_USUARIO@$HOSTINGER_SERVIDOR" \
      "mkdir -p '$HOSTINGER_DESTINO'"
fi

# Se envían solo los archivos de la lista, respetando la estructura de carpetas.
rsync "${OPCIONES[@]}" \
  --relative \
  "${ARCHIVOS[@]/#/$AQUI/./}" \
  "$HOSTINGER_USUARIO@$HOSTINGER_SERVIDOR:$HOSTINGER_DESTINO/"

echo
if [[ "$MODO" == "simulacro" ]]; then
  echo "Simulacro terminado. Repite con --aplicar cuando la lista de arriba te cuadre."
else
  echo "Despliegue terminado."
  echo "Comprueba el resultado con:  ./verificar.sh https://accionimpro.com.co/tablero/"
fi
