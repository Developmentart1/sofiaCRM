# Informe — Fase 1 (Tareas y Actividades)

Proyecto: `C:\Users\migue\CRM-Splash`. Ejecutada la Fase 1 del plan (`docs/mvp-plan.md`) según el brief `docs/fase1-brief.md`. El backend se adapta al contrato del frontend (`frontend/src/lib/types/api.ts` y clientes `tasks.ts`/`activities.ts`).

---

## Resumen

Implementados los módulos `modules/tasks` y `modules/activities` (backend real para las páginas `/tasks` y `/activities` existentes), la migración `0002`, la actividad automática `stage_change` vía event bus, y 12 tests nuevos. Las 5 verificaciones pasan (19 tests, smoke `SMOKE OK`, `tsc` exit 0). No se tocó el frontend.

---

## 1. Migración `0002_tasks_activities_gaps`

`backend/migrations/versions/0002_tasks_activities_gaps.py` (revisión `0002_tasks_activities_gaps`, down_revision `0001_initial`):

- `activities`: añade `task_id` (String(36), nullable), `duration_minutes` (Integer, nullable) y `occurred_at` (DateTime, nullable). Backfill `occurred_at = scheduled_at` para no perder datos existentes; `scheduled_at` se conserva.
- `tasks`: **sin cambios de tabla** (ver decisión de mapeo más abajo).

### Decisión de mapeo `occurred_at`
`occurred_at` ("cuándo pasó") y `scheduled_at` ("cuándo está planificado") son semánticamente distintos. Añado `occurred_at` como columna nueva y copio los datos de `scheduled_at`; las actividades nuevas siempre fijan `occurred_at` explícitamente (default = now, y `event.entered_stage_at` para `stage_change`).

### Decisión de mapeo `due_date` (tasks)
El frontend expone `due_date` como datetime; la tabla tiene `due_date` Date + `due_time` Time. **No toco la tabla**: expongo el datetime combinado en el schema Pydantic (`_combine_due`/`_split_due` en `service.py`) y, al recibir un datetime del frontend, lo separo en `due_date`/`due_time`. Es el mapeo más limpio (cero migración de datos, sin columna duplicada).

### Nota sobre `task_id` y SQLite
SQLite no soporta `ALTER TABLE ... ADD CONSTRAINT` (FK), por lo que `task_id` se añade como `String(36)` plano; el modelo ORM `Activity.task_id` sí declara `ForeignKey("tasks.id", ondelete="SET NULL")` (solo afecta a `create_all`, no al runtime de consultas).

### Verificación (SQLite temporal `_verify_fase1.db`, borrado después)
```
tasks columns: 15  → id, organization_id, contact_id, company_id, opportunity_id,
                     assigned_user_id, title, description, priority, status,
                     due_date, due_time, completed_at, created_at, updated_at
activities columns: 16 → id, organization_id, contact_id, company_id, opportunity_id,
                     user_id, type, subject, body, metadata_json, scheduled_at,
                     completed_at, created_at, task_id, duration_minutes, occurred_at
temp dir removed: True
```

---

## 2. Módulo `modules/tasks`

- `domain.py`: modelo `Task` espejo de la tabla `tasks`.
- `schemas.py`: `TaskCreate`/`TaskUpdate`/`TaskRead`. `owner_id` ↔ `assigned_user_id`. Coerción de `""` → `None` en IDs/`due_date` opcionales (el frontend envía cadenas vacías).
- `service.py`: CRUD tenant-scoped; `list` con todos los filtros de `TaskFilters` (`search` título/descripción, `status`, `priority`, `owner_id`, `contact_id`, `opportunity_id`, `company_id`, `due_before`/`due_after`, `view` ∈ `mine`/`today`/`overdue`/`upcoming`). `complete` idempotente (no falla ni re-setea `completed_at` si ya estaba completada). Validación cross-tenant de `contact/opportunity/company/owner` (404 `NotFoundError`). `owner_id` default = usuario actual.
- `routes.py`: GET list (paginado), GET /{id}, POST, PATCH /{id}, DELETE /{id} (204). El `complete` del frontend es un `PATCH` con `status=completed` (funciona con permiso `TASK_UPDATE`).
- `TaskRead` con nombres denormalizados (`contact_name`, `opportunity_name`, `company_name`, `owner_name`) vía LEFT JOINs dentro de la org.
- **Estado `overdue` derivado**: nunca se almacena. En la capa de lectura, si la tarea no está `completed`/`cancelled` y su `due_date` < hoy, se devuelve `status="overdue"` (coherente con `view=overdue` y con el filtro del frontend `t.status === "overdue"`).
- Eventos: `TaskCreated` al crear, `TaskCompleted` al completar (solo en la transición no-completada → completada).

