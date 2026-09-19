#!/usr/bin/env python3
"""
fix_notebook_setup.py
---------------------
Repoint every workshop notebook at the shared setup module.

    python3 fix_notebook_setup.py --dir workshop/full_day --dry-run
    python3 fix_notebook_setup.py --dir workshop/full_day

What it fixes, in each notebook
-------------------------------
1. THE SETUP CELL. Five different versions exist across the ten notebooks, four
   of which run `pip install -e .`. That cannot work: this repo has no
   pyproject.toml and no setup.py, so every self-study user gets
   "does not appear to be a Python project". Replaced with the two-line call to
   sh2026_setup, which clones once, installs from requirements-workshop.txt,
   and puts the repo root on sys.path.

2. THE COLAB BADGE. Points at the old repository and the old branch.

3. SHOW_REFERENCE. Defaults to True in notebook 01, which hands over the answer
   key and destroys the exercise the preceding cells spent fifteen minutes
   building.

4. nbformat source lines. Any cell whose lines lack trailing newlines collapses
   to one line when a reader joins them: markdown stops rendering and code stops
   parsing. Repaired in place.

Always run with --dry-run first. It reports what it would change and writes
nothing.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = "IgnatiusEzeani/spatial-humanities-2026"
REF = "sh2026-workshop"

SETUP = f"""!wget -q https://raw.githubusercontent.com/{REPO}/{REF}/workshop/sh2026_setup.py

import sh2026_setup as sh
ctx = sh.setup()

from workshop_support.display import (show_spans, compare_spans, show_journey,
                                      show_fields, checkpoint)
"""

BADGE = re.compile(
    r"\[!\[Open In Colab\]\([^)]*\)\]\(https://colab\.research\.google\.com/github/"
    r"[^)]*\)")

# a cell is a setup cell if it does any of these
SETUP_MARKERS = ("git clone", "pip install", "requirements-lite",
                 "spatio-textual.git", "repo_dir =", "sys.path.insert")


def fix_source(src: list[str]) -> tuple[list[str], bool]:
    """Ensure every line but the last ends with a newline."""
    joined = "".join(src)
    fixed = joined.splitlines(keepends=True)
    return fixed, fixed != src


def process(path: Path, dry: bool) -> dict:
    nb = json.loads(path.read_text(encoding="utf-8"))
    report = {"setup": 0, "badge": 0, "show_reference": 0, "newlines": 0,
              "cells": len(nb["cells"])}

    for cell in nb["cells"]:
        src = "".join(cell["source"])

        if cell["cell_type"] == "code":
            # 1. setup cell: replace wholesale, keeping any imports below it
            if sum(m in src for m in SETUP_MARKERS) >= 2:
                tail = []
                for line in src.splitlines(keepends=True):
                    s = line.strip()
                    if (s.startswith("import ") or s.startswith("from ")) and \
                            "sh2026_setup" not in s and "workshop_support" not in s \
                            and "subprocess" not in s and "pathlib" not in s \
                            and "sys" not in s and "os" not in s:
                        tail.append(line)
                cell["source"] = (SETUP + ("\n" + "".join(tail) if tail else "")
                                  ).splitlines(keepends=True)
                report["setup"] += 1
                continue

            # 3. the answer key
            if re.search(r"SHOW_REFERENCE\s*=\s*True", src):
                cell["source"] = re.sub(
                    r"SHOW_REFERENCE\s*=\s*True[^\n]*",
                    'SHOW_REFERENCE = False  # @param {type:"boolean"}',
                    src).splitlines(keepends=True)
                report["show_reference"] += 1
                continue

        else:
            # 2. badge
            if "Open In Colab" in src:
                new = BADGE.sub(
                    f"[![Open In Colab](https://colab.research.google.com/assets/"
                    f"colab-badge.svg)](https://colab.research.google.com/github/"
                    f"{REPO}/blob/{REF}/workshop/full_day/{path.name})", src)
                if new != src:
                    cell["source"] = new.splitlines(keepends=True)
                    report["badge"] += 1
                    continue

        # 4. newlines, on every cell
        fixed, changed = fix_source(cell["source"])
        if changed:
            cell["source"] = fixed
            report["newlines"] += 1

    if not dry:
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = sorted(a.dir.glob("*.ipynb"))
    if not files:
        print(f"no notebooks in {a.dir}")
        return 1

    print(f"{'notebook':44s} {'cells':>6s} {'setup':>6s} {'badge':>6s} "
          f"{'showref':>8s} {'nl':>5s}")
    total = {"setup": 0, "badge": 0, "show_reference": 0, "newlines": 0}
    for f in files:
        r = process(f, a.dry_run)
        for k in total:
            total[k] += r[k]
        print(f"{f.name:44s} {r['cells']:6d} {r['setup']:6d} {r['badge']:6d} "
              f"{r['show_reference']:8d} {r['newlines']:5d}")
    print(f"\n{'TOTAL':44s} {'':6s} {total['setup']:6d} {total['badge']:6d} "
          f"{total['show_reference']:8d} {total['newlines']:5d}")

    if a.dry_run:
        print("\n--dry-run: nothing written. Re-run without it to apply.")
    else:
        print("\nWritten. Now RUN each notebook once and commit the outputs: "
              "self-study\nnotebooks without outputs give a lone reader no way "
              "to tell whether their\nresult is right.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
