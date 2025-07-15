"""
Vector database implementation using sqlite-vec for fast similarity search.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
import sqlite_vec
from loguru import logger
from .simple_processor import get_embedding_processor
from graph.sqlite_client import SQLiteConnection
from config import config


class VectorDatabase:
    """Manages vector database with sqlite-vec."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.sqlite.embeddings_db
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._connect()

    def _connect(self):
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.enable_load_extension(True)
            sqlite_vec.load(self.connection)
            self._setup_vector_tables()
            logger.debug(f"Connected to vector database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to vector database: {e}")
            raise

    def _setup_vector_tables(self):
        try:
            # First, check if we need to migrate the existing table
            cursor = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Check if the table has the new columns
                cursor = self.connection.execute("PRAGMA table_info(embeddings)")
                columns = [row[1] for row in cursor.fetchall()]

                if "chunk_start_line" not in columns:
                    # Need to recreate the table with new schema
                    logger.info(
                        "Migrating embeddings table to include chunk line information"
                    )
                    self.connection.execute("DROP TABLE IF EXISTS embeddings")
                    table_exists = False

            if not table_exists:
                self.connection.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                        embedding_id INTEGER PRIMARY KEY,
                        node_id INTEGER,
                        project_id INTEGER,
                        chunk_index INTEGER,
                        chunk_start_line INTEGER,
                        chunk_end_line INTEGER,
                        embedding FLOAT[384]
                    )
                """
                )
                logger.debug(
                    "Created sqlite-vec virtual table with chunk line information support"
                )

            self.connection.commit()

        except Exception as e:
            logger.error(f"Failed to setup vector tables: {e}")
            raise

    def store_embedding(
        self,
        node_id: int,
        project_id: int,
        chunk_index: int,
        embedding: np.ndarray,
        chunk_start_line: int = None,
        chunk_end_line: int = None,
    ) -> int:
        """
        Store an embedding vector for a node chunk with line information.

        Args:
            node_id: The node ID
            project_id: The project ID this node belongs to
            chunk_index: Index of the chunk within the node
            embedding: The embedding vector (384 dimensions)
            chunk_start_line: Starting line number of the chunk
            chunk_end_line: Ending line number of the chunk

        Returns:
            The embedding ID
        """
        try:
            # Ensure embedding is the right shape and type
            if isinstance(embedding, np.ndarray):
                embedding_array = embedding.astype(np.float32)
            else:
                embedding_array = np.array(embedding, dtype=np.float32)

            if len(embedding_array.shape) != 1 or embedding_array.shape[0] != 384:
                raise ValueError(
                    f"Expected 384-dimensional vector, got shape {embedding_array.shape}"
                )

            # Insert into sqlite-vec virtual table (numpy array implements Buffer protocol)
            cursor = self.connection.execute(
                """
                INSERT INTO embeddings (node_id, project_id, chunk_index, chunk_start_line, chunk_end_line, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
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
            logger.error(
                f"Failed to store embedding for node {node_id} project {project_id} chunk {chunk_index}: {e}"
            )
            raise

    def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 30,
        threshold: float = 0.20,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings using sqlite-vec, optionally filtered by project."""
        try:
            if isinstance(query_embedding, np.ndarray):
                query_vector = query_embedding.astype(np.float32)
            else:
                query_vector = np.array(query_embedding, dtype=np.float32)

            if project_id is not None:
                query_sql = """
                    SELECT
                        embedding_id,
                        node_id,
                        project_id,
                        chunk_index,
                        chunk_start_line,
                        chunk_end_line,
                        distance
                    FROM embeddings
                    WHERE project_id = ? AND embedding MATCH ? 
                    ORDER BY distance
                    LIMIT ?
                """
                query_params = (project_id, query_vector, limit)
            else:
                query_sql = """
                    SELECT
                        embedding_id,
                        node_id,
                        project_id,
                        chunk_index,
                        chunk_start_line,
                        chunk_end_line,
                        distance
                    FROM embeddings
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """
                query_params = (query_vector, limit)

            cursor = self.connection.execute(query_sql, query_params)

            results = []
            for (
                embedding_id,
                node_id,
                proj_id,
                chunk_index,
                chunk_start_line,
                chunk_end_line,
                distance,
            ) in cursor.fetchall():

                # Convert distance to similarity (assuming L2 distance by default)
                # For L2 distance, smaller distance = higher similarity
                # We'll normalize this to 0-1 range where 1 = perfect match
                similarity = 1.0 / (1.0 + distance)

                # Only include results that meet the threshold
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
            logger.error(f"sqlite-vec similarity search failed: {e}")
            return []

    def search_similar_chunks(
        self,
        query_text: str,
        limit: int = 30,
        threshold: float = 0.2,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using text query, optionally filtered by project."""
        try:

            # Initialize the processor using the global getter to respect config path
            processor = get_embedding_processor()

            # Generate embedding for the query text
            query_embedding = processor.get_embedding(query_text)

            # Use the existing search_similar method with project filtering
            return self.search_similar(query_embedding, limit, threshold, project_id)

        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            return []

    def search_chunks_with_code(
        self,
        query_text: str,
        limit: int = 30,
        threshold: float = 0.2,
        max_display_lines: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks and return them with their specific code content.

        Args:
            query_text: The search query
            limit: Maximum number of chunks to return
            threshold: Similarity threshold
            max_display_lines: Maximum lines to display per chunk (None = no limit, show full chunks)

        Returns:
            List of chunks with their code content and line information
        """
        try:
            # Get similar chunks with expanded search
            chunk_results = self.search_similar_chunks(query_text, limit, threshold)

            if not chunk_results:
                return []


            db_connection = SQLiteConnection()
            enriched_chunks = []

            for chunk in chunk_results:
                try:
                    # Get node details
                    cursor = db_connection.connection.cursor()
                    cursor.execute(
                        """
                        SELECT n.node_id, n.node_type, n.name, n.lines, n.code_snippet,
                               fh.file_path, p.name as project_name, p.language
                        FROM nodes n
                        LEFT JOIN file_hashes fh ON n.file_hash_id = fh.id
                        LEFT JOIN projects p ON n.project_id = p.id
                        WHERE n.node_id = ? AND n.project_id = ?
                        """,
                        (chunk["node_id"], chunk["project_id"]),
                    )

                    node_row = cursor.fetchone()
                    if not node_row:
                        continue

                    # Extract specific lines from the code if we have line information
                    code_snippet = node_row[4] or ""
                    chunk_start_line = chunk.get("chunk_start_line")
                    chunk_end_line = chunk.get("chunk_end_line")

                    chunk_code = ""
                    if code_snippet:
                        if chunk_start_line and chunk_end_line:
                            # Parse node lines to get the node's starting line
                            node_lines = node_row[3]
                            if node_lines:
                                import json

                                try:
                                    lines_data = json.loads(node_lines)
                                    if (
                                        isinstance(lines_data, list)
                                        and len(lines_data) >= 1
                                    ):
                                        node_start_line = lines_data[0]

                                        # Calculate relative line positions within the code
                                        relative_start = max(
                                            0, chunk_start_line - node_start_line
                                        )
                                        relative_end = (
                                            chunk_end_line - node_start_line + 1
                                        )

                                        code_lines = code_snippet.split("\n")

                                        # Debug logging
                                        logger.debug(f"Chunk extraction debug:")
                                        logger.debug(
                                            f"  chunk_start_line: {chunk_start_line}, chunk_end_line: {chunk_end_line}"
                                        )
                                        logger.debug(
                                            f"  node_start_line: {node_start_line}"
                                        )
                                        logger.debug(
                                            f"  relative_start: {relative_start}, relative_end: {relative_end}"
                                        )
                                        logger.debug(
                                            f"  code_lines length: {len(code_lines)}"
                                        )

                                        if (
                                            relative_start < len(code_lines)
                                            and relative_start >= 0
                                            and relative_end > relative_start
                                            and relative_end <= len(code_lines)
                                        ):
                                            # Extract only the lines that belong to this chunk
                                            chunk_lines = code_lines[
                                                relative_start:relative_end
                                            ]
                                            chunk_code = "\n".join(chunk_lines)

                                            # Debug logging
                                            logger.debug(
                                                f"  Extracted {len(chunk_lines)} lines: {relative_start} to {relative_end-1}"
                                            )

                                            # Limit chunk size to reasonable amount
                                            if (
                                                max_display_lines
                                                and len(chunk_lines) > max_display_lines
                                            ):
                                                chunk_lines = chunk_lines[
                                                    :max_display_lines
                                                ]
                                                chunk_code = (
                                                    "\n".join(chunk_lines)
                                                    + f"\n... (chunk truncated at {max_display_lines} lines)"
                                                )
                                                # Update chunk end line to reflect actual displayed content
                                                chunk_end_line = (
                                                    chunk_start_line
                                                    + len(chunk_lines)
                                                    - 1
                                                )
                                        else:
                                            # If relative calculation fails, use full code but limit it
                                            logger.debug(
                                                f"  Relative calculation failed, using full code"
                                            )
                                            code_lines = code_snippet.split("\n")
                                            if (
                                                max_display_lines
                                                and len(code_lines) > max_display_lines
                                            ):
                                                chunk_code = (
                                                    "\n".join(
                                                        code_lines[:max_display_lines]
                                                    )
                                                    + f"\n... (truncated at {max_display_lines} lines)"
                                                )
                                                # Update chunk end line to reflect actual displayed content
                                                chunk_end_line = (
                                                    chunk_start_line
                                                    + max_display_lines
                                                    - 1
                                                )
                                            else:
                                                chunk_code = code_snippet
                                                # Keep the original chunk line range, don't recalculate
                                                # chunk_end_line remains as stored
                                except (json.JSONDecodeError, ValueError):
                                    # Fallback to full code if parsing fails
                                    logger.debug(
                                        f"  JSON parsing failed, using full code"
                                    )
                                    code_lines = code_snippet.split("\n")
                                    if (
                                        max_display_lines
                                        and len(code_lines) > max_display_lines
                                    ):
                                        chunk_code = (
                                            "\n".join(code_lines[:max_display_lines])
                                            + f"\n... (truncated at {max_display_lines} lines)"
                                        )
                                        # Update chunk end line to reflect actual displayed content
                                        chunk_end_line = (
                                            chunk_start_line + max_display_lines - 1
                                        )
                                    else:
                                        chunk_code = code_snippet
                                        # Keep the original chunk line range, don't recalculate
                                        # chunk_end_line remains as stored
                            else:
                                # No node lines info, use full code
                                code_lines = code_snippet.split("\n")
                                if (
                                    max_display_lines
                                    and len(code_lines) > max_display_lines
                                ):
                                    chunk_code = (
                                        "\n".join(code_lines[:max_display_lines])
                                        + f"\n... (truncated at {max_display_lines} lines)"
                                    )
                                    # Update chunk end line to reflect actual displayed content
                                    chunk_end_line = (
                                        chunk_start_line + max_display_lines - 1
                                    )
                                else:
                                    chunk_code = code_snippet
                                    # Keep the original chunk line range, don't recalculate
                                    # chunk_end_line remains as stored
                        else:
                            # No chunk line info, use full code
                            code_lines = code_snippet.split("\n")
                            if (
                                max_display_lines
                                and len(code_lines) > max_display_lines
                            ):
                                chunk_code = (
                                    "\n".join(code_lines[:max_display_lines])
                                    + f"\n... (truncated at {max_display_lines} lines)"
                                )
                                # Set reasonable line range for display
                                chunk_start_line = 1
                                chunk_end_line = max_display_lines
                            else:
                                chunk_code = code_snippet
                                # Set line range to match actual content
                                chunk_start_line = 1
                                chunk_end_line = len(code_lines)
                    else:
                        # No code snippet available
                        chunk_code = ""
                        chunk_start_line = None
                        chunk_end_line = None

                    enriched_chunks.append(
                        {
                            "node_id": chunk["node_id"],
                            "project_id": chunk["project_id"],
                            "chunk_index": chunk["chunk_index"],
                            "similarity": chunk["similarity"],
                            "chunk_start_line": chunk_start_line,
                            "chunk_end_line": chunk_end_line,
                            "node_type": node_row[1],
                            "node_name": node_row[2],
                            "file_path": node_row[5] or "unknown",
                            "project_name": node_row[6] or "unknown",
                            "language": node_row[7] or "unknown",
                            "chunk_code": chunk_code,
                        }
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to enrich chunk {chunk.get('embedding_id', 'unknown')}: {e}"
                    )
                    continue

            return enriched_chunks

        except Exception as e:
            logger.error(f"Failed to search chunks with code: {e}")
            return []

    def clear_all_embeddings(self):
        """Clear all embeddings from the database."""
        try:
            cursor = self.connection.execute("DELETE FROM embeddings")
            deleted_count = cursor.rowcount
            self.connection.commit()
            logger.info(f"Cleared {deleted_count} embeddings from the database")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear embeddings: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
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

            # Storage method
            stats["storage_method"] = "sqlite-vec"
            stats["vector_dimension"] = 384

            # Database size
            stats["database_size_mb"] = round(
                self.db_path.stat().st_size / (1024 * 1024), 2
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
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
            logger.info("Vector database connection closed")


# Global instance
_vector_db = None


def get_vector_db() -> VectorDatabase:
    """Get the global vector database instance."""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase(config.sqlite.embeddings_db)
    return _vector_db
