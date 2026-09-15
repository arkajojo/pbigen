"""The deterministic default model.

No API key, no network, no cost. It runs the rule-based design brain in
:mod:`pbigen.core.design`, which already reasons over canonical types and cardinality to pick
charts and filters. This is what ``pbigen generate`` uses unless you opt into an LLM.

Author: Arka Gupta
"""
from __future__ import annotations

from ..core.design import Design
from ..core.design import design as _design
from ..core.schema import Schema
from .base import Model


class NullModel(Model):
    name = "deterministic"

    def design(self, schema: Schema, objective: str) -> Design:
        return _design(schema, objective)
