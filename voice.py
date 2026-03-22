from __future__ import annotations

import io
import re

from config import TRANSCRIPTION_MODEL, TTS_MODEL


def transcribe_audio(openai_client, audio_bytes: bytes, filename: str = "question.wav") -> str:
    buffer = io.BytesIO(audio_bytes)
    buffer.name = filename
    response = openai_client.audio.transcriptions.create(model=TRANSCRIPTION_MODEL, file=buffer)
    return response.text.strip()


def _plain_text_for_tts(text: str) -> str:
    cleaned = re.sub(r"[`*_>#-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def synthesize_speech(openai_client, text: str, voice: str) -> bytes:
    response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=_plain_text_for_tts(text)[:3000],
    )
    if hasattr(response, "read"):
        return response.read()
    if hasattr(response, "content"):
        return response.content
    if hasattr(response, "iter_bytes"):
        return b"".join(response.iter_bytes())
    raise RuntimeError("Unsupported TTS response type returned by OpenAI client.")
