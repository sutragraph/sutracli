from pathlib import Path
import uuid
from typing import Iterator, Dict, Any

from src.config.settings import config
from src.services.agent.agentic_core import AgentAction


def execute_write_to_file_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute write to file tool."""
    try:
        file_path = action.parameters.get("path", "")
        content = action.parameters.get("content", "")

        if not file_path:
            yield {
                "type": "tool_error",
                "error": "Missing required parameter: path",
                "tool_name": "write_to_file"
            }
            return

        # Read original content for backup
        file_to_check = Path(file_path)
        original_content = (
            file_to_check.read_text(encoding="utf-8") if file_to_check.exists() else ""
        )
        # Generate change id and backup original
        change_id = str(uuid.uuid4())
        backup_dir = Path(config.storage.file_edits_dir)
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{change_id}_{file_to_check.name}.backup"
        backup_path.write_text(original_content, encoding="utf-8")
        # Create directory if it doesn't exist
        file_to_check.parent.mkdir(parents=True, exist_ok=True)
        # Write new content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Yield applied result with backup information
        yield {
            "type": "tool_use",
            "tool_name": "write_to_file",
            "change_id": change_id,
            "file_path": file_path,
            "backup_path": str(backup_path),
            "success": True,
            "message": f"Successfully wrote to {file_path}",
        }

        # Yield detailed TOOL STATUS (success - no original_request needed)
        yield {
            "type": "tool_status",
            "used_tool": "write_to_file",
            "applied_changes_to_files": [file_path],
            "failed_files": [],
            "status": "success",
            "summary": f"Successfully wrote content to {file_path}"
        }

    except Exception as e:
        yield {
            "type": "tool_error",
            "error": f"Failed to write file: {str(e)}",
            "tool_name": "write_to_file"
        }

        # Yield detailed TOOL STATUS for failure (include full original_request)
        yield {
            "type": "tool_status",
            "used_tool": "write_to_file",
            "applied_changes_to_files": [],
            "failed_files": [file_path] if file_path else ["unknown"],
            "status": "failed",
            "summary": f"Failed to write to file: {str(e)}",
            "failed_changes": f"<error>{str(e)}</error>",
            "original_request": f"<write_to_file><path>{file_path if file_path else 'unknown'}</path><content>{content if content else ''}</content></write_to_file>",
            "details": {
                "operation": "file_write",
                "file_path": file_path if file_path else "unknown",
                "error": str(e)
            }
        }
