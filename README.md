# Chatbot Black Dog Store Cloud

Prototipo académico del curso Desarrollo de Soluciones en la Nube. Está aislado de la web comercial de Black Dog Store y solo usa datos ficticios.

| Documento | Contenido |
|---|---|
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Componentes, decisiones, estado del 25 % y trabajo restante |
| [docs/API.md](docs/API.md) | Endpoints, roles, errores y rate limits |
| [docs/BASE_DE_DATOS.md](docs/BASE_DE_DATOS.md) | Diagrama entidad-relación editable y tablas |
| [docs/PRUEBAS.md](docs/PRUEBAS.md) | Pruebas ejecutadas, resultados y cómo repetirlas |
| [docs/MIGRACION_SERVIDOR.md](docs/MIGRACION_SERVIDOR.md) | Migración de proveedor y rollback |
| [infra/aws/README.md](infra/aws/README.md) | Diseño de IAM y S3 y script `preparar-s3.sh` (sin recursos creados) |

## Requisitos

- Docker Desktop (Docker Compose v2).
- Node.js 20.9 o superior, solo para las pruebas Playwright o para trabajar el frontend fuera de Docker.

## Primer arranque

```bash
cp .env.example .env
# Completar DJANGO_SECRET_KEY, CHATBOT_SECRET_KEY, POSTGRES_PASSWORD y DEMO_PASSWORD.
# Generar cada valor con:
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

docker compose up -d --build
docker compose exec backend python manage.py seed_demo   # usuarios y FAQ ficticios
```

El backend aplica las migraciones al iniciar.

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API Django | http://localhost:8000/api/health/ |
| Chatbot | http://localhost:8001/health/ |

`seed_demo` crea, todos con la contraseña `DEMO_PASSWORD` de `.env` y datos ficticios:

| Cuenta | Rol |
|---|---|
| `plataforma@example.com` | Superadministrador de la plataforma |
| `admin@example.com`, `asesor@example.com` | Administrador y asesor de **Black Dog Store** (negocio piloto) |
| `admin@cafe.example.com`, `asesor@cafe.example.com` | Administrador y asesor de **Café Aurora (ficticio)**, segundo negocio |
| `cliente@example.com` | Cliente registrado del chat de la plataforma |

## Recorrido de demostración

1. Abrir http://localhost:3000 y comprobar que los tres servicios están operativos.
2. Crear una cuenta en `/registro`. Al terminar se abre `/chat`.
3. Preguntar "¿Cuál es el horario?": responde una FAQ.
4. Preguntar "¿Cuánto cuesta la laptop X?": no hay FAQ y la consulta se deriva a un asesor.
5. Cerrar sesión. `/chat` vuelve a pedir login.
6. Entrar como `asesor@example.com` y abrir "Bandeja del asesor" (`/asesor`): ver la consulta derivada del paso 4, responderla y cerrarla. Al recargar `/chat`, el cliente ve la respuesta.
7. Entrar como `admin@example.com` y abrir "Administrar FAQ" (`/admin/faqs`): crear, editar, desactivar o eliminar preguntas. El chatbot usa los cambios en la siguiente consulta.
8. Como administrador, abrir "Auditoría de accesos" (`/admin/auditoria`): aparecen los inicios de sesión, intentos fallidos, accesos denegados y cambios de FAQ, con filtros por acción y resultado.
9. Cambiar el idioma con los botones ES / EN de la parte superior.

## Plataforma multiempresa y widget (entrega del 100 %)

Una sola plataforma atiende a varios negocios. Cada negocio tiene sus FAQ, su
configuración del chatbot, su equipo, sus dominios autorizados y sus
conversaciones; los datos de uno nunca aparecen en otro.

1. Como `admin@example.com`, abrir `/panel` (métricas) y `/admin/chatbot`:
   configuración del asistente, dominios autorizados y **código de instalación**.
