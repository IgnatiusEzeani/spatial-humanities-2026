#!/usr/bin/env python3
"""
fix_notebook_setup.py  (v2)
---------------------------
Repoint each notebook's setup cell at the shared module, WITHOUT discarding the
notebook's own imports.

    python3 workshop/fix_notebook_setup.py --dir workshop/full_day --dry-run
    python3 workshop/fix_notebook_setup.py --dir workshop/full_day

Why v2
------
v1 replaced the whole setup cell and tried to preserve "any imports below it"
with a heuristic. The heuristic dropped exactly the imports that mattered:
RuleGazetteerAnnotator, load_gold, filter_supported_gold_labels, gazetteer_path.
Every notebook then failed with a NameError cascade from cell 3 onward, and
because the cells still RAN (they just raised), the runner reported "ok".

v2 edits the cell line by line instead. It removes only the bootstrap lines
(clone, pip, chdir, sys.path, repo_dir) and prepends the shared setup. Anything
else in that cell, above all the project imports, is kept verbatim.

The lesson, which is the same one that produced the collapsed notebook lines
earlier: replacing a whole thing is easy to write and easy to get wrong. Editing
the specific lines you understand is slower and survives contact with reality.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

REPO = "IgnatiusEzeani/spatial-humanities-2026"
REF = "sh2026-workshop"

HEADER = f"""!wget -q https://raw.githubusercontent.com/{REPO}/{REF}/workshop/sh2026_setup.py

import sh2026_setup as sh
ctx = sh.setup()

