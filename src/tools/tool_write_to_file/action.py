from typing import Iterator, Dict, Any
import uuid
from pathlib import Path

from config.settings import config
from models.agent import AgentAction


def execute_write_to_file_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute file operation tool - handles both write_to_file operations."""
    try:
        file_path = action.parameters.get("path")
        content = action.parameters.get("content")
        line_number = action.parameters.get("line")
        is_new_file = action.parameters.get("is_new_file", False)

        # Validate required parameters
        if not file_path:
            yield {
                "type": "tool_use",
                "tool_name": "write_to_file",
                "successful_files": [],
                "failed_files": [],
                "status": "failed",
                "message": "Missing required parameter: path",
                "summary": "Failed to process 0/1 files",
                "total_files": 1,
                "success_count": 0,
                "failure_count": 1,
                "applied_changes_to_files": [],
                "original_request": "<write_to_file><path>unknown</path><content></content></write_to_file>",
            }
            return

        if content is None:
            yield {
                "type": "tool_use",
                "tool_name": "write_to_file",
                "successful_files": [],
                "failed_files": [file_path],
                "status": "failed",
                "message": "Missing required parameter: content",
                "summary": "Failed to process 0/1 files",
                "total_files": 1,
                "success_count": 0,
                "failure_count": 1,
                "applied_changes_to_files": [],
                "original_request": f"<write_to_file><path>{file_path}</path><content></content></write_to_file>",
            }
            return

        # Validate line_number if provided
        if line_number is not None:
            try:
                line_number = int(line_number)
                if line_number < 0:
                    yield {
                        "type": "tool_use",
                        "tool_name": "write_to_file",
                        "successful_files": [],
                        "failed_files": [file_path],
                        "status": "failed",
                        "message": "Line number must be 0 or positive (0 = append to end, 1+ = insert before line)",
                        "summary": "Failed to process 0/1 files",
                        "total_files": 1,
                        "success_count": 0,
                        "failure_count": 1,
                        "applied_changes_to_files": [],
                        "original_request": f"<write_to_file><path>{file_path}</path><line>{line_number}</line><content>{content}</content></write_to_file>",
                    }
                    return
            except (ValueError, TypeError):
                yield {
                    "type": "tool_use",
                    "tool_name": "write_to_file",
                    "successful_files": [],
                    "failed_files": [file_path],
                    "status": "failed",
                    "message": "Line number must be a valid integer",
                    "summary": "Failed to process 0/1 files",
                    "total_files": 1,
                    "success_count": 0,
                    "failure_count": 1,
                    "applied_changes_to_files": [],
                    "original_request": f"<write_to_file><path>{file_path}</path><line>{line_number}</line><content>{content}</content></write_to_file>",
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

        if is_new_file:
            # Create directory if it doesn't exist
            file_to_check.parent.mkdir(parents=True, exist_ok=True)
            # Write new content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            success_message = f"Successfully wrote to {file_path}"

        else:
            # Create new file if it doesn't exist and is_new_file is True
            if not file_to_check.exists() and is_new_file:
                file_to_check.parent.mkdir(parents=True, exist_ok=True)
                lines = []
            else:
                # Read existing file into lines
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    lines = []

            # Ensure content ends with newline if it doesn't already
            if content and not content.endswith("\n"):
                content += "\n"

            # Insert content at specified line or append if line_number is None
            if line_number is None or line_number == 0:
                # Append to end
                lines.append(content)
                success_message = f"Successfully appended content to {file_path}"
            else:
                # Insert at specific line (1-based)
                insert_index = max(0, line_number - 1)
                lines.insert(insert_index, content)
                success_message = f"Successfully inserted content at line {line_number} in {file_path}"

            # Write back to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        # Yield success result
        result = {
            "type": "tool_use",
            "tool_name": "write_to_file",
            "change_id": change_id,
            "file_path": file_path,
            "backup_path": str(backup_path),
            "successful_files": [file_path],
            "failed_files": [],
            "status": "success",
            "message": success_message,
            "summary": f"Successfully processed 1/1 files",
            "total_files": 1,
            "success_count": 1,
            "failure_count": 0,
            "applied_changes_to_files": [file_path],
        }

        # Add line_number to result if it was an insert operation and line_number was specified
        if not is_new_file and line_number is not None:
            result["line_number"] = line_number

        yield result

    except Exception as e:
        # Create appropriate original_request based on operation
        if not is_new_file:
            original_request = f"<write_to_file><path>{file_path if file_path else 'unknown'}</path><line>{line_number if line_number is not None else 'unknown'}</line><content>{content if content else ''}</content></write_to_file>"
        else:
            original_request = f"<write_to_file><path>{file_path if file_path else 'unknown'}</path><content>{content if content else ''}</content></write_to_file>"

        yield {
            "type": "tool_use",
            "tool_name": "write_to_file",
            "successful_files": [],
            "failed_files": [file_path] if file_path else [],
            "status": "failed",
            "message": f"Failed to perform file operation on {file_path}: {str(e)}",
            "summary": f"Failed to process 0/1 files",
            "total_files": 1,
            "success_count": 0,
            "failure_count": 1,
            "applied_changes_to_files": [],
            "original_request": original_request,
        }
