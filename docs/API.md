# API REST

Base local: `http://localhost:8000`. Formato JSON (`Content-Type: application/json`).
Colección Postman con ejemplos y pruebas: [`postman/BlackDogStore.postman_collection.json`](postman/BlackDogStore.postman_collection.json).

## Autenticación

`POST /api/auth/login/` devuelve un token. Enviarlo en cada petición protegida:

```
Authorization: Token <token>
```

El token caduca a las `TOKEN_TTL_HOURS` horas de crearse (8 por defecto). El login devuelve `expires_at`. Un token caducado responde 401 con `code: token_expired` y se borra. Un nuevo login reutiliza el token si sigue vigente y crea otro si caducó. El cierre de sesión borra el token en el servidor.

El frontend guarda el token en una cookie `httpOnly` que caduca a la vez. Si la API indica `token_expired`, envía a `/login?motivo=expirada`, que muestra "Tu sesión expiró".

## Roles

| Rol | Cómo se obtiene | Permisos actuales |
|---|---|---|
| `cliente` | Registro público | Chat, historial propio, lectura de FAQ activas |
| `asesor` | `seed_demo` o administrador de Django | Lo anterior; bandeja de todas las conversaciones, responder y cerrar |
| `admin` | `seed_demo` o `createsuperuser` | Lo anterior, CRUD de FAQ, lectura de FAQ inactivas y auditoría |

El registro público siempre crea `cliente`; un campo `role` enviado por el cliente se ignora.

## Endpoints

| Método | Ruta | Acceso | Éxito | Errores |
|---|---|---|---|---|
| GET | `/api/health/` | Público | 200 | 503 si falla la base de datos o el chatbot |
| POST | `/api/auth/register/` | Público | 201 | 400, 429 |
| POST | `/api/auth/login/` | Público | 200 | 400, 401, 429 |
| POST | `/api/auth/logout/` | Sesión | 204 | 401 |
| GET | `/api/users/me/` | Sesión | 200 | 401 |
| GET | `/api/faqs/` | Público | 200 paginado; `?search=`, `?category=`, `?ordering=` | 404 si la página no existe |
| POST | `/api/faqs/` | `admin` | 201 | 400, 401, 403 |
| GET | `/api/faqs/{id}/` | Público | 200 | 404 |
| PUT, PATCH | `/api/faqs/{id}/` | `admin` | 200 | 400, 401, 403, 404 |
| DELETE | `/api/faqs/{id}/` | `admin` | 204 | 401, 403, 404 |
| POST | `/api/chat/messages/` | Sesión | 201 | 400, 401, 404, 429, 503 |
| GET | `/api/chat/conversations/` | Sesión (el cliente solo ve las suyas) | 200 paginado; `?status=`, `?ordering=` | 400 estado desconocido, 401 |
| GET | `/api/chat/conversations/latest/` | Sesión | 200 con mensajes; 204 si no hay | 401 |
| GET | `/api/chat/conversations/{id}/` | Sesión | 200 con mensajes | 401, 404 |
| POST | `/api/chat/conversations/{id}/reply/` | `asesor`, `admin` | 201 | 400, 401, 403, 404, 409 |
| POST | `/api/chat/conversations/{id}/close/` | `asesor`, `admin` | 200 | 401, 403, 404, 409 |
| GET | `/api/audit/` | `admin` | 200 paginado; `?action=`, `?result=` | 400 filtro desconocido, 401, 403 |
| GET | `/api/audit/{id}/` | `admin` | 200 | 401, 403, 404 |

Cualquier otra ruta bajo `/api/` responde 404. Un método no permitido responde 405.

### Paginación, filtros y orden

Todos los listados devuelven `{"count", "next", "previous", "results"}`.

