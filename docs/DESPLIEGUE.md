# Despliegue en la nube (Render Free y Neon)

Estado al 29 de octubre de 2026. Este documento es un **plan**: no se desplegó ningún cambio nuevo en Render ni en Neon. Cada paso que modifica un servicio público requiere la autorización expresa del equipo.

## 1. Situación actual

| Componente | Dónde corre | Estado |
|---|---|---|
| Backend Django + chatbot | Un Web Service de Render Free (`Dockerfile.render`) | Publicado por el equipo |
| PostgreSQL | Neon (plan Free), conexión con `POSTGRES_SSLMODE=require` | Publicado por el equipo |
| Frontend Next.js | — | **No publicado** |

`infra/render/start.py` aplica las migraciones y arranca dos procesos en la misma instancia:

- el chatbot con gunicorn en `127.0.0.1:8001`, que no es accesible desde Internet;
- la API en el puerto `PORT` de Render.

Si uno de los dos procesos termina, el script se detiene y Render reinicia la instancia.

### Revisión de la configuración existente

| Punto | Resultado | Acción |
|---|---|---|
| Secretos | Se leen de variables de entorno; ninguno en el repositorio | — |
| SSL hacia Neon | `POSTGRES_SSLMODE=require` | Recomendado `verify-full` cuando se pruebe |
| Chatbot | Solo escucha en `127.0.0.1`: no queda expuesto | — |
| Usuario del contenedor | `app`, sin privilegios | — |
| Dependencias | `requirements.render.lock` con hashes | El chatbot ahora declara `gunicorn`, que ya estaba en el lock |
| Conexiones a Neon | Antes `CONN_MAX_AGE=0`: una conexión SSL nueva por petición | Ahora se reutilizan 60 s (`POSTGRES_CONN_MAX_AGE`) |
| Rate limit | Sin `NUM_PROXIES`, el cliente podía alterar `X-Forwarded-For` | Definir `NUM_PROXIES` (ver la sección 3) |
| CORS | No configurado | `CORS_ALLOWED_ORIGINS` con la URL del frontend |

## 2. Plan para publicar el frontend (Render Free)

Se usa otro Web Service gratuito de Render, que ya conocen y permite Docker. No se agrega un proveedor nuevo.

1. En Render, crear un **Web Service** desde el repositorio con:
   - **Root Directory:** `frontend`
   - **Runtime:** Docker (usa `frontend/Dockerfile`, salida `standalone` de Next.js)
   - **Plan:** Free
2. Variables de entorno del frontend:

   | Variable | Valor |
   |---|---|
   | `API_INTERNAL_URL` | `https://<backend>.onrender.com` |
   | `COOKIE_SECURE` | `true` (las cookies de sesión e idioma solo viajan por HTTPS) |

3. Variables nuevas del backend (servicio ya existente):

   | Variable | Valor |
   |---|---|
   | `CORS_ALLOWED_ORIGINS` | `https://<frontend>.onrender.com` (sin barra final y sin `*`) |
   | `NUM_PROXIES` | `2` (ver la sección 3) |
   | `POSTGRES_CONN_MAX_AGE` | `60` |
   | `DJANGO_ALLOWED_HOSTS` | `<backend>.onrender.com` |
   | `DJANGO_HTTPS` | `true` (cookies seguras, HSTS de 1 h y redirección a HTTPS; `/api/health/` queda exento) |

4. Desplegar primero el backend, comprobar `https://<backend>.onrender.com/api/health/` (esperado: 200 y `"status": "ok"`) y después crear el frontend.

### Verificación después del despliegue

| Prueba | Esperado |
|---|---|
| `https://<frontend>.onrender.com/` | Los tres servicios "Operativo" |
| Registro, login, chat y cierre de sesión | Igual que en local |
| Cookie `session` en el navegador | `HttpOnly`, `Secure`, `SameSite=Lax` |
| `curl -H "Origin: https://evil.example.com" https://<backend>.onrender.com/api/faqs/` | 403 `origin_not_allowed` |
| `http://` en lugar de `https://` | Render redirige a HTTPS |

## 3. Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| La instancia gratuita se duerme tras ~15 min sin tráfico | La primera petición tarda decenas de segundos | El frontend muestra la pantalla "El servidor tardó demasiado" con "Reintentar"; para la demostración, abrir el sitio unos minutos antes |
| `NUM_PROXIES` incorrecto | Con un valor bajo, todos los usuarios compartirían el límite del servidor del frontend; con uno alto, el cliente podría falsear su IP | Valor previsto `2`: proxy de Render del frontend y del backend. Confirmar con una petición real revisando el campo "Origen" en `/admin/auditoria` |
| 512 MB de RAM en el plan Free | Dos procesos (API y chatbot) comparten memoria | `GUNICORN_WORKERS=1`, el chatbot con 1 proceso, `--max-requests` recicla procesos |
| Pruebas de carga contra Render | Pueden agotar las horas gratuitas o bloquear la cuenta por abuso | Solo con autorización y un volumen bajo (sección 4) |
| Neon Free: ventana de restauración corta | Un error de datos detectado tarde no se puede revertir desde Neon | Respaldos propios con `infra/backup/respaldar.sh --neon` (ver `BACKUPS.md`) |

## 4. Prueba de carga en el servidor (pendiente de autorización)

La rúbrica pide pruebas en el servidor. Antes de ejecutarlas se necesita aprobación con estos datos:

| Dato | Propuesta |
|---|---|
| Destino | `https://<backend>.onrender.com` (solo la API; no Neon directamente) |
| Perfil | `Lectura` (no escribe en Neon), modalidad A |
| Cantidad | 1000 solicitudes totales; si todo va bien, 2000 |
| Usuarios | 10 concurrentes |
| Tasa estimada | 10 a 20 solicitudes por segundo |
| Duración | Unos 2 minutos por prueba |
| Rate limit | Con los límites normales, la mayoría de peticiones recibirían 429, porque salen de una sola IP. Hay que subir temporalmente `THROTTLE_*` en Render y restaurarlos al terminar |
| Riesgo | Bajo para Neon (lecturas); medio para la instancia Free (puede saturarse). Se detiene ante más de 5 % de fallos |

Comando, solo después de la autorización:

```bash
docker run --rm -v "$PWD/loadtest:/mnt/locust" -w /mnt/locust -e TOTAL_REQUESTS=1000 \
  -e DEMO_PASSWORD="$DEMO_PASSWORD" locustio/locust:2.46.7 \
  -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 10m \
  --host https://<backend>.onrender.com \
  --csv resultados/render-A-1000req-lectura --html resultados/render-A-1000req-lectura.html \
  --only-summary Lectura
```

Requisito previo: las cuentas `cliente@example.com` y `asesor@example.com` deben existir en Neon, creadas con `seed_demo` y datos ficticios.

## 5. VPC (extra opcional): evaluación

No se implementó una VPC:

- Render Free no ofrece red privada hacia Neon.
- La conexión privada de Neon (Private Networking) requiere planes de pago.
- La VM de Google Cloud no forma parte de la arquitectura actual: la regla del curso es no agregar servicios que no sean necesarios.

Con los recursos actuales, los datos se protegen de tres formas:

- SSL obligatorio entre Render y Neon.
- El chatbot escucha solo en `127.0.0.1` dentro de la instancia.
- PostgreSQL local no publica su puerto (Docker Compose).

Una VPC tendría sentido al pasar a un plan de pago o a un único proveedor.