# The notebooks below were written against these two names. Bind them from the
# shared context rather than rewriting every downstream cell.
repo_dir = ctx.repo
data_dir = ctx.data
"""

SETUP_MARKERS = ("git clone", "pip install", "requirements-", "spatio-textual.git",
                 "repo_dir =", "sys.path.insert", "subprocess.run")

BOOTSTRAP_MODULES = {"subprocess", "sys", "os", "pathlib", "shutil", "site",
                     "importlib", "sh2026_setup"}

# Paths moved when the workshop left the spatio-textual repo.
PATH_FIXES = [
    # Path-segment form, with and without spaces. This is the one that mattered:
    # every notebook builds its data path as
    #   repo_dir/"projects"/"sh2026"/"workshop"/"data"/...
    # which stopped existing when the workshop moved out of spatio-textual.
    # The imports were fine all along; the directory was not.
    ('"projects"/"sh2026"/"workshop"', '"workshop"'),
    ('"projects" / "sh2026" / "workshop"', '"workshop"'),
    ("'projects'/'sh2026'/'workshop'", "'workshop'"),
    ("'projects' / 'sh2026' / 'workshop'", "'workshop'"),
    ('"projects/sh2026/workshop"', '"workshop"'),
    ("'projects/sh2026/workshop'", "'workshop'"),
    ("projects/sh2026/workshop/", "workshop/"),
    # the cached teaching fallbacks moved too
    ('"projects" / "sh2026" / "demo"', '"demo"'),
    ('"projects"/"sh2026"/"demo"', '"demo"'),
    ("'projects' / 'sh2026' / 'demo'", "'demo'"),
    ("projects/sh2026/demo/", "demo/"),
    # anything else under the old tree
    ('"projects" / "sh2026"', '"."'),
    ('"projects"/"sh2026"', '"."'),
]


def keep_statement(node: ast.AST, seg: str) -> bool:
    """Should this top-level statement survive?

    Whole STATEMENTS, not lines. Removing lines orphaned `if`/`else` headers
    whose bodies were bootstrap, producing cells that would not parse.
    """
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] not in BOOTSTRAP_MODULES
    if isinstance(node, ast.Import):
        # Keep the NON-bootstrap names. `import os, subprocess, sys, json, time`
        # is one statement; dropping it whole because of `os` also removed json
        # and time, and seven notebooks then failed on NameError: json.
        return any(a.name.split(".")[0] not in BOOTSTRAP_MODULES
                   for a in node.names)
    if isinstance(node, (ast.If, ast.Try, ast.While, ast.For)):
        # control flow in a setup cell is always the clone-or-reuse dance
        return not any(m in seg for m in SETUP_MARKERS + ("Path.cwd", "chdir"))
    if isinstance(node, ast.Expr):
        return not (seg.startswith("os.") or seg.startswith("sys.")
                    or any(m in seg for m in ("subprocess", "Repository:")))
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return not any(m in seg for m in
                       ("subprocess", "Path.cwd", "REPO", "BRANCH", "clone"))
    if isinstance(node, ast.Expr) or seg.startswith("os."):
        return False
    return True


def strip_bootstrap(src: str) -> str:
    """Return the non-bootstrap statements of a setup cell, verbatim."""
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith(("!", "%")))
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ""                       # unparseable: keep nothing, report 0
    kept = []
    for node in tree.body:
        seg = ast.get_source_segment(code, node) or ""
        if isinstance(node, ast.Import):
            names = [a for a in node.names
                     if a.name.split(".")[0] not in BOOTSTRAP_MODULES]
            if names:
                kept.append("import " + ", ".join(
                    a.name + (f" as {a.asname}" if a.asname else "")
                    for a in names))
            continue
        if keep_statement(node, seg):
            kept.append(seg)
    out = "\n".join(kept)
    for a, b in PATH_FIXES:
        out = out.replace(a, b)
    return out.strip("\n")


def process(path: Path, dry: bool) -> dict:
    nb = json.loads(path.read_text(encoding="utf-8"))
    r = {"setup": 0, "kept_lines": 0, "paths": 0, "showref": 0, "newlines": 0}

    for cell in nb["cells"]:
        src = "".join(cell["source"])

        # ALREADY MIGRATED by an earlier run: the bootstrap markers are gone,
        # so the branch below never fires. v1 removed `repo_dir =` without
        # replacing it, which is why every downstream cell raised NameError
        # while the runner still reported "ok". Repair in place, idempotently.
        if (cell["cell_type"] == "code" and "sh2026_setup" in src
                and "repo_dir = ctx.repo" not in src):
            add = ("\n# Bound from the shared context: the cells below were "
                   "written against\n# these names.\nrepo_dir = ctx.repo\n"
                   "data_dir = ctx.data\n")
            anchor = "ctx = sh.setup()\n"
            new = (src.replace(anchor, anchor + add, 1) if anchor in src
                   else src.rstrip("\n") + "\n" + add)
            cell["source"] = new.splitlines(keepends=True)
            r["setup"] += 1
            r["kept_lines"] = len([l for l in new.splitlines() if l.strip()])
            src = new

        if cell["cell_type"] == "code" and sum(m in src for m in SETUP_MARKERS) >= 2:
            kept = strip_bootstrap(src)
            r["kept_lines"] = len([l for l in kept.splitlines() if l.strip()])
            new = HEADER + ("\n" + kept + "\n" if kept else "")
            cell["source"] = new.splitlines(keepends=True)
            r["setup"] += 1
            continue

        if cell["cell_type"] == "code":
            fixed = src
            for a, b in PATH_FIXES:
                fixed = fixed.replace(a, b)
            if fixed != src:
                cell["source"] = fixed.splitlines(keepends=True)
                src = fixed
                r["paths"] += 1

        if cell["cell_type"] == "code" and re.search(r"SHOW_REFERENCE\s*=\s*True", src):
            cell["source"] = re.sub(
                r"SHOW_REFERENCE\s*=\s*True[^\n]*",
                'SHOW_REFERENCE = False  # @param {type:"boolean"}',
                src).splitlines(keepends=True)
            r["showref"] += 1
            continue

        fixed = "".join(cell["source"]).splitlines(keepends=True)
        if fixed != cell["source"]:
            cell["source"] = fixed
            r["newlines"] += 1

    if not dry:
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = sorted(a.dir.glob("*.ipynb"))
    if not files:
        print(f"no notebooks in {a.dir}")
        return 1

    print(f"{'notebook':44s} {'setup':>6s} {'kept':>6s} {'paths':>6s} "
          f"{'showref':>8s} {'nl':>4s}")
    for f in files:
        r = process(f, a.dry_run)
        print(f"{f.name:44s} {r['setup']:6d} {r['kept_lines']:6d} "
              f"{r['paths']:6d} {r['showref']:8d} {r['newlines']:4d}")
    print("\n`kept` is the number of non-blank lines preserved from the original "
          "setup cell\n(project imports, constants). A ZERO there on a notebook "
          "that needs imports\nmeans they were lost: check before running anything.")
    if a.dry_run:
        print("\n--dry-run: nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
