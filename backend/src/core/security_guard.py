"""Security guard — one-file ASGI middleware covering the core attack surface.

Vulnerabilidad        → Detección                                → Respuesta inicial
Prompt Injection      → clasificadores de instrucciones/tool-call → aislar contenido,
                        indirectos en body/query                    bloquear tool-calls, evidencia
SQL Injection         → patrones de payload en params/body        → bloquear 400, alertar, marcar endpoint
XSS                   → patrones de payload reflejado + CSP       → neutralizar salida, bloquear respuesta riesgosa
Auth Bypass           → credenciales ausentes, claims cross-tenant → denegar 401/403, alerta crítica
Data Leakage          → secretos/PII/tamaño excesivo en respuestas → redactar, bloquear salida, alertar
Rate Limit Missing    → ventana deslizante por identidad/IP/       → 429 + hallazgo
                        tenant/endpoint
Insecure Output       → campos prohibidos en respuestas JSON       → sanear campos, alertar

Stdlib only. Evidencia: JSONL en SECURITY_EVIDENCE_LOG (default security_evidence.jsonl).
ponytail: rate limiter en memoria (por proceso) y scan de respuesta acotado a 256KB —
Redis / escaneo streaming si corre multi-worker o sirve JSON gigante.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import deque
from urllib.parse import unquote_plus

from starlette.routing import Match

log = logging.getLogger("security_guard")

# ── Reglas de detección ─────────────────────────────────────────────

PROMPT_INJECTION = [
    r"ignore\s+(all\s+)?(previous|prior|above|todas\s+las)\s+(instructions?|instrucciones)",
    r"you\s+are\s+now\s+(a|an|un|una)",
    r"disregard\s+(the\s+)?(system|previous|above)",
    r"(system\s*prompt|instrucciones\s+del\s+sistema)",
    r"\[INST\]|\[SYS\]|<\|im_start\|>",
    r"(reveal|show|print|muestra|revela)\s+(your|the|tu|el)\s+(system|initial)?\s*(prompt|instructions?|instrucciones)",
    r"jailbreak|do\s+anything\s+now|DAN\s+mode",
]

# Subconjunto que intenta ejecutar herramientas/comandos → se bloquea de plano.
TOOL_CALL_DIRECTIVES = [
    r"(call|invoke|ejecuta|invoca|usa)\s+(the\s+|a\s+|el\s+|la\s+)?(tool|function|herramienta|función|api)",
    r"```(bash|sh|shell|powershell|cmd|python)",
    r"(sudo\s|rm\s+-rf|curl\s+[^\n]*\|\s*(ba)?sh|powershell\s+-enc)",
]

SQL_INJECTION = [
    r"('|\")\s*(or|and)\s+('|\")?\d+('|\")?\s*=\s*('|\")?\d+",
    r"(union\s+(all\s+)?select|select\s+.+\s+from\s+)",
    r"(;\s*(drop|delete|update|insert|truncate|alter)\s)",
    r"(sleep|benchmark|pg_sleep|waitfor\s+delay)\s*\(",
    r"(xp_cmdshell|load_file\s*\(|into\s+(out|dump)file)",
    r"(--\s|#\s|/\*)\s*$",
]

XSS_PAYLOAD = [
    r"<\s*script[^>]*>",
    r"javascript\s*:",
    r"on(error|load|click|mouseover|focus)\s*=",
    r"<\s*(iframe|object|embed|svg|img)[^>]*>",
    r"(document\.cookie|window\.location\s*=)",
]

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_key"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "github_token"),
    (re.compile(r"sk-[^\s»\"]{4,}"), "api_key"),
    (re.compile(r"redacted\s*:\s*sk-[^\s»\"]+", re.I), "masked_api_key"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"), "jwt"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private_key"),
    (re.compile(r"(password|passwd|secret|api_key|token)\s*[:=]\s*\S{8,}", re.I), "credential"),
]

# PII sensible solo se redacta si la respuesta es anónima: los contactos de un
# CRM legítimamente contienen datos personales para usuarios autenticados.
PII_PATTERNS = [
    (re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b"), "curp"),
    (re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b"), "rfc"),
    (re.compile(r"\b\d{18}\b"), "clabe"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "tarjeta"),
]

DENIED_OUTPUT_FIELDS = {
    "password", "password_hash", "passwd", "secret", "secret_key",
    "private_key", "token_hash", "internal_id",
}

_MAX_SCAN_BYTES = 256 * 1024   # ponytail: bodies mayores pasan sin escanear
_MAX_REPLAY_BYTES = 1024 * 1024

# Dependencias de auth de FastAPI: si una ruta las pide, requiere credenciales.
_AUTH_DEPS = {"get_current_user", "require_permission"}
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")
_PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/openapi.json",
    "/api/v1/users/login",
    "/api/v1/users/login/company",
    "/api/v1/organizations/bootstrap",
}

_REDACTED = "[REDACTED]"
_ISOLATED = "[CONTENIDO AISLADO]"


def _find(patterns: list[str], text: str) -> list[str]:
    hits = []
    for pat in patterns:
        m = re.search(pat, text, re.I | re.M)
        if m:
            hits.append(m.group(0)[:120])
    return hits


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def _strip_fields(obj):
    """Quita campos prohibidos de un JSON (insecure output)."""
    if isinstance(obj, dict):
        return {
            k: _strip_fields(v)
            for k, v in obj.items()
            if k.lower() not in DENIED_OUTPUT_FIELDS
        }
    if isinstance(obj, list):
        return [_strip_fields(v) for v in obj]
    return obj


# ── Rate limiter (ventana deslizante en memoria) ────────────────────

class _RateLimiter:
    """ponytail: memoria por proceso; Redis si corre multi-worker."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] > 60.0:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True