| Parámetro | Valores | Notas |
|---|---|---|
| `page` | 1, 2, … | 404 si la página no existe |
| `page_size` | 1 a 100 (por defecto 20) | Un valor mayor se limita a 100 |
| `ordering` | FAQ: `category`, `question`, `updated_at`, `id`; conversaciones: `created_at`, `id`; con `-` para descendente | Por defecto: FAQ por categoría; conversaciones y auditoría, más recientes primero |
| `search` | Texto | Solo FAQ: busca en pregunta, respuesta y palabras clave |
| `status` | `abierta`, `derivada`, `cerrada` | Solo conversaciones |
| `action`, `result` | Valores de la auditoría (`login`, `login_fallido`, `faq_crear`…; `exito`, `fallo`) | Solo `/api/audit/` |

La auditoría no admite `POST`, `PUT`, `PATCH` ni `DELETE` (405): es un registro inmutable.

### Cuerpos de petición

```jsonc
// POST /api/auth/register/   -> 201 {"id", "name", "email", "role"}
{"name": "Ana Ficticia", "email": "ana@example.com", "password": "Clave-ficticia-123"}

// POST /api/auth/login/      -> 200 {"token", "expires_at", "user": {...}}
{"email": "ana@example.com", "password": "Clave-ficticia-123"}

// POST /api/faqs/            -> 201 FAQ completa
{"category": "horarios", "question": "¿...?", "answer": "...", "keywords": "horario, atención", "is_active": true}

// POST /api/chat/messages/   -> 201
{"message": "¿Cuál es el horario?", "conversation_id": 1}   // conversation_id es opcional
```

Respuesta de `POST /api/chat/messages/`:

```json
{
  "conversation": {"id": 1, "user": 5, "status": "abierta", "created_at": "..."},
  "user_message": {"id": 1, "sender": "cliente", "content": "¿Cuál es el horario?", "created_at": "..."},
  "bot_message": {"id": 2, "sender": "bot", "content": "DATO FICTICIO: ...", "created_at": "..."},
  "category": "horarios",
  "escalated": false
}
```

Reglas:

- Contraseña: mínimo 8 caracteres, no solo números, no común, no parecida al nombre o correo.
- `message`: de 1 a 500 caracteres.
- Sin `conversation_id` se crea una conversación nueva. Con el `id` de una conversación ajena responde 404.
- Si ninguna FAQ coincide, `escalated` es `true` y la conversación pasa a `derivada` (RF-09).
- `GET /api/chat/conversations/latest/` devuelve la última conversación **del usuario de la sesión** con sus mensajes en orden cronológico. Filtra por usuario también para asesor y administrador. El chat web la usa para recuperar el historial al entrar o recargar.
- El listado y el detalle de conversaciones muestran todas al asesor y al administrador; al cliente, solo las suyas. Una conversación ajena responde 404.
- `GET /api/chat/conversations/?status=derivada` filtra por estado (`abierta`, `derivada`, `cerrada`). Cada conversación incluye `user_name`.
- `reply` guarda un mensaje con `sender: "asesor"` (1 a 2000 caracteres). `close` pasa la conversación a `cerrada`. En una conversación cerrada, `reply`, `close` y `POST /api/chat/messages/` con su `conversation_id` responden 409; el cliente continúa sin `conversation_id` y se crea otra.
- `GET /api/faqs/?category=horarios` filtra por categoría. `?page=2` cambia de página (20 por página).

## Formato de errores

Todos los errores usan la misma forma. `fields` solo aparece en errores de validación.

