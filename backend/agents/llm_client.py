"""Provider-neutral LLM completion client for the demo agents.

The default is an OpenAI-compatible chat-completions endpoint. Anthropic remains
available by setting ``LLM_PROVIDER=anthropic``.
"""
from __future__ import annotations

import os
from typing import Any


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai-compatible").strip().lower()
LLM_API_KEY = _first_env(
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "CAII_API_KEY",
    "API_TOKEN",
    "ANTHROPIC_API_KEY",
)
LLM_BASE_URL = _first_env("LLM_BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE")
LLM_MODEL = os.environ.get(
    "LLM_MODEL",
    "claude-sonnet-4-20250514" if LLM_PROVIDER == "anthropic" else "gpt-4o-mini",
)


def _require_key() -> str:
    if not LLM_API_KEY:
        raise RuntimeError(
            "No LLM token configured. Set LLM_API_KEY, OPENAI_API_KEY, "
            "API_TOKEN, or ANTHROPIC_API_KEY."
        )
    return LLM_API_KEY


def complete(prompt: str, *, max_tokens: int = 2000) -> str:
    """Return a text completion from the configured provider."""
    token = _require_key()
    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=token)
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    if LLM_PROVIDER not in {"openai", "openai-compatible", "openai_compatible"}:
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    from openai import OpenAI

    kwargs: dict[str, Any] = {"api_key": token}
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL
    client = OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Configured LLM returned an empty response")
    return content


if __name__ == "__main__":
    assert LLM_PROVIDER
    print(f"LLM client configured for provider={LLM_PROVIDER}, model={LLM_MODEL}")
