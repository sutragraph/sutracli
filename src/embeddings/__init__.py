"""
Embeddings module - unified embedding generation and vector storage.
Clean architecture with proper separation of concerns.
"""

from embeddings.vector_store import VectorStore, get_vector_store
from embeddings.embedding_engine import (
    EmbeddingEngine,
    get_embedding_engine,
    parse_entity_id,
)

__all__ = [
    "VectorStore",
    "get_vector_store",
    "EmbeddingEngine",
    "get_embedding_engine",
    "parse_entity_id",
]
