#!/usr/bin/env python3
"""Optional OpenAI-compatible / Ollama LLM generation utilities with offline fallback."""

from __future__ import annotations

import json
import os
import urllib.request


def _llm_generate(
    system_prompt: str,
    user_prompt: str,
    timeout: int = 60,
    provider: str = "auto",
    json_mode: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """Generate text via configured OpenAI-compatible endpoint, or return deterministic offline notice."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("DOCUMENT_ORGANIZER_LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        return "[ERROR] OPENAI_API_KEY is not configured; using deterministic offline fallback."

    payload: dict[str, object] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            choices = body.get("choices") or []
            if choices:
                return str(choices[0].get("message", {}).get("content", "")).strip()
        return "[ERROR] Empty LLM response."
    except Exception as exc:
        return f"[ERROR] LLM request failed: {exc}"


def _is_rate_limit_error(error: Exception) -> bool:
    """Check whether an exception indicates HTTP 429 / rate limiting."""
    err_str = str(error).lower()
    return any(
        hint in err_str
        for hint in ["429", "resource_exhausted", "resourceexhausted", "rate limit"]
    )
