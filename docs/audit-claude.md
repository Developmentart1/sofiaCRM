# Auditoría Exhaustiva — CRM-Splash

> **Fecha:** 2026-08-18
> **Alcance:** Todo el código fuente de `backend/src/` (~44 archivos .py, ~2700 LOC) y `frontend/src/` (~6300 LOC). Se excluyeron `.venv`, `node_modules`, `.next`, `_backup_modules`, `.git`.
> **Método:** Lectura exhaustiva de cada archivo, verificación de evidencia línea por línea. Sin modificaciones al código.

---

## 1. Resumen Ejecutivo

CRM-Splash es un proyecto en **estado temprano-funcional** con una base arquitectónica sólida pero con brechas significativas entre lo diseñado y lo implementado.

**Fortalezas:**
- Arquitectura multi-tenant bien diseñada con aislamiento por `ContextVar` y filtrado por `organization_id` en todas las queries de los módulos implementados.
- RBAC granular con 5 roles y 28 permisos definidos en `backend/src/core/rbac.py`.
- Modelo de datos robusto: 17 tablas en la migración inicial con integridad referencial, índices y tipos correctos.
- Ciclo de vida de oportunidades implementado con reglas de negocio (RB-004 a RB-010) en `backend/src/modules/opportunities/service.py`.
- Event bus con patrón outbox para persistencia transaccional en `backend/src/core/event_bus/event_bus.py`.

**Riesgos Críticos:**
1. **Frontend↔Backend desconectado:** El frontend llama a 6+ endpoints que NO existen en el backend (`/api/activities/*`, `/api/tasks/*`, `/api/documents/*`, `/api/reports/*`, `/api/automations/*`). Las páginas de Actividades, Documentos, Reportes y Configuración son stubs vacíos.
2. **RBAC no enforceado en rutas:** `require_permission()` existe pero la mayoría de rutas no lo llaman. Solo 2 de 5 módulos lo usan parcialmente.
3. **Event bus no conectado:** `register_module(app, None)` — el bus siempre es `None`. Los eventos se definen pero nunca se disparan.
4. **Secrets hardcodeados:** `.env` contiene valores de desarrollo (`dev-secret-change-me`) que se usan directamente.
5. **Token en memoria volátil:** El frontend almacena el JWT en una variable JavaScript que se pierde al recargar la página.

**Veredicto:** El proyecto tiene ~40% de funcionalidad real implementada (contacts, opportunities, pipelines, auth). El ~60% restante (activities, tasks, documents, reports, automations) son tablas en BD + definiciones de eventos + frontend UI, pero sin backend service/routes. Apto para demo, NO para producción.

---

## 2. Tabla de Madurez

| Dimensión | Estado | Evidencia Principal | Gap Crítico | Prioridad |
|---|---|---|---|---|
| **Multi-tenant aislamiento** | FUNCIONAL | `core/tenant.py:28-36` — ContextVar + `current_org_id()`. Todos los services filtran por org. | Sin Row-Level Security en BD; depende 100% del código. | P1 |
| **Ciclo de vida oportunidades** | SÓLIDO | `opportunities/service.py:96-130` — transiciones con validación de stage_type, lost_reason, weighted_value. | Sin máquina de estados formal; transiciones se validan solo por stage_type. | P2 |
| **Contactos** | FUNCIONAL | `contacts/service.py:46-86` — CRUD completo con normalización de email/phone. | Sin deduplicación real (solo normalización, no merge automático). Endpoint `/duplicates` definido en frontend pero ausente en backend. | P2 |
| **Actividades y tareas** | AUSENTE | Migración crea tablas `activities` y `tasks` (`migrations/versions/0001_initial.py:214-258`). Frontend tiene UI. | NO hay service, routes ni domain en backend. Frontend llama a endpoints inexistentes. | P0 |
| **Documentos** | AUSENTE | Tabla `documents` en migración (`:260-278`). Frontend tiene UI y API client. | NO hay service, routes ni domain en backend. | P0 |
| **Automatización** | AUSENTE | Tablas `automation_rules`, `automation_actions`, `automation_executions` en migración (`:313-350`). Event models definidos. | NO hay service, routes, ni engine. Event bus no conectado. | P1 |
| **Auth JWT** | FUNCIONAL | `core/security.py:30-51` — JWT con HS256, bcrypt, expiración configurable. | Sin refresh token. Sin revocación. Secrets hardcodeados en `.env`. | P1 |
| **RBAC** | RUDIMENTARIO | `core/rbac.py` — 5 roles, 28 permisos, `require_permission()`. | Solo enforceado en `users/routes.py:43,54` y `organizations/routes.py:31,42`. Contacts, pipelines, opportunities NO lo usan. | P0 |
| **Auditoría** | RUDIMENTARIO | `core/audit.py` — decorator `@audit_log`. | Solo en 4 rutas: `users/routes.py:39,48`, `organizations/routes.py:16,36`. No se usa en contacts/pipelines/opportunities. | P1 |
| **Event bus** | RUDIMENTARIO | `core/event_bus/event_bus.py` — outbox table, dispatch_pending, typed events. | Bus siempre `None` en `register_module(app, None)`. Nunca se publican eventos. | P1 |
| **Migraciones Alembic** | SÓLIDO | `migrations/versions/0001_initial.py` — 17 tablas, FK, índices, unique constraints. | Solo 1 versión. No hay migraciones incrementales. | P2 |
| **Tests** | RUDIMENTARIO | `tests/test_tenant_isolation.py`, `tests/test_business_rules.py` — 7 tests. | Tests usan status ranges (`200, 403`), no assert exacto. No cobertura de contacts, pipelines, auth flows. | P1 |
| **Seed script** | FUNCIONAL | `scripts/seed.py` — 9 usuarios, 13 etapas, 10 empresas, 30 contactos, 20 oportunidades. | Solo 1 org de demo. Sin reset/clean. | P3 |
| **Frontend auth** | RUDIMENTARIO | `lib/hooks/use-auth.ts` — in-memory token, AuthGuard client-side. | Sin middleware Next.js. Token se pierde al recargar. Sin refresh. | P0 |
| **Frontend API real** | RUDIMENTARIO | Contacts, Opportunities, Pipelines, Companies, Dashboard llaman a API real. | Activities, Tasks, Documents, Reports, Settings son stubs. | P0 |
| **CORS** | FUNCIONAL | `main.py:28-33` — regex para localhost. | Hardcodeado a localhost. Sin configuración por env. | P3 |
| **Configuración** | FUNCIONAL | `core/config.py` — pydantic-settings con .env. | Secrets en `.env` con valores de desarrollo. Sin validación de producción. | P1 |

