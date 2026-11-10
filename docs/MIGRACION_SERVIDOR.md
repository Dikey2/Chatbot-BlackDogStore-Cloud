# Migración de servidor y rollback

Procedimiento para mover la plataforma a otro proveedor sin perder datos y con
el menor corte posible. **Ningún paso se ejecuta contra producción sin
autorización del propietario.**

## 1. Qué hace portable al sistema

| Pieza | Cómo viaja |
|---|---|
| Backend, chatbot, frontend | Imágenes Docker de `backend/`, `services/chatbot/` y `frontend/` (la CI las construye en cada push). |
| Configuración | Solo variables de entorno (`.env.example`). Nada del proveedor está en el código. |
| Base de datos | PostgreSQL estándar (17). Respaldo `pg_dump -Fc` con `infra/backup/respaldar.sh`. |
| Esquema | Migraciones de Django reproducibles (`makemigrations --check` en la CI). |
| Salud | `GET /api/health/live/` (proceso vivo, sin dependencias) y `GET /api/health/` (base y chatbot; 503 si alguno falla). |
| Widget | `https://PLATAFORMA/widget.js`. Los negocios instalan esa URL: usar un **dominio propio estable** (CNAME) para cambiar de proveedor sin pedir a cada negocio que cambie su código. |

## 2. Antes del cambio

1. Bajar el TTL del DNS de la plataforma a 60 s con un día de anticipación.
2. Levantar el stack completo en el proveedor nuevo con las mismas variables
   (secretos nuevos generados allí; los actuales no se copian a mano).
3. Respaldar y restaurar en el entorno nuevo:
   ```bash
   infra/backup/respaldar.sh --neon            # o la base local
   infra/backup/restaurar-prueba.sh <archivo>  # comprueba conteos en una base aislada
   ```
4. Aplicar migraciones en el entorno nuevo como **paso explícito**
   (`python manage.py migrate`) y comprobar `makemigrations --check`.
5. Verificar el entorno nuevo: `/api/health/live/` = 200, `/api/health/` = 200,
   pruebas de humo (login, widget de un negocio de prueba, bandeja del asesor).

## 3. Corte (ventana corta)

1. Poner el stack actual en mantenimiento para escrituras (el frontend ya tiene
   `/mantenimiento`; el widget muestra "no disponible" sin romper la web del negocio).
2. Respaldo final → restauración en el entorno nuevo (solo el delta del último
   respaldo si se usa replicación lógica de PostgreSQL, que evita la ventana).
3. Cambiar el DNS al proveedor nuevo y vigilar los logs JSON (`status >= 500`,
   `duration_ms`, `request_id`) y `/api/health/`.

## 4. Rollback

- El entorno anterior queda **encendido y sin cambios** hasta confirmar el nuevo.
- Volver atrás = devolver el DNS (TTL 60 s). Si hubo escrituras en el nuevo,
  respaldarlas antes y reaplicarlas.
- Las migraciones se escriben compatibles hacia atrás (agregar primero, quitar
  después en otra versión): la versión anterior del código sigue funcionando con
  el esquema nuevo durante el rollback.
- Si la base quedó dañada: restaurar el último respaldo verificado
  (`docs/BACKUPS.md`).

## 5. Comprobaciones automáticas

- CI (`.github/workflows/ci.yml`): pruebas de backend sobre PostgreSQL, chatbot,
  TypeScript, ESLint, build de Next, sintaxis del widget, migraciones al día y
  build de las tres imágenes. No despliega.
- Resiliencia local: `infra/pruebas/resiliencia.sh` (chatbot, PostgreSQL y
  backend caídos o congelados).
