#!/usr/bin/env python3
"""
recover_setup_cells.py
----------------------
Recover the ORIGINAL setup cells from git history, then re-apply the migration.

    python3 workshop/recover_setup_cells.py --dir workshop/full_day --dry-run
    python3 workshop/recover_setup_cells.py --dir workshop/full_day

Why this is needed
------------------
An earlier version of fix_notebook_setup.py replaced each setup cell wholesale
and kept only what a heuristic recognised as an import. That heuristic lost
`json`, `time`, `FAST_MODE`, `transformer_rows` and similar, and the loss is
already committed. The notebooks now fail with NameError on names that were
defined in a cell that no longer exists.

Git still has them. This walks back through history for each notebook, finds the
newest version whose setup cell still contained the bootstrap, lifts that cell
out, and puts it back. Running fix_notebook_setup.py afterwards then migrates it
properly, keeping everything that is not bootstrap.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

MARKERS = ("git clone", "subprocess.run", "pip install")


def commits_for(path: Path) -> list[str]:
    # --follow is required: these notebooks moved from workshop/ into
    # workshop/full_day/, and without it git log stops at the rename and
    # reports no history at all.
    out = subprocess.run(
        ["git", "log", "--all", "--follow", "--format=%H", "--", str(path)],
        capture_output=True, text=True)
    return out.stdout.split()


def candidate_paths(path: Path) -> list[str]:
    """The path now, and where it used to live before the move."""
    return [str(path), f"workshop/{path.name}", f"projects/sh2026/workshop/{path.name}"]


def version_at(sha: str, path: Path) -> dict | None:
    for p in candidate_paths(path):
        out = subprocess.run(["git", "show", f"{sha}:{p}"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            continue
        try:
            return json.loads(out.stdout)
        except json.JSONDecodeError:
            continue
    return None


def setup_cell_of(nb: dict) -> tuple[int, str] | None:
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if sum(m in src for m in MARKERS) >= 2:
            return i, src
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print(f"{'notebook':44s} {'found in':>10s}  {'lines':>5s}  action")
    for path in sorted(a.dir.glob("*.ipynb")):
        current = json.loads(path.read_text(encoding="utf-8"))
        if setup_cell_of(current):
            print(f"{path.name:44s} {'':>10s}  {'':>5s}  already original, skipped")
            continue

        recovered = None
        for sha in commits_for(path):
            old = version_at(sha, path)
            if not old:
                continue
            hit = setup_cell_of(old)
            if hit:
                recovered = (sha[:7], hit[1])
                break

        if not recovered:
            print(f"{path.name:44s} {'':>10s}  {'':>5s}  NOT FOUND in history")
            continue

        sha, src = recovered
        nlines = len([l for l in src.splitlines() if l.strip()])
        # put it back in place of the current migrated setup cell
        target = None
        for i, c in enumerate(current["cells"]):
            if c["cell_type"] == "code" and "sh2026_setup" in "".join(c["source"]):
                target = i
                break
        if target is None:
            print(f"{path.name:44s} {sha:>10s}  {nlines:5d}  no migrated cell to replace")
            continue

        if not a.dry_run:
            current["cells"][target]["source"] = src.splitlines(keepends=True)
            path.write_text(json.dumps(current, indent=1, ensure_ascii=False),
                            encoding="utf-8")
        print(f"{path.name:44s} {sha:>10s}  {nlines:5d}  restored at cell {target}")

    if a.dry_run:
        print("\n--dry-run: nothing written.")
    else:
        print("\nNow migrate them properly:")
        print("  python3 workshop/fix_notebook_setup.py --dir "
              f"{a.dir} --dry-run")
        print(f"  python3 workshop/fix_notebook_setup.py --dir {a.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
