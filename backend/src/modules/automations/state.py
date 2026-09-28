"""Engine context state for anti-recursion and dry-run, held in ContextVars.

The event payloads are ``extra="forbid"`` so we cannot smuggle flags into them;
the engine therefore tracks its own nesting state in ContextVars that are
scoped to the current (synchronous) call stack. These are process-wide but the
values are thread/context local, and every mutation is restored in a ``finally``.
"""
from contextvars import ContextVar

# Current automation nesting depth (0 == top level, i.e. a user-triggered event).
depth: ContextVar[int] = ContextVar("automation_depth", default=0)

# Rule ids currently being executed on this call stack (breaks A→B→A cycles).
in_progress: ContextVar[frozenset[str]] = ContextVar(
    "automation_in_progress", default=frozenset()
)

# When True, actions must not persist or publish events (dry-run /test endpoint).
dry_run: ContextVar[bool] = ContextVar("automation_dry_run", default=False)
