"""List files tool with hidden directory support."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterator, List

from models.agent import AgentAction
from tools.utils.constants import SEARCH_CONFIG
from tools.utils.project_utils import (
    auto_detect_project_from_paths,
    resolve_project_base_path,
)
from utils.file_utils import should_ignore_directory, should_ignore_file


def chunk_content(content: str, chunk_size: int = 600) -> List[Dict[str, Any]]:
    """Chunk content into smaller pieces based on line count.

    Args:
        content: The content to chunk
        chunk_size: Maximum lines per chunk

    Returns:
        List of chunk dictionaries with chunk_info
    """
    if not content:
        return []

    lines = content.split("\n")
    total_lines = len(lines)

    if total_lines <= chunk_size:
        return [
            {
                "data": content,
                "chunk_info": {
                    "chunk_num": 1,
                    "total_chunks": 1,
                    "start_line": 1,
                    "end_line": total_lines,
                    "original_file_lines": total_lines,
                },
            }
        ]

    chunks = []
    total_chunks = (total_lines + chunk_size - 1) // chunk_size

    for i in range(total_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_lines)
        chunk_lines = lines[start_idx:end_idx]
        chunk_content = "\n".join(chunk_lines)

        chunk_info = {
            "chunk_num": i + 1,
            "total_chunks": total_chunks,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "original_file_lines": total_lines,
        }

        chunks.append({"data": chunk_content, "chunk_info": chunk_info})

    return chunks


class DirectoryScanner:
    """Handles directory scanning with hidden directory support."""

    HIDDEN_MARKER = " [hidden]"

    def __init__(self, base_path: str):
        """Initialize scanner with base path.

        Args:
            base_path: The base directory path to scan
        """
        self.base_path = Path(base_path).resolve()
        self.is_hidden_request = should_ignore_directory(self.base_path)

    def is_hidden_directory(self, path: str) -> bool:
        """Check if a directory is hidden.

        Args:
            path: The directory path to check

        Returns:
            True if the directory should be hidden, False otherwise
        """
        return should_ignore_directory(path)

    def scan_non_recursive(self) -> List[str]:
        """Scan directory non-recursively.

        Returns:
            List of files and directories in the top level
        """
        files_list = []

        # Get files using rg with max-depth
        try:
            result = subprocess.run(
                ["rg", "--files", "--max-depth", "1", str(self.base_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            for file_path in result.stdout.strip().split("\n"):
                if file_path:
                    abs_path = os.path.abspath(file_path)
                    # Only include files that are directly in the directory
                    if os.path.dirname(abs_path) == str(self.base_path):
                        files_list.append(abs_path)
        except subprocess.CalledProcessError:
            pass

        # Add .env* files at top level
        try:
            env_result = subprocess.run(
                [
                    "rg",
                    "--files",
                    "--glob",
                    ".env*",
                    "--max-depth",
                    "0",
                    str(self.base_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            for file_path in env_result.stdout.strip().split("\n"):
                if file_path:
                    abs_path = os.path.abspath(file_path)
                    if (
                        os.path.dirname(abs_path) == str(self.base_path)
                        and abs_path not in files_list
                    ):
                        files_list.append(abs_path)
        except Exception:
            pass

        # Add directories (including hidden ones)
        for item in self.base_path.iterdir():
            if item.is_dir():
                files_list.append(str(item.absolute()) + "/")

        return files_list

    def scan_recursive(self) -> List[str]:
        """Scan directory recursively with hidden directory handling.

        Returns:
            List of files and directories with hidden directories marked
        """
        files_list = []

        if not self.is_hidden_request:
            # Get regular files using rg
            try:
                result = subprocess.run(
                    ["rg", "--files", str(self.base_path)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                for file_path in result.stdout.strip().split("\n"):
                    if file_path:
                        abs_path = os.path.abspath(file_path)
                        files_list.append(abs_path)
            except subprocess.CalledProcessError:
                pass

            # Add hidden directories with [hidden] marker
            for root, dirs, _ in os.walk(str(self.base_path)):
                dirs_to_remove = []
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    abs_dir_path = os.path.abspath(dir_path)
                    if self.is_hidden_directory(abs_dir_path):
                        files_list.append(abs_dir_path + "/" + self.HIDDEN_MARKER)
                        dirs_to_remove.append(dir_name)

                # Remove hidden dirs to prevent recursion
                for dir_name in dirs_to_remove:
                    dirs.remove(dir_name)

            # Add .env* files
            try:
                env_result = subprocess.run(
                    ["rg", "--files", "--glob", ".env*", str(self.base_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                for file_path in env_result.stdout.strip().split("\n"):
                    if file_path:
                        abs_path = os.path.abspath(file_path)
                        if abs_path not in files_list:
                            files_list.append(abs_path)
            except Exception:
                pass

            # Add regular parent directories
            self._add_parent_directories(files_list)

        else:
            # Request is for a hidden directory - include everything
            for root, dirs, files in os.walk(str(self.base_path)):
                for file in files:
                    abs_path = os.path.abspath(os.path.join(root, file))
                    files_list.append(abs_path)
                for dir_name in dirs:
                    abs_path = os.path.abspath(os.path.join(root, dir_name)) + "/"
                    files_list.append(abs_path)

        return files_list

    def _add_parent_directories(self, files_list: List[str]) -> None:
        """Add parent directories for all files, skipping hidden ones.

        Args:
            files_list: List of files to process, modified in place
        """
        dirs_set = set()

        for file_path in files_list:
            # Skip hidden directories (already added with marker)
            if file_path.endswith(self.HIDDEN_MARKER):
                continue

            abs_file_path = os.path.abspath(file_path)
            dir_path = os.path.dirname(abs_file_path)

            # Walk up the directory tree
            while dir_path != os.path.dirname(dir_path) and dir_path.startswith(
                str(self.base_path)
            ):
                if dir_path != str(self.base_path):
                    # Only add if not a hidden directory
                    if not self.is_hidden_directory(dir_path):
                        dirs_set.add(dir_path + "/")
                dir_path = os.path.dirname(dir_path)

        files_list.extend(sorted(dirs_set))


class ResultFilter:
    """Handles filtering of scan results."""

    HIDDEN_MARKER = " [hidden]"

    def __init__(self, base_path: str):
        """Initialize filter with base path.

        Args:
            base_path: The base directory path
        """
        self.base_path = Path(base_path).resolve()
        self.is_hidden_request = should_ignore_directory(self.base_path)

    def filter_paths(self, files_list: List[str]) -> List[str]:
        """Filter paths according to ignore patterns and hidden directory rules.

        Args:
            files_list: List of file and directory paths to filter

        Returns:
            Filtered list with appropriate items included
        """
        filtered_list = []

        for item in files_list:
            # Handle hidden marker
            has_hidden_marker = item.endswith(self.HIDDEN_MARKER)
            clean_item = item.replace(self.HIDDEN_MARKER, "")

            is_directory = clean_item.endswith("/")
            item_path = Path(clean_item.rstrip("/"))

            # Apply filtering rules
            if self._should_include_item(item_path, is_directory):
                filtered_list.append(item)

        return filtered_list

    def _should_include_item(self, item_path: Path, is_directory: bool) -> bool:
        """Determine if an item should be included in the results.

        Args:
            item_path: The path to the item
            is_directory: Whether the item is a directory

        Returns:
            True if the item should be included, False otherwise
        """
        # Skip ignored files
        if not is_directory and should_ignore_file(item_path):
            return False

        # Handle directory inclusion rules
        if is_directory and should_ignore_directory(item_path):
            # Always include the requested directory itself
            if item_path.resolve() == self.base_path:
                return True

            # Include hidden directories in non-hidden requests
            if not self.is_hidden_request:
                return True

            # Skip hidden directories when not specifically requested
            return False

        # Check parent directory hierarchy
        return not self._has_ignored_parent(item_path, is_directory)

    def _has_ignored_parent(self, item_path: Path, is_directory: bool) -> bool:
        """Check if item has an ignored parent directory.

        Args:
            item_path: The path to the item
            is_directory: Whether the item is a directory

        Returns:
            True if the item has an ignored parent, False otherwise
        """
        current_path = item_path.parent if not is_directory else item_path

        while current_path != current_path.parent and current_path != self.base_path:
            if should_ignore_directory(current_path):
                # Allow hidden directories themselves but not their contents
                if not self.is_hidden_request and is_directory:
                    return current_path.resolve() != item_path.resolve()
                return True
            current_path = current_path.parent

        return False


def execute_list_files_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute list files tool with hidden directory support."""
    try:
        # Get parameters
        project_name = action.parameters.get("project_name")
        directory_path = action.parameters.get("path")
        recursive = action.parameters.get("recursive", False)
        ignore_patterns = action.parameters.get("ignore_patterns", True)

        # Resolve project and directory
        directory_path = _resolve_directory_path(directory_path, project_name)

        # Initialize scanner and filter
        scanner = DirectoryScanner(directory_path)
        result_filter = ResultFilter(directory_path)

        # Scan directory
        if recursive in ("true", "True") or recursive is True:
            files_list = scanner.scan_recursive()
        else:
            files_list = scanner.scan_non_recursive()

        files_list.sort()

        # Apply filtering if enabled
        if ignore_patterns:
            files_list = result_filter.filter_paths(files_list)

        # Prepare result data
        abs_directory_path = os.path.abspath(directory_path)
        data_message = _format_results(files_list, abs_directory_path, project_name)

        # Check if content needs chunking
        chunking_threshold = SEARCH_CONFIG["chunking_threshold"]
        chunk_size = SEARCH_CONFIG["chunk_size"]

        lines = data_message.split("\n")
        total_lines = len(lines)

        if total_lines <= chunking_threshold:
            # Return as single chunk
            yield {
                "type": "tool_use",
                "directory": abs_directory_path,
                "recursive": recursive,
                "ignore_patterns": ignore_patterns,
                "count": len(files_list),
                "data": data_message,
                "tool_name": "list_files",
                "project_name": project_name,
            }
        else:
            # Return chunked content
            chunks = chunk_content(data_message, chunk_size)
            for chunk in chunks:
                yield {
                    "type": "tool_use",
                    "directory": abs_directory_path,
                    "recursive": recursive,
                    "ignore_patterns": ignore_patterns,
                    "count": len(files_list),
                    "data": chunk["data"],
                    "tool_name": "list_files",
                    "project_name": project_name,
                    "chunk_info": chunk["chunk_info"],
                }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to list files: {str(e)}",
            "tool_name": "list_files",
            "project_name": action.parameters.get("project_name"),
        }


