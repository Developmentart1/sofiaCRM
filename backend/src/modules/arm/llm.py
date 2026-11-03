"""Mimo LLM client - single synchronous OpenAI-compatible completion call."""

import os

import httpx

from core.errors import CRMError


class ArmConfigurationError(CRMError):
    """Raised when the Mimo runtime is not configured."""

    status_code = 503
    code = "arm_configuration_error"


class ArmLLMError(CRMError):
    """Raised when the Mimo call fails or returns an unusable payload."""

    status_code = 502
    code = "arm_llm_error"


def complete(system: str, user: str) -> str:
    """Send a single chat completion to Mimo and return the assistant text."""
    base_url = os.environ.get("MIMO_BASE_URL")
    api_key = os.environ.get("MIMO_API_KEY")
    model = os.environ.get("MIMO_MODEL", "mimo")

    if not api_key:
        raise ArmConfigurationError(
            "MIMO_API_KEY is not configured",
            details={"hint": "set MIMO_API_KEY in the environment"},
        )
    if not base_url:
        raise ArmConfigurationError(
            "MIMO_BASE_URL is not configured",
            details={"hint": "set MIMO_BASE_URL in the environment"},
        )

    url = base_url.rstrip("/") + "/chat/completions"
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # network, timeout, HTTP error, bad JSON
        raise ArmLLMError("LLM request failed", details={"reason": str(exc)}) from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ArmLLMError("LLM response missing content", details={"reason": str(exc)}) from exc

    if not isinstance(content, str):
        raise ArmLLMError("LLM response content is not text")
    return content
