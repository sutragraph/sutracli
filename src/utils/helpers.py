"""Helper functions for tree-sitter processing."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Generator, List


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_node_type(node_type: str) -> str:
    """Convert node type to PascalCase database label format."""
    # Convert to PascalCase and remove special characters
    normalized = re.sub(r"[^a-zA-Z0-9]", "_", node_type)
    normalized = "".join(word.capitalize() for word in normalized.split("_") if word)

    # Ensure it starts with a letter
    if normalized and not normalized[0].isalpha():
        normalized = f"Node_{normalized}"

    return normalized or "UnknownNode"


def normalize_relationship_type(rel_type: str) -> str:
    """
    Normalize relationship type to follow SQLite conventions.

    Args:
        rel_type: Original relationship type

    Returns:
        Normalized relationship type (UPPER_SNAKE_CASE)
    """
    # Convert to UPPER_SNAKE_CASE
    normalized = re.sub(
        r"[^a-zA-Z0-9]", "_", rel_type
    )  # Replace non-alphanumeric with underscores
    normalized = normalized.upper()

    # Remove consecutive underscores
    normalized = re.sub(
        r"_+", "_", normalized
    )  # Replace multiple underscores with a single one
    normalized = normalized.strip("_")  # Strip leading/trailing underscores

    return normalized or "UNKNOWN_RELATIONSHIP"


def chunk_list(lst: List[Any], chunk_size: int) -> Generator[List[Any], None, None]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]
