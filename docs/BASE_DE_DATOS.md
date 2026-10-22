# Base de datos

PostgreSQL 17. Solo la API Django lee y escribe. Solo contiene datos ficticios.

Fuente editable del diagrama: [`diagrama-er.mmd`](diagrama-er.mmd) (Mermaid). Si se cambia ese archivo, copiar el contenido al bloque de abajo.

```mermaid
%% Diagrama entidad-relación. Fuente editable (Mermaid).
%% Editar aquí o pegar en https://mermaid.live. Se muestra en docs/BASE_DE_DATOS.md.
%% Las entidades marcadas PLANIFICADA aún no existen en la base de datos.
erDiagram
    USERS_USER ||--o{ CHAT_CONVERSATION : "inicia"
    USERS_USER ||--o| AUTHTOKEN_TOKEN : "tiene sesión"
    CHAT_CONVERSATION ||--o{ CHAT_MESSAGE : "contiene"
    USERS_USER ||--o{ EVENTO_AUDITORIA : "genera (PLANIFICADA)"
    CHAT_CONVERSATION ||--o{ ARCHIVO : "adjunta (PLANIFICADA)"

    USERS_USER {
        bigint id PK
        varchar name "nombre"
        varchar email UK "correo, usado para iniciar sesión"
        varchar password "hash PBKDF2-SHA256, nunca texto plano"
        varchar role "cliente | asesor | admin"
        boolean is_active
        boolean is_staff
        boolean is_superuser
        timestamptz date_joined
        timestamptz last_login
    }
    AUTHTOKEN_TOKEN {
        varchar key PK "token de sesión"
        bigint user_id FK,UK
        timestamptz created
    }
    FAQS_FAQ {
        bigint id PK
        varchar category "categoría, indexada"
        varchar question "pregunta"
        text answer "respuesta"
        varchar keywords "palabras clave separadas por coma"
        boolean is_active "estado"
        timestamptz created_at
        timestamptz updated_at
    }
    CHAT_CONVERSATION {
        bigint id PK
        bigint user_id FK
        varchar status "abierta | derivada | cerrada"
        timestamptz created_at
    }
    CHAT_MESSAGE {
        bigint id PK
        bigint conversation_id FK
        varchar sender "cliente | bot | asesor"
        text content
        timestamptz created_at
    }
    EVENTO_AUDITORIA {
        bigint id PK
        bigint user_id FK "PLANIFICADA, RF-12"
        varchar accion
        varchar resultado
        timestamptz fecha
    }
    ARCHIVO {
        bigint id PK
        bigint conversation_id FK "PLANIFICADA, RF-10"
        varchar clave_s3
        varchar nombre
        varchar tipo
        timestamptz creado_en
    }
```

## Tablas implementadas

| Tabla | App Django | Requisito | Notas |
|---|---|---|---|
| `users_user` | `users` | RF-01, RF-02, RF-08 | Correo único. El rol por defecto es `cliente`. |
| `authtoken_token` | DRF | RF-02 | Un token por usuario. Se borra al cerrar sesión. |
| `faqs_faq` | `faqs` | RF-04, RF-07 | `is_active=false` oculta la FAQ al público y al chatbot. |
| `chat_conversation` | `chat` | RF-05, RF-09 | Pasa a `derivada` cuando el chatbot no encuentra respuesta. |
| `chat_message` | `chat` | RF-05 | Se borra en cascada con su conversación. |

Django crea además sus tablas internas (`django_*`, `auth_group`, `auth_permission`).

## Entidades planificadas

- **EventoAuditoría** (RF-12): accesos y operaciones relevantes.
- **Archivo** (RF-10): metadatos de archivos guardados en S3.

## Diferencias con el modelo inicial del documento

- `FAQ` añade `keywords`: el chatbot por reglas necesita palabras clave para elegir la respuesta.
- Se añade `authtoken_token` para las sesiones.

## Migraciones

```bash
docker compose run --rm -v "$PWD/backend:/app" backend python manage.py makemigrations
docker compose up -d --build backend     # aplica las migraciones al iniciar
```
