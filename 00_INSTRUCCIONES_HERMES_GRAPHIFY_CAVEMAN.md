# PROYECTO ACADÉMICO: CHATBOT BLACK DOG STORE CLOUD

**Documento de inicio para Hermes Agent, Claude Code y Codex**  
**Versión:** 1.0 — 12 de octubre de 2026  
**Fuente principal:** `Requerimientos_y_Desarrollo_Chatbot_Black_Dog_Store.docx` (documento del equipo, 8 páginas).

> **PRIMERA ORDEN: SOLO PLANIFICAR.** No generar código ni ejecutar instalaciones, despliegues, migraciones, commits o cambios de configuración sin autorización explícita.

## 1. Contexto y alcance verificable

Es un proyecto académico del curso **Desarrollo de Soluciones en la Nube**. Consiste en un **chatbot empresarial web de Black Dog Store** para responder consultas frecuentes sobre horarios, garantías, servicios y productos, utilizando información administrada y, cuando exista autorización, una API de catálogo. Debe permitir derivar consultas no resueltas a un asesor.

**IMPORTANTE:** es un prototipo académico **aislado** de la web comercial existente de Black Dog Store. No acceder a la base de datos comercial ni modificar la web en producción. Utilizar datos ficticios y pruebas en entornos controlados.

**Alcance inicial:** chatbot basado en reglas y FAQ administrables. La inteligencia artificial generativa y las integraciones con WhatsApp, Instagram y TikTok quedan fuera del alcance inicial.

**Equipo:** Villar Collantes, Alexis; Morales Puma, Gisela; Kana Huillcapacco, Cesar; Ochoa Chama, Briggith.

## 2. Requisitos funcionales (RF-01 al RF-12)

| ID | Requisito |
|---|---|
| RF-01 | Registro de usuarios con validaciones. |
| RF-02 | Inicio y cierre de sesión seguros. |
| RF-03 | Interfaz de chat web. |
| RF-04 | Preguntas frecuentes por categoría, con contenido administrado. |
| RF-05 | Historial de conversaciones según permisos. |
| RF-06 | Consultas al catálogo solo mediante API autorizada; no inventar precios ni stock. |
| RF-07 | Panel administrativo y CRUD de preguntas frecuentes. |
| RF-08 | Roles de cliente, asesor y administrador. |
| RF-09 | Derivación de consultas no resueltas a un asesor. |
| RF-10 | Gestión de archivos permitidos con Amazon S3. |
| RF-11 | Pantallas 404, en desarrollo y manejo de errores del servidor. |
| RF-12 | Auditoría de accesos y operaciones relevantes. |

**Requisitos no funcionales:** seguridad (hash seguro de contraseñas, HTTPS al publicar, secretos fuera del repositorio), autorización por recurso/endpoint, disponibilidad, rendimiento medible, mantenibilidad, escalabilidad, logs estructurados sin datos sensibles y respaldo/restauración cuando aplique.

## 3. Tecnologías y arquitectura de referencia

- **Next.js:** chat, registro, inicio de sesión y panel administrativo.
- **Django + Django REST Framework:** API, autenticación, autorizaciones y coordinación.
- **Servicio independiente Python / API REST:** reglas, FAQ y derivación de conversaciones.
- **Servicio/adaptador de catálogo:** consulta mediante contrato API autorizado; modo simulado si no existe dicho contrato.
- **PostgreSQL:** usuarios, conversaciones, mensajes, FAQ y auditoría.
- **Docker + Docker Compose:** contenedores separados para pruebas locales.
- **AWS IAM:** usuarios, roles y permisos mínimos sobre recursos académicos.
- **Amazon S3:** documentos y archivos permitidos de prueba.
- **Hospedaje del prototipo:** pendiente de definir según recursos de la asignatura y costos autorizados.

**Flujo general:** cliente → Next.js → API Django → servicio de chatbot → FAQ o catálogo autorizado → respuesta; las conversaciones se conservan en PostgreSQL y los archivos permitidos en S3.

La separación exacta y comunicación de los servicios deben justificarse durante el diseño. Evitar microservicios adicionales sin necesidad. Definir responsabilidad de cada esquema de datos y políticas de acceso.

## 4. Endpoints iniciales de referencia (sujetos a diseño)

- `POST /api/auth/register/` — registro.
- `POST /api/auth/login/` — autenticación.
- `GET /api/users/me/` — perfil autenticado.
- `POST /api/chat/messages/` — enviar consulta.
- `GET /api/chat/conversations/` — historial paginado.
- `GET /api/faqs/` — consultar FAQ.
- `POST /api/faqs/` — crear FAQ con rol autorizado.
- `GET /api/products/search/` — búsqueda autorizada/simulada.

No asumir que estos endpoints existen ya. Son ejemplos del documento de requisitos.

## 5. Modelo inicial de datos

- **Usuario:** id, nombre, correo, hash_contraseña, rol.
- **Conversación:** id, usuario_id, estado, creada_en.
- **Mensaje:** id, conversación_id, emisor, contenido, fecha.
- **PreguntaFrecuente:** id, categoría, pregunta, respuesta, estado.
- **Archivo:** id, clave_s3, nombre, tipo, creado_en.
- **EventoAuditoría:** id, usuario_id, acción, resultado, fecha.

Entregar un diagrama entidad-relación **editable** (no solo una imagen).

## 6. Entregables académicos y prioridades

### Entrega 25 % — semana 9

