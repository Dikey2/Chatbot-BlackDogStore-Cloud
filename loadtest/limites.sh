#!/usr/bin/env bash
# Cambia los rate limits del backend LOCAL para las pruebas de carga.
#   loadtest/limites.sh altos     -> 100000/min (docker-compose.loadtest.yml)
#   loadtest/limites.sh normales  -> valores de .env (restaurar SIEMPRE al terminar)
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  altos)    docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d backend ;;
  normales) docker compose up -d backend ;;
  *) echo "uso: $0 altos|normales" >&2; exit 2 ;;
esac
# Espera a que la API responda antes de seguir.
for _ in $(seq 1 60); do
  curl -fs http://127.0.0.1:8000/api/health/ >/dev/null && break
  sleep 1
done
docker compose exec -T backend python manage.py shell -v 0 -c \
  "from django.conf import settings as s; print('rate limits:', s.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'])"
