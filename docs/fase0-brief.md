# Tarea: CRM-Splash — Fase 0 (Cimientos críticos)

Proyecto: `C:\Users\migue\CRM-Splash`. CRM multi-tenant: FastAPI+SQLAlchemy en `backend/src`, Next.js App Router en `frontend/src`. Lee `docs/mvp-plan.md` para contexto general, y `docs/audit-claude.md` para el estado actual.

Ejecuta SOLO la Fase 0 del plan. No toques fases posteriores. Convenciones existentes obligatorias: módulos se registran vía `register_module(app, bus)`; services usan `current_org_id()` de `core/tenant.py`; errores vía subclases de `CRMError` (`core/errors.py`).

## 0.1 RBAC en rutas
- Revisa `backend/src/core/rbac.py`: garantiza permisos para contacts, pipelines y opportunities (READ/CREATE/UPDATE/DELETE por módulo; créalos si faltan y asígnalos a los roles existentes de forma coherente con los que ya tienen USER/ORG).
- Añade `require_permission(...)` en TODAS las rutas de `modules/contacts/routes.py`, `modules/pipelines/routes.py`, `modules/opportunities/routes.py`. Sigue el patrón exacto de `modules/users/routes.py:43,54`.

## 0.2 Conectar el event bus
- En `backend/src/main.py`: crea el bus con `configure_bus()` de `core/event_bus` y pásalo a cada `register_module(app, bus)` (hoy reciben `None`).
- Publica eventos reales dentro de la transacción en los services (usa el outbox — `SyncEventBus.publish` ya persiste): mínimo `ContactCreated`/`ContactUpdated`, `OpportunityCreated`/`OpportunityStageChanged`/`OpportunityWon`/`OpportunityLost`, y los equivalentes de pipelines si aplica. Usa los modelos tipados de `core/event_bus/models.py` (NO inventes tipos nuevos).
- Arranca el despacho: en startup de la app, un loop/task que llame `dispatch_pending` periódicamente (intervalo corto, p. ej. 2s; implementación simple con asyncio task, suficiente para MVP). Si el patrón existente del bus requiere una session por llamada, créala correctamente y ciérrala.
- NO suscribas handlers nuevos todavía (eso es Fase 2). Solo publicar + despachar outbox.

## 0.3 Sesión persistente (frontend)
- Backend: en `modules/users` login, además del body actual, setea cookie HttpOnly `access_token` con el JWT (SameSite=lax, max-age = expiración del token). Añade `POST /logout` que limpia la cookie. El middleware de autenticación actual debe aceptar la cookie como fuente del token (además del header, para no romper nada).
- Frontend: `frontend/src/lib/api/client.ts` debe enviar `credentials: "include"`. `frontend/src/lib/hooks/use-auth.ts`: elimina el estado del token en memoria como fuente de verdad; tras el login la sesión la mantiene la cookie. Añade middleware Next.js (`frontend/src/middleware.ts`) que redirija a `/login` cualquier ruta bajo `/(authed)` si no hay cookie `access_token` (validación de presencia, la decodificación la hace el backend). Ajusta `AuthState` y consumidores para que sigan compilando.
- Nota: hay un cliente `documents.ts` que usa fetch directo con `credentials: "include"` — déjalo como está.

## 0.4 Secrets
- `backend/.env.example` con placeholders documentados. En `core/config.py`: si el entorno no es dev/test y `jwt_secret` es el valor por defecto, la app debe fallar en startup con mensaje claro. Si hay un `environment`/`debug` setting, úsalo; si no, añade uno simple.

## 0.5 Smoke test
- Crea `backend/scripts/smoke.py`: contra un SQLite TEMPORAL (nunca el .db existente del proyecto): bootstrap org → crear usuario → login (assert cookie presente en la respuesta) → crear contacto → pipeline + etapas → oportunidad → transición de etapa → verificar que la tabla `event_outbox` tiene filas. Print final `SMOKE OK` o exit != 0 con el fallo.

## Verificación obligatoria antes de terminar (hazlo tú y muestra la salida real)
1. `cd backend && python -m py_compile $(git ls-files 'backend/src/*.py')` o compilación equivalente de todos los .py tocados.
2. `cd backend && python -m pytest tests/ -q` — debe pasar (si un test existente queda obsoleto por el cambio de cookie/RBAC, adáptalo mínimamente y explica por qué).
3. `cd backend && python scripts/smoke.py` — debe imprimir SMOKE OK.
4. `cd frontend && npx tsc --noEmit` — debe salir 0.

## Informe
Escribe `docs/fase0-informe.md`: cambios por archivo, decisiones, resultados de los 4 comandos de verificación (salida real), y cualquier desviación del plan. Responde al final con un resumen corto.