Entorno AWS preparado; endpoints desarrollados; registro/login diferenciados; rate limits; páginas inexistente/en desarrollo; respuestas HTTP controladas; CRUD estructurado e iniciado; `.env.example` sin secretos; hashes de contraseña; pruebas unitarias y masivas mínimas; PostgreSQL conectado y diagrama ER editable; pruebas de servidor aprox. **50–100** según escenario acordado.

### Entrega 80 % — semana 11

CRUD completo; paginación y latencia; múltiples roles; proyecto en servidor académico; BD completa/diagrama; CORS restringido; pruebas de estabilidad; autenticación, autorización y expiración de tokens; pantallas de fallo; pruebas de servidor aprox. **1.000–5.000**; respaldos cuando correspondan.

### Entrega 100 % — semana 13

Demostración funcional integral; pruebas controladas aprox. **10.000–50.000**; detección y mejora de cuellos de botella; logs estructurados; gestión de errores, caídas e incidencias; documentación y evidencias finales.

**Advertencia:** el documento original no define si los rangos numéricos de las pruebas representan peticiones acumuladas o usuarios concurrentes. Debe aclararse antes de probar. No ejecutar cargas masivas contra la web comercial ni contra infraestructura AWS sin aprobación de costos y límites.

## 7. Asignación propuesta de herramientas / agentes

**Hermes Agent — coordinador:** consolidar requerimientos, construir backlog y fases, registrar decisiones y avances. No afirmar comunicación entre agentes hasta verificarla.

**Codex — arquitecto/revisor:** estudiar diseño, relaciones entre servicios, esquemas de datos, contratos API, amenazas, calidad y criterios de aceptación.

**Claude Code — implementador:** desarrollar módulos **solo después de aprobar el plan**, añadir pruebas y documentación; cambios en repositorio aislado.

**Graphify — análisis de código:** verificar disponibilidad de skill/CLI; si **no hay código**, proponer arquitectura conceptual sin afirmar que existe un grafo; cuando haya código, analizar dependencias del repositorio y documentar hallazgos. La presencia de `graphify-mcp` o de una skill no confirma por sí sola la conexión MCP operativa.

**Caveman — eficiencia de contexto:** comprobar skill/plugin; reducir repeticiones y salidas verbosas, mantener resúmenes de estado, leer solo lo necesario y reportar ahorro **solo si hay medición real**. No omitir fallos, hallazgos de seguridad, diffs críticos ni pruebas.

**Skills:** inventariar las disponibles; elegir solo las necesarias. No instalar ni activar hooks automáticos sin aprobación. Revisar el contenido de las skills por sus permisos de ejecución.

## 8. Política de ejecución y control

1. Trabajar **únicamente** dentro de este directorio académico. No utilizar el repositorio de Black Dog Store Web como proyecto base ni acceder a sus secretos.
2. Si existe código, ejecutar primero auditoría **de solo lectura** de estructura y `git status`; preservar archivos y cambios locales.
3. No instalar dependencias, crear archivos, ejecutar pruebas de carga, usar AWS, introducir credenciales, hacer commits, push o despliegue sin aprobación.
4. Usar valores simulados donde falten contratos comerciales. Indicar claramente lo simulado.
5. Mantener trazabilidad **requisito → módulo → prueba → evidencia**.
6. Preparar documentación de API, despliegue local, diagramas editables y plan de evidencias del curso.
7. Los resultados de análisis deben distinguir: **documentado**, **verificado en el repositorio** y **propuesta**.

## 9. PRIMERA INSTRUCCIÓN PARA HERMES (copiar y enviar)

> Lee este archivo de inicio y, si tu entorno lo permite, el documento `Requerimientos_y_Desarrollo_Chatbot_Black_Dog_Store.docx`. Actúa como coordinador técnico del proyecto académico **Chatbot Black Dog Store Cloud**. Verifica en modo de solo lectura las skills disponibles de Graphify y Caveman y cualquier acceso real a Claude Code y Codex. **No programes ni instales nada todavía.** Entrega: (1) resumen del alcance; (2) matriz RF-01 a RF-12 con módulos y pruebas; (3) arquitectura propuesta y justificación de microservicios; (4) árbol de carpetas; (5) modelo de datos inicial; (6) endpoints y esquema de permisos; (7) backlog para 25 %, 80 % y 100 %; (8) plan de evidencias AWS IAM/S3, Docker y pruebas; (9) riesgos, dudas y costos; (10) propuesta de roles para Hermes/Claude/Codex, Graphify y Caveman. Marca qué aspectos provienen del documento, cuáles están verificados y cuáles son recomendaciones. Usa respuestas concisas, completas y con trazabilidad. Termina solicitando mi aprobación de la arquitectura antes de crear o modificar archivos.

## 10. Cómo utilizar estos archivos

Guardar en el mismo directorio:

```
Chatbot-BlackDogStore-Cloud/
├── 00_INSTRUCCIONES_HERMES_GRAPHIFY_CAVEMAN.md
├── Requerimientos_y_Desarrollo_Chatbot_Black_Dog_Store.docx
└── 01_Guia_Inicio_Chatbot_Black_Dog_Store.docx   (versión de lectura opcional)
```

Abrir Hermes desde la carpeta del proyecto. Pegar el texto de la sección 9, mencionando este archivo por su nombre. Si el agente no puede abrir `.docx`, este `.md` contiene el resumen operativo; para conservar todos los matices académicos, es importante también revisar el documento original.
