"""
Embeddings module initialization.
Contains only core embedding functionality - no processing logic.
"""

from .simple_processor import SimpleEmbeddingProcessor, get_embedding_processor
from .vector_db import VectorDatabase, get_vector_db

__all__ = [
    "SimpleEmbeddingProcessor",
    "get_embedding_processor", 
    "VectorDatabase",
    "get_vector_db"
]