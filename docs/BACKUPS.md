# Respaldos y restauración de PostgreSQL

## Procedimiento

| Paso | Comando | Qué hace |
|---|---|---|
| Respaldo local | `infra/backup/respaldar.sh` | `pg_dump` en formato *custom* desde el contenedor `db` |
| Respaldo de Neon | `NEON_DATABASE_URL=… infra/backup/respaldar.sh --neon` | Lo mismo contra Neon, con `pg_dump` 17 en un contenedor temporal |
| Prueba de restauración | `infra/backup/restaurar-prueba.sh backups/<archivo>.dump` | Restaura en una base temporal aislada, compara filas y la elimina |

### Respaldo

- **Nombre con fecha y hora:** `backups/local_AAAAMMDD-HHMMSS.dump` o `backups/neon_AAAAMMDD-HHMMSS.dump`.
- **Almacenamiento:** carpeta `backups/`, excluida de Git en `.gitignore`. Los archivos se crean con permisos `600` (`umask 077`): solo los puede leer el usuario que los genera.
- **Credenciales:** el script local lee usuario y base de `.env`. El de Neon recibe la URL por la variable `NEON_DATABASE_URL` y la pasa al contenedor como variable de entorno, así que no aparece en la línea de comandos ni en el archivo.
- **Integridad:**
  1. `pg_restore --list` comprueba que el archivo se puede leer completo.
  2. Se guarda la suma SHA-256 en `<archivo>.dump.sha256`.
  3. La prueba de restauración vuelve a verificar esa suma antes de usar el archivo.
- **Retención:** se conservan los 7 respaldos más recientes de cada origen (`BACKUP_KEEP=7`). Los más antiguos se eliminan al crear uno nuevo.
- **Formato:** `--no-owner --no-privileges`, para poder restaurar en otra base u otro usuario.

### Restauración de prueba

`restaurar-prueba.sh` **nunca escribe en la base principal**:

1. Verifica la suma SHA-256 del respaldo.
2. Crea la base temporal `restore_<fecha>_<hora>` en el contenedor local. El script se detiene si el nombre coincidiera con el de la base principal.
3. Restaura con `pg_restore --exit-on-error`: cualquier error detiene el proceso.
4. Cuenta las filas de `users_user`, `chat_conversation`, `chat_message`, `faqs_faq`, `audit_auditevent` y `django_migrations`, y las compara con la base de origen.
5. Elimina la base temporal. Con `--conservar` la deja para inspeccionarla.

### Recuperación real (solo si se pierde la base)

Requiere autorización del equipo, porque reemplaza datos:

```bash
docker compose stop backend frontend
docker compose exec -T db pg_restore --clean --if-exists --no-owner --no-privileges \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/<archivo>.dump
docker compose start backend frontend
```

Antes de restaurar, se respalda la base actual con `respaldar.sh`, para poder volver atrás.

## Neon (plan Free)

Neon guarda el historial de cambios y permite restaurar a un instante anterior (*instant restore / point-in-time restore*). En el plan Free esa ventana es corta (horas, no días). La duración exacta se revisa en la consola de Neon, en la configuración del proyecto, antes de depender de ella.

Por eso se propone complementar con un respaldo propio de Neon (`respaldar.sh --neon`) antes de cada entrega o cambio de esquema. No se automatizó con un programador de tareas en la nube: requeriría guardar la URL de Neon en otro servicio. Tampoco se ejecutó contra Neon sin autorización.

## Prueba realizada (29 de octubre de 2026, base local)

| Paso | Resultado |
|---|---|
| Respaldo | `backups/local_20261029-151108.dump`, 1,3 MB, permisos `-rw-------` |
| SHA-256 | `a382d8f25362f22e726663767d41a4376f7bee791c1f78681ecd3fca30f19107` |
| Lectura completa (`pg_restore --list`) | Correcta |
| Verificación de la suma antes de restaurar | `OK` |
| Restauración en `restore_20261029_151110` | Correcta, sin errores |
| Conteos restaurados | 2337 usuarios, 10 225 conversaciones, 80 676 mensajes, 5 FAQ, 5458 eventos de auditoría, 29 migraciones: **coinciden con la base de origen** |
| Base temporal | Eliminada; la base principal no se modificó |
| Retención (`BACKUP_KEEP=2`, tres respaldos seguidos) | Quedan los 2 más recientes; se eliminó el más antiguo |
| Respaldo alterado (un byte agregado) | `shasum` responde `FAILED` y el script se detiene antes de crear la base temporal |

Evidencias: `docs/evidencias/backup_respaldo_20261029-151108.log` y `docs/evidencias/backup_restauracion_20261029-151110.log`.

El respaldo de Neon (`--neon`) no se ejecutó: requiere la URL de producción y la autorización del equipo.
