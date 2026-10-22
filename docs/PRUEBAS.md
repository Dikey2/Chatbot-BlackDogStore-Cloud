# Pruebas y evidencias

Resultados obtenidos el 13 de octubre de 2026 en el entorno local de Docker Compose (macOS, Docker Desktop 29.7.2). Todos se pueden repetir con los comandos indicados.

## Resumen

| Tipo | Herramienta | Resultado |
|---|---|---|
| Unitarias e integración de la API | pytest + pytest-django, contra PostgreSQL | 111 de 111 correctas (22 de octubre) |
| Unitarias del chatbot | pytest | 17 de 17 correctas |
| API de extremo a extremo | Colección Postman ejecutada con Newman | 37 peticiones, 67 aserciones, 0 fallos (21 de octubre) |
| Web de extremo a extremo | Playwright (Chromium) | 9 de 9 correctas (21 de octubre) |
| Estático del frontend | `eslint`, `tsc --noEmit`, `next build` | Sin errores |
| Carga | Locust 2.46.7 | 100 peticiones totales; 50 y 100 usuarios concurrentes: 0 fallos (22 de octubre) |
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
set -a; . ../.env; set +a        # DEMO_PASSWORD, para la prueba del administrador
npm run test:e2e
```

Usa el stack levantado en `http://localhost:3000` y requiere `seed_demo`. Sin `DEMO_PASSWORD` la prueba del administrador se omite.

| Prueba | Resultado |
|---|---|
| El inicio muestra los tres servicios operativos | Correcta |
| Una ruta inexistente responde 404 con la página propia | Correcta |
| Páginas de mantenimiento y en desarrollo | Correcta |
| El chat y la administración sin sesión redirigen al login | Correcta |
| Registro, chat, recarga con historial, reapertura del navegador, cookie `httpOnly`, cierre de sesión | Correcta |
| El registro rechaza un correo ya usado | Correcta |
| Al volver a iniciar sesión se recupera el historial y la conversación continúa | Correcta |
| Otro usuario no ve el historial; un cliente no entra a FAQ ni a la bandeja; el asesor responde y cierra la consulta derivada; el cliente ve la respuesta y el cierre, y su siguiente mensaje abre otra conversación; el asesor no administra FAQ | Correcta |
| Administrador: validación, crear, editar, desactivar, activar y eliminar una FAQ; el chatbot usa cada cambio; 404 al editar una inexistente | Correcta |

Cada ejecución hace 9 peticiones de autenticación. Dos ejecuciones seguidas en el mismo minuto pueden recibir 429; esperar un minuto.

## 4. Pruebas de carga (Locust)

### Interpretación de "50–100"

El docente no define si "50–100" son peticiones o usuarios concurrentes. Se midieron las dos lecturas:

- **Escenario A:** 100 peticiones HTTP totales, repartidas entre 5 usuarios.
- **Escenarios B y C:** 50 y 100 usuarios concurrentes durante 60 s.

### Configuración común

| Parámetro | Valor |
|---|---|
| Destino | `http://backend:8000`, red interna de Docker Compose |
| Servidor | gunicorn, 4 procesos (antes: `runserver` de Django) |
| Flujo por usuario | Registro y login; después, al azar: FAQ (peso 3), chat (3), perfil (1), health (1) |
| Espera entre peticiones por usuario | 0,1 a 0,5 s |
| Rate limits | Subidos a 100000/min con `docker-compose.loadtest.yml` |
| Equipo | Docker Desktop en macOS, 8 CPU virtuales y 3,8 GiB para la VM de Docker |

Los rate limits se suben porque todas las peticiones salen de una sola IP: con los límites normales se mediría el bloqueo y no el rendimiento. El bloqueo se prueba en la sección 5.

```bash
docker compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d backend
C="docker compose -f docker-compose.yml -f docker-compose.loadtest.yml --profile loadtest run --rm locust"

# A: 100 peticiones totales
$C
# B y C: usuarios concurrentes durante 60 s
TOTAL_REQUESTS=1000000 $C -f locustfile.py --headless --users 50 --spawn-rate 50 --run-time 60s \
  --host http://backend:8000 --csv resultados/concurrentes-50u --html resultados/concurrentes-50u.html --only-summary
#   (lo mismo con 100)

docker compose up -d backend    # restaura los rate limits normales
```

Los contadores del rate limit se guardan en PostgreSQL y sobreviven al reinicio. Esperar un minuto después de la carga antes de lanzar Newman o Playwright; si no, algunas peticiones pueden recibir 429.

### Resultados finales (gunicorn, 22 de octubre de 2026)

| Escenario | Peticiones | Fallos | req/s | Mediana | p95 | p99 | Media |
|---|---|---|---|---|---|---|---|
| A: 100 peticiones totales, 5 usuarios | 100 | 0 (0 %) | 15,9 | 22 ms | 360 ms | 540 ms | 54 ms |
| B: 50 usuarios concurrentes, 60 s | 6048 | 0 (0 %) | 101,1 | 100 ms | 560 ms | 2700 ms | 197 ms |
| C: 100 usuarios concurrentes, 60 s | 3480 | 0 (0 %) | 58,2 | 850 ms | 6200 ms | 8900 ms | 1429 ms |