---

## 3. Análisis Detallado por Bloque

### Bloque 1 — Arquitectura y Dominio del CRM

#### 1.1 Modelo de datos multi-tenant

**Implementación real:**
- `core/tenant.py:15` — `ContextVar[str | None]` almacena el `organization_id` del request actual.
- `core/tenant.py:28-36` — `current_org_id()` levanta `OrganizationBoundaryError` si no hay org en contexto.
- `modules/users/auth_deps.py:42` — `set_org(str(org))` se llama en `get_current_user()`, estableciendo el contexto para toda la request.
- Todos los services usan `current_org_id()` para filtrar:
  - `contacts/service.py:23` — `list_companies()`: `Company.organization_id == org`
  - `contacts/service.py:47` — `list_contacts()`: `Contact.organization_id == org`
  - `opportunities/service.py:47-49` — `list_opportunities()`: `Opportunity.organization_id == org`
  - `pipelines/service.py:15-17` — `list_pipelines()`: `Pipeline.organization_id == org`
  - `users/repository.py:17` — `get()`: `User.organization_id == org_id`

**Gap:** No hay Row-Level Security en SQLite. El aislamiento depende 100% de que cada query filtre correctamente. Un query sin filtro sería una brecha de tenant.

**Veredicto:** FUNCIONAL — el patrón es correcto y consistente en todos los módulos implementados.

#### 1.2 Ciclo de vida de oportunidades/pipelines

**Implementación real:**
- `opportunities/service.py:64-83` — `create_opportunity()`: valida que stage pertenezca al pipeline (RB-004), calcula `weighted_value` = `estimated_value * probability / 100`.
- `opportunities/service.py:96-130` — `transition_stage()`: implementa:
  - RB-004: stage debe pertenecer al mismo pipeline (`:105-106`)
  - RB-005: cerrar como perdido requiere `lost_reason_id` (`:116-117`)
  - RB-006: cerrar como ganado registra `closed_at` y `won_value` (`:111-113`)
  - RB-008: actualiza `stage_id`, `entered_stage_at`, `probability`, `weighted_value` (`:123-128`)
- `opportunities/service.py:99` — Solo oportunidades `open` pueden cambiar de etapa.
- `opportunities/service.py:132-136` — `delete_opportunity()` es soft-delete (`deleted_at` + status `discarded`).

**Modelo de datos:**
- `opportunities/domain.py` — 22 columnas incluyendo `status`, `stage_id`, `pipeline_id`, `probability`, `weighted_value`, `won_value`, `lost_reason_id`, `entered_stage_at`.
- `pipelines/domain.py:25-42` — `Stage` con `stage_type` (open/won/lost), `probability`, `maximum_days`, `entry_requirements`, `exit_requirements`.

**Gap:** No hay validación de transiciones secuenciales (solo valida stage_type, no si el movimiento es "hacia adelante" o "hacia atrás"). No hay enforcement de `maximum_days`. `entry_requirements` y `exit_requirements` son campos de texto sin lógica asociada.

**Veredicto:** SÓLIDO — las reglas de negocio core están implementadas correctamente.

#### 1.3 Contactos

**Implementación real:**
- `contacts/service.py:61-72` — `create_contact()`: normaliza `email` a lowercase+strip y `phone` eliminando espacios.
- `contacts/domain.py:33-62` — Modelo con 22 columnas incluyendo `email_normalized`, `phone_normalized`, `type` (PF/PM), `rfc`, `tags`, `assigned_user_id`.
- CRUD completo: list, get, create, update, delete (soft-delete).

**Gaps:**
- **Sin deduplicación real:** El frontend define `contactsApi.checkDuplicates()` (`frontend/src/lib/api/contacts.ts:45-47`) pero el backend NO tiene ese endpoint. La normalización existe pero no hay merge automático.
- **Sin importación CSV en backend:** El frontend define `contactsApi.importCsv()` (`:48-60`) pero no hay endpoint `/api/contacts/import` en el backend.
- **Sin paginación real:** `list_contacts()` devuelve TODOS los contactos sin paginación, a pesar de que `core/pagination.py` existe con `PageParams` y `Page`.

