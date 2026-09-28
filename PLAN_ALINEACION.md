# Plan de Alineación CRM-Splash
> Objetivo: Resolver los gaps críticos entre frontend y backend para lograr una demo E2E funcional.
> Base: 84 tests verdes, backend sólido, frontend con desconexiones de schema y endpoints faltantes.

---

## Contexto

### Estado actual verificado (2026-08-26)
- **Backend**: 10 módulos completos (users, orgs, contacts, pipelines, opportunities, tasks, activities, automations, documents, reports)
- **RBAC**: Enforceado en todas las rutas con `require_permission()`
- **Event bus**: Conectado con outbox pattern y dispatch loop
- **Tests**: 84/84 passing (9 archivos de test)
- **Seed**: 2 organizaciones con reglas de automatización reales
- **Frontend**: Next.js 14 + Tailwind 4 + Radix UI + React Hook Form + Zod v3

### Gaps críticos identificados

| # | Gap | Archivos afectados | Prioridad |
|---|---|---|---|
| 1 | Schemas frontend↔backend no coinciden | `frontend/src/lib/types/api.ts` vs `backend/src/modules/*/schemas.py` | **P0** |
| 2 | Login hardcodeado a org demo | `frontend/src/lib/api/auth.ts:16` | **P0** |
| 3 | Sub-recursos sin backend | `frontend/src/lib/api/contacts.ts` (6 endpoints) | **P0** |
| 4 | Dashboard con datos fake | `frontend/src/app/(authed)/dashboard/page.tsx:27-40` | **P1** |
| 5 | Lint backend (estilo) | `backend/src/**/*.py` | **P2** |

---

## Fase 0 — Preparación (15 min)

### 0.1 Crear entorno de trabajo
```bash
# En C:\Users\migue\CRM-Splash
cd backend
# Verificar que el venv funciona
.venv\Scripts\python.exe -c "import sys; print(sys.version)"

cd ../frontend
# Verificar npm
npm --version
```

### 0.2 Verificar estado actual
```bash
# Backend tests
cd backend
.venv\Scripts\python.exe -m pytest tests/ -q

# Frontend typecheck
cd ../frontend
npx tsc --noEmit
```

---

## Fase 1 — Alinear Schemas (P0, 2-3 horas)
> **Objetivo**: Hacer que los tipos TypeScript del frontend coincidan exactamente con los schemas Pydantic del backend.

### 1.1 Extraer todos los schemas del backend
```bash
cd backend
# Listar todos los schemas
find src -name "schemas.py" -type f
```

Archivos a revisar:
- `backend/src/modules/users/schemas.py` → User, UserCreate, UserRead
- `backend/src/modules/organizations/schemas.py` → Organization, OrganizationCreate, OrganizationRead
- `backend/src/modules/contacts/schemas.py` → Contact, ContactCreate, ContactRead, ContactUpdate, Company, CompanyCreate, CompanyRead
- `backend/src/modules/pipelines/schemas.py` → Pipeline, PipelineCreate, PipelineRead, Stage, StageCreate, StageRead
- `backend/src/modules/opportunities/schemas.py` → Opportunity, OpportunityCreate, OpportunityRead, OpportunityUpdate, StageTransition
- `backend/src/modules/tasks/schemas.py` → Task, TaskCreate, TaskRead, TaskUpdate, TaskFilters
- `backend/src/modules/activities/schemas.py` → Activity, ActivityCreate, ActivityRead, ActivityFilters
- `backend/src/modules/documents/schemas.py` → Document, DocumentCreate, DocumentRead, DocumentFilters
- `backend/src/modules/automations/schemas.py` → AutomationRule, AutomationRuleCreate, AutomationRuleRead, AutomationAction, AutomationActionSpec, AutomationExecution, AutomationExecutionRead, AutomationTestResult
- `backend/src/modules/reports/schemas.py` → KpiResponse, ReportSummary, UserPerformance

### 1.2 Mapear diferencias críticas

#### UserRole
```diff
# FRONTEND (actual)
export type UserRole = "admin" | "manager" | "member" | "viewer";

# BACKEND (actual)
class Role(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    GERENTE = "gerente"
    ASESOR = "asesor"
    OPERACIONES = "operaciones"
```

**Solución**: Alinear frontend con backend (5 roles reales).

#### OpportunityCreate
```diff
# FRONTEND (actual)
export interface OpportunityCreate {
  name: string;
  amount: number;           # ❌
  currency?: string;
  pipeline_id: UUID;
  stage_id: UUID;
  expected_close_date?: ISODateString | null;
  contact_id?: UUID | null;
  company_id?: UUID | null;
  owner_id?: UUID | null;
  description?: string | null;
}

# BACKEND (actual)
class OpportunityCreate(BaseModel):
    name: str
    estimated_value: float  # ✅
    currency: str = "MXN"
    pipeline_id: UUID
    stage_id: UUID
    expected_close_date: Optional[date] = None
    contact_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    description: Optional[str] = None
```

