import subprocess
import re
from pathlib import Path
from typing import Iterator, Dict, Any

from models.agent import AgentAction

def execute_search_keyword_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute search keyword tool using ripgrep."""
    try:
        keyword = action.parameters.get("keyword", "")
        file_paths_str = action.parameters.get("file_paths", "")
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

        # Parse and validate file paths
        file_paths = []
        invalid_paths = []
        if file_paths_str:
            raw_paths = [path.strip() for path in file_paths_str.split(",") if path.strip()]
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
                    "tool_name": "search_keyword"
                }

        # Validate regex if needed
        if use_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                yield {
                    "type": "tool_error",
                    "error": f"Invalid regex pattern: {str(e)}",
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

        # Debug: Log the command being executed
        cmd1_str = " ".join(cmd1)
        print(f"🔍 DEBUG: Executing ripgrep command: {cmd1_str}")
        
        result1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=".")
        
        # Debug: Log command result
        print(f"🔍 DEBUG: Command exit code: {result1.returncode}")
        if result1.stderr:
            print(f"🔍 DEBUG: Command stderr: {result1.stderr}")
        print(f"🔍 DEBUG: Command stdout length: {len(result1.stdout) if result1.stdout else 0} chars")
        
        # Check for ripgrep errors (exit codes > 1 indicate errors)
        if result1.returncode > 1:
            yield {
                "type": "tool_error",
                "error": f"Ripgrep error (exit code {result1.returncode}): {result1.stderr}",
                "tool_name": "search_keyword",
                "command": cmd1_str
            }
            return
            
        if result1.returncode == 0:
            all_results.append(result1.stdout)
        commands_run.append(cmd1_str)

        # Search in .env* files specifically (if no specific file paths given)
        if not file_paths:
            cmd2 = build_base_cmd()
            cmd2.extend(["--glob", ".env*"])
            
            cmd2_str = " ".join(cmd2)
            print(f"🔍 DEBUG: Executing .env search command: {cmd2_str}")

            result2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=".")
            
            print(f"🔍 DEBUG: .env search exit code: {result2.returncode}")
            if result2.stderr:
                print(f"🔍 DEBUG: .env search stderr: {result2.stderr}")
            
            # Check for errors in .env search too
            if result2.returncode > 1:
                yield {
                    "type": "tool_warning",
                    "warning": f"Error searching .env files (exit code {result2.returncode}): {result2.stderr}",
                    "tool_name": "search_keyword"
                }
            elif result2.returncode == 0:
                all_results.append(result2.stdout)
            commands_run.append(cmd2_str)

        # Combine results
        combined_output = "\n".join(all_results).strip()
        
        print(f"🔍 DEBUG: Combined output length: {len(combined_output) if combined_output else 0} chars")
        
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
