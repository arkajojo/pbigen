"""Model registry.

``get_model(spec, **cfg)`` resolves the design model:

* ``None`` / ``"deterministic"`` / ``"none"`` -> :class:`NullModel` (default, no key, no network).
* anything else -> :class:`LiteLLMModel` with that string as the LiteLLM model id
  (e.g. ``"gpt-4o-mini"``, ``"anthropic/claude-sonnet-4-6"``, ``"ollama/llama3"``).

Author: Arka Gupta
"""
from __future__ import annotations

from typing import Any

from .base import Model
from .null_model import NullModel

_DETERMINISTIC = {None, "", "deterministic", "none", "null", "offline"}


def get_model(spec: str | None = None, **cfg: Any) -> Model:
    if spec in _DETERMINISTIC or (isinstance(spec, str) and spec.lower() in _DETERMINISTIC):
        return NullModel()
    from .litellm_model import LiteLLMModel
    return LiteLLMModel(model=spec, **cfg)


__all__ = ["Model", "NullModel", "get_model"]
