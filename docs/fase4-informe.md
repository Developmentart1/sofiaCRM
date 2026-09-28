# Informe — Fase 4 (Endurecimiento y demo)

Proyecto: `C:\Users\migue\CRM-Splash`. Ejecutada la Fase 4 del plan (`docs/mvp-plan.md`) según el brief `docs/fase4-brief.md`. Leídos antes `docs/fase0..fase3-informe.md`. Regla de oro respetada: no se leyó ni modificó ningún `.env*`; la config se tomó de `backend/src/core/config.py` y toda verificación usó variables de entorno inline (`DATABASE_URL`/`ENV`) contra bases SQLite **temporales** (el `.db` real jamás se tocó).

---

## Resumen

Cubiertos los dos huecos reales que quedaban (tests de auth y de RBAC/tenant-isolation), renovado el seed a 2 organizaciones con reglas de automatización reales, ejecutado lint/typecheck, y reescrito `INTEGRATION_TEST.md` con el flujo E2E real (cookies, `/api/v1`, `/api/documents`). Además se **corrigieron 3 bugs latentes** de fases previas que impedían cumplir los tests de auth/RBAC (detalle en §7). Resultado: **84 tests** (39 previos + 45 nuevos) todos verdes, smoke `SMOKE OK`, `tsc --noEmit` exit 0.

---

## 1. Tests de auth (`tests/test_auth_flow.py`, 7 tests)

Ejercen el flujo de auth real (login por `/api/v1/users/login`, cookie HttpOnly, logout, cambio de contraseña, expiración de token):

1. `test_login_valid_sets_httponly_cookie` — 200 + `access_token` presente en `Set-Cookie` con `httponly` y `samesite=lax`.
2. `test_login_wrong_password_401_no_cookie` — 401 sin cookie.
3. `test_cookie_only_auth_no_authorization_header` — cookie válida sola autentica un endpoint protegido (sin header `Authorization`).
4. `test_missing_cookie_and_header_401` — sin cookie ni header → 401.
5. `test_expired_token_401` — JWT generado con `expires_minutes=-1` (misma librería/config del proyecto) → 401.
6. `test_logout_clears_cookie` — `POST /logout` limpia la cookie (header `Set-Cookie` con `Max-Age=0`/expira 1970) y una request posterior queda en 401.
7. `test_change_password_wrong_then_correct` — contraseña vieja incorrecta → 401; correcta → 200 y login funciona con la nueva (y deja de funcionar con la vieja).

Nota: la ruta real de cambio de contraseña es `POST /api/v1/users/me/password` (verificada en `modules/users/routes.py`).

## 2. Matriz RBAC (`tests/test_rbac_matrix.py`, 38 tests)

Se leyeron los roles reales de `core/rbac.py` (**5**: admin, director, gerente, asesor, operaciones). Matriz `rol × endpoint clave`, parametrizada (cada celda es un assert):

| Endpoint (permiso) | admin | director | gerente | asesor | operaciones |
|---|---|---|---|---|---|
| `POST /automations/rules` (`AUTOMATION_MANAGE`) | 201 | 201 | 403 | 403 | 403 |
| `POST /users` (`USER_CREATE`) | 201 | 403 | 403 | 403 | 403 |
| `POST /contacts` (`CONTACT_CREATE`) | 201 | 201 | 201 | 201 | 403 |
| `POST /opportunities` (`OPPORTUNITY_CREATE`) | 201 | 201 | 201 | 201 | 403 |
| `POST /pipelines` (`PIPELINE_CREATE`) | 201 | 201 | 403 | 403 | 403 |
| `GET /reports/kpis` (`REPORT_READ`) | 200 | 200 | 200 | 200 | 200 |

Más:
- `test_all_roles_401_without_auth` (6 asserts): cada endpoint clave devuelve 401 sin credenciales.
- `test_org_isolation_list_and_get`: usuario de org B (token válido) no ve contactos de org A (lista filtrada) y `GET /contacts/{id}` de org A → 404.
- `test_org_isolation_write_denied`: `PATCH /contacts/{id}` de org A con token de org B → 404.

## 3. Seed renovado (`backend/scripts/seed.py`)

Mismo estilo raw SQL (sin imports de ORM), sin romper lo existente:

