from __future__ import annotations

from config import CHAT_MODEL, HIGH_RISK_KEYWORDS, load_prompt
from models import QueryAnalysis, RetrievedHit


def _source_context(hits: list[RetrievedHit]) -> str:
    lines = []
    for index, hit in enumerate(hits[:5], start=1):
        metadata = hit.metadata
        lines.append(
            f"Source {index}: {metadata.get('title', metadata.get('file_name', 'Unknown'))}\n"
            f"Document type: {metadata.get('document_type')}\n"
            f"Vehicle model: {metadata.get('vehicle_model')}\n"
            f"Market: {metadata.get('market')}\n"
            f"Language: {metadata.get('language')}\n"
            f"Section: {metadata.get('section_title')}\n"
            f"Page: {metadata.get('page_number')}\n"
            f"Excerpt: {hit.text}\n"
        )
    return "\n".join(lines) if lines else "No internal sources were retrieved."


def answer_query(
    openai_client,
    question: str,
    analysis: QueryAnalysis,
    hits: list[RetrievedHit],
    vehicle_context: str,
) -> str:
    prompt_name = "troubleshooting_agent.md" if analysis.intent == "troubleshooting" else "answer_agent.md"
    system_prompt = load_prompt(prompt_name)
    response_language = "Chinese" if analysis.language == "chinese" else "English"

    user_prompt = (
        f"Question: {question}\n\n"
        f"Detected language: {analysis.language}\n"
        f"Detected intent: {analysis.intent}\n"
        f"Detected vehicle model: {analysis.vehicle_model}\n"
        f"Mode used: {analysis.mode_used}\n\n"
        f"Live vehicle context:\n{vehicle_context}\n\n"
        f"Retrieved sources:\n{_source_context(hits)}\n\n"
        f"Respond in {response_language}. Be concise but specific."
    )

    completion = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return completion.choices[0].message.content.strip()


def review_answer_for_safety(
    openai_client,
    question: str,
    answer: str,
    analysis: QueryAnalysis,
    hits: list[RetrievedHit],
) -> tuple[str, str]:
    lowered_question = question.lower()
    high_risk = any(keyword in lowered_question for keyword in HIGH_RISK_KEYWORDS)
    high_risk = high_risk or any(hit.metadata.get("risk_level") == "warning" for hit in hits)

    if not high_risk and analysis.intent in {"warning_light", "troubleshooting", "service_escalation"}:
        status = "caution"
    elif high_risk:
        status = "warning"
    else:
        status = "normal"

    if status == "normal":
        return answer, status

    system_prompt = load_prompt("safety_reviewer.md")
    review_prompt = (
        f"Question: {question}\n\n"
        f"Detected intent: {analysis.intent}\n"
        f"Safety status: {status}\n\n"
        f"Draft answer:\n{answer}\n\n"
        "Rewrite the answer so it stays helpful, avoids unsafe overconfidence, and clearly marks when the user should stop and contact authorized service."
    )

    try:
        completion = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": review_prompt},
            ],
        )
        return completion.choices[0].message.content.strip(), status
    except Exception:
        prefix = "Safety note: If the issue involves a warning indicator, high-voltage systems, brake performance, or unusual heat, stop and contact authorized service.\n\n"
        return prefix + answer, status
