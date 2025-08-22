import subprocess
import re
from pathlib import Path
from typing import Iterator, Dict, Any
from loguru import logger
from models.agent import AgentAction
from graph.sqlite_client import SQLiteConnection
from tools.utils.project_utils import (
    auto_detect_project_from_paths,
    resolve_project_base_path,
)


def execute_search_keyword_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute search keyword tool using ripgrep."""
    try:
        project_name = action.parameters.get("project_name")
        keyword = action.parameters.get("keyword", "")
        file_paths_str = action.parameters.get("file_paths", "")
        before_lines = int(action.parameters.get("before_lines", 0))
        after_lines = int(action.parameters.get("after_lines", 10))
        case_sensitive = (
            str(action.parameters.get("case_sensitive", "false")).lower() == "true"
        )
        use_regex = str(action.parameters.get("regex", "false")).lower() == "true"

        if not keyword:
            raise Exception("Missing required parameter: keyword")

        # Auto-detect project name from absolute file paths if not provided
        if not project_name and file_paths_str:
            raw_paths = [
                path.strip() for path in file_paths_str.split(",") if path.strip()
            ]
            detection_result = auto_detect_project_from_paths(raw_paths)
            if detection_result:
                project_name, matched_paths = detection_result

        # Validate that either file_paths or project_name is provided
        if not file_paths_str and not project_name:
            raise Exception("Either file_paths or project_name must be provided")

        # Handle path resolution based on priority and relative/absolute paths
        project_base_path = None

        # Get project base path if project_name is provided
        if project_name:
            project_base_path = resolve_project_base_path(project_name)
            if not project_base_path:
                raise Exception(f"Project '{project_name}' not found or has no path")

        # Priority logic for path resolution
        if not file_paths_str and project_name:
            # Case 1: Only project_name provided - use project base path
            file_paths_str = project_base_path
            yield {
                "type": "info",
                "message": f"Using project base path: {project_base_path}",
                "tool_name": "search_keyword",
                "project_name": project_name,
            }
        elif file_paths_str and project_name and project_base_path:
            # Case 2: Both provided - check if file_paths are relative and resolve against project base
            raw_paths = [
                path.strip() for path in file_paths_str.split(",") if path.strip()
            ]
            resolved_paths = []

            for path in raw_paths:
                path_obj = Path(path)
                if path_obj.is_absolute():
                    # Absolute path - use as-is
                    resolved_paths.append(path)
                else:
                    # Relative path - resolve against project base path
                    resolved_path = str(Path(project_base_path) / path)
                    resolved_paths.append(resolved_path)

            file_paths_str = ", ".join(resolved_paths)
            yield {
                "type": "info",
                "message": f"Resolved relative paths against project base: {project_base_path}",
                "tool_name": "search_keyword",
                "project_name": project_name,
            }
        # Case 3: Only file_paths provided - use as-is (relative paths resolved against current directory)

        # Parse and validate file paths
        file_paths = []
        invalid_paths = []
        if file_paths_str:
            raw_paths = [
                path.strip() for path in file_paths_str.split(",") if path.strip()
            ]
            for path in raw_paths:
                path_obj = Path(path)

                # Check if path exists (can be file or directory)
                if path_obj.exists():
                    file_paths.append(path)
                else:
                    # Try relative to current directory
                    abs_path = Path.cwd() / path
                    if abs_path.exists():
                        file_paths.append(path)  # Keep original relative path
                    else:
                        invalid_paths.append(path)

            # Report invalid paths if any
            if invalid_paths:
                yield {
                    "type": "tool_warning",
                    "warning": f"Skipping non-existent paths: {', '.join(invalid_paths)}",
                    "tool_name": "search_keyword",
                    "project_name": project_name,
                }

        # Validate regex if needed
        if use_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                raise Exception(f"Invalid regex pattern: {str(e)}")

        def build_base_cmd():
            """Build base ripgrep command with common options."""
            cmd = ["rg"]

            # Add context lines
            if before_lines > 0:
                cmd.extend(["-B", str(before_lines)])
            if after_lines > 0:
                cmd.extend(["-A", str(after_lines)])

            # Case sensitivity
            if not case_sensitive:
                cmd.append("-i")

            # Line numbers
            cmd.append("-n")

            # Add keyword
            if use_regex:
                cmd.append(keyword)
            else:
                cmd.extend(["-F", keyword])  # Fixed string search

            return cmd

        all_results = []
        commands_run = []

        # Search in normal files (respects .gitignore)
        cmd1 = build_base_cmd()
        if file_paths:
            # Add each file path to the command
            cmd1.extend(file_paths)

        # Debug: Log the command being executed
        cmd1_str = " ".join(cmd1)
        logger.debug(f"🔍 Executing ripgrep command: {cmd1_str}")

        result1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=".")

        # Debug: Log command result
        logger.debug(f"🔍 Command exit code: {result1.returncode}")
        if result1.stderr:
            logger.debug(f"🔍 Command stderr: {result1.stderr}")
        logger.debug(
            f"🔍 Command stdout length: {len(result1.stdout) if result1.stdout else 0} chars"
        )

        # Check for ripgrep errors (exit codes > 1 indicate errors)
        if result1.returncode > 1:
            raise Exception(
                f"Ripgrep error (exit code {result1.returncode}): {result1.stderr}"
            )

        if result1.returncode == 0:
            all_results.append(result1.stdout)
        commands_run.append(cmd1_str)

        # Search in .env* files specifically (if no specific file paths given)
        if not file_paths:
            cmd2 = build_base_cmd()
            cmd2.extend(["--glob", ".env*"])

            cmd2_str = " ".join(cmd2)
            logger.debug(f"🔍 Executing .env search command: {cmd2_str}")

            result2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=".")

            logger.debug(f"🔍 .env search exit code: {result2.returncode}")
            if result2.stderr:
                logger.debug(f"🔍 .env search stderr: {result2.stderr}")

            # Check for errors in .env search too
            if result2.returncode > 1:
                yield {
                    "type": "tool_warning",
                    "warning": f"Error searching .env files (exit code {result2.returncode}): {result2.stderr}",
                    "tool_name": "search_keyword",
                    "project_name": project_name,
                }
            elif result2.returncode == 0:
                all_results.append(result2.stdout)
            commands_run.append(cmd2_str)

        # Combine results
        combined_output = "\n".join(all_results).strip()

        logger.debug(
            f"🔍 Combined output length: {len(combined_output) if combined_output else 0} chars"
        )

        if combined_output:
            # Project header will be added by delivery system
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_paths": (
                    file_paths if file_paths else "all files (including .env*)"
                ),
                "matches_found": True,
                "data": combined_output,
                "command": " | ".join(commands_run),
                "project_name": project_name,
            }
        else:
            no_matches_msg = f"No matches found for '{keyword}'"
            # Project header will be added by delivery system
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_paths": (
                    file_paths if file_paths else "all files (including .env*)"
                ),
                "matches_found": False,
                "data": no_matches_msg,
                "command": " | ".join(commands_run),
                "project_name": project_name,
            }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to search keyword: {str(e)}",
            "tool_name": "search_keyword",
            "project_name": action.parameters.get("project_name"),
        }
