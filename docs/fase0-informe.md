# Informe — Fase 0 (Cimientos críticos)

Proyecto: `C:\Users\migue\CRM-Splash`. Ejecutada únicamente la Fase 0 del plan (`docs/mvp-plan.md`).

---

## Resumen

Fase 0 completada. Los 4 comandos de verificación pasan. Además de lo pedido en el brief, fue necesario corregir tres bugs latentes que el smoke test destapó y que bloqueaban el objetivo: (1) el ORM `EventOutbox` no coincidía con la tabla real `event_outbox` de la migración 0001, (2) la FK de `opportunities.source_id` apuntaba a `lead_sources` sin modelo ORM, y (3) el `ContextVar` de tenant no se propagaba de la dependencia sync al endpoint (por eso los tests existentes eran laxos con `200/403`).

---

## 0.1 — RBAC en rutas

### `core/rbac.py`
- Añadidos `PIPELINE_CREATE`, `PIPELINE_UPDATE`, `PIPELINE_DELETE` (faltaban; solo existían `PIPELINE_READ`/`PIPELINE_MANAGE`).
- Asignados a `DIRECTOR` los nuevos permisos de pipeline (coherente con que DIRECTOR ya tenía `PIPELINE_MANAGE`). `GERENTE`/`ASESOR`/`OPERACIONES` siguen con solo `PIPELINE_READ`.
- `CONTACT_DELETE` y `OPPORTUNITY_DELETE` ahora también se asignan a `DIRECTOR` (antes solo los tenía `ADMIN`), para que los módulos queden coherentes con READ/CREATE/UPDATE/DELETE.

### Rutas con `require_permission(...)`
Seguido el patrón de `modules/users/routes.py:43,54`:

| Ruta | Permiso |
|---|---|
| `contacts` GET /companies | `CONTACT_READ` |
| `contacts` POST /companies | `CONTACT_CREATE` |
| `contacts` GET "" / `/{id}` | `CONTACT_READ` |
| `contacts` POST "" | `CONTACT_CREATE` |
| `contacts` PATCH /{id} | `CONTACT_UPDATE` |
| `contacts` DELETE /{id} | `CONTACT_DELETE` |
| `pipelines` GET "" / `/{id}` / `/{id}/stages` | `PIPELINE_READ` |
| `pipelines` POST "" | `PIPELINE_CREATE` |
| `pipelines` POST `/{id}/stages` | `PIPELINE_UPDATE` |
| `opportunities` GET "" / `/{id}` | `OPPORTUNITY_READ` |
| `opportunities` POST "" | `OPPORTUNITY_CREATE` |
| `opportunities` PATCH /{id} | `OPPORTUNITY_UPDATE` |
| `opportunities` POST `/{id}/transition` | `OPPORTUNITY_CHANGE_STAGE` |
| `opportunities` DELETE /{id} | `OPPORTUNITY_DELETE` |

### Bug corregido (relacionado)
`modules/users/routes.py:43` usaba `Permission.USER_LIST`, que no existe en la enum (`AttributeError` en runtime para cualquier usuario autenticado). Corregido a `Permission.USER_READ`.

---

## 0.2 — Conectar el event bus

### `main.py`
- `create_app()` ahora instancia `bus = configure_bus()` y lo pasa a cada `register_module(app, bus)` (antes `None`).
- Añadido `lifespan` que arranca un `asyncio.create_task(_dispatch_loop())`; el loop llama `get_bus().dispatch_pending(db=SessionLocal())` cada 2 s, crea/cierra la sesión por iteración y hace `commit()`. Se cancela al apagar la app.
- **No** se suscriben handlers (Fase 2).

### Publicación de eventos (outbox, dentro de la transacción)
Los services ahora hacen `db.flush()` antes de publicar (para tener IDs) y publican antes de `commit()`, usando `get_bus().publish(..., db=self.db)`:

- `contacts/service.py`: `CompanyCreated` (create_company), `ContactCreated` (create_contact), `ContactUpdated` con `changed_fields` (update_contact).
- `pipelines/service.py`: `PipelineCreated` (create_pipeline), `StageCreated` (create_stage).
- `opportunities/service.py`: `OpportunityCreated` (create), `OpportunityStageChanged` + `OpportunityWon`/`OpportunityLost` (transition), `OpportunityDiscarded` (delete).

