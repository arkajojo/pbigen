"""Bring-your-own-model backend via LiteLLM, driving the staged design pipeline.

LiteLLM gives one interface to ~100 providers, so the same code targets a hosted API
(OpenAI, Anthropic, Gemini) or a local open-source model (Ollama, vLLM, LM Studio) — you
choose with ``model=`` and the matching credentials/endpoint in the environment.

The model runs :class:`~pbigen.ai.pipeline.DesignPipeline`: business context -> objectives &
KPI tree -> research (live web search where the provider supports it) -> storyboard -> critique.
It only ever sees *metadata* (column names, canonical types, approximate distinct counts) plus
aggregate profiles when you opt in with ``--profile``. No row data is sent. If the model is
unreachable or returns something unusable, the deterministic design is used so generation never
hard-fails — and the result says so honestly.

Author: Arka Gupta
"""
from __future__ import annotations

import sys
from typing import Any

from ..ai.pipeline import DesignPipeline, DesignRequest, extract_json, parse_design
from ..core.design import Design
from ..core.design import design as _baseline
from ..core.schema import Schema
from .base import Model


class LiteLLMModel(Model):
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3,
                 api_key: str | None = None, api_base: str | None = None,
                 max_tokens: int = 12000, verbose: bool = True, **extra: Any):
        self.model = model
        self.name = f"litellm:{model}"
        self.temperature = temperature
        self.api_key = api_key
        self.api_base = api_base
        self.max_tokens = max_tokens
        self.verbose = verbose
        self.extra = extra

    def design(self, schema: Schema, objective: str, request: DesignRequest | None = None) -> Design:
        request = request or DesignRequest(objective=objective)
        if objective and not request.objective:
            request.objective = objective
        try:
            import litellm  # noqa: F401
        except ImportError:
            print("pbigen: the LLM pipeline needs litellm — pip install 'pbigen[llm]'; "
                  "falling back to the deterministic design.", file=sys.stderr)
            return _baseline(schema, objective, context=request.context)
        try:
            return DesignPipeline(self._complete, self.model, verbose=self.verbose).run(schema, request)
        except Exception as exc:  # noqa: BLE001 - never let the model break generation
            print(f"pbigen: model '{self.model}' did not run ({type(exc).__name__}: "
                  f"{str(exc)[:200]}); falling back to the deterministic design.", file=sys.stderr)
            return _baseline(schema, objective, context=request.context)

    # -- transport -----------------------------------------------------------------
    def _complete(self, system: str, user: str, web: bool = False) -> str:
        import litellm
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if web:
            kwargs.update(self._web_kwargs())
        kwargs.update(self.extra)
        resp = litellm.completion(**kwargs)
        return _text(resp)

    def _web_kwargs(self) -> dict:
        """Provider-appropriate web search switch (raises if the model has none)."""
        import litellm
        m = self.model.lower()
        if m.startswith("anthropic/") or m.startswith("claude"):
            return {"tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]}
        try:
            supported = litellm.supports_web_search(model=self.model)
        except Exception:  # noqa: BLE001
            supported = False
        if not supported:
            raise RuntimeError(f"{self.model} has no web search in LiteLLM")
        return {"web_search_options": {"search_context_size": "medium"}}


def _text(resp: Any) -> str:
    """The text of a completion — joining content blocks when a tool (web search) was used."""
    msg = resp["choices"][0]["message"]
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content or ""


def _parse(raw: str, schema: Schema, baseline: Design) -> Design | None:
    """Parse a model's design JSON (kept for backwards compatibility / tests)."""
    return parse_design(extract_json(raw), schema, baseline)


_extract_json = extract_json
