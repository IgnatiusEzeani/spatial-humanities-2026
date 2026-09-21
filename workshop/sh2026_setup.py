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

NOTE: four of those run `pip install -e .`, which CANNOT work: this repository
has no pyproject.toml and no setup.py. It is a materials repo, not a package.
Installation goes through the requirements files.

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
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

REPO_URL = "https://github.com/IgnatiusEzeani/spatial-humanities-2026.git"

# Pin a TAG for the workshop, not a branch. A branch can move under a
# participant mid-session; a tag cannot. Freeze this after the release gates pass.
# Set to the TAG once it is cut; the working branch until then. Whatever this
# says is what Colab clones, so a local edit does nothing until it is pushed.
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
    # The workshop moved from spatio-textual into its own repo, and this check
    # was still looking for the OLD layout (a spatio_textual/ package plus
    # projects/sh2026/). It therefore never recognised an existing checkout,
    # re-cloned every time, and then put a non-existent directory on sys.path.
    return (p / "workshop").is_dir() and (p / "workshop_support").is_dir()


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
    extras    : which requirements file to install. "core" (default) is
                requirements-lite.txt; "app" adds the demo dependencies,
                "transformers" the heavyweight route, "llm" the API clients.
    """
    t0 = time.time()
    root = COLAB_ROOT if _in_colab() else pathlib.Path.cwd()

    repo = _find_repo()
    if repo is None:
        repo = root / "spatial-humanities-2026"
        if repo.exists():
            # A previous attempt left a partial checkout. `git clone` refuses to
            # write into a non-empty directory and fails with exit 128, which
            # looks like an auth or network problem and is neither. Re-runs must
            # be safe: a participant whose first attempt failed will press play
            # again, and telling them to delete the runtime is not a workshop.
            if (repo / ".git").is_dir():
                print("Found a partial checkout. Updating it instead of cloning.")
                subprocess.run(["git", "-C", str(repo), "fetch", "--depth", "1",
                                "origin", REF], check=False)
                subprocess.run(["git", "-C", str(repo), "checkout", "-f",
                                "FETCH_HEAD"], check=False)
            else:
                print("Removing an incomplete download and starting again.")
                shutil.rmtree(repo, ignore_errors=True)
        if not (repo / ".git").is_dir():
            print(f"Cloning {REF} ... this takes about 30 seconds.")
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", REF,
                 REPO_URL, str(repo)],
                capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(
                    "Could not clone the workshop repository.\n"
                    f"  branch : {REF}\n  url    : {REPO_URL}\n"
                    f"  git said: {(proc.stderr or '').strip().splitlines()[-1:] }\n"
                    "If this says the branch was not found, REF is set to a tag "
                    "or branch that does not exist yet.")
    else:
        print(f"Reusing existing checkout at {repo}")

    os.chdir(repo)

    # Install once per runtime. The marker means re-running this cell, which
    # participants WILL do, costs nothing.
    # This repo is NOT an installable package: no pyproject.toml, no setup.py.
    # `pip install -e .` fails with "does not appear to be a Python project",
    # which is exactly what happened on a clean machine. Install from the
    # requirements files instead.
    REQS = {"core": "requirements-workshop.txt",
            "app": "requirements.txt",
            "transformers": "requirements-transformers.txt",
            "llm": "requirements-llm.txt"}
    want = extras or "core"
    req = repo / REQS.get(want, REQS["core"])
    marker = repo / ".sh2026_installed"
    if marker.exists() and marker.read_text().strip() == want:
        print("Dependencies already installed in this runtime.")
    elif not req.exists():
        print(f"  ! {req.name} not found; skipping install. If imports fail, "
              f"install by hand.")
    else:
        print(f"Installing from {req.name} ... 1 to 2 minutes. "
              f"Good moment to read the next markdown cell.")
        # Do NOT swallow pip's output. A failed install used to surface as a
        # bare CalledProcessError with the reason hidden, which is useless in a
        # room of thirty people. Show what pip actually said, and carry on: a
        # partial environment is often enough for the first two blocks, and the
        # instructor can decide rather than the script.
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()
            print("\n  ! pip failed. The last lines were:\n")
            for line in tail[-12:]:
                print("     ", line)
            print("\n  Continuing anyway. If an import fails later, this is why.")
        else:
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
