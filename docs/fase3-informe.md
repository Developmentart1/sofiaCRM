# Informe — Fase 3 (Documentos y Reportes reales)

Proyecto: `C:\Users\migue\CRM-Splash`. Ejecutada la Fase 3 del plan (`docs/mvp-plan.md`) según el brief `docs/fase3-brief.md`. Leídos antes `docs/fase0-informe.md`, `docs/fase1-informe.md` y `docs/fase2-informe.md`. Regla de oro respetada: **el backend se adapta al contrato del frontend** (`frontend/src/lib/types/api.ts` y clientes `documents.ts`/`reports.ts`). No se leyó ni tocó ningún `.env*`.

---

## Resumen

Implementados `modules/documents` (upload/download/list/delete con doble prefijo de red), `modules/reports` (KPIs, summary y performance por usuario con agregación SQL tenant-scoped), los tres endpoints que el dashboard ya consumía (`activities/recent`, `tasks/upcoming`, `opportunities/stuck`), la migración `0004`, y las páginas `/documents` y `/reports` reales (antes eran fachadas). Las 4 verificaciones pasan: compilación OK, **39 tests** (27 previos + 12 nuevos), smoke `SMOKE OK`, `tsc --noEmit` exit 0.

---

## 1. Doble prefijo de red en `modules/documents`

El quirk crítico del brief está confirmado en `frontend/src/lib/api/documents.ts`: `list/get/remove` van por el cliente `api` (`/api/documents` → rewrite Next.js → `/api/v1/documents`), mientras que `upload` y `downloadUrl` hacen `fetch` **directo** a `http://localhost:8000/api/documents` (sin rewrite, sin `/v1`).

Solución: `documents/routes.py` define **dos routers** que comparten las mismas funciones handler:

- `v1_router` (`prefix="/documents"`) montado en `/api/v1` → CRUD completo: `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `POST /api/v1/documents`, `GET /api/v1/documents/{id}/download`, `DELETE /api/v1/documents/{id}`.
- `direct_router` (`prefix="/documents"`) montado en `/api` → solo `POST /api/documents` y `GET /api/documents/{id}/download`.

Verificado con TestClient contra ambas rutas (`tests/test_documents.py::test_upload_download_roundtrip_both_prefixes` y smoke). El frontend **no** se modificó en su capa de API.

## 2. Alineación de puertos del rewrite

`frontend/next.config.mjs` apuntaba el fallback del rewrite a `http://localhost:8002`; el backend corre en **8000** (`core/config.py` no define puerto, `main.py` usa 8000 y `INTEGRATION_TEST.md` lo fija). Se alineó el fallback a `http://localhost:8000` (NO se tocaron `.env`; `NEXT_PUBLIC_API_URL` sigue teniendo prioridad si está definida).

---

## 3. Módulo `modules/documents`

- **Migración `0004_documents_folder`**: añade columna `folder` (String(200), nullable) a `documents`, down_revision `0003`. Verificada contra SQLite temporal `_verify_fase3.db` (ver §7).
- **`domain.py`**: modelo `Document` espejo de la tabla `documents` (0001) + `folder`. Soft delete vía `deleted_at`; todas las queries lo filtran.
- **Upload** (`POST` multipart): guarda en `{settings.storage_path}/{org_id}/{uuid}_{safe_name}` (crea directorios). Límite configurable `max_upload_size_bytes` (default 25MB → `ValidationError` 422 al exceder, borrando el archivo parcial). Valida que contact/opportunity/company pertenezcan a la misma org (404). `uploaded_by_id` = usuario actual. Publica `DocumentUploaded` al bus.
- **List** paginado con filtros del cliente (`search` por filename/safe_name, `contact_id`, `opportunity_id`, `company_id`, `folder`) → campos exactos del tipo `Document`: `name`(=filename), `size`(=size_bytes), `url`(ruta de download), `mime_type`, nombres denormalizados de contact/opportunity/company/uploader.
- **Download** `GET /{id}/download`: valida org (NUNCA cross-tenant, id de otra org → 404), sirve con `FileResponse` y `Content-Disposition` del filename original.
- **Delete**: soft delete (`deleted_at`), 204.
- **RBAC**: `DOCUMENT_READ/UPLOAD/DELETE` ya existían. Se **asignó `DOCUMENT_DELETE` a `DIRECTOR`** (antes solo `ADMIN`), coherente con `CONTACT_DELETE`/`OPPORTUNITY_DELETE`.

## 4. Módulo `modules/reports` (solo lectura, agregación SQL tenant-scoped)

Rutas (todas `REPORT_READ`, permiso **nuevo** asignado a todos los roles: admin/director/gerente/asesor/operaciones):

