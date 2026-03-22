# Multilingual EV Voice Copilot - Project Plan

This repo is the standalone transformation of the downloaded GitHub example in `repo_inspect/voice_ai_agents/voice_rag_openaisdk`.

## Source We Started From

- Base example: `repo_inspect/voice_ai_agents/voice_rag_openaisdk`
- Transformation reference: `repo_inspect/voice_ai_agents/voice_rag_openaisdk/EV_VOICE_COPILOT_PLAN.md`

## Final Public Identity

- Project name: `Multilingual EV Voice Copilot`
- Repo slug: `multilingual-ev-voice-copilot`

## Product Goal

Turn the generic voice-RAG demo into a serious `multilingual EV support copilot` for portfolio use.

The final app should feel like an automotive AI product, not a basic PDF chatbot.

## What We Are Changing From The Original GitHub Project

- Refactor the single-file demo into a modular app structure.
- Replace generic document chat with EV manual, charging, warranty, and troubleshooting support.
- Add `English + Chinese` interaction support.
- Add metadata-aware ingestion and filtered retrieval.
- Add mocked live vehicle telemetry for state-aware answers.
- Add troubleshooting mode with safer escalation guidance.
- Add speech input and text-to-speech output.
- Add a cleaner recruiter-ready README and sample evaluation data.

## Build Checklist

- [x] Confirm source project and transformation direction
- [x] Create standalone repo folder
- [x] Add modular app files
- [x] Add demo data and mock vehicle state
- [x] Add multilingual retrieval and answer flow
- [x] Add voice transcription and TTS flow
- [x] Add troubleshooting and safety behavior
- [x] Write recruiter-ready README
- [x] Validate the code locally
- [x] Initialize Git, commit, and prepare/push repo
- [x] Update `CV_PROJECTS_MASTER.md` with Project 2 details

## Final Status

- GitHub repo: `https://github.com/ms347135/multilingual-ev-voice-copilot`
- Local virtual environment created: `.venv`
- Dependencies installed and import checks passed
- Initial commit pushed to `main`

## Push Standard

Only push after the repo has:

- a clear project name
- a clean README
- runnable app structure
- demo data for easy testing
- honest feature claims
- CV-ready positioning

## Notes

This file should stay in the repo so we always know:

- what the original GitHub project was
- what was changed from the source
- why the transformed version is stronger for your BYD/LLM applications
