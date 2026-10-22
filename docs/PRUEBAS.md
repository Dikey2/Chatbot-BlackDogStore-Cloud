# Pruebas y evidencias

Resultados obtenidos el 13 de octubre de 2026 en el entorno local de Docker Compose (macOS, Docker Desktop 29.7.2). Todos se pueden repetir con los comandos indicados.

## Resumen

| Tipo | Herramienta | Resultado |
|---|---|---|
| Unitarias e integración de la API | pytest + pytest-django, contra PostgreSQL | 81 de 81 correctas (19 de octubre) |
| Unitarias del chatbot | pytest | 17 de 17 correctas |
| API de extremo a extremo | Colección Postman ejecutada con Newman | 28 peticiones, 50 aserciones, 0 fallos (19 de octubre) |
| Web de extremo a extremo | Playwright (Chromium) | 8 de 8 correctas (19 de octubre) |
| Estático del frontend | `eslint`, `tsc --noEmit`, `next build` | Sin errores |
| Carga inicial | Locust 2.46.7 | 100 peticiones, 0 fallos |
| Rate limit en vivo | `curl` | 429 con `Retry-After` |

## 1. Pytest

```bash
docker compose run --rm backend pytest
docker compose run --rm chatbot pytest
```

| Archivo (`backend/tests/`) | Qué comprueba |
|---|---|
| `test_auth.py` | Registro y validaciones, hash de contraseña, rol forzado a `cliente`, login, 401 idéntico para correo o contraseña erróneos, perfil, logout que invalida el token |
| `test_faqs.py` | Listado público paginado, filtro por categoría, FAQ inactivas ocultas, CRUD de administrador, 401 y 403 para los demás roles |
| `test_chat.py` | Creación de conversación, mensajes guardados, derivación a asesor, aislamiento entre usuarios, 503 si el chatbot falla, 500 sin detalles internos, historial por rol, `latest` (orden cronológico, 204, nunca conversaciones ajenas para ningún rol) |
| `test_rate_limit_and_errors.py` | Bloqueo 429 en login (10/min), anónimo (60/min) y chat (30/min por usuario), límite por IP, 404 JSON, JSON mal formado, 415 |
| `test_health.py` | 200, 503 por dependencia caída, 405, sin rate limit |

En `test_chat.py` la llamada HTTP al chatbot se sustituye por un doble de prueba. La integración real entre API y chatbot la cubren Newman y Playwright.

## 2. Postman y Newman

Colección: `docs/postman/BlackDogStore.postman_collection.json`. Requiere `seed_demo`.

En Postman: importar la colección, poner en la variable `admin_password` el valor de `DEMO_PASSWORD` de `.env` y ejecutar la colección completa en orden.

Por consola, sin instalar nada:

```bash
set -a; . ./.env; set +a
docker run --rm --network blackdog-chatbot_default \
  -v "$PWD/docs/postman:/etc/newman" postman/newman:alpine \
  run BlackDogStore.postman_collection.json \
  --env-var base_url=http://backend:8000 --env-var admin_password="$DEMO_PASSWORD"
```

Resultado del 13 de octubre: 26 peticiones, 47 aserciones, 0 fallos, respuesta media de 105 ms. Resultado del 19 de octubre, con las peticiones de historial: 28 peticiones, 50 aserciones, 0 fallos.

## 3. Playwright

```bash
cd frontend
npm install
npx playwright install chromium     # solo la primera vez
npm run test:e2e
```

Usa el stack levantado en `http://localhost:3000` y requiere `seed_demo`.

| Prueba | Resultado |
|---|---|
| El inicio muestra los tres servicios operativos | Correcta |
| Una ruta inexistente responde 404 con la página propia | Correcta |
| Páginas de mantenimiento y en desarrollo | Correcta |
| El chat sin sesión redirige al login | Correcta |
| Registro, chat, recarga con historial, reapertura del navegador, cookie `httpOnly`, cierre de sesión | Correcta |
| El registro rechaza un correo ya usado | Correcta |
| Al volver a iniciar sesión se recupera el historial y la conversación continúa | Correcta |
| Otro usuario no ve el historial del primero | Correcta |

Cada ejecución hace 7 peticiones de autenticación. Dos ejecuciones seguidas en el mismo minuto pueden recibir 429; esperar un minuto.

## 4. Prueba de carga inicial (Locust)

### Supuesto

**El rango "50–100" del docente se interpreta provisionalmente como peticiones HTTP totales, no como usuarios concurrentes.** Queda pendiente confirmarlo con el docente.

### Escenario

| Parámetro | Valor |
|---|---|
| Peticiones totales | 100 (la prueba se detiene sola al llegar) |
| Usuarios simulados | 5, todos desde el inicio |
| Espera entre peticiones por usuario | 0,1 a 0,5 s |
| Destino | `http://backend:8000`, red interna de Docker Compose |
| Servidor | `runserver` de Django (un proceso, desarrollo) |
| Flujo por usuario | Registro y login; después, al azar: FAQ (peso 3), chat (3), perfil (1), health (1) |
| Rate limits | Subidos a 100000/min con `docker-compose.loadtest.yml` |

Los rate limits se suben porque las 100 peticiones salen de una sola IP: con los límites normales se mediría el bloqueo y no el rendimiento. El bloqueo se prueba en la sección 5.

