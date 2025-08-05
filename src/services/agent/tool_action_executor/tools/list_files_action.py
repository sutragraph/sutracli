import os
import subprocess
from pathlib import Path
from typing import Iterator, Dict, Any

from services.agent.agentic_core import AgentAction

def execute_list_files_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute list files tool."""
    try:
        directory_path = action.parameters.get("path", ".")
        recursive = action.parameters.get("recursive", False)

        path = Path(directory_path)
        if not path.exists():
            yield {
                "type": "tool_error",
                "error": f"Directory does not exist: {directory_path}",
                "tool_name": "list_files"
            }
            return

        files_list = []

        if recursive:
            # Recursive listing using rg
            try:
                # First, get normal files (respects .gitignore)
                result = subprocess.run(
                    ['rg', '--files', directory_path],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Get relative paths for normal files
                for file_path in result.stdout.strip().split('\n'):
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
                            dir_path = os.sep.join(dir_parts[:i+1]) + "/"
                            dirs_set.add(dir_path)

                files_list.extend(sorted(dirs_set))

            except subprocess.CalledProcessError:
                # Fallback to os.walk if rg fails
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), directory_path)
                        files_list.append(rel_path)
                    for dir in dirs:
                        rel_path = os.path.relpath(os.path.join(root, dir), directory_path) + "/"
                        files_list.append(rel_path)
        else:
            # Top-level only - use rg with max-depth
            try:
                # First, get normal files (respects .gitignore)
                result = subprocess.run(
                    ['rg', '--files', '--max-depth', '1', directory_path],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Get just the filenames for top-level files
                for file_path in result.stdout.strip().split('\n'):
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
                        "1",
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

        # Convert to absolute path for tool status
        abs_directory_path = os.path.abspath(directory_path)

        # Check if no files were found and provide appropriate message
        if not files_list:
            data_message = f"No files or directories found in: {abs_directory_path}"
            if recursive:
                data_message += " (searched recursively)"
        else:
            data_message = "\n".join(files_list)

        yield {
            "type": "tool_use",
            "directory": abs_directory_path,
            "recursive": recursive,
            "count": len(files_list),
            "data": data_message,
            "tool_name": "list_files",
        }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to list files: {str(e)}",
            "tool_name": "list_files"
        }
