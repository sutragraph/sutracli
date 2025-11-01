"""
Apply diff executor for handling apply_diff tool actions.
"""


from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, cast

from loguru import logger

from baml_client.types import Edit, EditFileMode, EditFileParams
from config.settings import config
from models.agent import AgentAction


@dataclass
class EditFileToolOutput:
    """Output structure for the edit file tool."""

    original_path: Path
    new_text: str
    old_text: str
    diff: str


class EditFileToolWithMode:
    """The edit file tool with three distinct modes of operation."""

    @staticmethod
    def resolve_path(input: EditFileParams) -> Path:
        """Resolve and validate the path based on the input type."""
        path = Path(input.path)

        match input.mode:
            case EditFileMode.EDIT:
                # Check if file exists
                if not path.exists():
                    raise ValueError("Can't edit file: path not found")

                # Check if it's a file (not a directory)
                if not path.is_file():
                    raise ValueError("Can't edit file: path is a directory")

                return path

            case EditFileMode.OVERWRITE:
                # For overwrite mode, we don't need to check if the file exists
                # It can be created or overwritten
                return path

            case EditFileMode.CREATE:
                # Check if file already exists
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        preview = content[:300]
                        total_chars = len(content)
                        remaining = total_chars - 300

                        if remaining > 0:
                            msg = f"Can't create file: file already exists.\nContent preview ({total_chars} chars total, {remaining} more):\n{preview}"
                        else:
                            msg = f"Can't create file: file already exists. Content preview ({total_chars} chars total):\n{preview}"
                        raise ValueError(msg)
                    except (UnicodeDecodeError, PermissionError):
                        raise ValueError("Can't create file: file already exists.")

                # Check if parent directory exists
                if not path.parent.exists():
                    raise ValueError(
                        "Can't create file: parent directory doesn't exist"
                    )

                # Check if filename is valid
                if not path.name:
                    raise ValueError("Can't create file: file already exists")

                return path

    @staticmethod
    def execute(input: EditFileParams) -> EditFileToolOutput:
        """Execute the edit file operation based on the input type."""
        path = EditFileToolWithMode.resolve_path(input)

        match input.mode:
            case EditFileMode.EDIT:
                # For edit mode, read the file and apply the edit instructions
                with open(path, "r") as f:
                    old_text = f.read()

                # Apply edits to the content
                if input.edits is None:
                    raise ValueError("Edits cannot be None for EDIT mode")
                new_text = EditFileToolWithMode.apply_edits(old_text, input.edits)

                # Write the updated content back to the file
                with open(path, "w") as f:
                    f.write(new_text)

                # Generate diff
                diff = EditFileToolWithMode.generate_diff(old_text, new_text)

                return EditFileToolOutput(
                    original_path=path, new_text=new_text, old_text=old_text, diff=diff
                )

            case EditFileMode.CREATE:
                # For create mode, create a new file with the provided content
                if input.content is None:
                    raise ValueError("Content cannot be None for CREATE mode")
                with open(path, "w") as f:
                    f.write(input.content)

                old_text = ""
                new_text = input.content
                diff = EditFileToolWithMode.generate_diff(old_text, new_text)

                return EditFileToolOutput(
                    original_path=path, new_text=new_text, old_text=old_text, diff=diff
                )

            case EditFileMode.OVERWRITE:
                # For overwrite mode, replace the entire content
                old_text = ""
                if path.exists():
                    with open(path, "r") as f:
                        old_text = f.read()

                if input.content is None:
                    raise ValueError("Content cannot be None for OVERWRITE mode")
                with open(path, "w") as f:
                    f.write(input.content)

                diff = EditFileToolWithMode.generate_diff(old_text, input.content)

                return EditFileToolOutput(
                    original_path=path,
                    new_text=input.content,
                    old_text=old_text,
                    diff=diff,
                )

    @staticmethod
    def apply_edits(content: str, edits: List[Edit]) -> str:
        """Apply edits to file content."""
        result = content

        # Separate insertion edits (empty old_text) from other edits
        insertion_edits = []
        other_edits = []

        for edit in edits:
            if edit.old_text == "":
                insertion_edits.append(edit)
            else:
                other_edits.append(edit)

        # Apply other edits in reverse order to maintain line numbers
        for edit in reversed(other_edits):
            # Count occurrences of old_text
            occurrences = result.count(edit.old_text)

            if occurrences == 0:
                raise ValueError(f"Could not find text to replace: '{edit.old_text}'")
            elif occurrences == 1:
                # Only one occurrence, simple replacement
                result = result.replace(edit.old_text, edit.new_text)
            else:
                # Multiple occurrences, use line_hint to select the right one
                if edit.line_hint is not None:
                    result = EditFileToolWithMode.apply_edit_with_line_hint(
                        result, edit
                    )
                else:
                    # Multiple occurrences but no line_hint, raise an error
                    raise ValueError(
                        f"Multiple occurrences of text found but no line_hint provided: '{edit.old_text}'"
                    )

        # Apply insertion edits in forward order with proper line number tracking
        if insertion_edits:
            # Sort insertion edits by line_hint to maintain order
            insertion_edits.sort(key=lambda e: e.line_hint or 0)

            # For insertions, we need to track line offsets to maintain correct positions
            # We'll use a line-by-line approach to ensure accuracy
            result = EditFileToolWithMode.apply_multiple_insertions(
                result, insertion_edits
            )

        return result

    @staticmethod
    def apply_multiple_insertions(content: str, edits: List[Edit]) -> str:
        """Apply multiple insertion edits with proper line number tracking."""
        if not edits:
            return content

        # Sort edits by line_hint to process them in order
        # Put None line_hint at the end
        sorted_edits = sorted(
            edits, key=lambda e: (e.line_hint is None, e.line_hint or 0)
        )

        # Apply insertions one by one, reusing the existing insert_at_line method
        result = content
        for edit in sorted_edits:
            result = EditFileToolWithMode.insert_at_line(result, edit)

        return result

    @staticmethod
    def insert_at_line(content: str, edit: Edit) -> str:
        """Insert text at the specified line number (1-based)."""
        lines = content.splitlines(keepends=True)

        # Handle None line_hint (append to end)
        if edit.line_hint is None:
            return content + edit.new_text

        # Convert line_hint from 1-based to 0-based index
        target_line = edit.line_hint - 1  # type: ignore[arg-type]

        # Handle edge cases for line number
        if target_line < 0:
            # Insert at beginning
            insert_pos = 0
        elif target_line >= len(lines):
            # Insert at end
            insert_pos = len(lines)
        else:
            # Insert after the target line (more intuitive for insertions)
            insert_pos = target_line + 1

        # Insert the new text at the calculated position
        lines.insert(insert_pos, edit.new_text)

        return "".join(lines)

    @staticmethod
    def apply_edit_with_line_hint(content: str, edit: Edit) -> str:
        """Apply an edit using line_hint to select the correct occurrence."""
        lines = content.splitlines(keepends=True)

        # Convert line_hint from 1-based to 0-based index
        target_line = edit.line_hint - 1  # type: ignore[arg-type]

        # Find all occurrences of old_text and their line numbers
        occurrences = []
        for i, line in enumerate(lines):
            if edit.old_text in line:
                occurrences.append((i, line))

        if not occurrences:
            raise ValueError(f"Could not find text to replace: '{edit.old_text}'")

        # Find the occurrence closest to the line_hint
        # Allow a tolerance similar to Zed's implementation
        LINE_HINT_TOLERANCE = 50
        best_occurrence = None
        best_distance = float("inf")

        for line_num, line in occurrences:
            distance = abs(line_num - target_line)
            if distance <= LINE_HINT_TOLERANCE and distance < best_distance:
                best_distance = distance
                best_occurrence = (line_num, line)

        if best_occurrence is None:
            # No occurrence within tolerance, use the first one
            line_num, line = occurrences[0]
        else:
            line_num, line = best_occurrence

        # Replace the text in the selected line
        updated_line = line.replace(edit.old_text, edit.new_text)
        lines[line_num] = updated_line

        return "".join(lines)

    @staticmethod
    def generate_diff(old_text: str, new_text: str) -> str:
        """Generate a unified diff showing the changes."""
        if old_text == new_text:
            return ""

        # For simplicity, we'll use a basic diff format
        # In a real implementation, you might use difflib.unified_diff
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff_lines = ["--- a/file\n", "+++ b/file\n"]

        # This is a very simplified diff implementation
        # A proper implementation would use difflib
        if old_lines != new_lines:
            diff_lines.append("@@ -1,1 +1,1 @@\n")

            # Find the first different line
            for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
                if old_line != new_line:
                    diff_lines.append(f"-{old_line}")
                    diff_lines.append(f"+{new_line}")
                    break

        return "".join(diff_lines)


def execute_edit_file_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute the edit_file action.

    Args:
        action (AgentAction): The action to execute.

    Yields:
        Iterator[Dict[str, Any]]: The result of the action execution.
    """
    params = EditFileParams(**action.parameters)
    try:
        result = EditFileToolWithMode.execute(params)

        yield {
            "type": "tool_use",
            "tool_name": "edit_file",
            "data": {
                "original_path": str(result.original_path),
                "new_text": result.new_text,
                "old_text": result.old_text,
                "diff": result.diff,
            },
        }
    except Exception as e:
        logger.error(f"Error executing edit_file action: {e}")
        yield {
            "type": "tool_error",
            "tool_name": "edit_file",
            "error": str(e),
        }
