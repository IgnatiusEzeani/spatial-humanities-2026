from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "workshop"
EXPECTED = [f"{i:02d}_{name}.ipynb" for i, name in enumerate([
    "setup_and_orientation",
    "manual_annotation",
    "rules_and_gazetteers",
    "contextual_ner",
    "linking_and_ambiguity",
    "affect_and_events",
    "llm_structured_extraction",
    "compare_and_adjudicate",
    "from_text_to_map",
    "responsible_spatial_ai",
])]


def _compilable_source(source: str) -> str:
    """Remove IPython-only command lines before ordinary Python syntax checking."""
    lines = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("!") or stripped.startswith("%"):
            lines.append("pass  # stripped IPython command for static syntax check")
        else:
            lines.append(line)
    return "\n".join(lines)


def test_all_sh2026_notebooks_exist_and_have_valid_json():
    found = sorted(path.name for path in NOTEBOOK_DIR.glob("*.ipynb"))
    for name in EXPECTED:
        assert name in found, f"Missing SH2026 notebook: {name}"
        data = json.loads((NOTEBOOK_DIR / name).read_text(encoding="utf-8"))
        assert data.get("nbformat") == 4
        assert isinstance(data.get("cells"), list) and data["cells"], f"{name} has no cells"


def test_sh2026_python_code_cells_are_syntax_valid():
    failures = []
    for name in EXPECTED:
        data = json.loads((NOTEBOOK_DIR / name).read_text(encoding="utf-8"))
        for index, cell in enumerate(data.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            try:
                compile(_compilable_source(str(source)), f"{name}:cell{index}", "exec")
            except SyntaxError as exc:
                failures.append(f"{name} cell {index}: {exc}")
    assert not failures, "Notebook syntax failures:\n" + "\n".join(failures)


def test_notebooks_do_not_embed_obvious_secret_assignments():
    forbidden = (
        'OPENAI_API_KEY = "',
        "OPENAI_API_KEY = '",
        'GROQ_API_KEY = "',
        "GROQ_API_KEY = '",
        'ANTHROPIC_API_KEY = "',
        "ANTHROPIC_API_KEY = '",
        'GOOGLE_API_KEY = "',
        "GOOGLE_API_KEY = '",
        'MISTRAL_API_KEY = "',
        "MISTRAL_API_KEY = '",
    )
    for name in EXPECTED:
        text = (NOTEBOOK_DIR / name).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"Possible hard-coded secret assignment in {name}: {marker}"


def test_all_notebooks_use_one_setup_and_release_badge():
    for name in EXPECTED:
        text = (NOTEBOOK_DIR / name).read_text(encoding="utf-8")
        assert "workshop/sh2026_setup.py" in text
        assert 'pathlib.Path(\\"sh2026_setup.py\\")' in text
        assert "if local_setup is None:" in text
        assert "spatial-humanities-2026/blob/main" in text
        assert "IgnatiusEzeani/spatio-textual/blob/" not in text
        assert "git\\\", \\\"clone" not in text


def test_reviewed_notebook_failures_are_regression_guarded():
    manual = (NOTEBOOK_DIR / EXPECTED[1]).read_text(encoding="utf-8")
    affect = (NOTEBOOK_DIR / EXPECTED[5]).read_text(encoding="utf-8")
    llm = (NOTEBOOK_DIR / EXPECTED[6]).read_text(encoding="utf-8")
    mapping = (NOTEBOOK_DIR / EXPECTED[8]).read_text(encoding="utf-8")

    assert "SHOW_REFERENCE = False" in manual
    assert "_tokens" not in affect
    assert "class TeachingClient" not in llm
    assert "class BadEvidenceClient" not in llm
    assert "display(IFrame" not in mapping
    assert "map_path.read_text" in mapping
