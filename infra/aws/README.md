# AWS: IAM y S3 (preparación)

**Estado: no se ha creado ningún recurso en AWS ni se han usado credenciales reales.** Esta carpeta contiene solo diseño y plantillas.

## Restricciones acordadas

- Presupuesto adicional autorizado: **S/ 0**.
- Vía prioritaria: **AWS Academy Learner Lab**, si la asignatura da acceso.
- No activar facturación ni registrar tarjetas en cuentas personales.
- Solo datos ficticios en el bucket.

## Diseño

| Recurso | Propósito | Configuración |
|---|---|---|
| Bucket S3 privado | Archivos permitidos de prueba (RF-10) | Bloqueo de acceso público completo, cifrado SSE-S3, solo HTTPS |
| Identidad del backend | Acceso de la API Django a S3 | Solo la política `iam-policy-s3-minimo.json` |
| Usuarios del equipo | Consola, para evidencias | Sin cuenta raíz; MFA si la cuenta lo permite |

Solo la API Django accederá a S3. El chatbot y el frontend no reciben credenciales AWS.

## Archivos

| Archivo | Uso |
|---|---|
| `iam-policy-s3-minimo.json` | Política IAM de permisos mínimos: listar un bucket y leer, escribir y borrar sus objetos |
| `s3-bucket-policy-solo-https.json` | Política del bucket que rechaza peticiones sin HTTPS |

Reemplazar `NOMBRE_DEL_BUCKET` en ambos antes de usarlos.

## Límites de Learner Lab que afectan al diseño

Comprobar cada punto en el laboratorio real, porque dependen de cómo lo configure la institución:

- Las credenciales son temporales y cambian en cada sesión. Incluyen `AWS_SESSION_TOKEN`.
- IAM suele estar restringido: normalmente no se pueden crear usuarios ni roles y se trabaja con el rol predefinido `LabRole`. Si es así, la evidencia de "creación de cuentas IAM" (semana 8) habrá que acordarla con el docente.
- El laboratorio tiene un crédito limitado y se cierra por tiempo. Un bucket S3 con pocos archivos de prueba consume una fracción mínima de ese crédito.
- Las regiones disponibles suelen limitarse a `us-east-1` y `us-west-2`.

## Script: `preparar-s3.sh` (recomendado)

Hace todos los pasos de abajo y guarda las salidas en `infra/aws/evidencias/<fecha>/`. Esa carpeta no se sube a Git porque contiene el ID de la cuenta.

```bash
cd infra/aws
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=...   # del laboratorio
export AWS_REGION=us-east-1
export BUCKET=blackdog-chatbot-academico-<sufijo-unico>
./preparar-s3.sh
```

El script:

1. Muestra la identidad y pide confirmar que es la cuenta del laboratorio.
2. Crea el bucket, o lo reutiliza si ya existe.
3. Aplica el bloqueo de acceso público, el cifrado y la política solo HTTPS.
4. Intenta crear la política IAM mínima; si el laboratorio no lo permite, lo deja registrado.
5. Sube un archivo ficticio y comprueba que el acceso anónimo devuelve 403.

**Estado:** solo se comprobó la sintaxis (`bash -n`). No se ha ejecutado contra AWS.

Al final imprime el comando para borrar el bucket si hace falta.

## Pasos manuales equivalentes

Ningún comando de esta sección se ha ejecutado.

```bash
# 1. Credenciales temporales del laboratorio (AWS Details > AWS CLI), solo en la terminal local
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=... AWS_REGION=us-east-1

# 2. Bucket privado (el nombre debe ser único en todo AWS)
BUCKET=blackdog-chatbot-academico-<sufijo>
aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION"
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# 3. Política solo HTTPS (después de reemplazar NOMBRE_DEL_BUCKET)
aws s3api put-bucket-policy --bucket "$BUCKET" --policy file://s3-bucket-policy-solo-https.json

# 4. Comprobación
aws s3api get-public-access-block --bucket "$BUCKET"
aws s3 cp prueba-ficticia.txt "s3://$BUCKET/pruebas/prueba-ficticia.txt"
```

Si el laboratorio permite IAM: crear la política con `iam-policy-s3-minimo.json`, crear el usuario `blackdog-chatbot-backend` y adjuntarle solo esa política.

## Evidencias a capturar

1. Bucket creado, con "Block all public access" activado y cifrado por defecto.
2. Política del bucket aplicada.
3. Usuario o rol IAM con la política de permisos mínimos.
4. Subida y lectura de un archivo ficticio; acceso anónimo rechazado (403).
5. Panel de costos del laboratorio.

## Variables de entorno reservadas

`AWS_REGION`, `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (ver `.env.example`). Ningún código las lee todavía.

## Pendiente

1. Confirmar el acceso a Learner Lab.
2. Ejecutar los pasos anteriores y guardar las capturas.
3. Integrar `boto3` en el backend para RF-10 (entrega del 80 %).
