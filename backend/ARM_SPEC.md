# ARM — Agentic Relation Management (módulo backend)

## Contexto
- Proyecto: CRM-Splash backend (FastAPI + SQLAlchemy + pytest). Venv: `C:/Users/migue/CRM-Splash/backend/.venv/Scripts/python.exe`.
- Piso de tests: 101 tests colectados hoy. La suite completa debe quedar verde al terminar.
- Objetivo: módulo ARM v1 = funciones SÍNCRONAS de gestión de relaciones asistida por LLM.

## NO negociable
- NO toques otros módulos salvo el punto de registro del router (mira cómo se registra el router de contacts).
- NO modifiques tests existentes ni archivos fuera del alcance.
- NO ejecutes `git add` ni `git commit`. Deja los archivos en el working tree y repórtalos.
- El LLM de runtime es **mimo** por configuración de entorno: `MIMO_BASE_URL`, `MIMO_API_KEY`, `MIMO_MODEL` (default `"mimo"`). Nada de claves hardcodeadas.
- Sin frameworks de agentes, sin colas, sin tablas nuevas, sin migraciones. Una sola función de llamada LLM.
- Si hay ambigüedad de diseño: elige la opción más simple, documéntala en tu reporte final y NO termines con una pregunta.

## Arquitectura (mínima)

```
src/modules/arm/
  __init__.py
  llm.py      — cliente mimo: POST {MIMO_BASE_URL}/chat/completions (formato OpenAI-compatible) vía httpx.
                Una función: complete(system: str, user: str) -> str.
                Si falta MIMO_API_KEY en runtime → error claro del dominio (no crash, no fallback inventado).
  service.py  — ArmService(db):
                  draft_followup(contact_id) -> str
                  summarize_relation(contact_id) -> str
                Cada uno lee el contacto + sus actividades recientes del tenant actual,
                construye el prompt con datos REALES (nunca inventes datos), llama a llm.complete,
                devuelve el texto.
  router.py   — POST /arm/contacts/{id}/draft-followup
                POST /arm/contacts/{id}/summarize
                Sigue los patrones existentes del repo: aislamiento de tenant (current_org_id),
                RBAC (require_permission), errores del proyecto (NotFoundError, etc.).
```

## Tests (`tests/test_arm.py`)
Stub de `llm.complete` con monkeypatch — NUNCA llamar a la API real en tests.
1. `draft_followup` incluye en el prompt el nombre del contacto y sus actividades recientes.
2. `summarize_relation` aísla tenant: contacto de otra organización → error (NotFoundError o OrganizationBoundaryError).
3. RBAC: sin permiso → ForbiddenError.
4. Si `llm.complete` lanza excepción → error controlado del dominio (5xx mapeado), el proceso no revienta.

## Verificación obligatoria (antes de terminar)
```
.venv/Scripts/python.exe -m pytest tests/ -q
```
OJO: el working tree tiene cambios sin commitear de otra sesión. Si hay tests preexistentes en rojo, NO los arregles: repórtalos como baseline rojo; tu obligación es que tus tests nuevos estén en verde y que los que ya pasaban sigan pasando. Si pytest falla por ACLs de Temp en Windows:
`.venv/Scripts/python.exe -m pytest tests/ -q --basetemp=.pytest_tmp -p no:cacheprovider`

## Reporte final (obligatorio)
- Archivos creados (rutas).
- Salida real de pytest (conteo).
- Decisiones tomadas ante ambigüedades.
