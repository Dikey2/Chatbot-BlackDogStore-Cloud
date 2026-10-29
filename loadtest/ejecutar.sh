#!/usr/bin/env bash
# Ejecuta UN escenario de Locust contra Docker Compose local y registra recursos.
#
# Uso:
#   loadtest/ejecutar.sh NOMBRE "CLASES" USUARIOS TASA_ALTA [DURACION]
#
#   TOTAL_REQUESTS=1000 loadtest/ejecutar.sh A-1000-lectura "Lectura LecturaAsesor" 50 10
#   TOTAL_REQUESTS=0    loadtest/ejecutar.sh B-100u-escritura Escritura 100 10 60s
#
# Requisito: backend levantado con docker-compose.loadtest.yml (rate limits altos).
# Usar loadtest/campana.sh, que además restaura los límites normales al terminar.
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=$1; CLASSES=$2; USERS=$3; SPAWN=$4; RUNTIME=${5:-15m}
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="resultados/${STAMP}_${NAME}"
DIR=loadtest
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.loadtest.yml --profile loadtest)

DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)

# No empezar hasta que Docker marque el backend como "healthy" (tras un reinicio,
# gunicorn tarda unos segundos en aceptar conexiones).
for _ in $(seq 1 90); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' blackdog-chatbot-backend-1 2>/dev/null)" = healthy ] && break
  sleep 1
done
ok=0
for _ in $(seq 1 90); do
  if curl -fs http://127.0.0.1:8000/api/health/ >/dev/null; then ok=$((ok + 1)); else ok=0; fi
  [ "$ok" -ge 3 ] && break
  sleep 1
done

# Muestreo de CPU, memoria y conexiones a PostgreSQL cada ~3 s.
sample() {
  echo "hora,contenedor,cpu,memoria,conexiones_pg" > "$DIR/${OUT}_recursos.csv"
  while true; do
    local now conns
    now=$(date +%H:%M:%S)
    conns=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc \
      "select count(*) from pg_stat_activity where datname = current_database()" 2>/dev/null || echo "")
    docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' \
      blackdog-chatbot-backend-1 blackdog-chatbot-db-1 blackdog-chatbot-chatbot-1 2>/dev/null \
      | sed "s|^|$now,|; s|$|,$conns|" >> "$DIR/${OUT}_recursos.csv"
    sleep 1
  done
}
sample & SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT

echo "== $NAME: clases=$CLASSES usuarios=$USERS tasa=$SPAWN total=${TOTAL_REQUESTS:-0} duracion_max=$RUNTIME"
# shellcheck disable=SC2086
TOTAL_REQUESTS=${TOTAL_REQUESTS:-0} "${COMPOSE[@]}" run --rm --no-deps -T locust \
  -f locustfile.py --headless --users "$USERS" --spawn-rate "$SPAWN" --run-time "$RUNTIME" \
  --host http://backend:8000 --csv "$OUT" --html "$OUT.html" --only-summary $CLASSES \
  2>&1 | grep -v 'I/O operation on closed file' | tee "$DIR/${OUT}_consola.txt" | tail -14
