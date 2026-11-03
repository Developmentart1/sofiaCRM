# Plan de Reparación CRM-Splash — Cline

## Estado actual
- ✅ 90 tests passing (84 originales + 6 nuevos)
- ✅ Mutation score 100% en rbac.py, reports/service.py, users/service.py
- ✅ Dead code eliminado (base query en summary)
- ✅ pipeline/distribution y pipeline/trend corregidos
- ⚠️ Login 404 pendiente de confirmar (¿era dev server stale?)

## Tarea 1: Verificar login end-to-end

El usuario reportó "Error 404" al hacer login. El dev server fue reiniciado con
cache limpio. Verificar que el flujo completo funciona:

1. Abrir http://localhost:3000/login
2. Llenar: slug=`crm-splash-demo`, email=`admin@crmsplash.mx`, pass=`Demo1234!`
3. Click "Ingresar"
4. Debe redirigir a /dashboard sin errores

Si falla, revisar:
- `frontend/src/lib/api/auth.ts` — el POST a `/api/users/login`
- `frontend/next.config.mjs` — el rewrite a `http://localhost:8000/api/v1/users/login`
- Backend logs en terminal

## Tarea 2: Verificar dashboard con datos reales

Después del login, verificar que:
1. Los KPIs muestran datos reales (no 0s)
2. El gráfico "Actividad del pipeline" muestra datos (no vacío)
3. El gráfico "Oportunidades por etapa" muestra las 13 etapas
4. Las pestañas de contactos (activities, tasks, etc.) funcionan

Endpoints que debe llamar el frontend:
- GET /api/reports/kpis
- GET /api/reports/pipeline/trend?days=7
- GET /api/reports/pipeline/distribution
- GET /api/activities/recent
- GET /api/tasks/upcoming
- GET /api/opportunities/stuck

## Tarea 3: Verificar sub-recursos de contacts

Navegar a un contacto y verificar que las pestañas cargan:
- GET /api/contacts/{id}/activities
- GET /api/contacts/{id}/tasks
- GET /api/contacts/{id}/opportunities
- GET /api/contacts/{id}/documents

## Tarea 4: Tests de integración

Ejecutar la suite completa y verificar:
- 90 tests passing
- Mutation score 100% en los 3 módulos críticos
- Sin warnings de deprecation

## Comandos útiles

```bash
# Backend
cd backend && .venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir src

# Frontend
cd frontend && npm run dev

# Tests
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q

# Login test
curl -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"organization_slug":"crm-splash-demo","email":"admin@crmsplash.mx","password":"Demo1234!"}'
```

## Archivos clave
- `backend/src/modules/reports/service.py` — pipeline_trend, pipeline_distribution
- `backend/src/modules/contacts/routes.py` — sub-recursos
- `frontend/src/lib/api/auth.ts` — login
- `frontend/src/app/login/page.tsx` — formulario
- `frontend/src/app/(authed)/dashboard/page.tsx` — dashboard
- `backend/tests/test_reports.py` — tests de boundary (freezegun)
