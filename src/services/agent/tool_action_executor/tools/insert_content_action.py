from typing import Iterator, Dict, Any
import uuid
from pathlib import Path

from src.config.settings import config
from src.services.agent.agentic_core import AgentAction

def execute_insert_content_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute insert content tool."""
    try:
        file_path = action.parameters.get("path")
        line_number = action.parameters.get("line")
        content = action.parameters.get("content")

        if not file_path:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: path",
                "tool_name": "insert_content"
            }
            return

        if line_number is None:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: line",
                "tool_name": "insert_content"
            }
            return

        if content is None:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: content",
                "tool_name": "insert_content"
            }
            return

        # Validate line_number is a non-negative integer
        try:
            line_number = int(line_number)
            if line_number < 0:
                yield {
                    "type": "tool_error",
                    "error": "Line number must be 0 or positive (0 = append to end, 1+ = insert before line)",
                    "tool_name": "insert_content"
                }
                return
        except (ValueError, TypeError):
            yield {
                "type": "tool_error",
                "error": "Line number must be a valid integer",
                "tool_name": "insert_content"
            }
            return

        # Prepare backup of original content
        file_to_check = Path(file_path)
        original_content = (
            file_to_check.read_text(encoding="utf-8") if file_to_check.exists() else ""
        )
        change_id = str(uuid.uuid4())
        backup_dir = Path(config.storage.file_edits_dir)
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{change_id}_{file_to_check.name}.backup"
        backup_path.write_text(original_content, encoding="utf-8")
        # Read existing file into lines
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        # Ensure content ends with newline if it doesn't already
        if content and not content.endswith('\n'):
            content += '\n'

        # Insert content at specified line
        if line_number == 0:
            # Append to end
            lines.append(content)
        else:
            # Insert at specific line (1-based)
            insert_index = max(0, line_number - 1)
            lines.insert(insert_index, content)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        # Yield applied result with backup information and change_id
        yield {
            "type": "tool_use",
            "tool_name": "insert_content",
            "change_id": change_id,
            "file_path": file_path,
            "backup_path": str(backup_path),
            "line_number": line_number,
            "success": True,
            "message": f"Successfully inserted content at line {line_number} in {file_path}",
        }

        # Yield detailed TOOL STATUS (success - no original_request needed)
        yield {
            "type": "tool_status",
            "used_tool": "insert_content",
            "applied_changes_to_files": [file_path],
            "failed_files": [],
            "status": "success",
            "summary": f"Successfully inserted content at line {line_number} in {file_path}"
        }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to insert content: {str(e)}",
            "tool_name": "insert_content"
        }

        # Yield detailed TOOL STATUS for failure (include full original_request)
        yield {
            "type": "tool_status",
            "used_tool": "insert_content",
            "applied_changes_to_files": [],
            "failed_files": [file_path] if file_path else ["unknown"],
            "status": "failed",
            "summary": f"Failed to insert content: {str(e)}",
            "failed_changes": f"<error>{str(e)}</error>",
            "original_request": f"<insert_content><path>{file_path if file_path else 'unknown'}</path><line>{line_number if line_number is not None else 'unknown'}</line><content>{content if content else ''}</content></insert_content>",
            "details": {
                "operation": "content_insert",
                "file_path": file_path if file_path else "unknown",
                "line_number": line_number if line_number is not None else "unknown",
                "error": str(e)
            }
        }
