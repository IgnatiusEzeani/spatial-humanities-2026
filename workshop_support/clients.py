from __future__ import annotations

from typing import Any


class GroundedClient:
    """Deterministic response whose evidence is present in the source."""

    provider = "teaching"
    model = "grounded-example"

    def complete_json(
        self, task: str, prompt: str, *, input_text: str | None = None
    ) -> dict[str, Any]:
        return {
            "journeys": [{
                "start_location": "Amsterdam",
                "end_location": "Brussels",
                "transport_mode": "train",
                "date": "The next morning",
                "journey_reason": "to join my sister",
                "evidence_quote": "The next morning I travelled by train to Brussels to join my sister.",
                "explicit_or_inferred": {
                    "start_location": "contextual_inference",
                    "end_location": "explicit",
                    "transport_mode": "explicit",
                    "date": "explicit",
                    "journey_reason": "explicit",
                },
                "confidence": 0.92,
                "notes": ["Origin comes from the immediately preceding narrator statement."],
            }],
            "telemetry": {
                "task": task,
                "backend": "teaching",
                "provider": self.provider,
                "model": self.model,
                "success": True,
            },
        }


class HallucinatedEvidenceClient:
    """Deterministic response whose plausible quotation is absent."""

    provider = "teaching"
    model = "hallucinated-evidence-example"

    def complete_json(
        self, task: str, prompt: str, *, input_text: str | None = None
    ) -> dict[str, Any]:
        return {
            "journeys": [{
                "start_location": "Amsterdam",
                "end_location": "Brussels",
                "transport_mode": "train",
                "date": None,
                "journey_reason": None,
                "evidence_quote": "I boarded the train in Amsterdam and arrived in Brussels.",
                "explicit_or_inferred": {
                    "start_location": "explicit",
                    "end_location": "explicit",
                    "transport_mode": "explicit",
                    "date": "missing",
                    "journey_reason": "missing",
                },
                "confidence": 0.99,
            }],
        }


class InvalidStatusClient:
    """Deterministic response containing invalid status and confidence values."""

    provider = "teaching"
    model = "invalid-status-example"

    def complete_json(
        self, task: str, prompt: str, *, input_text: str | None = None
    ) -> dict[str, Any]:
        return {
            "journeys": [{
                "start_location": "Amsterdam",
                "end_location": "Brussels",
                "transport_mode": None,
                "date": "tomorrow",
                "journey_reason": None,
                "evidence_quote": "The next morning I travelled by train to Brussels to join my sister.",
                "explicit_or_inferred": {
                    "start_location": "probably",
                    "end_location": "explicit",
                    "transport_mode": "explicit",
                    "date": "missing",
                    "journey_reason": "missing",
                },
                "confidence": 1.4,
            }],
        }


class NullFriendlyClient:
    """Deterministic response that preserves unsupported fields as null."""

    provider = "teaching"
    model = "null-friendly-example"

    def complete_json(
        self, task: str, prompt: str, *, input_text: str | None = None
    ) -> dict[str, Any]:
        source = input_text or "I left Cambridge and travelled to London."
        return {
            "journeys": [{
                "start_location": "Cambridge",
                "end_location": "London",
                "transport_mode": None,
                "date": None,
                "journey_reason": None,
                "evidence_quote": source,
                "explicit_or_inferred": {
                    "start_location": "explicit",
                    "end_location": "explicit",
                    "transport_mode": "missing",
                    "date": "missing",
                    "journey_reason": "missing",
                },
                "confidence": 0.95,
            }],
        }