def _resolve_directory_path(
    directory_path: str | None, project_name: str | None
) -> str:
    """Resolve the directory path, handling project auto-detection."""
    # Handle case where both project name and directory path are provided
    if project_name and directory_path:
        project_base_path = resolve_project_base_path(project_name)
        if not project_base_path:
            raise Exception(f"Project '{project_name}' not found or has no path")
        # Join the project base path with the relative directory path
        directory_path = str(Path(project_base_path) / Path(directory_path))
    else:
        # Auto-detect project from directory path if not provided
        if not project_name and directory_path:
            detection_result = auto_detect_project_from_paths([directory_path])
            if detection_result:
                project_name, matched_paths = detection_result

        # Use project base path if no directory specified
        if not directory_path and project_name:
            project_base_path = resolve_project_base_path(project_name)
            if not project_base_path:
                raise Exception(f"Project '{project_name}' not found or has no path")
            directory_path = project_base_path

        # Fall back to current directory
        if not directory_path:
            directory_path = "."

    path = Path(directory_path)
    if not path.exists():
        raise Exception(f"Directory does not exist: {directory_path}")

    return directory_path


def _format_results(
    files_list: List[str], abs_directory_path: str, project_name: str | None
) -> str:
    """Format the results for output."""
    if not files_list:
        data_message = f"No files or directories found in: {abs_directory_path}"
    else:
        data_message = "\n".join(files_list)

    # Add project header if available
    if project_name:
        data_message = f"PROJECT: {project_name}\n{data_message}"

    return data_message
