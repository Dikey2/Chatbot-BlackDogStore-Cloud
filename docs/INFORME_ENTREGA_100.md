# Informe de la entrega del 100 %

**Proyecto:** Chatbot Black Dog Store Cloud — plataforma multiempresa con widget flotante
**Curso:** Desarrollo de Soluciones en la Nube
**Equipo:** Villar Collantes, Alexis; Morales Puma, Gisela; Kana Huillcapacco, Cesar; Ochoa Chama, Briggith
**Fecha:** 11 de noviembre de 2026

## 1. Qué se entrega

| Pieza | Dónde |
|---|---|
| Repositorio | `Dikey2/Chatbot-BlackDogStore-Cloud`, rama `main` |
| API (backend Django) en Render | `https://chatbot-blackdogstore-cloud.onrender.com` |
| Interfaz web (Next.js) en Render | `https://blackdog-chatbot-frontend.onrender.com` |
| Base de datos | Neon (PostgreSQL 18.6) |
| Sitio de prueba con el widget instalado | Tienda demo `https://blackdog-store-demo.onrender.com` |

Todos los servicios usan el plan gratuito de Render: se duermen tras 15 minutos sin tráfico y la primera
petición tarda entre 20 y 40 s (ver la preparación de la sección 5).

## 2. Cómo leer este informe

- **Cumple:** implementado y comprobado.
- **Parcial:** implementado, pero falta una parte de lo que pide el criterio; se explica cuál.
- **Falta:** no implementado; se explica por qué.
- **Local:** comprobado en Docker Compose en el equipo del equipo de trabajo.
- **Render:** comprobado en los servicios publicados, con consultas de solo lectura (`PRUEBAS.md` §14).

## 3. Requisitos de la rúbrica

### 3.1 Entrega del 25 %

| Requisito | Estado | Local | Render | Evidencia |
|---|---|---|---|---|
| Entorno cloud | Cumple | — | Sí | Render + Neon; `/api/health/` → 200 con `database ok` y `chatbot ok` |
| Endpoints | Cumple | Sí | Sí | `API.md`, colecciones de `postman/` |
| Registro y login diferenciados | Cumple | Sí | Sí | `/registro` y `/login`; `POST /api/auth/register/` y `/api/auth/login/` |
| Rate limits | Parcial | Sí | **No aplicado** | `config/settings.py` (anónimo 60/min, login 10/min, chat 30/min, widget 10-120/min); en local, 60 × 200 y luego 429. En Render, 70 peticiones anónimas seguidas → 70 × 200: hallazgo de configuración (`PRUEBAS.md` §16.4) |
| Vista de página inexistente o en desarrollo | Cumple | Sí | Sí | 404 propio en el frontend y JSON en la API; `/en-desarrollo` y `/mantenimiento` |
| Control de respuestas HTTP | Cumple | Sí | Sí | `core/errors.py`: formato `{"error":{"code","message"}}`; en Render se vieron 401, 403 y 404 |
| CRUD estructurado | Cumple | Sí | Sí | FAQ (`faqs/views.py`), equipo y dominios |
| Variables de entorno | Cumple | Sí | Sí | `.env.example`; ningún `.env` en el repositorio |
| Cifrado de contraseñas | Cumple | Sí | Sí | PBKDF2-SHA256 con 1 000 000 de iteraciones y validadores de Django |
| Pruebas unitarias y masivas | Cumple | Sí | CI | API 238, chatbot 43 y frontend 10 pruebas correctas en GitHub Actions; Playwright y Newman en local |
| BD conectada y diagrama editable | Cumple | Sí | Sí | `diagrama-er.mmd` (editable), `diagrama-er.svg`, `BASE_DE_DATOS.md` |
| Pruebas de 50 a 100 en el servidor | Cumple | Sí | Sí | Render: 98 solicitudes con 10 usuarios, 0 fallos (`PRUEBAS.md` §16); local: §4 |
| Extra: cifrar el código | Cumple | Sí | Pendiente de despliegue | `widget.js` ofuscado con `javascript-obfuscator`; frontend minificado y sin mapas de código fuente (`PRUEBAS.md` §17) |
| Extra: diagrama de BD | Cumple | — | — | `diagrama-er.*`, actualizado con la plataforma multiempresa |

### 3.2 Entrega del 80 %

