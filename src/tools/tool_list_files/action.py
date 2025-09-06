import os
import subprocess
from pathlib import Path
from typing import Iterator, Dict, Any, List

from models.agent import AgentAction
from utils.file_utils import should_ignore_file, should_ignore_directory
from graph.sqlite_client import SQLiteConnection
from tools.utils.project_utils import (
    auto_detect_project_from_paths,
    resolve_project_base_path,
)
from tools.utils.constants import SEARCH_CONFIG


def chunk_content(content: str, chunk_size: int = 600) -> List[Dict[str, Any]]:
    """
    Chunk content into smaller pieces based on line count.

    Args:
        content: The content to chunk
        chunk_size: Maximum lines per chunk

    Returns:
        List of chunk dictionaries with chunk_info
    """
    if not content:
        return []

    lines = content.split('\n')
    total_lines = len(lines)

    # If content is small enough, return as single chunk
    if total_lines <= chunk_size:
        return [{
            "data": content,
            "chunk_info": {
                "chunk_num": 1,
                "total_chunks": 1,
                "start_line": 1,
                "end_line": total_lines,
                "original_file_lines": total_lines
            }
        }]

    chunks = []
    total_chunks = (total_lines + chunk_size - 1) // chunk_size  # Ceiling division

    for i in range(total_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_lines)

        chunk_lines = lines[start_idx:end_idx]
        chunk_content = '\n'.join(chunk_lines)

        chunk_info = {
            "chunk_num": i + 1,
            "total_chunks": total_chunks,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "original_file_lines": total_lines
        }

        chunks.append({
            "data": chunk_content,
            "chunk_info": chunk_info
        })

    return chunks


def filter_ignored_paths(files_list: list, directory_path: str) -> list:
    """
    Filter out ignored files and directories from the list using file_utils.

    Args:
        files_list: List of file/directory paths
        directory_path: Base directory path

    Returns:
        Filtered list with ignored paths removed
    """
    filtered_list = []
    base_path = Path(directory_path)

    for item in files_list:
        is_directory = item.endswith("/")
        item_path = base_path / item.rstrip("/")

        # Skip if the item should be ignored
        if is_directory:
            if should_ignore_directory(item_path):
                continue
        else:
            if should_ignore_file(item_path):
                continue

        # Check if any parent directory in the path should be ignored
        path_parts = item.rstrip("/").split(os.sep)
        should_skip = False

        for i in range(
            len(path_parts) - 1
        ):  # Don't check the file itself, only parents
            partial_path = base_path / os.sep.join(path_parts[: i + 1])
            if should_ignore_directory(partial_path):
                should_skip = True
                break

        if not should_skip:
            filtered_list.append(item)

    return filtered_list


