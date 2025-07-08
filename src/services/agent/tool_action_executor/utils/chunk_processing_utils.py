"""
Simple utility functions for chunk processing shared between executors.
"""

from typing import Dict, Any


def create_chunk_info(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized chunk info dictionary.

    Args:
        chunk: Chunk data from chunk_large_code_clean

    Returns:
        Standardized chunk info dictionary
    """
    return {
        "chunk_num": chunk["chunk_num"],
        "total_chunks": chunk["total_chunks"],
        "chunk_start_line": chunk.get("chunk_start_line", chunk.get("start_line")),
        "chunk_end_line": chunk.get("chunk_end_line", chunk.get("end_line")),
        "total_lines": chunk["total_lines"],
    }


def should_chunk_content(code_content: str, chunking_threshold: int) -> bool:
    """
    Determine if content should be chunked.

    Args:
        code_content: Code content to check
        chunking_threshold: Threshold for chunking

    Returns:
        True if content should be chunked
    """
    code_lines = code_content.split("\n")
    return len(code_lines) > chunking_threshold



