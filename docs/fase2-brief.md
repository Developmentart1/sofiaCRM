# Tarea: CRM-Splash — Fase 2 (Módulo de Automatizaciones)

Proyecto: `C:\Users\migue\CRM-Splash`. Contexto: `docs/mvp-plan.md` (Fase 2). El estado actual tras Fases 0-1 está en `docs/fase0-informe.md` y `docs/fase1-informe.md` — léelos antes (especialmente cómo quedó el event bus).

**Hechos del código actual que condicionan el diseño (verificados):**
- `core/event_bus/event_bus.py`: `SyncEventBus.publish()` persiste al outbox Y entrega a handlers **síncronamente dentro de la misma transacción**. `subscribe_event(event_cls, handler)` es el patrón de suscripción (mira `modules/activities/__init__.py`).
- Los eventos de `core/event_bus/models.py` tienen `model_config = ConfigDict(extra="forbid")` → **NO puedes añadir campos (flags) a los payloads**. La anti-recursión debe implementarse con `contextvars`, no con flags en el evento.
- Las tablas `automation_rules`, `automation_actions`, `automation_executions` ya existen en la migración 0001 con las columnas descritas en `docs/mvp-plan.md`. NO crees migración salvo falta real justificada.
- Convenciones: estructura por módulo (`domain/schemas/service/routes/__init__`), `register_module(app, bus)`, tenant con `current_org_id()`, errores con subclases de `CRMError`, `require_permission()` en rutas, paginación de `core/pagination.py`.

## 1. Backend — `modules/automations`

### Estructura
- `domain.py`: modelos SQLAlchemy `AutomationRule`, `AutomationAction`, `AutomationExecution` mapeados a las tablas existentes.
- `schemas.py`: `RuleCreate/RuleUpdate/RuleRead` (RuleRead incluye acciones anidadas y contadores de ejecuciones), `ExecutionRead`, `RuleTestRequest` (evento sintético para dry-run).
- `conditions.py`: evaluación de condiciones. Formato JSON en `automation_rules` — si la tabla no tiene columna para condiciones, guárdalas como una acción especial o añade la columna con migración `0003_automation_conditions` (decide lo más limpio; documenta). Semántica: lista de `{field, op, value}` combinadas con AND; ops: `eq, neq, contains, gt, lt`. `field` resuelve contra atributos del payload del evento (soporta un nivel de lookup simple, p. ej. `to_stage_id`). Si la regla no tiene condiciones, siempre matchea.
- `actions.py`: registro extensible `ACTION_REGISTRY: dict[str, ActionHandler]` con:
  - `create_task`: `config_json` con `title` (soporta placeholders `{{event.opportunity_id}}`, `{{event.title}}` simples), `priority`, `due_offset_days` opcional, `assigned_user_id` estático o `{"from_event": "opportunity.assigned_user_id"}` con fallback al owner de la oportunidad.
  - `create_activity`: registra nota/actividad en el contacto u oportunidad del evento (usa el service de activities).
  - `move_stage`: transiciona la oportunidad del evento a `stage_id` destino usando el service de opportunities (respeta sus reglas de negocio; si la transición es inválida, la acción falla y se registra el error, no crashea la request original).
  - `update_field`: allowlist estricta de campos actualizables (`opportunity.value`, `contact.email`, etc. — define la allowlist en código, nada de setattr libre).
- `engine.py`:
  - `handle_event(event, db)`: busca reglas activas de la org cuyo `trigger_event == event.event_type`; evalúa condiciones; ejecuta acciones en orden de `position`; crea `AutomationExecution` por regla disparada (`status`: `success/failed/skipped`, `result_json`, `error`).
  - **Anti-recursión (crítico, con contextvars)**:
    1. `ContextVar[int]` de profundidad: el motor la incrementa antes de ejecutar acciones y restaura al terminar. Si la profundidad actual >= `rule.max_depth` → la regla se marca `skipped` (con motivo en result_json) y no ejecuta.
    2. `ContextVar[frozenset[str]]` de reglas en curso: si el evento proviene de una ejecución cuya regla ya está en el stack, se salta (rompe ciclos A→B→A aunque ninguna supere max_depth individual).
  - El motor NUNCA propaga excepciones al handler del bus: todo fallo se registra en la ejecución.
