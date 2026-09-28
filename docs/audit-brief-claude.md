# Brief de auditoría — CRM-Splash

Eres un arquitecto de software senior auditando este repositorio de forma EXHAUSTIVA y basada en EVIDENCIA.

Contexto: CRM multi-tenant con RBAC. Backend FastAPI + SQLAlchemy + Alembic en `backend/` (44 archivos .py, ~2700 LOC; módulos: organizations, users, contacts, pipelines, opportunities; core: security, rbac, tenant, event_bus, audit). Frontend Next.js (App Router) + TypeScript + shadcn/radix en `frontend/src` (~6300 LOC). Tests en `backend/tests`. Ignora: `frontend/.next`, `node_modules`, `backend/.venv`, `backend/_backup_modules`, `.git`.

MODO: solo lectura del código. No modifiques ningún archivo existente. Investiga el código real antes de afirmar cualquier cosa. Toda afirmación debe citar evidencia: `ruta:linea`. NO inventes funcionalidades que no estén en el código; si algo no existe, márcalo explícitamente como "AUSENTE".

## Dimensiones a evaluar

### Bloque 1 — Arquitectura y dominio del CRM
1. Modelo de datos multi-tenant (aislamiento real de tenants: ¿todas las queries filtran por tenant/org? revisar service.py y repository de cada módulo)
2. Ciclo de vida de oportunidades/pipelines (máquina de estados, transiciones válidas, etapas)
3. Contactos (deduplicación, importación, validación)
4. Actividades y tareas (¿backend real o solo páginas frontend?)
5. Documentos y reportes (¿backend real o solo frontend?)
6. Automatización (el README/main.py menciona "automation" — ¿existe?)

### Bloque 2 — Core Platform
1. Auth: JWT, hashing de contraseñas, expiración, refresh
2. RBAC: roles, permisos, enforcement real en rutas (no solo en frontend)
3. Auditoría (audit.py — ¿se usa realmente?)
4. Event bus (persistencia, reintentos, o solo in-memory)
5. Manejo de errores y validación
6. Configuración y secrets (¿valores hardcodeados?)
7. CORS y superficie de seguridad

### Bloque 3 — Capa de datos
1. Migraciones Alembic (¿versiones coherentes con los modelos actuales?)
2. Integridad referencial, índices, tipos correctos
3. Seed script
4. Tests: cobertura real, qué prueban, si corren

### Bloque 4 — Frontend
1. Páginas que consumen API real vs páginas mock/hardcodeadas (revisar cada page.tsx)
2. Manejo de auth en el cliente (middleware, almacenamiento de token)
3. Consistencia frontend↔backend (¿el frontend llama endpoints que no existen en backend?)

## Formato del informe final (en español)

1. **Resumen ejecutivo** (máx. 1 página): madurez global, fortalezas, riesgos críticos, veredicto.
2. **Tabla de madurez**: una fila por dimensión → columnas: Estado (AUSENTE / RUDIMENTARIO / FUNCIONAL / SÓLIDO), evidencia principal, gap crítico, prioridad (P0-P3).
3. **Análisis detallado por bloque**: hallazgos con evidencia `archivo:linea`, qué funciona, qué es fachada/stub, qué falta.
4. **Riesgos críticos** de seguridad e integridad.
5. **Roadmap recomendado** priorizado.

Sé riguroso y directo: distingue explícitamente entre código real que funciona, stubs/placeholders y funcionalidad ausente.

Escribe el informe completo en `docs/audit-claude.md`. IMPORTANTE: escribe el archivo POR ETAPAS — primero el resumen y tabla con Write, luego añade cada bloque con Edit — para no perder el trabajo si la respuesta se corta. Tu respuesta final debe confirmar la ruta escrita y un resumen breve.
