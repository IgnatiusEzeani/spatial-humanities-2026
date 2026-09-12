from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

EXTRACTION_RULE_VERSION = "sh2026-cldw-paragraph-v1"
MIN_CHARS = 80
MAX_CHARS = 1200
TARGET_MIN_PLACES = 2


def git_blob_sha(data: bytes) -> str:
    """Return the SHA-1 Git uses for a blob object."""
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _flatten_raw_with_place_spans(elem: ET.Element) -> tuple[str, list[tuple[int, int]]]:
    """Flatten mixed XML content while recording raw <cdplace> boundaries."""
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    length = 0

    def append(value: str | None) -> None:
        nonlocal length
        if value:
            pieces.append(value)
            length += len(value)

    def walk(node: ET.Element) -> None:
        nonlocal length
        is_place = _local_name(node.tag) == "cdplace"
        start = length if is_place else None
        append(node.text)
        for child in list(node):
            walk(child)
            append(child.tail)
        if is_place:
            assert start is not None
            spans.append((start, length))

    walk(elem)
    return "".join(pieces), spans


def _normalise_with_boundary_map(raw: str) -> tuple[str, list[int]]:
    """Collapse XML whitespace to one space and map every raw boundary.

    The boundary map has len(raw)+1 entries. A pending inter-token space is
    emitted immediately before the following non-space character so that a tag
    beginning after source whitespace receives the correct normalised offset.
    """
    out: list[str] = []
    boundary = [0] * (len(raw) + 1)
    pending_space = False

    for i, ch in enumerate(raw):
        if ch.isspace():
            boundary[i] = len(out)
            if out:
                pending_space = True
            boundary[i + 1] = len(out)
            continue

        if pending_space and out:
            out.append(" ")
            pending_space = False
        boundary[i] = len(out)
        out.append(ch)
        boundary[i + 1] = len(out)

    text = "".join(out)
    return text, boundary


def paragraph_record(paragraph: ET.Element) -> tuple[str, list[dict[str, Any]]]:
    raw, raw_spans = _flatten_raw_with_place_spans(paragraph)
    text, boundary = _normalise_with_boundary_map(raw)
    spans: list[dict[str, Any]] = []
    for idx, (raw_start, raw_end) in enumerate(sorted(raw_spans), start=1):
        start = boundary[raw_start]
        end = boundary[raw_end]
        mention = text[start:end]
        if not mention.strip():
            raise ValueError("Encountered empty <cdplace> after normalisation")
        spans.append(
            {
                "span_id": f"s{idx:03d}",
                "layer": "entity",
                "label": "TOPONYM",
                "text": mention,
                "start_char": start,
                "end_char": end,
                "conceptual_level": "location",
                "certainty": "explicit",
                "attributes": {"source_markup": "cdplace"},
                "notes": None,
            }
        )
    return text, spans


def _paragraphs(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter() if _local_name(elem.tag) == "p"]


def select_passage(root: ET.Element) -> tuple[int, str, list[dict[str, Any]], str]:
    candidates: list[tuple[int, str, list[dict[str, Any]]]] = []
    for ordinal, paragraph in enumerate(_paragraphs(root), start=1):
        text, spans = paragraph_record(paragraph)
        if MIN_CHARS <= len(text) <= MAX_CHARS and spans:
            candidates.append((ordinal, text, spans))
            if len(spans) >= TARGET_MIN_PLACES:
                return ordinal, text, spans, "first_paragraph_ge2_places"
    if candidates:
        ordinal, text, spans = candidates[0]
        return ordinal, text, spans, "fallback_first_paragraph_ge1_place"
    raise ValueError(
        f"No eligible paragraph with a <cdplace> mention and {MIN_CHARS}-{MAX_CHARS} normalised characters"
    )


def _parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Could not parse {path}: {exc}") from exc


def build_record(
    *,
    upstream_root: Path,
    entry: dict[str, Any],
    upstream: dict[str, Any],
) -> dict[str, Any]:
    relative_path = Path(entry["path"])
    path = upstream_root / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"Pinned CLDW source missing: {path}")

    data = path.read_bytes()
    actual_blob = git_blob_sha(data)
    expected_blob = str(entry["blob_sha"])
    if actual_blob != expected_blob:
        raise ValueError(
            f"Git blob mismatch for {relative_path}: expected {expected_blob}, got {actual_blob}"
        )

    root = _parse_xml(path)
    ordinal, text, spans, selection_tier = select_passage(root)
    for span in spans:
        a, b = span["start_char"], span["end_char"]
        if text[a:b] != span["text"]:
            raise AssertionError(
                f"Offset mismatch in {relative_path} paragraph {ordinal}: {span['text']!r} at {a}:{b}"
            )

    stem = relative_path.stem.replace("_cqp", "").replace("__", "_")
    example_id = f"cldw_external_{stem.lower()}"
    return {
        "schema_version": "spatio-textual-gold-0.1",
        "example_id": example_id,
        "title": f"CLDW external validation: {stem}",
        "text": text,
        "source": {
            "genre": "historical Lake District writing",
            "source_note": (
                f"Source-derived external-validation passage reconstructed from {upstream['repository']} "
                f"at commit {upstream['commit']}, file {relative_path}."
            ),
            "distribution_status": "source_derived_cc_by_nc_sa_4_0",
            "repository": upstream["repository"],
            "upstream_commit": upstream["commit"],
            "path": str(relative_path),
            "blob_sha": expected_blob,
            "paragraph_ordinal": ordinal,
            "selection_tier": selection_tier,
            "extraction_rule_version": EXTRACTION_RULE_VERSION,
            "license": upstream.get("license"),
            "reference": upstream.get("reference"),
        },
        "annotation_policy": "docs/EXTERNAL_VALIDATION_PROTOCOL.md",
        "reference_status": "adjudicated_reference",
        "spans": spans,
        "relations": [],
        "journeys": [],
        "adjudication_notes": [
            "TOPONYM reference spans are derived from the pre-existing CLDW <cdplace> gold markup.",
            "This record is for named-place external validation only; it does not validate the richer SH2026 ontology.",
        ],
    }


def build_dataset(manifest_path: Path, upstream_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "sh2026-cldw-external-manifest-v1":
        raise ValueError("Unsupported CLDW external manifest schema")
    upstream = manifest.get("upstream") or {}
    entries = manifest.get("files") or []
    expected_n = int((manifest.get("selection_policy") or {}).get("n_source_texts") or 0)
    if len(entries) != expected_n:
        raise ValueError(f"Manifest expected {expected_n} sources but lists {len(entries)}")

    records = [
        build_record(upstream_root=upstream_root, entry=entry, upstream=upstream)
        for entry in entries
    ]
    ids = [record["example_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Derived CLDW example IDs are not unique")
    return manifest, records


def write_dataset(records: list[dict[str, Any]], output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)
    output.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8"
    )
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frozen-source CLDW SH2026 external validation set")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("cldw_external_manifest_v1.json"),
    )
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("cldw_external_v1.jsonl"),
    )
    args = parser.parse_args()

    manifest, records = build_dataset(args.manifest, args.upstream_root)

    # Import here so the builder's XML/offset helpers remain usable standalone.
    from spatio_textual.gold import assert_valid_gold

    assert_valid_gold(records)
    digest = write_dataset(records, args.output)
    place_mentions = sum(len(record["spans"]) for record in records)
    print(f"Built {len(records)} CLDW external-validation passages with {place_mentions} gold place mentions")
    print(f"Upstream: {manifest['upstream']['repository']}@{manifest['upstream']['commit']}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
