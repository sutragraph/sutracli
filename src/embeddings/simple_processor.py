"""
Simple embedding processor using ONNX Runtime for all-MiniLM-L12-v2 model.
Supports both single embeddings and text chunking for maximum information retention.
"""

import json
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Any, Tuple
from tokenizers import Tokenizer

from loguru import logger


class SimpleEmbeddingProcessor:
    """Lightweight embedding processor using ONNX Runtime."""

    def __init__(self, model_path: str = "models/all-MiniLM-L12-v2"):
        self.model_path = Path(model_path)
        self.session = None
        self.tokenizer = None
        self.model_info = None
        self._load_model()

    def _load_model(self):
        """Load the ONNX model and tokenizer."""
        try:
            model_info_path = self.model_path / "model_info.json"
            if model_info_path.exists():
                with open(model_info_path, "r") as f:
                    self.model_info = json.load(f)

            model_file = self.model_path / "model.onnx"
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")

            providers = ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(model_file), providers=providers)

            # Store expected input names
            self.input_names = [input.name for input in self.session.get_inputs()]
            logger.debug(f"Model expects inputs: {self.input_names}")

            tokenizer_file = self.model_path / "tokenizer.json"
            if tokenizer_file.exists():
                self.tokenizer = Tokenizer.from_file(str(tokenizer_file))
            else:
                logger.warning("Tokenizer file not found, using basic tokenization")

            logger.debug(f"Loaded model from {self.model_path}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _tokenize(self, text: str, max_length: int = 256) -> Dict[str, np.ndarray]:
        """Tokenize text for the model."""
        if self.tokenizer:
            # Use the proper tokenizer
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
            attention_mask = [1] * len(tokens)

            # Pad to max_length
            while len(tokens) < max_length:
                tokens.append(0)
                attention_mask.append(0)

        # Create base inputs
        inputs = {
            "input_ids": np.array([tokens], dtype=np.int64),
            "attention_mask": np.array([attention_mask], dtype=np.int64),
        }

        # Add token_type_ids only if the model expects it
        if "token_type_ids" in self.input_names:
            token_type_ids = [0] * len(tokens)
            inputs["token_type_ids"] = np.array([token_type_ids], dtype=np.int64)

        return inputs

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text."""
        if self.session is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")

        try:
            # Tokenize
            inputs = self._tokenize(text)

            # Run inference
            outputs = self.session.run(None, inputs)

            # Extract embeddings (usually the first output)
            embeddings = np.array(outputs[0], dtype=np.float32)

            # Mean pooling (common for sentence transformers)
            attention_mask = inputs["attention_mask"].astype(np.float32)

            # Apply attention mask and mean pooling
            masked_embeddings = embeddings * np.expand_dims(attention_mask, -1)
            summed = np.sum(masked_embeddings, axis=1)
            counts = np.sum(attention_mask, axis=1, keepdims=True)
            counts = np.maximum(counts, 1e-8)  # Avoid division by zero
            mean_pooled = summed / counts

            # Get the first (and only) sentence embedding
            embedding = mean_pooled[0]

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise

    def chunk_text(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks based on token limits with precise line tracking.
        Uses efficient batch tokenization for better performance.

        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks

        Returns:
            List of chunk dictionaries with text, start, end, start_line, end_line
        """
        if not text or not text.strip():
            return []

        lines = text.splitlines(keepends=True)
        if not lines:
            return []

        # Use efficient batch tokenization
        return self._chunk_text_batch_efficient(text, lines, max_tokens, overlap_tokens)

    def _chunk_text_batch_efficient(
        self, text: str, lines: List[str], max_tokens: int, overlap_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        Efficient batch-based chunking that tokenizes text in larger batches.
        Much faster than line-by-line tokenization while maintaining accuracy.
        """
        chunks = []
        current_chunk_lines = []
        current_chunk_tokens = 0
        current_start_line = 1
        current_char_start = 0

        # Process lines with flexible window size
        initial_window_size = 25  # Start with 25 lines
        extension_size = 5  # Add 5 more lines if needed
        i = 0

        while i < len(lines):
            # Start with initial window size
            window_size = initial_window_size
            batch_end = min(i + window_size, len(lines))
            batch_lines = lines[i:batch_end]
            batch_text = "".join(batch_lines)

            # Tokenize the batch
            if self.tokenizer:
                batch_encoding = self.tokenizer.encode(batch_text)
                batch_tokens = len(batch_encoding.ids)
            else:
                # Fallback: rough estimate
                batch_tokens = len(batch_text.split()) + 2

            # If we're under the token limit and there are more lines, try to add more
            while (
                batch_tokens < max_tokens
                and batch_end < len(lines)
                and window_size < initial_window_size + extension_size
            ):

                # Try adding 5 more lines
                next_batch_end = min(batch_end + extension_size, len(lines))
                additional_lines = lines[batch_end:next_batch_end]
                additional_text = "".join(additional_lines)

                # Check if adding these lines would exceed the token limit
                if self.tokenizer:
                    additional_encoding = self.tokenizer.encode(additional_text)
                    additional_tokens = len(additional_encoding.ids)
                else:
                    additional_tokens = len(additional_text.split()) + 2

                if batch_tokens + additional_tokens <= max_tokens:
                    # Add the additional lines
                    batch_lines.extend(additional_lines)
                    batch_text = "".join(batch_lines)
                    batch_tokens += additional_tokens
                    batch_end = next_batch_end
                    window_size += extension_size
                else:
                    break

            # Check if adding this batch would exceed the token limit
            if current_chunk_tokens + batch_tokens > max_tokens and current_chunk_lines:
                # Create a chunk from current lines
                chunk_text = "".join(current_chunk_lines)
                chunk_end_line = i
                chunk_char_end = current_char_start + len(chunk_text)

                # Validate chunk size
                if self.tokenizer:
                    chunk_encoding = self.tokenizer.encode(chunk_text)
                    actual_tokens = len(chunk_encoding.ids)
                else:
                    actual_tokens = len(chunk_text.split()) + 2

                # If chunk is too large, truncate it
                if actual_tokens > max_tokens:
                    logger.warning(
                        f"Chunk exceeded token limit ({actual_tokens} > {max_tokens}), truncating"
                    )
                    # Truncate the chunk text to fit within token limit
                    if self.tokenizer:
                        # Find the right truncation point
                        encoding = self.tokenizer.encode(chunk_text)
                        if len(encoding.ids) > max_tokens:
                            # Decode back to text with truncation
                            truncated_ids = encoding.ids[:max_tokens]
                            chunk_text = self.tokenizer.decode(truncated_ids)
                            # Recalculate end position
                            chunk_char_end = current_char_start + len(chunk_text)
                            actual_tokens = max_tokens

                chunks.append(
                    {
                        "text": chunk_text,
                        "start": current_char_start,
                        "end": chunk_char_end,
                        "start_line": current_start_line,
                        "end_line": chunk_end_line,
                        "token_count": actual_tokens,
                    }
                )

                # Start new chunk with overlap
                if overlap_tokens > 0 and current_chunk_tokens > overlap_tokens:
                    # Find where to start overlap by counting backwards
                    overlap_chars = 0
                    overlap_tokens_counted = 0
                    overlap_lines = []

                    for j in range(len(current_chunk_lines) - 1, -1, -1):
                        overlap_line = current_chunk_lines[j]
                        if self.tokenizer:
                            overlap_line_encoding = self.tokenizer.encode(overlap_line)
                            overlap_line_tokens = len(overlap_line_encoding.ids)
                        else:
                            overlap_line_tokens = len(overlap_line.split()) + 2

                        if (
                            overlap_tokens_counted + overlap_line_tokens
                            <= overlap_tokens
                        ):
                            overlap_lines.insert(0, overlap_line)
                            overlap_chars += len(overlap_line)
                            overlap_tokens_counted += overlap_line_tokens
                        else:
                            break

                    # Start new chunk with overlap
                    current_chunk_lines = overlap_lines
                    current_chunk_tokens = overlap_tokens_counted
                    current_start_line = chunk_end_line - len(overlap_lines) + 1
                    current_char_start = chunk_char_end - overlap_chars
                else:
                    # No overlap, start fresh
                    current_chunk_lines = []
                    current_chunk_tokens = 0
                    current_start_line = i + 1
                    current_char_start = sum(len(l) for l in lines[:i])

            # Add current batch to chunk
            current_chunk_lines.extend(batch_lines)
            current_chunk_tokens += batch_tokens
            i = batch_end

        # Add the last chunk if there are remaining lines
        if current_chunk_lines:
            chunk_text = "".join(current_chunk_lines)
            chunk_end_line = len(lines)
            chunk_char_end = current_char_start + len(chunk_text)

            # Validate final chunk size
            if self.tokenizer:
                chunk_encoding = self.tokenizer.encode(chunk_text)
                actual_tokens = len(chunk_encoding.ids)
            else:
                actual_tokens = len(chunk_text.split()) + 2

            # If chunk is too large, truncate it
            if actual_tokens > max_tokens:
                logger.warning(
                    f"Final chunk exceeded token limit ({actual_tokens} > {max_tokens}), truncating"
                )
                if self.tokenizer:
                    encoding = self.tokenizer.encode(chunk_text)
                    if len(encoding.ids) > max_tokens:
                        truncated_ids = encoding.ids[:max_tokens]
                        chunk_text = self.tokenizer.decode(truncated_ids)
                        chunk_char_end = current_char_start + len(chunk_text)
                        actual_tokens = max_tokens

            chunks.append(
                {
                    "text": chunk_text,
                    "start": current_char_start,
                    "end": chunk_char_end,
                    "start_line": current_start_line,
                    "end_line": chunk_end_line,
                    "token_count": actual_tokens,
                }
            )

        logger.debug(
            f"Split text into {len(chunks)} chunks with flexible window processing"
        )
        return chunks

    def get_chunked_embeddings(
        self, text: str, max_tokens: int = 240, overlap_tokens: int = 30
    ) -> List[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        Get embeddings for text chunks with metadata.

        Args:
            text: Text to process
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks

        Returns:
            List of tuples (embedding, chunk_metadata)
        """
        chunks = self.chunk_text(
            text, max_tokens=max_tokens, overlap_tokens=overlap_tokens
        )

        if not chunks:
            return []

        embeddings_with_metadata = []

        for chunk in chunks:
            try:
                embedding = self.get_embedding(chunk["text"])
                embeddings_with_metadata.append((embedding, chunk))
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk: {e}")
                continue

        return embeddings_with_metadata


# Global instance (lazy loading)
_embedding_processor = None


def get_embedding_processor() -> SimpleEmbeddingProcessor:
    """Get the global embedding processor instance."""
    global _embedding_processor
    if _embedding_processor is None:
        # Get model path from configuration
        try:
            from src.config.settings import get_config

            config = get_config()
            import os

            model_path = os.path.expanduser(config.embedding.model_path)
            _embedding_processor = SimpleEmbeddingProcessor(model_path)
        except Exception as e:
            # Fallback to default path if config fails
            import warnings

            warnings.warn(
                f"Failed to load model path from config: {e}. Using default path."
            )
            _embedding_processor = SimpleEmbeddingProcessor()
    return _embedding_processor
