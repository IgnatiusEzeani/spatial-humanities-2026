"""
workshop_support/annotate.py
----------------------------
Point-and-click span annotation for the workshop, with a typing fallback.

Why not just have participants type the phrase
----------------------------------------------
Typing has a failure mode that teaches nothing: a typo produces "not found,
check the spelling", and the participant debugs a string instead of thinking
about the annotation. In a room of mixed coding experience that is where the
time goes.

Choosing the FIRST and LAST word of a span from two dropdowns removes the typing
and, more usefully, makes the boundary decision explicit. "Does `Lowther Hall`
include `Hall`?" stops being a question about quoting and becomes a question you
answer by picking a different end word, which is exactly what Exercise A is for.

Colab support
-------------
Colab ships ipywidgets. If the import fails, or widgets do not render, this
degrades to `manual_annotation()`, which is the original typed list. Never let a
widget be the only route: a workshop that depends on one is a workshop that can
stop.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence

LABELS = ("TOPONYM", "GEONOUN", "RELATION", "DISTANCE", "TIME")

_WORD = re.compile(r"\S+")


def tokenize(text: str) -> list[dict]:
    """Whitespace tokens with their character offsets.

    Offsets are kept from the start so a span assembled from token indices can
    be reported in characters, which is what every scorer here expects. Nothing
    downstream ever has to re-find a string.
    """
    return [{"i": i, "text": m.group(), "start": m.start(), "end": m.end()}
            for i, m in enumerate(_WORD.finditer(text))]


def span_from_tokens(text: str, tokens: Sequence[dict], i: int, j: int,
                     label: str) -> dict:
    """Build a character span from the first and last token index, inclusive.

    Trailing punctuation is trimmed from the end but NOT from the start, because
    a leading quotation mark is sometimes part of a title and a trailing comma
    never is. This is a small annotation policy decision and it is stated here
    rather than buried.
    """
    if j < i:
        i, j = j, i
    start, end = tokens[i]["start"], tokens[j]["end"]
    while end > start and text[end - 1] in ",.;:!?)]}\u2019\u201d":
        end -= 1
    return {"start_char": start, "end_char": end, "label": label,
            "text": text[start:end]}


# --------------------------------------------------------------------------
# fallback: no widgets
# --------------------------------------------------------------------------

def manual_annotation(text: str, pairs: Sequence[tuple[str, str]],
                      verbose: bool = True) -> list[dict]:
    """Typed (phrase, label) pairs, located in the text. The original route."""
    out = []
    for phrase, label in pairs:
        i = text.find(phrase)
        if i < 0:
            if verbose:
                print(f"  not found, check the spelling: {phrase!r}")
            continue
        out.append({"start_char": i, "end_char": i + len(phrase),
                    "label": label, "text": phrase})
    return out


# --------------------------------------------------------------------------
# widget route
# --------------------------------------------------------------------------

class Annotator:
    """Holds the participant's spans. `.spans` is a plain list of dicts."""

    def __init__(self, text: str, labels: Sequence[str] = LABELS,
                 renderer: Callable | None = None):
        self.text = text
        self.labels = list(labels)
        self.tokens = tokenize(text)
        self.spans: list[dict] = []
        self._render = renderer

    # -- operations, usable with or without widgets -------------------------
    def add(self, i: int, j: int, label: str) -> dict | None:
        s = span_from_tokens(self.text, self.tokens, i, j, label)
        if any(s["start_char"] < x["end_char"] and s["end_char"] > x["start_char"]
               for x in self.spans):
            return None                      # overlapping: reject, do not stack
        self.spans.append(s)
        self.spans.sort(key=lambda x: x["start_char"])
        return s

    def undo(self) -> None:
        if self.spans:
            self.spans.pop()

    def clear(self) -> None:
        self.spans.clear()

    def summary(self) -> str:
        if not self.spans:
            return "nothing marked yet"
        return ", ".join(f"{s['text']} [{s['label']}]" for s in self.spans)


def annotation_widget(text: str, labels: Sequence[str] = LABELS,
                      renderer: Callable | None = None) -> Annotator:
    """Two token dropdowns, a label dropdown, and add/undo/clear.

    Returns the Annotator immediately, so the next cell can read `.spans`
    whether or not the widgets rendered.
    """
    ann = Annotator(text, labels, renderer)

    try:
        import ipywidgets as w
        from IPython.display import display, clear_output
    except ImportError:
        print("ipywidgets is unavailable here. Use the typed route instead:\n"
              "    spans = manual_annotation(text, [(\"Penrith\", \"TOPONYM\")])")
        return ann

    opts = [(f'{t["i"]:>2}  {t["text"]}', t["i"]) for t in ann.tokens]
    first = w.Dropdown(options=opts, value=0, description="from word:",
                       layout=w.Layout(width="260px"))
    last = w.Dropdown(options=opts, value=0, description="to word:",
                      layout=w.Layout(width="260px"))
    lab = w.Dropdown(options=list(labels), value=labels[0], description="label:",
                     layout=w.Layout(width="220px"))
    add = w.Button(description="Add span", button_style="success",
                   icon="plus", layout=w.Layout(width="120px"))
    undo = w.Button(description="Undo", icon="rotate-left",
                    layout=w.Layout(width="100px"))
    clear = w.Button(description="Clear", icon="trash",
                     layout=w.Layout(width="100px"))
    note = w.HTML("")
    out = w.Output()

    def redraw(msg: str = "") -> None:
        note.value = (f'<span style="font-family:system-ui;font-size:12px;'
                      f'color:#C4622D;">{msg}</span>')
        with out:
            clear_output(wait=True)
            if ann._render:
                ann._render(ann.text, ann.spans, title="Your annotation")
            else:
                print(ann.summary())

    def on_add(_):
        s = ann.add(first.value, last.value, lab.value)
        redraw("" if s else "that overlaps a span you already marked")

    def on_undo(_):
        ann.undo(); redraw()

    def on_clear(_):
        ann.clear(); redraw()

    add.on_click(on_add); undo.on_click(on_undo); clear.on_click(on_clear)

    def sync(change):
        # a span almost always starts and ends on the same word, so move the
        # end marker with the start unless the participant has moved it past
        if change["name"] == "value" and last.value < first.value:
            last.value = first.value
    first.observe(sync, names="value")

    display(w.VBox([w.HBox([first, last, lab]),
                    w.HBox([add, undo, clear, note]), out]))
    redraw()
    return ann
