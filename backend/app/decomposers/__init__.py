"""Decomposer registry.

Importing this package registers every built-in decomposer.
"""
from __future__ import annotations

from .base import REGISTRY, BaseDecomposer, DecomposerContext  # noqa: F401
from . import (  # noqa: F401  (import side effects populate REGISTRY)
    deterministic,
    naive,
    llamaindex_subq,
    least_to_most,
    self_ask,
    r2_reasoner,
    hybridflow,
    uno_orchestra,
)

__all__ = ["REGISTRY", "BaseDecomposer", "DecomposerContext"]
