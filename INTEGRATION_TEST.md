# CRM-Splash — Test de Integración E2E (actualizado Fase 4)

> Flujo real de extremo a extremo contra el backend en `http://localhost:8000`
> usando **cookies HttpOnly** (el login ya no va por `/api/auth/login` ni el
> alta por `/api/organizations/signup`). Todas las rutas de la API viven bajo
> `/api/v1/...`, excepto la subida/descarga de documentos que usan el prefijo
> directo `/api/documents` (lo que el frontend consume sin rewrite).

## Prerrequisitos

```bash
cd backend
.venv\Scripts\activate          # Windows  (o: source .venv/bin/activate)
alembic upgrade head
python scripts/seed.py          # opcional: 2 orgs demo + reglas de automatización
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

En otra terminal, verificar salud:

```bash
curl -s http://localhost:8000/api/health
# → {"status":"ok","version":"1.0.0"}
```

Los comandos de abajo asumen `jq` para extraer IDs (si no lo tienes, copia el
`id` manualmente de cada respuesta). Las cookies se guardan en `cookies.txt`.

---

## 1. Bootstrap de organización + login (guarda la cookie)

```bash
BASE=http://localhost:8000

# 1a. Crear tenant + primer admin (el único endpoint público de alta)
curl -s -X POST $BASE/api/v1/organizations/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo E2E",
    "slug": "demo-e2e",
    "timezone": "America/Mexico_City",
    "currency": "MXN",
    "locale": "es-MX",
    "admin_email": "admin@demo.mx",
    "admin_password": "Demo1234!",
    "admin_full_name": "Admin Demo"
  }' | jq .

# 1b. Login → establece la cookie `access_token` (HttpOnly) en cookies.txt
curl -s -X POST $BASE/api/v1/users/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"organization_slug":"demo-e2e","email":"admin@demo.mx","password":"Demo1234!"}' | jq .

# La cookie basta para autenticar (no hace falta header Authorization):
curl -s -b cookies.txt $BASE/api/v1/contacts | jq .
```

## 2. Contacto, pipeline y oportunidad; transición de etapa

```bash
BASE=http://localhost:8000

CONTACT_ID=$(curl -s -X POST $BASE/api/v1/contacts \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"first_name":"Juan","last_name":"Pérez","email":"juan@demo.mx"}' | jq -r .id)

PIPELINE_ID=$(curl -s -X POST $BASE/api/v1/pipelines \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"name":"Ventas E2E"}' | jq -r .id)

# Etapas: open / won / lost
STAGE_OPEN=$(curl -s -X POST $BASE/api/v1/pipelines/$PIPELINE_ID/stages \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"name":"Abierta","stage_type":"open","probability":20,"position":1}' | jq -r .id)
STAGE_WON=$(curl -s -X POST $BASE/api/v1/pipelines/$PIPELINE_ID/stages \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"name":"Ganada","stage_type":"won","probability":100,"position":2}' | jq -r .id)

OPP_ID=$(curl -s -X POST $BASE/api/v1/opportunities \
  -H "Content-Type: application/json" -b cookies.txt \
  -d "{\"pipeline_id\":\"$PIPELINE_ID\",\"stage_id\":\"$STAGE_OPEN\",\"name\":\"Oportunidad E2E\",\"estimated_value\":150000,\"contact_id\":\"$CONTACT_ID\"}" | jq -r .id)
```

## 3. Regla de automatización → ganar oportunidad → verificar ejecución

```bash
BASE=http://localhost:8000

# Regla: al ganar (opportunity.won) → crear tarea de onboarding
RULE_ID=$(curl -s -X POST $BASE/api/v1/automations/rules \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{
    "name": "Onboarding al ganar",
    "trigger_event": "opportunity.won",
    "actions": [{"action_type":"create_task","config":{"title":"Onboarding post-venta","due_offset_days":3}}]
  }' | jq -r .id)

# Ganar la oportunidad (transición a la etapa ganada)
curl -s -X POST $BASE/api/v1/opportunities/$OPP_ID/transition \
  -H "Content-Type: application/json" -b cookies.txt \
  -d "{\"stage_id\":\"$STAGE_WON\"}" | jq .

# La tarea de onboarding se creó automáticamente
curl -s -b cookies.txt "$BASE/api/v1/tasks?opportunity_id=$OPP_ID" | jq .

# Ejecución registrada como success
curl -s -b cookies.txt "$BASE/api/v1/automations/executions?rule_id=$RULE_ID" | jq .
```

## 4. Documentos: subir y descargar (ruta directa `/api/documents`)

```bash
BASE=http://localhost:8000

echo "documento de prueba" > demo.txt

# Subida directa (sin /v1), multipart
DOC_ID=$(curl -s -X POST $BASE/api/documents \
  -b cookies.txt \
  -F "file=@demo.txt;type=text/plain" \
  -F "folder=e2e" \
  -F "opportunity_id=$OPP_ID" | jq -r .id)

# Descarga directa
curl -s -b cookies.txt $BASE/api/documents/$DOC_ID/download

# El listado (que sí va por /v1) debe incluir el documento
curl -s -b cookies.txt $BASE/api/v1/documents | jq .
```

## 5. Reportes / KPIs

```bash
curl -s -b cookies.txt $BASE/api/v1/reports/kpis | jq .
curl -s -b cookies.txt $BASE/api/v1/reports/summary | jq .
curl -s -b cookies.txt $BASE/api/v1/reports/performance | jq .
```

---

## Aislamiento entre organizaciones (crítico)

Bootstrap de una segunda org y verificar que **no ve** los datos de la primera:

```bash
BASE=http://localhost:8000

curl -s -X POST $BASE/api/v1/organizations/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo B","slug":"demo-b","admin_email":"admin@demob.mx","admin_password":"Demo1234!","admin_full_name":"Admin B"}' > /dev/null

curl -s -X POST $BASE/api/v1/users/login \
  -H "Content-Type: application/json" -c cookies_b.txt \
  -d '{"organization_slug":"demo-b","email":"admin@demob.mx","password":"Demo1234!"}' > /dev/null

# Org B no tiene contactos de Org A → lista vacía
curl -s -b cookies_b.txt $BASE/api/v1/contacts | jq .
# → []
```

---

## Tests y smoke

```bash
# Tests (usar el venv del backend; nunca toca la DB real, usa SQLite temporal)
cd backend && .venv\Scripts\python -m pytest tests/ -q

# Smoke E2E (DB temporal + flujo completo, imprime "SMOKE OK")
cd backend && .venv\Scripts\python scripts/smoke.py

# Frontend
cd frontend && npx tsc --noEmit && npm run lint
```

## Si algo falla

1. Confirmar que el backend corre en el puerto 8000 (`curl $BASE/api/health`).
2. Revisar que `alembic upgrade head` corrió contra la misma DB que usa uvicorn.
3. Si el login devuelve 401, verificar `organization_slug` (no `email` global) y
   que el usuario existe en esa organización.
