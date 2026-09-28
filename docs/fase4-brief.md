# Tarea: CRM-Splash — Fase 4 (Endurecimiento y demo)

Proyecto: `C:\Users\migue\CRM-Splash`. Contexto: `docs/mvp-plan.md` (Fase 4) e informes `fase0..fase3-informe.md`. Estado: 39 tests pasando, 5 módulos de negocio + documents/reports/automations, bus con outbox, sesión por cookie, smoke OK.

RESTRICCIÓN: NO leas ni modifiques ningún archivo `.env*` ni ejecutes `cat/env/printenv` sobre ellos. Config de referencia en `backend/src/core/config.py`. Para cualquier comando usa variables de entorno inline (p. ej. `CRM_ENV=test`) según config.py.

## 4.1 Tests de auth y RBAC (los únicos huecos reales que quedan)
`tests/test_auth_flow.py`:
1. Login con credenciales válidas → 200 + cookie `access_token` HttpOnly presente en Set-Cookie.
2. Login con contraseña incorrecta → 401, sin cookie.
3. Request con cookie válida a endpoint protegido → 200 (sin header Authorization; la cookie basta).
4. Request sin cookie ni header → 401.
5. Token expirado (genera JWT con exp en pasado usando la misma librería/config del proyecto) → 401.
6. `POST /logout` → limpia la cookie.
7. Cambio de contraseña (`/users/me/password` o la ruta real — verifica en el código): contraseña vieja incorrecta → error; correcta → login funciona con la nueva.

`tests/test_rbac_matrix.py`:
- Construye la matrix rol × endpoint clave. Usa los roles reales de `core/rbac.py` (léelos; hay ~5: admin y otros). Para cada módulo (contacts, opportunities, tasks, automations) verifica: el rol más privilegiado puede, el rol menos privilegiado (p. ej. asesor) obtiene 403 en operaciones de gestión (crear reglas de automatización, borrar usuarios, etc.), y todos obtienen 401 sin auth. Mínimo 12 asserts en forma parametrize.
- Aislamiento entre orgs a nivel API: usuario de org B con token válido no ve ni modifica datos de org A (1-2 casos extra si no están ya cubiertos).

## 4.2 Seed renovado (`backend/scripts/seed.py`)
El seed actual usa raw SQL y 1 org. Extiéndelo (mismo estilo raw SQL, sin romper lo existente):
- **2 organizaciones** completas (cada una con su pipeline, usuarios en roles variados: admin, gerente/manager si existe, asesores).
- Contactos, empresas y oportunidades para AMBAS orgs (para demostrar aislamiento y reportes por org).
- **2-3 reglas de automatización por org**: p. ej. "oportunidad gana → crear tarea de onboarding", "contacto creado → crear actividad de bienvenida", una con condición. Insértalas con acciones coherentes con el formato real de `modules/automations` (verifica sus schemas/código antes — el formato de config_json es el que el engine parsea).
- Opcional: flag `--clean` que recrea la DB desde cero.
- Verifica: ejecuta el seed contra un SQLite TEMPORAL con nombre único (`DATABASE_URL=sqlite:///./_verify_seed.db`) + migraciones previas, y comprueba conteos (orgs=2, reglas>=4). Borra el temporal después. NUNCA toques el .db real.

## 4.3 Lint y typecheck
- Backend: ejecuta `uvx ruff check src/ tests/ scripts/` (uv está instalado en el sistema). Si hay errores, corrígelos (mínimo: imports sin uso, sintaxis). Si ruff no corre por red, usa `python -m py_compile` sobre todo y documenta la limitación. NO añadas ruff como dependencia del proyecto sin necesidad.
- Frontend: `npx tsc --noEmit` (ya debe pasar) y `npm run lint` si existe — reporta resultado real; corrige solo errores introducidos por fases previas, no reescribas código existente por estilo.

## 4.4 `INTEGRATION_TEST.md` actualizado
El archivo actual está OBSOLETO: cita rutas como `/api/auth/login` y `/api/organizations/signup` que no existen (verifica las reales en `modules/users/routes.py` y `organizations/routes.py`). Reescríbelo con el flujo E2E real de hoy, comandos copiables contra localhost:8000 (backend con uvicorn) usando cookies:
1. Signup/bootstrap de org → crear usuario → login (guardar cookie).
2. Crear contacto, pipeline, oportunidad; transición de etapa.
3. Crear regla de automatización; ganar la oportunidad; verificar tarea creada y ejecución vía `/automations/executions`.
4. Subir documento y descargarlo (ruta directa `/api/documents/{id}/download`).
5. Consultar `/reports/kpis`.
Incluye cómo correr los tests (`pytest`) y el smoke (`scripts/smoke.py`).

## 4.5 Verificación obligatoria (salida real en el informe)
1. `cd backend && .venv/Scripts/python -m pytest tests/ -q` — TODO verde (39 previos + nuevos de auth/rbac).
2. Verificación del seed contra DB temporal (conteos reales).
3. `uvx ruff check ...` o documenta la limitación.
4. `cd frontend && npx tsc --noEmit` — exit 0.
5. `cd backend && .venv/Scripts/python scripts/smoke.py` — sigue imprimiendo SMOKE OK (no debería romperse; si lo rompes, arréglalo).

## Informe
Escribe `docs/fase4-informe.md`: tests añadidos, matrix RBAC resumida, seed nuevo, resultados de lint, salida real de las 5 verificaciones, desviaciones. Al final, un párrafo "Estado final del MVP": qué puede hacer el sistema hoy de extremo a extremo y qué queda fuera.
