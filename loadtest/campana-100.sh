#!/usr/bin/env bash
# Campaña del 100 % contra Docker Compose LOCAL (nunca contra Render ni Neon).
#
# Modalidad A (solicitudes ACUMULADAS): 10000, 20000, 30000 y 50000 solicitudes
# totales con 100 usuarios CONCURRENTES. Mezcla realista: cliente registrado que
# consulta, asesor que recorre la bandeja y visitantes anónimos del widget que
# conversan. Las solicitudes acumuladas y los usuarios concurrentes son cosas
# distintas: aquí la concurrencia es fija (100) y crece el volumen total.
#
# Uso:  loadtest/campana-100.sh [etiqueta]      (etiqueta: antes | despues)
# Los rate limits se suben al empezar y se restauran SIEMPRE al terminar.
set -uo pipefail
cd "$(dirname "$0")/.."
TAG=${1:-antes}
USERS=${USERS:-100}
trap 'loadtest/limites.sh normales' EXIT
loadtest/limites.sh altos

MIX="Lectura LecturaAsesor Widget"

for total in 10000 20000 30000 50000; do
  TOTAL_REQUESTS=$total loadtest/ejecutar.sh "C-${total}req-${TAG}" "$MIX" "$USERS" 20 30m
  sleep 15
done

# Recuperación después de la carga: la API debe seguir sana y responder rápido.
PORT=$(grep '^BACKEND_PORT=' .env | cut -d= -f2); PORT=${PORT:-8000}
echo "== recuperación (5 peticiones a /api/health/ tras la campaña)"
for _ in 1 2 3 4 5; do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" "http://127.0.0.1:${PORT}/api/health/"
done | tee "loadtest/resultados/$(date +%Y%m%d-%H%M%S)_C-recuperacion-${TAG}_consola.txt"
