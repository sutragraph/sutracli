"""
Code Fetcher Module

Handles fetching code content from database and file operations.
"""

from typing import Optional, Any
from pathlib import Path
from loguru import logger
from src.queries.agent_queries import GET_CODE_FROM_FILE


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

            # Execute database query to get file content
            cursor = self.db_connection.connection.cursor()
            params = {"file_path": fixed_file_path, "project_id": None}
            cursor.execute(GET_CODE_FROM_FILE, params)

            results = cursor.fetchall()
            if not results:
                logger.warning(f"No code found for file path: {file_path}")
                return ""

            # Get the first result (should be the File node)
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

            from src.services.agent.tool_action_executor.utils.code_processing_utils import (
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

        Args:
            file_path: Original file path

        Returns:
            str: Fixed file path with current directory if needed
        """
        try:
            current_dir = Path.cwd()
            file_path_obj = Path(file_path)

            # Check if file path starts with current directory
            try:
                # If file_path is relative to current dir, this will work
                file_path_obj.relative_to(current_dir)
                # Path is already relative to current dir, use as is
                return str(file_path_obj)
            except ValueError:
                # Path is not relative to current dir, concatenate with current dir
                fixed_path = current_dir / file_path
                logger.debug(f"Fixed file path: {file_path} -> {fixed_path}")
                return str(fixed_path)

        except Exception as e:
            logger.error(f"Error fixing file path {file_path}: {str(e)}")
            return file_path  # Return original path if fixing fails
