from __future__ import annotations

from importlib import metadata

from spatio_textual.journeys import JourneyExtractor

from workshop.sh2026_setup import PACKAGE_VERSION
from workshop_support import (
    GroundedClient,
    HallucinatedEvidenceClient,
    InvalidStatusClient,
    NullFriendlyClient,
)


SOURCE = (
    "We had been living in Amsterdam. "
    "The next morning I travelled by train to Brussels to join my sister."
)


def test_project_records_the_installed_package_version():
    assert metadata.version("spatio-textual") == PACKAGE_VERSION


def test_grounded_and_hallucinated_clients_expose_different_provenance():
    grounded = JourneyExtractor(client=GroundedClient()).extract(SOURCE, file_id="grounded")["journeys"][0]
    hallucinated = JourneyExtractor(client=HallucinatedEvidenceClient()).extract(
        SOURCE, file_id="hallucinated"
    )["journeys"][0]

    assert grounded["evidence_grounded"] is True
    assert hallucinated["evidence_grounded"] is False
    assert hallucinated["requires_review"] is True


def test_invalid_and_null_clients_remain_auditable():
    invalid = JourneyExtractor(client=InvalidStatusClient()).extract(
        SOURCE, file_id="invalid"
    )["journeys"][0]
    null_record = JourneyExtractor(client=NullFriendlyClient()).extract(
        "I left Cambridge and travelled to London.", file_id="null"
    )["journeys"][0]

    assert invalid["requires_review"] is True
    assert invalid["confidence"] == 1.0
    assert null_record["transport_mode"] is None
    assert null_record["explicit_or_inferred"]["transport_mode"] == "missing"
