"""
Node embedding processor for generating chunked embeddings for code nodes.
"""

from typing import List, Dict, Any, Optional

from loguru import logger
from tqdm import tqdm

from ..models.schema import CodeNode
from ..embeddings import get_embedding_processor, get_vector_db
from ..embeddings.vector_db import VectorDatabase


class NodeEmbeddingProcessor:
    """Processes code nodes and generates chunked embeddings for maximum information retention."""

    def __init__(self, max_tokens: int = 150, overlap_tokens: int = 25):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.embedding_processor = None
        self.vector_db: Optional[VectorDatabase] = None
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            try:
                self.embedding_processor = get_embedding_processor()
                self.vector_db = get_vector_db()
                self._initialized = True
                print("🧠 Node embedding processor initialized with chunking support")
            except Exception as e:
                logger.error(f"Failed to initialize embedding processor: {e}")
                raise

    def _generate_node_embedding_text(self, node: CodeNode) -> str:
        """Generate embedding text for a file node with optimized content for semantic search."""
        text_parts = []

        # Add file context information
        if hasattr(node, "path") and node.path:
            # Extract file name and directory context
            import os

            file_name = os.path.basename(node.path)
            dir_name = os.path.basename(os.path.dirname(node.path))
            text_parts.append(f"File: {file_name}")
            text_parts.append(f"Directory: {dir_name}")
            text_parts.append(f"Path: {node.path}")

        # Add file metadata if available
        if node.metadata:
            language = node.metadata.get("language", "")
            if language:
                text_parts.append(f"Language: {language}")

            file_size = node.metadata.get("size", 0)
            if file_size:
                text_parts.append(f"Size: {file_size} bytes")

        # Add the actual file content which is most important for semantic search
        if node.content:
            text_parts.append(f"Code:\n{node.content}")

        # Add line information if available
        if node.lines:
            if isinstance(node.lines, list) and len(node.lines) > 0:
                if len(node.lines) == 1:
                    text_parts.append(f"Line: {node.lines[0]}")
                else:
                    text_parts.append(f"Lines: {node.lines[0]}-{node.lines[-1]}")

        return "\n".join(text_parts)

    def _store_node_embeddings(
        self, node_id: int, project_id: int, embedding_text: str, node: CodeNode
    ) -> List[int]:
        """Generate and store chunked embeddings for a node with line information."""
        if not embedding_text.strip():
            logger.debug(f"No content to embed for node {node_id}")
            return []

        try:
            assert (
                self.embedding_processor is not None
            ), "Embedding processor not initialized"
            assert self.vector_db is not None, "Vector database not initialized"

            # Use the raw file content for chunking and line number calculation
            # This ensures chunk line numbers are relative to the actual file, not metadata
            file_content = node.content or ""
            if not file_content.strip():
                logger.debug(f"No file content to embed for node {node_id}")
                return []

            # Generate embeddings using the full embedding_text (with metadata) for better semantic search
            embeddings_with_metadata = self.embedding_processor.get_chunked_embeddings(
                embedding_text,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            if not embeddings_with_metadata:
                logger.warning(f"No embeddings generated for node {node_id}")
                return []

            # Also chunk the file content directly to get accurate line numbers
            file_chunks = self.embedding_processor.chunk_text(
                file_content,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            embedding_ids = []

            for chunk_index, (embedding, chunk_metadata) in enumerate(
                embeddings_with_metadata
            ):
                try:
                    # Use the file chunk for line number calculation
                    if chunk_index < len(file_chunks):
                        file_chunk = file_chunks[chunk_index]
                        chunk_text = file_chunk["text"]
                        chunk_start_line = file_chunk["start_line"]
                        chunk_end_line = file_chunk["end_line"]
                    else:
                        # Fallback if chunk counts don't match
                        chunk_text = chunk_metadata.get("text", "")
                        char_start = chunk_metadata.get("start", 0)

                        # Calculate line numbers based on the raw file content
                        text_up_to_start = file_content[:char_start]
                        lines_before_chunk = text_up_to_start.count("\n")
                        chunk_lines = chunk_text.split("\n")
                        chunk_line_count = len(chunk_lines)
                        chunk_start_line = lines_before_chunk + 1
                        chunk_end_line = chunk_start_line + chunk_line_count - 1

                    # Ensure we don't exceed the file's actual length
                    total_file_lines = len(file_content.split("\n"))
                    chunk_end_line = min(chunk_end_line, total_file_lines)
                    chunk_start_line = min(chunk_start_line, total_file_lines)

                    logger.debug(
                        f"Node {node_id} chunk {chunk_index}: lines={chunk_start_line}-{chunk_end_line}, file_total_lines={total_file_lines}"
                    )

                    embedding_id = self.vector_db.store_embedding(
                        node_id=node_id,
                        project_id=project_id,
                        chunk_index=chunk_index,
                        embedding=embedding,
                        chunk_start_line=chunk_start_line,
                        chunk_end_line=chunk_end_line,
                    )

                    embedding_ids.append(embedding_id)

                    logger.debug(
                        f"Stored embedding {embedding_id} for node {node_id} chunk {chunk_index} "
                        f"(lines {chunk_start_line}-{chunk_end_line})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to store embedding for node {node_id} chunk {chunk_index}: {e}"
                    )
                    continue

            return embedding_ids

        except Exception as e:
            logger.error(
                f"Failed to generate embeddings for node {node_id} in project {project_id}: {e}"
            )
            return []

    def process_node_with_embeddings(
        self, node: CodeNode, project_id: int, project_name: str
    ) -> CodeNode:
        """Process a single node and generate chunked embeddings."""
        if not self._initialized:
            self._initialize()

        # Only generate embeddings for file type nodes
        if node.type.lower() != "file":
            logger.debug(
                f"Skipping embeddings for node {node.id} ({node.type}) - only file nodes are embedded"
            )
            return node

        # Generate embeddings for ALL file nodes
        logger.debug(
            f"Processing embeddings for file node {node.id} - generating chunked embeddings"
        )

        try:
            embedding_text = self._generate_node_embedding_text(node)

            embedding_ids = self._store_node_embeddings(
                node.id, project_id, embedding_text, node
            )

            logger.debug(
                f"Processed file node {node.id} with {len(embedding_ids)} embeddings"
            )
            return node

        except Exception as e:
            logger.error(f"Failed to process file node {node.id} with embeddings: {e}")
            return node

    def process_nodes_with_embeddings(
        self,
        nodes: List[CodeNode],
        project_id: int,
        project_name: str,
        batch_size: int = 200,
    ) -> List[CodeNode]:
        """Process multiple nodes with embeddings in batches."""
        if not self._initialized:
            self._initialize()

        # Filter to only file nodes for embedding processing
        file_nodes = [node for node in nodes if node.type.lower() == "file"]
        non_file_nodes = [node for node in nodes if node.type.lower() != "file"]

        logger.info(f"Processing {len(nodes)} total nodes:")
        logger.info(f"  - {len(file_nodes)} file nodes (will be embedded)")
        logger.info(
            f"  - {len(non_file_nodes)} non-file nodes (skipped for embeddings)"
        )

        processed_nodes = []
        total_embeddings = 0
        total_chunks = 0

        # Process file nodes with embeddings
        with tqdm(
            total=len(file_nodes), desc="Embedding file nodes", unit="file"
        ) as pbar:
            for i in range(0, len(file_nodes), batch_size):
                batch_nodes = file_nodes[i : i + batch_size]
                for node in batch_nodes:
                    processed_node = self.process_node_with_embeddings(
                        node, project_id, project_name
                    )
                    processed_nodes.append(processed_node)
                    total_embeddings += 1
                    total_chunks += 1
                    pbar.update(1)

        # Add non-file nodes without processing (they don't need embeddings)
        processed_nodes.extend(non_file_nodes)

        print(f"✅ Processed {len(processed_nodes)} total nodes:")
        print(f"   📁 {len(file_nodes)} file nodes processed with embeddings")
        print(
            f"   📄 {len(non_file_nodes)} non-file nodes skipped (no embeddings needed)"
        )
        print(f"   🧠 Embeddings stored in vector DB for semantic search")

        return processed_nodes

    def search_similar_nodes(
        self, query_text: str, limit: int = 20, threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """Search for nodes similar to query text using chunked embeddings."""
        if not self._initialized:
            self._initialize()

        try:
            assert (
                self.embedding_processor is not None
            ), "Embedding processor not initialized"
            assert self.vector_db is not None, "Vector database not initialized"

            query_embedding = self.embedding_processor.get_embedding(query_text)

            chunk_results = self.vector_db.search_similar(
                query_embedding=query_embedding,
                limit=limit * 3,  # Get more chunks to ensure diverse nodes
                threshold=threshold,
            )

            node_results = {}

            for result in chunk_results:
                node_id = result["node_id"]

                if (
                    node_id not in node_results
                    or result["similarity"] > node_results[node_id]["similarity"]
                ):
                    node_results[node_id] = result

            final_results = sorted(
                node_results.values(), key=lambda x: x["similarity"], reverse=True
            )[:limit]

            logger.info(
                f"Found {len(final_results)} similar nodes for query: {query_text}"
            )
            return final_results

        except Exception as e:
            logger.error(f"Failed to search similar nodes: {e}")
            return []

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Return current embedding statistics."""
        if not self._initialized:
            self._initialize()

        try:
            assert self.vector_db is not None, "Vector database not initialized"
            stats = self.vector_db.get_stats()

            stats.update(
                {
                    "max_tokens_per_chunk": self.max_tokens,
                    "overlap_tokens": self.overlap_tokens,
                    "chunking_enabled": True,
                }
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {
                "total_embeddings": 0,
                "unique_nodes": 0,
                "average_chunks_per_node": 0,
                "max_tokens_per_chunk": self.max_tokens,
                "overlap_tokens": self.overlap_tokens,
                "chunking_enabled": True,
            }


# Global instance
_node_embedding_processor = None


def get_node_embedding_processor(
    max_tokens: int = 150, overlap_tokens: int = 25
) -> NodeEmbeddingProcessor:
    """Return singleton instance of NodeEmbeddingProcessor."""
    global _node_embedding_processor
    if _node_embedding_processor is None:
        _node_embedding_processor = NodeEmbeddingProcessor(max_tokens, overlap_tokens)
    return _node_embedding_processor
