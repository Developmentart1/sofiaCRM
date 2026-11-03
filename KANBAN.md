# Kanban — CRM-SOFIA2026

Alcance exclusivo: C:/Users/migue/CRM-SOFIA2026. No incluye DAG SF ERP ni SITI.
Estado basado en las verificaciones de esta conversación, no en una nueva ejecución. No hay trabajo corriendo confirmado. Las pruebas de dagsf-monolithic NO validan este CRM.

## Hecho (alcance limitado)
- [x] Copiar CRM-Splash a CRM-SOFIA2026 conservando historial Git.
- [x] Ampliar .gitignore para evidencia de seguridad, storage y claves.
- [x] Corregir contrato de registro frontend/backend y auto-login. Registro y dashboard observados en navegador.
- [x] Verificar por HTTP bootstrap 201, login 200, /users/me autenticado 200 y anónimo 401 en aquella ejecución.
- [x] Sustituir junction de node_modules por instalación local. Build de producción verificado.
- [x] Configurar frontend local para usar explícitamente el backend aislado `8010` y nombre CRM-SOFIA2026.
- [x] Corregir SecurityGuard: health público, headers también en respuestas bloqueadas y redacción de API keys.
- [x] Cambiar default de `ENV` a `production`; defaults de secretos se rechazan fuera de dev/test.
- [x] Suite backend completa: 117 tests passed.
- [x] Crear `frontend/DESIGN.md` con sistema visual nórdico brutalista, escala azul-gris y naranja.
- [x] Aplicar rediseño del shell: rail lateral, topbar, tokens globales, cards, botones, metadatos y copy Sofia.
- [x] Mantener fondo claro fijo y eliminar el toggle de tema del shell.
- [x] Typecheck + build Next.js verificados después del rediseño.
- [x] QA real de `/login` en producción local: HTTP 200, título CRM Sofia, formulario y paleta visibles.
- [x] Construir imagen Podman `crm-sofia:20261103` y desplegar contenedor `crm-sofia` en CherryServer, publicado localmente en `127.0.0.1:8093`.
- [x] Verificar contenedor estable (`RESTARTS=0`), frontend responde y `/api/health` devuelve HTTP 200.
- [x] Instalar `cloudflared` 2026.10.7 en la imagen Podman y recrear `crm-sofia` para que la instalación persista en los reinicios.

## Por revisar (no dar por terminado)
- [ ] P0 — Revisar SecurityGuardMiddleware completo: clasificación de rutas, dependencias anidadas, cookies, CORS/preflight, límite de login, lectura/replay de body, streaming, límite de tamaño, redacción JSON y excepción de tokens solo donde corresponde. Regex no sustituye parametrización SQL, autorización por objeto ni aislamiento de herramientas LLM. Cierre: tests de ataques y tráfico legítimo pasan sin corrupción ni bypass.
- [ ] P1 — Revisar configuración de secretos y ENV en deploy: variables reales, cookies Secure y CORS de dominio. Cierre: producción falla sin secretos válidos y desarrollo se configura explícitamente.
- [ ] P1 — Revisar fallo de auditoría en bootstrap (organization_id nulo). Cierre: alta persiste también la bitácora con tenant correcto.
- [ ] P1 — Inventariar datos sintéticos agregados a Supabase en la organización 4m1f y proponer tratamiento. No borrar, alterar ni añadir más datos sin aprobación.

## Pendiente (orden de ejecución)
- [ ] P0 — Aislar arranque de la copia: identificar procesos/puertos propios, usar puerto libre y dependencias de la copia. No detener procesos de CRM-Splash ni dagsf-monolithic. Cierre: frontend y backend de SOFIA identificados y accesibles.
- [ ] P0 — Diagnosticar /contacts en blanco y navegación/sidebar. La causa junction/chunks fue una hipótesis, no quedó demostrada. Cierre: consola/red inspeccionadas, contactos y menú renderizan tras recarga.
- [ ] P0 — Contactos y empresas: crear, abrir, editar y comprobar persistencia tras recarga desde UI. Cierre: resultados leídos desde API y navegador, sin datos ficticios presentados como reales.
- [ ] P1 — Pipelines y oportunidades: configurar etapas, crear oportunidad, mover de etapa y comprobar persistencia/métricas.
- [ ] P1 — Tareas y actividades: crear, editar, completar y verificar sus relaciones/persistencia.
- [ ] P1 — Documentos: subir, listar y descargar con autorización; probar rechazo entre tenants.
- [ ] P1 — Automatizaciones y reportes: comprobar ejecución real y cifras contra registros fuente; no basta abrir las pantallas.
- [ ] P1 — Configuración, roles y aislamiento: matriz RBAC y pruebas IDOR/BOLA entre organizaciones, sin usar datos de terceros.
- [ ] P1 — Cierre integral: suite propia de SOFIA, typecheck/build sin tuberías que oculten exit codes, navegación completa y evidencia de cada flujo. Separar commits. Despliegue requiere autorización independiente.

## En curso
Ninguna ejecución confirmada al preparar este tablero.

## Dependencias y autorizaciones
1. Arranque aislado → diagnóstico visual → pruebas CRUD → validación integral.
2. Revisión de seguridad puede realizarse independientemente; corregir regresiones antes del cierre integral.
3. Limpieza de datos sintéticos y despliegue: requieren aprobación. No son autorización implícita para escribir en producción.
4. Dominio `sofia.miguelic.com`: contenedor listo, pero falta añadir el Public Hostname/CNAME en Cloudflare; el dashboard quedó bloqueado por la verificación anti-bot y no hay `cert.pem`/API token disponible para hacerlo por CLI.

## Aclaraciones
- Hay páginas y endpoints existentes; su existencia no demuestra funcionalidad.
- El dashboard poblado usa datos de prueba: no equivale a operación real.
- Estado actual: CRM incompleto; navegación y operación integral pendientes.
