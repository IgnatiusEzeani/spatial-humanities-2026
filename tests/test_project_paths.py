from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD_MONOREPO_MARKERS = (
    "projects/sh2026/",
    "tutorials/sh2026/",
    "docs/sh2026/",
    "IgnatiusEzeani/spatio-textual/blob/fix/sh2026-demo-release-gates",
)


def test_conference_repository_does_not_vendor_the_package():
    assert not (ROOT / "spatio_textual").exists()


def test_required_project_directories_exist():
    for name in ("benchmarks", "config", "demo", "docs", "scripts", "tests", "workshop"):
        assert (ROOT / name).is_dir(), name


def test_live_text_files_do_not_reference_old_monorepo_paths():
    offenders: list[str] = []
    extensions = {".md", ".py", ".json", ".jsonl", ".yml", ".yaml"}
    for path in ROOT.rglob("*"):
        if path.resolve() == Path(__file__).resolve() or ".git" in path.parts or path.suffix not in extensions:
            continue
        text = path.read_text(encoding="utf-8")
        hits = [marker for marker in OLD_MONOREPO_MARKERS if marker in text]
        if hits:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(hits)}")
    assert not offenders, "Old monorepo paths remain:\n" + "\n".join(offenders)


def test_notebook_colab_links_target_the_conference_repository():
    expected = "github/IgnatiusEzeani/spatial-humanities-2026/"
    offenders: list[str] = []
    for path in sorted((ROOT / "workshop").glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", []))
            if isinstance(cell.get("source", []), list)
            else str(cell.get("source", ""))
            for cell in notebook.get("cells", [])
        )
        if expected not in source:
            offenders.append(path.name)
    assert not offenders, "Notebooks with stale/missing Colab links: " + ", ".join(offenders)