def execute_list_files_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute list files tool."""
    try:
        project_name = action.parameters.get("project_name")
        directory_path = action.parameters.get("path")
        recursive = action.parameters.get("recursive", False)
        ignore_patterns = action.parameters.get("ignore_patterns", True)

        # Auto-detect project name from absolute directory path if not provided
        if not project_name and directory_path:
            detection_result = auto_detect_project_from_paths([directory_path])
            if detection_result:
                project_name, matched_paths = detection_result

        # If no path is provided but project_name is available, use project's base path
        if not directory_path and project_name:
            project_base_path = resolve_project_base_path(project_name)
            if not project_base_path:
                raise Exception(f"Project '{project_name}' not found or has no path")

            directory_path = project_base_path
            yield {
                "type": "info",
                "message": f"Using project base path: {directory_path}",
                "tool_name": "list_files",
                "project_name": project_name,
            }

        # Fall back to current directory if still no path
        if not directory_path:
            directory_path = "."

        path = Path(directory_path)
        if not path.exists():
            raise Exception(f"Directory does not exist: {directory_path}")

        files_list = []

        if recursive == "true" or recursive == "True" or recursive is True:
            # Recursive listing using rg
            try:
                # First, get normal files (respects .gitignore)
                result = subprocess.run(
                    ["rg", "--files", directory_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Get relative paths for normal files
                for file_path in result.stdout.strip().split("\n"):
                    if file_path:  # Skip empty lines
                        rel_path = os.path.relpath(file_path, directory_path)
                        files_list.append(rel_path)

                # Now get .env* files specifically
                env_result = subprocess.run(
                    ["rg", "--files", "--glob", ".env*", directory_path],
                    capture_output=True,
                    text=True,
                    check=False,  # Don't fail if no .env files found
                )

                # Add .env* files to the list
                for file_path in env_result.stdout.strip().split("\n"):
                    if file_path:  # Skip empty lines
                        rel_path = os.path.relpath(file_path, directory_path)
                        if rel_path not in files_list:  # Avoid duplicates
                            files_list.append(rel_path)

                # Extract unique directories from all file paths
                dirs_set = set()
                all_files = result.stdout.strip().split(
                    "\n"
                ) + env_result.stdout.strip().split("\n")
                for file_path in all_files:
                    if file_path:
                        rel_path = os.path.relpath(file_path, directory_path)
                        dir_parts = rel_path.split(os.sep)[:-1]  # Remove filename
                        for i in range(len(dir_parts)):
                            dir_path = os.sep.join(dir_parts[: i + 1]) + "/"
                            dirs_set.add(dir_path)

                files_list.extend(sorted(dirs_set))

            except subprocess.CalledProcessError:
                # Fallback to os.walk if rg fails
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        rel_path = os.path.relpath(
                            os.path.join(root, file), directory_path
                        )
                        files_list.append(rel_path)
                    for dir in dirs:
                        rel_path = (
                            os.path.relpath(os.path.join(root, dir), directory_path)
                            + "/"
                        )
                        files_list.append(rel_path)
        else:
            # Top-level only - use rg with max-depth
            try:
                # First, get normal files (respects .gitignore)
                result = subprocess.run(
                    ["rg", "--files", "--max-depth", "1", directory_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Get just the filenames for top-level files
                for file_path in result.stdout.strip().split("\n"):
                    if file_path:  # Skip empty lines
                        rel_path = os.path.relpath(file_path, directory_path)
                        # Only include files that are directly in the directory (no subdirectories)
                        if os.sep not in rel_path:
                            files_list.append(rel_path)

                # Now get .env* files specifically at top level
                env_result = subprocess.run(
                    [
                        "rg",
                        "--files",
                        "--glob",
                        ".env*",
                        "--max-depth",
                        "0",
                        directory_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,  # Don't fail if no .env files found
                )

                # Add .env* files to the list
                for file_path in env_result.stdout.strip().split("\n"):
                    if file_path:  # Skip empty lines
                        rel_path = os.path.relpath(file_path, directory_path)
                        # Only include files that are directly in the directory (no subdirectories)
                        if os.sep not in rel_path and rel_path not in files_list:
                            files_list.append(rel_path)

                # Add directories manually for top-level
                for item in path.iterdir():
                    if item.is_dir():
                        files_list.append(item.name + "/")

            except subprocess.CalledProcessError:
                # Fallback to pathlib if rg fails
                for item in path.iterdir():
                    if item.is_file():
                        files_list.append(item.name)
                    elif item.is_dir():
                        files_list.append(item.name + "/")

        files_list.sort()

        # Apply ignore patterns to filter out unwanted files and directories (if enabled)
        if ignore_patterns:
            files_list = filter_ignored_paths(files_list, directory_path)

        # Convert to absolute path for tool status
        abs_directory_path = os.path.abspath(directory_path)

        # Check if no files were found and provide appropriate message
        if not files_list:
            data_message = f"No files or directories found in: {abs_directory_path}"
            if recursive:
                data_message += " (searched recursively)"
        else:
            data_message = "\n".join(files_list)

        # Add project header if project_name is available
        if project_name:
            data_message = f"PROJECT: {project_name}\n{data_message}"

        # Check if content needs chunking
        chunking_threshold = SEARCH_CONFIG["chunking_threshold"]
        chunk_size = SEARCH_CONFIG["chunk_size"]

        lines = data_message.split('\n')
        total_lines = len(lines)

        if total_lines <= chunking_threshold:
            # Content is small enough, return as-is
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
            # Content needs chunking
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
