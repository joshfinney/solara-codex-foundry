"""PandasAI integration primitives used by the Primary Credit workspace."""

from __future__ import annotations

from .patches import apply_all_patches, register_patch
from .pipeline import PandasAIChatBackend, PandasAIExecutionContext
from .progress import PipelineProgress
from .response_parser import PandasAIResponseParser

__all__ = [
    "PandasAIChatBackend",
    "PandasAIExecutionContext",
    "PandasAIResponseParser",
    "PipelineProgress",
    "apply_all_patches",
    "register_patch",
]

# Apply registered patches eagerly so that PandasAI customisations are active as
# soon as the integration package is imported.
apply_all_patches()
