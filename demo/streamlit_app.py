from __future__ import annotations

import html
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from spatio_textual.benchmark import summarize_telemetry
from spatio_textual.emotion import EmotionAnalyzer
from spatio_textual.evaluation import harmonize_ner_entities
from spatio_textual.journeys import JOURNEY_FIELDS, JourneyExtractor, normalise_model_journey
from spatio_textual.llm import LLMClient
from spatio_textual.provenance import build_run_manifest
from spatio_textual.review import apply_human_review, apply_place_review
from spatio_textual.rules import RuleGazetteerAnnotator
from spatio_textual.sentiment import SentimentAnalyzer
from spatio_textual.utils import Annotator, load_spacy_model
from spatio_textual.viz import build_cooccurrence, journeys_to_geojson, to_geojson

DEMO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_DIR.parent
REPO_ROOT = PROJECT_ROOT
WORKSHOP_DATA = PROJECT_ROOT / "workshop" / "data"
EXAMPLES_PATH = WORKSHOP_DATA / "examples.json"
TEACHING_GAZETTEER = WORKSHOP_DATA / "teaching_gazetteer.csv"
BENCHMARK_SNAPSHOT_PATH = PROJECT_ROOT / "benchmarks" / "results_snapshot_v1.json"
FALLBACK_JOURNEYS_PATH = DEMO_DIR / "fallback_journeys_v1.json"
try:
    from importlib.resources import files as package_files

    PACKAGE_RESOURCES = package_files("spatio_textual") / "resources"
except (ImportError, ModuleNotFoundError):
    PACKAGE_RESOURCES = None

