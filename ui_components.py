from __future__ import annotations

import streamlit as st

from models import RetrievedHit


def render_vehicle_panel(profile_name: str, state: dict, warnings: list[str]) -> None:
    st.subheader("Vehicle State")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Profile", profile_name)
    col2.metric("SOC", f"{state.get('soc', 'N/A')}%")
    col3.metric("Range", f"{state.get('estimated_range_km', 'N/A')} km")
    col4.metric("Charge Status", str(state.get("charging_status", "N/A")).replace("_", " ").title())
    if warnings:
        for item in warnings:
            st.warning(item)


def render_status_row(result: dict) -> None:
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Language", result["language"].title())
    col2.metric("Intent", result["intent"].replace("_", " ").title())
    col3.metric("Mode", result["mode_used"].replace("_", " + ").title())
    col4.metric("Confidence", result["confidence"].title())
    col5.metric("Safety", result["safety_status"].title())
    col6.metric("Sources", str(len(result["hits"])))
    st.caption(f"Latency: {result['latency_ms']} ms")


def render_answer_panel(result: dict) -> None:
    st.subheader("Copilot Answer")
    if result.get("transcribed_text"):
        st.caption(f"Transcribed speech: {result['transcribed_text']}")
    st.markdown(result["answer"])
    if result.get("audio_bytes"):
        st.audio(result["audio_bytes"], format="audio/mp3")


def render_sources(hits: list[RetrievedHit]) -> None:
    st.subheader("Citations")
    if not hits:
        st.info("No internal sources were retrieved.")
        return
    for index, hit in enumerate(hits[:5], start=1):
        metadata = hit.metadata
        with st.container(border=True):
            st.markdown(f"**{index}. {metadata.get('title', metadata.get('file_name', 'Unknown Source'))}**")
            st.caption(
                f"{metadata.get('document_type')} | {metadata.get('vehicle_model')} | {metadata.get('market')} | "
                f"page {metadata.get('page_number')} | rerank {hit.rerank_score:.2f}"
            )
            st.write(hit.text)
