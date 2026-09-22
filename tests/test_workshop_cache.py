from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_panel_cache_builder_reproduces_committed_cache(tmp_path: Path) -> None:
    generated = tmp_path / "panel_cache.json"
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "workshop" / "tools" / "make_workshop_cache.py"),
            "--panel",
            str(PROJECT_ROOT / "panel" / "panel_panel_v1_openrouter.jsonl"),
            "--results",
            str(PROJECT_ROOT / "panel" / "results_snapshot_v2.json"),
            "--passages",
            str(PROJECT_ROOT / "workshop" / "data" / "workshop_passages.json"),
            "--out",
            str(generated),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    committed = PROJECT_ROOT / "workshop" / "data" / "panel_cache.json"
    assert generated.read_bytes() == committed.read_bytes()
