import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterator, List

from loguru import logger

from models.agent import AgentAction
from tools.utils.constants import SEARCH_CONFIG
from tools.utils.project_utils import (
    auto_detect_project_from_paths,
    resolve_project_base_path,
)
from utils.ignore_patterns import IGNORE_DIRECTORY_PATTERNS, IGNORE_FILE_PATTERNS


def group_matches_by_file(ripgrep_output: str) -> str:
    """
    Group ripgrep matches by file path to avoid repeating file paths on every line.

    Args:
        ripgrep_output: Raw ripgrep output with file:line:content format

    Returns:
        Formatted output with matches grouped by file
    """
    if not ripgrep_output.strip():
        return ripgrep_output

    # Dictionary to store matches grouped by file
    file_matches = {}

    lines = ripgrep_output.split("\n")
    logger.debug(f"🔍 Processing {len(lines)} lines from ripgrep output")

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        # Handle ripgrep separator lines between match groups
        if line == "--":
            # Add spacing between match groups - find the last file that had content
            if file_matches:
                last_file = list(file_matches.keys())[-1]
                file_matches[last_file].append("")
            continue

        # More robust parsing: ripgrep format is always file<separator>line_number<separator>content
        # where separator is ':' for matches and '-' for context lines
        # We need to find the SECOND occurrence of the separator (after line number)

        file_path = None
        line_number = None
        content = None

        # Try matching line format first (file:line:content)
        if ":" in line:
            # Find all colon positions
            colon_indices = [i for i, c in enumerate(line) if c == ":"]
            if len(colon_indices) >= 2:
                # The line number should be between the first and second colon
                # and should be all digits
                for i in range(len(colon_indices) - 1):
                    potential_file = line[: colon_indices[i]]
                    potential_line_num = line[
                        colon_indices[i] + 1 : colon_indices[i + 1]
                    ]

                    # Check if this looks like a line number (all digits)
                    if potential_line_num.strip().isdigit():
                        file_path = potential_file
                        line_number = potential_line_num
                        content = line[colon_indices[i + 1] + 1 :]
                        break

        # Try context line format (file-line-content)
        if file_path is None and "-" in line:
            # Find all dash positions
            dash_indices = [i for i, c in enumerate(line) if c == "-"]
            if len(dash_indices) >= 2:
                # The line number should be between the first and second dash
                # and should be all digits
                for i in range(len(dash_indices) - 1):
                    potential_file = line[: dash_indices[i]]
                    potential_line_num = line[dash_indices[i] + 1 : dash_indices[i + 1]]

                    # Check if this looks like a line number (all digits)
                    if potential_line_num.strip().isdigit():
                        file_path = potential_file
                        line_number = potential_line_num
                        content = line[dash_indices[i + 1] + 1 :]
                        break

        # Process if we successfully parsed the line
        if file_path is not None and line_number is not None and content is not None:
            # Initialize file entry if it doesn't exist
            if file_path not in file_matches:
                file_matches[file_path] = []

            # Format the line
            formatted_line = f"{line_number.strip()} | {content}"
            file_matches[file_path].append(formatted_line)
        else:
            logger.debug(f"🔍 Failed to parse line: '{line}'")

    # Format grouped output
    grouped_lines = []
    for file_path, matches in file_matches.items():
        grouped_lines.append(f"{file_path}:")
        for match in matches:
            if match == "":  # Empty line for spacing
                grouped_lines.append("")
            else:
                grouped_lines.append(f"  {match}")
        grouped_lines.append("")  # Empty line between files

    # Remove the last empty line
    if grouped_lines and grouped_lines[-1] == "":
        grouped_lines.pop()

    return "\n".join(grouped_lines)


