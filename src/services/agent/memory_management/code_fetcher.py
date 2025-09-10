"""
Code Fetcher Module

Handles fetching code content from database and file operations.
"""

from pathlib import Path
from typing import Any, Optional

from loguru import logger

from graph.graph_operations import GraphOperations

from .query_cache import get_query_cache


class CodeFetcher:
    """Handles code fetching operations from database"""

    def __init__(self):
        self.graph_ops = GraphOperations()

    def fetch_code_from_file(
        self, file_path: str, start_line: int, end_line: int
    ) -> str:
        """
        Fetch code content from file using database query and line filtering.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            str: Filtered code content
        """
        try:
            # Use graph_operations for all database operations

            # Get file_id first using graph_operations
            file_id = self.graph_ops._get_file_id_by_path(file_path)
            if not file_id:
                logger.warning(f"File not found in database: {file_path}")
                return ""

            # Use graph_operations to get file content
            file_data = self.graph_ops.resolve_file(file_id)
            if not file_data:
                logger.warning(f"No file data found for file_id: {file_id}")
                return ""

            # Extract code content
            raw_code = file_data.get("content", "")

            from tools.utils.code_processing_utils import (
                process_code_with_line_filtering,
            )

            filtered_result = process_code_with_line_filtering(
                code_snippet=raw_code,
                file_start_line=1,
                start_line=start_line,
                end_line=end_line,
            )

            # Return the filtered code without truncation
            return filtered_result.get("code", "")

        except Exception as e:
            logger.error(f"Error fetching code from file {file_path}: {str(e)}")
            return ""

    def _fix_file_path(self, file_path: str) -> str:
        """
        Fix file path by prepending current directory if needed.
        Handles cases where path might duplicate directory names.

        Args:
            file_path: Original file path

        Returns:
            str: Fixed file path with current directory if needed
        """
        try:
            current_dir = Path.cwd()
            file_path_obj = Path(file_path)

            # If it's already an absolute path, use as is
            if file_path_obj.is_absolute():
                return str(file_path_obj)

            # Check if file path starts with current directory
            try:
                # If file_path is relative to current dir, this will work
                file_path_obj.relative_to(current_dir)
                # Path is already relative to current dir, use as is
                return str(file_path_obj)
            except ValueError:
                # Path is not relative to current dir, need to fix it

                # Check if the file path starts with the last component of current_dir
                # to avoid duplication like server/server/src/index.js
                current_dir_name = current_dir.name
                file_path_parts = Path(file_path).parts

                if file_path_parts and file_path_parts[0] == current_dir_name:
                    # The file path already starts with the current directory name
                    # Try to construct path by going up one level and then adding the file path
                    parent_dir = current_dir.parent
                    fixed_path = parent_dir / file_path
                    logger.debug(
                        f"Fixed file path (avoiding duplication): {file_path} -> {fixed_path}"
                    )
                    return str(fixed_path)
                else:
                    # Normal case: concatenate with current dir
                    fixed_path = current_dir / file_path
                    logger.debug(f"Fixed file path: {file_path} -> {fixed_path}")
                    return str(fixed_path)

        except Exception as e:
            logger.error(f"Error fixing file path {file_path}: {str(e)}")
            return file_path  # Return original path if fixing fails

    def _try_get_file_content(self, file_path: str) -> list:
        """
        Try to get file content from database for a given file path.

        Args:
            file_path: File path to try

        Returns:
            List of results from database query, empty if not found
        """
        try:
            # Get file_id first using graph_operations
            file_id = self.graph_ops._get_file_id_by_path(file_path)
            if not file_id:
                logger.warning(f"File not found in database: {file_path}")
                return []

            # Use graph_operations to get file content
            file_data = self.graph_ops.resolve_file(file_id)
            if not file_data:
                logger.warning(f"No file data found for file_id: {file_id}")
                return []

            # Convert to the expected format for backward compatibility
            results = [
                {
                    "content": file_data.get("content", ""),
                    "file_path": file_data.get("file_path", file_path),
                    "language": file_data.get("language", ""),
                    "project_name": file_data.get("project_name", ""),
                    "file_id": file_id,
                }
            ]

            return results

        except Exception as e:
            logger.error(f"Error trying to get file content for {file_path}: {str(e)}")
            return []

    def _get_fallback_paths(self, original_path: str, fixed_path: str) -> list:
        """
        Generate fallback paths to try if the main path doesn't work.

        Args:
            original_path: Original file path from input
            fixed_path: Path after fixing

        Returns:
            List of fallback paths to try
        """
        fallback_paths = []

        try:
            from pathlib import Path

            current_dir = Path.cwd()

            # If the fixed path has duplicated directory names, try removing one level
            fixed_path_obj = Path(fixed_path)
            if fixed_path_obj.is_absolute():
                parts = fixed_path_obj.parts
                # Look for consecutive duplicate directory names
                for i in range(len(parts) - 1):
                    if parts[i] == parts[i + 1]:
                        # Found duplicate, create path without one of them
                        new_parts = parts[:i] + parts[i + 1 :]
                        fallback_path = str(Path(*new_parts))
                        fallback_paths.append(fallback_path)
                        logger.debug(
                            f"Generated fallback path by removing duplicate '{parts[i]}': {fallback_path}"
                        )
                        break

            # Try the original path as-is (in case it was already correct)
            if original_path != fixed_path:
                fallback_paths.append(original_path)

            # Try with current directory as base (different approach)
            if not Path(original_path).is_absolute():
                simple_concat = str(current_dir / original_path)
                if simple_concat not in [fixed_path] + fallback_paths:
                    fallback_paths.append(simple_concat)

        except Exception as e:
            logger.error(f"Error generating fallback paths: {str(e)}")

        return fallback_paths
