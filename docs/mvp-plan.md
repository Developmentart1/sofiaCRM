# Plan MVP — CRM-Splash

> Objetivo: pasar del estado actual (~40% funcional, fachada en 5 páginas) a un MVP demostrable de extremo a extremo, **incluyendo un módulo de automatizaciones real**.
> Base aprovechable: multi-tenancy sólida, auth JWT+bcrypt, event bus con outbox (sin conectar), 17 tablas migradas (incl. `automation_rules/actions/executions`), 20 eventos tipados ya definidos, frontend con clientes API para casi todo.

---

## Fase 0 — Cimientos críticos (P0, prerrequisito de todo)

| # | Tarea | Detalle |
|---|---|---|
| 0.1 | **Enforzar RBAC en rutas** | Añadir `require_permission()` en todas las rutas de contacts, pipelines, opportunities. Permisos nuevos: `CONTACT_*`, `PIPELINE_*`, `OPPORTUNITY_*` ya deben existir en `core/rbac.py` — verificar y completar. |
| 0.2 | **Conectar el event bus** | `create_app()` instancia `configure_bus()` y lo pasa a cada `register_module(app, bus)`. Los services publican eventos reales (`ContactCreated`, `OpportunityStageChanged`, etc.) dentro de la misma transacción (outbox). Arrancar `dispatch_pending` en un loop (startup task con intervalo corto, suficiente para MVP). |
| 0.3 | **Persistencia de sesión frontend** | Cambiar token in-memory → cookie HttpOnly en backend (set-cookie en `/login`) + middleware Next.js que protege `/(*authed)`. Eliminar `memoryState` de `use-auth.ts`. |
| 0.4 | **Secrets** | `.env.example` con placeholders; fallar en startup si `jwt_secret` es el valor por defecto en no-dev. |
| 0.5 | **Smoke test base** | Script `scripts/smoke.py`: bootstrap org → login → crear contacto → pipeline → oportunidad → transición. Corre contra SQLite temporal. |

**Criterio de salida:** `smoke.py` pasa; los módulos existentes publican eventos visibles en `event_outbox`.

---

## Fase 1 — Tareas y Actividades (backend real para el frontend existente)

Las tablas ya existen (migración 0001) y el frontend ya tiene `tasksApi`/`activitiesApi`.

- `modules/tasks`: domain (Task con estado `pending/done/overdue`, `due_at`, asignado a usuario, vinculado opcional a oportunidad), service con aislamiento tenant, routes CRUD + `POST /{id}/complete` + filtro "mis tareas / vencidas".
- `modules/activities`: timeline append-only (`activity_type`: note/call/email/stage_change/system), routes de listado filtrado por contacto/oportunidad + creación manual (notas).
- Los services publican `TaskCreated`, `TaskCompleted`, `ActivityCreated` al bus.
- Verificar que los contratos coincidan con `frontend/src/lib/types/api.ts` (ajustar backend al schema existente del frontend, no al revés).

**Criterio:** páginas `/tasks` y `/activities` funcionan contra API real sin tocar el frontend (o con ajustes mínimos).

---

## Fase 2 — Módulo de Automatizaciones (nuevo)

### Diseño

El schema ya soporta el motor: `automation_rules` (trigger_event, is_active, max_depth) + `automation_actions` (action_type, config_json, position) + `automation_executions` (status, depth, result, error). El bus ya entrega eventos tipados. Falta el motor.

```
modules/automations/
├── domain.py       # AutomationRule, AutomationAction, AutomationExecution (SQLAlchemy)
├── schemas.py      # Pydantic: RuleCreate/Read, ActionSpec, ExecutionRead
├── engine.py       # motor de evaluación y ejecución
├── actions.py      # registro de acciones extensible
├── service.py      # CRUD de reglas + consulta de ejecuciones (tenant-scoped)
├── routes.py       # API REST
└── __init__.py     # register_module(app, bus) → suscribe el handler del motor
```

### Semántica