**Veredicto:** FUNCIONAL para CRUD básico. Sin deduplicación ni importación.

#### 1.4 Actividades y tareas

**Evidencia de ausencia:**
- NO hay archivos en `backend/src/modules/` para activities ni tasks.
- La migración crea las tablas `activities` (`migrations/versions/0001_initial.py:214-233`) y `tasks` (`:236-258`) con todas las columnas.
- Los event models están definidos en `core/event_bus/models.py:128-157` (`TaskCreated`, `TaskCompleted`, `TaskOverdue`, `ActivityCreated`).
- El frontend tiene UI para tasks (`frontend/src/app/(authed)/tasks/page.tsx`) pero activities es stub.
- El frontend llama a endpoints que NO existen en backend: `GET /api/tasks`, `PATCH /api/tasks/:id`, `GET /api/activities`, `GET /api/activities/recent`, `GET /api/tasks/upcoming`.

**Veredicto:** AUSENTE en backend. Tablas y UI existen pero sin service/routes.

#### 1.5 Documentos y reportes

**Evidencia de ausencia:**
- Tabla `documents` en migración (`:260-278`) con `filename`, `safe_name`, `mime_type`, `size_bytes`, `storage_path`.
- `core/security.py:62-77` — `sign_storage_url()` y `verify_storage_url()` implementados para URLs firmadas.
- Frontend tiene stubs vacíos para documents y reports.
- Frontend llama a endpoints inexistentes: `GET /api/documents`, `POST /api/documents`, `GET /api/reports/kpis`, `GET /api/opportunities/stuck`.

**Veredicto:** AUSENTE en backend. Infraestructura de storage URLs lista pero sin implementación.

#### 1.6 Automatización

**Evidencia de ausencia:**
- Tablas en migración: `automation_rules` (`:314-326`), `automation_actions` (`:329-336`), `automation_executions` (`:339-350`).
- `core/rbac.py:69-70` — Permisos `AUTOMATION_READ` y `AUTOMATION_MANAGE` definidos.
- 19 tipos de eventos definidos en `core/event_bus/models.py` con discriminated union.
- Frontend define `automationsApi` con CRUD completo.
- NO hay módulo en `backend/src/modules/` para automations.
- El event bus nunca se conecta (`register_module(app, None)` en todos los módulos).

**Veredicto:** AUSENTE. Solo tablas y definiciones de tipos.

---

### Bloque 2 — Core Platform

#### 2.1 Auth: JWT, hashing, expiración, refresh

**Implementación real:**
- `core/security.py:14` — `CryptContext(schemes=["bcrypt"])` para hashing de contraseñas.
- `core/security.py:18-20` — `hash_password()` y `verify_password()` con bcrypt.
- `core/security.py:30-51` — `create_access_token()` genera JWT con claims: `sub` (user_id), `org` (organization_id), `role`, `exp`, `iat`.
- `core/security.py:54-59` — `decode_access_token()` valida y decodifica, levanta `UnauthorizedError` en fallo.
- `modules/users/service.py:67-91` — `login()`: busca org por slug, usuario por email_normalizado, verifica password, genera token.
- `modules/users/auth_deps.py:32-49` — `get_current_user()`: extraeBearer token, decodifica, establece `set_org()`, devuelve `CurrentUser` dataclass.
- `core/config.py:27` — `jwt_expire_minutes: int = 1440` (24 horas).

**Gaps críticos:**
- **Sin refresh token:** Una vez expirado el JWT, el usuario debe re-login. No hay endpoint `/refresh`.
- **Sin revocación:** No hay blacklist de tokens. Un token válido hasta que expire.
- **Secrets hardcodeados:** `backend/.env:8-9` contiene `SECRET_KEY=change-me-in-production-please-use-secrets-token-urlsafe` y `JWT_SECRET=another-secret-for-jwt-tokens-change-me-too`. Estos son los valores reales usados.
- **Sin email en JWT:** `create_access_token()` no incluye `email` ni `name` en el payload, pero `get_current_user()` lee `payload.get("email", "")` y `payload.get("name", "")` — siempre serán strings vacíos.
- **Token en memoria volátil en frontend:** `frontend/src/lib/api/auth.ts:9` — `let _token: string | null = null`. Se pierde al recargar la página. No hay `localStorage` ni cookies.

**Veredicto:** FUNCIONAL para flujo básico. Sin refresh, sin revocación, secrets débiles.

#### 2.2 RBAC: roles, permisos, enforcement

**Implementación real:**
- `core/rbac.py:15-20` — 5 roles: `admin`, `director`, `gerente`, `asesor`, `operaciones`.
- `core/rbac.py:23-74` — 28 permisos agrupados por módulo (org, user, pipeline, contact, opportunity, activity, document, audit, automation, dashboard).
- `core/rbac.py:76-161` — `ROLE_PERMISSIONS` mapea cada rol a sus permisos. Admin tiene todos.
- `core/rbac.py:173-179` — `require_permission()` levanta `ForbiddenError` si el rol no tiene el permiso.

**Enforcement real en rutas:**
- `modules/users/routes.py:43` — `require_permission(current.role, Permission.USER_LIST)` en `list_users`. **NOTA:** `USER_LIST` no existe en la enum `Permission` — debería ser `USER_READ`. Esto causaría un error en runtime.
- `modules/users/routes.py:54` — `require_permission(current.role, Permission.USER_CREATE)` en `create_user`.
- `modules/organizations/routes.py:31` — `require_permission(current.role, Permission.ORG_READ)` en `get_my_organization`.
- `modules/organizations/routes.py:42` — `require_permission(current.role, Permission.ORG_UPDATE)` en `update_my_organization`.

