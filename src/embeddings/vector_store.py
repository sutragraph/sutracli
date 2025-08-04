"""
Unified vector store that combines embedding generation and vector storage.
Merges the functionality of simple_processor.py and vector_db.py into a clean interface.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import onnxruntime as ort
import sqlite_vec
from loguru import logger
from tokenizers import Tokenizer

from config import config


class EmbeddingModel:
    """Handles embedding model loading and inference."""

    def __init__(self, model_path: str = "models/all-MiniLM-L12-v2"):
        self.model_path = Path(model_path)
        self.session = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the ONNX model and tokenizer."""
        try:
            model_file = self.model_path / "model.onnx"
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")

            providers = ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(model_file), providers=providers)
            self.input_names = [input.name for input in self.session.get_inputs()]

            tokenizer_file = self.model_path / "tokenizer.json"
            if tokenizer_file.exists():
                self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
            else:
                logger.warning("Tokenizer file not found, using basic tokenization")

            logger.debug(f"Loaded embedding model from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _tokenize(self, text: str, max_length: int = 256) -> Dict[str, np.ndarray]:
        """Tokenize text for the model."""
        if self.tokenizer:
            encoding = self.tokenizer.encode(text)
            tokens = encoding.ids
            attention_mask = encoding.attention_mask

            # Truncate or pad to max_length
            if len(tokens) > max_length:
                tokens = tokens[:max_length]
                attention_mask = attention_mask[:max_length]
            else:
                padding_length = max_length - len(tokens)
                tokens.extend([0] * padding_length)
                attention_mask.extend([0] * padding_length)
        else:
            # Basic fallback tokenization
            tokens = (
                [1]
                + [hash(word) % 30000 for word in text.split()][: max_length - 2]
                + [2]
            )
            tokens = tokens[:max_length]
            attention_mask = [1] * len(tokens)

            # Pad if necessary
            if len(tokens) < max_length:
                padding_length = max_length - len(tokens)
                tokens.extend([0] * padding_length)
                attention_mask.extend([0] * padding_length)

        # Create token_type_ids (all zeros for single sentence)
        token_type_ids = [0] * len(tokens)

        return {
            "input_ids": np.array([tokens], dtype=np.int64),
            "attention_mask": np.array([attention_mask], dtype=np.int64),
            "token_type_ids": np.array([token_type_ids], dtype=np.int64),
        }

    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)

        try:
            inputs = self._tokenize(text)
            outputs = self.session.run(None, inputs)
            embeddings = np.array(outputs[0], dtype=np.float32)

            # Mean pooling
            attention_mask = inputs["attention_mask"].astype(np.float32)
            masked_embeddings = embeddings * np.expand_dims(attention_mask, -1)
            summed = np.sum(masked_embeddings, axis=1)
            counts = np.sum(attention_mask, axis=1, keepdims=True)
            counts = np.maximum(counts, 1e-8)
            mean_pooled = summed / counts

            return mean_pooled[0]

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return np.zeros(384, dtype=np.float32)

    def get_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts in batch for better performance."""
        if not texts:
            return []

        try:
            # Tokenize all texts
            all_inputs = []
            for text in texts:
                if not text or not text.strip():
                    all_inputs.append({
                        "input_ids": np.zeros((1, 256), dtype=np.int64),
                        "attention_mask": np.zeros((1, 256), dtype=np.int64),
                        "token_type_ids": np.zeros((1, 256), dtype=np.int64),
                    })
                else:
                    all_inputs.append(self._tokenize(text))

            # Batch all inputs
            batch_input_ids = np.vstack([inp["input_ids"] for inp in all_inputs])
            batch_attention_mask = np.vstack([inp["attention_mask"] for inp in all_inputs])
            batch_token_type_ids = np.vstack([inp["token_type_ids"] for inp in all_inputs])

            batch_inputs = {
                "input_ids": batch_input_ids,
                "attention_mask": batch_attention_mask,
                "token_type_ids": batch_token_type_ids,
            }

            # Run inference on entire batch
            outputs = self.session.run(None, batch_inputs)
            embeddings = np.array(outputs[0], dtype=np.float32)

            # Mean pooling for each item in batch
            attention_mask = batch_attention_mask.astype(np.float32)
            masked_embeddings = embeddings * np.expand_dims(attention_mask, -1)
            summed = np.sum(masked_embeddings, axis=1)
            counts = np.sum(attention_mask, axis=1, keepdims=True)
            counts = np.maximum(counts, 1e-8)
            mean_pooled = summed / counts

            return [mean_pooled[i] for i in range(len(texts))]

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            # Fallback to individual processing
            return [self.get_embedding(text) for text in texts]


class TextChunker:
    """Handles text chunking with precise line tracking."""

    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def chunk_text(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with line tracking."""
        if not text or not text.strip():
            return []

        lines = text.splitlines(keepends=True)
        if not lines:
            return []

        chunks = []
        current_chunk_lines = []
        current_tokens = 0
        start_line = 1

        for line_num, line in enumerate(lines, 1):
            # Estimate tokens for this line (rough approximation)
            line_tokens = len(line.split()) + 1

            if current_tokens + line_tokens > max_tokens and current_chunk_lines:
                # Create chunk from current lines
                chunk_text = "".join(current_chunk_lines)
                chunks.append(
                    {
                        "text": chunk_text,
                        "start": len("".join(lines[: start_line - 1])),
                        "end": len("".join(lines[: line_num - 1])),
                        "start_line": start_line,
                        "end_line": line_num - 1,
                    }
                )

                # Start new chunk with overlap
                overlap_lines = max(1, overlap_tokens // 10)  # Rough estimate
                if len(current_chunk_lines) > overlap_lines:
                    current_chunk_lines = current_chunk_lines[-overlap_lines:]
                    start_line = line_num - overlap_lines
                    current_tokens = sum(
                        len(l.split()) + 1 for l in current_chunk_lines
                    )
                else:
                    current_chunk_lines = []
                    current_tokens = 0
                    start_line = line_num

            current_chunk_lines.append(line)
            current_tokens += line_tokens

        # Add final chunk
        if current_chunk_lines:
            chunk_text = "".join(current_chunk_lines)
            chunks.append(
                {
                    "text": chunk_text,
                    "start": len("".join(lines[: start_line - 1])),
                    "end": len(text),
                    "start_line": start_line,
                    "end_line": len(lines),
                }
            )

        return chunks

    def get_chunked_embeddings(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """Get embeddings for text chunks with metadata using batch processing."""
        chunks = self.chunk_text(text, max_tokens, overlap_tokens)

        if not chunks:
            return []

        # Extract all chunk texts for batch processing
        chunk_texts = [chunk["text"] for chunk in chunks]

        try:
            # Generate embeddings in batch for much better performance
            logger.debug(f"Generating batch embeddings for {len(chunk_texts)} chunks")
            embeddings = self.embedding_model.get_embeddings_batch(chunk_texts)
            logger.debug(f"Successfully generated {len(embeddings)} batch embeddings")

            # Combine embeddings with metadata
            embeddings_with_metadata = []
            for embedding, chunk in zip(embeddings, chunks):
                embeddings_with_metadata.append((embedding, chunk))

            return embeddings_with_metadata

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings, falling back to individual: {e}")
            import traceback
            logger.error(f"Batch embedding error details: {traceback.format_exc()}")
            # Fallback to individual processing
            embeddings_with_metadata = []
            for chunk in chunks:
                try:
                    embedding = self.embedding_model.get_embedding(chunk["text"])
                    embeddings_with_metadata.append((embedding, chunk))
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk: {e}")
                    continue
            return embeddings_with_metadata


class VectorStore:
    """Unified vector store with embedding generation and similarity search."""

    def __init__(self, db_path: str = None, model_path: str = None):
        # Initialize database
        if db_path is None:
            db_path = config.sqlite.embeddings_db
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None

        # Initialize embedding components
        if model_path is None:
            try:
                import os
                from config.settings import get_config

                config_obj = get_config()
                model_path = os.path.expanduser(config_obj.embedding.model_path)
            except Exception:
                model_path = "models/all-MiniLM-L12-v2"

        self.embedding_model = EmbeddingModel(model_path)
        self.text_chunker = TextChunker(self.embedding_model)

        self._connect()

    def _connect(self):
        """Connect to vector database and setup tables."""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.enable_load_extension(True)
            sqlite_vec.load(self.connection)
            self._setup_vector_tables()
            logger.debug(f"Connected to vector store: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to vector store: {e}")
            raise

    def _setup_vector_tables(self):
        """Setup vector tables using sqlite-vec."""
        try:
            self.connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                    node_id TEXT,
                    project_id INTEGER,
                    chunk_index INTEGER,
                    chunk_start_line INTEGER,
                    chunk_end_line INTEGER,
                    embedding FLOAT[384]
                )
            """
            )
            self.connection.commit()
            logger.debug("Vector tables setup complete")
        except Exception as e:
            logger.error(f"Failed to setup vector tables: {e}")
            raise

    # Embedding generation methods
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        return self.embedding_model.get_embedding(text)

    def chunk_text(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Dict[str, Any]]:
        """Split text into chunks with line tracking."""
        return self.text_chunker.chunk_text(text, max_tokens, overlap_tokens)

    def get_chunked_embeddings(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """Get embeddings for text chunks."""
        return self.text_chunker.get_chunked_embeddings(
            text, max_tokens, overlap_tokens
        )

    # Vector storage methods
    def store_embedding(
        self,
        node_id: str,
        project_id: int,
        chunk_index: int,
        embedding: np.ndarray,
        chunk_start_line: int,
        chunk_end_line: int,
    ) -> int:
        """Store embedding in vector database."""
        try:
            if isinstance(embedding, np.ndarray):
                embedding_array = embedding.astype(np.float32)
            else:
                embedding_array = np.array(embedding, dtype=np.float32)

            if len(embedding_array.shape) != 1 or embedding_array.shape[0] != 384:
                raise ValueError(
                    f"Expected 384-dimensional vector, got shape {embedding_array.shape}"
                )

            cursor = self.connection.execute(
                """INSERT INTO embeddings (node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, embedding)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    node_id,
                    project_id,
                    chunk_index,
                    chunk_start_line,
                    chunk_end_line,
                    embedding_array,
                ),
            )

            embedding_id = cursor.lastrowid
            self.connection.commit()
            return embedding_id

        except Exception as e:
            logger.error(f"Failed to store embedding for node {node_id}: {e}")
            raise

    def store_embeddings_batch(self, embedding_data_list: List[Dict]) -> List[int]:
        """
        Store multiple embeddings in a single database transaction for massive performance improvement.

        Args:
            embedding_data_list: List of dictionaries containing embedding data

        Returns:
            List of embedding IDs
        """
        if not embedding_data_list:
            return []

        embedding_ids = []

        try:
            # Begin transaction for batch insert
            cursor = self.connection.cursor()
            cursor.execute("BEGIN TRANSACTION")

            for data in embedding_data_list:
                # Validate and convert embedding
                embedding = data['embedding']
                if isinstance(embedding, np.ndarray):
                    embedding_array = embedding.astype(np.float32)
                else:
                    embedding_array = np.array(embedding, dtype=np.float32)

                if len(embedding_array.shape) != 1 or embedding_array.shape[0] != 384:
                    raise ValueError(
                        f"Expected 384-dimensional vector, got shape {embedding_array.shape}"
                    )

                cursor.execute(
                    """INSERT INTO embeddings (node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, embedding)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        data['node_id'],
                        data['project_id'],
                        data['chunk_index'],
                        data['chunk_start_line'],
                        data['chunk_end_line'],
                        embedding_array,
                    ),
                )
                embedding_ids.append(cursor.lastrowid)

            # Commit all inserts at once - this is the key performance improvement!
            cursor.execute("COMMIT")
            logger.debug(f"Batch stored {len(embedding_ids)} embeddings in single transaction")

        except Exception as e:
            cursor.execute("ROLLBACK")
            logger.error(f"Failed to batch store embeddings: {e}")
            raise

        return embedding_ids

    def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 30,
        threshold: float = 0.20,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        try:
            if isinstance(query_embedding, np.ndarray):
                query_vector = query_embedding.astype(np.float32)
            else:
                query_vector = np.array(query_embedding, dtype=np.float32)

            if len(query_vector.shape) != 1 or query_vector.shape[0] != 384:
                raise ValueError(
                    f"Expected 384-dimensional query vector, got shape {query_vector.shape}"
                )

            # Build query with optional project filtering
            if project_id is not None:
                query_sql = """
                    SELECT rowid, node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, distance
                    FROM embeddings
                    WHERE embedding MATCH ? AND project_id = ?
                    ORDER BY distance
                    LIMIT ?
                """
                query_params = (query_vector, project_id, limit)
            else:
                query_sql = """
                    SELECT rowid, node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, distance
                    FROM embeddings
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """
                query_params = (query_vector, limit)

            cursor = self.connection.execute(query_sql, query_params)
            results = []

            for row in cursor.fetchall():
                (
                    embedding_id,
                    node_id,
                    proj_id,
                    chunk_index,
                    chunk_start_line,
                    chunk_end_line,
                    distance,
                ) = row

                # Convert distance to similarity
                similarity = 1.0 / (1.0 + distance)

                if similarity >= threshold:
                    results.append(
                        {
                            "embedding_id": embedding_id,
                            "node_id": node_id,
                            "project_id": proj_id,
                            "chunk_index": chunk_index,
                            "chunk_start_line": chunk_start_line,
                            "chunk_end_line": chunk_end_line,
                            "similarity": similarity,
                            "distance": distance,
                        }
                    )

            return results

        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            return []

    def search_similar_chunks(
        self,
        query_text: str,
        limit: int = 30,
        threshold: float = 0.2,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using text query."""
        try:
            query_embedding = self.get_embedding(query_text)
            return self.search_similar(query_embedding, limit, threshold, project_id)
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            stats = {}

            # Total embeddings
            cursor = self.connection.execute("SELECT COUNT(*) FROM embeddings")
            stats["total_embeddings"] = cursor.fetchone()[0]

            # Unique nodes
            cursor = self.connection.execute(
                "SELECT COUNT(DISTINCT node_id) FROM embeddings"
            )
            stats["unique_nodes"] = cursor.fetchone()[0]

            # Average chunks per node
            if stats["unique_nodes"] > 0:
                stats["average_chunks_per_node"] = round(
                    stats["total_embeddings"] / stats["unique_nodes"], 2
                )
            else:
                stats["average_chunks_per_node"] = 0

            stats["storage_method"] = "sqlite-vec"
            stats["vector_dimension"] = 384
            stats["database_size_mb"] = round(
                self.db_path.stat().st_size / (1024 * 1024), 2
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {
                "total_embeddings": 0,
                "unique_nodes": 0,
                "average_chunks_per_node": 0,
                "storage_method": "unknown",
                "error": str(e),
            }

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Vector store connection closed")


# Global instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
