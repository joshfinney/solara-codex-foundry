"""
Solara chat component library.

Exports data models, controller, and UI components for building chat experiences with
attestation gating, feedback collection, and flicker-free message rendering.
"""

from . import backend, models, state, attestation, view

__all__ = [
    "backend",
    "models",
    "state",
    "attestation",
    "view",
]