# ── Evidencia ───────────────────────────────────────────────────────

_evidence_lock = threading.Lock()


def _evidence(path: str, finding: dict) -> None:
    finding.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    line = json.dumps(finding, ensure_ascii=False, default=str)
    with _evidence_lock:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            log.warning("evidencia no persistida: %s", finding.get("kind"))
    log.warning("security_guard %s: %s", finding.get("kind"), finding.get("detail", "")[:200])


# ── Middleware ──────────────────────────────────────────────────────

def _asgi_json(scope, status_code: int, code: str, message: str):
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
    ]
    if not scope.get("path", "").startswith(_CSP_EXEMPT_PREFIXES):
        headers.append((b"content-security-policy", b"default-src 'self'"))
    return {
        "type": "http.response.start",
        "status": status_code,
        "headers": headers,
    }, {
        "type": "http.response.body",
        "body": body,
        "more_body": False,
    }


def _token_from(scope) -> str | None:
    for k, v in scope.get("headers", []):
        if k == b"authorization" and v.lower().startswith(b"bearer "):
            return v[7:].decode(errors="ignore").strip() or None
        if k == b"cookie":
            for part in v.decode(errors="ignore").split(";"):
                key, _, value = part.strip().partition("=")
                if key == "access_token" and value:
                    return value
    return None


def _org_claim(token: str) -> str | None:
    try:
        from core.security import decode_access_token
        return decode_access_token(token).get("org")
    except Exception:  # noqa: BLE001 — token inválido lo resuelve la ruta
        return None


