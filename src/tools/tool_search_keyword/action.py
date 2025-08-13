import subprocess
from typing import Iterator, Dict, Any

from models.agent import AgentAction

def execute_search_keyword_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute search keyword tool using ripgrep."""
    try:
        keyword = action.parameters.get("keyword", "")
        file_paths_str = action.parameters.get("file_paths", "")
        # Parse comma-separated file paths
        if file_paths_str:
            file_paths = [path.strip() for path in file_paths_str.split(",") if path.strip()]
        else:
            file_paths = []
        before_lines = int(action.parameters.get("before_lines", 5))
        after_lines = int(action.parameters.get("after_lines", 5))
        case_sensitive = str(action.parameters.get("case_sensitive", "false")).lower() == "true"
        use_regex = str(action.parameters.get("regex", "false")).lower() == "true"

        if not keyword:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: keyword",
                "tool_name": "search_keyword"
            }
            return

        # Validate file_paths_str if provided
        if file_paths_str and not isinstance(file_paths_str, str):
            yield {
                "type": "tool_error",
                "error": "file_paths parameter must be a comma-separated string",
                "tool_name": "search_keyword"
            }
            return

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

        result1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=".")
        if result1.returncode == 0:
            all_results.append(result1.stdout)
        commands_run.append(" ".join(cmd1))

        # Search in .env* files specifically (if no specific file paths given)
        if not file_paths:
            cmd2 = build_base_cmd()
            cmd2.extend(["--glob", ".env*"])

            result2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=".")
            if result2.returncode == 0:
                all_results.append(result2.stdout)
            commands_run.append(" ".join(cmd2))

        # Combine results
        combined_output = "\n".join(all_results).strip()

        if combined_output:
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_paths": file_paths if file_paths else "all files (including .env*)",
                "matches_found": True,
                "data": combined_output,
                "command": " | ".join(commands_run),
            }
        else:
            # No matches found
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_paths": file_paths if file_paths else "all files (including .env*)",
                "matches_found": False,
                "data": f"No matches found for '{keyword}'",
                "command": " | ".join(commands_run),
            }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to search keyword: {str(e)}",
            "tool_name": "search_keyword"
        }