2. Pegar el código en cualquier web autorizada:
   ```html
   <script src="https://PLATAFORMA/widget.js" data-chatbot-id="ID_PUBLICO" defer></script>
   ```
   Opcionales: `data-position="left"`, `data-offset-bottom="96"`,
   `data-launcher="none"` (la página abre el chat con `window.BDChatbot.open()`).
3. Probar el widget en `/vista-previa?id=ID_PUBLICO` o en la segunda web ficticia:
   `docker compose --profile demo up -d demo-cafe` → http://localhost:8090.
4. El visitante conversa sin cuenta. Si el bot no tiene la respuesta, o el
   visitante pide un asesor, la consulta aparece en `/asesor` del negocio.
5. Como `plataforma@example.com`, abrir `/plataforma`: crear, suspender o
   activar negocios, asignar administradores y ver la auditoría global.

## Comandos

```bash
docker compose ps                                        # estado
docker compose logs -f backend                           # logs de un servicio
docker compose down                                      # detener (conserva los datos)

docker compose run --rm backend pytest                   # pruebas de la API (usa PostgreSQL)
docker compose run --rm chatbot pytest                   # pruebas del chatbot
cd frontend && npm run lint && npx tsc --noEmit          # verificación del frontend
cd frontend && DEMO_PASSWORD=... npm run test:e2e        # Playwright, con el stack levantado

# Crear migraciones después de cambiar modelos (escribe en ./backend)
docker compose run --rm -v "$PWD/backend:/app" backend python manage.py makemigrations

# Consola de PostgreSQL
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
```

```bash
loadtest/campana.sh                                      # carga con Locust (1000–5000 y 50–500 usuarios), solo local
loadtest/campana-100.sh antes                            # 10 000–50 000 solicitudes con 100 usuarios, solo local
python3 loadtest/resumen.py                              # tabla y gráficos de los resultados
infra/pruebas/resiliencia.sh                             # caídas controladas de chatbot, base y backend (local)
infra/backup/respaldar.sh                                # respaldo con fecha, SHA-256 y retención
infra/backup/restaurar-prueba.sh backups/<archivo>.dump  # restauración en una base temporal aislada
```

Newman (colección Postman), Locust y resiliencia: ver [docs/PRUEBAS.md](docs/PRUEBAS.md). Respaldos: [docs/BACKUPS.md](docs/BACKUPS.md). Despliegue en Render y Neon: [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

Después de cambiar código hay que reconstruir: `docker compose up -d --build`.

`docker compose down -v` borra también la base de datos local.

## Seguridad

- `.env` está en `.gitignore`. Solo se versiona `.env.example`, sin valores secretos.
- Los servicios no arrancan si falta un secreto.
- Los puertos se publican solo en `127.0.0.1`. PostgreSQL no se publica.
- Las contraseñas se guardan con hash PBKDF2-SHA256.
- El token de sesión se guarda en una cookie `httpOnly`; el navegador nunca llama a la API.
- Rate limits en registro, login, chat y resto de la API.
- CORS con lista explícita (`CORS_ALLOWED_ORIGINS`); un origen no autorizado recibe 403.
- Auditoría de accesos y operaciones, sin contraseñas ni tokens, separada por negocio.
- Multiempresa: el negocio lo resuelve el servidor; `X-Business-Id` solo elige entre los negocios del usuario. La autoridad es la membresía (admin o asesor) en ese negocio.
- Widget público: sin claves en el JavaScript; CORS por negocio (solo sus dominios autorizados); visitantes con token anónimo de 24 h (en la base solo su hash), rotación y límites por IP, por visitante y por sesión.
- Logs estructurados en JSON con request ID; nunca contraseñas, tokens ni el texto de los mensajes.
- En producción, `DJANGO_HTTPS=true` activa cookies seguras, HSTS y redirección a HTTPS.
- El backend corre con gunicorn (4 procesos). `DEBUG=true` en `.env` es solo para el entorno local; antes de publicar hay que ponerlo en `false` y revisar `ALLOWED_HOSTS`.
- No se ha creado ningún recurso en AWS.