class SecurityGuardMiddleware:
    """ASGI middleware: detección + respuesta inicial por vulnerabilidad."""

    def __init__(self, app, *, per_minute: int | None = None,
                 evidence_log: str | None = None):
        self.app = app
        if per_minute is None:
            try:
                from core.config import get_settings
                per_minute = get_settings().rate_limit_per_minute
            except Exception:  # noqa: BLE001
                per_minute = 120
        self.limiter = _RateLimiter(per_minute)
        self.evidence_log = evidence_log or os.getenv(
            "SECURITY_EVIDENCE_LOG", "security_evidence.jsonl"
        )

    # ── request ─────────────────────────────────────────────────────

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        requires_auth = self._requires_auth(scope)
        deny, receive = await self._inspect_request(scope, receive, path, requires_auth)
        if deny is not None:
            start, body = deny
            await send(start)
            await send(body)
            return

        await self.app(scope, receive, self._wrap_send(send, scope))

    @staticmethod
    def _requires_auth(scope) -> bool:
        """Pregunta a FastAPI si la ruta pide auth, en vez de una allowlist manual.

        Si la ruta no es de FastAPI u oculta sus deps, fail-closed: exige auth.
        """
        if scope.get("path", "") in _PUBLIC_PATHS:
            return False
        app = scope.get("app")
        if app is None:
            return True
        for r in app.routes:
            match, _ = r.matches(scope) if hasattr(r, "matches") else (Match.NONE, {})
            if match != Match.FULL:
                continue
            dep = getattr(r, "dependant", None)
            if dep is None:
                return True  # ruta no-FastAPI: fail-closed
            names = {getattr(d.call, "__name__", "") for d in getattr(dep, "dependencies", [])}
            return bool(names & _AUTH_DEPS)
        return True

    async def _inspect_request(self, scope, receive, path, requires_auth: bool):
        method = scope.get("method", "GET").upper()
        query = unquote_plus(scope.get("query_string", b"").decode(errors="ignore"))
        token = _token_from(scope)

        # Auth bypass: credenciales ausentes solo en rutas que la app exige.
        if requires_auth and not token:
            self._finding("auth_bypass", scope,
                          "request sin credenciales a ruta protegida", critical=True)
            return _asgi_json(scope, 401, "unauthorized", "authentication required"), receive

        # Rate limit por identidad + endpoint.
        ident = scope.get("client", ("anon",))[0]
        org = _org_claim(token) or "unknown"
        if not self.limiter.allow(f"{org}|{ident}|{path}"):
            self._finding("rate_limit", scope,
                          f"superado límite de {self.limiter.per_minute}/min en {path}")
            return _asgi_json(scope, 429, "rate_limited", "too many requests"), receive

        # Body (solo JSON/urlencoded; multipart se salta — uploads grandes).
        content_type = ""
        for k, v in scope.get("headers", []):
            if k == b"content-type":
                content_type = v.decode(errors="ignore").lower()
        body = b""
        if method in ("POST", "PUT", "PATCH") and "multipart" not in content_type:
            body = await self._read_body(receive)
            if len(body) > _MAX_REPLAY_BYTES:
                body = b""
        text = query + "\n" + body.decode(errors="ignore")

        # SQL injection → bloquear.
        hits = _find(SQL_INJECTION, text)
        if hits:
            self._finding("sql_injection", scope, f"payload {hits}", endpoint=path)
            return _asgi_json(scope, 400, "bad_request", "malicious input rejected"), receive

        # XSS → bloquear (la neutralización de salida va abajo).
        hits = _find(XSS_PAYLOAD, text)
        if hits:
            self._finding("xss", scope, f"payload {hits}", endpoint=path)
            return _asgi_json(scope, 400, "bad_request", "malicious input rejected"), receive

        # Prompt injection: tool-calls → bloquear; instrucciones → aislar.
        if _find(TOOL_CALL_DIRECTIVES, text):
            self._finding("prompt_injection", scope,
                          "directiva de tool-call/ejecución en input", endpoint=path)
            return _asgi_json(scope, 400, "bad_request", "tool invocation blocked"), receive
        if _find(PROMPT_INJECTION, text) and body:
            clean = body.decode(errors="ignore")
            for pat in PROMPT_INJECTION:
                clean = re.sub(pat, _ISOLATED, clean, flags=re.I)
            body = clean.encode()
            self._finding("prompt_injection", scope,
                          "instrucción indirecta aislada del contenido", endpoint=path)

        # Cross-tenant: claim de org en headers/body distinto al del token.
        header_org = self._header(scope, b"x-org-id")
        body_org = self._json_field(body, "org_id")
        if (header_org and header_org != org) or (body_org and body_org != org):
            self._finding("auth_bypass", scope,
                          f"claim cross-tenant token={org} vs request={header_org or body_org}",
                          critical=True)
            return _asgi_json(scope, 403, "forbidden", "cross-tenant access denied"), receive

        return None, self._replay(body) if body else receive

    async def _read_body(self, receive) -> bytes:
        chunks = []
        while True:
            msg = await receive()
            if msg["type"] != "http.request":
                break
            chunks.append(msg.get("body", b""))
            if not msg.get("more_body"):
                break
        return b"".join(chunks)

    def _replay(self, body: bytes):
        async def _receive():
            return {"type": "http.request", "body": body, "more_body": False}
        return _receive

    @staticmethod
    def _header(scope, name: bytes) -> str | None:
        for k, v in scope.get("headers", []):
            if k == name:
                return v.decode(errors="ignore")
        return None

    @staticmethod
    def _json_field(body: bytes, field: str) -> str | None:
        try:
            obj = json.loads(body)
        except Exception:  # noqa: BLE001
            return None
        val = obj.get(field) if isinstance(obj, dict) else None
        return str(val) if val else None

    # ── response ────────────────────────────────────────────────────

    def _wrap_send(self, send, scope):
        state = {"ctype": "", "buf": bytearray(), "start": None, "pass": False}

        async def wrapper(msg):
            if msg["type"] == "http.response.start":
                headers = []
                for k, v in msg.get("headers", []):
                    if k == b"content-type":
                        state["ctype"] = v.decode(errors="ignore").lower()
                    headers.append((k, v))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"referrer-policy", b"no-referrer"))
                if not scope.get("path", "").startswith(_CSP_EXEMPT_PREFIXES):
                    headers.append((b"content-security-policy", b"default-src 'self'"))
                state["start"] = dict(msg, headers=headers)
                return

            scan = "json" in state["ctype"] or "text" in state["ctype"]
            if scan and not state["pass"]:
                state["buf"].extend(msg.get("body", b""))
                if len(state["buf"]) > _MAX_SCAN_BYTES:
                    # Se acabó el presupuesto: emitir lo acumulado sin escanear.
                    state["pass"] = True
                    await send(state["start"])
                    state["start"] = None
                    await send({"type": "http.response.body",
                                "body": bytes(state["buf"]), "more_body": True})
                    state["buf"].clear()
                    return
                if msg.get("more_body"):
                    return
                out = self._scan_response(bytes(state["buf"]), scope)
                state["buf"].clear()
                start = state["start"]
                start["headers"] = [
                    (k, str(len(out)).encode()) if k == b"content-length" else (k, v)
                    for k, v in start["headers"]
                ]
                await send(start)
                state["start"] = None
                await send({"type": "http.response.body", "body": out, "more_body": False})
                return

            if state["start"] is not None:
                await send(state["start"])
                state["start"] = None
            await send(msg)

        return wrapper

    def _scan_response(self, raw: bytes, scope) -> bytes:
        try:
            obj = json.loads(raw)
        except Exception:  # noqa: BLE001
            return raw

        # Insecure output: campos prohibidos.
        stripped = _strip_fields(obj)
        if stripped != obj:
            self._finding("insecure_output", scope, "campos sensibles eliminados de la respuesta")
            obj = stripped

        # El access_token de login es el producto, no un leak: se protege del scan.
        safe_tokens: list[str] = []
        obj = self._stash_session_tokens(obj, safe_tokens)

        text = json.dumps(obj, ensure_ascii=False, default=str)

        # Data leakage: secretos siempre; PII solo si la respuesta es anónima.
        for pat, label in SECRET_PATTERNS:
            if pat.search(text):
                text = pat.sub(_REDACTED, text)
                self._finding("data_leakage", scope, f"secreto '{label}' redactado de la respuesta")
        if self._is_anonymous(scope):
            for pat, label in PII_PATTERNS:
                if pat.search(text):
                    text = pat.sub(_REDACTED, text)
                    self._finding("data_leakage", scope,
                                  f"PII '{label}' redactada en respuesta anónima", critical=True)

        # XSS: neutraliza marcadores peligrosos que se reflejen en la salida.
        for pat in XSS_PAYLOAD:
            text = re.sub(pat, _ISOLATED, text, flags=re.I)

        for i, tok in enumerate(safe_tokens):
            text = text.replace(f"__SESSION_TOKEN_{i}__", tok)

        return text.encode()

    @staticmethod
    def _stash_session_tokens(obj, stash: list):
        """Sustituye access_token/refresh_token por marcadores antes del scan."""
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k.lower() in ("access_token", "refresh_token") and isinstance(v, str):
                    stash.append(v)
                    out[k] = f"__SESSION_TOKEN_{len(stash) - 1}__"
                else:
                    out[k] = SecurityGuardMiddleware._stash_session_tokens(v, stash)
            return out
        if isinstance(obj, list):
            return [SecurityGuardMiddleware._stash_session_tokens(v, stash) for v in obj]
        return obj

    def _is_anonymous(self, scope) -> bool:
        return not _token_from(scope)

    # ── evidencia ───────────────────────────────────────────────────

    def _finding(self, kind: str, scope, detail: str, *, critical: bool = False,
                 endpoint: str | None = None) -> None:
        _evidence(self.evidence_log, {
            "kind": kind,
            "detail": detail,
            "method": scope.get("method"),
            "path": scope.get("path"),
            "endpoint": endpoint or scope.get("path"),
            "client": scope.get("client", ("anon",))[0],
            "critical": critical,
        })
