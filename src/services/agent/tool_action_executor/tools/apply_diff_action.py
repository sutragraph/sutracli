"""
Apply diff executor for handling apply_diff tool actions.
"""

import re
import uuid
import time
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from loguru import logger

from src.services.agent.agentic_core import AgentAction


class ApplyDiffExecutor:
    """Executor for apply_diff actions using search/replace format."""

    def apply_diff(
        self,
        file_path: str,
        diff_content: str,
        session_id: str,
        query_id: str,
    ) -> Iterator[Dict[str, Any]]:
        """
        Apply diff changes to a file using search/replace format.
        
        Args:
            file_path: Path to the file to modify
            diff_content: Diff content in search/replace format
            session_id: Current session ID
            query_id: Current query ID
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
                yield {"success": False, "error": "No valid search/replace blocks found"}
                return

            # Apply all search/replace operations
            modified_content = original_content
            for block in search_replace_blocks:
                modified_content = self._apply_search_replace(
                    modified_content, block["search"], block["replace"], block.get("start_line")
                )

            if modified_content is None:
                yield {"success": False, "error": "Failed to apply search/replace operations"}
                return

            # Create backup and apply changes
            change_id = str(uuid.uuid4())
            backup_path = self._create_backup(file_path, change_id, original_content)

            # Write modified content
            file_to_check.parent.mkdir(parents=True, exist_ok=True)
            file_to_check.write_text(modified_content)

            yield {
                "type": "tool_use",
                "change_id": change_id,
                "file_path": file_path,
                "message": f"📝 Applied diff {change_id} to {file_path}",
            }

            yield {
                "success": True,
                "change_id": change_id,
                "file_path": file_path,
                "status": "applied",
                "backup_path": backup_path,
                "changes_applied": len(search_replace_blocks),
            }

            # Yield detailed TOOL STATUS (success - no original_request needed)
            yield {
                "type": "tool_status",
                "used_tool": "apply_diff",
                "applied_changes_to_files": [file_path],
                "failed_files": [],
                "status": "success",
                "summary": f"Successfully applied {len(search_replace_blocks)} diff changes to {file_path}",
            }

        except Exception as e:
            logger.error(f"Failed to apply diff to {file_path}: {e}")
            yield {"success": False, "error": str(e)}

            # Yield detailed TOOL STATUS for failure (include full original_request)
            yield {
                "type": "tool_status",
                "used_tool": "apply_diff",
                "applied_changes_to_files": [],
                "failed_files": [file_path],
                "status": "failed",
                "summary": f"Failed to apply diff to {file_path}: {str(e)}",
                "failed_changes": f"<error>{str(e)}</error>",
                "original_request": f"<apply_diff><path>{file_path}</path><diff>{diff_content}</diff></apply_diff>",
                "details": {
                    "operation": "diff_apply",
                    "file_path": file_path,
                    "error": str(e),
                },
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
            backup_dir = Path(".sutra_backups")
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"{change_id}_{Path(file_path).name}.backup"
            backup_path.write_text(content)

            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""


def execute_apply_diff_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute apply_diff action.
    
    Args:
        action: AgentAction containing apply_diff parameters
    Yields:
        Dictionary containing the results of the apply_diff operation.
    """
    try:
        executor = ApplyDiffExecutor()
        parameters = action.parameters or {}

        file_path = parameters.get("path")
        diff_content = parameters.get("diff")
        session_id = parameters.get("session_id", "default")
        query_id = parameters.get("query_id", "default")

        if not file_path:
            yield {
                "tool_name": "apply_diff",
                "status": "error",
                "data": {"error": "path parameter is required"},
            }
            return

        if not diff_content:
            yield {
                "tool_name": "apply_diff", 
                "status": "error",
                "data": {"error": "diff parameter is required"},
            }
            return

        # Apply the diff
        results = list(executor.apply_diff(file_path, diff_content, session_id, query_id))

        # Check if successful
        success = any(result.get("success") for result in results)

        if success:
            yield {
                "tool_name": "apply_diff",
                "status": "success", 
                "data": {
                    "summary": f"Successfully applied diff to {file_path}",
                    "file_path": file_path,
                    "results": results
                },
            }
        else:
            error_msg = next((r.get("error") for r in results if r.get("error")), "Unknown error")
            yield {
                "tool_name": "apply_diff",
                "status": "error",
                "data": {"error": error_msg, "file_path": file_path},
            }

            # Yield detailed TOOL STATUS for main-level failure (include full original_request)
            yield {
                "type": "tool_status",
                "used_tool": "apply_diff",
                "applied_changes_to_files": [],
                "failed_files": [file_path],
                "status": "failed",
                "summary": f"Apply diff operation failed: {error_msg}",
                "failed_changes": f"<error>{error_msg}</error>",
                "original_request": f"<apply_diff><path>{file_path}</path><diff>{diff_content}</diff></apply_diff>",
                "details": {
                    "operation": "diff_apply",
                    "file_path": file_path,
                    "error": error_msg,
                },
            }

    except Exception as e:
        logger.error(f"Apply diff action execution failed: {e}")
        yield {
            "tool_name": "apply_diff",
            "status": "error", 
            "data": {"error": f"Apply diff execution failed: {str(e)}"},
        }
