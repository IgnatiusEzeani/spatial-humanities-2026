"""Canonical setup path for every Spatial Humanities 2026 notebook."""

from __future__ import annotations

import importlib.metadata
import os
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass


WORKSHOP_REPO = "https://github.com/IgnatiusEzeani/spatial-humanities-2026.git"
WORKSHOP_REF = "main"
PACKAGE_VERSION = "0.4.0"
PACKAGE_REF = "d91d32977924f2cf6fc826b01a77463f8c30267a"
COLAB_ROOT = pathlib.Path("/content")


@dataclass(frozen=True)
class Context:
    project: pathlib.Path
    data: pathlib.Path
    outputs: pathlib.Path
    fast_mode: bool
    project_commit: str
    package_version: str
    package_ref: str
    elapsed_s: float


def _in_colab() -> bool:
    return "google.colab" in sys.modules or COLAB_ROOT.exists()


def _looks_like_project(path: pathlib.Path) -> bool:
    return (path / "workshop").is_dir() and (path / "demo").is_dir() and (path / "benchmarks").is_dir()


def _find_project() -> pathlib.Path | None:
    cwd = pathlib.Path.cwd().resolve()
    candidates = (cwd, *cwd.parents, COLAB_ROOT / "spatial-humanities-2026")
    return next((path for path in candidates if _looks_like_project(path)), None)


def _install(project: pathlib.Path, extras: str) -> None:
    requirements = {
        "": "requirements-lite.txt",
        "app": "requirements-lite.txt",
        "transformers": "requirements-transformers.txt",
        "llm": "requirements-llm.txt",
    }
    if extras not in requirements:
        raise ValueError(f"Unsupported workshop dependency set: {extras!r}")

    requirement = requirements[extras]
    marker = project / f".sh2026-installed-{extras or 'lite'}"
    try:
        installed = importlib.metadata.version("spatio-textual")
    except importlib.metadata.PackageNotFoundError:
        installed = None

    if installed == PACKAGE_VERSION:
        marker.touch()
        print(f"Dependencies already installed (spatio-textual {installed}).")
        return

    print(f"Installing {requirement}; allow about 1–2 minutes in a fresh runtime.")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(project / requirement)],
        check=True,
    )
    installed = importlib.metadata.version("spatio-textual")
    if installed != PACKAGE_VERSION:
        raise RuntimeError(
            f"Expected spatio-textual {PACKAGE_VERSION}, but installed {installed}."
        )
    marker.touch()


def setup(*, fast_mode: bool = True, extras: str = "", quiet: bool = False) -> Context:
    """Prepare one workshop checkout and an exactly pinned package dependency."""
    started = time.perf_counter()
    root = COLAB_ROOT if _in_colab() else pathlib.Path.cwd()
    project = _find_project()
    if project is None:
        project = root / "spatial-humanities-2026"
        print(f"Cloning workshop release {WORKSHOP_REF}.")
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", WORKSHOP_REF, WORKSHOP_REPO, str(project)],
            check=True,
        )
    else:
        print(f"Reusing workshop checkout at {project}")

    os.chdir(project)
    _install(project, extras)
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))

    revision = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    project_commit = revision.stdout.strip() if revision.returncode == 0 else "uncommitted"
    outputs = project / "sh2026_outputs"
    for name in ("annotations", "comparisons", "geojson", "figures", "human_review"):
        (outputs / name).mkdir(parents=True, exist_ok=True)

    ctx = Context(
        project=project,
        data=project / "workshop" / "data",
        outputs=outputs,
        fast_mode=fast_mode,
        project_commit=project_commit,
        package_version=importlib.metadata.version("spatio-textual"),
        package_ref=PACKAGE_REF,
        elapsed_s=time.perf_counter() - started,
    )
    if not quiet:
        route = "CPU only; no API key required" if fast_mode else "optional heavyweight route"
        print(
            f"Ready in {ctx.elapsed_s:.0f}s.\n"
            f"  workshop commit : {ctx.project_commit}\n"
            f"  package version  : {ctx.package_version}\n"
            f"  package ref      : {ctx.package_ref}\n"
            f"  data             : {ctx.data}\n"
            f"  outputs          : {ctx.outputs}\n"
            f"  route            : {route}"
        )
    return ctx