- **2 organizaciones** completas (`crm-splash-demo` y `crm-splash-norte`), cada una con su pipeline (13 etapas), usuarios en roles variados (admin/director/gerente/asesor/operaciones), empresas, contactos y oportunidades.
- **3 reglas de automatización por org** (6 total), insertadas con el `config_json`/`conditions_json` exacto que el engine parsea (`modules/automations`):
  1. `opportunity.won` → `create_task` ("Onboarding de cliente", `due_offset_days=3`, `assigned_user_id` estático al asesor).
  2. `contact.created` → `create_activity` ("Bienvenida {{ event.full_name }}", demostrando el placeholder `event.*`).
  3. `opportunity.created` **con condición** `{"field":"value","op":"gt","value":100000}` → `create_task` ("Seguimiento VIP", `priority=high`).
- **Flag `--clean`**: recrea el schema (alembic `downgrade base` → `upgrade head`) antes de sembrar.

## 4. Lint y typecheck

**Backend (ruff, vía `uvx` — uv instalado, corre sin red):**
- Archivos nuevos (`test_auth_flow.py`, `test_rbac_matrix.py`, `seed.py`): **0 errores**.
- Se corrigieron los **9 imports sin uso** (`F401`) existentes en fases previas (`audit.py`, `event_bus.py`, `auth_deps.py`, `users/routes.py`, `opportunities/service.py`, `organizations/domain.py`, `reports/service.py`, `helpers.py`) — el "mínimo" que pedía el brief.
- Quedan **239** hallazgos preexistentes de estilo, todos de fases 0-3 y **ninguno de sintaxis ni de imports sin uso**: `B008` (109, el idioma `Depends(...)` de FastAPI), `I001` (39, orden de imports), `UP017` (38, `datetime.UTC`), `RUF059`, `SIM102`, `RUF100`, `BLE001`, `E402`, y 3 `F841` (variables asignadas y no usadas, sin impacto funcional). Por la regla "no reescribas código existente por estilo" **no se tocaron**.
- `python -m compileall` sobre `src/ tests/ scripts/` → `PY_COMPILE OK` (sin errores de sintaxis).

**Frontend:**
- `npx tsc --noEmit` → **exit 0**.
- `npm run lint` → **exit 0** (solo warnings preexistentes `react-hooks/exhaustive-deps` en `use-*.ts`).

## 5. `INTEGRATION_TEST.md` actualizado

El archivo citaba rutas inexistentes (`/api/auth/login`, `/api/organizations/signup`). Reescrito con el flujo real de hoy (verificado en `modules/users/routes.py` y `modules/organizations/routes.py`):
1. Bootstrap (`POST /api/v1/organizations/bootstrap`) → login (`POST /api/v1/users/login`, guarda cookie `cookies.txt`).
2. Contacto, pipeline + etapas, oportunidad; transición de etapa.
3. Regla de automatización → ganar oportunidad → verificar tarea creada y ejecución vía `/automations/executions`.
4. Subir documento (`POST /api/documents`) y descargarlo (`GET /api/documents/{id}/download`).
5. `GET /api/v1/reports/kpis`.
Incluye cómo correr `pytest` y `scripts/smoke.py`, y una sección de aislamiento entre orgs.

## 6. Verificación obligatoria (salida real)

### 1. Tests
```
$ cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
collected 84 items
tests\test_activities.py ......                                          [  7%]
tests\test_auth_flow.py .......                                          [ 15%]
tests\test_automations.py ........                                       [ 25%]
tests\test_business_rules.py ..                                          [ 27%]
tests\test_documents.py ......                                           [ 34%]
tests\test_rbac_matrix.py ......................................         [ 79%]
tests\test_reports.py ......                                             [ 86%]
tests\test_tasks.py ......                                               [ 94%]
tests\test_tenant_isolation.py .....                                     [100%]
============================= 84 passed in 5.76s ==============================
```

### 2. Seed contra DB temporal (migraciones previas + conteos reales)
```
$ DATABASE_URL=sqlite:///./_verify_seed.db ENV=test <alembic upgrade head>
$ DATABASE_URL=sqlite:///./_verify_seed.db ENV=test .venv/Scripts/python.exe scripts/seed.py
   • CRM Splash Demo (crm-splash-demo): 7 usuarios · 10 empresas · 30 contactos · 20 oportunidades · 3 reglas
   • CRM Splash Norte (crm-splash-norte): 5 usuarios · 5 empresas · 12 contactos · 8 oportunidades · 3 reglas
✅ Seed completado:
   2 organizaciones  ·  6 reglas de automatización
$ <conteos SQL>
orgs=2 rules=6 actions=6 users=12 contacts=42 opportunities=28
rules per org: [(org1, 3), (org2, 3)]
```
(El temporal `_verify_seed.db` se borró después. El `--clean` también se verificó contra otro temporal: downgrade→upgrade→seed→`orgs=2`.)

