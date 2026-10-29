#!/usr/bin/env bash
# Respaldo de PostgreSQL con fecha y hora, suma SHA-256 y retención.
#
#   infra/backup/respaldar.sh            # base LOCAL de Docker Compose
#   infra/backup/respaldar.sh --neon     # base de Neon (lee NEON_DATABASE_URL del entorno)
#
# Variables opcionales:
#   BACKUP_DIR   carpeta de destino (por defecto ./backups, fuera de Git)
#   BACKUP_KEEP  cuántos respaldos conservar (por defecto 7)
#
# Seguridad: las credenciales se leen de .env o del entorno y nunca se escriben
# en el respaldo, en el nombre del archivo ni en la salida del script.
set -euo pipefail
cd "$(dirname "$0")/../.."

BACKUP_DIR=${BACKUP_DIR:-backups}
BACKUP_KEEP=${BACKUP_KEEP:-7}
STAMP=$(date +%Y%m%d-%H%M%S)
umask 077
mkdir -p "$BACKUP_DIR"

if [ "${1:-}" = "--neon" ]; then
  : "${NEON_DATABASE_URL:?Defina NEON_DATABASE_URL (no se guarda en el repositorio)}"
  FILE="$BACKUP_DIR/neon_${STAMP}.dump"
  # pg_dump 17 en un contenedor temporal; la URL viaja como variable, no como argumento visible.
  docker run --rm -e NEON_DATABASE_URL postgres:17-alpine \
    sh -c 'pg_dump --format=custom --no-owner --no-privileges "$NEON_DATABASE_URL"' > "$FILE"
  PREFIX=neon
else
  DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
  DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
  FILE="$BACKUP_DIR/local_${STAMP}.dump"
  docker compose exec -T db pg_dump --format=custom --no-owner --no-privileges \
    -U "$DB_USER" -d "$DB_NAME" > "$FILE"
  PREFIX=local
fi

# Integridad: el archivo debe poder leerse completo como respaldo de PostgreSQL.
docker run --rm -i postgres:17-alpine pg_restore --list < "$FILE" > /dev/null
( cd "$BACKUP_DIR" && shasum -a 256 "$(basename "$FILE")" > "$(basename "$FILE").sha256" )

echo "Respaldo: $FILE ($(du -h "$FILE" | cut -f1))"
echo "SHA-256:  $(cut -d' ' -f1 "$FILE.sha256")"

# Retención: conservar solo los BACKUP_KEEP más recientes de este origen.
ls -1t "$BACKUP_DIR"/${PREFIX}_*.dump 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | while read -r old; do
  rm -f "$old" "$old.sha256"
  echo "Retención: eliminado $old"
done