st.set_page_config(
    page_title="Spatial Humanities 2026 | spatio-textual",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_examples() -> list[dict[str, Any]]:
    if not EXAMPLES_PATH.exists():
        return []
    return json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_benchmark_snapshot() -> dict[str, Any]:
    if not BENCHMARK_SNAPSHOT_PATH.exists():
        return {"rows": [], "omissions": []}
    return json.loads(BENCHMARK_SNAPSHOT_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_fallback_journeys() -> dict[str, Any]:
    if not FALLBACK_JOURNEYS_PATH.exists():
        return {"examples": {}}
    return json.loads(FALLBACK_JOURNEYS_PATH.read_text(encoding="utf-8"))


@st.cache_resource
def load_contextual_model():
    return load_spacy_model(
        "en_core_web_sm",
        resources_dir=PACKAGE_RESOURCES,
        add_entity_ruler=False,
    )


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def entity_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for entity in record.get("entities") or []:
            rows.append({
                "segment": record.get("segId", 1),
                "text": entity.get("text"),
                "label": entity.get("label"),
                "start_char": entity.get("start_char"),
                "end_char": entity.get("end_char"),
                "resolved_name": entity.get("resolved_name"),
                "resolution_status": entity.get("resolution_status"),
                "ambiguous": entity.get("ambiguous"),
                "lat": entity.get("lat"),
                "lon": entity.get("lon"),
                "source": entity.get("source"),
                "human_status": entity.get("human_status", "unreviewed"),
            })
    return rows


def telemetry_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.extend(row for row in (record.get("telemetry") or []) if isinstance(row, dict))
    return rows


def analyse(text: str, *, link_places: bool = True) -> dict[str, Any]:
    nlp = load_contextual_model()
    annotator = Annotator(
        nlp,
        resources_dir=PACKAGE_RESOURCES,
        model_name="en_core_web_sm",
        link_places=link_places,
    )
    contextual = annotator.annotate(
        text,
        include_text=True,
        include_entities=True,
        include_events=True,
    )
    contextual["fileId"] = "demo"
    contextual["segId"] = 1

    rules = RuleGazetteerAnnotator(
        gazetteer_path=TEACHING_GAZETTEER,
        link_places=False,
    ).annotate(text)

    sentiment = SentimentAnalyzer("rule").predict([text])[0]
    emotion = EmotionAnalyzer("rule").predict([text])[0]

    contextual["sentiment_label"] = sentiment.get("label")
    contextual["sentiment_distribution"] = sentiment.get("distribution")
    contextual["emotion_label"] = emotion.get("label")
    contextual["emotion_dist"] = emotion.get("distribution")
    contextual.setdefault("telemetry", []).extend(
        [row for row in (sentiment.get("telemetry"), emotion.get("telemetry")) if row]
    )

    return {"records": [contextual], "rules": rules}


def maybe_extract_journeys(text: str) -> dict[str, Any] | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None
    client = LLMClient(provider="openai")
    result = JourneyExtractor(client=client).extract(text, file_id="demo", seg_id=1)
    if any(row.get("success") is False for row in result.get("telemetry", []) if isinstance(row, dict)):
        raise RuntimeError("The live provider could not complete journey extraction.")
    result["demo_source"] = "live_llm"
    return result


def fallback_journey_result(example_id: str | None, source_text: str) -> dict[str, Any] | None:
    if not example_id:
        return None
    raw_rows = (load_fallback_journeys().get("examples") or {}).get(example_id)
    if not raw_rows:
        return None
    journeys = [
        normalise_model_journey(
            raw,
            source_text=source_text,
            file_id=f"demo:{example_id}",
            seg_id=1,
            model="instructor_curated_v1",
            provider="sh2026",
        )
        for raw in raw_rows
    ]
    return {
        "journeys": journeys,
        "review_notes": [],
        "demo_source": "curated_teaching_fallback",
    }


def _valid_spans(text: str, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for span in spans:
        start = span.get("start_char")
        end = span.get("end_char")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > len(text):
            continue
        valid.append(span)
    return sorted(valid, key=lambda row: (row["start_char"], -(row["end_char"] - row["start_char"])))


def highlighted_source_html(text: str, spans: list[dict[str, Any]]) -> str:
    """Render source text with non-overlapping evidence spans highlighted.

    Overlapping predictions remain visible in the tables; the text view chooses
    the earliest/longest span only to avoid malformed nested HTML.
    """
    parts: list[str] = []
    cursor = 0
    for span in _valid_spans(text, spans):
        start = span["start_char"]
        end = span["end_char"]
        if start < cursor:
            continue
        parts.append(html.escape(text[cursor:start]))
        label = html.escape(str(span.get("label") or "SPAN"))
        snippet = html.escape(text[start:end])
        parts.append(
            f'<mark title="{label}" style="padding:0.08rem 0.18rem;border-radius:0.2rem;">'
            f'{snippet}<sup style="font-size:0.65em;margin-left:0.2rem;">{label}</sup></mark>'
        )
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return '<div style="line-height:1.9;white-space:pre-wrap;">' + "".join(parts) + "</div>"


def render_highlighted_source(text: str, spans: list[dict[str, Any]], *, caption: str | None = None) -> None:
    if caption:
        st.caption(caption)
    if not spans:
        st.code(text, language=None)
        return
    st.markdown(highlighted_source_html(text, spans), unsafe_allow_html=True)


def _distribution_frame(distribution: dict[str, Any] | None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, value in (distribution or {}).items():
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        rows.append({"label": str(label), "score": score})
    if not rows:
        return pd.DataFrame(columns=["score"])
    return pd.DataFrame(rows).sort_values("score", ascending=False).set_index("label")


def render_affect(rec: dict[str, Any]) -> None:
    sentiment = _distribution_frame(rec.get("sentiment_distribution"))
    emotion = _distribution_frame(rec.get("emotion_dist"))
    left, right = st.columns(2)
    with left:
        st.markdown("#### Sentiment signal")
        st.metric("Top label", rec.get("sentiment_label") or "n/a")
        if sentiment.empty:
            st.caption("No sentiment distribution available.")
        else:
            st.bar_chart(sentiment)
    with right:
        st.markdown("#### Emotion signal")
        st.metric("Top label", rec.get("emotion_label") or "n/a")
        if emotion.empty:
            st.caption("No emotion distribution available.")
        else:
            st.bar_chart(emotion)
    st.caption("These labels are analytical model signals, not claims about a narrator's psychological state.")


def render_journey_cards(journeys: list[dict[str, Any]], *, source: str | None = None) -> None:
    if not journeys:
        st.caption("No structured journeys are available for this passage.")
        return
    if source == "curated_teaching_fallback":
        st.info(
            "Offline-safe teaching fallback: these structured records were curated by the instructor to demonstrate the schema and audit workflow. "
            "They are not LLM predictions and are not benchmark results."
        )
    elif source == "live_llm":
        st.caption("Live structured extraction. Evidence quotations are grounded and character offsets are computed locally.")

    for index, journey in enumerate(journeys, start=1):
        with st.container(border=True):
            start = journey.get("start_location") or "origin not stated"
            end = journey.get("end_location") or "destination not stated"
            st.markdown(f"#### Journey {index}: {start} → {end}")
            quote = journey.get("evidence_quote")
            if quote:
                st.markdown("**Source evidence**")
                st.code(quote, language=None)
            m1, m2, m3 = st.columns(3)
            m1.metric("Evidence grounded", "Yes" if journey.get("evidence_grounded") else "No")
            m2.metric("Human review", "Required" if journey.get("requires_review") else "Not flagged")
            confidence = journey.get("confidence")
            m3.metric("Confidence", f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "not supplied")
            statuses = journey.get("explicit_or_inferred") or {}
            fields = []
            for field in JOURNEY_FIELDS:
                fields.append({
                    "Field": field,
                    "Value": journey.get(field),
                    "Provenance": statuses.get(field, "missing"),
                })
            st.dataframe(pd.DataFrame(fields), use_container_width=True, hide_index=True)
            if journey.get("review_notes"):
                st.warning("; ".join(map(str, journey.get("review_notes") or [])))


def render_map(records: list[dict[str, Any]], journeys: list[dict[str, Any]]) -> None:
    try:
        import folium
        import streamlit.components.v1 as components
    except Exception as exc:
        st.info(f"Interactive map unavailable in this environment: {exc}")
        return

    point_geo = to_geojson(records)
    route_geo = journeys_to_geojson(journeys) if journeys else {"features": [], "audit": []}
    features = list(point_geo.get("features", [])) + list(route_geo.get("features", []))
    if not features:
        st.info("No currently resolved geometry is available. Unresolved spatial evidence remains visible in the tables.")
        return

    coordinates: list[tuple[float, float]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Point":
            lon, lat = geometry.get("coordinates", [None, None])[:2]
            if lon is not None and lat is not None:
                coordinates.append((float(lat), float(lon)))
        elif geometry.get("type") == "LineString":
            for pair in geometry.get("coordinates") or []:
                if len(pair) >= 2:
                    coordinates.append((float(pair[1]), float(pair[0])))

    center = [52.0, 0.0]
    if coordinates:
        center = [
            sum(lat for lat, _ in coordinates) / len(coordinates),
            sum(lon for _, lon in coordinates) / len(coordinates),
        ]
    fmap = folium.Map(location=center, zoom_start=4)
    folium.GeoJson({"type": "FeatureCollection", "features": features}).add_to(fmap)
    components.html(fmap._repr_html_(), height=520)
    if route_geo.get("audit"):
        st.caption("Some journey records could not be mapped without further resolution.")
        st.dataframe(pd.DataFrame(route_geo["audit"]), use_container_width=True, hide_index=True)


def _results_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame[["task", "method", "precision", "recall", "f1"]].rename(
        columns={
            "task": "Task",
            "method": "Method",
            "precision": "Precision",
            "recall": "Recall",
            "f1": "F1",
        }
    )


def benchmark_snapshot() -> None:
    st.markdown("### Frozen SH2026 benchmark snapshot")
    st.caption(
        "Only artifact-backed, reportable rows are shown. Synthetic controlled results and source-derived CLDW validation are kept separate."
    )
    snapshot = load_benchmark_snapshot()
    rows = [row for row in snapshot.get("rows", []) if row.get("status") == "reportable"]
    synthetic = [row for row in rows if row.get("dataset") == "Synthetic holdout v1"]
    external = [row for row in rows if row.get("dataset") == "CLDW external validation"]

    if synthetic:
        st.markdown("#### Synthetic controlled holdout")
        st.dataframe(_results_frame(synthetic), use_container_width=True, hide_index=True)
    else:
        st.warning("No reportable synthetic benchmark rows are available in the release snapshot.")

    if external:
        with st.expander("Source-derived CLDW TOPONYM validation"):
            st.dataframe(_results_frame(external), use_container_width=True, hide_index=True)
            st.caption(
                "The CLDW check uses a small purposively selected source-derived sample; it is not a population-level estimate for the corpus."
            )

    omissions = snapshot.get("omissions", [])
    for omission in omissions:
        if omission.get("status") == "not_reportable":
            st.warning(
                f"{omission.get('task')} / {omission.get('method')} is not shown as a scored result: "
                f"{omission.get('reason')}"
            )

    st.info(
        "Read the table as a trade-off, not a leaderboard: representational reach, evidence, inference and review burden change with the method."
    )


if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "journeys" not in st.session_state:
    st.session_state.journeys = []
if "journey_notes" not in st.session_state:
    st.session_state.journey_notes = []
if "journey_source" not in st.session_state:
    st.session_state.journey_source = None

examples = load_examples()

with st.sidebar:
    st.markdown("## Spatial Humanities 2026")
    page = st.radio("Navigate", ["Home", "Analyse", "Compare", "Explore", "Review", "About"])
    st.divider()
    st.caption("Conference demonstrator built on the reusable `spatio-textual` package.")

st.title("From Coordinates to Context")
st.caption("Auditable spatial-text analysis: recognition → event reconstruction → interpretation")

if page == "Home":
    st.markdown(
        "This demonstrator compares computational methods without assuming that newer models simply replace older ones. "
        "The central question is what each method can represent, what evidence supports its output, and what a scholar still needs to validate."
    )
    a, b, c = st.columns(3)
    a.metric("Recognition", "Spatial entities")
    b.metric("Reconstruction", "Journeys")
    c.metric("Interpretation", "Affect")

    st.markdown("### Public-safe examples")
    example_columns = st.columns(min(3, max(1, len(examples))))
    for index, example in enumerate(examples[:3]):
        with example_columns[index]:
            with st.container(border=True):
                st.markdown(f"**{example.get('title')}**")
                st.caption(example.get("genre") or "narrative")
                st.write(", ".join(example.get("teaching_targets") or []))

    benchmark_snapshot()
    st.markdown("### Methodological progression")
    st.markdown("**Rules / resources → contextual transformers → structured LLMs → human adjudication**")

elif page == "Analyse":
    st.subheader("Analyse a public-safe example")
    titles = [example["title"] for example in examples]
    chosen = st.selectbox("Example", titles) if titles else None
    selected_example = examples[titles.index(chosen)] if chosen else None
    default_text = selected_example["text"] if selected_example else ""
    if selected_example and selected_example.get("source_note"):
        st.caption(selected_example["source_note"])
    text = st.text_area("Source text", value=default_text, height=220)
    link_places = st.checkbox("Resolve named places where possible", value=True)
    journey_mode = st.selectbox(
        "Structured journey layer",
        [
            "Off",
            "Automatic: live if configured, otherwise teaching fallback",
            "Teaching fallback: offline-safe",
            "Live LLM: server-configured",
        ],
    )
    if journey_mode != "Off" and not os.getenv("OPENAI_API_KEY"):
        st.caption(
            "No live provider key is configured on the server. Supported unchanged teaching examples can still use the curated offline fallback."
        )

    if st.button("Run analysis", type="primary", use_container_width=True):
        if not text.strip():
            st.error("Enter source text first.")
        else:
            result = analyse(text, link_places=link_places)
            example_id = selected_example.get("id") if selected_example else None
            st.session_state.analysis = {"text": text, "example_id": example_id, **result}
            st.session_state.journeys = []
            st.session_state.journey_notes = []
            st.session_state.journey_source = None

            journey_result: dict[str, Any] | None = None
            exact_teaching_example = bool(selected_example and text == selected_example.get("text"))
            wants_live = journey_mode in {
                "Automatic: live if configured, otherwise teaching fallback",
                "Live LLM: server-configured",
            }
            wants_fallback = journey_mode in {
                "Automatic: live if configured, otherwise teaching fallback",
                "Teaching fallback: offline-safe",
            }

            if journey_mode != "Off":
                if wants_live and os.getenv("OPENAI_API_KEY"):
                    try:
                        journey_result = maybe_extract_journeys(text)
                    except Exception:
                        st.session_state.journey_notes = [
                            "Live journey extraction is unavailable. Automatic mode uses a teaching fallback where available."
                        ]
                if journey_result is None and wants_fallback and exact_teaching_example:
                    journey_result = fallback_journey_result(example_id, text)
                if journey_result is None and journey_mode != "Live LLM: server-configured":
                    st.session_state.journey_notes.append(
                        "No curated journey fallback exists for this exact passage. The rest of the analysis remains available."
                    )
                elif journey_result is None and not os.getenv("OPENAI_API_KEY"):
                    st.session_state.journey_notes.append(
                        "Live LLM extraction is unavailable because the server has no provider key configured."
                    )

            if journey_result:
                st.session_state.journeys = journey_result.get("journeys") or []
                st.session_state.journey_notes.extend(journey_result.get("review_notes") or [])
                st.session_state.journey_source = journey_result.get("demo_source")

    analysis = st.session_state.analysis
    if analysis:
        records = analysis["records"]
        entities = entity_rows(records)
        m1, m2, m3 = st.columns(3)
        m1.metric("Contextual entities", len(entities))
        m2.metric("Rule spans", len(analysis["rules"].get("spans") or []))
        m3.metric("Journeys", len(st.session_state.journeys))

        st.markdown("### Source with contextual annotations")
        render_highlighted_source(
            analysis["text"],
            records[0].get("entities") or [],
            caption="Highlights show grounded character spans; overlapping alternatives remain available in the table below.",
        )
        st.dataframe(pd.DataFrame(entities), use_container_width=True, hide_index=True)

        st.markdown("### Affect signals")
        render_affect(records[0])

        st.markdown("### Evidence-first structured journeys")
        render_journey_cards(st.session_state.journeys, source=st.session_state.journey_source)
        if st.session_state.journey_notes:
            st.warning("; ".join(map(str, st.session_state.journey_notes)))

elif page == "Compare":
    st.subheader("Compare what the methods can represent")
    analysis = st.session_state.analysis
    if not analysis:
        st.info("Run an analysis first.")
    else:
        source = analysis["text"]
        rule_spans = analysis["rules"].get("spans") or []
        contextual_raw = analysis["records"][0].get("entities") or []
        contextual = harmonize_ner_entities(contextual_raw)
        left, right = st.columns(2)
        with left:
            st.markdown("#### Rules / gazetteer")
            render_highlighted_source(source, rule_spans)
            st.dataframe(pd.DataFrame(rule_spans), use_container_width=True, hide_index=True)
            st.caption("Transparent and deterministic, but bounded by encoded resources and patterns.")
        with right:
            st.markdown("#### Contextual NER")
            render_highlighted_source(source, contextual_raw)
            st.dataframe(pd.DataFrame(contextual), use_container_width=True, hide_index=True)
            st.caption("Context-sensitive recognition, but still bounded by its entity ontology.")

        st.markdown("### Richer structured layer")
        render_journey_cards(st.session_state.journeys, source=st.session_state.journey_source)
        st.info(
            "Better recognition within a narrow ontology is not the same as richer spatial understanding. Richer representation also increases the audit burden."
        )

elif page == "Explore":
    st.subheader("Explore spatial representations")
    analysis = st.session_state.analysis
    if not analysis:
        st.info("Run an analysis first.")
    else:
        records = analysis["records"]
        journeys = st.session_state.journeys
        render_map(records, journeys)
        st.markdown("### Co-occurrence as a non-route representation")
        edges = build_cooccurrence(records)
        if edges:
            st.dataframe(pd.DataFrame(edges, columns=["source", "target", "weight"]), use_container_width=True, hide_index=True)
        else:
            st.caption("No co-occurrence edges in the current one-segment example.")
        st.caption("Unresolved or relational spatial evidence should remain textual rather than being forced onto a coordinate map.")

elif page == "Review":
    st.subheader("Human review remains part of the method")
    analysis = st.session_state.analysis
    if not analysis:
        st.info("Run an analysis first.")
    else:
        records = analysis["records"]
        flagged = [
            (i, entity)
            for i, entity in enumerate(records[0].get("entities") or [])
            if entity.get("ambiguous") or entity.get("resolution_status") == "unresolved" or entity.get("requires_review")
        ]
        st.metric("Flagged place records", len(flagged))
        if not flagged:
            st.caption("No place-resolution records are currently flagged.")
        for index, entity in flagged:
            with st.container(border=True):
                st.write({k: entity.get(k) for k in ("text", "resolved_name", "resolution_status", "ambiguous", "candidates")})
                decision = st.selectbox("Decision", ["accept", "edit", "reject"], key=f"place_decision_{index}")
                replacement = None
                if decision == "edit":
                    replacement = st.text_input(
                        "Corrected/resolved place name",
                        value=str(entity.get("resolved_name") or entity.get("text") or ""),
                        key=f"place_edit_{index}",
                    )
                if st.button("Record review", key=f"place_review_{index}"):
                    if entity.get("ambiguous"):
                        reason = "ambiguous_place"
                    elif entity.get("resolution_status") == "unresolved":
                        reason = "unresolved_place"
                    else:
                        reason = "human_flag"
                    kwargs: dict[str, Any] = {}
                    if decision == "edit":
                        kwargs = {"field": "resolved_name", "new_value": replacement}
                    records[0]["entities"][index] = apply_place_review(
                        entity,
                        action=decision,
                        reason=reason,
                        **kwargs,
                    )
                    st.session_state.analysis["records"] = records
                    st.success("Review appended to the audit trail; the original machine value remains in the edit event.")
                    if decision == "edit":
                        st.info("The corrected place remains unresolved. Previous coordinates have been cleared until its location is verified.")

        st.markdown("### Journey review")
        if not st.session_state.journeys:
            st.caption("No structured journey records to review.")
        for index, journey in enumerate(st.session_state.journeys):
            if not journey.get("requires_review"):
                continue
            with st.container(border=True):
                st.write(f"{journey.get('start_location') or '∅'} → {journey.get('end_location') or '∅'}")
                st.caption(journey.get("evidence_quote") or "No grounded evidence")
                st.write("Field provenance:", journey.get("explicit_or_inferred"))
                decision = st.selectbox("Journey decision", ["accept", "edit", "reject"], key=f"journey_decision_{index}")
                edit_field = None
                edit_value = None
                if decision == "edit":
                    edit_field = st.selectbox("Field to edit", list(JOURNEY_FIELDS), key=f"journey_field_{index}")
                    edit_value = st.text_input(
                        "Corrected value (leave blank to mark missing)",
                        value=str(journey.get(edit_field) or ""),
                        key=f"journey_value_{index}",
                    )
                if st.button("Record journey review", key=f"journey_review_{index}"):
                    inferred = any(
                        status == "contextual_inference"
                        for status in (journey.get("explicit_or_inferred") or {}).values()
                    )
                    reason = "contextual_inference" if inferred else "human_flag"
                    kwargs = {}
                    if decision == "edit" and edit_field:
                        new_value = edit_value if edit_value not in (None, "") else None
                        kwargs = {"field": edit_field, "new_value": new_value}
                    reviewed = apply_human_review(journey, action=decision, reason=reason, **kwargs)
                    if decision == "edit" and edit_field:
                        statuses = dict(reviewed.get("explicit_or_inferred") or {})
                        statuses[edit_field] = "human_supplied" if reviewed.get(edit_field) not in (None, "") else "missing"
                        reviewed["explicit_or_inferred"] = statuses
                    st.session_state.journeys[index] = reviewed
                    st.success("Journey review appended to the audit trail.")

elif page == "About":
    st.subheader("About the SH2026 demonstrator")
    st.markdown("**Workshop:** *AI and NLP for Spatial Humanities: From Manual Annotation to LLM-Assisted Interpretation*")
    st.markdown("**Keynote:** *From Coordinates to Context: Rethinking Spatial Humanities in the Age of Large Language Models*")
    st.write(
        "The demo is a project-specific presentation layer over the reusable `spatio-textual` package. "
        "It uses public-safe or synthetic material and does not bundle controlled-access testimony transcripts."
    )
    st.markdown("### Reliability modes")
    st.write(
        "The core entity, affect, comparison and review paths run locally. Optional live journey extraction uses a server-side provider configuration; "
        "supported teaching examples have an explicitly labelled instructor-curated fallback so the demonstration does not depend on an API call."
    )
    st.markdown("### Provenance")
    records = (st.session_state.analysis or {}).get("records", []) if st.session_state.analysis else []
    manifest = build_run_manifest(
        input_text=(st.session_state.analysis or {}).get("text", "") if st.session_state.analysis else "",
        config={
            "demo": "SH2026",
            "live_llm_available": bool(os.getenv("OPENAI_API_KEY")),
            "journey_source": st.session_state.journey_source,
        },
        git_commit=git_commit(),
    )
    st.json({
        "manifest": manifest,
        "telemetry_summary": summarize_telemetry(telemetry_rows(records)) if records else {},
        "common_schema": "docs/COMMON_SCHEMA.md",
        "benchmark_protocol": "docs/BENCHMARK_PROTOCOL.md",
        "benchmark_snapshot": "benchmarks/results_snapshot_v1.json",
        "teaching_fallback": "demo/fallback_journeys_v1.json",
    })