## 3. Módulo `modules/activities`

- `domain.py`: modelo `Activity` espejo de la tabla.
- `schemas.py`: `ActivityCreate`/`ActivityRead`; constantes `MANUAL_ACTIVITY_TYPES` (`note`, `call`, `email`, `meeting`, `sms`, `whatsapp`) y `SYSTEM_ACTIVITY_TYPES` (`stage_change`, `created`, `updated`, `task_completed`). `metadata` ↔ `metadata_json` (dict plano de escalares, validado por el tipo).
- `service.py`: timeline append-only. POST crea solo tipos manuales (422 para tipos de sistema); GET lista paginada con filtros (`type`, `contact_id`, `opportunity_id`, `company_id`, `user_id`, rango `from`/`to`); DELETE solo tipos manuales (403 para sistema). `user_id` = usuario actual, no editable. Publica `ActivityCreated` al crear.
- `routes.py`: filtros `from`/`to` con `Query(alias="from"/"to")` para coincidir con las keys del frontend.

## 4. Actividades automáticas `stage_change`

- `modules/activities/__init__.py` suscribe en el bus, en `register_module(app, bus)`, el handler `record_stage_change` para `OpportunityStageChanged` (patrón preferido, el mismo que usará el motor de automatizaciones en Fase 2). **No** se añadió lógica al service de opportunities.
- **Decisión sobre dispatch asíncrono**: el outbox se entrega por un loop de fondo cada 2 s, lo que haría el smoke/test no determinista ("misma request"). En lugar de complicar, se hizo **síncrona** la entrega: `SyncEventBus.publish` ahora entrega a los suscriptores dentro de la misma transacción del publicador (y marca `dispatched_at` para que el loop no re-entregue). Así la activity `stage_change` queda registrada atómicamente con la transición, verificación determinista, y sin tocar `opportunities/service.py`.
- Actor de la activity: `current_user_id()` (nuevo ContextVar fijado por `OrgContextMiddleware`) con fallback a `assigned_user_id` de la oportunidad; si no hay actor, se omite la activity (no se viola el NOT NULL de `user_id`).

## 5. Cambios de soporte

