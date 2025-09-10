"""
Unified vector store that combines embedding generation and vector storage.
Merges the functionality of simple_processor.py and vector_db.py into a clean interface.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        self.session: Optional[ort.InferenceSession] = None
        self.tokenizer: Optional[Tokenizer] = None
        self.input_names: List[str] = []
        self._load_model()

    def _load_model(self) -> None:
        """Load the ONNX model and tokenizer."""
        try:
            model_file = self.model_path / "model.onnx"
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")

            providers = ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(model_file), providers=providers)
            self.input_names = [inp.name for inp in self.session.get_inputs()]

            tokenizer_file = self.model_path / "tokenizer.json"
            if tokenizer_file.exists():
                self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
                # Override tokenizer's default max_length to use model's full capacity
                if self.tokenizer is not None:
                    self.tokenizer.enable_truncation(
                        max_length=config.embedding.tokenizer_max_length
                    )
                    self.tokenizer.enable_padding(
                        length=config.embedding.tokenizer_max_length
                    )
            else:
                logger.warning("Tokenizer file not found, using basic tokenization")
                self.tokenizer = None

            logger.debug(f"Loaded embedding model from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _tokenize(
        self, text: str, max_length: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """Tokenize text for the model."""
        if max_length is None:
            max_length = config.embedding.tokenizer_max_length

        # Type assertion to help type checker
        assert max_length is not None, "max_length must be set"

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

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens using the actual tokenizer with detailed logging."""
        if not self.tokenizer:
            raise RuntimeError(
                "Tokenizer not available - cannot count tokens accurately"
            )

        try:
            # Align counting with the embedding model's tokenization and max length
            inputs = self._tokenize(
                text, max_length=config.embedding.tokenizer_max_length
            )
            attention_mask = inputs["attention_mask"]
            if isinstance(attention_mask, np.ndarray):
                # attention_mask shape is (1, seq_len)
                token_count = int(attention_mask[0].sum().item())
            else:
                token_count = int(sum(attention_mask))

            return token_count
        except Exception as e:
            logger.error(f"❌ TOKENIZER FAILED: {e}")
            logger.error(f"❌ Text length: {len(text)}")
            logger.error(f"❌ Text preview: '{text[:200]}...'")
            raise RuntimeError(f"Tokenizer failed: {e}")

    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)

        try:
            inputs = self._tokenize(text)
            session = self.session
            if session is None:
                raise RuntimeError("Embedding model session is not initialized")
            outputs = session.run(None, inputs)
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
            # Pre-allocate batch tensors for better performance
            batch_size = len(texts)
            max_length = config.embedding.tokenizer_max_length

            batch_input_ids = np.zeros((batch_size, max_length), dtype=np.int64)
            batch_attention_mask = np.zeros((batch_size, max_length), dtype=np.int64)
            batch_token_type_ids = np.zeros((batch_size, max_length), dtype=np.int64)

            # Batch tokenization with direct tensor insertion
            for i, text in enumerate(texts):
                if text and text.strip():
                    tokens = self._tokenize(text)
                    batch_input_ids[i] = tokens["input_ids"].reshape(-1)[:max_length]
                    batch_attention_mask[i] = tokens["attention_mask"].reshape(-1)[
                        :max_length
                    ]
                    batch_token_type_ids[i] = tokens["token_type_ids"].reshape(-1)[
                        :max_length
                    ]
                # Empty texts remain as zeros (already pre-allocated)

            batch_inputs = {
                "input_ids": batch_input_ids,
                "attention_mask": batch_attention_mask,
                "token_type_ids": batch_token_type_ids,
            }

            # Run inference on entire batch
            session = self.session
            if session is None:
                raise RuntimeError("Embedding model session is not initialized")
            outputs = session.run(None, batch_inputs)
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
        self._fallback_logged = False  # Track if we've logged the fallback warning

    def _count_tokens(self, text: str) -> int:
        """Accurately count tokens using the embedding model's tokenizer."""
        # Use the embedding model's tokenizer for accurate token counting
        return self.embedding_model.count_tokens(text)

    def chunk_text(
        self,
        text: str,
        max_tokens: int = 240,
        overlap_tokens: int = 30,
        metadata: str = "",
    ) -> List[Dict[str, Any]]:
        """Split text into token-based adaptive chunks. First chunk includes metadata prefix once."""
        if not text or not text.strip():
            return []

        lines = text.splitlines(keepends=True)
        if not lines:
            return []

        chunks: List[Dict[str, Any]] = []
        metadata_prefix = (metadata + "\n\n") if metadata else ""

        # Reserve tokens for metadata in first chunk
        first_chunk_token_budget = (
            max_tokens - self._count_tokens(metadata_prefix)
            if metadata_prefix
            else max_tokens
        )

        line_index = 0
        overlap_text = ""

        while line_index < len(lines):
            start_line = line_index + 1
            chunk_lines = []
            current_chunk_text = overlap_text

            # Add metadata to first chunk only
            if len(chunks) == 0 and metadata_prefix:
                current_chunk_text = metadata_prefix + current_chunk_text
                token_budget = first_chunk_token_budget
            else:
                token_budget = max_tokens

            # Build chunk line by line until we hit token limit
            while line_index < len(lines):
                line_to_add = lines[line_index]
                potential_text = current_chunk_text + line_to_add

                if self._count_tokens(potential_text) > token_budget and chunk_lines:
                    # We've hit the token limit and have at least one line
                    break

                chunk_lines.append(line_to_add)
                current_chunk_text = potential_text
                line_index += 1

            # If no lines fit, take at least one line (truncated if necessary)
            if not chunk_lines and line_index < len(lines):
                line_to_add = lines[line_index]
                potential_text = current_chunk_text + line_to_add

                if self._count_tokens(potential_text) > token_budget:
                    # Truncate the line to fit
                    truncated_line = self._trim_to_max_tokens(
                        current_chunk_text + line_to_add, token_budget
                    )
                    # Remove the prefix to get just the truncated line part
                    prefix_len = len(current_chunk_text)
                    if len(truncated_line) > prefix_len:
                        line_to_add = truncated_line[prefix_len:]
                    else:
                        line_to_add = ""

                chunk_lines.append(line_to_add)
                current_chunk_text = current_chunk_text + line_to_add
                line_index += 1

            if not chunk_lines:
                break

            # Calculate line numbers and character offsets
            chunk_start_line = start_line
            chunk_end_line = start_line + len(chunk_lines) - 1

            # Remove overlap text from the beginning for character offset calculation
            chunk_text_for_offset = "".join(chunk_lines)
            if overlap_text and current_chunk_text.startswith(overlap_text):
                char_start = len("".join(lines[: start_line - 1])) - len(
                    overlap_text.rstrip("\n")
                )
            else:
                char_start = len("".join(lines[: start_line - 1]))

            char_end = len("".join(lines[:chunk_end_line]))

            chunks.append(
                {
                    "text": current_chunk_text,
                    "start": char_start,
                    "end": char_end,
                    "start_line": chunk_start_line,
                    "end_line": chunk_end_line,
                    "token_count": self._count_tokens(current_chunk_text),
                }
            )

            # Prepare overlap for next chunk
            if overlap_tokens > 0 and line_index < len(lines):
                overlap_text = self._get_overlap_text(
                    chunk_text_for_offset, overlap_tokens
                )
                if overlap_text:
                    overlap_text += "\n"
            else:
                overlap_text = ""

        return chunks

    def _trim_to_max_tokens(self, text: str, max_tokens: int) -> str:
        """Trim text to fit within max_tokens."""
        if self._count_tokens(text) <= max_tokens:
            return text

        # Binary search to find the right length
        left, right = 0, len(text)
        best_text = ""

        while left <= right:
            mid = (left + right) // 2
            candidate = text[:mid]

            if self._count_tokens(candidate) <= max_tokens:
                best_text = candidate
                left = mid + 1
            else:
                right = mid - 1

        return best_text

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Get the last overlap_tokens worth of text for overlap."""
        if overlap_tokens <= 0:
            return ""

        # Start from the end and work backwards
        words = text.split()
        if not words:
            return ""

        # Try different word counts to get close to overlap_tokens
        for word_count in range(min(len(words), overlap_tokens * 2), 0, -1):
            candidate = " ".join(words[-word_count:])
            if self._count_tokens(candidate) <= overlap_tokens:
                return candidate

        return ""

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
            logger.error(
                f"Failed to generate batch embeddings, falling back to individual: {e}"
            )
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

    # Attributes for type checkers
    embedding_model: EmbeddingModel
    text_chunker: TextChunker
    db_path: Path
    connection: Optional[sqlite3.Connection]

    _instance: Optional["VectorStore"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "VectorStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.debug("🔧 Creating new VectorStore singleton instance")
                    cls._instance = super(VectorStore, cls).__new__(cls)
        return cls._instance  # type: ignore[return-value]

    def __init__(self, db_path: Optional[str] = None, model_path: Optional[str] = None):
        # Initialize only once due to singleton pattern
        if getattr(self, "initialized", False):
            return

        # Initialize database
        if db_path is None:
            resolved_db_path: str = str(config.sqlite.embeddings_db)
        else:
            resolved_db_path = db_path
        self.db_path = Path(resolved_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: Optional[sqlite3.Connection] = None

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
        self.initialized = True
        logger.debug("✅ VectorStore initialized")

    def _connect(self) -> None:
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

    def _setup_vector_tables(self) -> None:
        """Setup vector tables using sqlite-vec."""
        try:
            assert self.connection is not None
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
        self,
        text: str,
        max_tokens: int = 240,
        overlap_tokens: int = 30,
        metadata: str = "",
    ) -> List[Dict[str, Any]]:
        """Split text into chunks with line tracking."""
        return self.text_chunker.chunk_text(text, max_tokens, overlap_tokens, metadata)

    def get_chunked_embeddings(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """Get embeddings for text chunks."""
        return self.text_chunker.get_chunked_embeddings(
            text, max_tokens, overlap_tokens
        )

    def get_chunked_embeddings_with_metadata(
        self,
        text: str,
        metadata: str = "",
        max_tokens: int = 240,
        overlap_tokens: int = 30,
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """Get embeddings for text chunks with metadata added to first chunk only."""
        chunks = self.chunk_text(text, max_tokens, overlap_tokens, metadata)

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
            logger.error(
                f"Failed to generate batch embeddings, falling back to individual: {e}"
            )
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
            embedding_array = (
                embedding.astype(np.float32)
                if isinstance(embedding, np.ndarray)
                else np.array(embedding, dtype=np.float32)
            )

            if len(embedding_array.shape) != 1 or embedding_array.shape[0] != 384:
                raise ValueError(
                    f"Expected 384-dimensional vector, got shape {embedding_array.shape}"
                )

            # Store in vector database using sqlite-vec
            assert self.connection is not None
            cursor = self.connection.execute(
                """INSERT INTO embeddings (node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, embedding)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(node_id),  # Convert to string for sqlite-vec
                    project_id,
                    chunk_index,
                    chunk_start_line,
                    chunk_end_line,
                    embedding_array,
                ),
            )

            embedding_id = cursor.lastrowid
            self.connection.commit()
            if embedding_id is None:
                raise RuntimeError("Failed to retrieve lastrowid after insert")
            return int(embedding_id)

        except Exception as e:
            logger.error(f"Failed to store embedding for node {node_id}: {e}")
            raise

    def store_embeddings_batch(
        self, embedding_data_list: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Store multiple embeddings in a single database transaction for massive performance improvement.

        Args:
            embedding_data_list: List of dictionaries containing embedding data

        Returns:
            List of embedding IDs
        """
        if not embedding_data_list:
            return []

        embedding_ids: List[int] = []

        cursor = None
        try:
            # Store embeddings in vector database using sqlite-vec
            assert self.connection is not None
            cursor = self.connection.cursor()

            # Begin transaction for batch insert
            cursor.execute("BEGIN TRANSACTION")

            for data in embedding_data_list:
                # Validate and convert embedding
                embedding = data["embedding"]
                embedding_array = (
                    embedding.astype(np.float32)
                    if isinstance(embedding, np.ndarray)
                    else np.array(embedding, dtype=np.float32)
                )

                if len(embedding_array.shape) != 1 or embedding_array.shape[0] != 384:
                    raise ValueError(
                        f"Expected 384-dimensional vector, got shape {embedding_array.shape}"
                    )

                cursor.execute(
                    """INSERT INTO embeddings (node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, embedding)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(data["node_id"]),  # Convert to string for sqlite-vec
                        data["project_id"],
                        data["chunk_index"],
                        data["chunk_start_line"],
                        data["chunk_end_line"],
                        embedding_array,
                    ),
                )
                rowid = cursor.lastrowid
                if rowid is None:
                    raise RuntimeError("Failed to retrieve lastrowid for batch insert")
                embedding_ids.append(int(rowid))

            # Commit all inserts at once
            cursor.execute("COMMIT")
            logger.debug(
                f"Batch stored {len(embedding_ids)} embeddings in single transaction"
            )

            return embedding_ids

        except Exception as e:
            try:
                if cursor is not None:
                    cursor.execute("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Failed to batch store embeddings: {e}")
            raise

    def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 30,
        threshold: float = 0.0,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        try:
            query_vector = (
                query_embedding.astype(np.float32)
                if isinstance(query_embedding, np.ndarray)
                else np.array(query_embedding, dtype=np.float32)
            )

            if len(query_vector.shape) != 1 or query_vector.shape[0] != 384:
                raise ValueError(
                    f"Expected 384-dimensional query vector, got shape {query_vector.shape}"
                )

            # Build query with optional project filtering
            if project_id is not None:
                query_sql = """
                    SELECT rowid, node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, distance
                    FROM embeddings
                    WHERE project_id = ? AND embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """
                query_params: Tuple[Any, ...] = (project_id, query_vector, limit)
            else:
                query_sql = """
                    SELECT rowid, node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, distance
                    FROM embeddings
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """
                query_params = (query_vector, limit)

            assert self.connection is not None
            cursor = self.connection.execute(query_sql, query_params)
            results: List[Dict[str, Any]] = []

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
                similarity = 1.0 / (1.0 + float(distance))

                if similarity >= threshold:
                    results.append(
                        {
                            "embedding_id": int(embedding_id),
                            "node_id": str(node_id),
                            "project_id": int(proj_id),
                            "chunk_index": int(chunk_index),
                            "chunk_start_line": int(chunk_start_line),
                            "chunk_end_line": int(chunk_end_line),
                            "similarity": float(similarity),
                            "distance": float(distance),
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
        threshold: float = 0.0,
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
            stats: Dict[str, Any] = {}

            assert self.connection is not None
            # Total embeddings
            cursor = self.connection.execute("SELECT COUNT(*) FROM embeddings")
            stats["total_embeddings"] = int(cursor.fetchone()[0])

            # Unique nodes
            cursor = self.connection.execute(
                "SELECT COUNT(DISTINCT node_id) FROM embeddings"
            )
            stats["unique_nodes"] = int(cursor.fetchone()[0])

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

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Vector store connection closed")


def get_vector_store() -> VectorStore:
    """Get the singleton vector store instance."""
    return VectorStore()
