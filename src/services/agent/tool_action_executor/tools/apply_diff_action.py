"""
Apply diff executor for handling apply_diff tool actions.
"""

import re
import uuid
import time
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from loguru import logger

from src.config.settings import config
from src.services.agent.agentic_core import AgentAction


class ApplyDiffExecutor:
    """Executor for apply_diff actions using search/replace format."""

    def apply_diff(
        self,
        file_path: str,
        diff_content: str,
        session_id: str,
        query_id: str,
    ) -> Dict[str, Any]:
        """
        Apply diff changes to a file using search/replace format.

        Args:
            file_path: Path to the file to modify
            diff_content: Diff content in search/replace format
            session_id: Current session ID
            query_id: Current query ID

        Returns:
            Dictionary with success status and details
        """
        try:
            # Resolve file path
            file_to_check = Path(file_path)

            # Read original content
            if file_to_check.exists():
                original_content = file_to_check.read_text()
            else:
                original_content = ""

            # Parse the diff content
            search_replace_blocks = self._parse_diff_content(diff_content)

            if not search_replace_blocks:
                return {
                    "success": False,
                    "file_path": file_path,
                    "error": "No valid search/replace blocks found",
                    "failed_diff": diff_content,
                }

            # Apply all search/replace operations
            modified_content = original_content
            failed_blocks = []

            for block in search_replace_blocks:
                result = self._apply_search_replace(
                    modified_content,
                    block["search"],
                    block["replace"],
                    block.get("start_line"),
                )

                if result is None:
                    failed_blocks.append(block)
                else:
                    modified_content = result

            if failed_blocks:
                return {
                    "success": False,
                    "file_path": file_path,
                    "error": f"Failed to apply {len(failed_blocks)} search/replace operations",
                    "failed_diff": diff_content,
                    "failed_blocks": failed_blocks,
                }

            # Create backup and apply changes
            change_id = str(uuid.uuid4())
            backup_path = self._create_backup(file_path, change_id, original_content)

            # Write modified content
            file_to_check.parent.mkdir(parents=True, exist_ok=True)
            file_to_check.write_text(modified_content)

            return {
                "success": True,
                "file_path": file_path,
                "change_id": change_id,
                "backup_path": backup_path,
                "changes_applied": len(search_replace_blocks),
            }

        except Exception as e:
            logger.error(f"Failed to apply diff to {file_path}: {e}")
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e),
                "failed_diff": diff_content,
            }

    def _parse_diff_content(self, diff_content: str) -> list:
        """Parse diff content to extract search/replace blocks."""
        blocks = []

        logger.debug(f"Original diff content: {diff_content[:200]}...")

        # Clean up the diff content first
        cleaned_diff = self._clean_diff_content(diff_content)
        logger.debug(f"Cleaned diff content: {cleaned_diff[:200]}...")

        # Split the content by search blocks manually since regex is failing
        # Look for the pattern: <<<<<<<SEARCH :start_line:N followed by content until >>>>>>> REPLACE
        search_blocks = []

        # Split by >>>>>>> REPLACE to get individual blocks
        parts = cleaned_diff.split('>>>>>>> REPLACE')

        for part in parts[:-1]:  # Last part is empty after split
            # Look for the search header
            if '<<<<<<<' in part and 'SEARCH' in part:
                lines = part.strip().split('\n')

                # Find the search header line
                search_header_idx = -1
                start_line = None

                for i, line in enumerate(lines):
                    if '<<<<<<<' in line and 'SEARCH' in line:
                        search_header_idx = i
                        break

                # Look for start_line in the next few lines after the search header
                if search_header_idx >= 0:
                    for i in range(search_header_idx, min(search_header_idx + 3, len(lines))):
                        if ':start_line:' in lines[i]:
                            try:
                                start_line = int(re.search(r':start_line:\s*(\d+)', lines[i]).group(1))
                                break
                            except:
                                start_line = None

                if search_header_idx >= 0:
                    # Find the separator line (-------)
                    separator_idx = -1
                    for i in range(search_header_idx + 1, len(lines)):
                        if '-------' in lines[i]:
                            separator_idx = i
                            break

                    # Find the replace separator (=======)
                    replace_idx = -1
                    for i in range(separator_idx + 1, len(lines)):
                        if '=======' in lines[i]:
                            replace_idx = i
                            break

                    if separator_idx > 0 and replace_idx > separator_idx:
                        # Extract search and replace content
                        search_content = '\n'.join(lines[separator_idx + 1:replace_idx]).strip()
                        replace_content = '\n'.join(lines[replace_idx + 1:]).strip()

                        if search_content and replace_content:
                            blocks.append({
                                "start_line": start_line,
                                "search": search_content,
                                "replace": replace_content
                            })
                            logger.debug(f"Found block with start_line: {start_line}")

        logger.debug(f"Parsed {len(blocks)} blocks")
        return blocks

    def _clean_diff_content(self, diff_content: str) -> str:
        """Clean up malformed diff content."""
        # Remove multiple consecutive ======= lines, keep only one
        cleaned = re.sub(r"=======+", "=======", diff_content)

        # Fix malformed SEARCH headers - preserve the start_line info
        # Convert "<<<<<<<SEARCH :start_line:1" to "<<<<<<< SEARCH\n:start_line:1"
        cleaned = re.sub(
            r"<<<<<<<\s*SEARCH\s*:start_line:\s*(\d+)",
            r"<<<<<<< SEARCH\n:start_line:\1",
            cleaned
        )

        # Ensure proper spacing around markers
        cleaned = re.sub(r"<<<<<<<\s*SEARCH", "<<<<<<< SEARCH", cleaned)
        cleaned = re.sub(r">>>>>>>\s*REPLACE", ">>>>>>> REPLACE", cleaned)

        return cleaned

    def _apply_search_replace(self, content: str, search: str, replace: str, start_line: Optional[int] = None) -> Optional[str]:
        """Apply search and replace operation to content."""
        try:
            # If start_line is provided, use it as a hint for more precise matching
            if start_line and start_line > 0:
                lines = content.splitlines(keepends=True)
                if start_line <= len(lines):
                    # Look for the search content around the specified line
                    search_lines = search.splitlines()
                    content_around_line = ''.join(lines[start_line-1:start_line-1+len(search_lines)])

                    if search in content_around_line:
                        # Replace in the specific section
                        before = ''.join(lines[:start_line-1])
                        after_start = start_line - 1 + len(search_lines)
                        after = ''.join(lines[after_start:]) if after_start < len(lines) else ""

                        return before + replace + "\n" + after

            # Fallback to global search and replace
            if search in content:
                return content.replace(search, replace, 1)  # Replace only first occurrence
            else:
                logger.warning(f"Search content not found: {search[:100]}...")
                return None

        except Exception as e:
            logger.error(f"Failed to apply search/replace: {e}")
            return None

    def _create_backup(self, file_path: str, change_id: str, content: str) -> str:
        """Create backup of original file content."""
        try:
            backup_dir = Path(config.storage.file_edits_dir)
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"{change_id}_{Path(file_path).name}.backup"
            backup_path.write_text(content)

            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""

    def apply_multiple_diffs(
        self,
        file_diffs: Dict[str, str],
        session_id: str,
        query_id: str,
    ) -> Dict[str, Any]:
        """
        Apply diffs to multiple files and return consolidated results.

        Args:
            file_diffs: Dictionary mapping file paths to diff content
            session_id: Current session ID
            query_id: Current query ID

        Returns:
            Consolidated results with all successful and failed files
        """
        successful_files = []
        failed_files = []
        failed_diffs = {}

        for file_path, diff_content in file_diffs.items():
            result = self.apply_diff(file_path, diff_content, session_id, query_id)

            if result["success"]:
                successful_files.append(
                    {
                        "file_path": file_path,
                        "changes_applied": result["changes_applied"],
                    }
                )
            else:
                failed_files.append(
                    {
                        "file_path": file_path,
                        "error": result["error"],
                    }
                )
                failed_diffs[file_path] = result["failed_diff"]

        return {
            "type": "tool_use",
            "tool_name": "apply_diff",
            "successful_files": successful_files,
            "failed_files": failed_files,
            "failed_diffs": failed_diffs,
            "status": (
                "success"
                if not failed_files
                else "partial" if successful_files else "failed"
            ),
            "summary": f"Applied diffs to {len(successful_files)}/{len(file_diffs)} files successfully",
            "total_files": len(file_diffs),
            "success_count": len(successful_files),
            "failure_count": len(failed_files),
        }


