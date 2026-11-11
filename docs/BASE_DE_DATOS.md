# Base de datos

PostgreSQL 17. Solo la API Django lee y escribe. Solo contiene datos ficticios.

Fuente editable del diagrama: [`diagrama-er.mmd`](diagrama-er.mmd) (Mermaid). Versiones visuales: [`diagrama-er.svg`](diagrama-er.svg) y [`diagrama-er.png`](diagrama-er.png). Si se cambia la fuente, copiar el contenido al bloque de abajo y regenerar la imagen:

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD/docs:/data" minlag/mermaid-cli:11.4.2 \
  -i diagrama-er.mmd -o diagrama-er.svg -b white
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD/docs:/data" minlag/mermaid-cli:11.4.2 \
  -i diagrama-er.mmd -o diagrama-er.png -b white -w 2400 -s 2.5
```

```mermaid
%% Diagrama entidad-relación de la entrega del 100 % (plataforma multiempresa). Fuente editable (Mermaid).
%% Fuente de verdad: modelos y migraciones de Django (makemigrations --check: sin cambios).
%% Editar aquí o pegar en https://mermaid.live. Se copia en docs/BASE_DE_DATOS.md y se exporta
%% a docs/diagrama-er.svg y docs/diagrama-er.png (comandos en BASE_DE_DATOS.md).
%% Convenciones: PK clave primaria, FK clave foránea, UK valor único.
%% "NULL" en el comentario = la columna admite nulos; sin esa marca, NOT NULL.
%% |o en una relación = la clave foránea admite nulos.
erDiagram
    TENANTS_BUSINESS ||--o{ TENANTS_BUSINESSDOMAIN : "autoriza orígenes del widget"
    TENANTS_BUSINESS ||--o{ TENANTS_MEMBERSHIP : "tiene equipo"
    USERS_USER ||--o{ TENANTS_MEMBERSHIP : "pertenece (admin | asesor)"
    TENANTS_BUSINESS ||--o| TENANTS_CHATBOTCONFIG : "configura su chatbot"
    TENANTS_BUSINESS ||--o{ TENANTS_VISITORSESSION : "sesiones anónimas del widget"
    TENANTS_BUSINESS |o--o{ FAQS_FAQ : "sus FAQ"
    TENANTS_BUSINESS |o--o{ CHAT_CONVERSATION : "sus conversaciones"
    TENANTS_BUSINESS |o--o{ AUDIT_AUDITEVENT : "sus eventos"
    USERS_USER |o--o{ CHAT_CONVERSATION : "cliente (user_id)"
    TENANTS_VISITORSESSION |o--o{ CHAT_CONVERSATION : "visitante (visitor_id)"
    USERS_USER |o--o{ CHAT_CONVERSATION : "asesor asignado (assigned_to_id)"
    USERS_USER ||--o| AUTHTOKEN_TOKEN : "sesión"
    CHAT_CONVERSATION ||--o{ CHAT_MESSAGE : "contiene"
    USERS_USER |o--o{ AUDIT_AUDITEVENT : "genera"

    TENANTS_BUSINESS {
        bigint id PK
        varchar(40) public_id UK "id público del widget (no es secreto)"
        varchar(60) slug UK
        varchar(120) name "nombre comercial"
        text description
        varchar(500) logo_url "https, puede estar vacío"
        boolean is_active "false = suspendido"
        timestamptz created_at
        timestamptz updated_at
    }
    TENANTS_BUSINESSDOMAIN {
        bigint id PK
        bigint business_id FK "ON DELETE CASCADE"
        varchar(255) origin "scheme://host[:puerto]; único con business_id"
        timestamptz created_at
    }
    TENANTS_MEMBERSHIP {
        bigint id PK
        bigint user_id FK "ON DELETE CASCADE; único con business_id"
        bigint business_id FK "ON DELETE CASCADE"
        varchar(10) role "admin | asesor (fuente de autoridad)"
        timestamptz created_at
    }
    TENANTS_CHATBOTCONFIG {
        bigint business_id PK, FK "uno a uno; ON DELETE CASCADE"
        varchar(80) assistant_name
        varchar(300) welcome_message
        varchar(300) no_answer_message
        varchar(300) handoff_message
        varchar(255) handoff_keywords "reglas de derivación"
        text schedule "puede estar vacío"
        text contact_info "puede estar vacío"
        varchar(7) primary_color "#RRGGBB"
        boolean is_active
        varchar(500) catalog_api_url "API de productos; vacío = sin catálogo"
        varchar(500) catalog_page_url "enlace al catálogo; puede estar vacío"
        timestamptz updated_at
    }
    TENANTS_VISITORSESSION {
        bigint id PK
        bigint business_id FK "ON DELETE CASCADE"
        varchar(64) token_hash UK "SHA-256; el token en claro no se guarda"
        varchar(255) origin
        integer message_count "control de abuso"
        timestamptz created_at
        timestamptz last_seen_at
        timestamptz expires_at
        timestamptz revoked_at "NULL"
    }
    USERS_USER {
        bigint id PK
        varchar(150) name
        varchar(254) email UK "inicio de sesión"
        varchar(128) password "hash PBKDF2-SHA256"
        varchar(10) role "cliente | asesor | admin (heredado)"
        boolean is_active
        boolean is_staff
        boolean is_superuser "superadministrador de la plataforma"
        timestamptz date_joined
        timestamptz last_login "NULL"
    }
    AUTHTOKEN_TOKEN {
        varchar(40) key PK "token de sesión"
        bigint user_id FK, UK "ON DELETE CASCADE"
        timestamptz created "caduca a las TOKEN_TTL_HOURS"
    }
    FAQS_FAQ {
        bigint id PK
        bigint business_id FK "NULL en BD (rollback seguro); ON DELETE CASCADE"
        varchar(50) category
        varchar(255) question
        text answer
        varchar(255) keywords "separadas por coma"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    CHAT_CONVERSATION {
        bigint id PK
        bigint business_id FK "NULL en BD (rollback seguro); ON DELETE CASCADE"
        bigint user_id FK "NULL; cliente registrado; ON DELETE CASCADE"
        bigint visitor_id FK "NULL; visitante del widget; ON DELETE SET NULL"
        bigint assigned_to_id FK "NULL; asesor; ON DELETE SET NULL"
        varchar(10) status "abierta | derivada | atendiendo | cerrada"
        timestamptz created_at
    }
    CHAT_MESSAGE {
        bigint id PK
        bigint conversation_id FK "ON DELETE CASCADE"
        varchar(10) sender "cliente | bot | asesor"
        text content
        timestamptz created_at
    }
    AUDIT_AUDITEVENT {
        bigint id PK
        bigint business_id FK "NULL = evento de plataforma; ON DELETE SET NULL"
        bigint user_id FK "NULL; ON DELETE SET NULL"
        varchar(254) email "copia del correo"
        varchar(30) action "login, faq_crear, negocio_crear, ..."
        varchar(10) result "exito | fallo"
        varchar(64) source "IP del cliente"
        varchar(255) detail "sin contraseñas, tokens ni mensajes"
        timestamptz created_at
    }
    CORE_RATECOUNTER {
        varchar(200) key PK "límite + cliente (tabla operativa, sin relaciones)"
        timestamptz window_start "inicio de la ventana"
        integer count "peticiones en la ventana"
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
| `audit_auditevent` | `audit` | RF-12 | Registro inmutable (sin edición ni borrado por la API). Si se borra el usuario, el evento queda con `user_id` nulo y conserva el correo. |
| `django_cache` | `core` | Rate limit | Contadores compartidos entre procesos de gunicorn. |

Django crea además sus tablas internas (`django_*`, `auth_group`, `auth_permission`).

## Integridad referencial

| Relación | Regla | Motivo |
|---|---|---|
| `chat_conversation.user_id → users_user.id` | `ON DELETE CASCADE` | El historial pertenece al usuario |
| `chat_message.conversation_id → chat_conversation.id` | `ON DELETE CASCADE` | Un mensaje no existe sin su conversación |
| `authtoken_token.user_id → users_user.id` | `ON DELETE CASCADE`, único | Un token por usuario |
| `audit_auditevent.user_id → users_user.id` | `ON DELETE SET NULL` | La auditoría debe sobrevivir al usuario |

Restricciones: `users_user.email` es único; `status`, `sender`, `role`, `action` y `result` solo aceptan los valores de sus `choices` (validados por la API).

## Índices

| Índice | Columnas | Consulta que acelera |
|---|---|---|
| `conv_estado_fecha_idx` | `status, created_at DESC, id DESC` | Bandeja del asesor: `WHERE status = … ORDER BY created_at DESC` |
| `conv_usuario_fecha_idx` | `user_id, created_at DESC, id DESC` | Historial propio y `latest` |
| `msg_conv_fecha_idx` | `conversation_id, created_at, id` | Mensajes de una conversación en orden |
| `audit_recientes_idx` | `created_at DESC, id DESC` | Listado de auditoría |
| `audit_accion_idx` | `action, created_at DESC` | Auditoría filtrada por acción |
| `faqs_faq_category_*` | `category` | Filtro por categoría |

Medición con `EXPLAIN ANALYZE` sobre 9056 conversaciones (bandeja, página 3), 29 de octubre de 2026:

| Plan | Tiempo |
|---|---|
| Sin índice: `Seq Scan` + `Sort` de 3184 filas | 2,18 ms |
| Con `conv_estado_fecha_idx`: `Index Scan`, sin ordenamiento | 1,08 ms |

Con el volumen actual la diferencia es pequeña. El recorrido completo crece con el número de conversaciones; el índice solo lee las filas de la página pedida. La mejora grande de rendimiento vino de reutilizar conexiones (ver `PRUEBAS.md`).

## Entidad planificada

- **Archivo** (RF-10): metadatos de archivos adjuntos. No se implementa en esta entrega porque requiere un almacenamiento externo de archivos y la regla del equipo es no agregar servicios que no sean imprescindibles.

## Diferencias con el modelo inicial del documento

- `FAQ` añade `keywords`: el chatbot por reglas necesita palabras clave para elegir la respuesta.
- Se añade `authtoken_token` para las sesiones.
- `EventoAuditoría` se implementa como `audit_auditevent`, con `email`, `source` y `detail` para poder revisar intentos fallidos sin guardar datos sensibles.

## Migraciones

```bash
docker compose run --rm -v "$PWD/backend:/app" backend python manage.py makemigrations
docker compose up -d --build backend     # aplica las migraciones al iniciar
```