**Rutas SIN enforcement de RBAC:**
- `modules/contacts/routes.py` — TODAS las rutas (list, get, create, update, delete) NO llaman a `require_permission()`. Cualquier usuario autenticado puede hacer cualquier operación.
- `modules/opportunities/routes.py` — TODAS las rutas (list, get, create, update, transition, delete) NO llaman a `require_permission()`.
- `modules/pipelines/routes.py` — TODAS las rutas (list, get, create, list_stages, create_stage) NO llaman a `require_permission()`.

**Veredicto:** RUDIMENTARIO — la infraestructura existe pero solo se enforcea en 2 de 5 módulos. Contacts, opportunities y pipelines son accesibles sin restricción de rol.

#### 2.3 Auditoría

**Implementación real:**
- `core/audit.py:16-78` — Decorator `@audit_log(action, entity_type)` que:
  - Ejecuta la función original primero (`:24`).
  - Extrae `db` y `current` de kwargs (`:27-28`).
  - Inserta fila en `audit_logs` con id, org_id, user_id, action, entity_type, entity_id, created_at (`:54-68`).
  - Usa `db.commit()` separado (`:69`).

**Uso real:**
- `modules/organizations/routes.py:16` — `@audit_log("org.bootstrap", entity_type="organization")`
- `modules/organizations/routes.py:36` — `@audit_log("org.update", entity_type="organization")`
- `modules/users/routes.py:39` — `@audit_log("user.list")`
- `modules/users/routes.py:48` — `@audit_log("user.create")`

**Rutas SIN auditoría:**
- Todas las rutas de contacts, opportunities, pipelines no tienen `@audit_log`.
- Login no se audita.
- Cambios de contraseña no se auditan.

**Problema técnico:** El decorator hace `db.commit()` después de la función original (`:69`), pero la función ya hizo su propio `commit()` en el service. Esto significa un segundo commit que podría fallar si la sesión ya está cerrada.

**Veredicto:** RUDIMENTARIO — existe pero solo en 4 rutas de 15+ disponibles.

#### 2.4 Event bus

**Implementación real:**
- `core/event_bus/event_bus.py:30-42` — Tabla `EventOutbox` con columnas: id, organization_id, event_type, payload_json, created_at, dispatched_at, attempts, last_error.
- `core/event_bus/event_bus.py:50-114` — `SyncEventBus` con:
  - `subscribe()` / `subscribe_event()` para registrar handlers.
  - `publish()` persiste evento en outbox dentro de la transacción del caller.
  - `dispatch_pending()` entrega eventos no despachados a subscribers, con reintentos.
- `core/event_bus/models.py` — 19 tipos de eventos con Pydantic discriminated union.

**Problema:** El bus NUNCA se conecta. En `main.py:39-49`:
```python
register_orgs(app, None)    # bus=None
register_users(app, None)   # bus=None
register_contacts(app, None) # bus=None
register_pipelines(app, None) # bus=None
register_opportunities(app, None) # bus=None
```
Los módulos reciben `bus=None` y nunca publican eventos. `configure_bus()` nunca se llama.

**Veredicto:** RUDIMENTARIO — infraestructura completa pero desconectada. Los eventos se definen pero nunca se disparan.

#### 2.5 Manejo de errores y validación

**Implementación real:**
- `core/errors.py` — Jerarquía de errores tipados:
  - `CRMError` (base, 500)
  - `UnauthorizedError` (401)
  - `ForbiddenError` (403)
  - `NotFoundError` (404)
  - `ConflictError` (409)
  - `ValidationError` (422)
  - `StageTransitionError` (422)
  - `MissingRequiredFieldError` (422)
  - `OrganizationBoundaryError` (403)
- `main.py:52-77` — Exception handlers globales para `CRMError`, `RequestValidationError`, `IntegrityError`, y `Exception` genérico.
- Schemas Pydantic con validación: `Field(min_length=1, max_length=300)`, `pattern`, `ge=0`, `le=100`.

**Gap:** El handler de `IntegrityError` (`:66-72`) no revela qué constraint falló — solo dice "constraint violated". Esto dificulta el debugging.

**Veredicto:** SÓLIDO — buena jerarquía de errores, validación en schemas, handlers globales.

#### 2.6 Configuración y secrets

**Implementación real:**
- `core/config.py:10-57` — `Settings` con pydantic-settings, carga de `.env`.
- Campos: `database_url`, `secret_key`, `jwt_secret`, `jwt_algorithm`, `jwt_expire_minutes`, `storage_root`, `cors_origins`, `rate_limit_per_minute`, `log_level`, `env`.

**Problemas:**
- `backend/.env:8` — `SECRET_KEY=change-me-in-production-please-use-secrets-token-urlsafe` — valor de desarrollo usado directamente.
- `backend/.env:9` — `JWT_SECRET=another-secret-for-jwt-tokens-change-me-too` — valor de desarrollo.
- `backend/.env:6` — `DATABASE_URL=sqlite:///./crm_splash.db` — SQLite para desarrollo, sin validación de producción.
- `core/config.py:24` — `secret_key` tiene default `"dev-secret-change-me"`. Si `.env` no existe, se usa este valor.
- `rate_limit_per_minute: int = 120` — definido pero NO implementado en ninguna parte. No hay middleware de rate limiting.