def execute_apply_diff_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute apply_diff action.

    Args:
        action: AgentAction containing apply_diff parameters
    Yields:
        Dictionary containing the consolidated results of the apply_diff operation.
    """
    try:
        executor = ApplyDiffExecutor()
        parameters = action.parameters or {}

        session_id = parameters.get("session_id", "default")
        query_id = parameters.get("query_id", "default")

        # Handle single file diff
        if "path" in parameters and "diff" in parameters:
            file_path = parameters["path"]
            diff_content = parameters["diff"]

            if not file_path:
                yield {
                    "tool_name": "apply_diff",
                    "status": "error",
                    "error": "path parameter is required",
                }
                return

            if not diff_content:
                yield {
                    "tool_name": "apply_diff",
                    "status": "error",
                    "error": "diff parameter is required",
                }
                return

            file_diffs = {file_path: diff_content}

        # Handle multiple files (if parameters include files list)
        elif "files" in parameters:
            file_diffs = parameters["files"]
            if not isinstance(file_diffs, dict):
                yield {
                    "tool_name": "apply_diff",
                    "status": "error",
                    "error": "files parameter must be a dictionary mapping file paths to diff content",
                }
                return
        else:
            yield {
                "tool_name": "apply_diff",
                "status": "error",
                "error": "Either 'path' and 'diff' parameters or 'files' parameter is required",
            }
            return

        # Apply all diffs and get consolidated result
        result = executor.apply_multiple_diffs(file_diffs, session_id, query_id)

        # Yield the consolidated result
        yield result

    except Exception as e:
        logger.error(f"Apply diff action execution failed: {e}")
        yield {
            "tool_name": "apply_diff",
            "status": "error", 
            "data": {"error": f"Apply diff execution failed: {str(e)}"},
        }
