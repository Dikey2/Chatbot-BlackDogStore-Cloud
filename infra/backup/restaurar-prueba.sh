#!/usr/bin/env bash
# Prueba de restauración en una base TEMPORAL y aislada del contenedor local.
# Nunca escribe en la base principal.
#
#   infra/backup/restaurar-prueba.sh backups/local_20261029-150000.dump [--conservar]
#
# 1. Verifica la suma SHA-256 del respaldo.
# 2. Crea la base temporal restore_<fecha> y restaura el respaldo en ella.
# 3. Compara el número de filas de las tablas principales con la base de origen.
# 4. Elimina la base temporal (salvo con --conservar).
set -euo pipefail
cd "$(dirname "$0")/../.."

FILE=${1:?Indique el archivo .dump}
KEEP=${2:-}
DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
TARGET="restore_$(date +%Y%m%d_%H%M%S)"

if [ "$TARGET" = "$DB_NAME" ]; then
  echo "La base temporal no puede llamarse igual que la principal." >&2
  exit 1
fi

( cd "$(dirname "$FILE")" && shasum -a 256 -c "$(basename "$FILE").sha256" )

psql_db() { docker compose exec -T db psql -v ON_ERROR_STOP=1 -U "$DB_USER" "$@"; }

cleanup() {
  if [ "$KEEP" != "--conservar" ]; then
    psql_db -d postgres -qc "DROP DATABASE IF EXISTS $TARGET;" && echo "Base temporal $TARGET eliminada."
  fi
}
trap cleanup EXIT

psql_db -d postgres -qc "CREATE DATABASE $TARGET;"
docker compose exec -T db pg_restore --no-owner --no-privileges --exit-on-error \
  -U "$DB_USER" -d "$TARGET" < "$FILE"
echo "Restaurado en $TARGET."

COUNT_SQL="select 'users_user', count(*) from users_user
  union all select 'chat_conversation', count(*) from chat_conversation
  union all select 'chat_message', count(*) from chat_message
  union all select 'faqs_faq', count(*) from faqs_faq
  union all select 'audit_auditevent', count(*) from audit_auditevent
  union all select 'django_migrations', count(*) from django_migrations
  order by 1;"

restored=$(psql_db -d "$TARGET" -tAF' ' -c "$COUNT_SQL")
echo "Filas restauradas:"
echo "$restored" | sed 's/^/  /'

if [ "${COMPARE_WITH_SOURCE:-1}" = 1 ]; then
  source=$(psql_db -d "$DB_NAME" -tAF' ' -c "$COUNT_SQL")
  if [ "$restored" = "$source" ]; then
    echo "Resultado: coincide con la base de origen."
  else
    echo "Aviso: la base de origen cambió desde el respaldo (es normal si siguió en uso):"
    echo "$source" | sed 's/^/  origen /'
  fi
fi
