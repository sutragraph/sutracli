"""Utility functions for generating and managing file diffs."""

import difflib
from typing import Dict, List

from loguru import logger


def generate_unified_diff(old_content: str, new_content: str, file_path: str) -> str:
    """Generate a unified diff between old and new content.

    Args:
        old_content: Original file content
        new_content: Modified file content
        file_path: Path to the file (for display in diff)
        change_type: Type of change ("added", "modified", "deleted")

    Returns:
        Unified diff as a string
    """
    try:
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        diff_str = "\n".join(diff_lines)
        return diff_str if diff_str else "No differences found"

    except Exception as e:
        logger.error(f"Error generating diff for {file_path}: {e}")
        return f"Error generating diff: {str(e)}"


def generate_diffs_from_content_map(
    content_map: Dict[str, Dict[str, str]]
) -> List[Dict[str, str]]:
    """Generate diffs from a content map containing old and new content for files.

    Args:
        content_map: Dictionary mapping file paths to dict with 'old_content' and 'new_content'

    Returns:
        List of dictionaries containing path, change_type, and diff for each file
    """
    diffs = []

    for file_path, content_info in content_map.items():
        old_content = content_info.get("old_content", "")
        new_content = content_info.get("new_content", "")

        # Determine change type
        if not old_content and new_content:
            change_type = "added"
        elif old_content and not new_content:
            change_type = "deleted"
        else:
            change_type = "modified"

        diff_str = generate_unified_diff(old_content, new_content, file_path)

        diffs.append(
            {
                "path": file_path,
                "change_type": change_type,
                "diff": diff_str,
            }
        )

    return diffs


def format_diffs_for_message(diffs: List[Dict[str, str]]) -> str:
    """Format diffs into a readable message for agent communication.

    Args:
        diffs: List of diff dictionaries with path, change_type, and diff

    Returns:
        Formatted string with all diffs
    """
    if not diffs:
        return ""

    message_parts = ["\n\nDiff of changes made:"]

    for diff_info in diffs:
        file_path = diff_info.get("path", "unknown")
        change_type = diff_info.get("change_type", "modified")
        diff_text = diff_info.get("diff", "")

        message_parts.append(f"\n{change_type.upper()}: {file_path}")
        message_parts.append(f"{diff_text}\n")

    return "\n".join(message_parts)
