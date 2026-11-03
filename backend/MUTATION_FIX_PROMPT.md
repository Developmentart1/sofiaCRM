# Correcciones post-auditoría de mutación — CRM-Splash Backend

## Contexto
Auditoría de mutación encontró 7 mutantes supervivientes en 3 módulos críticos.
Los 84 tests actuales pasan, pero NO verifican estos comportamientos.

## Tarea
Escribe los tests que maten los 7 mutantes supervivientes. Cada test debe fallar
cuando la mutación está aplicada y pasar cuando el código está correcto.

## Corrección 1: rbac.py — Test de rechazo de rol inválido (CRÍTICO)

**Archivo:** `tests/test_rbac_matrix.py`
**Mutante:** `return False` → `return True` en `role_has()` (L204 de `src/core/rbac.py`)
**Qué verificar:** Un rol que no existe (ej: "hacker") debe ser denegado.

```python
def test_invalid_role_is_denied():
    """Un rol inexistente debe retornar False y lanzar ForbiddenError."""
    from core.rbac import role_has, require_permission, Permission, ForbiddenError
    assert role_has("rol_inexistente", Permission.CONTACT_READ) is False
    with pytest.raises(ForbiddenError):
        require_permission("rol_inexistente", Permission.CONTACT_READ)
```

## Corrección 2: reports/service.py — Tests de boundary dates

**Archivo:** `tests/test_reports.py`
**Mutantes:** `>=` → `>` y `<=` → `<` en filtros de fecha (L227-228, L241-242, etc.)
**Qué verificar:** Una oportunidad cerrada EXACTAMENTE en el límite del período debe incluirse.

Necesitas:
1. Crear una oportunidad con `status="won"` y `closed_at` = datetime.combine(fecha_inicio, time.min)
2. Llamar `ReportService(db).summary(from_=fecha_inicio, to=fecha_inicio)`
3. Verificar que `total_revenue > 0`

Usa los fixtures existentes del test (db session, organización, etc.).

## Corrección 3: reports/service.py — Test de etapas inactivas

**Archivo:** `tests/test_reports.py`
**Mutante:** `Stage.is_active.is_(True)` → `Stage.is_active.is_(False)` (L479)
**Qué verificar:** Una etapa con `is_active=False` NO debe aparecer en la distribución.

Necesitas:
1. Crear una etapa con `is_active=False` en el pipeline
2. Crear una oportunidad en esa etapa
3. Llamar `ReportService(db).pipeline_distribution()`
4. Verificar que esa etapa NO aparece en los resultados

## Corrección 4: users/service.py — Test de usuario inactivo

**Archivo:** `tests/test_auth_flow.py`
**Mutante:** `or` → `and` en `if user is None or not user.is_active` (L82)
**Qué verificar:** Un usuario con `is_active=False` NO puede hacer login.

Necesitas:
1. Crear un usuario con `is_active=False`
2. Intentar hacer login con sus credenciales
3. Verificar que lanza UnauthorizedError o similar

## Instrucciones
- Usa los fixtures y helpers existentes en `tests/`
- NO modifiques código de producción, solo escribe tests
- Después de escribir cada test, ejecuta `pytest tests/test_<modulo>.py -v` para verificar que pasa
- Al final ejecuta `pytest tests/ -q` para verificar que los 84 tests originales + los nuevos pasan todos