1. **Trigger** = un `event_type` existente (`opportunity.stage_changed`, `contact.created`, `task.created`, …). El motor se suscribe a cada tipo conocido en `register_module`.
2. **Condición opcional**: `config_json` de la regla con filtros simples sobre el payload (`{"field": "to_stage_id", "op": "eq", "value": "…"}` combinables con AND). Para MVP: comparadores `eq / neq / contains / gt / lt` — nada de DSL complejo.
3. **Acciones** (registro `{action_type: handler}` en `actions.py`), MVP:
   - `create_task` — crea tarea asignada (campo estático o derivado del evento, p. ej. `assigned_from_event: opportunity.assigned_user_id`).
   - `create_activity` — registra actividad/nota en el contacto u oportunidad del evento.
   - `move_stage` — transiciona la oportunidad a otra etapa (usa el mismo service de opportunities, respetando sus reglas de negocio).
   - `update_field` — actualiza un campo permitido de contacto/oportunidad (allowlist estricta).
   - Cada acción es idempotente por `(execution_id)` y corre en la transacción de la ejecución.
4. **Anti-recursión** (crítico):
   - El motor lleva `depth` en la ejecución; si una acción genera un evento que dispara otra regla, `depth += 1` y se rechaza al superar `rule.max_depth` (default 5).
   - Regla dura: las acciones del motor publican sus eventos con flag `source="automation"` y el motor **ignora eventos con ese flag** cuando quien dispara sería la misma regla. Sin excepciones.
5. **Ejecución**: el handler del motor crea `automation_executions` (`pending → success/failed/skipped`), guarda `result_json`/`error`. Fallos de una acción no revierten las previas (se registra), pero sí marcan `failed`.

### API

```
GET    /api/v1/automations/rules          # listar reglas de la org
POST   /api/v1/automations/rules          # crear regla + acciones
GET    /api/v1/automations/rules/{id}
PATCH  /api/v1/automations/rules/{id}     # editar / is_active
DELETE /api/v1/automations/rules/{id}
GET    /api/v1/automations/executions     # historial (filtro por regla/estado)
POST   /api/v1/automations/rules/{id}/test # dry-run con un evento sintético
```

Permisos RBAC: `AUTOMATION_READ / AUTOMATION_MANAGE`. Auditoría `@audit_log` en crear/editar/borrar reglas.

### Frontend

- Página `/automations` (nueva, bajo `(authed)`): lista de reglas con switch activo/inactivo, builder simple: trigger (select de eventos) + condiciones (fila campo/op/valor) + acciones ordenadas. Historial de ejecuciones con estado.
- Cliente `lib/api/automations.ts` siguiendo el patrón de `contacts.ts`.

**Criterio:** regla "al ganar oportunidad → crear tarea de seguimiento" se dispara sola desde la UI de oportunidades; ejecuciones visibles; recursión bloqueada por test.

---

## Fase 3 — Documentos y Reportes (alcance mínimo honesto)

- **Documentos**: backend real (upload multipart a disco en `storage/{org_id}/`, tabla `documents` ya existe, firmas de URL como en `verify_storage_url`), solo si es parte del MVP; si no, **ocultar la página** del nav hasta tener backend (no mostrar fachadas).
- **Reportes/Dashboard**: endpoints reales de KPIs (pipeline value por etapa, oportunidades ganadas/perdidas, tareas vencidas) con agregaciones SQL simples tenant-scoped. Conectar la página `/reports` y los widgets del dashboard existentes.

---

## Fase 4 — Endurecimiento y demo

| # | Tarea |
|---|---|
| 4.1 | Tests: auth flow completo, RBAC por rol (matrix básica), tenant isolation de los módulos nuevos, anti-recursión de automatizaciones, transiciones de oportunidad. Meta: pytest verde, ~30 tests. |
| 4.2 | Seed renovado: 2 orgs (para demostrar aislamiento), roles variados, 2-3 reglas de automatización de ejemplo. |
| 4.3 | Lint/typecheck: `ruff` + `mypy` backend, `tsc --noEmit` frontend en CI local. |
| 4.4 | `INTEGRATION_TEST.md` actualizado con el flujo E2E real. |

---

## Orden y dependencias

```
F0 (cimientos) ──> F1 (tasks/activities) ──> F2 (automatizaciones) ──> F3 (docs/reportes) ──> F4
                        └── F2 necesita los eventos de F1 como triggers útiles
```

F3 puede paralelizarse con F2. Estimación: F0 ½ día, F1 1 día, F2 1-2 días, F3 1 día, F4 1 día.

## Fuera del MVP (declarado)

- Custom fields (tabla existe, no se implementa), merge de contactos, notificaciones externas (email), refresh tokens, RLS a nivel de BD.
