from __future__ import annotations

import hashlib
import tempfile
import uuid

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import Distance, PointStruct, VectorParams

from config import CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME, DATA_DIR, EMBEDDING_MODEL, VECTOR_SIZE, load_json


def _embed_texts(openai_client, texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _chunk_texts(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_text(text)


def _stable_point_id(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def recreate_collection(qdrant_client) -> None:
    try:
        qdrant_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def seed_demo_dataset(openai_client, qdrant_client, reset: bool = False) -> int:
    if reset:
        recreate_collection(qdrant_client)

    documents = load_json(DATA_DIR / "demo_documents.json")
    points: list[PointStruct] = []

    for doc in documents:
        chunks = _chunk_texts(doc["content"])
        embeddings = _embed_texts(openai_client, chunks)
        for index, chunk in enumerate(chunks):
            payload = {
                "title": doc["title"],
                "content": chunk,
                "file_name": doc["source_name"],
                "document_type": doc["document_type"],
                "vehicle_model": doc["vehicle_model"],
                "model_year": doc["model_year"],
                "market": doc["market"],
                "language": doc["language"],
                "section_title": doc["section_title"],
                "risk_level": doc["risk_level"],
                "source_reliability": "high",
                "page_number": 1,
                "demo_seed": True,
            }
            points.append(
                PointStruct(
                    id=_stable_point_id(f"{doc['id']}:{index}"),
                    vector=embeddings[index],
                    payload=payload,
                )
            )

    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def process_uploaded_pdf(uploaded_file, metadata: dict) -> list[dict]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        loader = PyPDFLoader(temp_file.name)
        pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks: list[dict] = []
    for page in pages:
        page_number = int(page.metadata.get("page", 0)) + 1
        page_chunks = splitter.split_text(page.page_content)
        for index, chunk in enumerate(page_chunks):
            payload = {
                "title": metadata.get("section_title") or uploaded_file.name,
                "content": chunk,
                "file_name": uploaded_file.name,
                "document_type": metadata["document_type"],
                "vehicle_model": metadata["vehicle_model"],
                "model_year": metadata["model_year"],
                "market": metadata["market"],
                "language": metadata["language"],
                "section_title": metadata.get("section_title") or f"Page {page_number}",
                "risk_level": metadata["risk_level"],
                "source_reliability": metadata["source_reliability"],
                "page_number": page_number,
                "upload_hash": hashlib.sha1(uploaded_file.getvalue()).hexdigest(),
                "demo_seed": False,
                "chunk_index": index,
            }
            chunks.append(payload)
    return chunks


def upsert_uploaded_chunks(openai_client, qdrant_client, chunks: list[dict]) -> int:
    texts = [item["content"] for item in chunks]
    embeddings = _embed_texts(openai_client, texts)
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=embeddings[index], payload=payload)
        for index, payload in enumerate(chunks)
    ]
    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)