```bash
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d backend
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml --profile loadtest run --rm locust
docker compose up -d backend        # restaura los rate limits normales
```

Para cambiar el tamaño: `TOTAL_REQUESTS=50 LOAD_USERS=5` delante del segundo comando.

### Resultado

| Endpoint | Peticiones | Fallos | Mediana (ms) | Media (ms) | Máx (ms) | req/s |
|---|---|---|---|---|---|---|
| `POST /api/auth/register/` | 5 | 0 | 1400 | 1408 | 1431 | 0,48 |
| `POST /api/auth/login/` | 5 | 0 | 1815 | 1828 | 1847 | 0,48 |
| `POST /api/chat/messages/` | 31 | 0 | 45 | 95 | 566 | 2,98 |
| `GET /api/faqs/` | 37 | 0 | 31 | 59 | 369 | 3,55 |
| `GET /api/users/me/` | 15 | 0 | 32 | 68 | 351 | 1,44 |
| `GET /api/health/` | 7 | 0 | 33 | 32 | 48 | 0,67 |
| **Total** | **100** | **0 (0 %)** | **39** | **225** | **1847** | **9,60** |

Percentiles del total: p50 39 ms, p90 1400 ms, p95 1800 ms. Duración: unos 10 s.

Archivos de evidencia en `loadtest/resultados/`: `carga.html` (gráficos), `carga_stats.csv`, `carga_stats_history.csv`, `carga_failures.csv`.

### Lectura

- Sin errores con 100 peticiones.
- Registro y login tardan entre 1,4 y 1,8 s. Los 5 usuarios se registran a la vez y el hash PBKDF2 de la contraseña es costoso a propósito; el servidor de desarrollo los atiende en un solo proceso. Esos 10 valores explican el p90 y el p95.
- El resto de endpoints tiene mediana de 31 a 45 ms.
- No se midió CPU ni RAM. Pendiente para la entrega del 80 %.

## 5. Rate limit en vivo

Con los límites normales, 5 logins fallidos después de una ejecución de Playwright (que ya había hecho 5 peticiones de autenticación en el mismo minuto):

```
401 401 401 401 401 429 429 429 429 429 429
HTTP/1.1 429 Too Many Requests
Retry-After: 43
{"error":{"code":"throttled","message":"Solicitud fue regulada (throttled). Se espera que esté disponible en 43 segundos."}}
```

El bloqueo llega en la petición 11 del minuto, como fija `THROTTLE_AUTH=10/min`.

## 6. Corrección: el historial del chat desaparecía al recargar (19 de octubre de 2026)

### Causa

- PostgreSQL sí guardaba conversaciones y mensajes. Comprobado con SQL antes de corregir: la conversación de la prueba manual tenía 4 mensajes.
- El componente `ChatBox` guardaba los mensajes solo en memoria del navegador (`useState([])`), y la página `/chat` no pedía el historial. Al recargar, la lista empezaba vacía y el siguiente mensaje abría una conversación nueva.
- En el backend faltaba un endpoint adecuado: el listado de conversaciones devuelve todas a asesor y administrador, así que no servía para cargar "mi chat".

### Corrección

- Backend: `GET /api/chat/conversations/latest/` devuelve la última conversación del usuario de la sesión, con sus mensajes en orden cronológico; 204 si no tiene.
- Frontend: `/chat` carga ese historial en el servidor antes de mostrar el chat, con el estado "Cargando historial…". Los mensajes nuevos continúan la misma conversación.
- Errores de conexión: si la API no responde, `/chat` muestra un aviso con "Reintentar" y no envía al login. Si falla el envío de un mensaje, el texto escrito se conserva.
- Los 404 ya no muestran nombres internos de modelos.

### Comprobaciones

| Comprobación | Herramienta | Resultado |
|---|---|---|
| Mensajes guardados en PostgreSQL | `psql` | Usuario E2E: 1 conversación, 6 mensajes en orden (`cliente`, `bot`, …) |
| Reaparecen al recargar la página | Playwright | 4 mensajes, mismo texto y orden |
| Cerrar y volver a abrir el navegador | Playwright: nuevo Chromium con las cookies guardadas | 4 mensajes, mismo orden |
| Iniciar sesión otra vez y recuperar el historial | Playwright | 4 mensajes; el siguiente queda en la misma conversación (6 tras recargar) |
| Otro usuario no ve el historial | Playwright | Chat vacío, ningún texto del primer usuario |
| Otro usuario no puede leer ni escribir en la conversación ajena | `curl` a la API | 404 en detalle y en envío; la conversación ajena sigue con 4 mensajes |
| `latest` nunca devuelve conversaciones ajenas | pytest (cliente, asesor, admin) | 204 |
| API caída con sesión activa | `curl` con la cookie de sesión | "No se pudo conectar con el servidor. Tu sesión sigue activa." |
| API restablecida | `curl` | Vuelve a mostrarse el chat |

## 6. Pendiente

- Confirmar con el docente la interpretación de "50–100".
- Medir CPU y RAM durante la carga.
- Repetir la carga con un servidor de producción (gunicorn) antes de la entrega del 80 %.
- Pruebas E2E del panel administrativo, cuando exista.
- Pruebas de CORS y de expiración de tokens (entrega del 80 %).
