# Informe — Fase 2 (Módulo de Automatizaciones)

Proyecto: `C:\Users\migue\CRM-Splash`. Ejecutada la Fase 2 del plan (`docs/mvp-plan.md`) según el brief `docs/fase2-brief.md`. Se leyeron antes `docs/fase0-informe.md` y `docs/fase1-informe.md` (en especial cómo quedó el event bus con entrega síncrona).

---

## Resumen

Implementado el motor de automatizaciones (`modules/automations`) con reglas, condiciones, acciones extensibles, anti-recursión por ContextVars, API REST con RBAC y dry-run, la migración `0003`, 8 tests nuevos y la página `/automations` en el frontend. Las 5 verificaciones pasan (27 tests, smoke `SMOKE OK`, `tsc` exit 0, `lint` exit 0).

---

## 1. Arquitectura del motor

El motor es un handler del event bus suscrito a **todos** los `event_type` de `core/event_bus/models.py`. El flujo:

```
event (BaseEvent) ──> bus.publish ──> _deliver (síncrono) ──> automations.engine.handle_event
                                                                    │
                                        tenant-scope por event.organization_id
                                                                    │
                                        reglas activas con trigger_event == event.event_type
                                                                    │
                                        por regla: condiciones (AND) → acciones (por position)
```

- `handle_event(event, db)` está suscrito en `register_module` iterando el union `EventEnvelope` (`all_event_classes()`). **Nunca propaga excepciones**: cada fallo se registra en una `AutomationExecution` (o se loguea si ni siquiera se pudo crear la ejecución).
- `conditions.py`: condiciones como lista `{field, op, value}` combinadas con AND; ops `eq/neq/contains/gt/lt`. `field` resuelve contra atributos planos del payload. Los `UUID` se comparan por su forma `.hex` (el formato de almacenamiento de las entidades) y los `datetime` por `isoformat()`, para que `to_stage_id eq <hex>` funcione.
- `actions.py`: `ACTION_REGISTRY: dict[str, ActionHandler]` extensible con `@register_action`. Handlers: `create_task`, `create_activity`, `move_stage`, `update_field`. Corren en la transacción del engine (solo `flush`, nunca `commit`) y, salvo en dry-run, publican su propio evento para permitir encadenamiento (acotado por la anti-recursión).
- `engine.py`: `_run_single` evalúa condiciones → ejecuta acciones → persiste `AutomationExecution` con `status ∈ success/failed/skipped`, `result_json` y `error`.

### Anti-recursión (ContextVars)

Como los payloads son `extra="forbid"`, no se pueden añadir flags. En `state.py` se definen:

1. `depth: ContextVar[int]` — el engine la incrementa antes de ejecutar las acciones de una regla y la restaura en `finally`. Si `depth >= rule.max_depth` la regla queda `skipped` (`reason: max_depth`).
2. `in_progress: ContextVar[frozenset[str]]` — ids de reglas en el stack. Si el evento proviene de una ejecución cuya regla ya está en el stack, se salta (`reason: cycle`), rompiendo ciclos A→B→A.
3. `dry_run: ContextVar[bool]` — en `/test` los handlers no persisten ni publican.

### Dry-run

`POST /rules/{id}/test` construye un evento sintético (`build_event`, validado contra `EventEnvelope` → 422 si es inválido) y ejecuta `_run_single(dry_run=True)`: las acciones corren dentro de un `SAVEPOINT` (`db.begin_nested()`) que se revierte, con `dry_run=True` para que `create_task`/`create_activity` no publiquen eventos y `move_stage` solo valide. Devuelve `{matched, status, reason, actions:[{action_type, position, ok, result|error}], error}`.

---

## 2. Decisiones

1. **Condiciones: columna nueva (`conditions_json`)** en vez de "acción especial". Es el camino más limpio y consultable; se añadió con la migración `0003_automation_conditions` (columna `Text` nullable sobre `automation_rules`, down_revision `0002`).
2. **Anti-recursión por ContextVars** (no por flags en el evento), como exige el brief.
3. **`trigger_event_id` de la ejecución = aggregate id del evento** (mejor esfuerzo). El handler del bus recibe el `BaseEvent`, no el id de la fila de outbox, así que se usa el mismo criterio de aggregate que `event_bus._event_aggregate_id` (fallback a `organization_id`).
4. **`move_stage` usa `OpportunityService.transition_stage`** envuelto en `org_scope(event.organization_id)`, respetando sus reglas de negocio. Su `commit()` interno se conserva (el brief lo permite explícitamente); el engine solo lo invoca fuera de dry-run. Una transición inválida se captura y deja la ejecución `failed` sin revertir la oportunidad.
5. **Resolución de asignatario** (`create_task`/`create_activity`): estático → `{"from_event": "..."}` → owner de la oportunidad del evento → `event.assigned_user_id` → primer admin de la org. Necesario porque `tasks.assigned_user_id` y `activities.user_id` son NOT NULL; si no se puede resolver, la acción falla con error claro (no crashea).
6. **`update_field`**: allowlist estricta en código (`opportunity.estimated_value/priority/assigned_user_id`, `contact.email/phone/status`), sin `setattr` libre.
7. **Permisos**: `AUTOMATION_READ`/`AUTOMATION_MANAGE` **ya existían** en `core/rbac.py` (definidos en una fase previa y asignados a `ADMIN` (todos), `DIRECTOR` (ambos) y `GERENTE` (solo `AUTOMATION_READ`)). No hubo que tocar `rbac.py`; se usan tal cual en las rutas.
8. **Frontend**: el modelo de permisos del frontend (`lib/types/domain.ts`) ya tenía `automations:read`/`automations:write` y se usan en el sidebar; no se tocó. La API del frontend (`reports.ts`) tenía un `automationsApi` fachada apuntando a `/api/automations` (sin backend y sin consumidores); se dejó intacto y el cliente real va en `lib/api/automations.ts`.