| Requisito | Estado | Local | Render | Evidencia |
|---|---|---|---|---|
| CRUD completo | Cumple | Sí | Sí | FAQ, equipo, dominios y configuración desde el panel |
| Paginación con tiempos cómodos | Cumple | Sí | Sí | 20 por página; en Render `/api/faqs/` devuelve `count 22` y `next` |
| Varios tipos de usuario | Cumple | Sí | Sí | Superadministrador, administrador y asesor por negocio, cliente |
| Proyecto en el servidor | Cumple | — | Sí | Render despliega `main` automáticamente |
| BD completa y diagrama | Cumple | Sí | Sí | `BASE_DE_DATOS.md` |
| CORS restringido | Cumple | Sí | Sí | Origen desconocido → 403 en Render; sin comodines en producción; el widget solo acepta los dominios de cada negocio |
| Pruebas previas contra caídas | Cumple | Sí | No | `PRUEBAS.md` §11 y §13. En Render no se provocaron caídas |
| Autenticación y autorización | Cumple | Sí | Sí | Sin token o con token falso → 401 en Render |
| Ingreso con cuenta de correo | Cumple | Sí | Sí | Login con correo y contraseña. No hay ingreso con Google |
| Tokens expirados y rutas sin permiso | Cumple | Sí | Sí | Caducidad absoluta (`users/authentication.py`); `/panel` sin sesión redirige a `/login` |
| Pantallas de errores previstos | Cumple | Sí | Parcial | «Servicio no disponible», «El servidor tardó demasiado», error global (`PRUEBAS.md` §13). En Render solo se observó el reintento del widget al despertar el servidor |
| Pruebas de 1000 a 5000 en el servidor | Cumple | Sí | Sí | Render: 995 y 4 993 solicitudes con 20 y 25 usuarios, 0 fallos, p95 450 y 340 ms (`PRUEBAS.md` §16); local: §10 |
| Control de backups | Cumple | Sí | Sí | `infra/backup/`; respaldo real de Neon `neon_20261110-171155.dump`, verificado y restaurado en una copia (`BACKUPS.md`) |
| Extra: VPC | Falta (justificado) | — | — | Render Free no ofrece red privada con Neon (`DESPLIEGUE.md` §5) |
| Extra: recursos del equipo | Cumple | Sí | — | `GUNICORN_WORKERS` medido (`PRUEBAS.md` §10) |

### 3.3 Entrega del 100 %

| Requisito | Estado | Local | Render | Evidencia |
|---|---|---|---|---|
| Proyecto funcional al 100 % | Cumple | Sí | Sí | Plataforma multiempresa, widget en la tienda demo, 22 FAQ reales, catálogo con precios reales (`PRUEBAS.md` §14) |
| Pruebas de 10 000 a 50 000 en el servidor | Parcial | Sí | Hasta 5 000 | `PRUEBAS.md` §12: 50 000 solicitudes con 100 usuarios y 0 fallos en local. Contra Render, prueba controlada hasta 5 000 (§16); más volumen no se autorizó por los límites del plan gratuito |
| Controlar los cuellos de botella | Cumple | Sí | Desplegado | Contador atómico de rate limit, `gunicorn --preload`, reciclaje escalonado (`PRUEBAS.md` §12.6) |
| Logs estructurados | Cumple | Sí | No revisado | JSON con `request_id`, sin datos sensibles (`core/logging.py`). Los logs de Render no se revisaron para este informe |
| Contener errores y mostrar el motivo de una caída | Cumple | Sí | Parcial | 503/504 con código propio, pantallas de servicio no disponible, reintentos del widget (`PRUEBAS.md` §13 y §15) |
| Extra: pipeline de CI/CD | Cumple | — | Sí | `.github/workflows/ci.yml` (API, chatbot, frontend, imágenes Docker) + SonarCloud; Render despliega `main` |
| Extra: migración de servidor | Cumple | — | — | `MIGRACION_SERVIDOR.md`: preparación, corte, rollback y comprobaciones |

### 3.4 Requisitos generales

| Requisito | Estado | Evidencia |
|---|---|---|
| Documentación actualizada | Cumple | Este informe, `ARQUITECTURA.md` §7 y `PRUEBAS.md` §12-15 |
| Diagramas de rendimiento y estrés | Cumple | `evidencias/graficos-carga-100-*.png` (4 gráficos) y `evidencias/graficos-carga.png` (80 %) |
| Caídas del servidor con motivo y solución | Cumple | `PRUEBAS.md` §15 (10 incidencias) y §12.8 |
| Mencionar lo agregado fuera de la rúbrica | Cumple | Sección 4 |

## 4. Lo que se agregó fuera de la rúbrica

Se presenta aparte, como pide la indicación del docente:

1. **Plataforma multiempresa (SaaS).** Varios negocios en la misma instalación, con datos aislados.
   Black Dog Store es el negocio piloto; en el entorno local, una cafetería de prueba demuestra el aislamiento.
2. **Widget flotante instalable.** Una etiqueta `<script>` agrega el chat a cualquier sitio autorizado.
   Tiene tema claro, oscuro o el del sitio, y una API para la página (`window.BDChatbot`).
3. **Panel del negocio y panel de la plataforma.** Configuración del asistente, dominios, equipo,
   métricas, vista previa del widget y auditoría por negocio y global.
4. **Conector de catálogo.** Responde precio y stock reales desde la API de productos del negocio; nunca
   los inventa.
