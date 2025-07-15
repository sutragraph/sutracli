import subprocess
from typing import Iterator, Dict, Any

from services.agent.agentic_core import AgentAction

def execute_search_keyword_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute search keyword tool using ripgrep."""
    try:
        keyword = action.parameters.get("keyword", "")
        file_path = action.parameters.get("file_path", "")
        before_lines = int(action.parameters.get("before_lines", 0))
        after_lines = int(action.parameters.get("after_lines", 2))
        case_sensitive = str(action.parameters.get("case_sensitive", "false")).lower() == "true"
        use_regex = str(action.parameters.get("regex", "false")).lower() == "true"

        if not keyword:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: keyword",
                "tool_name": "search_keyword"
            }
            return

        # Build ripgrep command
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

        # Add file path if specified
        if file_path:
            cmd.append(file_path)

        # Execute command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd="."
        )

        if result.returncode == 0:
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_path": file_path or "all files",
                "matches_found": True,
                "data": result.stdout,
                "command": " ".join(cmd),
            }
        elif result.returncode == 1:
            # No matches found
            yield {
                "type": "tool_use",
                "tool_name": "search_keyword",
                "keyword": keyword,
                "file_path": file_path or "all files",
                "matches_found": False,
                "data": f"No matches found for '{keyword}'",
                "command": " ".join(cmd),
            }
        else:
            # Error occurred
            yield {
                "type": "tool_error",
                "error": f"Search failed: {result.stderr}",
                "tool_name": "search_keyword"
            }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to search keyword: {str(e)}",
            "tool_name": "search_keyword"
        }
