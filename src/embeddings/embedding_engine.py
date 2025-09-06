"""
Code block embedding engine for generating strategic embeddings for FileData and its nested CodeBlocks.
Moved from processors/ to embeddings/ for better organization.
"""

from typing import List, Dict, Optional
from pathlib import Path

from loguru import logger
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)

from models.schema import CodeBlock, FileData
from embeddings.vector_store import get_vector_store
from config import config


class EmbeddingEngine:
    """
    Processes FileData and embeds its nested code blocks.

    Strategy:
    1. Embed the entire file for high-level context
    2. Embed all extracted code blocks (they were deemed important during extraction)
    3. Recursively embed nested blocks
    4. Provide fallback file embedding when block extraction fails
    """

    def __init__(self):
        """Initialize the embedding engine with chunking parameters."""
        self.max_tokens = config.embedding.max_tokens
        self.overlap_tokens = config.embedding.overlap_tokens
        self.vector_store = get_vector_store()

    def _should_embed_block(self, block: CodeBlock) -> bool:
        """
        Determine if a code block should be embedded.
        All extracted blocks are embedded since they were deemed important during extraction.

        Args:
            block: CodeBlock to evaluate

        Returns:
            True if block should be embedded, False otherwise
        """
        # Embed all blocks that have content
        return bool(block.content and block.content.strip())

    def _generate_file_embedding_text(self, file_data: FileData) -> str:
        """Generate embedding text for the entire file."""
        # Return only the file content - metadata will be added to first chunk only
        return file_data.content or ""

    def _generate_file_metadata(self, file_data: FileData) -> str:
        """Generate metadata text for the file (to be added to first chunk only)."""
        metadata_parts = []

        # Add file metadata
        if file_data.file_path:
            file_path = Path(file_data.file_path)
            metadata_parts.append(f"File: {file_path.name}")
            metadata_parts.append(f"Directory: {file_path.parent.name}")
            metadata_parts.append(f"Path: {file_data.file_path}")

        if file_data.language:
            metadata_parts.append(f"Language: {file_data.language}")

        return "\n".join(metadata_parts)

    def _generate_block_metadata_template(
        self, block: CodeBlock, file_data: FileData
    ) -> str:
        """Generate metadata template for a code block (without the code content)."""
        text_parts = []

        # Add file context
        if file_data.file_path:
            file_path = Path(file_data.file_path)
            text_parts.append(f"File: {file_path.name}")

        if file_data.language:
            text_parts.append(f"Language: {file_data.language}")

        # Add hierarchical context
        hierarchy_path = self._get_block_hierarchy_path(block, file_data)
        if hierarchy_path:
            text_parts.append(f"Context: {hierarchy_path}")

        # Add block metadata
        text_parts.append(f"Type: {block.type.value}")
        text_parts.append(f"Name: {block.name}")

        # Add line information
        if block.start_line == block.end_line:
            text_parts.append(f"Line: {block.start_line}")
        else:
            text_parts.append(f"Lines: {block.start_line}-{block.end_line}")

        return "\n".join(text_parts)

    def _store_embeddings_batch_for_blocks(
        self, blocks: List[CodeBlock], file_data: FileData, project_id: int
    ) -> Dict[str, int]:
        """
        Generate and store embeddings for multiple blocks in a single batch.
        This provides massive performance improvement by processing all blocks together.

        Args:
            blocks: List of code blocks to embed
            file_data: File data for context
            project_id: Project ID

        Returns:
            Dictionary with embedding statistics
        """
        if not blocks:
            return {"total_embeddings": 0}

        logger.debug(f"Batch processing {len(blocks)} blocks for {file_data.file_path}")

        # Collect all text chunks from all blocks (without generating embeddings yet)
        all_chunk_texts = []
        block_chunk_mapping = []  # Track which chunks belong to which block

        for block in blocks:
            # First, chunk the raw block content to get proper 20-line boundaries
            content_chunks = self.vector_store.chunk_text(
                block.content or "",
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            # Generate metadata template for this block
            metadata_template = self._generate_block_metadata_template(block, file_data)

            # Track which chunks belong to this block
            for chunk_idx, chunk_metadata in enumerate(content_chunks):
                # Create embedding text by adding metadata to this specific chunk
                chunk_embedding_text = f"{metadata_template}\nCode:\n{chunk_metadata['text']}"
                all_chunk_texts.append(chunk_embedding_text)

                # Calculate actual source line numbers using chunk boundaries
                chunk_start_line = chunk_metadata["start_line"] + block.start_line - 1
                chunk_end_line = chunk_metadata["end_line"] + block.start_line - 1

                block_chunk_mapping.append(
                    {
                        "block": block,
                        "chunk_index": chunk_idx,
                        "embedding_text": chunk_embedding_text,
                        "chunk_start_line": chunk_start_line,
                        "chunk_end_line": chunk_end_line,
                    }
                )

        # Generate ALL embeddings in one batch - this is the key performance improvement!
        if not all_chunk_texts:
            logger.debug("No chunk texts to embed")
            return {"total_embeddings": 0, "blocks_processed": 0}

        logger.debug(
            f"Generating embeddings for {len(all_chunk_texts)} chunks in one batch"
        )
        all_embeddings = self.vector_store.embedding_model.get_embeddings_batch(
            all_chunk_texts
        )

        if all_embeddings is None:
            logger.error("Embedding generation returned None")
            return {"total_embeddings": 0, "blocks_processed": 0}

        # Prepare all embedding data for batch database insertion
        batch_embedding_data = []
        for i, embedding in enumerate(all_embeddings):
            mapping = block_chunk_mapping[i]
            block = mapping["block"]
            chunk_index = mapping["chunk_index"]
            chunk_start_line = mapping["chunk_start_line"]
            chunk_end_line = mapping["chunk_end_line"]

            batch_embedding_data.append(
                {
                    "node_id": f"block_{block.id}",
                    "project_id": project_id,
                    "embedding": embedding,
                    "chunk_index": chunk_index,
                    "chunk_start_line": chunk_start_line,
                    "chunk_end_line": chunk_end_line,
                }
            )

        # Store ALL embeddings in a single database transaction - MASSIVE speedup!
        embedding_ids = self.vector_store.store_embeddings_batch(batch_embedding_data)

        # Log batch results
        for i, embedding_id in enumerate(embedding_ids):
            data = batch_embedding_data[i]
            logger.debug(
                f"Stored embedding {embedding_id} for block {data['node_id']} chunk {data['chunk_index']} "
                f"(lines {data['chunk_start_line']}-{data['chunk_end_line']})"
            )

        total_embeddings = len(embedding_ids)

        logger.debug(
            f"Batch processed {len(blocks)} blocks, generated {total_embeddings} embeddings"
        )
        return {"total_embeddings": total_embeddings}

    def _get_block_hierarchy_path(
        self, target_block: CodeBlock, file_data: FileData
    ) -> str:
        """Get the hierarchical path to a block (e.g., 'ClassName.method_name')."""

        def find_parent_path(
            block_id: int, blocks: List[CodeBlock], path: List[str] = []
        ) -> List[str]:

            for block in blocks:
                if block.id == block_id:
                    return path + [block.name]

                # Check if target is in children
                if block.children:
                    child_path = find_parent_path(
                        block_id, block.children, path + [block.name]
                    )
                    if child_path:
                        return child_path

            return []

        # Find the hierarchical path
        hierarchy = find_parent_path(target_block.id, file_data.blocks)

        # Remove the target block's own name (it's already in the metadata)
        if hierarchy and hierarchy[-1] == target_block.name:
            hierarchy = hierarchy[:-1]

        return " > ".join(hierarchy) if hierarchy else ""

    def _store_embeddings_with_metadata(
        self,
        entity_id: str,
        project_id: int,
        content: str,
        metadata: str,
        is_file: bool = False,
        source_content: Optional[str] = None,
        source_start_line: int = 1,
    ) -> List[int]:
        """
        Generate and store chunked embeddings with metadata added only to first chunk.

        Args:
            entity_id: Unique identifier (file ID or block ID)
            project_id: Project ID
            content: Raw content to be chunked
            metadata: Metadata to add to first chunk only
            is_file: True if this is a file embedding, False if it's a block embedding

        Returns:
            List of embedding IDs that were stored
        """
        if not content.strip():
            logger.debug(f"No content to embed for entity {entity_id}")
            return []

        # Add prefix to distinguish file vs block IDs during retrieval
        prefix = "file" if is_file else "block"
        prefixed_entity_id = f"{prefix}_{entity_id}"

        try:
            # Generate embeddings using content with metadata added to first chunk only
            embeddings_with_metadata = (
                self.vector_store.get_chunked_embeddings_with_metadata(
                    content,
                    metadata=metadata,
                    max_tokens=self.max_tokens,
                    overlap_tokens=self.overlap_tokens,
                )
            )

            if not embeddings_with_metadata:
                logger.warning(f"No embeddings generated for entity {entity_id}")
                return []

            # For line number calculation, use source content if provided (for blocks),
            # otherwise use the full content (for files)
            line_calc_content = source_content if source_content is not None else content
            content_chunks = self.vector_store.chunk_text(
                line_calc_content,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            embedding_ids = []

            for chunk_index, (embedding, chunk_metadata) in enumerate(
                embeddings_with_metadata
            ):
                try:
                    # Calculate line numbers
                    if chunk_index < len(content_chunks):
                        content_chunk = content_chunks[chunk_index]
                        # Add source start line offset for blocks
                        chunk_start_line = content_chunk["start_line"] + source_start_line - 1
                        chunk_end_line = content_chunk["end_line"] + source_start_line - 1
                    else:
                        # Fallback calculation using source content for line numbers
                        char_start = chunk_metadata.get("start", 0)
                        text_up_to_start = line_calc_content[:char_start]
                        lines_before_chunk = text_up_to_start.count("\n")
                        chunk_text = chunk_metadata.get("text", "")
                        chunk_line_count = len(chunk_text.split("\n"))
                        chunk_start_line = lines_before_chunk + 1 + source_start_line - 1
                        chunk_end_line = chunk_start_line + chunk_line_count - 1

                    # Store embedding in vector database
                    embedding_id = self.vector_store.store_embedding(
                        node_id=prefixed_entity_id,
                        project_id=project_id,
                        chunk_index=chunk_index,
                        chunk_start_line=chunk_start_line,
                        chunk_end_line=chunk_end_line,
                        embedding=embedding,
                    )

                    if embedding_id:
                        embedding_ids.append(embedding_id)
                        logger.debug(
                            f"Stored embedding {embedding_id} for {prefixed_entity_id} chunk {chunk_index} (lines {chunk_start_line}-{chunk_end_line})"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to store embedding for {prefixed_entity_id} chunk {chunk_index}: {e}"
                    )
                    continue

            return embedding_ids

        except Exception as e:
            logger.error(f"Failed to generate embeddings for entity {entity_id}: {e}")
            return []

    def _store_embeddings(
        self,
        entity_id: str,
        project_id: int,
        embedding_text: str,
        content: str,
        is_file: bool = False,
    ) -> List[int]:
        """
        Generate and store chunked embeddings for an entity.

        Args:
            entity_id: Unique identifier (file ID or block ID)
            project_id: Project ID
            embedding_text: Rich text with metadata for semantic search (file path, language, etc.)
            content: Raw code content for accurate line number calculation
            is_file: True if this is a file embedding, False if it's a block embedding

        Returns:
            List of embedding IDs that were stored
        """
        if not embedding_text.strip():
            logger.debug(f"No content to embed for entity {entity_id}")
            return []

        # Add prefix to distinguish file vs block IDs during retrieval
        prefix = "file" if is_file else "block"
        prefixed_entity_id = f"{prefix}_{entity_id}"

        try:
            # Generate embeddings using the full embedding_text (with metadata)
            embeddings_with_metadata = self.vector_store.get_chunked_embeddings(
                embedding_text,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            if not embeddings_with_metadata:
                logger.warning(f"No embeddings generated for entity {entity_id}")
                return []

            # Also chunk the content directly to get accurate line numbers
            content_chunks = self.vector_store.chunk_text(
                content,
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
            )

            embedding_ids = []

            for chunk_index, (embedding, chunk_metadata) in enumerate(
                embeddings_with_metadata
            ):
                try:
                    # Calculate line numbers
                    if chunk_index < len(content_chunks):
                        content_chunk = content_chunks[chunk_index]
                        chunk_start_line = content_chunk["start_line"]
                        chunk_end_line = content_chunk["end_line"]
                    else:
                        # Fallback calculation
                        char_start = chunk_metadata.get("start", 0)
                        text_up_to_start = content[:char_start]
                        lines_before_chunk = text_up_to_start.count("\n")
                        chunk_text = chunk_metadata.get("text", "")
                        chunk_line_count = len(chunk_text.split("\n"))
                        chunk_start_line = lines_before_chunk + 1
                        chunk_end_line = chunk_start_line + chunk_line_count - 1

                    # Store embedding with prefixed ID
                    embedding_id = self.vector_store.store_embedding(
                        node_id=prefixed_entity_id,  # "file_123" or "block_456"
                        project_id=project_id,
                        chunk_index=chunk_index,
                        embedding=embedding,
                        chunk_start_line=chunk_start_line,
                        chunk_end_line=chunk_end_line,
                    )

                    embedding_ids.append(embedding_id)
                    logger.debug(
                        f"Stored embedding {embedding_id} for {prefix} {entity_id} "
                        f"chunk {chunk_index} (lines {chunk_start_line}-{chunk_end_line})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to store embedding for {prefix} {entity_id} "
                        f"chunk {chunk_index}: {e}"
                    )
                    continue

            return embedding_ids

        except Exception as e:
            logger.error(f"Failed to generate embeddings for entity {entity_id}: {e}")
            return []

    def _collect_blocks_to_embed(self, blocks: List[CodeBlock]) -> List[CodeBlock]:
        """
        Collect all blocks that should be embedded.

        Args:
            blocks: List of code blocks to evaluate

        Returns:
            List of blocks that should be embedded
        """
        blocks_to_embed = []

        for block in blocks:
            if self._should_embed_block(block):
                blocks_to_embed.append(block)

                # Recursively check nested blocks
                if block.children:
                    nested_blocks = self._collect_blocks_to_embed(block.children)
                    blocks_to_embed.extend(nested_blocks)

        return blocks_to_embed

    def process_file_data(self, file_data: FileData, project_id: int) -> Dict[str, int]:
        """
        Process a FileData object and generate embeddings for the file and its strategic blocks.

        Args:
            file_data: FileData object to process
            project_id: Project ID

        Returns:
            Dictionary with embedding statistics
        """
        stats = {
            "file_embeddings": 0,
            "block_embeddings": 0,
            "total_chunks": 0,
            "blocks_processed": 0,
        }

        try:
            # Collect blocks to embed first
            blocks_to_embed = self._collect_blocks_to_embed(file_data.blocks)
            logger.debug(
                f"Found {len(blocks_to_embed)} blocks to embed in {file_data.file_path}"
            )

            if blocks_to_embed:
                # If we have extracted blocks, embed them with hierarchical context
                # Skip file-level chunking to avoid redundancy
                logger.debug(
                    f"Embedding {len(blocks_to_embed)} hierarchical blocks for {file_data.file_path}"
                )
            elif getattr(file_data, "unsupported", False):
                # Only embed entire file for unsupported file types
                logger.debug(
                    f"Unsupported file type, embedding entire file: {file_data.file_path}"
                )
                file_content = self._generate_file_embedding_text(file_data)
                file_metadata = self._generate_file_metadata(file_data)
                file_embedding_ids = self._store_embeddings_with_metadata(
                    entity_id=str(file_data.id),
                    project_id=project_id,
                    content=file_content,
                    metadata=file_metadata,
                    is_file=True,
                )
                stats["file_embeddings"] = len(file_embedding_ids)
                stats["total_chunks"] += len(file_embedding_ids)
            else:
                # Supported file type but no blocks extracted - skip embedding
                logger.debug(
                    f"Supported file with no extractable blocks, skipping: {file_data.file_path}"
                )

            # Process all blocks in a single batch for massive performance improvement
            if blocks_to_embed:
                block_embedding_stats = self._store_embeddings_batch_for_blocks(
                    blocks_to_embed, file_data, project_id
                )
                stats["block_embeddings"] += block_embedding_stats["total_embeddings"]
                stats["total_chunks"] += block_embedding_stats["total_embeddings"]
                stats["blocks_processed"] += len(blocks_to_embed)

            return stats

        except Exception as e:
            logger.error(f"Error processing file {file_data.file_path}: {e}")
            return stats

    def process_multiple_files(
        self, file_data_list: List[FileData], project_id: int, batch_size: int = 50
    ) -> Dict[str, int]:
        """
        Process multiple FileData objects in batches.

        Args:
            file_data_list: List of FileData objects to process
            project_id: Project ID
            batch_size: Number of files to process in each batch

        Returns:
            Dictionary with total embedding statistics
        """
        total_stats = {
            "files_processed": 0,
            "file_embeddings": 0,
            "block_embeddings": 0,
            "total_chunks": 0,
            "blocks_processed": 0,
        }

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            TextColumn("{task.fields[stats]}"),
            refresh_per_second=4,
        ) as progress:
            task_id = progress.add_task(
                "Embedding files", total=len(file_data_list), stats=""
            )
            for i in range(0, len(file_data_list), batch_size):
                batch_files = file_data_list[i : i + batch_size]

                for file_data in batch_files:
                    file_stats = self.process_file_data(file_data, project_id)

                    # Accumulate stats
                    total_stats["files_processed"] += 1
                    total_stats["file_embeddings"] += file_stats["file_embeddings"]
                    total_stats["block_embeddings"] += file_stats["block_embeddings"]
                    total_stats["total_chunks"] += file_stats["total_chunks"]
                    total_stats["blocks_processed"] += file_stats["blocks_processed"]

                    # Update progress bar with detailed stats
                    stats_text = f"chunks={total_stats['total_chunks']}, blocks={total_stats['blocks_processed']}, embeddings={total_stats['file_embeddings'] + total_stats['block_embeddings']}"
                    progress.update(task_id, advance=1, stats=stats_text)

        return total_stats

    def delete_embeddings(self, node_ids: List[str], project_id: int) -> None:
        """Delete embeddings for specified nodes.

        Args:
            node_ids: List of node IDs to delete (should include prefixes like 'file_' or 'block_')
            project_id: Project ID to scope the deletion
        """
        try:
            if not node_ids:
                logger.debug("No node IDs provided for deletion")
                return

            # Get vector store to access embeddings database
            vector_store = get_vector_store()

            if vector_store.connection is None:
                logger.error(
                    "Vector store connection is None, cannot delete embeddings"
                )
                return

            # Create placeholders for the SQL query
            placeholders = ",".join(["?" for _ in node_ids])
            params = tuple(node_ids + [str(project_id)])

            # Execute deletion
            vector_store.connection.execute(
                f"""DELETE FROM embeddings
                   WHERE node_id IN ({placeholders})
                   AND project_id = ?""",
                params,
            )
            vector_store.connection.commit()

            logger.debug(
                f"Deleted {len(node_ids)} embeddings from database (file: 1, blocks: {len(node_ids)-1})"
            )

        except Exception as e:
            logger.error(f"Error deleting node embeddings: {e}")
            logger.error(f"Node IDs: {node_ids}, Project ID: {project_id}")


def parse_entity_id(prefixed_id: str) -> tuple[str, str]:
    """
    Parse a prefixed entity ID to extract the type and original ID.

    Args:
        prefixed_id: ID with prefix like "file_123" or "block_456"

    Returns:
        Tuple of (entity_type, original_id) where entity_type is "file" or "block"

    Example:
        parse_entity_id("file_123") -> ("file", "123")
        parse_entity_id("block_456") -> ("block", "456")
    """
    if prefixed_id.startswith("file_"):
        return "file", prefixed_id[5:]  # Remove "file_" prefix
    elif prefixed_id.startswith("block_"):
        return "block", prefixed_id[6:]  # Remove "block_" prefix
    else:
        # Fallback for IDs without prefix (backward compatibility)
        return "unknown", prefixed_id


# Global instance
_embedding_engine = None


def get_embedding_engine() -> EmbeddingEngine:
    """Return singleton instance of EmbeddingEngine."""
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine
