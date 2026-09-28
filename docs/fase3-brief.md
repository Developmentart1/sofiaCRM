# Tarea: CRM-Splash — Fase 3 (Documentos y Reportes reales)

Proyecto: `C:\Users\migue\CRM-Splash`. Contexto: `docs/mvp-plan.md` (Fase 3) y los informes `fase0-informe.md`, `fase1-informe.md`, `fase2-informe.md`. El objetivo: que las páginas `/documents`, `/reports` y `/dashboard` consuman datos reales — cero fachadas al terminar esta fase.

RESTRICCIÓN: NO leas ni modifiques ningún archivo `.env*` (`backend/.env`, `frontend/.env.local`, etc.) ni ejecutes `cat/env/printenv` sobre ellos — están fuera de tu alcance y cualquier intento aborta la sesión. Toda la configuración que necesitas:
- Backend: `backend/src/core/config.py` (léelo; defaults: `database_url=sqlite:///./crm_splash.db`, `storage_root=./storage`, `cors_origins=http://localhost:3000`). Puerto canónico del backend: **8000** (ver `INTEGRATION_TEST.md`).
- Frontend: el rewrite en `frontend/next.config.mjs` usa `${NEXT_PUBLIC_API_URL || "http://localhost:8002"}`; `frontend/src/lib/api/documents.ts` usa `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`. El desajuste 8000/8002 se resuelve alineando el fallback del rewrite a 8000 (NO tocando archivos .env).
- Para tests/smoke: usa variables de entorno inline (p. ej. `CRM_ENV=test`, `DATABASE_URL=sqlite:///./_verify_fase3.db`) según los nombres que defina config.py.

**Regla de oro: el backend se adapta al contrato del frontend.** Contratos canónicos en `frontend/src/lib/types/api.ts` (`Document`, `DashboardKPIs`, `UserPerformance`, `ReportSummary`) y clientes en `frontend/src/lib/api/documents.ts` y `reports.ts`.

## QUIRK CRÍTICO de documentos (verificado en el código)
`frontend/src/lib/api/documents.ts` usa DOS rutas de red distintas:
- `list/get/remove` van por el cliente `api` (`/api/documents` → rewrite Next.js → backend `/api/v1/documents`).
- `upload` y `downloadUrl` hacen fetch DIRECTO a `http://localhost:8000/api/documents` y `.../api/documents/{id}/download` (sin rewrite, sin `/v1`).

→ El módulo documents debe servir en AMBOS prefijos: registra el router con `prefix="/api/v1"` para CRUD y además monta upload (`POST /api/documents`) y download (`GET /api/documents/{id}/download`) bajo `prefix="/api"`. Verifícalo con TestClient contra ambas rutas. No modifiques el frontend salvo que sea estrictamente necesario.

Además verifica `frontend/next.config.mjs`: el rewrite apunta a `${NEXT_PUBLIC_API_URL || "http://localhost:8002"}` mientras el backend usa por defecto otro puerto (revisa `core/config.py`). Si hay desajuste real, alinea el default del rewrite al puerto real del backend y documéntalo en el informe.

## 1. Módulo `modules/documents`
- Migración `0004_documents_folder`: añade columna `folder` (String(200), nullable) a `documents`. Verifica contra SQLite TEMPORAL de nombre único (`_verify_fase3.db`), nunca el .db real.
- `domain.py`: modelo `Document` sobre la tabla existente (soft delete vía `deleted_at`; todas las queries lo filtran).
- Upload: multipart (`UploadFile`), guarda en `{settings.storage_path}/{org_id}/{uuid}_{safe_name}` (usa `settings.storage_root` de config; crea directorios). Límite de tamaño configurable (default 25MB → error 413/422 con CRMError). Valida que contact/opportunity/company referenciados pertenezcan a la misma org. `uploaded_by_id` = usuario actual. Publica `DocumentUploaded` al bus.
- List paginado con filtros del cliente frontend (`search` por filename, `contact_id`, `opportunity_id`, `company_id`, `folder`) → respuesta con campos del tipo `Document` del frontend: `name` (=filename), `size` (=size_bytes), `url` (ruta de download), nombres denormalizados de contact/opportunity/company/uploader.
- Download `GET /{id}/download`: valida que el documento es de la org del usuario actual (NUNCA servir cross-tenant, ni siquiera con id válido de otra org), sirve el archivo con `FileResponse` y content-disposition del filename original.
- Delete: soft delete (`deleted_at`), 204. Permiso RBAC: usa/crea `DOCUMENT_READ`, `DOCUMENT_UPLOAD`, `DOCUMENT_DELETE` (ya existen en rbac.py según la auditoría — verifica y asigna a roles).

