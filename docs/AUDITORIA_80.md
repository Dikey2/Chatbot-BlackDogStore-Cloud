# Auditoría inicial de la entrega del 80 %

Fecha: 29 de octubre de 2026. Rama de trabajo: `feat/entrega-80`, creada desde `main` (`0e6a3f6`).

## Estado del repositorio al iniciar

| Elemento | Estado |
|---|---|
| Rama `main` | Sincronizada con `origin/main` (incluye el PR #2 de Render) |
| Cambios locales sin commit | Frontend bilingüe (es/en), saludos del chatbot, documentación; se conservan |
| Worktrees de otros integrantes | `Chatbot-BlackDogStore-Cloud-PR1` y `Chatbot-BlackDogStore-Cloud-Render`; no se tocan |
| Ramas locales | `main`, `feat/render-free-chatbot` (ya fusionada), `backup-antes-reescritura` |
| Servicios locales | `db`, `backend`, `chatbot`, `frontend` en Docker Compose, todos activos |
| Datos locales | 581 usuarios, 8955 conversaciones, 18032 mensajes (casi todos de pruebas de carga anteriores) |
| Migraciones | `makemigrations --check`: sin cambios pendientes |

## Pruebas ejecutadas antes de modificar el código

| Suite | Resultado |
|---|---|
| Pytest backend | 111 aprobadas |
| Pytest chatbot | 36 aprobadas |
| Newman (Postman) | 37 peticiones, 67 aserciones, 0 fallos |
| Playwright | 9 aprobadas |
| ESLint y TypeScript | Sin errores |
| `next build` | Correcto |

## Matriz de requisitos

| # | Requisito | Estado actual | Evidencia | Problema detectado | Acción necesaria | Prioridad | Prueba de aceptación |
|---|---|---|---|---|---|---|---|
| 01 | CRUD completo | Implementado y verificado (FAQ) | `faqs/views.py`, `test_faqs.py`, Playwright FAQ | No hay búsqueda ni orden en el listado; el administrador no puede supervisar operaciones | Agregar filtros y orden; registro de auditoría de solo lectura para supervisión | Media | Pytest por rol: crear, leer, editar, eliminar, 403 a cliente/asesor, 404 a inexistente |
| 02 | Paginación y tiempos | Implementado parcialmente | `PAGE_SIZE 20`, paginación en `/asesor` y `/admin/faqs` | Tamaño fijo, sin orden configurable; sin índices para `status` + fecha; `CONN_MAX_AGE=0` abre una conexión por petición; sin medición de latencia de listados | `page_size` con límite 100, `ordering`, índices compuestos, reutilizar conexiones, medir antes y después | Alta | Locust de lectura antes/después; prueba de número de consultas (N+1) |
| 03 | Múltiples tipos de usuario | Implementado y verificado | `core/permissions.py`, `RoleGate`, `test_advisor.py` | El administrador no tiene pantalla de supervisión | Pantalla de auditoría solo para administrador | Media | Pytest y Playwright: cliente, asesor y administrador con accesos permitidos y denegados |
| 04 | Proyecto en el servidor | Implementado parcialmente | `Dockerfile.render`, `infra/render/start.py` | Frontend no publicado; sin guía de despliegue; `.env.example` sin `POSTGRES_HOST/PORT/SSLMODE` | Plan de despliegue del frontend en Render Free; completar variables | Alta | Plan revisado; `docker build` del frontend en modo producción |
| 05 | BD completa y diagrama | Implementado parcialmente | `docs/diagrama-er.mmd`, `BASE_DE_DATOS.md` | Falta la entidad de auditoría del modelo inicial; faltan índices justificados | Modelo `AuditEvent`, migraciones no destructivas, diagrama actualizado | Media | `migrate` sobre la base existente sin pérdida de datos; diagrama coincide con modelos |
| 06 | CORS | No implementado | Django no envía cabeceras CORS | No hay lista explícita de orígenes ni respuesta a `OPTIONS` | Middleware con lista `CORS_ALLOWED_ORIGINS` por entorno | Alta | Pytest: origen permitido, no permitido (403), preflight, métodos y cabeceras |
| 07 | Pruebas contra caídas | Implementado parcialmente | Chatbot caído → 503 (`test_chat.py`) | El chatbot local usa `runserver`; sin `restart` ni `healthcheck` en backend/frontend; sin pruebas de base caída ni de reinicio | gunicorn en el chatbot, políticas de reinicio, pruebas locales de caída | Alta | Simulación local: parar `db` y `chatbot`, reiniciar `backend`; respuestas controladas |
| 08 | Autenticación y autorización | Implementado y verificado | `test_auth.py`, `test_token_expiration.py` | Ninguno grave | Cubrir 401/403 de los nuevos endpoints | Media | Pytest 401 sin token, 403 con rol incorrecto |
| 09 | Ingreso con correo | Implementado y verificado | `test_login_email_is_case_insensitive`, mismo 401 | Correo con espacios no se prueba | Normalizar espacios y probarlo | Baja | Pytest de login con mayúsculas y espacios |
| 10 | Tokens expirados y rutas protegidas | Implementado y verificado | `test_token_expiration.py`, Playwright redirección | Falta prueba de token revocado reutilizado tras logout | Agregar prueba | Baja | Pytest: logout y reutilización → 401 |
| 11 | Pantallas de errores | Implementado parcialmente | `not-found`, `error`, `mantenimiento`, `en-desarrollo` | Backend caído se muestra como una línea de texto; no se distingue tiempo de espera; falta `global-error` | Pantalla de servicio no disponible y de tiempo agotado, bilingüe | Media | Parar backend local y comprobar la pantalla; Playwright de páginas de error |
| 12 | Pruebas 1000–5000 (Locust) | Implementado parcialmente | Escenarios de 100 peticiones y 50/100/300 usuarios | No hay separación lectura/escritura; no se registra CPU/RAM automáticamente; no hay 1000–5000 | Escenarios A (1000–5000 peticiones) y B (50–500 usuarios), lectura y escritura separadas, recursos y gráficos | **Alta** | Reportes HTML/CSV con nombre único y tabla comparativa |
| 13 | Backups | No implementado | — | No hay respaldo ni prueba de restauración | Scripts de respaldo con fecha, suma SHA-256, retención y restauración en base temporal | Alta | Restaurar en base aislada y comparar conteos |
| Extra | VPC | Bloqueado | Render Free no ofrece red privada con Neon | Requiere servicios de pago o proveedores no autorizados | Solo evaluación documentada | Baja | — |
| Extra | Recursos del equipo | Implementado parcialmente | gunicorn con `GUNICORN_WORKERS` | Sin hilos ni reutilización de conexiones | Hilos de gunicorn y `CONN_MAX_AGE`, medidos | Baja | Locust antes/después |

## Riesgos de seguridad detectados

- **Rate limit detrás de proxy:** DRF usa la cabecera `X-Forwarded-For` completa cuando `NUM_PROXIES` no está definido. Detrás del proxy de Render un cliente puede variar esa cabecera para eludir el límite. Se agrega `NUM_PROXIES` configurable.
- **Archivo `00_INSTRUCCIONES_…md` en el repositorio público:** contiene instrucciones internas del equipo. Pendiente de decisión del equipo.

## Estado al cierre (29 de octubre de 2026)

Los requisitos 01 a 13 se implementaron y verificaron (`ARQUITECTURA.md` §6 e `INFORME_ENTREGA_80.md`). Quedan bloqueados por autorización:

- Publicar el frontend.
- La prueba de carga contra Render.
- El respaldo de Neon.

El riesgo de `NUM_PROXIES` se resolvió con una variable configurable. Falta validar su valor en Render.
