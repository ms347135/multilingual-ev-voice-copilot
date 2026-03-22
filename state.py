from __future__ import annotations

import streamlit as st


def init_session_state() -> None:
    defaults = {
        "openai_api_key": "",
        "qdrant_mode": "local",
        "qdrant_url": "",
        "qdrant_api_key": "",
        "qdrant_local_path": "qdrant_local_data",
        "openai_client": None,
        "qdrant_client": None,
        "backend_ready": False,
        "selected_voice": "nova",
        "selected_language": "auto",
        "vehicle_profile": "BYD Seal Dynamic Range",
        "auto_tts": True,
        "last_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
