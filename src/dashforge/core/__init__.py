"""Core: the platform-neutral brain — canonical schema, design rules, layout, generator.

Nothing in ``core`` imports a database driver or a cloud SDK, so the design logic is fully
testable on its own and portable across every source and emitter.

Author: Arka Gupta
"""
from __future__ import annotations

from .design import Design, Measure, Page, Visual, classify, design, propose_measures
from .generator import GenerateResult, generate
from .layout import pack
from .schema import Column, Schema

__all__ = [
    "Column", "Schema", "Measure", "Visual", "Page", "Design",
    "classify", "propose_measures", "design", "pack", "generate", "GenerateResult",
]