- `GET /api/v1/reports/kpis` → `DashboardKPIs` con los **14 campos** exactos del tipo del frontend (ver nota en §9 sobre "15 campos"). Todo con `func()` de SQLAlchemy, sin cargar tablas en Python.
- `GET /api/v1/reports/summary?from&to&pipeline_id` → `ReportSummary`: `total_revenue` (ganadas en rango), `revenue_by_pipeline`, `revenue_by_owner`, `conversion_by_stage`, `period_start/end`.
- `GET /api/v1/reports/performance?from&to` → `UserPerformance[]` por usuario de la org (agregaciones agrupadas por usuario, no per-user round-trips).

### Fórmulas (documentadas)

- `conversion_rate = won / (won + lost)`, `0.0` si el denominador es 0.
- `average_deal_size = won_opportunities_value / won_opportunities_count`, `0.0` si no hay ganadas.
- `pipeline_velocity = (Σ won_value de ganadas en los últimos 30 días) / 30` → **ingreso ganado diario promedio** (ventana rodante de 30 días). Fórmula simple y positiva, documentada.
- "este mes" = mes calendario UTC actual (para `contacts_added_this_month` y `opportunities_won_this_month`).
- `won_value` se resuelve con `COALESCE(won_value, estimated_value)`.
- Rango por defecto de summary/performance cuando no llega `from`/`to`: últimos 30 días.

## 5. Endpoints que el dashboard ya consumía (añadidos a los módulos existentes)

- `GET /api/v1/activities/recent?limit` → últimas activities de la org (`list_recent`, orden `occurred_at` desc).
- `GET /api/v1/tasks/upcoming?limit` → tareas `pending/in_progress` con `due_date >= hoy`, ordenadas por vencimiento ascendente. Registrada **antes** de `GET /{task_id}` para no ser absorbida por el path param.
- `GET /api/v1/opportunities/stuck?days=14` → abiertas sin cambio de etapa hace > `days` días. Umbral constante `14` (default y query param). Usa `COALESCE(entered_stage_at, created_at)` < ahora − N días. Registrada **antes** de `GET /{opp_id}`.

## 6. Cambios de soporte

- `core/config.py`: `max_upload_size_bytes` (default `25 * 1024 * 1024`).
- `core/rbac.py`: `REPORT_READ = "report:read"` + asignación a los 5 roles; `DOCUMENT_DELETE` a `DIRECTOR`.
- `main.py`: registra `documents` y `reports`.
- `tests/conftest.py`: `STORAGE_ROOT` apuntado a un directorio temporal (los tests de documentos escriben en storage temporal, nunca en `backend/storage`).
- `scripts/smoke.py`: `STORAGE_ROOT` temporal + flujo de documentos (subir→listar→descargar por ambas rutas→assert de bytes) y fetch de KPIs (assert de estructura completa).

## 7. Verificación (salida real)

### 1. Compilación
```
$ cd backend && .venv/Scripts/python.exe -m py_compile <todos los .py tocados>
PY_COMPILE OK
```

### 2. Tests
```
$ cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
collected 39 items
tests\test_activities.py ......                                          [ 15%]
tests\test_automations.py ........                                       [ 35%]
tests\test_business_rules.py ..                                          [ 41%]
tests\test_documents.py ......                                           [ 56%]
tests\test_reports.py ......                                             [ 71%]
tests\test_tasks.py ......                                               [ 87%]
tests\test_tenant_isolation.py .....                                     [100%]
============================= 39 passed in 3.07s ==============================
```
(27 previos + 12 nuevos; ningún test existente necesitó adaptación.)

### 3. Smoke
```
$ cd backend && .venv/Scripts/python.exe scripts/smoke.py
INFO ... Running upgrade  -> 0001_initial
INFO ... Running upgrade 0001_initial -> 0002_tasks_activities_gaps
INFO ... Running upgrade 0002_tasks_activities_gaps -> 0003_automation_conditions
INFO ... Running upgrade 0003_automation_conditions -> 0004_documents_folder
SMOKE OK (event_outbox rows: 13)
```

### 4. Frontend typecheck
```
$ cd frontend && npx tsc --noEmit
(exit 0)
```
(`npm run lint` también sale con exit 0; solo warnings preexistentes de `react-hooks/exhaustive-deps` en `use-*.ts`, ninguno en los archivos nuevos.)

### Migración 0004 (verificación en SQLite temporal `_verify_fase3.db`)
```
documents columns: 14
[... 'filename', 'safe_name', 'mime_type', 'size_bytes', 'storage_path', 'created_at', 'deleted_at', 'folder']
folder present: True
```

