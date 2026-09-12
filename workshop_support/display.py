"""
sh2026_display.py
-----------------
Display helpers for the SH2026 workshop notebooks.

Purpose: humanities participants should read HIGHLIGHTED TEXT, not span offsets
and not raw JSON. Every function here turns a data structure into something a
non-programmer can evaluate at a glance.

No third-party dependencies beyond IPython (already present in Colab/Jupyter).
Works with or without spaCy installed.

These helpers deliberately live in the conference repository rather than the
reusable package because their presentation and wording are workshop-specific.
"""

from __future__ import annotations

import html as _html
from typing import Any, Iterable, Mapping, Sequence

try:
    from IPython.display import HTML, display
except ImportError:  # pragma: no cover - allows plain-python import for tests
    HTML = None
    display = print


# Okabe-Ito palette: distinguishable under all common forms of colour vision
# deficiency. Never rely on colour alone; every span also carries a text label.
_PALETTE = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#999999",
]

_LABEL_COLOURS: dict[str, str] = {}


def colour_for(label: str) -> str:
    """Stable colour per label, assigned in first-seen order."""
    if label not in _LABEL_COLOURS:
        _LABEL_COLOURS[label] = _PALETTE[len(_LABEL_COLOURS) % len(_PALETTE)]
    return _LABEL_COLOURS[label]


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _sorted_non_overlapping(spans: Sequence[Mapping]) -> list[Mapping]:
    """Sort by start; drop later spans that overlap an already-kept span.

    Overlaps are dropped rather than nested because nested <mark> elements
    render unpredictably. Dropped spans are reported by the caller.
    """
    kept: list[Mapping] = []
    last_end = -1
    for s in sorted(spans, key=lambda x: (x["start_char"], -x["end_char"])):
        if s["start_char"] >= last_end:
            kept.append(s)
            last_end = s["end_char"]
    return kept


def spans_html(text: str, spans: Sequence[Mapping], label_key: str = "label") -> str:
    """Return HTML for `text` with `spans` highlighted inline."""
    kept = _sorted_non_overlapping(spans)
    parts: list[str] = []
    cursor = 0
    for s in kept:
        start, end = s["start_char"], s["end_char"]
        label = s.get(label_key) or s.get("label") or "SPAN"
        colour = colour_for(label)
        parts.append(_esc(text[cursor:start]))
        parts.append(
            f'<mark style="background:{colour}33;border-bottom:3px solid {colour};'
            f'padding:1px 2px;border-radius:3px;">'
            f"{_esc(text[start:end])}"
            f'<sup style="font-size:0.62em;font-weight:700;color:#333;'
            f'margin-left:3px;letter-spacing:0.03em;">{_esc(label)}</sup>'
            f"</mark>"
        )
        cursor = end
    parts.append(_esc(text[cursor:]))
    body = "".join(parts)
    dropped = len(spans) - len(kept)
    note = ""
    if dropped:
        note = (
            f'<div style="font-size:0.8em;color:#a33;margin-top:6px;">'
            f"{dropped} overlapping span(s) not drawn. Inspect the table for the full list."
            f"</div>"
        )
    return (
        f'<div style="font-family:Georgia,serif;font-size:1.06em;line-height:2.1;'
        f'padding:14px 16px;border:1px solid #ddd;border-radius:6px;background:#fff;">'
        f"{body}{note}</div>"
    )


def show_spans(text: str, spans: Sequence[Mapping], title: str | None = None,
               label_key: str = "label") -> None:
    """Render one annotated passage. Use instead of display(pd.DataFrame(spans))."""
    head = (
        f'<div style="font-family:system-ui,sans-serif;font-weight:600;'
        f'margin:14px 0 6px;color:#222;">{_esc(title)}</div>' if title else ""
    )
    counts: dict[str, int] = {}
    for s in spans:
        lab = s.get(label_key) or s.get("label") or "SPAN"
        counts[lab] = counts.get(lab, 0) + 1
    legend = " ".join(
        f'<span style="display:inline-block;margin:2px 8px 2px 0;font-size:0.78em;'
        f'font-family:system-ui,sans-serif;">'
        f'<span style="display:inline-block;width:11px;height:11px;background:{colour_for(k)};'
        f'border-radius:2px;vertical-align:-1px;margin-right:4px;"></span>{_esc(k)} ({v})</span>'
        for k, v in sorted(counts.items())
    )
    if not spans:
        legend = ('<span style="font-size:0.8em;color:#a33;'
                  'font-family:system-ui,sans-serif;">No spans returned.</span>')
    display(HTML(head + spans_html(text, spans, label_key) +
                 f'<div style="margin-top:7px;">{legend}</div>'))


def compare_spans(text: str, by_method: Mapping[str, Sequence[Mapping]],
                  label_key: str = "label") -> None:
    """Stack the same passage once per method, highlighted.

    This is the single most useful cell in the workshop: it shows WHERE methods
    disagree, in the text itself, with no metric to interpret.
    """
    blocks = []
    for method, spans in by_method.items():
        found = ", ".join(s["text"] for s in sorted(spans, key=lambda x: x["start_char"])) or "nothing"
        blocks.append(
            f'<div style="margin-bottom:16px;">'
            f'<div style="font-family:system-ui,sans-serif;font-size:0.85em;'
            f'font-weight:700;color:#444;margin-bottom:4px;letter-spacing:0.02em;">'
            f"{_esc(method)}</div>"
            f"{spans_html(text, spans, label_key)}"
            f'<div style="font-family:system-ui,sans-serif;font-size:0.76em;'
            f'color:#666;margin-top:4px;">found: {_esc(found)}</div>'
            f"</div>"
        )
    display(HTML("".join(blocks)))


