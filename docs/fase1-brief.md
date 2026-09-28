# Tarea: CRM-Splash — Fase 1 (Tareas y Actividades)

Proyecto: `C:\Users\migue\CRM-Splash`. Contexto: `docs/mvp-plan.md` (lee la Fase 1), estado tras Fase 0 en `docs/fase0-informe.md`.

**Regla de oro: el backend se adapta al contrato del frontend, no al revés.** El contrato canónico está en `frontend/src/lib/types/api.ts` (interfaces `Task`, `TaskCreate`, `TaskFilters`, `Activity`, `ActivityCreate`, tipos `TaskStatus/TaskPriority/ActivityType`) y los clientes en `frontend/src/lib/api/tasks.ts` y `activities.ts` (endpoints `/api/tasks`, `/api/activities` — llegan al backend como `/api/v1/tasks` etc. vía el rewrite de Next.js; tú registras el router con `prefix="/api/v1"` como los demás módulos).

Convenciones obligatorias (mira `modules/contacts/` como referencia): estructura `domain.py / schemas.py / service.py / routes.py / __init__.py` con `register_module(app, bus)`; aislamiento tenant con `current_org_id()`; errores con subclases de `CRMError`; `require_permission()` en todas las rutas (añade permisos `TASK_*` y `ACTIVITY_*` a `core/rbac.py` y asígnalos a los roles igual que los demás); paginación con el helper de `core/pagination.py` (respuesta `PaginatedResponse`); publicación de eventos al bus con los modelos de `core/event_bus/models.py`.

## 1. Migración incremental (Alembic)
Las tablas `tasks` y `activities` ya existen (migración 0001) pero les faltan columnas que el frontend necesita. Crea `backend/migrations/versions/0002_tasks_activities_gaps.py`:
- `activities`: añade `task_id` (FK tasks.id, ondelete SET NULL, nullable), `duration_minutes` (Integer, nullable). La columna `scheduled_at` existente mapea al concepto `occurred_at` del frontend si no hay algo mejor: decide el mapeo más limpio (puedes añadir columna `occurred_at` DateTime nullable y copiar datos; explica la decisión en el informe).
- `tasks`: el frontend usa `due_date` como datetime; la tabla tiene `due_date` Date + `due_time` Time. Decide el mapeo más limpio (p. ej. exponer datetime combinado en el schema Pydantic sin tocar la tabla, o añadir columna; justifica).
- Verifica la migración contra un SQLite TEMPORAL con nombre único (`_verify_fase1.db`): `alembic upgrade head` desde cero, cuenta columnas de ambas tablas, y borra el archivo temporal después. NUNCA toques el .db real del proyecto.

## 2. Módulo `modules/tasks`
- `domain.py`: modelo SQLAlchemy `Task` mapeado a la tabla existente.
- `service.py`: CRUD tenant-scoped; `list` con todos los filtros de `TaskFilters` incluidos `search` (título/descripción), `view` (`mine` = asignadas al usuario actual, `today` = due hoy, `overdue` = due < hoy y status no completed/cancelled, `upcoming` = due >= hoy) y `due_before/due_after`; `complete` (idempotente: si ya completed no falla, no re-setea `completed_at`); validación de que contact/opportunity/company/owner existen y pertenecen a la misma org (error 404/422 con CRMError, nunca permitir cross-tenant).
- `routes.py`: GET list (paginado), GET /{id}, POST, PATCH /{id}, DELETE /{id} (204). El complete del frontend es un PATCH con status=completed — debe funcionar, pero no rompas RBAC.
- Respuesta `TaskRead` con nombres denormalizados: `contact_name`, `opportunity_name`, `company_name`, `owner_name` (JOINs o subqueries dentro de la misma org). `owner_id` default = usuario actual si no se especifica.
- Eventos: publica `TaskCreated` al crear y `TaskCompleted` al completar.

## 3. Módulo `modules/activities`
- Timeline append-only: POST crea, GET lista paginada con filtros (`type`, `contact_id`, `opportunity_id`, `company_id`, `user_id`, rango `from/to`), DELETE solo para tipos manuales (`note`, `call`, `email`, `meeting`, `sms`, `whatsapp`) — las actividades generadas por sistema (`stage_change`, `created`, `updated`, `task_completed`) no se borran ni se crean por API.
- `user_id` = usuario actual, no editable.
- `metadata` ↔ columna `metadata_json` (JSON serializado; valida que sea un objeto plano de valores escalares).
- Publica `ActivityCreated` al crear.

## 4. Actividades automáticas básicas (integra con lo existente, sin sobre-ingeniería)
Cuando una oportunidad cambia de etapa (`opportunities/service.py` ya publica `OpportunityStageChanged`), registra una activity `stage_change` en esa oportunidad. Implementación preferida: suscribe un handler en el bus en `modules/activities/__init__.py` (register_module recibe el bus) — NO añadas lógica en el service de opportunities. Si el dispatch del bus es asíncrono/diferido y complica la verificación, usa la opción más simple que garantice que la activity queda registrada en la misma request, y explícalo.

## 5. Verificación obligatoria (ejecuta y muestra salida real)
1. Compila todos los .py tocados (`python -m py_compile ...`).
2. `cd backend && .venv/Scripts/python -m pytest tests/ -q` — todo verde (adapta tests existentes solo si tu cambio los rompe de forma justificada).
3. Tests NUEVOS: `tests/test_tasks.py` (crear/complete/filters view=overdue/aislamiento tenant entre 2 orgs/permiso denegado a rol sin permiso) y `tests/test_activities.py` (crear nota, listado filtrado, borrado permitido vs sistema prohibido, stage_change genera activity). Mínimo 10 tests nuevos, todos pasando.
4. Amplía `scripts/smoke.py`: crear tarea → completarla → crear nota → transición de oportunidad → verificar activities incluye la de stage_change. Debe seguir imprimiendo SMOKE OK.
5. `cd frontend && npx tsc --noEmit` — exit 0 (no deberías necesitar tocar frontend; si necesitas tocar algo, mínimo y justificado).

## Informe
Escribe `docs/fase1-informe.md`: archivos creados/cambiados, decisiones de mapeo (occurred_at, due_date), salida real de las 5 verificaciones, y cualquier desviación.
