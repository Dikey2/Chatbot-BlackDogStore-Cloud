#!/usr/bin/env bash
# Pruebas controladas de caídas. SOLO sobre Docker Compose local.
#
#   infra/pruebas/resiliencia.sh
#
# Para, pausa y reinicia contenedores, pero nunca borra volúmenes ni datos:
# usa `stop`, `pause` y `restart`, nunca `down -v` ni `rm`. Al terminar deja
# todos los servicios en marcha. La salida se guarda en docs/evidencias/.
set -uo pipefail
cd "$(dirname "$0")/../.."

[ "$(docker compose config --format json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')" = blackdog-chatbot ] \
  || { echo "Solo se ejecuta contra el proyecto local blackdog-chatbot." >&2; exit 1; }

mkdir -p docs/evidencias
LOG="docs/evidencias/resiliencia_$(date +%Y%m%d-%H%M%S).log"
exec > >(tee "$LOG") 2>&1

API=http://127.0.0.1:8000
WEB=http://127.0.0.1:3000
PASS=$(grep '^DEMO_PASSWORD=' .env | cut -d= -f2)
DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
FAILS=0

restore() {
  docker compose unpause chatbot backend >/dev/null 2>&1 || true
  docker compose start db chatbot backend frontend >/dev/null 2>&1 || true
}
trap restore EXIT

wait_healthy() {
  for _ in $(seq 1 90); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "blackdog-chatbot-$1-1" 2>/dev/null)" = healthy ] && return 0
    sleep 1
  done
  return 1
}

# status <método> <url> [datos] -> imprime "código cuerpo"
call() {
  local method=$1 url=$2 data=${3:-}
  local args=(-s -o /tmp/resiliencia_body -w '%{http_code} %{time_total}' -X "$method" --max-time 20)
  [ -n "${TOKEN:-}" ] && args+=(-H "Authorization: Token $TOKEN")
  [ -n "$data" ] && args+=(-H 'Content-Type: application/json' -d "$data")
  curl "${args[@]}" "$url"
}

check() { # check <descripción> <esperado> <obtenido>
  if [ "$2" = "$3" ]; then echo "  OK    $1 (esperado $2)"; else echo "  FALLA $1: esperado $2, obtenido $3"; FAILS=$((FAILS + 1)); fi
}

no_leak() { # el cuerpo no debe exponer detalles internos
  if grep -qiE 'traceback|psycopg|OperationalError|/usr/local/lib|SECRET|password' /tmp/resiliencia_body; then
    echo "  FALLA la respuesta expone detalles internos"; FAILS=$((FAILS + 1))
  else
    echo "  OK    sin detalles internos en la respuesta"
  fi
}

counts() {
  docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc \
    "select (select count(*) from users_user)||' usuarios, '||(select count(*) from chat_conversation)||' conversaciones, '||(select count(*) from chat_message)||' mensajes'"
}

