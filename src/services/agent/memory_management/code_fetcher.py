"""
Code Fetcher Module

Handles fetching code content from database and file operations.
"""

from typing import Optional, Any
from pathlib import Path
from loguru import logger
from queries.agent_queries import GET_CODE_FROM_FILE
from .query_cache import get_query_cache


class CodeFetcher:
    """Handles code fetching operations from database"""

    def __init__(self, db_connection: Optional[Any] = None):
        self.db_connection = db_connection

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
            # Check if database connection is available
            if self.db_connection is None:
                logger.warning(
                    "Database connection not available, returning empty code content"
                )
                return ""

            # Check if required imports are available
            if GET_CODE_FROM_FILE is None:
                logger.warning("Required imports not available for code fetching")
                return ""

            # Fix file path - prepend current directory if path doesn't start with current dir
            fixed_file_path = self._fix_file_path(file_path)

            # Try to get file content with the fixed path
            results = self._try_get_file_content(fixed_file_path)

            # If no results found, try fallback paths
            if not results:
                fallback_paths = self._get_fallback_paths(file_path, fixed_file_path)
                for fallback_path in fallback_paths:
                    logger.debug(f"Trying fallback path: {fallback_path}")
                    results = self._try_get_file_content(fallback_path)
                    if results:
                        fixed_file_path = fallback_path
                        break

            if not results:
                logger.warning(f"No code found for file path: {file_path}")
                return ""

            # Get the first result (should be the File node)
            # We need to execute a query to get column descriptions
            cursor = self.db_connection.connection.cursor()
            params = {"file_path": fixed_file_path, "project_id": None}
            cursor.execute(GET_CODE_FROM_FILE, params)
            cursor.fetchall()  # Fetch to get column descriptions

            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, results[0]))

            # Extract code snippet and file start line
            raw_code = result.get("code_snippet", "")
            lines_data = result.get("lines", "[]")

            # Parse lines data to get file start line
            try:
                import json

                lines_list = json.loads(lines_data) if lines_data else [1]
                file_start_line = lines_list[0] if lines_list else 1
                
                # Fix: Ensure file_start_line is never 0 (line numbers should be 1-indexed)
                if file_start_line <= 0:
                    logger.warning(f"Database returned invalid file_start_line: {file_start_line}, correcting to 1")
                    file_start_line = 1
                
                logger.debug(f"File: {file_path}, Lines data: {lines_data}")
                logger.debug(f"Parsed lines_list: {lines_list}")
                logger.debug(f"Corrected file_start_line: {file_start_line}")
                logger.debug(f"Requested range: {start_line}-{end_line}")
                
            except (json.JSONDecodeError, IndexError):
                file_start_line = 1
                logger.debug(f"Failed to parse lines data, using default file_start_line: 1")

            from services.agent.tool_action_executor.utils.code_processing_utils import (
                process_code_with_line_filtering,
            )

            filtered_result = process_code_with_line_filtering(
                code_snippet=raw_code,
                file_start_line=file_start_line,
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
                    logger.debug(f"Fixed file path (avoiding duplication): {file_path} -> {fixed_path}")
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
            # Check cache first
            cache = get_query_cache()
            cache_key_params = {"file_path": file_path, "project_id": None}
            cached_results = cache.get(GET_CODE_FROM_FILE, cache_key_params)

            # Execute database query to get file content
            cursor = self.db_connection.connection.cursor()
            params = {"file_path": file_path, "project_id": None}
            cursor.execute(GET_CODE_FROM_FILE, params)

            if cached_results is not None:
                results = cached_results
                logger.debug(f"Using cached results for file: {file_path}")
                # Still need to call fetchall() to get column descriptions
                cursor.fetchall()
            else:
                results = cursor.fetchall()
                if results:
                    # Cache the results
                    cache.set(GET_CODE_FROM_FILE, cache_key_params, results)

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
                        new_parts = parts[:i] + parts[i+1:]
                        fallback_path = str(Path(*new_parts))
                        fallback_paths.append(fallback_path)
                        logger.debug(f"Generated fallback path by removing duplicate '{parts[i]}': {fallback_path}")
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
