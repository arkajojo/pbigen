"""The Model contract.

A model turns a table's *metadata* (columns, canonical types, approximate cardinality) plus a
plain-language objective into a design brief: which pages, which visuals, which filters, and the
"how to use this report" notes. Only metadata ever leaves the machine — never row data.

Two implementations ship in the box:

* :class:`~pbigen.models.null_model.NullModel` — deterministic, no network, no key. The default.
* :class:`~pbigen.models.litellm_model.LiteLLMModel` — any provider LiteLLM supports
  (OpenAI, Anthropic, Gemini, Ollama, vLLM, …) via "bring your own key / endpoint".

Author: Arka Gupta
"""
from __future__ import annotations

import abc

from ..ai.pipeline import DesignRequest
from ..core.design import Design
from ..core.schema import Schema


class Model(abc.ABC):
    """Produces a :class:`Design` from a schema and a :class:`DesignRequest`."""

    name: str = "model"

    @abc.abstractmethod
    def design(self, schema: Schema, objective: str, request: DesignRequest | None = None) -> Design:
        """Return a :class:`Design` (pages, visuals, measures, usage notes, reasoning brief)."""
