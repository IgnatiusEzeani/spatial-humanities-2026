"""Exercise actual Streamlit controls with deterministic provider responses.

These are UI regression tests, not a replacement for hosted/Colab rehearsals.
"""
from pathlib import Path

import pytest

pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest

from spatio_textual.llm import LLMClient
from spatio_textual.viz import to_geojson

APP = Path(__file__).resolve().parents[1] / 'demo' / 'streamlit_app.py'
AUTO = 'Automatic: live if configured, otherwise teaching fallback'
LIVE = 'Live LLM: server-configured'


@pytest.mark.parametrize('mode,success,has_key,edited,expected', [
    (AUTO, False, True, False, 'curated_teaching_fallback'),
    (AUTO, True, True, False, 'live_llm'),  # empty success is not failure
    (AUTO, False, False, False, 'curated_teaching_fallback'),
    (AUTO, False, True, True, None),  # never reuse fallback for changed text
    (LIVE, False, True, False, None),
    (LIVE, False, False, False, None),
])
def test_journey_modes(monkeypatch, mode, success, has_key, edited, expected):
    if has_key:
        monkeypatch.setenv('OPENAI_API_KEY', 'test-only-placeholder')
    else:
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    calls = []

    def response(self, *args, **kwargs):
        calls.append(True)
        return {'journeys': [], 'telemetry': {'success': success}}

    monkeypatch.setattr(LLMClient, 'complete_json', response)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.sidebar.radio[0].set_value('Analyse').run()
    app.selectbox[0].set_value('Synthetic oral-history Q/A journey').run()
    app.selectbox[1].set_value(mode)
    if edited:
        app.text_area[0].set_value(app.text_area[0].value + ' Additional text.')
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['journey_source'] == expected
    assert bool(calls) == has_key
    if expected == 'curated_teaching_fallback':
        assert app.session_state['journeys']
    if has_key and not success:
        assert any('unavailable' in n for n in app.session_state['journey_notes'])
    if success:
        assert app.session_state['journeys'] == []


def test_place_edit_control_removes_old_map_point():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.session_state['analysis'] = {
        'text': 'Cambridge', 'rules': {'spans': []},
        'records': [{'entities': [{
            'text': 'Cambridge', 'label': 'GPE', 'resolved_name': 'Cambridge',
            'lat': 52.2, 'lon': 0.12, 'ambiguous': True,
            'resolution_status': 'resolved_ambiguous', 'requires_review': True,
        }]}],
    }
    app.sidebar.radio[0].set_value('Review').run()
    app.selectbox(key='place_decision_0').set_value('edit').run()
    app.text_input(key='place_edit_0').set_value('Cambridge, Massachusetts')
    app.button(key='place_review_0').click().run()
    assert not app.exception
    records = app.session_state['analysis']['records']
    assert records[0]['entities'][0]['resolved_name'] == 'Cambridge, Massachusetts'
    assert records[0]['entities'][0]['requires_review']
    assert to_geojson(records)['features'] == []
    app.sidebar.radio[0].set_value('Explore').run()
    assert not app.exception
    assert any('No currently resolved geometry' in i.value for i in app.info)