- `service.py` + `routes.py` (RBAC: añade permisos `AUTOMATION_READ`, `AUTOMATION_MANAGE` a `core/rbac.py` y asígnalos a roles admin/manager como los demás):
  ```
  GET    /api/v1/automations/rules
  POST   /api/v1/automations/rules        # regla + acciones anidadas
  GET    /api/v1/automations/rules/{id}
  PATCH  /api/v1/automations/rules/{id}
  DELETE /api/v1/automations/rules/{id}   # 204
  GET    /api/v1/automations/executions   # paginado, filtros rule_id/status
  POST   /api/v1/automations/rules/{id}/test  # dry-run: recibe payload sintético, ejecuta condiciones+acciones en modo NO persistir acciones (o transacción rollback), devuelve qué habría pasado
  ```
  Valida en create/update: `trigger_event` debe ser un event_type existente en `models.py`; `action_type` debe estar en el registro; `stage_id`/entidades referenciadas en configs deben existir en la misma org.
- `__init__.py`: `register_module(app, bus)` suscribe `engine.handle_event` a TODOS los event_types de `models.py` (iterando el union `EventEnvelope` o la lista de clases). `@audit_log` en create/update/delete de reglas.

### Integración con lo existente
- `opportunities/service.py` ya publica eventos al mover etapas — el motor debe dispararse con eso sin tocar opportunities.
- La suscripción ocurre en startup: verifica el orden de registro de módulos en `main.py` (automations después de activities/opportunities).

## 2. Frontend — página `/automations`
- Cliente `frontend/src/lib/api/automations.ts` (patrón `contacts.ts`) + tipos en `frontend/src/lib/types/api.ts`.
- Página `frontend/src/app/(authed)/automations/page.tsx`: lista de reglas con switch activo/inactivo (PATCH), botón Nueva regla → diálogo/builder con: select de trigger (eventos disponibles), condiciones (filas campo/op/valor, agregables), acciones ordenadas (select de tipo + campos de config según tipo). Historial de ejecuciones (tabla con estado, regla, fecha, error).
- Añade la entrada al nav en `frontend/src/components/layout/sidebar.tsx` (icono Zap o Workflow, permission `automations:read` si el sidebar usa permissions, sigue el patrón existente).
- Estilo: usa los componentes existentes (mira `/tasks` o `/pipelines` como referencia de patrones, tablas, diálogos). Nada de dependencias nuevas.

## 3. Tests nuevos (backend)
`tests/test_automations.py`, mínimo:
1. Regla `opportunity.stage_changed` + `create_task` → al mover etapa se crea la tarea (assert real en BD).
2. Condición que no matchea → ejecución no se crea o `skipped`.
3. **Anti-recursión**: regla `task.created → create_task` con max_depth 5 → la cadena se detiene y no explota (assert de profundidad acotada en ejecuciones).
4. Ciclo entre dos reglas → una se salta.
5. `move_stage` a etapa inválida → ejecución `failed`, la oportunidad intacta.
6. Aislamiento tenant: regla de org A no se dispara con eventos de org B.
7. Permiso denegado a rol sin `AUTOMATION_MANAGE`.
8. Dry-run `/test` no persiste efectos.

## 4. Verificación obligatoria (salida real en el informe)
1. Compila todos los .py tocados.
2. `cd backend && .venv/Scripts/python -m pytest tests/ -q` — TODO verde (los 19 previos + los nuevos).
3. Amplía `scripts/smoke.py`: crear regla "al ganar oportunidad → crear tarea de seguimiento" → ganar la oportunidad → assert de que la tarea existe y la ejecución quedó `success`. Debe seguir imprimiendo SMOKE OK.
4. `cd frontend && npx tsc --noEmit` — exit 0.
5. `cd frontend && npm run lint` si existe configurado — reporta resultado (no bloquees si falla por reglas preexistentes).

## Informe
Escribe `docs/fase2-informe.md`: arquitectura del motor, decisiones (condiciones: columna o convención; anti-recursión), archivos creados/cambiados, salida real de las 5 verificaciones, desviaciones.