---

## 8. Tests nuevos (12)

`tests/test_documents.py` (6):
1. `test_upload_download_roundtrip_both_prefixes` — sube por `/api/documents`, lista por `/api/v1`, descarga por `/api/documents/{id}/download` **y** `/api/v1/documents/{id}/download` (assert de bytes).
2. `test_download_tenant_isolation` — org B pide doc de org A → 404, y no aparece en su list.
3. `test_soft_delete_hides_and_blocks_download` — delete 204 → no aparece en list y download 404.
4. `test_upload_size_limit` — con `max_upload_size_bytes=20` (monkeypatch), archivo mayor → 422.
5. `test_upload_rejects_cross_tenant_contact` — subir con `contact_id` de otra org → 404.
6. `test_list_filters_by_folder_and_search` — filtros `folder` y `search`.

`tests/test_reports.py` (6):
1. `test_kpis_exact_values` — asserts de **valores exactos** (no rangos) de los 14 KPIs con seed conocido.
2. `test_summary_with_range_filter` — total_revenue y agrupaciones acotadas por `from`/`to`.
3. `test_performance_by_user` — métricas exactas por usuario (2 usuarios, uno sin actividad → ceros).
4. `test_recent_activities_endpoint` — `activities/recent` devuelve la más reciente primero.
5. `test_upcoming_tasks_endpoint` — excluye vencidas y completadas.
6. `test_stuck_opportunities_endpoint` — solo abiertas con `entered_stage_at` viejo.

---

## 9. Desviaciones / decisiones destacadas

1. **"15 campos" → 14**: el brief menciona "15 campos" para `DashboardKPIs` pero lista 14, y el tipo del frontend (`DashboardKPIs`) tiene exactamente **14**. Se implementaron los 14 del contrato; el smoke asevera esas 14 keys.
2. **`DOCUMENT_DELETE` a `DIRECTOR`** (antes solo admin), coherente con el patrón de DELETE de contacts/opportunities.
3. **`pipeline_velocity`** definida como ingreso ganado diario promedio (últimos 30 días), fórmula simple documentada en §4 (el brief dejaba la fórmula a criterio).
4. **Umbral de `stuck`** = 14 días (constante default + query param `days`).
5. **`url` del `Document`** = `/api/documents/{id}/download` (ruta canónica de download); la página `/documents` usa ese campo para el enlace de descarga (evita consumir `downloadUrl`, que es `async`/`Promise<string>`).
6. **"este mes" en UTC**: consistente con el resto del backend (tasks/activities usan `datetime.now(timezone.utc)`). Los tests de reports usan la misma referencia UTC para ser deterministas.
7. **`conversion_by_stage`** = para cada etapa con oportunidades `open`/`won`, `count` = oportunidades en la etapa y `conversion_rate` = ganadas en esa etapa / count (guard de división por cero). No acotado por `from`/`to` (distribución actual del pipeline).
8. **Rango por defecto** de summary/performance = últimos 30 días (el dashboard llama `performanceByUser({})` sin fechas).
9. **Frontend**: páginas `/documents` y `/reports` implementadas como componentes reales (antes fachadas); `next.config.mjs` alineado a 8000. No se tocaron `documents.ts`/`reports.ts`.

---

## 10. Cambios por archivo

**Backend (nuevos)**
- `migrations/versions/0004_documents_folder.py`
- `src/modules/documents/{__init__,domain,schemas,service,routes}.py`
- `src/modules/reports/{__init__,schemas,service,routes}.py`
- `tests/test_documents.py`, `tests/test_reports.py`

**Backend (modificados)**
- `src/core/config.py` — `max_upload_size_bytes`.
- `src/core/rbac.py` — `REPORT_READ` + asignaciones; `DOCUMENT_DELETE` a DIRECTOR.
- `src/main.py` — registro de `documents` y `reports`.
- `src/modules/activities/{service,routes}.py` — `GET /recent`.
- `src/modules/tasks/{service,routes}.py` — `GET /upcoming`.
- `src/modules/opportunities/{service,routes}.py` — `GET /stuck`.
- `scripts/smoke.py` — flujo de documentos + KPIs + `STORAGE_ROOT` temporal.
- `tests/conftest.py` — `STORAGE_ROOT` temporal.

**Frontend (modificados)**
- `next.config.mjs` — fallback del rewrite 8002 → 8000.
- `src/app/(authed)/documents/page.tsx` — página real (list/upload/download/delete).
- `src/app/(authed)/reports/page.tsx` — página real (KPIs, ingresos por pipeline/owner, desempeño).