Se usan únicamente los modelos tipados de `core/event_bus/models.py`.

### Correcciones necesarias en el bus (bloqueantes)
- **`EventOutbox` ORM vs migración 0001**: el modelo ORM tenía `created_at`, `attempts`, `last_error` y sin `aggregate_id`; la migración crea `occurred_at`, `retries`, `error`, `aggregate_id` (NOT NULL) y `event_type` String(100). Reescrito el modelo para reflejar la migración y ajustados `publish` (calcula `aggregate_id` best-effort y usa `occurred_at`) y `dispatch_pending` (`occurred_at` para ordenar, `retries`/`error`). Sin esto, `publish` fallaba con `no such column: event_outbox.created_at`.
- **`lead_sources` sin modelo ORM**: `opportunities.source_id` tiene `ForeignKey("lead_sources.id")` pero no existía modelo `LeadSource`, por lo que el mapper ORM fallaba al resolver la FK. Añadido modelo `LeadSource` en `opportunities/domain.py` (espejo de la migración). No se añadió `lost_reasons` porque `lost_reason_id` no tiene FK (es `String(36)` plano).

---

## 0.3 — Sesión persistente (frontend)

### Backend
- `modules/users/routes.py`: `POST /users/login` ahora setea cookie `access_token` (HttpOnly, `SameSite=lax`, `secure` solo fuera de dev/test, `max_age = jwt_expire_minutes * 60`). Añadido `POST /users/logout` que limpia la cookie.
- `modules/users/auth_deps.py`: `get_current_user` acepta el token desde la cookie `access_token` además del header `Authorization`.
- **`OrgContextMiddleware`** (nuevo en `auth_deps.py`, cableado en `main.py`): fija el `ContextVar` de org en el event loop. Motivo: `get_current_user` es una dependencia sync que FastAPI ejecuta en un threadpool; el `ContextVar` seteado allí no se propagaba al endpoint (también sync, otro threadpool). Sin esto, toda ruta devolvía `403 organization_boundary`. El middleware extrae el token (header o cookie), decodifica y llama `set_org()` en el loop; cada `run_in_threadpool` copia ese contexto.

### Frontend
- `lib/api/client.ts`: ya enviaba `credentials: "include"`; se retiró la inyección del header `Authorization` desde el token en memoria (ahora la cookie es la fuente de verdad).
- `lib/api/auth.ts`: eliminado `_token`/`getToken`/`setToken`; `logout()` hace `POST /api/users/logout`; `signup()` ya no finge devolver un `AuthResponse`.
- `lib/hooks/use-auth.ts`: `AuthState` pasa a `{ user, loading, error }` (sin `session`/`access_token`). `isAuthenticated = !!user`; `refresh()` resuelve vía `authApi.me()` (cookie). Ajustados `login`/`signup`/`logout` y el return para que los consumidores (`login`, `signup`, `topbar`, `sidebar`, `auth-guard`, `dashboard`) sigan compilando.
- `src/middleware.ts` (nuevo): redirige a `/login` (con `next=`) cualquier ruta de `/(authed)` sin cookie `access_token` (solo presencia; la decodificación la hace el backend). Matcher con las rutas concretas (los segmentos de grupo `(authed)` no aparecen en la URL).
- `lib/api/documents.ts`: sin cambios (ya usaba fetch directo con `credentials: "include"`).

> Nota: `signup` sigue sin iniciar sesión (la cookie solo se setea en `/login`). Es el comportamiento preexistente (el endpoint `bootstrap` no devuelve token) y no se regresa respecto al estado previo; se documenta, no se corrige aquí por estar fuera de Fase 0.

---

## 0.4 — Secrets

- `core/config.py`: `@model_validator(mode="after")` que, si `env` no es `development`/`test` y `jwt_secret` (o `secret_key`) conserva el default inseguro, falla en startup con mensaje claro. Se usa el setting `env` ya existente.
- `.env.example`: reescrito con placeholders explícitos (`change-me-generate-...`) y comentarios por variable.

---

## 0.5 — Smoke test