**Veredicto:** FUNCIONAL para desarrollo. Secrets débiles, rate limit no implementado.

#### 2.7 CORS y superficie de seguridad

**Implementación real:**
- `main.py:28-33` — CORS con `allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?"`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- `core/config.py:34` — `cors_origins: str = "http://localhost:3000"` — no se usa, el regex está hardcodeado.

**Problemas:**
- `allow_methods=["*"]` y `allow_headers=["*"]` — demasiado permisivo para producción.
- `allow_credentials=True` con wildcard origins es una vulnerabilidad conocida.
- El regex de CORS está hardcodeado en `main.py`, no se lee de configuración.
- No hay middleware de rate limiting.
- No hay headers de seguridad (HSTS, CSP, X-Frame-Options).

**Veredicto:** FUNCIONAL para desarrollo local. Inseguro para producción.

---

### Bloque 3 — Capa de Datos

#### 3.1 Migraciones Alembic

**Implementación real:**
- `backend/alembic.ini` — configuración estándar de Alembic.
- `backend/migrations/env.py` — entorno de migración.
- `backend/migrations/versions/0001_initial.py` — migración única que crea 17 tablas:
  - `organizations`, `users`, `companies`, `contacts`, `lead_sources`
  - `pipelines`, `pipeline_stages`, `opportunities`, `lost_reasons`
  - `activities`, `tasks`, `documents`
  - `audit_logs`, `event_outbox`
  - `automation_rules`, `automation_actions`, `automation_executions`
  - `custom_field_definitions`, `custom_field_values`
  - `notifications`

**Coherencia con modelos ORM:**
- Los modelos ORM en `domain.py` de cada módulo coinciden con las columnas de la migración.
- Ejemplo: `contacts/domain.py:33-62` tiene las mismas 22 columnas que `migrations/versions/0001_initial.py:79-108`.
- Ejemplo: `opportunities/domain.py:13-41` tiene las mismas 22 columnas que la migración.

**Índices creados:**
- `ix_organizations_slug` (unique)
- `ix_users_organization_id`, `ix_users_email_normalized`, `ix_user_org_role`
- `ix_companies_organization_id`
- `ix_contacts_organization_id`, `ix_contacts_company_id`, `ix_contacts_email_normalized`, `ix_contacts_phone_normalized`, `ix_contacts_assigned_user_id`
- `ix_opportunities_*` — 7 índices (organization_id, contact_id, company_id, pipeline_id, stage_id, assigned_user_id, status)
- `ix_pipeline_stages_organization_id`, `ix_pipeline_stages_pipeline_id`
- `ix_activities_*` — 4 índices
- `ix_tasks_*` — 5 índices
- `ix_documents_*` — 2 índices
- `ix_audit_logs_*` — 3 índices
- `ix_event_outbox_*` — 2 índices

**Gaps:**
- Solo 1 migración (la inicial). No hay migraciones incrementales para cambios posteriores.
- Tablas como `automation_rules`, `custom_field_definitions`, `notifications` se crean pero nunca se usan en el código.

**Veredicto:** SÓLIDO — migración completa, bien indexada, coherente con modelos.

#### 3.2 Integridad referencial, índices, tipos

**Integridad referencial:**
- Todas las FK tienen `ondelete` definido:
  - `CASCADE` en `organization_id` (borrar org borra todo).
  - `SET NULL` en `contact_id`, `company_id`, `assigned_user_id` (borrar referenciado no borra el padre).
  - `RESTRICT` en `pipeline_id` y `stage_id` de opportunities (no se puede borrar pipeline/stage con oportunidades).
- `UniqueConstraint("organization_id", "email_normalized", name="uq_user_org_email")` en `users/domain.py:46`.
- `UniqueConstraint` en `custom_field_values` por `(definition_id, entity_id)`.

**Tipos de datos:**
- IDs: `String(36)` para UUIDs (no nativo UUID de BD, pero compatible con SQLite).
- Monedas: `Numeric(18, 4)` para valores financieros — correcto para precisión decimal.
- Fechas: `DateTime` con timezone-aware (`datetime.now(UTC)`).
- Texto libre: `Text` para notes, description, body.

**Gap:** `opportunities/domain.py:33` — `lost_reason_id` es `String(36)` sin FK a `lost_reasons`. La migración tampoco crea la FK. Esto permite IDs de motivos de pérdida inválidos.

**Veredicto:** SÓLIDO — integridad referencial bien diseñada, tipos apropiados.

#### 3.3 Seed script

**Implementación real:**
- `scripts/seed.py` — crea datos de demo completos:
  - 1 organización (`crm-splash-demo`)
  - 9 usuarios con roles variados (admin, director, gerente, 3 asesores, operaciones, finanzas, cumplimiento)
  - 5 fuentes de lead
  - 5 motivos de pérdida
  - 1 pipeline con 13 etapas (prospección → cerrado ganado/perdido/descartado/standby)
  - 10 empresas
  - 30 contactos
  - 20 oportunidades (5 ganadas, 3 perdidas, 12 abiertas)
  - Password para todos: `Demo1234!`

**Gaps:**
- Solo crea 1 organización. No hay forma de resetear sin borrar el archivo `.db`.
- No crea actividades, tareas ni documentos (tablas vacías).
- Usa raw SQL directo, no los ORM models.