Uso de recursos a mitad de prueba (`docker stats`):

| Escenario | Backend | PostgreSQL | Chatbot |
|---|---|---|---|
| B: 50 usuarios | CPU 190 %, RAM 208 MiB | CPU 180 %, RAM 47 MiB | CPU 16 %, RAM 76 MiB |
| C: 100 usuarios | CPU 196 %, RAM 210 MiB | CPU 186 %, RAM 66 MiB | CPU 13 %, RAM 76 MiB |

Evidencias en `loadtest/resultados/`: `carga.html`, `concurrentes-50u.html` y `concurrentes-100u.html` (gráficos), más sus CSV. Las cifras de la tabla son el resumen final de Locust en consola; los CSV pueden tener unas pocas peticiones menos porque se escriben un instante antes de terminar.

### Antes: servidor de desarrollo `runserver`

| Escenario | Peticiones | Fallos | req/s | Mediana | p95 |
|---|---|---|---|---|---|
| A: 100 peticiones totales | 100 | 0 (0 %) | 9,6 | 39 ms | 1800 ms |
| B: 50 usuarios concurrentes | 3521 | **48 (1,4 %)** | 59,3 | 28 ms | 720 ms |
| C: 100 usuarios concurrentes | 5309 | **122 (2,3 %)** | 88,8 | 37 ms | 610 ms |

Evidencias en `loadtest/resultados/antes-runserver/`.

### Cuello de botella encontrado y corrección

- **Síntoma:** con 50 y 100 usuarios concurrentes fallaban el 48 % y el 61 % de los registros y logins con `ConnectionResetError(104, 'Connection reset by peer')`. Los logins con 401 eran de usuarios cuyo registro había fallado. El resto de endpoints no tenía fallos.
- **Causa:** `runserver` acepta solo 5 conexiones en cola (`socketserver.TCPServer.request_queue_size = 5`, comprobado en el contenedor). Una ráfaga de registros, lentos a propósito por el hash PBKDF2, llena la cola y el sistema reinicia las conexiones nuevas.
- **Corrección:** el backend corre con gunicorn (4 procesos, cola de 2048). Como cada proceso tendría su propia memoria, los contadores del rate limit pasan a una caché compartida en PostgreSQL (`DatabaseCache`).
- **Resultado:** 0 fallos en los tres escenarios. En vivo, 11 logins seguidos dan 10 × 401 y 1 × 429 aunque los atiendan 4 procesos distintos.
- **Por qué el C con `runserver` muestra más req/s:** los usuarios con registro fallido dejaban de enviar peticiones, así que había menos usuarios activos. No era mejor rendimiento.

### Lectura

- **50 usuarios:** sin fallos, unas 100 req/s y mediana de 100 ms.
- **100 usuarios:** sin fallos, pero la latencia sube (mediana 850 ms, p95 6,2 s) y el throughput baja a 58 req/s. El backend y PostgreSQL están cerca de 2 CPU cada uno. Se atribuye a:
  1. El hash de 100 contraseñas a la vez.
  2. La consulta y escritura de los contadores de rate limit en PostgreSQL en cada petición.
- **Pendiente para el 80 %:** medir por separado esas dos causas, probar más procesos de gunicorn y valorar una caché dedicada si el coste en PostgreSQL se confirma.

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

## 7. Expiración de tokens (21 de octubre de 2026)

Pytest: `backend/tests/test_token_expiration.py`, 13 casos. Token vigente a las 7,9 h; rechazado a las 8,1 h con `token_expired` y borrado; bloqueado en cada ruta protegida; login devuelve `expires_at`; reutiliza el token vigente; reemplaza el caducado; duración configurable.

Comprobación en vivo (usuario ficticio `cliente@example.com`; el token se envejeció 9 h con `UPDATE` en PostgreSQL):

| Paso | Resultado |
|---|---|
| `/chat` con token vigente | Chat visible |
| `/chat` con token caducado | Redirige a `/login?motivo=expirada` |
| Token caducado en PostgreSQL tras usarlo | Borrado (0 filas) |
| `/login?motivo=expirada` | "Tu sesión expiró. Inicia sesión de nuevo." |
| `/login` sin parámetro | Sin aviso |
| Nuevo login | Token distinto; `/api/users/me/` responde 200 |

## 8. Bandeja del asesor (21 de octubre de 2026)

| Herramienta | Qué comprueba | Resultado |
|---|---|---|
| pytest `test_advisor.py` (17 casos) | Filtro por estado y `user_name`; respuesta guardada como `asesor`; el cliente la ve en `latest`; cliente sin permiso para responder o cerrar (403); validación; 404; cierre; 409 en conversación cerrada; el cliente continúa en una nueva | 17 de 17 |
| Newman, carpeta "4b. Bandeja del asesor" (9 peticiones) | Lo mismo contra el stack real | 0 fallos |
| Playwright, prueba 8 | Cliente y asesor en dos navegadores: derivación, respuesta, cierre y nueva conversación | Correcta |

## 9. Pendiente

- Reducir la latencia con 100 usuarios concurrentes (sección 4).
- Pruebas de CORS (entrega del 80 %).
