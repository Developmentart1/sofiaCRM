# Auditoría de Mutación — CRM-Splash Backend
> Fecha: 2026-09-29
> Método: Mutación manual (mutmut no corre en Windows)
> Gates: ✅ 84 passed | ✅ 83% cobertura

## Resumen

| Módulo | Score | Detectados | Total | Supervivientes |
|--------|-------|------------|-------|----------------|
| `src/core/rbac.py` | **0%** | 0 | 1 | 1 (CRÍTICO) |
| `src/modules/reports/service.py` | **44%** | 4 | 9 | 5 |
| `src/modules/users/service.py` | **67%** | 2 | 3 | 1 |

## Hallazgos críticos

### 1. rbac.py — 0% — `return False` → `return True` (L204)

**Qué pasa:** `role_has()` devuelve `False` cuando el rol no existe (ValueError). Si un atacante envía un rol inválido, la mutación lo convierte en `return True` → otorga TODOS los permisos.

**Impacto:** Un usuario con rol inventado ("hacker") pasaría cualquier `require_permission()`.

**Test necesario:**
```python
def test_invalid_role_denied():
    assert role_has("rol_inexistente", Permission.CONTACT_READ) is False
    with pytest.raises(ForbiddenError):
        require_permission("rol_inexistente", Permission.CONTACT_READ)
```

### 2. reports/service.py — 44% — 5 supervivientes

| Mutación | Línea | Riesgo |
|----------|-------|--------|
| `>=` → `>` | L227, L241, L256, L281, L363 | Un registro creado exactamente en el límite se excluiría |
| `<=` → `<` | L228, L242, L257, L282, L364 | Un registro cerrado exactamente en el límite se excluiría |
| `True` → `False` | L479 | Etapas inactivas aparecerían en la distribución |

**Test necesario (boundary):**
```python
def test_summary_includes_boundary_dates(db, org):
    """Una oportunidad cerrada exactamente en from_dt debe incluirse."""
    from datetime import date, datetime, time
    today = date.today()
    opp = create_opportunity(db, org, status="won",
        closed_at=datetime.combine(today, time.min))
    result = ReportService(db).summary(from_=today, to=today)
    assert any(r.revenue > 0 for r in result.revenue_by_pipeline)
```

**Test necesario (inactive stages):**
```python
def test_distribution_excludes_inactive_stages(db, org):
    """Etapa inactiva no debe aparecer en la distribución."""
    stage = create_stage(db, org, is_active=False)
    create_opportunity(db, org, stage_id=stage.id)
    result = ReportService(db).pipeline_distribution()
    assert not any(s["stage_name"] == stage.name for s in result)
```

### 3. users/service.py — 67% — 1 superviviente

| Mutación | Línea | Riesgo |
|----------|-------|--------|
| `or` → `and` | L82 | Usuario inactivo pasaría la autenticación |

**Línea:** `if user is None or not user.is_active:` → con `and`, un usuario existente pero inactivo pasaría.

**Test necesario:**
```python
def test_login_rejects_inactive_user(db, org):
    """Usuario inactivo no puede hacer login."""
    user = create_user(db, org, is_active=False)
    with pytest.raises(UnauthorizedError):
        UserService(db).login(LoginRequest(
            email=user.email, password="Demo1234!",
            organization_slug=org.slug
        ))
```

## Conclusión

El mutation score ponderado es ~37%. Los tests verifican el camino feliz pero no:
- **Seguridad**: roles inválidos, usuarios inactivos
- **Límites exactos**: fechas boundary
- **Filtros de exclusión**: etapas inactivas

Los 3 tests propuestos arreglan los 7 mutantes supervivientes.