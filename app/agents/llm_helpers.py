"""Helpers for safe, validated LLM calls with bounded retries.

Not every provider reliably returns structured output. We therefore:
  1. Try the model's native structured output if available.
  2. Otherwise parse JSON from the text response.
  3. Validate against a Pydantic schema.
  4. Retry a bounded number of times, then give up (caller marks for review).
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.provider import NoProviderError, get_llm
from app.security.sanitization import truncate

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


async def call_structured(
    system_prompt: str,
    user_content: str,
    schema: type[T],
    max_retries: int = 2,
) -> T | None:
    """Call the LLM and return a validated schema instance, or None on failure."""
    try:
        llm = get_llm()
    except NoProviderError:
        return None

    user_content = truncate(user_content, 7000)
    # Attempt native structured output first.
    structured = None
    try:
        structured = llm.with_structured_output(schema)
    except (NotImplementedError, AttributeError, TypeError):
        structured = None

    for _attempt in range(max_retries + 1):
        try:
            if structured is not None:
                result = await structured.ainvoke(
                    f"{system_prompt}\n\n{user_content}"
                )
                if isinstance(result, schema):
                    return result
                return schema.model_validate(result)
            # Fallback: ask for JSON and parse it.
            prompt = (
                f"{system_prompt}\n\n{user_content}\n\n"
                f"Respond with ONLY valid JSON matching this schema keys: "
                f"{list(schema.model_fields.keys())}."
            )
            resp = await llm.ainvoke(prompt)
            text = getattr(resp, "content", str(resp))
            data = _extract_json(text if isinstance(text, str) else str(text))
            if data is not None:
                return schema.model_validate(data)
        except (ValidationError, ValueError) as exc:
            str(exc)
        except Exception as exc:  # provider/runtime error
            f"{type(exc).__name__}: {exc}"
            break  # don't hammer a failing provider
    return None


async def call_text(system_prompt: str, user_content: str) -> str | None:
    """Plain text completion. Returns None if no provider is available."""
    try:
        llm = get_llm()
    except NoProviderError:
        return None
    try:
        resp = await llm.ainvoke(f"{system_prompt}\n\n{truncate(user_content, 7000)}")
        text = getattr(resp, "content", str(resp))
        return text if isinstance(text, str) else str(text)
    except Exception:
        return None
