#!/usr/bin/env bash
#
# MATCH IMPRO DIRECTOR · Comprobación del tablero web ya publicado
# -----------------------------------------------------------------------------
# Revisa que el despliegue haya quedado bien. Ejecútalo DESDE TU COMPUTADOR.
#
#   ./verificar.sh https://accionimpro.com.co/tablero/
#
# Corporación Acción Impro · Medellín, Colombia · 2026 · CC BY 4.0

set -uo pipefail

URL="${1:-}"
if [[ -z "$URL" ]]; then
  echo "Uso: ./verificar.sh https://tudominio.com/tablero/" >&2
  exit 2
fi
URL="${URL%/}/"

FALLOS=0
ok()    { echo "  ✓ $1"; }
fallo() { echo "  ✗ $1"; FALLOS=$((FALLOS + 1)); }

echo "Comprobando $URL"
echo

# 1. La página principal responde
CODIGO=$(curl -sS -o /tmp/mid_index.html -w '%{http_code}' -L --max-time 25 "$URL" 2>/dev/null)
if [[ "$CODIGO" == "200" ]]; then
  ok "la página responde (HTTP 200)"
else
  fallo "la página respondió HTTP $CODIGO (¿ruta correcta? ¿archivos subidos?)"
fi

# 2. Es realmente nuestro panel
if grep -q "MATCH IMPRO DIRECTOR" /tmp/mid_index.html 2>/dev/null; then
  ok "el contenido es el panel del operador"
else
  fallo "la respuesta no parece el panel (¿te devolvió una página de WordPress?)"
fi

# 3. HTTPS con certificado válido
if curl -sS -o /dev/null --max-time 25 "$URL" 2>/dev/null; then
  ok "el certificado HTTPS es válido"
else
  fallo "problema con HTTPS (revisa el SSL en hPanel)"
fi

# 4. Los módulos JavaScript se sirven con el tipo correcto
TIPO=$(curl -sSI --max-time 25 "${URL}js/panel.js" 2>/dev/null \
       | grep -i '^content-type:' | tr -d '\r' | cut -d' ' -f2-)
case "$TIPO" in
  *javascript*|*ecmascript*) ok "los .js se sirven como $TIPO" ;;
  "")  fallo "js/panel.js no se encontró (¿subiste la carpeta js/?)" ;;
  *)   fallo "js/panel.js se sirve como '$TIPO'; el navegador no lo ejecutará.
       Añade 'AddType application/javascript .js' al .htaccess" ;;
esac

# 5. El resto de archivos están donde toca
for RUTA in tablero.html css/estilos.css js/estado.js js/tablero.js js/almacen.js; do
  C=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "${URL}${RUTA}" 2>/dev/null)
  [[ "$C" == "200" ]] && ok "$RUTA" || fallo "$RUTA respondió HTTP $C"
done

# 6. La carpeta no lista su contenido
LISTADO=$(curl -sS --max-time 25 "${URL}js/" 2>/dev/null | head -c 400)
if echo "$LISTADO" | grep -qi "index of"; then
  fallo "el servidor lista el contenido de las carpetas (falta 'Options -Indexes')"
else
  ok "las carpetas no se listan públicamente"
fi

# 7. Compresión activa (afecta a la velocidad de carga)
if curl -sSI -H 'Accept-Encoding: gzip' --max-time 25 "${URL}js/panel.js" 2>/dev/null \
   | grep -qi '^content-encoding:.*gzip'; then
  ok "los archivos viajan comprimidos"
else
  echo "  · sin compresión gzip (opcional, pero acelera la primera carga)"
fi

# 8. Imagen de portada para compartir en redes
C=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "${URL}portada.png" 2>/dev/null)
if [[ "$C" == "200" ]]; then
  ok "portada.png presente (se verá al compartir el enlace)"
else
  echo "  · falta portada.png (1200×630) — el enlace se compartirá sin imagen"
fi

rm -f /tmp/mid_index.html
echo
if [[ $FALLOS -eq 0 ]]; then
  echo "Todo correcto. Abre $URL y pulsa «Abrir tablero» para la prueba final."
else
  echo "$FALLOS comprobación(es) fallaron. Revisa los puntos marcados con ✗."
  exit 1
fi
