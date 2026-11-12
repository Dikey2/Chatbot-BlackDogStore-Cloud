#!/usr/bin/env bash
# Prueba de carga controlada contra Render (ver locustfile_render.py).
# Uso: loadtest/render/ejecutar_render.sh <total_solicitudes> <usuarios>
set -euo pipefail
cd "$(dirname "$0")/../.."
# macOS: sin suspensión durante la prueba (incidencia 12.8-A de PRUEBAS.md).
if command -v caffeinate >/dev/null 2>&1 && [ -z "${CAFFEINATED:-}" ]; then
  exec env CAFFEINATED=1 caffeinate -i "$0" "$@"
fi
TOTAL=${1:?total de solicitudes}
USERS=${2:?usuarios concurrentes}
API=${API_URL:-https://chatbot-blackdogstore-cloud.onrender.com}
WEB=${FRONTEND_URL:-https://blackdog-chatbot-frontend.onrender.com}
OUT=loadtest/resultados/render
mkdir -p "$OUT"
TAG="$(date +%Y%m%d-%H%M%S)_R-${TOTAL}req-${USERS}u"

# 1. Despertar los servicios (Render Free se duerme): la prueba no debe medir el arranque.
for url in "$API/api/health/" "$WEB/login"; do
  for _ in $(seq 1 20); do
    code=$(curl -s -o /dev/null -m 60 -w "%{http_code}" "$url" || true)
    [ "$code" = 200 ] && break
    sleep 5
  done
  echo "despierto: $url -> $code"
  [ "$code" = 200 ] || { echo "El servicio no respondió 200: no se ejecuta la prueba."; exit 1; }
done

# 2. Prueba con Locust (contenedor; nada se instala en el equipo).
docker run --rm -v "$PWD/loadtest/render:/mnt/locust" -v "$PWD/$OUT:/mnt/out" -w /mnt/locust \
  -e TOTAL_REQUESTS="$TOTAL" -e FRONTEND_URL="$WEB" locustio/locust:2.46.7 \
  -f locustfile_render.py --headless --host "$API" --users "$USERS" --spawn-rate "$USERS" \
  --run-time 20m --csv "/mnt/out/$TAG" --html "/mnt/out/$TAG.html" --only-summary \
  2>&1 | tee "$OUT/${TAG}_consola.txt"

# 3. Recuperación: 5 peticiones de salud después de la carga.
echo "== recuperación" | tee -a "$OUT/${TAG}_consola.txt"
for _ in 1 2 3 4 5; do
  curl -s -o /dev/null -m 60 -w "%{http_code} %{time_total}s\n" "$API/api/health/"
done | tee -a "$OUT/${TAG}_consola.txt"
