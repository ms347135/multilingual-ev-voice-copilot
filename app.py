from __future__ import annotations

import time

import streamlit as st

from agents import answer_query, review_answer_for_safety
from analytics import log_event, summarize_events
from backend import collection_count, initialize_backend
from config import SOURCE_RELIABILITY_OPTIONS, SUPPORTED_DOCUMENT_TYPES, SUPPORTED_LANGUAGES, SUPPORTED_MARKETS, SUPPORTED_VEHICLE_MODELS, VOICE_OPTIONS, ensure_runtime_dirs
from ingestion import process_uploaded_pdf, seed_demo_dataset, upsert_uploaded_chunks
from retrieval import analyze_query, confidence_label, retrieve_hits
from state import init_session_state
from ui_components import render_answer_panel, render_sources, render_status_row, render_vehicle_panel
from vehicle_tools import get_warning_flags, load_vehicle_profiles, load_vehicle_state, summarize_vehicle_state
from voice import synthesize_speech, transcribe_audio


def main() -> None:
    st.set_page_config(page_title="Multilingual EV Voice Copilot", page_icon="🚗", layout="wide")
    ensure_runtime_dirs()
    init_session_state()

    profiles = load_vehicle_profiles()
    _render_sidebar(profiles)
    _render_header()

    if not st.session_state.backend_ready:
        st.info("Enter your OpenAI key, keep Qdrant in local mode for the easiest setup, then click Connect / Refresh.")
        return

    profile_name = st.session_state.vehicle_profile
    vehicle_state = load_vehicle_state(profile_name)
    warnings = get_warning_flags(vehicle_state)
    render_vehicle_panel(profile_name, vehicle_state, warnings)

    _render_demo_loader()
    _render_uploads()
    _render_query_experience(vehicle_state)
    _render_analytics_summary()


def _render_sidebar(profiles: list[dict]) -> None:
    with st.sidebar:
        st.title("Multilingual EV Voice Copilot")
        st.caption("Voice-enabled automotive support copilot with multilingual RAG and vehicle-state-aware reasoning.")

        st.session_state.openai_api_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password")
        st.session_state.qdrant_mode = st.radio(
            "Qdrant Mode",
            options=["local", "cloud"],
            horizontal=True,
            index=0 if st.session_state.qdrant_mode == "local" else 1,
        )

        if st.session_state.qdrant_mode == "local":
            st.session_state.qdrant_local_path = st.text_input("Local Qdrant Path", value=st.session_state.qdrant_local_path)
        else:
            st.session_state.qdrant_url = st.text_input("Qdrant URL", value=st.session_state.qdrant_url)
            st.session_state.qdrant_api_key = st.text_input("Qdrant API Key", value=st.session_state.qdrant_api_key, type="password")

        st.session_state.selected_language = st.selectbox(
            "Response Language",
            options=SUPPORTED_LANGUAGES,
            index=SUPPORTED_LANGUAGES.index(st.session_state.selected_language),
        )
        st.session_state.selected_voice = st.selectbox(
            "Voice",
            options=VOICE_OPTIONS,
            index=VOICE_OPTIONS.index(st.session_state.selected_voice),
        )

        profile_names = [item["name"] for item in profiles]
        st.session_state.vehicle_profile = st.selectbox(
            "Vehicle Profile",
            options=profile_names,
            index=profile_names.index(st.session_state.vehicle_profile) if st.session_state.vehicle_profile in profile_names else 0,
        )
        st.session_state.auto_tts = st.checkbox("Generate spoken answer", value=st.session_state.auto_tts)

        if st.button("Connect / Refresh", use_container_width=True):
            _connect_backend()

        if st.session_state.backend_ready:
            st.success("Backend ready")
            st.caption(f"Indexed chunks: {collection_count(st.session_state.qdrant_client)}")
        else:
            st.warning("Backend not initialized")


def _connect_backend() -> None:
    has_qdrant_config = (
        bool(st.session_state.qdrant_local_path)
        if st.session_state.qdrant_mode == "local"
        else bool(st.session_state.qdrant_url and st.session_state.qdrant_api_key)
    )
    if not (st.session_state.openai_api_key and has_qdrant_config):
        st.error("Provide your OpenAI key and Qdrant configuration first.")
        return

    try:
        openai_client, qdrant_client = initialize_backend(
            openai_api_key=st.session_state.openai_api_key,
            qdrant_mode=st.session_state.qdrant_mode,
            qdrant_url=st.session_state.qdrant_url,
            qdrant_api_key=st.session_state.qdrant_api_key,
            qdrant_local_path=st.session_state.qdrant_local_path,
        )
    except RuntimeError as exc:
        st.error("Local Qdrant appears locked by another process. Close other app instances or use a different local path.")
        st.exception(exc)
        return
    except Exception as exc:
        st.error("Backend setup failed.")
        st.exception(exc)
        return

    st.session_state.openai_client = openai_client
    st.session_state.qdrant_client = qdrant_client
    st.session_state.backend_ready = True


