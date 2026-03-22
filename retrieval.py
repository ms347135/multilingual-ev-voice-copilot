from __future__ import annotations

import re

from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue

from config import COLLECTION_NAME, EMBEDDING_MODEL, SUPPORTED_VEHICLE_MODELS, TOP_K
from models import QueryAnalysis, RetrievedHit
from vehicle_tools import should_use_vehicle_state


def detect_language(query: str, preferred_language: str) -> str:
    if preferred_language == "english":
        return "english"
    if preferred_language == "chinese":
        return "chinese"
    if re.search(r"[\u4e00-\u9fff]", query):
        return "chinese"
    return "english"


def detect_vehicle_model(query: str) -> str:
    lowered = query.lower()
    for model in SUPPORTED_VEHICLE_MODELS:
        if model == "General":
            continue
        if model.lower() in lowered:
            return model
    if "atto3" in lowered or "atto 3" in lowered:
        return "Atto 3"
    return "General"


def classify_intent(query: str) -> str:
    lowered = query.lower()
    if any(keyword in lowered for keyword in ["warning light", "fault", "error", "warning", "警告", "故障", "报码"]):
        return "warning_light"
    if any(keyword in lowered for keyword in ["charging stopped", "stopped at", "not charging", "interrupted", "检查", "排查", "troubleshoot", "problem", "issue"]):
        return "troubleshooting"
    if any(keyword in lowered for keyword in ["service center", "service", "visit service", "authorized service", "售后", "维修中心"]):
        return "service_escalation"
    if any(keyword in lowered for keyword in ["range", "efficiency", "consumption", "空调", "续航", "里程"]):
        return "range_question"
    if any(keyword in lowered for keyword in ["charge", "charging", "dc fast", "ac charging", "plug", "充电", "快充", "慢充"]):
        return "charging_help"
    return "manual_qa"


def preferred_doc_types(intent: str) -> list[str]:
    mapping = {
        "manual_qa": ["owner_manual", "quick_start"],
        "charging_help": ["charging_guide", "quick_start", "owner_manual"],
        "warning_light": ["roadside_safety", "owner_manual", "service_faq"],
        "range_question": ["owner_manual", "quick_start", "service_faq"],
        "troubleshooting": ["service_faq", "roadside_safety", "owner_manual"],
        "service_escalation": ["service_faq", "warranty_terms", "roadside_safety"],
    }
    return mapping.get(intent, ["owner_manual"])


def analyze_query(query: str, preferred_language: str) -> QueryAnalysis:
    language = detect_language(query, preferred_language)
    intent = classify_intent(query)
    vehicle_model = detect_vehicle_model(query)
    uses_state = should_use_vehicle_state(query, intent)
    mode_used = "docs_plus_state" if uses_state else "docs_only"
    if intent == "troubleshooting":
        mode_used = "troubleshooting"
    return QueryAnalysis(
        language=language,
        intent=intent,
        vehicle_model=vehicle_model,
        doc_type_preferences=preferred_doc_types(intent),
        uses_vehicle_state=uses_state,
        mode_used=mode_used,
    )


def _language_code(language: str) -> str:
    return "zh" if language == "chinese" else "en"


def _build_filter(analysis: QueryAnalysis) -> Filter | None:
    must = []
    if analysis.vehicle_model != "General":
        must.append(FieldCondition(key="vehicle_model", match=MatchValue(value=analysis.vehicle_model)))
    if analysis.doc_type_preferences:
        must.append(FieldCondition(key="document_type", match=MatchAny(any=analysis.doc_type_preferences)))
    must.append(FieldCondition(key="language", match=MatchAny(any=[_language_code(analysis.language), "en", "zh"])))
    return Filter(must=must) if must else None


def _embed_query(openai_client, query: str) -> list[float]:
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    return response.data[0].embedding


def retrieve_hits(openai_client, qdrant_client, query: str, analysis: QueryAnalysis, limit: int = TOP_K) -> list[RetrievedHit]:
    query_vector = _embed_query(openai_client, query)
    query_filter = _build_filter(analysis)

    response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
        query_filter=query_filter,
    )
    points = list(getattr(response, "points", []) or [])

    if not points:
        response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        points = list(getattr(response, "points", []) or [])

    reranked: list[RetrievedHit] = []
    for point in points:
        payload = point.payload or {}
        rerank_score = float(point.score or 0)
        if payload.get("vehicle_model") == analysis.vehicle_model and analysis.vehicle_model != "General":
            rerank_score += 0.20
        if payload.get("language") == _language_code(analysis.language):
            rerank_score += 0.10
        if payload.get("document_type") in analysis.doc_type_preferences:
            rerank_score += 0.12
        if analysis.intent in {"warning_light", "troubleshooting"} and payload.get("risk_level") in {"caution", "warning"}:
            rerank_score += 0.10
        reranked.append(
            RetrievedHit(
                text=payload.get("content", ""),
                score=float(point.score or 0),
                rerank_score=rerank_score,
                metadata=payload,
            )
        )

    reranked.sort(key=lambda hit: hit.rerank_score, reverse=True)
    return reranked


def confidence_label(hits: list[RetrievedHit]) -> str:
    if not hits:
        return "low"
    top_score = hits[0].rerank_score
    if top_score >= 0.92 and len(hits) >= 3:
        return "high"
    if top_score >= 0.68:
        return "medium"
    return "low"
