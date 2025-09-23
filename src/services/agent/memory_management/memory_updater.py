"""
Memory Updater Module

Handles updating Sutra memory when code changes happen during incremental indexing.
This module ensures that stored code snippets remain accurate when files are modified.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from graph.graph_operations import GraphOperations

from .memory_operations import MemoryOperations
from .models import CodeSnippet


@dataclass
class LineChange:
    """Represents a line number change in a file"""

    line_number: int
    change_type: str  # "insert" or "delete"
    change_amount: int  # number of lines added/removed


@dataclass
class CodeUpdate:
    """Represents an update to a code snippet"""

    code_id: str
    new_start_line: int
    new_end_line: int
    new_content: Optional[str] = None
    should_remove: bool = False


class MemoryUpdater:
    """Handles updating Sutra memory when code changes occur"""

    def __init__(self, memory_ops: MemoryOperations):
        self.memory_ops = memory_ops
        self.graph_ops = GraphOperations()

    def update_memory_for_file_changes(
        self, changed_files: Set[Path], deleted_files: Set[Path], project_id: int
    ) -> Dict[str, Any]:
        """
        Update Sutra memory when files change during incremental indexing.

        Args:
            changed_files: Set of file paths that were modified
            deleted_files: Set of file paths that were deleted
            project_id: Project ID for database queries

        Returns:
            Dict with update statistics
        """
        updates_made = {
            "codes_updated": 0,
            "codes_removed": 0,
            "line_number_updates": 0,
            "content_updates": 0,
            "files_processed": 0,
        }

        try:
            # Get all stored code snippets
            all_code_snippets = self.memory_ops.get_all_code_snippets()

            logger.debug(
                f"Memory updater found {len(all_code_snippets)} code snippets in memory"
            )
            for snippet_id, snippet in all_code_snippets.items():
                logger.debug(
                    f"  - {snippet_id}: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})"
                )

            if not all_code_snippets:
                logger.debug("No code snippets in memory to update")
                return updates_made

            # Process deleted files first
            for file_path in deleted_files:
                file_path_str = str(file_path)
                removed_count = self._remove_code_snippets_for_file(file_path_str)
                updates_made["codes_removed"] += removed_count
                if removed_count > 0:
                    updates_made["files_processed"] += 1
                    logger.debug(
                        f"🗑️  Removed {removed_count} code snippets for deleted file: {file_path}"
                    )

            # Process changed files
            for file_path in changed_files:
                file_path_str = str(file_path)
                file_updates = self._update_code_snippets_for_file(
                    file_path_str, project_id
                )
                updates_made["codes_updated"] += file_updates["codes_updated"]
                updates_made["line_number_updates"] += file_updates[
                    "line_number_updates"
                ]
                updates_made["content_updates"] += file_updates["content_updates"]

                if file_updates["codes_updated"] > 0:
                    updates_made["files_processed"] += 1
                    logger.debug(
                        f"🔄 Updated {file_updates['codes_updated']} code snippets for file: {file_path}"
                    )

            total_updates = (
                updates_made["codes_updated"] + updates_made["codes_removed"]
            )
            if total_updates > 0:
                logger.debug(
                    f"✅ Memory update completed: {total_updates} code snippets processed"
                )
            else:
                logger.debug("No memory updates required")

        except Exception as e:
            logger.error(f"Error updating memory for file changes: {e}")

        return updates_made

    def _remove_code_snippets_for_file(self, file_path: str) -> int:
        """Remove all code snippets for a deleted file"""
        removed_count = 0
        code_snippets = self.memory_ops.get_code_snippets_by_file(file_path)

        for code_snippet in code_snippets:
            if self.memory_ops.remove_code_snippet(code_snippet.id):
                removed_count += 1
                logger.debug(
                    f"Removed code snippet {code_snippet.id} for deleted file {file_path}"
                )

        return removed_count

    def _update_code_snippets_for_file(
        self, file_path: str, project_id: int
    ) -> Dict[str, int]:
        """Update code snippets for a changed file"""
        updates = {"codes_updated": 0, "line_number_updates": 0, "content_updates": 0}

        logger.debug(f"Updating code snippets for file: {file_path}")

        # Get code snippets for this file
        code_snippets = self.memory_ops.get_code_snippets_by_file(file_path)

        logger.debug(f"Found {len(code_snippets)} code snippets for file {file_path}")
        for snippet in code_snippets:
            logger.debug(
                f"  - {snippet.id}: lines {snippet.start_line}-{snippet.end_line}"
            )

        if not code_snippets:
            logger.debug(f"No code snippets found for file {file_path}")
            return updates

        # Get current file content from database
        current_content = self._get_current_file_content(file_path, project_id)
        if not current_content:
            logger.warning(f"Could not retrieve current content for {file_path}")
            return updates

        # Analyze each code snippet
        for code_snippet in code_snippets:
            try:
                logger.debug(f"Analyzing code snippet {code_snippet.id}...")

                update_info = self._analyze_code_snippet_changes(
                    code_snippet, current_content
                )

                logger.debug(f"Analysis result for {code_snippet.id}: {update_info}")

                if update_info:
                    if update_info.should_remove:
                        # Remove code snippet if content no longer exists
                        self.memory_ops.remove_code_snippet(code_snippet.id)
                        logger.debug(
                            f"Removed code snippet {code_snippet.id} - content no longer exists"
                        )
                    else:
                        # Update the code snippet
                        success = self._apply_code_snippet_update(
                            code_snippet, update_info
                        )
                        if success:
                            updates["codes_updated"] += 1
                            if update_info.new_content:
                                updates["content_updates"] += 1
                            if (
                                update_info.new_start_line != code_snippet.start_line
                                or update_info.new_end_line != code_snippet.end_line
                            ):
                                updates["line_number_updates"] += 1

                            logger.debug(
                                f"Updated code snippet {code_snippet.id}: "
                                f"lines {code_snippet.start_line}-{code_snippet.end_line} -> "
                                f"{update_info.new_start_line}-{update_info.new_end_line}"
                            )
                else:
                    logger.debug(
                        f"No updates needed for code snippet {code_snippet.id}"
                    )

            except Exception as e:
                logger.error(f"Error updating code snippet {code_snippet.id}: {e}")
                import traceback

                traceback.print_exc()

        return updates

    def _get_current_file_content(
        self, file_path: str, project_id: int
    ) -> Optional[str]:
        """Get current file content from database using graph_operations"""
        try:
            import os
            from pathlib import Path

            # Try multiple path variations to find the file in database
            path_variations = []

            # Normalize the input file path
            normalized_input = os.path.normpath(file_path)
            path_variations.append(normalized_input)

            # Try absolute path if input is relative
            if not os.path.isabs(file_path):
                try:
                    abs_path = str(Path(file_path).resolve())
                    path_variations.append(abs_path)
                except Exception:
                    pass

            # Try relative path if input is absolute
            if os.path.isabs(file_path):
                try:
                    # Get just the filename
                    basename = os.path.basename(file_path)
                    path_variations.append(basename)

                    # Try to make it relative to current working directory
                    try:
                        rel_path = os.path.relpath(file_path)
                        path_variations.append(rel_path)
                    except Exception:
                        pass
                except Exception:
                    pass

            # Try each path variation using graph_operations
            for path_variant in path_variations:
                logger.debug(
                    f"Trying to find file content for path variant: {path_variant}"
                )

                file_id = self.graph_ops._get_file_id_by_path(path_variant)
                if file_id:
                    file_data = self.graph_ops.resolve_file(file_id)
                    if file_data and file_data.get("content"):
                        logger.debug(f"Found database content for {path_variant}")
                        return file_data.get("content", "")

            logger.debug(
                f"No database content found for {file_path} (tried {len(path_variations)} variations)"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting current file content for {file_path}: {e}")
            return None

    def _analyze_code_snippet_changes(
        self, code_snippet: CodeSnippet, current_content: str
    ) -> Optional[CodeUpdate]:
        """
        Analyze changes to a code snippet and determine required updates.

        Args:
            code_snippet: The stored code snippet
            current_content: Current file content from database

        Returns:
            CodeUpdate object if updates are needed, None otherwise
        """
        if not current_content:
            return CodeUpdate(
                code_id=code_snippet.id,
                new_start_line=0,
                new_end_line=0,
                should_remove=True,
            )

        current_lines = current_content.split("\n")

        # Check if the original content still exists in the file
        original_content_lines = (
            code_snippet.content.split("\n") if code_snippet.content else []
        )

        if not original_content_lines:
            # If we don't have original content, we can't track changes
            logger.warning(f"Code snippet {code_snippet.id} has no content to track")
            return None

        # Strip line numbers from original content for comparison
        # Content may be stored with line numbers like "1 | content"
        stripped_original_lines = []
        for line in original_content_lines:
            if " | " in line and line.split(" | ")[0].strip().isdigit():
                # Remove line number prefix
                stripped_line = " | ".join(line.split(" | ")[1:])
                stripped_original_lines.append(stripped_line)
            else:
                stripped_original_lines.append(line)

        logger.debug(f"Code snippet {code_snippet.id} stripped content:")
        for i, line in enumerate(stripped_original_lines[:3]):
            logger.debug(f"  {i + 1}: {line}")

        logger.debug(f"Current file content (first 5 lines):")
        for i, line in enumerate(current_lines[:5]):
            logger.debug(f"  {i + 1}: {line}")

        # Try to find the content in the current file
        new_location = self._find_content_in_file(
            stripped_original_lines, current_lines
        )

        logger.debug(f"Content search result for {code_snippet.id}: {new_location}")

        if new_location is None:
            # Content not found - check if it was partially modified
            fuzzy_location = self._find_similar_content(
                stripped_original_lines, current_lines
            )

            if fuzzy_location:
                # Content found but modified - update both location and content
                new_start, new_end = fuzzy_location
                new_content = "\n".join(current_lines[new_start - 1 : new_end])

                return CodeUpdate(
                    code_id=code_snippet.id,
                    new_start_line=new_start,
                    new_end_line=new_end,
                    new_content=new_content,
                )
            else:
                # Content completely removed or significantly changed
                return CodeUpdate(
                    code_id=code_snippet.id,
                    new_start_line=0,
                    new_end_line=0,
                    should_remove=True,
                )
        else:
            # Content found at new location
            new_start, new_end = new_location

            if new_start != code_snippet.start_line or new_end != code_snippet.end_line:
                # Line numbers changed
                return CodeUpdate(
                    code_id=code_snippet.id,
                    new_start_line=new_start,
                    new_end_line=new_end,
                )

        return None  # No changes needed

    def _find_content_in_file(
        self, content_lines: List[str], file_lines: List[str]
    ) -> Optional[Tuple[int, int]]:
        """
        Find exact content match in file and return (start_line, end_line).
        Line numbers are 1-indexed.
        """
        if not content_lines or not file_lines:
            return None

        content_length = len(content_lines)

        for i in range(len(file_lines) - content_length + 1):
            # Check if content matches at this position
            if file_lines[i : i + content_length] == content_lines:
                return (i + 1, i + content_length)  # 1-indexed

        return None

    def _find_similar_content(
        self,
        content_lines: List[str],
        file_lines: List[str],
        similarity_threshold: float = 0.2,
    ) -> Optional[Tuple[int, int]]:
        """
        Find similar content in file using fuzzy matching.
        Returns (start_line, end_line) if found, None otherwise.
        """
        if not content_lines or not file_lines:
            return None

        content_length = len(content_lines)
        best_match = None
        best_similarity = 0

        for i in range(len(file_lines) - content_length + 1):
            candidate_lines = file_lines[i : i + content_length]
            similarity = self._calculate_similarity(content_lines, candidate_lines)

            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = (i + 1, i + content_length)  # 1-indexed

        return best_match

    def _calculate_similarity(self, lines1: List[str], lines2: List[str]) -> float:
        """Calculate similarity between two sets of lines"""
        if len(lines1) != len(lines2):
            return 0.0

        if not lines1:
            return 1.0

        matching_lines = sum(
            1 for l1, l2 in zip(lines1, lines2) if l1.strip() == l2.strip()
        )
        return matching_lines / len(lines1)

    def _apply_code_snippet_update(
        self, code_snippet: CodeSnippet, update_info: CodeUpdate
    ) -> bool:
        """Apply updates to a code snippet"""
        try:
            # Update the code snippet in place
            code_snippet.start_line = update_info.new_start_line
            code_snippet.end_line = update_info.new_end_line

            if update_info.new_content is not None:
                code_snippet.content = update_info.new_content

            # Update the snippet in memory operations
            self.memory_ops.code_snippets[code_snippet.id] = code_snippet

            return True

        except Exception as e:
            logger.error(
                f"Error applying update to code snippet {code_snippet.id}: {e}"
            )
            return False

    def detect_line_changes(
        self, old_content: str, new_content: str
    ) -> List[LineChange]:
        """
        Detect line insertions and deletions between old and new content.
        This is a simplified diff algorithm for detecting basic changes.
        """
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        changes = []

        # Simple approach: compare line by line and detect insertions/deletions
        old_idx = 0
        new_idx = 0

        while old_idx < len(old_lines) and new_idx < len(new_lines):
            if old_lines[old_idx] == new_lines[new_idx]:
                # Lines match, move forward
                old_idx += 1
                new_idx += 1
            else:
                # Lines don't match, try to determine if it's insertion or deletion
                if (
                    old_idx + 1 < len(old_lines)
                    and old_lines[old_idx + 1] == new_lines[new_idx]
                ):
                    # Deletion in old content
                    changes.append(
                        LineChange(
                            line_number=old_idx + 1,
                            change_type="delete",
                            change_amount=1,
                        )
                    )
                    old_idx += 1
                elif (
                    new_idx + 1 < len(new_lines)
                    and old_lines[old_idx] == new_lines[new_idx + 1]
                ):
                    # Insertion in new content
                    changes.append(
                        LineChange(
                            line_number=new_idx + 1,
                            change_type="insert",
                            change_amount=1,
                        )
                    )
                    new_idx += 1
                else:
                    # Content changed, treat as both deletion and insertion
                    changes.append(
                        LineChange(
                            line_number=old_idx + 1,
                            change_type="delete",
                            change_amount=1,
                        )
                    )
                    changes.append(
                        LineChange(
                            line_number=new_idx + 1,
                            change_type="insert",
                            change_amount=1,
                        )
                    )
                    old_idx += 1
                    new_idx += 1

        # Handle remaining lines
        while old_idx < len(old_lines):
            changes.append(
                LineChange(
                    line_number=old_idx + 1, change_type="delete", change_amount=1
                )
            )
            old_idx += 1

        while new_idx < len(new_lines):
            changes.append(
                LineChange(
                    line_number=new_idx + 1, change_type="insert", change_amount=1
                )
            )
            new_idx += 1

        return changes

    def update_line_numbers_for_changes(
        self, code_snippets: List[CodeSnippet], line_changes: List[LineChange]
    ) -> List[CodeSnippet]:
        """
        Update line numbers for code snippets based on detected line changes.
        """
        updated_snippets = []

        for snippet in code_snippets:
            new_start = snippet.start_line
            new_end = snippet.end_line

            # Apply each line change
            for change in line_changes:
                if change.change_type == "insert":
                    # Lines were inserted
                    if change.line_number <= snippet.start_line:
                        # Insertion before snippet start
                        new_start += change.change_amount
                        new_end += change.change_amount
                    elif change.line_number <= snippet.end_line:
                        # Insertion within snippet
                        new_end += change.change_amount

                elif change.change_type == "delete":
                    # Lines were deleted
                    if change.line_number < snippet.start_line:
                        # Deletion before snippet start
                        new_start -= change.change_amount
                        new_end -= change.change_amount
                    elif change.line_number <= snippet.end_line:
                        # Deletion within snippet
                        new_end -= change.change_amount
                        # If deletion affects start of snippet, adjust start too
                        if change.line_number <= snippet.start_line:
                            new_start -= change.change_amount

            # Create updated snippet
            updated_snippet = CodeSnippet(
                id=snippet.id,
                file_path=snippet.file_path,
                start_line=max(1, new_start),  # Ensure line numbers are at least 1
                end_line=max(new_start, new_end),  # Ensure end >= start
                description=snippet.description,
                content=snippet.content,
                is_traced=snippet.is_traced,
                root_elements=snippet.root_elements,
                needs_tracing=snippet.needs_tracing,
                call_chain_summary=snippet.call_chain_summary,
                created_at=snippet.created_at,
            )

            updated_snippets.append(updated_snippet)

        return updated_snippets