def _render_header() -> None:
    st.title("🚗 Multilingual EV Voice Copilot")
    st.markdown(
        "Ask EV manual, charging, warranty, or troubleshooting questions in English or Chinese. "
        "The assistant combines retrieved documents, optional live vehicle telemetry, and spoken responses."
    )


def _render_demo_loader() -> None:
    with st.expander("Demo Dataset", expanded=True):
        st.write("Load synthetic EV support documents for an immediate recruiter-friendly demo.")
        reset = st.checkbox("Reset collection before loading demo dataset", value=False)
        if st.button("Load Demo Dataset"):
            count = seed_demo_dataset(
                openai_client=st.session_state.openai_client,
                qdrant_client=st.session_state.qdrant_client,
                reset=reset,
            )
            st.success(f"Loaded {count} demo chunks into Qdrant.")


def _render_uploads() -> None:
    with st.expander("Upload EV Documents"):
        uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
        col1, col2 = st.columns(2)
        document_type = col1.selectbox("Document Type", options=SUPPORTED_DOCUMENT_TYPES)
        vehicle_model = col2.selectbox("Vehicle Model", options=SUPPORTED_VEHICLE_MODELS)
        col3, col4 = st.columns(2)
        market = col3.selectbox("Market", options=SUPPORTED_MARKETS)
        language = col4.selectbox("Document Language", options=["en", "zh"])
        col5, col6 = st.columns(2)
        model_year = col5.text_input("Model Year", value="2025")
        risk_level = col6.selectbox("Risk Level", options=["normal", "caution", "warning"])
        section_title = st.text_input("Section Title", value="Uploaded EV document")
        source_reliability = st.selectbox("Source Reliability", options=SOURCE_RELIABILITY_OPTIONS, index=0)

        if st.button("Ingest Uploaded PDF"):
            if not uploaded_file:
                st.error("Upload a PDF first.")
                return
            chunks = process_uploaded_pdf(
                uploaded_file,
                {
                    "document_type": document_type,
                    "vehicle_model": vehicle_model,
                    "market": market,
                    "language": language,
                    "model_year": model_year,
                    "risk_level": risk_level,
                    "section_title": section_title,
                    "source_reliability": source_reliability,
                },
            )
            count = upsert_uploaded_chunks(st.session_state.openai_client, st.session_state.qdrant_client, chunks)
            st.success(f"Indexed {count} PDF chunks.")


def _render_query_experience(vehicle_state: dict) -> None:
    st.subheader("Ask the Copilot")
    st.caption("Try questions like: How do I precondition the battery before fast charging? / 我的续航为什么开空调后下降很快？")

    audio_input = st.audio_input("Speak your question") if hasattr(st, "audio_input") else None
    query = st.text_area("Or type your question", height=100, placeholder="Charging stopped at 82 percent. What should I safely check first?")

    if st.button("Ask Copilot", type="primary"):
        transcribed_text = None
        final_query = query.strip()

        if not final_query and audio_input is not None and getattr(audio_input, "getvalue", None) and audio_input.getvalue():
            transcribed_text = transcribe_audio(
                st.session_state.openai_client,
                audio_input.getvalue(),
                filename=getattr(audio_input, "name", "question.wav"),
            )
            final_query = transcribed_text

        if not final_query:
            st.error("Enter or record a question first.")
            return

        started_at = time.perf_counter()
        analysis = analyze_query(final_query, st.session_state.selected_language)
        hits = retrieve_hits(st.session_state.openai_client, st.session_state.qdrant_client, final_query, analysis)
        vehicle_context = summarize_vehicle_state(vehicle_state) if analysis.uses_vehicle_state else "No live vehicle context was needed for this answer."
        draft_answer = answer_query(st.session_state.openai_client, final_query, analysis, hits, vehicle_context)
        final_answer, safety_status = review_answer_for_safety(
            st.session_state.openai_client,
            final_query,
            draft_answer,
            analysis,
            hits,
        )

        audio_bytes = None
        if st.session_state.auto_tts:
            audio_bytes = synthesize_speech(st.session_state.openai_client, final_answer, st.session_state.selected_voice)

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        result = {
            "query": final_query,
            "transcribed_text": transcribed_text,
            "language": analysis.language,
            "intent": analysis.intent,
            "mode_used": analysis.mode_used,
            "confidence": confidence_label(hits),
            "safety_status": safety_status,
            "hits": hits,
            "answer": final_answer,
            "audio_bytes": audio_bytes,
            "latency_ms": latency_ms,
        }
        st.session_state.last_result = result

        log_event(
            "query",
            {
                "query": final_query,
                "language": analysis.language,
                "intent": analysis.intent,
                "mode_used": analysis.mode_used,
                "confidence": result["confidence"],
                "safety_status": safety_status,
                "source_count": len(hits),
            },
        )

    if st.session_state.last_result:
        render_status_row(st.session_state.last_result)
        center, right = st.columns([1.8, 1.2])
        with center:
            render_answer_panel(st.session_state.last_result)
        with right:
            render_sources(st.session_state.last_result["hits"])


def _render_analytics_summary() -> None:
    with st.expander("Analytics Snapshot"):
        summary = summarize_events()
        st.json(summary)


if __name__ == "__main__":
    main()