**Veredicto:** FUNCIONAL para demo. Sin reset ni datos de actividades/tasks.

#### 3.4 Tests

**Implementación real:**
- `tests/test_tenant_isolation.py` — 5 tests:
  - `test_user_can_see_own_contacts` — verifica que usuario puede ver contactos de su org.
  - `test_unauthorized_without_token` — verifica 401 sin token.
  - `test_invalid_token_rejected` — verifica 401 con token inválido.
  - `test_health_check` — verifica endpoint `/api/health`.
  - `test_login_works` — verifica login (con assertion laxa: `status_code in (200, 400, 404, 422)`).

- `tests/test_business_rules.py` — 2 tests:
  - `test_create_opportunity_succeeds` — crea oportunidad y verifica status/probability/weighted_value.
  - `test_close_lost_requires_reason` — verifica que cerrar como perdido requiere `lost_reason_id`.

**Problemas con los tests:**
- **Assertions laxas:** `test_user_can_see_own_contacts` acepta `status_code in (200, 403)` — no verifica cuál es correcto.
- **Tests dependen de BD real:** Usan `SessionLocal()` directo, no fixtures aisladas. Comparten la misma BD SQLite.
- **Path manipulation:** `sys.path.insert(0, str(SRC))` — fragile, podría romper con cambios de estructura.
- **Sin cobertura de:** contacts CRUD, pipelines CRUD, RBAC enforcement, audit log, event bus, error handling.
- **Tests podrían no correr:** `test_login_works` usa un slug que no existe en la BD de test.

**Veredicto:** RUDIMENTARIO — 7 tests con assertions laxas. Cobertura baja.

---

### Bloque 4 — Frontend

#### 4.1 Páginas que consumen API real vs mock/hardcodeadas

**Páginas con API real (conectan a backend):**

| Página | Archivo | Endpoints llamados | Estado |
|---|---|---|---|
| Login | `app/login/page.tsx` | `POST /api/users/login` | ✅ Funcional |
| Signup | `app/signup/page.tsx` | `POST /api/organizations/bootstrap` | ✅ Funcional |
| Dashboard | `app/(authed)/dashboard/page.tsx` | `GET /api/reports/kpis`, `GET /api/activities/recent`, `GET /api/tasks/upcoming`, `GET /api/opportunities/stuck`, `GET /api/reports/performance` | ⚠️ Llama a endpoints inexistentes |
| Contacts | `app/(authed)/contacts/page.tsx` | `GET /api/contacts` | ✅ Funcional |
| Contact Detail | `app/(authed)/contacts/[id]/page.tsx` | `GET /api/contacts/:id` | ✅ Funcional |
| New Contact | `app/(authed)/contacts/new/page.tsx` | `POST /api/contacts` | ✅ Funcional |
| Import Contacts | `app/(authed)/contacts/import/page.tsx` | `POST /api/contacts/import` | ⚠️ Endpoint no existe |
| Opportunities | `app/(authed)/opportunities/page.tsx` | `GET /api/opportunities`, `GET /api/pipelines`, `GET /api/pipelines/:id` | ✅ Funcional |
| Pipelines | `app/(authed)/pipelines/page.tsx` | `GET /api/pipelines` | ✅ Funcional |
| Companies | `app/(authed)/companies/page.tsx` | `GET /api/companies` | ⚠️ Endpoint no existe (ruta es `/api/contacts/companies`) |
| Tasks | `app/(authed)/tasks/page.tsx` | `GET /api/tasks` | ❌ Endpoint no existe |

**Páginas stub (solo UI, sin funcionalidad):**

| Página | Archivo | Contenido |
|---|---|---|
| Activities | `app/(authed)/activities/page.tsx` | Solo `<h1>Actividades</h1>` — 2 líneas |
| Documents | `app/(authed)/documents/page.tsx` | Solo `<h1>Documentos</h1>` — 2 líneas |
| Reports | `app/(authed)/reports/page.tsx` | Solo `<h1>Reportes</h1>` — 2 líneas |
| Settings | `app/(authed)/settings/page.tsx` | Solo `<h1>Configuración</h1>` — 2 líneas |

**Datos hardcodeados en dashboard:**
- `app/(authed)/dashboard/page.tsx:27-40` — `trendData` y `pipelineData` son arrays generados con `Math.random()` y datos estáticos. Los gráficos de "Actividad del pipeline" y "Oportunidades por etapa" muestran datos fake, no reales.

#### 4.2 Manejo de auth en el cliente

**Implementación real:**
- `lib/api/auth.ts:9` — Token almacenado en variable JavaScript en memoria: `let _token: string | null = null`.
- `lib/api/auth.ts:11-13` — `getToken()` / `setToken()` para acceder al token.
- `lib/api/client.ts:81` — `apiFetch()` inyecta `Authorization: Bearer ${getToken()}` en cada request.
- `lib/hooks/use-auth.ts` — Hook `useAuth()` con:
  - Estado global en memoria (`memoryState`, `listeners`).
  - `login()` llama a `authApi.login()`, guarda token.
  - `signup()` llama a `authApi.signup()`, guarda token.
  - `logout()` limpia token.
  - `refresh()` llama a `authApi.me()` para verificar token.
- `components/layout/auth-guard.tsx` — `AuthGuard` componente que redirige a `/login` si no autenticado.
- `app/(authed)/layout.tsx` — Todas las páginas authed están envueltas en `<AuthGuard>`.