**Solución**: Cambiar `amount` → `estimated_value` en frontend.

#### StageTransition
```diff
# FRONTEND (actual)
export interface StageTransition {
  to_stage_id: UUID;      # ❌
  notes?: string;
  lost_reason?: string;   # ❌ (debería ser lost_reason_id)
  close_as_won?: boolean;
  close_as_lost?: boolean;
}

# BACKEND (actual)
class StageTransition(BaseModel):
    stage_id: UUID           # ✅
    lost_reason_id: Optional[UUID] = None
    lost_notes: Optional[str] = None
```

**Solución**: Alinear con backend: `to_stage_id` → `stage_id`, `lost_reason` → `lost_reason_id`, `notes` → `lost_notes`.

### 1.3 Tareas de alineación

| # | Tarea | Archivo | Cambio |
|---|---|---|---|
| 1.3.1 | Alinear UserRole | `frontend/src/lib/types/api.ts:21` | Cambiar a 5 roles reales |
| 1.3.2 | Alinear OpportunityCreate | `frontend/src/lib/types/api.ts:197-208` | `amount` → `estimated_value` |
| 1.3.3 | Alinear StageTransition | `frontend/src/lib/types/api.ts:228-234` | `to_stage_id` → `stage_id`, `lost_reason` → `lost_reason_id` |
| 1.3.4 | Verificar todos los tipos | `frontend/src/lib/types/api.ts` | Revisar coincidencia con backend |
| 1.3.5 | Actualizar API clients | `frontend/src/lib/api/*.ts` | Asegurar que usan los tipos correctos |

### 1.4 Validación
```bash
cd frontend
npx tsc --noEmit
```

---

## Fase 2 — Fix Login Hardcodeado (P0, 30 min)
> **Objetivo**: Permitir que el usuario elija su organización al loguearse.

### 2.1 Problema actual
```typescript
// frontend/src/lib/api/auth.ts:13-18
async login(payload: LoginPayload): Promise<AuthResponse> {
  return api.post<AuthResponse>("/api/users/login", {
    ...payload,
    organization_slug: "crm-splash-demo",  // ❌ Hardcodeado
  });
}
```

### 2.2 Solución
```typescript
// frontend/src/lib/types/api.ts
export interface LoginPayload {
  email: string;
  password: string;
  organization_slug: string;  // ✅ Añadir campo
}

// frontend/src/app/login/page.tsx
// Añadir campo organization_slug al formulario
```

### 2.3 Tareas
| # | Tarea | Archivo | Cambio |
|---|---|---|---|
| 2.3.1 | Añadir organization_slug a LoginPayload | `frontend/src/lib/types/api.ts:49-52` | Añadir campo |
| 2.3.2 | Remover hardcode en authApi.login | `frontend/src/lib/api/auth.ts:13-18` | Usar payload.organization_slug |
| 2.3.3 | Añadir campo al formulario de login | `frontend/src/app/login/page.tsx` | Input para organization_slug |
| 2.3.4 | Validar que el backend acepta el campo | `backend/src/modules/users/schemas.py` | Verificar Login schema |

---

## Fase 3 — Sub-recursos Contacts (P0, 2-3 horas)
> **Objetivo**: Implementar los endpoints faltantes para sub-recursos de contacts.

### 3.1 Endpoints faltantes en backend

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/contacts/{id}/activities` | GET | Listar actividades de un contacto |
| `/api/v1/contacts/{id}/tasks` | GET | Listar tareas de un contacto |
| `/api/v1/contacts/{id}/opportunities` | GET | Listar oportunidades de un contacto |
| `/api/v1/contacts/{id}/documents` | GET | Listar documentos de un contacto |
| `/api/v1/contacts/{id}/audit` | GET | Listar auditoría de un contacto |
| `/api/v1/contacts/duplicates` | GET | Buscar contactos duplicados |
| `/api/v1/contacts/import` | POST | Importar contactos desde CSV |

### 3.2 Tareas de implementación

#### 3.2.1 Endpoints de listado (activities, tasks, opportunities, documents)
```python
# backend/src/modules/contacts/routes.py

