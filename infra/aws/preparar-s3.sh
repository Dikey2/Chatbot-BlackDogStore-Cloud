#!/usr/bin/env bash
# Prepara el bucket S3 académico y genera evidencias (criterio "entorno cloud preparado").
#
# NO crea nada si no se ejecuta a mano dentro de una sesión autorizada de
# AWS Academy Learner Lab. Presupuesto adicional autorizado: S/ 0. Solo datos ficticios.
#
# Uso, desde la carpeta infra/aws, con las credenciales temporales del laboratorio
# (AWS Details > AWS CLI) exportadas en la terminal:
#
#   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...
#   export AWS_REGION=us-east-1
#   export BUCKET=blackdog-chatbot-academico-<sufijo-unico>
#   ./preparar-s3.sh
#
# Las salidas quedan en infra/aws/evidencias/<fecha>/ para adjuntarlas al informe.
set -euo pipefail

: "${AWS_REGION:?Definir AWS_REGION (por ejemplo us-east-1)}"
: "${BUCKET:?Definir BUCKET con un nombre único en minúsculas}"
command -v aws >/dev/null || { echo "Falta AWS CLI v2: https://docs.aws.amazon.com/cli/" >&2; exit 1; }

cd "$(dirname "$0")"
OUT="evidencias/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
log() { echo "==> $*"; }

log "1. Identidad (debe ser la cuenta del laboratorio, nunca una cuenta personal con tarjeta)"
aws sts get-caller-identity | tee "$OUT/01-identidad.json"
read -r -p "¿Es la cuenta de AWS Academy Learner Lab? Escribe 'si' para continuar: " ok
[ "$ok" = "si" ] || { echo "Cancelado."; exit 1; }

log "2. Bucket privado $BUCKET en $AWS_REGION"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "El bucket ya existe en esta cuenta; se reutiliza."
elif [ "$AWS_REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "$BUCKET"
else
  aws s3api create-bucket --bucket "$BUCKET" \
    --create-bucket-configuration "LocationConstraint=$AWS_REGION"
fi

log "3. Bloqueo de acceso público"
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api get-public-access-block --bucket "$BUCKET" | tee "$OUT/03-bloqueo-publico.json"

log "4. Cifrado por defecto (SSE-S3)"
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api get-bucket-encryption --bucket "$BUCKET" | tee "$OUT/04-cifrado.json"

log "5. Política del bucket: solo HTTPS"
sed "s/NOMBRE_DEL_BUCKET/$BUCKET/g" s3-bucket-policy-solo-https.json > "$OUT/05-politica-bucket.json"
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "file://$OUT/05-politica-bucket.json"
aws s3api get-bucket-policy --bucket "$BUCKET" --query Policy --output text >> "$OUT/05-politica-bucket.json.aplicada"

log "6. Política IAM de permisos mínimos (solo se genera; crearla depende de lo que permita el laboratorio)"
sed "s/NOMBRE_DEL_BUCKET/$BUCKET/g" iam-policy-s3-minimo.json > "$OUT/06-politica-iam-minimo.json"
if aws iam create-policy --policy-name blackdog-chatbot-s3-minimo \
     --policy-document "file://$OUT/06-politica-iam-minimo.json" > "$OUT/06-iam-create-policy.json" 2> "$OUT/06-iam-error.txt"; then
  echo "Política IAM creada."
else
  echo "El laboratorio no permite crear políticas IAM (ver $OUT/06-iam-error.txt). Usar el rol LabRole y documentarlo."
fi

log "7. Archivo ficticio de prueba"
echo "Archivo de prueba FICTICIO del Chatbot Black Dog Store ($(date -u +%FT%TZ))" > "$OUT/prueba-ficticia.txt"
aws s3 cp "$OUT/prueba-ficticia.txt" "s3://$BUCKET/pruebas/prueba-ficticia.txt"
aws s3 ls "s3://$BUCKET/pruebas/" | tee "$OUT/07-listado.txt"

log "8. Acceso anónimo rechazado (se espera 403)"
code=$(curl -s -o /dev/null -w '%{http_code}' "https://$BUCKET.s3.$AWS_REGION.amazonaws.com/pruebas/prueba-ficticia.txt")
echo "HTTP $code" | tee "$OUT/08-acceso-anonimo.txt"
[ "$code" = "403" ] || echo "ATENCIÓN: se esperaba 403." >&2

log "Listo. Evidencias en infra/aws/$OUT"
echo "Capturas de consola pendientes: bucket con 'Block all public access', cifrado, política, panel de costos."
echo "Para borrar todo al terminar: aws s3 rm s3://$BUCKET --recursive && aws s3api delete-bucket --bucket $BUCKET"
