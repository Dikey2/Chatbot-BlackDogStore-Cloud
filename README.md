# Chatbot Black Dog Store Cloud

Prototipo académico del curso Desarrollo de Soluciones en la Nube. Está aislado de la web comercial de Black Dog Store y solo usa datos ficticios.

| Documento | Contenido |
|---|---|
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Componentes, decisiones, estado del 25 % y trabajo restante |
| [docs/API.md](docs/API.md) | Endpoints, roles, errores y rate limits |
| [docs/BASE_DE_DATOS.md](docs/BASE_DE_DATOS.md) | Diagrama entidad-relación editable y tablas |
| [docs/PRUEBAS.md](docs/PRUEBAS.md) | Pruebas ejecutadas, resultados y cómo repetirlas |
| [infra/aws/README.md](infra/aws/README.md) | Diseño de IAM y S3 (sin recursos creados) |

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

`seed_demo` crea `admin@example.com`, `asesor@example.com` y `cliente@example.com`, los tres con la contraseña `DEMO_PASSWORD` de `.env`, y 3 preguntas frecuentes ficticias.

## Recorrido de demostración

1. Abrir http://localhost:3000 y comprobar que los tres servicios están operativos.
2. Crear una cuenta en `/registro`. Al terminar se abre `/chat`.
3. Preguntar "¿Cuál es el horario?": responde una FAQ.
4. Preguntar "¿Cuánto cuesta la laptop X?": no hay FAQ y la consulta se deriva a un asesor.
5. Cerrar sesión. `/chat` vuelve a pedir login.

## Comandos

```bash
docker compose ps                                        # estado
docker compose logs -f backend                           # logs de un servicio
docker compose down                                      # detener (conserva los datos)

docker compose run --rm backend pytest                   # pruebas de la API (usa PostgreSQL)
docker compose run --rm chatbot pytest                   # pruebas del chatbot
cd frontend && npm run lint && npx tsc --noEmit          # verificación del frontend
cd frontend && npm run test:e2e                          # Playwright, con el stack levantado

# Crear migraciones después de cambiar modelos (escribe en ./backend)
docker compose run --rm -v "$PWD/backend:/app" backend python manage.py makemigrations

# Consola de PostgreSQL
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
```

Newman (colección Postman) y Locust (carga): ver [docs/PRUEBAS.md](docs/PRUEBAS.md).

Después de cambiar código hay que reconstruir: `docker compose up -d --build`.

`docker compose down -v` borra también la base de datos local.

## Seguridad

- `.env` está en `.gitignore`. Solo se versiona `.env.example`, sin valores secretos.
- Los servicios no arrancan si falta un secreto.
- Los puertos se publican solo en `127.0.0.1`. PostgreSQL no se publica.
- Las contraseñas se guardan con hash PBKDF2-SHA256.
- El token de sesión se guarda en una cookie `httpOnly`; el navegador nunca llama a la API.
- Rate limits en registro, login, chat y resto de la API.
- El backend usa el servidor de desarrollo de Django. No es apto para publicar.
- No se ha creado ningún recurso en AWS.
