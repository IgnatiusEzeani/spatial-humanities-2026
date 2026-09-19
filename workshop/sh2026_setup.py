"""
sh2026_setup.py
---------------
ONE canonical setup path for every SH2026 workshop notebook.

Why this exists
---------------
The ten notebooks currently contain five different setup cells:

  00            clone -> /content/spatio-textual  + pip -r requirements-lite.txt
  01, 02, 03    cwd-check -> /content/spatio-textual + pip -r requirements-lite.txt
  04, 06, 07, 09  clone -> ./spatio-textual        + pip install -e .
  05            three-way check                     + pip install -e .
  08            clone -> ./spatio-textual          + pip install -e .[app]

Consequences:
  * different dependency sets between notebooks;
  * `repo_dir` exists in 00-03 but not in 04-09, so data paths diverge;
  * 04-09 write outputs to a cwd-relative sh2026_outputs/, 01-03 to repo_dir/sh2026_outputs/;
  * running 04+ in a runtime where 00 already chdir'd clones a NESTED repo;
  * ten clone+install cycles on shared conference Wi-Fi.

Usage in every notebook, as the first code cell:

    !wget -q https://raw.githubusercontent.com/IgnatiusEzeani/spatio-textual/<TAG>/projects/sh2026/workshop/sh2026_setup.py
    import sh2026_setup as sh
    ctx = sh.setup()

`ctx` gives you: ctx.repo, ctx.data, ctx.outputs, ctx.fast_mode, ctx.commit
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass

REPO_URL = "https://github.com/IgnatiusEzeani/spatio-textual.git"

# Pin a TAG for the workshop, not a branch. A branch can move under a
# participant mid-session; a tag cannot. Freeze this after the release gates pass.
REF = "main"

COLAB_ROOT = pathlib.Path("/content")


@dataclass
class Context:
    repo: pathlib.Path
    data: pathlib.Path
    outputs: pathlib.Path
    fast_mode: bool
    commit: str
    elapsed_s: float


def _in_colab() -> bool:
    return "google.colab" in sys.modules or COLAB_ROOT.exists()


def _looks_like_repo(p: pathlib.Path) -> bool:
    return (p / "spatio_textual").exists() and (p / "projects" / "sh2026").exists()


def _find_repo() -> pathlib.Path | None:
    """Reuse an existing checkout instead of cloning again."""
    cwd = pathlib.Path.cwd()
    for candidate in (cwd, *cwd.parents, COLAB_ROOT / "spatio-textual"):
        if _looks_like_repo(candidate):
            return candidate
    return None


def setup(fast_mode: bool = True, quiet: bool = False, extras: str = "") -> Context:
    """Clone (once), install (once), and return stable paths.

    fast_mode : True keeps the CPU-only route with precomputed transformer/LLM
                outputs. Set False only for the optional heavyweight route.
    extras    : e.g. "app" for notebook 08's folium dependency, or
                "transformers" when fast_mode is False.
    """
    t0 = time.time()
    root = COLAB_ROOT if _in_colab() else pathlib.Path.cwd()

    repo = _find_repo()
    if repo is None:
        repo = root / "spatio-textual"
        print(f"Cloning {REF} ... this takes about 30 seconds.")
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", REF, REPO_URL, str(repo)],
            check=True,
        )
    else:
        print(f"Reusing existing checkout at {repo}")

    os.chdir(repo)

    # Install once per runtime. The marker means re-running this cell, which
    # participants WILL do, costs nothing.
    marker = repo / ".sh2026_installed"
    want = extras or "core"
    if marker.exists() and marker.read_text().strip() == want:
        print("Dependencies already installed in this runtime.")
    else:
        target = f".[{extras}]" if extras else "."
        print(f"Installing {target} ... this takes 1 to 2 minutes. "
              f"Good moment to read the next markdown cell.")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-e", target],
            check=True,
        )
        marker.write_text(want)

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, cwd=repo,
    ).stdout.strip()

    data = repo / "workshop" / "data"
    outputs = repo / "sh2026_outputs"
    for sub in ("annotations", "comparisons", "geojson", "figures", "human_review"):
        (outputs / sub).mkdir(parents=True, exist_ok=True)

    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    ctx = Context(repo, data, outputs, fast_mode, commit, time.time() - t0)

    if not quiet:
        route = "CPU only, no API key needed" if fast_mode else "heavyweight route"
        print(
            f"\nReady in {ctx.elapsed_s:.0f}s."
            f"\n  repo    : {ctx.repo}"
            f"\n  commit  : {ctx.commit}"
            f"\n  data    : {ctx.data}"
            f"\n  outputs : {ctx.outputs}"
            f"\n  route   : {route}"
            f"\n\nIf this cell failed, put your hand up. Do not re-run it more than once."
        )
    return ctx