### 3. Lint backend
```
$ uvx ruff check src/ tests/ scripts/
Found 239 errors.  [*] 97 fixable with the --fix option ...
```
(239 = hallazgos de estilo preexistentes de fases 0-3; **0 imports sin uso** tras corregir los 9 F401; **0 errores de sintaxis**; archivos nuevos limpios. `ruff --select=F401` → 0. `py_compile` → OK.)

### 4. Frontend typecheck
```
$ cd frontend && npx tsc --noEmit
(exit 0)
```

### 5. Smoke
```
$ cd backend && .venv/Scripts/python.exe scripts/smoke.py
INFO ... Running upgrade  -> 0001_initial
INFO ... Running upgrade 0001_initial -> 0002_tasks_activities_gaps
INFO ... Running upgrade 0002_tasks_activities_gaps -> 0003_automation_conditions
INFO ... Running upgrade 0003_automation_conditions -> 0004_documents_folder
SMOKE OK (event_outbox rows: 13)
```

## 7. Bugs latentes de fases previas corregidos

Necesarios para que los tests de auth/RBAC pasaran (errores reales, no estilo):

1. **`modules/users/routes.py:78`** — `create_user` pasaba `current.organization_id` extra a `UserService.create(payload)`, que solo acepta `payload` → `TypeError` en `POST /users`. Corregido a `create(payload)` (el tenant ya lo aplica `UserRepository` vía `current_org_id()`).
2. **`modules/users/service.py:change_password`** — no hacía `commit`, así que el cambio de contraseña se perdía al cerrar la sesión (la ruta no lleva `@audit_log`, que es quien commitaba en otros endpoints). Añadido `self.db.commit()`.
3. **Seis `NotFoundError(entidad, id)` con aridad incorrecta** (`CRMError.__init__` solo acepta `message`) en `contacts/service.py` (×2), `opportunities/service.py` (×3) y `pipelines/service.py` (×1) → devolvían 500 en lugar de 404 al cruzar tenant. Corregidos a mensaje único (`f"{entidad} {id} not found"`), que es lo que exige el aislamiento a nivel API.

## 8. Cambios por archivo

**Backend (nuevos)**
- `tests/test_auth_flow.py` (7 tests)
- `tests/test_rbac_matrix.py` (38 tests)

**Backend (modificados)**
- `scripts/seed.py` — 2 orgs + reglas de automatización + `--clean`.
- `src/modules/users/routes.py` — fix aridad en `create_user`.
- `src/modules/users/service.py` — `commit` en `change_password`.
- `src/modules/contacts/service.py`, `src/modules/opportunities/service.py`, `src/modules/pipelines/service.py` — `NotFoundError` con mensaje único.
- `src/core/audit.py`, `src/core/event_bus/event_bus.py`, `src/modules/users/auth_deps.py`, `src/modules/users/routes.py`, `src/modules/opportunities/service.py`, `src/modules/organizations/domain.py`, `src/modules/reports/service.py`, `tests/helpers.py` — imports sin uso retirados (F401).

**Raíz**
- `INTEGRATION_TEST.md` — reescrito.

## 9. Estado final del MVP

El sistema funciona hoy de extremo a extremo: bootstrap de tenant y login con cookie HttpOnly, RBAC granular por rol en cada módulo, gestión de contactos/empresas/pipelines/oportunidades con transiciones de etapa que publican eventos, motor de automatizaciones real (reglas con condiciones y acciones `create_task`/`create_activity`/`move_stage`/`update_field`, con anti-recursión por profundidad y ciclos, dry-run y ejecuciones auditadas), tareas y actividades, documentos (subida/descarga con doble prefijo de red), reportes/KPIs agregados por tenant, y aislamiento estricto entre organizaciones verificado por tests y por el seed de 2 orgs. Quedan **fuera del MVP** (declarado en el plan): custom fields, merge de contactos, notificaciones externas (email), refresh tokens y RLS a nivel de BD. La deuda pendiente es exclusivamente de estilo de lint backend (239 hallazgos preexistentes, sin impacto funcional).
