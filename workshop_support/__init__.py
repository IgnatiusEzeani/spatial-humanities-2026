"""Presentation and deterministic teaching helpers for the SH2026 workshop."""

from .clients import (
    GroundedClient,
    HallucinatedEvidenceClient,
    InvalidStatusClient,
    NullFriendlyClient,
)
from .display import checkpoint, compare_spans, display, show_fields, show_journey, show_spans

__all__ = [
    "GroundedClient",
    "HallucinatedEvidenceClient",
    "InvalidStatusClient",
    "NullFriendlyClient",
    "checkpoint",
    "compare_spans",
    "display",
    "show_fields",
    "show_journey",
    "show_spans",
]