- `core/pagination.py`: añadido `PaginatedResponse` (items/total/page/page_size/**total_pages**) para igualar el contrato del frontend (el helper solo tenía `Page`/`PageParams`).
- `core/tenant.py`: `set_user_id`/`current_user_id`/`current_user_id_or_none`/`reset_user_id`.
- `core/rbac.py`: permisos `TASK_READ/CREATE/UPDATE/DELETE` y `ACTIVITY_DELETE`; asignados siguiendo el patrón existente (DELETE solo ADMIN+DIRECTOR, READ para todos, CREATE/UPDATE para admin/director/gerente/asesor; `operaciones` solo `TASK_READ`).
- `core/event_bus/event_bus.py`: `publish` entrega sincrónicamente (`_deliver`); `dispatch_pending` conserva el reintento en fallo (no marca `dispatched_at` si el handler falla).
- `modules/users/auth_deps.py`: `OrgContextMiddleware` ahora también fija el `user_id` desde el `sub` del JWT.
- `main.py`: registra `tasks` y `activities`.

---

## Resultados de las 5 verificaciones

### 1. Compilación
```
$ cd backend && .venv/Scripts/python.exe -m py_compile <todos los .py tocados>
PY_COMPILE OK
```

### 2. Tests
```
$ cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
collected 19 items
tests\test_activities.py ......      [ 31%]
tests\test_business_rules.py ..      [ 42%]
tests\test_tasks.py ......           [ 73%]
tests\test_tenant_isolation.py ..... [100%]
============================== 19 passed in 2.05s ==============================
```
(7 tests preexistentes + 12 nuevos; ningún test existente necesitó adaptación.)

### 3. Smoke
```
$ cd backend && .venv/Scripts/python.exe scripts/smoke.py
...
SMOKE OK (event_outbox rows: 11)
```

### 4. Frontend typecheck
```
$ cd frontend && npx tsc --noEmit
(exit 0)
```
(Sin tocar el frontend.)

### 5. Migración (verificación en SQLite temporal)
Ver sección 1 (15/16 columnas, temp borrado).

---

## Tests nuevos (12)

`tests/test_tasks.py`: crear tarea (owner default), complete idempotente, `view=overdue`, aislamiento tenant entre 2 orgs, permiso denegado (`operaciones` → 403), rechazo cross-tenant de opportunity (404).

`tests/test_activities.py`: crear nota, listado filtrado por `type`, borrado manual permitido (204), borrado de actividad de sistema prohibido (403), creación de tipo de sistema prohibida (422), `stage_change` generada por transición de oportunidad.

Soporte: `tests/conftest.py` (apunta a SQLite temporal + migración `alembic upgrade head` una vez por sesión, para no tocar el `.db` real) y `tests/helpers.py` (seed raw SQL con IDs alineados al formato del ORM: `str(uuid4())` para orgs/usuarios, `uuid4().hex` para las demás entidades).

---

## Desviaciones / decisiones destacadas

1. **Entrega síncrona del bus** (`publish` entrega handlers en la misma transacción) para que `stage_change` quede en la misma request. Explicado en §4.
2. **`PaginatedResponse` añadido a `core/pagination.py`** (no existía; el helper solo exponía `Page`/`PageParams`).
3. **`task_id` sin constraint FK en SQLite** (limitación de `ALTER` de SQLite); FK declarada solo en el ORM.
4. **`NotFoundError` con un solo mensaje** (la firma real de `CRMError` es `(message, *, details)`); el patrón preexistente `NotFoundError("x", id)` es un bug latente en contacts/opportunities/pipelines que no se corrigió (fuera de alcance) — el código nuevo usa la firma correcta.
5. **`conftest.py`**: los tests (nuevos y preexistentes) corren contra un SQLite temporal migrado, no contra `crm_splash.db`.
6. **`occurred_at` vs `scheduled_at`** y **`due_date` combinado** — ver §1.

---

## Cambios por archivo

**Backend (nuevos)**
- `migrations/versions/0002_tasks_activities_gaps.py`
- `src/modules/tasks/{domain,schemas,service,routes,__init__}.py`
- `src/modules/activities/{domain,schemas,service,routes,__init__}.py`
- `tests/conftest.py`, `tests/helpers.py`, `tests/test_tasks.py`, `tests/test_activities.py`

**Backend (modificados)**
- `src/core/pagination.py` — `PaginatedResponse`.
- `src/core/tenant.py` — contexto de usuario.
- `src/core/rbac.py` — permisos `TASK_*` y `ACTIVITY_DELETE` + asignaciones.
- `src/core/event_bus/event_bus.py` — entrega síncrona en `publish`.
- `src/core/__init__.py` — exports nuevos.
- `src/modules/users/auth_deps.py` — `user_id` en `OrgContextMiddleware`.
- `src/main.py` — registro de `tasks` y `activities`.
- `scripts/smoke.py` — flujo ampliado (tarea → completar → nota → transición → activity `stage_change`).