@router.get("/{contact_id}/activities", response_model=list[ActivityRead])
def list_contact_activities(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_contact_activities(contact_id)

@router.get("/{contact_id}/tasks", response_model=list[TaskRead])
def list_contact_tasks(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_contact_tasks(contact_id)

@router.get("/{contact_id}/opportunities", response_model=list[OpportunityRead])
def list_contact_opportunities(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_contact_opportunities(contact_id)

@router.get("/{contact_id}/documents", response_model=list[DocumentRead])
def list_contact_documents(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).list_contact_documents(contact_id)
```

#### 3.2.2 Endpoint de auditoría
```python
@router.get("/{contact_id}/audit", response_model=list[AuditLogRead])
def list_contact_audit(
    contact_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.AUDIT_READ)
    return AuditService(db).list_by_entity("contact", contact_id)
```

#### 3.2.3 Endpoint de duplicados
```python
@router.get("/duplicates", response_model=list[ContactRead])
def find_duplicate_contacts(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_READ)
    return ContactService(db).find_duplicates(email=email, phone=phone)
```

#### 3.2.4 Endpoint de importación CSV
```python
@router.post("/import", status_code=201)
async def import_contacts(
    file: UploadFile,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    require_permission(current.role, Permission.CONTACT_CREATE)
    return await ContactService(db).import_csv(file)
```

### 3.3 Tareas de service

| # | Tarea | Archivo | Método |
|---|---|---|---|
| 3.3.1 | Implementar list_contact_activities | `backend/src/modules/contacts/service.py` | `list_contact_activities(contact_id)` |
| 3.3.2 | Implementar list_contact_tasks | `backend/src/modules/contacts/service.py` | `list_contact_tasks(contact_id)` |
| 3.3.3 | Implementar list_contact_opportunities | `backend/src/modules/contacts/service.py` | `list_contact_opportunities(contact_id)` |
| 3.3.4 | Implementar list_contact_documents | `backend/src/modules/contacts/service.py` | `list_contact_documents(contact_id)` |
| 3.3.5 | Implementar find_duplicates | `backend/src/modules/contacts/service.py` | `find_duplicates(email, phone)` |
| 3.3.6 | Implementar import_csv | `backend/src/modules/contacts/service.py` | `import_csv(file)` |

### 3.4 Validación
```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_contacts.py -q
```

---

## Fase 4 — Dashboard con datos reales (P1, 2 horas)
> **Objetivo**: Reemplazar datos fake con llamadas reales a la API.

### 4.1 Problema actual
```typescript
// frontend/src/app/(authed)/dashboard/page.tsx:27-40
const [trendData] = useState(() =>
  Array.from({ length: 7 }).map((_, i) => ({
    name: `D-${6 - i}`,
    value: Math.round(20000 + Math.random() * 50000),  // ❌ Fake
  }))
);

const [pipelineData] = useState(() => [  // ❌ Fake
  { name: "Prospección", value: 12 },
  { name: "Calificado", value: 8 },
  { name: "Propuesta", value: 5 },
  { name: "Negociación", value: 3 },
  { name: "Ganado", value: 2 },
]);
```

### 4.2 Solución
```typescript
// Usar datos de reportsApi
const { data: trendData } = useQuery(
  ["dashboard-trend"],
  () => reportsApi.getPipelineTrend({ days: 7 })
);

const { data: pipelineData } = useQuery(
  ["dashboard-pipeline"],
  () => reportsApi.getPipelineStageDistribution()
);
```

### 4.3 Tareas

| # | Tarea | Archivo | Cambio |
|---|---|---|---|
| 4.3.1 | Crear endpoint pipeline trend | `backend/src/modules/reports/routes.py` | `GET /pipeline/trend` |
| 4.3.2 | Crear endpoint pipeline distribution | `backend/src/modules/reports/routes.py` | `GET /pipeline/distribution` |
| 4.3.3 | Añadir métodos a reportsApi | `frontend/src/lib/api/reports.ts` | `getPipelineTrend`, `getPipelineStageDistribution` |
| 4.3.4 | Reemplazar useState fake | `frontend/src/app/(authed)/dashboard/page.tsx` | Usar useQuery |

---

## Fase 5 — Validación Final (1 hora)

### 5.1 Ejecutar todos los tests
```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/ -q
```

### 5.2 Typecheck frontend
```bash
cd frontend
npx tsc --noEmit
```

### 5.3 Smoke test E2E
```bash
cd backend
.venv\Scripts\python.exe scripts/smoke.py
```

### 5.4 Verificar en navegador
- Login con organización seleccionable
- Navegar a contacts → ver detalle con pestañas
- Ver dashboard con datos reales
- Probar automatizaciones

---

## Orden de Ejecución

```
Fase 1 (Schemas) ──> Fase 2 (Login) ──> Fase 3 (Sub-recursos)
                       └── Fase 4 (Dashboard) puede ser paralela
```

**Estimación total**: 8-10 horas de trabajo

---

## Asignación a Agentes

### OpenCode (Backend)
- Fase 1: Alinear schemas (revisión)
- Fase 3: Implementar sub-recursos contacts
- Fase 4: Endpoints de reports para dashboard

### Claude Code (Frontend)
- Fase 1: Alinear types/api.ts
- Fase 2: Fix login hardcodeado
- Fase 4: Reemplazar datos fake en dashboard

---

## Criterios de Aceptación

- [ ] `npx tsc --noEmit` → exit 0
- [ ] `pytest tests/ -q` → 84+ passed
- [ ] Login permite seleccionar organización
- [ ] Detalle de contacto muestra pestañas con datos reales
- [ ] Dashboard muestra gráficos con datos de API
- [ ] Smoke test pasa
