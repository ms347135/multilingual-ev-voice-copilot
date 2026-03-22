from __future__ import annotations

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams

from config import COLLECTION_NAME, LOCAL_QDRANT_PATH, VECTOR_SIZE


def initialize_backend(
    openai_api_key: str,
    qdrant_mode: str,
    qdrant_url: str,
    qdrant_api_key: str,
    qdrant_local_path: str,
):
    openai_client = OpenAI(api_key=openai_api_key)

    if qdrant_mode == "local":
        local_path = qdrant_local_path or str(LOCAL_QDRANT_PATH)
        qdrant_client = QdrantClient(path=local_path)
    else:
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    qdrant_client.get_collections()

    try:
        qdrant_client.get_collection(COLLECTION_NAME)
    except (UnexpectedResponse, ValueError):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    return openai_client, qdrant_client


def collection_count(qdrant_client: QdrantClient) -> int:
    info = qdrant_client.get_collection(COLLECTION_NAME)
    return int(getattr(info, "points_count", 0) or 0)