## 2. Módulo `modules/reports` (solo lectura, agregaciones SQL tenant-scoped)
Rutas (todas con `require_permission`, permiso nuevo `REPORT_READ` asignado a roles):
- `GET /api/v1/reports/kpis` → `DashboardKPIs` exacto del frontend (15 campos: total_contacts, total_companies, total_opportunities, open_opportunities_value, won_opportunities_value, won_opportunities_count, lost_opportunities_count, conversion_rate, average_deal_size, pipeline_velocity, overdue_tasks, tasks_due_today, contacts_added_this_month, opportunities_won_this_month). conversion_rate = won/(won+lost) con guard de división por cero. pipeline_velocity: defínela de forma simple y documentada (p. ej. valor ganado / días del periodo o avg días para ganar) — documenta la fórmula en el informe.
- `GET /api/v1/reports/summary?from&to&pipeline_id` → `ReportSummary`: total_revenue (ganadas en rango), revenue_by_pipeline, revenue_by_owner, conversion_by_stage, period_start/end.
- `GET /api/v1/reports/performance?from&to` → `UserPerformance[]` por usuario de la org.
- Todo con SQL agregado (func() de SQLAlchemy), sin cargar tablas enteras en Python.

## 3. Endpoints faltantes que el dashboard ya consume (verificado en `reports.ts`)
- `GET /api/v1/activities/recent?limit` → últimas activities de la org (ya existe el módulo activities).
- `GET /api/v1/tasks/upcoming?limit` → tareas pending/in_progress con due_date >= hoy, ordenadas por vencimiento.
- `GET /api/v1/opportunities/stuck` → oportunidades abiertas sin cambio de etapa hace > N días (usa `stage_entered_at` o equivalente del modelo; define el umbral como constante, default 14 días).
Añádelos en los módulos existentes respetando sus patrones y RBAC.

## 4. Tests nuevos
`tests/test_documents.py`: upload+download roundtrip (archivo real en storage temporal), aislamiento tenant en download (org B pide doc de org A → 404/403), soft delete no aparece en list, límite de tamaño.
`tests/test_reports.py`: KPIs correctos con datos seed conocidos (assert de valores exactos, no rangos), summary con filtro de rango, performance por usuario, recent/upcoming/stuck.
Mínimo 10 tests nuevos.

## 5. Verificación obligatoria (salida real en el informe)
1. Compila todos los .py tocados.
2. `cd backend && .venv/Scripts/python -m pytest tests/ -q` — TODO verde (27 previos + nuevos).
3. Amplía `scripts/smoke.py`: subir documento (bytes reales) → listar → descargar por ambas rutas (`/api/documents/{id}/download` directo Y vía `/api/v1`) → assert del contenido; fetch de KPIs → assert de estructura completa. Debe seguir imprimiendo SMOKE OK.
4. `cd frontend && npx tsc --noEmit` — exit 0.

## Informe
Escribe `docs/fase3-informe.md`: decisiones (doble prefijo, fórmula de pipeline_velocity, umbral stuck, alineación de puertos del rewrite), archivos, salida real de las 4 verificaciones, desviaciones.
