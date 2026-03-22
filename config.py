from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ANALYTICS_DIR = BASE_DIR / "analytics"
EVALS_DIR = BASE_DIR / "evals"
PROMPTS_DIR = BASE_DIR / "prompts"
LOCAL_QDRANT_PATH = BASE_DIR / "qdrant_local_data"

COLLECTION_NAME = "ev_voice_copilot_docs"
VECTOR_SIZE = 1536
CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
TTS_MODEL = "gpt-4o-mini-tts"
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"

TOP_K = 8
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

SUPPORTED_LANGUAGES = ["auto", "english", "chinese"]
SUPPORTED_MARKETS = ["global", "brazil", "thailand", "hungary", "vietnam", "indonesia", "china"]
SUPPORTED_VEHICLE_MODELS = [
    "General",
    "Seal",
    "Dolphin",
    "Atto 3",
    "Han",
    "Tang",
    "Seagull",
]
SUPPORTED_DOCUMENT_TYPES = [
    "owner_manual",
    "charging_guide",
    "quick_start",
    "warranty_terms",
    "roadside_safety",
    "service_faq",
    "glossary",
]
SOURCE_RELIABILITY_OPTIONS = ["high", "medium", "low"]
VOICE_OPTIONS = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"]
HIGH_RISK_KEYWORDS = [
    "high voltage",
    "battery fire",
    "thermal runaway",
    "airbag",
    "brake failure",
    "coolant leak",
    "electrical disassembly",
    "open battery pack",
    "电池起火",
    "高压系统",
    "安全气囊",
    "刹车失灵",
]


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ANALYTICS_DIR.mkdir(exist_ok=True)
    EVALS_DIR.mkdir(exist_ok=True)
    PROMPTS_DIR.mkdir(exist_ok=True)


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