**Problemas críticos:**
1. **Token se pierde al recargar:** Almacenado solo en memoria JavaScript. F5 = logout.
2. **Sin middleware Next.js:** No hay `middleware.ts` en `frontend/`. La protección es solo client-side (AuthGuard). Las páginas se renderizan brevemente antes de la redirección.
3. **Sin refresh token:** No hay mecanismo para renovar el token antes de expirar.
4. **Login hardcodea organization_slug:** `lib/api/auth.ts:29` — `organization_slug: "crm-splash-demo"` hardcodeado en el login. El usuario no puede elegir su organización.
5. **Signup no envía token automáticamente:** `auth.ts:36-38` — `signup()` hace `POST /api/organizations/bootstrap` pero el backend devuelve `OrganizationRead`, no `LoginResponse` con token. El frontend asume que la respuesta tiene `access_token`, pero el schema `OrganizationRead` no lo incluye.

#### 4.3 Consistencia frontend↔backend

**Desconexiones críticas:**

| Frontend espera | Backend tiene | Problema |
|---|---|---|
| `GET /api/contacts` | `GET /api/v1/contacts` | **Prefijo diferente:** frontend usa `/api/`, backend usa `/api/v1/` |
| `GET /api/tasks` | ❌ No existe | Módulo no implementado |
| `GET /api/activities` | ❌ No existe | Módulo no implementado |
| `GET /api/documents` | ❌ No existe | Módulo no implementado |
| `GET /api/reports/kpis` | ❌ No existe | Módulo no implementado |
| `GET /api/automations` | ❌ No existe | Módulo no implementado |
| `GET /api/companies` | `GET /api/v1/contacts/companies` | Ruta diferente |
| `GET /api/contacts/:id/activities` | ❌ No existe | Sub-recurso no implementado |
| `GET /api/contacts/:id/tasks` | ❌ No existe | Sub-recurso no implementado |
| `GET /api/contacts/:id/documents` | ❌ No existe | Sub-recurso no implementado |
| `GET /api/contacts/:id/audit` | ❌ No existe | Sub-recurso no implementado |
| `GET /api/contacts/duplicates` | ❌ No existe | Endpoint no implementado |
| `POST /api/contacts/import` | ❌ No existe | Endpoint no implementado |
| `GET /api/opportunities/:id/activities` | ❌ No existe | Sub-recurso no implementado |
| `PATCH /api/opportunities/:id/position` | ❌ No existe | Endpoint no implementado |
| `PATCH /api/pipelines/stages/:id` | ❌ No existe | Endpoint no implementado |
| `DELETE /api/pipelines/stages/:id` | ❌ No existe | Endpoint no implementado |
| `PATCH /api/pipelines/:id/stages/reorder` | ❌ No existe | Endpoint no implementado |

**Problema de prefijo:** El backend registra rutas con `prefix="/api/v1"` (`contacts/__init__.py:7`), pero el frontend llama a `/api/` sin el `v1`. Esto significa que NINGUNA llamada del frontend al backend funcionaría sin un proxy de reescritura de URL.

**Diferencias de schema:**
- Frontend `User.role` es `"admin" | "manager" | "member" | "viewer"` (`lib/types/api.ts:21`).
- Backend `Role` es `"admin" | "director" | "gerente" | "asesor" | "operaciones"` (`core/rbac.py:15-20`).
- Los roles no coinciden. `manager` no existe en backend, `director` no existe en frontend.

- Frontend `StageTransition` tiene `to_stage_id`, `notes`, `lost_reason`, `close_as_won`, `close_as_lost` (`lib/types/api.ts:228-234`).
- Backend `StageTransition` tiene `stage_id`, `lost_reason_id`, `lost_notes` (`opportunities/schemas.py:35-39`).
- Los campos no coinciden (`to_stage_id` vs `stage_id`, `lost_reason` vs `lost_reason_id`).

- Frontend `OpportunityCreate` tiene `amount` (`lib/types/api.ts:199`).
- Backend `OpportunityCreate` tiene `estimated_value` (`opportunities/schemas.py:16`).
- El campo no coincide.

**Veredicto:** RUDIMENTARIO — hay UI completa pero con desconexiones graves entre frontend y backend. El prefijo de URL, los schemas de tipos y los endpoints no coinciden.

---

## 4. Riesgos Críticos

### Riesgos de Seguridad (P0)

| # | Riesgo | Evidencia | Impacto | Remediación |
|---|---|---|---|---|
| S1 | **Secrets de desarrollo en `.env`** | `backend/.env:8-9` — `SECRET_KEY=change-me-in-production...`, `JWT_SECRET=another-secret...` | Cualquiera puede forjar JWTs válidos | Generar secrets aleatorios con `secrets.token_urlsafe(64)` y NO commitear `.env` |
| S2 | **RBAC no enforceado en 3 de 5 módulos** | `contacts/routes.py`, `opportunities/routes.py`, `pipelines/routes.py` no llaman `require_permission()` | Cualquier usuario autenticado puede crear/editar/eliminar contactos, oportunidades y pipelines | Agregar `require_permission()` en todas las rutas |
| S3 | **Token JWT sin refresh ni revocación** | `core/security.py` — no hay blacklist ni endpoint de refresh | Un token robado es válido hasta expire (24h). No hay forma de invalidarlo | Implementar refresh tokens y blacklist (o usar Redis) |
| S4 | **CORS demasiado permisivo** | `main.py:28-33` — `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True` | Habilita ataques CSRF cross-origin | Configurar origins, methods y headers específicos |
| S5 | **Sin rate limiting** | `core/config.py:37` — `rate_limit_per_minute` definido pero no implementado | Vulnerable a brute-force en login | Agregar middleware de rate limiting (slowapi o similar) |
| S6 | **Token en memoria volátil en frontend** | `frontend/src/lib/api/auth.ts:9` — `let _token` | Token se pierde al recargar. Sin protección real de sesión | Usar httpOnly cookies o localStorage con refresh |