5. **Integración con la tienda demo de Black Dog Store.** El botón «Asistente» de la tienda abre el
   widget dentro de la página.
6. **Análisis de calidad con SonarCloud** en cada PR.

## 5. Guía de demostración, paso a paso

### 5.1 Preparación (5 minutos antes)

1. Abrir en el navegador, en este orden, y esperar a que cada uno cargue:
   1. `https://chatbot-blackdogstore-cloud.onrender.com/api/health/` hasta ver `"status":"ok"`.
   2. `https://blackdog-chatbot-frontend.onrender.com/login`.
   3. `https://blackdog-store-demo-api.onrender.com/api/categories/`.
   4. `https://blackdog-store-demo.onrender.com`.
2. Tener a mano las cuentas de administrador, asesor y superadministrador. Las contraseñas no están en
   este documento.
3. Para la parte local (carga y resiliencia), tener Docker Compose levantado: `docker compose up -d`.

### 5.2 Recorrido

| Paso | Qué hacer | Qué se debe ver | Criterio que demuestra |
|---|---|---|---|
| 1 | Abrir `/api/health/` | `database ok`, `chatbot ok` | Entorno cloud y BD conectada |
| 2 | Abrir `/registro` y luego `/login` | Dos pantallas distintas | Registro y login |
| 3 | Login con un correo y una contraseña incorrectos | «Correo o contraseña incorrectos.» | Control de respuestas, ingreso con correo |
| 4 | Entrar a `/panel` sin sesión | Redirige a `/login` | Rutas protegidas |
| 5 | Abrir una ruta inexistente (`/no-existe`) | Página 404 propia | Vista de página inexistente |
| 6 | Iniciar sesión como administrador → «Preguntas frecuentes» | Lista paginada; crear, editar y desactivar una FAQ | CRUD y paginación |
| 7 | Panel → «Configuración del chatbot» y «Dominios» | Bienvenida, horario, contacto; dominio de la tienda autorizado | Multiempresa, CORS por negocio |
| 8 | Abrir la tienda demo y pulsar «Asistente» | El chat se abre dentro de la tienda | Proyecto funcional, widget |
| 9 | Preguntar: «¿dónde están ubicados?», «¿tiene garantía el iPhone?», «se me mojó el celular» | Respuestas de las FAQ reales | FAQ por categoría |
| 10 | Preguntar «iPhone 13» | Modelos con precio y stock del catálogo | Catálogo sin inventar datos |
| 11 | Escribir «quiero hablar con un asesor» | El chat avisa que un asesor responderá | Derivación |
| 12 | Iniciar sesión como asesor → `/asesor` | La conversación derivada; responderla y ver la respuesta en el widget | Varios tipos de usuario |
| 13 | Iniciar sesión como superadministrador → `/plataforma` y `/plataforma/auditoria` | Negocios registrados y auditoría global | Autorización por rol |
| 14 | Mostrar `PRUEBAS.md` §12 y los gráficos | 50 000 solicitudes con 0 fallos; antes y después | Carga y cuellos de botella |
| 15 | Mostrar `evidencias/resiliencia_20261110-150446.log` | 7 escenarios, 0 fallas | Errores esperados y caídas |
| 16 | Mostrar GitHub → Actions y el último despliegue en Render | CI verde y despliegue de `main` | CI/CD |
| 17 | Mostrar `BACKUPS.md` y `MIGRACION_SERVIDOR.md` | Respaldo de Neon verificado y plan de migración | Backups y migración |

### 5.3 Si algo falla durante la demostración

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| La página tarda 20-40 s | Servicio de Render dormido | Esperar; es el arranque del plan gratuito (`PRUEBAS.md` §15-G) |
| «No pudimos cargar el catálogo» en la tienda | Backend de la tienda dormido | Abrir `blackdog-store-demo-api…/api/categories/`, esperar el 200 y recargar (§15-H) |
| «iPhone 13» pasa a un asesor | El catálogo no respondió en 2,5 s | Igual que la fila anterior; la derivación es el comportamiento previsto |
| El botón «Asistente» no aparece | El backend del chatbot está arrancando | El widget reintenta a los 3, 8 y 15 s; esperar sin recargar (§15-G) |

## 6. Limitaciones conocidas

1. Las cargas de 10 000 a 50 000 se hicieron en Docker local. Contra Render se hizo una prueba controlada
   de hasta 5 000 solicitudes (`PRUEBAS.md` §16).
2. En Render, el límite anónimo no se aplicó a peticiones directas: hallazgo de configuración pendiente de
   revisar en el servicio (`PRUEBAS.md` §16.4).
3. RF-10 (archivos adjuntos con Amazon S3) no está implementado; no forma parte de lo evaluado.
4. En Render Free, el rendimiento es menor que en local: 1 proceso de gunicorn y 512 MB de memoria.
5. Extra no implementado: VPC (no disponible en el plan gratuito; ver la evaluación en `DESPLIEGUE.md` §5).