_STATUS_STYLE = {
    "explicit": ("#009E73", "stated in the text"),
    "contextual_inference": ("#E69F00", "inferred from context"),
    "missing": ("#999999", "not in the source"),
}


def show_journey(journey: Mapping, source: str | None = None) -> None:
    """Render a structured journey record as a provenance card.

    Replaces print(json.dumps(journey, indent=2)), which is ~30 lines of
    unreadable output for a non-programmer.
    """
    status = journey.get("explicit_or_inferred") or {}
    fields = ["start_location", "end_location", "transport_mode", "date", "journey_reason"]
    rows = []
    for f in fields:
        value = journey.get(f)
        st = status.get(f, "missing" if value in (None, "") else "explicit")
        colour, gloss = _STATUS_STYLE.get(st, ("#D55E00", "unrecognised status"))
        shown = _esc(value) if value not in (None, "") else "<em style='color:#999;'>null</em>"
        rows.append(
            f"<tr>"
            f'<td style="padding:6px 12px 6px 0;color:#555;font-size:0.85em;'
            f'white-space:nowrap;">{_esc(f.replace("_", " "))}</td>'
            f'<td style="padding:6px 12px 6px 0;font-weight:600;">{shown}</td>'
            f'<td style="padding:6px 0;"><span style="background:{colour}22;color:#222;'
            f'border:1px solid {colour};border-radius:10px;padding:1px 9px;'
            f'font-size:0.72em;white-space:nowrap;">{_esc(st)}</span>'
            f'<span style="color:#777;font-size:0.72em;margin-left:7px;">{_esc(gloss)}</span></td>'
            f"</tr>"
        )

    grounded = journey.get("evidence_grounded")
    if grounded is True:
        banner = ("#009E73", "Evidence quote found in the source. Offsets computed locally.")
    elif grounded is False:
        banner = ("#D55E00", "Evidence quote NOT found in the source. Not usable as evidence.")
    else:
        banner = ("#999999", "Grounding not recorded.")

    quote = journey.get("evidence_quote")
    ev_html = ""
    if quote and source and quote in source:
        idx = source.index(quote)
        ev_html = spans_html(
            source,
            [{"start_char": idx, "end_char": idx + len(quote),
              "label": "EVIDENCE", "text": quote}],
        )
    elif quote:
        ev_html = (
            f'<div style="font-family:Georgia,serif;padding:12px 14px;border:1px dashed #D55E00;'
            f'border-radius:6px;background:#fff6f2;">{_esc(quote)}'
            f'<div style="font-family:system-ui,sans-serif;font-size:0.76em;color:#a33;'
            f'margin-top:6px;">This wording does not occur in the source passage.</div></div>'
        )

    review = journey.get("requires_review")
    notes = journey.get("review_notes") or journey.get("notes") or []
    if isinstance(notes, str):
        notes = [notes]
    notes_html = ""
    if notes:
        items = "".join(f"<li>{_esc(n)}</li>" for n in notes)
        notes_html = (
            f'<div style="font-family:system-ui,sans-serif;font-size:0.8em;color:#555;'
            f'margin-top:10px;">Review notes:<ul style="margin:4px 0 0 18px;padding:0;">'
            f"{items}</ul></div>"
        )

    display(HTML(
        f'<div style="font-family:system-ui,sans-serif;border:1px solid #ddd;'
        f'border-radius:8px;padding:16px 18px;background:#fff;max-width:760px;">'
        f'<div style="background:{banner[0]}18;border-left:4px solid {banner[0]};'
        f'padding:8px 12px;margin-bottom:14px;font-size:0.85em;">{_esc(banner[1])}</div>'
        f'<table style="border-collapse:collapse;margin-bottom:14px;">{"".join(rows)}</table>'
        f'<div style="font-size:0.8em;color:#555;margin-bottom:5px;">Evidence quote, located in the source:</div>'
        f"{ev_html}"
        f'<div style="font-size:0.82em;margin-top:12px;">'
        f'Requires human review: <strong>{_esc(review)}</strong></div>'
        f"{notes_html}</div>"
    ))


def show_fields(record: Mapping, fields: Iterable[str] | None = None,
                title: str | None = None) -> None:
    """Small key/value card. Replaces print(json.dumps(...)) for short records."""
    keys = list(fields) if fields else list(record.keys())
    rows = "".join(
        f'<tr><td style="padding:4px 14px 4px 0;color:#555;font-size:0.85em;'
        f'white-space:nowrap;">{_esc(k)}</td>'
        f'<td style="padding:4px 0;font-weight:600;">'
        f'{_esc(record.get(k)) if record.get(k) not in (None, "") else "<em style=color:#999>null</em>"}'
        f"</td></tr>"
        for k in keys
    )
    head = (f'<div style="font-weight:600;margin-bottom:6px;">{_esc(title)}</div>'
            if title else "")
    display(HTML(
        f'<div style="font-family:system-ui,sans-serif;border:1px solid #e2e2e2;'
        f'border-radius:6px;padding:12px 14px;display:inline-block;background:#fff;">'
        f'{head}<table style="border-collapse:collapse;">{rows}</table></div>'
    ))


def checkpoint(message: str, ok: bool = True) -> None:
    """Friendly end-of-section marker. Use instead of a bare assert."""
    colour, mark = ("#009E73", "&#10003;") if ok else ("#D55E00", "&#10007;")
    display(HTML(
        f'<div style="font-family:system-ui,sans-serif;background:{colour}18;'
        f'border-left:4px solid {colour};padding:9px 13px;margin:12px 0;'
        f'border-radius:0 5px 5px 0;font-size:0.9em;">'
        f'<strong style="color:{colour};">{mark}</strong> {_esc(message)}</div>'
    ))