### Riesgos de Integridad (P1)

| # | Riesgo | Evidencia | Impacto | Remediación |
|---|---|---|---|---|
| I1 | **Event bus desconectado** | `main.py:39-49` — `register_module(app, None)` en todos los módulos | Los eventos se definen pero nunca se disparan. No hay automatización | Conectar el bus y llamar `bus.publish()` en los services |
| I2 | **lost_reason_id sin FK** | `opportunities/domain.py:33` — `String(36)` sin ForeignKey | Permite IDs de motivos de pérdida inválidos | Agregar FK a `lost_reasons` |
| I3 | **Prefijo de URL desalineado** | Backend usa `/api/v1/`, frontend usa `/api/` | Ninguna llamada del frontend funciona sin proxy | Alinear prefijos o agregar reescritura |
| I4 | **Schemas de tipos desalineados** | Frontend: `manager/member/viewer`, Backend: `director/gerente/asesor/operaciones` | Roles no coinciden, campos de schemas diferentes | Sincronizar tipos entre frontend y backend |
| I5 | **Signup no devuelve token** | Backend `bootstrap` devuelve `OrganizationRead`, frontend espera `LoginResponse` con `access_token` | Signup falla en el frontend | Modificar bootstrap para devolver token o hacer login automático post-signup |

### Riesgos Operacionales (P2)

| # | Riesgo | Evidencia | Impacto |
|---|---|---|---|
| O1 | Sin paginación en queries | `list_contacts()`, `list_opportunities()` devuelven TODOS los registros | Problema de performance con miles de registros |
| O2 | Sin migraciones incrementales | Solo 1 migración (`0001_initial`) | Cualquier cambio de schema requiere recrear la BD |
| O3 | Tests con assertions laxas | `status_code in (200, 403)` — no verifica cuál es correcto | Tests pasan incluso con bugs |
| O4 | Sin logging estructurado | `logging.basicConfig(level=...)` — solo texto plano | Dificulta debugging en producción |
| O5 | CORS hardcodeado | Regex en `main.py:29` no se lee de configuración | Requiere cambio de código para desplegar |

---

## 5. Roadmap Recomendado

### Fase 1 — Fundación (P0, ~2 semanas)

**Objetivo:** El sistema debe ser seguro y funcional de extremo a extremo.

1. **Corregir secrets** — Generar secrets aleatorios, mover `.env` a `.env.example` con placeholders, agregar `.env` a `.gitignore`.
2. **Alinear prefijos de URL** — Cambiar frontend de `/api/` a `/api/v1/` o viceversa. Unificar.
3. **Sincronizar schemas de tipos** — Alinear roles (`director/gerente/asesor/operaciones`), campos de schemas (`stage_id` vs `to_stage_id`, `estimated_value` vs `amount`).
4. **Corregir signup** — Modificar `bootstrap` para devolver `LoginResponse` con token, o hacer login automático después del signup.
5. **Enforce RBAC en todas las rutas** — Agregar `require_permission()` en contacts, opportunities, pipelines routes.
6. **Implementar Activities y Tasks backend** — Crear módulos `modules/activities/` y `modules/tasks/` con service, routes, schemas, domain.

### Fase 2 — Completar módulos (P1, ~3 semanas)

**Objetivo:** Todas las páginas del frontend deben funcionar.

7. **Implementar Documents backend** — Módulo con upload, list, download. Usar `sign_storage_url()`.
8. **Implementar Reports backend** — Endpoint `/api/reports/kpis` con queries agregadas.
9. **Implementar Automations engine** — Conectar event bus, crear motor de reglas.
10. **Agregar middleware Next.js** — Protección server-side de rutas authed.
11. **Implementar refresh tokens** — Nuevo endpoint `/api/users/refresh`.
12. **Agregar paginación real** — Usar `PageParams` y `Page` en todos los listados.

### Fase 3 — Calidad y operaciones (P2, ~2 semanas)

**Objetivo:** El sistema debe ser mantenible y observable.

13. **Escribir tests completos** — Cobertura de todos los módulos, assertions estrictas, fixtures aisladas.
14. **Agregar migraciones incrementales** — Para cada cambio de schema.
15. **Rate limiting** — Implementar con slowapi o similar.
16. **Logging estructurado** — JSON logs con correlation IDs.
17. **CORS configurable** — Leer de `Settings`, no hardcodeado.
18. **Headers de seguridad** — HSTS, CSP, X-Frame-Options.

### Fase 4 — Producción (P3, ~1 semana)

**Objetivo:** Listo para desplegar.

19. **PostgreSQL** — Migrar de SQLite a PostgreSQL para concurrencia real.
20. **Docker Compose** — Backend + Frontend + PostgreSQL + Redis.
21. **CI/CD** — GitHub Actions con tests, lint, build.
22. **Documentación API** — Swagger/OpenAPI actualizado.

---

*Fin del informe de auditoría.*