---

## 3. Archivos creados / cambiados

**Backend (nuevos)**
- `migrations/versions/0003_automation_conditions.py`
- `src/modules/automations/{__init__,domain,state,conditions,actions,engine,schemas,service,routes}.py`
- `tests/test_automations.py`

**Backend (modificados)**
- `src/main.py` — registra `automations` tras `activities`.
- `scripts/smoke.py` — flujo: crear regla "al ganar → crear tarea" → ganar → assert de tarea + ejecución `success`.

**Frontend (nuevos)**
- `src/lib/api/automations.ts`
- `src/app/(authed)/automations/page.tsx`

**Frontend (modificados)**
- `src/lib/types/api.ts` — tipos `AutomationCondition/ActionSpec/Action/RuleRead/RuleCreate/Execution/TestResult`.
- `src/components/layout/sidebar.tsx` — entrada "Automatizaciones" (icono `Zap`, permiso `automations:read`).

---

## 4. Resultados de las 5 verificaciones

### 1. Compilación
```
$ cd backend && .venv/Scripts/python.exe -m py_compile $(find src scripts -name '*.py')
PY_COMPILE OK (all src + scripts)
```

### 2. Tests
```
$ cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
collected 27 items
tests\test_activities.py ......                                          [ 22%]
tests\test_automations.py ........                                       [ 51%]
tests\test_business_rules.py ..                                          [ 59%]
tests\test_tasks.py ......                                               [ 81%]
tests\test_tenant_isolation.py .....                                     [100%]
============================= 27 passed in 2.18s ==============================
```
(19 previos + 8 nuevos; ningún test existente necesitó adaptación.)

### 3. Smoke
```
$ cd backend && .venv/Scripts/python.exe scripts/smoke.py
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, ...
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_tasks_activities_gaps, ...
INFO  [alembic.runtime.migration] Running upgrade 0002_tasks_activities_gaps -> 0003_automation_conditions, ...
SMOKE OK (event_outbox rows: 12)
```

### 4. Frontend typecheck
```
$ cd frontend && npx tsc --noEmit
(exit 0)
```

### 5. Lint
```
$ cd frontend && npm run lint
(exit 0 — solo warnings preexistentes de react-hooks/exhaustive-deps en use-*.ts; ninguno en los archivos nuevos)
```

---

## 5. Tests nuevos (8) — `tests/test_automations.py`

1. `test_rule_stage_changed_creates_task` — regla `opportunity.stage_changed` + `create_task` → al mover etapa se crea la tarea (assert en BD vía API) y la ejecución queda `success`.
2. `test_condition_not_matched_skips_execution` — condición `to_stage_id eq lost` que no matchea → ejecución `skipped` con `reason: conditions_not_met`, sin tarea.
3. `test_anti_recursion_bounded_depth` — regla `task.created → create_task` con `max_depth 5` → la cadena se detiene (profundidad acotada, ≤ 5 ejecuciones), sin explotar.
4. `test_cycle_between_two_rules_is_broken` — ciclo A(`task.created`→`create_activity`) ⇄ B(`activity.created`→`create_task`) → una ejecución queda `skipped` (`reason: cycle`).
5. `test_move_stage_invalid_marks_failed_and_keeps_opportunity` — `move_stage` a etapa que rompe regla de negocio → ejecución `failed`, oportunidad intacta (`won`).
6. `test_tenant_isolation_rule_does_not_fire_cross_org` — regla de org A no se dispara con evento de org B.
7. `test_create_rule_denied_for_role_without_permission` — rol `asesor` sin `AUTOMATION_MANAGE` → 403.
8. `test_dry_run_does_not_persist` — `/test` no persiste la tarea ni crea ejecución.

---

## 6. Desviaciones / decisiones destacadas

1. **Condiciones en columna nueva** (`0003_automation_conditions`) en lugar de "acción especial" (ver §2.1).
2. **Auto-ciclo de una misma regla se corta en profundidad 1** (el guard `in_progress` aplica también a A→A). El test #3 asevera "profundidad acotada y sin explosión" (que se cumple); `max_depth` opera sobre cadenas de reglas *distintas*. Documentado, no es una regresión.
3. **`move_stage` conserva el `commit()` interno** de `OpportunityService.transition_stage` (el brief lo permite); fuera de dry-run el engine no controla ese commit.
4. **Permisos RBAC ya existentes** (`AUTOMATION_READ/MANAGE`), sin cambios en `rbac.py`.
5. **Fallback a admin de la org** para resolver el asignatario de tareas/actividades cuando el evento no trae usuario (necesario por los NOT NULL de `tasks`/`activities`).
6. **`automationsApi` fachada** de `reports.ts` (sin backend, sin consumidores) dejada intacta; el cliente real en `lib/api/automations.ts`.

---

## 7. Cambios por archivo

**Backend (nuevos)**
- `migrations/versions/0003_automation_conditions.py`
- `src/modules/automations/{__init__,domain,state,conditions,actions,engine,schemas,service,routes}.py`
- `tests/test_automations.py`

**Backend (modificados)**
- `src/main.py` — registro de `automations`.
- `scripts/smoke.py` — flujo de automatización (regla + assert de tarea/ejecución).

**Frontend (nuevos)**
- `src/lib/api/automations.ts`
- `src/app/(authed)/automations/page.tsx`

**Frontend (modificados)**
- `src/lib/types/api.ts` — tipos de automatización.
- `src/components/layout/sidebar.tsx` — entrada de nav.