```json
{"error": {"code": "validation_error", "message": "Datos inválidos.", "fields": {"email": ["Ya existe una cuenta con este correo."]}}}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `validation_error`, `parse_error` | Datos inválidos o JSON mal formado |
| 401 | `not_authenticated`, `authentication_failed`, `token_expired` | Falta el token, token inválido o caducado, o credenciales incorrectas |
| 403 | `permission_denied` | El rol no tiene permiso (queda registrado como `acceso_denegado`) |
| 403 | `origin_not_allowed` | El encabezado `Origin` no está en `CORS_ALLOWED_ORIGINS` |
| 404 | `not_found` | Recurso o ruta inexistente |
| 405 | `method_not_allowed` | Método no permitido |
| 409 | `conversation_closed` | La conversación está cerrada |
| 415 | `unsupported_media_type` | El cuerpo no es JSON |
| 429 | `throttled` | Límite de peticiones superado; incluye la cabecera `Retry-After` |
| 500 | `server_error` | Error no previsto; el detalle queda solo en los logs |
| 503 | `chatbot_unavailable` | El servicio de chatbot no responde |

## CORS

La API solo acepta peticiones de navegador con un encabezado `Origin` incluido en `CORS_ALLOWED_ORIGINS`, que es una lista explícita: en producción no se admiten comodines y la aplicación no arranca si se configura `*`.

| Caso | Respuesta |
|---|---|
| Sin `Origin` (servidor de Next.js, curl, Locust) | Normal |
| `Origin` permitido | Normal, con `Access-Control-Allow-Origin: <origen>` y `Vary: Origin` |
| Preflight `OPTIONS` de un origen permitido | 204 con `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS`, `Access-Control-Allow-Headers: Authorization, Content-Type` y `Access-Control-Max-Age: 600` |
| `Origin` no permitido (incluido `null`) | 403 `origin_not_allowed`, sin cabeceras CORS |
| Mismo origen que la API (panel `/admin/` de Django) | Normal |

No se envía `Access-Control-Allow-Credentials`: la API se autentica con el encabezado `Authorization`, no con cookies.

CORS es una política que aplican los navegadores. Decide si una página de otro origen puede leer la respuesta, pero no protege frente a clientes que no son navegadores. La autenticación por token y los permisos por rol se comprueban siempre, con o sin CORS.

## Rate limits

Valores por defecto, configurables en `.env`.

| Ámbito | Límite | Clave | Variable |
|---|---|---|---|
| Registro y login (compartido) | 10 por minuto | IP | `THROTTLE_AUTH` |
| Envío de mensajes de chat | 30 por minuto | Usuario | `THROTTLE_CHAT` |
| Resto, sin sesión | 60 por minuto | IP | `THROTTLE_ANON` |
| Resto, con sesión | 120 por minuto | Usuario | `THROTTLE_USER` |

`/api/health/` no tiene límite.

Limitaciones conocidas:

- Los contadores se guardan en una caché compartida en PostgreSQL (`django_cache`), así que valen para todos los procesos de gunicorn. Sobreviven al reinicio del backend.
- La IP se toma de `X-Forwarded-For` cuando existe, porque el frontend reenvía la del visitante. Como el puerto 8000 solo se publica en `127.0.0.1`, esto es aceptable en local. Antes de publicar el backend hay que configurar `NUM_PROXIES` de DRF.

## Servicio de chatbot (interno)

Solo lo llama la API Django. Puerto local 8001.

| Método | Ruta | Respuestas |
|---|---|---|
| GET | `/health/` | 200 |
| POST | `/api/reply/` | 200; 400 si el cuerpo es inválido |

```jsonc
// Petición: la API envía el mensaje y las FAQ activas
{"message": "¿Cuál es el horario?", "faqs": [{"category": "horarios", "answer": "...", "keywords": ["horario", "atención"]}]}
// Respuesta
{"answer": "...", "category": "horarios", "matched": true, "escalate": false}
```

El chatbot compara palabras completas, sin distinguir mayúsculas ni tildes, y elige la FAQ con más coincidencias.

Si ninguna FAQ coincide y el mensaje es solo un saludo, agradecimiento, despedida o pedido de ayuda ("Buenos días", "gracias", "¿qué puedes hacer?"), responde sin derivar; el saludo y la ayuda listan las categorías de las FAQ activas. Si el mensaje trae algo más ("Hola, ¿cuánto cuesta la laptop X?"), se deriva a un asesor. Las FAQ siempre tienen prioridad.
