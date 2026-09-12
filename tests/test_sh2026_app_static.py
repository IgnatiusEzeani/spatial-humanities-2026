from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP = PROJECT_ROOT / "demo" / "streamlit_app.py"


def test_sh2026_app_exists_and_compiles():
    source = APP.read_text(encoding="utf-8")
    compile(source, str(APP), "exec")


def test_sh2026_app_has_required_humanities_facing_sections():
    source = APP.read_text(encoding="utf-8")
    for label in ["Home", "Analyse", "Compare", "Explore", "Review", "About"]:
        assert f'"{label}"' in source
    assert "From Coordinates to Context" in source
    assert "apply_human_review" in source
    assert "journeys_to_geojson" in source
    assert "build_run_manifest" in source


def test_sh2026_app_does_not_request_api_keys_in_ui():
    source = APP.read_text(encoding="utf-8")
    assert 'text_input("API key' not in source
    assert 'text_input("OpenAI API' not in source
    assert 'text_input("Groq API' not in source