`backend/scripts/smoke.py`: apunta a un SQLite **temporal** (creado en `tempfile.mkdtemp`, nunca el `.db` del proyecto), setea `DATABASE_URL`/`ENV=test` **antes** de importar la app, aplica la migración real (`alembic upgrade head`, necesario porque `lead_sources` no tenía modelo y `create_all` no bastaba), y ejecuta: bootstrap → login (assert de la cookie en el `Set-Cookie` y del body) → auth solo por cookie → contacto → pipeline + 3 etapas → oportunidad → transición a `won` → assert de filas en `event_outbox`. Imprime `SMOKE OK` o `SMOKE FAIL` con `exit != 0`.

---

## Resultados de los 4 comandos de verificación

### 1. Compilación
```
$ cd backend && .venv/Scripts/python.exe -m py_compile $(find src scripts -name '*.py')
PY_COMPILE OK (all src + scripts)
```

### 2. Tests
```
$ cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
collected 7 items
tests\test_business_rules.py ..                                          [ 28%]
tests\test_tenant_isolation.py .....                                     [100%]
============================== 7 passed in 1.53s ==============================
```
(No fue necesario adaptar tests: ahora, con el middleware de contexto, `test_create_opportunity_succeeds` resuelve por la rama `201` en vez del fallback `403`.)

### 3. Smoke
```
$ cd backend && .venv/Scripts/python.exe scripts/smoke.py
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, ...
SMOKE OK (event_outbox rows: 8)
```

### 4. Frontend typecheck
```
$ cd frontend && npx tsc --noEmit
(exit 0)
```

---

## Entorno (deuda preexistente resuelta para poder verificar)

El venv de `backend/` estaba incompleto (faltaban `passlib`, `pytest` y dependencias transitivas `typing_extensions`, `annotated_types`, etc.). Se reinstaló el proyecto y las dependencias de dev:

```
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -m pip install "passlib[bcrypt]==1.7.4" "pytest==8.3.4"
```

---

## Desviaciones del plan

1. **`EventOutbox` ORM ↔ migración** — fuera del enunciado literal, pero imprescindible para que `publish` persistiera (el brief asume que "ya persiste").
2. **`LeadSource` model** — necesario para resolver la FK de `opportunities.source_id`.
3. **`OrgContextMiddleware`** — el `ContextVar` de tenant no se propagaba de dependencia sync a endpoint; sin esto el smoke test (y en realidad toda la API autenticada) fallaba con 403.
4. **`Permission.USER_LIST` → `USER_READ`** — bug en `users/routes.py` corregido de paso.
5. **`CONTACT_DELETE`/`OPPORTUNITY_DELETE` a DIRECTOR** — asignación coherente de permisos ya existentes (no nuevos).
6. **`signup` no inicia sesión** — limitación preexistente no tocada (fuera de Fase 0).

---

## Cambios por archivo

**Backend**
- `src/core/rbac.py` — permisos pipeline CREATE/UPDATE/DELETE + asignaciones a DIRECTOR.
- `src/modules/users/routes.py` — cookie en login, `POST /logout`, fix `USER_READ`.
- `src/modules/users/auth_deps.py` — cookie en `get_current_user` + `OrgContextMiddleware`.
- `src/main.py` — `configure_bus()` + bus a módulos + dispatch loop (lifespan) + middleware.
- `src/modules/contacts/routes.py` — `require_permission` en todas las rutas.
- `src/modules/contacts/service.py` — publica `CompanyCreated`/`ContactCreated`/`ContactUpdated`.
- `src/modules/pipelines/routes.py` — `require_permission` en todas las rutas.
- `src/modules/pipelines/service.py` — publica `PipelineCreated`/`StageCreated`.
- `src/modules/opportunities/routes.py` — `require_permission` en todas las rutas.
- `src/modules/opportunities/service.py` — publica `OpportunityCreated`/`OpportunityStageChanged`/`OpportunityWon`/`OpportunityLost`/`OpportunityDiscarded`.
- `src/modules/opportunities/domain.py` — modelo `LeadSource`.
- `src/core/event_bus/event_bus.py` — `EventOutbox` alineado a la migración.
- `src/core/config.py` — validador de secrets.
- `.env.example` — placeholders documentados.
- `scripts/smoke.py` — nuevo.

**Frontend**
- `src/lib/api/client.ts` — quita header `Authorization` (cookie-based).
- `src/lib/api/auth.ts` — sin token en memoria; `logout` vía POST.
- `src/lib/hooks/use-auth.ts` — estado basado en `user`, no en token.
- `src/middleware.ts` — nuevo.
