from __future__ import annotations

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "benchmarks" / "build_cldw_external_v1.py"
spec = importlib.util.spec_from_file_location("build_cldw_external_v1", SCRIPT)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_git_blob_sha_matches_known_git_object_formula():
    assert builder.git_blob_sha(b"hello") == "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"


def test_mixed_content_normalisation_preserves_cdplace_offsets():
    paragraph = ET.fromstring(
        "<p> From <cdplace>Penrith</cdplace>  two roads lead to "
        "<cdplace><i>Pooley</i> Bridge</cdplace>, about six miles. </p>"
    )
    text, spans = builder.paragraph_record(paragraph)
    assert text == "From Penrith two roads lead to Pooley Bridge, about six miles."
    assert [span["text"] for span in spans] == ["Penrith", "Pooley Bridge"]
    for span in spans:
        assert text[span["start_char"]:span["end_char"]] == span["text"]


def test_selection_prefers_first_eligible_paragraph_with_two_places():
    root = ET.fromstring(
        "<text>"
        "<p>This paragraph names <cdplace>Keswick</cdplace> but is long enough to qualify as the one-place fallback candidate for testing.</p>"
        "<p>From <cdplace>Penrith</cdplace> the traveller continued by a winding road toward <cdplace>Ambleside</cdplace>, with several observations recorded along the route.</p>"
        "</text>"
    )
    ordinal, text, spans, tier = builder.select_passage(root)
    assert ordinal == 2
    assert tier == "first_paragraph_ge2_places"
    assert [span["text"] for span in spans] == ["Penrith", "Ambleside"]
    assert "winding road" in text


def test_build_record_rejects_changed_upstream_blob(tmp_path):
    source = tmp_path / "gold_standard" / "Example.xml"
    source.parent.mkdir(parents=True)
    source.write_text(
        "<text><p>From <cdplace>Keswick</cdplace> the road continues through the valley toward "
        "<cdplace>Ambleside</cdplace>, with enough descriptive prose to pass the minimum length.</p></text>",
        encoding="utf-8",
    )
    entry = {"path": "gold_standard/Example.xml", "blob_sha": "0" * 40}
    upstream = {
        "repository": "example/corpus",
        "commit": "deadbeef",
        "license": "test",
        "reference": "test",
    }
    try:
        builder.build_record(upstream_root=tmp_path, entry=entry, upstream=upstream)
    except ValueError as exc:
        assert "Git blob mismatch" in str(exc)
    else:
        raise AssertionError("Expected changed upstream bytes to be rejected")