echo "== Inicio $(date '+%F %T')"
for s in db chatbot backend frontend; do wait_healthy "$s" || echo "  aviso: $s no está healthy"; done
echo "Datos antes: $(counts)"
TOKEN=$(curl -s -X POST "$API/api/auth/login/" -H 'Content-Type: application/json' \
  -d "{\"email\":\"cliente@example.com\",\"password\":\"$PASS\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
COOKIE="session=$TOKEN"
MSG='{"message":"¿Cuál es el horario de atención?"}'

echo; echo "== 1. Chatbot detenido"
docker compose stop chatbot >/dev/null
read -r code _ <<<"$(TOKEN= call GET "$API/api/health/")"; check "health sin chatbot" 503 "$code"
grep -q '"chatbot":"error"' /tmp/resiliencia_body && echo "  OK    health indica chatbot=error"
before=$(counts)
read -r code _ <<<"$(call POST "$API/api/chat/messages/" "$MSG")"; check "enviar mensaje" 503 "$code"
grep -q chatbot_unavailable /tmp/resiliencia_body && echo "  OK    código chatbot_unavailable"
no_leak
check "no se guardó nada" "$before" "$(counts)"
docker compose start chatbot >/dev/null; wait_healthy chatbot
read -r code _ <<<"$(call POST "$API/api/chat/messages/" "$MSG")"; check "chat tras reiniciar chatbot" 201 "$code"

echo; echo "== 2. Chatbot congelado (tiempo de espera de 3 s)"
docker compose pause chatbot >/dev/null
read -r code time <<<"$(call POST "$API/api/chat/messages/" "$MSG")"
check "mensaje con chatbot congelado" 503 "$code"; echo "  tiempo de respuesta: ${time}s (límite del backend: 3 s)"
docker compose unpause chatbot >/dev/null

echo; echo "== 3. PostgreSQL detenido"
docker compose stop db >/dev/null
read -r code _ <<<"$(TOKEN= call GET "$API/api/health/")"; check "health sin base" 503 "$code"
grep -q '"database":"error"' /tmp/resiliencia_body && echo "  OK    health indica database=error"
read -r code _ <<<"$(TOKEN= call GET "$API/api/faqs/")"; check "listar FAQ sin base" 500 "$code"
grep -q server_error /tmp/resiliencia_body && echo "  OK    código server_error genérico"
no_leak
page=$(curl -s --max-time 20 -b "$COOKIE" "$WEB/chat")
echo "$page" | grep -q 'data-testid="service-unavailable"' && echo "  OK    /chat muestra la pantalla de servicio no disponible" || { echo "  FALLA /chat sin pantalla de caída"; FAILS=$((FAILS + 1)); }
docker compose start db >/dev/null; wait_healthy db
sleep 2
read -r code _ <<<"$(TOKEN= call GET "$API/api/faqs/")"; check "FAQ tras volver la base (sin reiniciar el backend)" 200 "$code"

echo; echo "== 4. Backend detenido y congelado (vista desde el frontend)"
docker compose stop backend >/dev/null
page=$(curl -s --max-time 20 -b "$COOKIE" "$WEB/chat")
echo "$page" | grep -q 'data-reason="unavailable"' && echo "  OK    backend detenido: pantalla 'Servicio no disponible'" || { echo "  FALLA backend detenido"; FAILS=$((FAILS + 1)); }
docker compose start backend >/dev/null; wait_healthy backend
docker compose pause backend >/dev/null
start=$(date +%s)
page=$(curl -s --max-time 30 -b "$COOKIE" "$WEB/chat")
echo "$page" | grep -q 'data-reason="timeout"' && echo "  OK    backend congelado: pantalla 'El servidor tardó demasiado' en $(( $(date +%s) - start )) s" || { echo "  FALLA backend congelado"; FAILS=$((FAILS + 1)); }
docker compose unpause backend >/dev/null

echo; echo "== 5. Caída del proceso principal del backend (reinicio automático)"
# La imagen no incluye el binario kill: se usa el de sh. Se exige un reinicio real.
started=$(docker inspect -f '{{.State.StartedAt}}' blackdog-chatbot-backend-1)
docker compose exec -T backend sh -c 'kill 1' || { echo "  FALLA no se pudo enviar la señal"; FAILS=$((FAILS + 1)); }
sleep 5
restarted=$(docker inspect -f '{{.State.StartedAt}}' blackdog-chatbot-backend-1)
restarts=$(docker inspect -f '{{.RestartCount}}' blackdog-chatbot-backend-1)
if [ "$restarted" != "$started" ] && wait_healthy backend; then
  echo "  OK    el proceso terminó y Docker reinició el backend (RestartCount=$restarts)"
else
  echo "  FALLA el backend no se reinició"; FAILS=$((FAILS + 1))
fi
read -r code _ <<<"$(TOKEN= call GET "$API/api/health/")"; check "health tras el reinicio" 200 "$code"

echo; echo "== 6. Reinicio del backend con carga (Locust, 20 usuarios de lectura, 40 s)"
# Rate limits altos solo durante esta parte: los 20 usuarios salen de una misma IP.
loadtest/limites.sh altos >/dev/null 2>&1
DEMO_PASSWORD=$PASS TOTAL_REQUESTS=0 docker compose -f docker-compose.yml -f docker-compose.loadtest.yml \
  --profile loadtest run --rm --no-deps -T locust -f locustfile.py --headless --users 20 --spawn-rate 20 \
  --run-time 40s --host http://backend:8000 --only-summary Lectura > /tmp/resiliencia_locust.txt 2>&1 &
LOCUST=$!
sleep 15; echo "  reinicio del backend a los 15 s"; docker compose restart backend >/dev/null
wait $LOCUST
grep -m1 Aggregated /tmp/resiliencia_locust.txt | sed 's/^/  /'
grep -A20 'Error report' /tmp/resiliencia_locust.txt | sed 's/^/  /'

echo; echo "== 7. Recarga en caliente de gunicorn (señal HUP) con la misma carga"
wait_healthy backend
DEMO_PASSWORD=$PASS TOTAL_REQUESTS=0 docker compose -f docker-compose.yml -f docker-compose.loadtest.yml \
  --profile loadtest run --rm --no-deps -T locust -f locustfile.py --headless --users 20 --spawn-rate 20 \
  --run-time 40s --host http://backend:8000 --only-summary Lectura > /tmp/resiliencia_hup.txt 2>&1 &
LOCUST=$!
sleep 15; echo "  señal HUP a los 15 s (gunicorn renueva sus procesos sin cerrar el puerto)"
docker compose kill -s HUP backend >/dev/null
wait $LOCUST
grep -m1 Aggregated /tmp/resiliencia_hup.txt | sed 's/^/  /'
grep -A6 'Error report' /tmp/resiliencia_hup.txt | sed 's/^/  /'
loadtest/limites.sh normales | tail -1 | sed 's/^/  restaurados /'
wait_healthy backend
read -r code _ <<<"$(TOKEN= call GET "$API/api/health/")"; check "health al terminar" 200 "$code"

echo; echo "Datos después: $(counts)"
echo "== Fin $(date '+%F %T'): $FAILS fallas"
echo "Evidencia: $LOG"