def chunk_grouped_content(content: str, chunk_size: int = 600) -> List[Dict[str, Any]]:
    """
    Chunk grouped content while respecting file group boundaries.
    Never splits a file's matches across different chunks.

    Args:
        content: The grouped content to chunk
        chunk_size: Maximum lines per chunk

    Returns:
        List of chunk dictionaries with chunk_info
    """
    if not content:
        return []

    lines = content.split("\n")
    total_lines = len(lines)

    # If content is small enough, return as single chunk
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

    # Find file group boundaries (lines that don't start with space and end with :)
    file_boundaries = []
    for i, line in enumerate(lines):
        if line and not line.startswith("  ") and line.endswith(":"):
            file_boundaries.append(i)

    # Add the end of content as a boundary
    file_boundaries.append(total_lines)

    # Group lines into file groups
    file_groups = []
    for i in range(len(file_boundaries) - 1):
        start_idx = file_boundaries[i]
        end_idx = file_boundaries[i + 1]

        # Include empty line after group if it exists
        if end_idx < total_lines and not lines[end_idx - 1].strip():
            group_lines = lines[start_idx:end_idx]
        else:
            group_lines = lines[start_idx:end_idx]

        file_groups.append(
            {
                "lines": group_lines,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "line_count": len(group_lines),
            }
        )

    # Create chunks respecting file group boundaries
    chunks = []
    current_chunk_lines = []
    current_chunk_start = 1
    current_chunk_line_count = 0

    for group in file_groups:
        # Check if adding this group would exceed chunk size
        if (
            current_chunk_line_count + group["line_count"] > chunk_size
            and current_chunk_lines
        ):
            # Save current chunk
            chunk_content = "\n".join(current_chunk_lines)
            chunks.append(
                {
                    "data": chunk_content,
                    "lines": current_chunk_lines.copy(),
                    "start_line": current_chunk_start,
                    "line_count": current_chunk_line_count,
                }
            )

            # Start new chunk with current group
            current_chunk_lines = group["lines"].copy()
            current_chunk_start = group["start_line"]
            current_chunk_line_count = group["line_count"]
        else:
            # Add group to current chunk
            if not current_chunk_lines:
                current_chunk_start = group["start_line"]
            current_chunk_lines.extend(group["lines"])
            current_chunk_line_count += group["line_count"]

    # Don't forget the last chunk
    if current_chunk_lines:
        chunk_content = "\n".join(current_chunk_lines)
        chunks.append(
            {
                "data": chunk_content,
                "lines": current_chunk_lines,
                "start_line": current_chunk_start,
                "line_count": current_chunk_line_count,
            }
        )

    # Add chunk info
    total_chunks = len(chunks)
    result_chunks = []

    for i, chunk in enumerate(chunks):
        chunk_info = {
            "chunk_num": i + 1,
            "total_chunks": total_chunks,
            "start_line": chunk["start_line"],
            "end_line": chunk["start_line"] + chunk["line_count"] - 1,
            "original_file_lines": total_lines,
        }

        result_chunks.append({"data": chunk["data"], "chunk_info": chunk_info})

    return result_chunks


def execute_search_keyword_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute search keyword tool using ripgrep."""
    try:
        project_name = action.parameters.get("project_name")
        keyword = action.parameters.get("keyword", "")
        file_paths_str = action.parameters.get("file_paths", "")
        # Handle None values properly for before_lines and after_lines
        before_lines_param = action.parameters.get("before_lines")
        after_lines_param = action.parameters.get("after_lines")

        before_lines = int(before_lines_param) if before_lines_param is not None else 0
        after_lines = int(after_lines_param) if after_lines_param is not None else 5

        logger.debug(
            f"🔍 Search parameters: keyword='{keyword}', before_lines={before_lines}, after_lines={after_lines}, regex={action.parameters.get('regex', 'false')}"
        )
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

        # Handle case when neither file_paths nor project_name is provided
        if not file_paths_str and not project_name:
            # Use current directory instead of raising an exception
            file_paths_str = "."

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

            # Add context lines - Fix: Always add these parameters properly
            if before_lines > 0:
                cmd.extend(["-B", str(before_lines)])
            if after_lines > 0:
                cmd.extend(["-A", str(after_lines)])

            # Case sensitivity
            if not case_sensitive:
                cmd.append("-i")

            # Line numbers and show file names
            cmd.extend(["-n", "-H"])
            cmd.append("--hidden")

            # Add ignore patterns for files and directories
            for pattern in IGNORE_FILE_PATTERNS:
                cmd.extend(["--glob", f"!{pattern}"])

            for pattern in IGNORE_DIRECTORY_PATTERNS:
                cmd.extend(["--glob", f"!{pattern}/**"])

            # Add keyword
            if use_regex:
                cmd.append(keyword)
            else:
                cmd.extend(["-F", keyword])

            return cmd

        all_results = []
        commands_run = []

        # Search in specified files/directories
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
            # Group matches by file path to avoid repetitive file paths
            grouped_output = group_matches_by_file(combined_output)

            # Add project header if project_name is available
            data_with_header = grouped_output
            if project_name:
                data_with_header = f"PROJECT: {project_name}\n{grouped_output}"

            # Check if content needs chunking
            chunking_threshold = SEARCH_CONFIG["chunking_threshold"]
            chunk_size = SEARCH_CONFIG["chunk_size"]

            lines = data_with_header.split("\n")
            total_lines = len(lines)

            if total_lines <= chunking_threshold:
                # Content is small enough, return as-is
                yield {
                    "type": "tool_use",
                    "tool_name": "search_keyword",
                    "keyword": keyword,
                    "file_paths": (
                        file_paths if file_paths else "all files (including .env*)"
                    ),
                    "matches_found": True,
                    "data": data_with_header,
                    "command": " | ".join(commands_run),
                    "project_name": project_name,
                }
            else:
                # Content needs chunking - use group-aware chunking for grouped output
                chunks = chunk_grouped_content(data_with_header, chunk_size)

                for chunk in chunks:
                    yield {
                        "type": "tool_use",
                        "tool_name": "search_keyword",
                        "keyword": keyword,
                        "file_paths": (
                            file_paths if file_paths else "all files (including .env*)"
                        ),
                        "matches_found": True,
                        "data": chunk["data"],
                        "command": " | ".join(commands_run),
                        "project_name": project_name,
                        "chunk_info": chunk["chunk_info"],
                    }
        else:
            no_matches_msg = f"No matches found for '{keyword}' - try different keywords or check spelling."
            # Add project header for no matches case if needed
            if project_name:
                no_matches_msg = f"PROJECT: {project_name}\n{no_matches_msg}"

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
