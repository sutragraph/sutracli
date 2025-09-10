"""
Memory Formatter Module

Handles formatting of memory state for LLM context and other display purposes.
"""

from typing import List
from .models import TaskStatus
from .memory_operations import MemoryOperations


class MemoryFormatter:
    """Handles formatting of memory state for various contexts"""

    def __init__(self, memory_ops: MemoryOperations):
        self.memory_ops = memory_ops

    def get_memory_for_llm(self) -> str:
        """
        Get current memory state formatted for LLM context in text format.

        Returns:
            str: Formatted memory state for LLM context
        """
        return self._get_memory_text()

    def _get_memory_text(self) -> str:
        """Generate plain text formatted memory state for LLM"""
        content = [
            "ID FORMAT: All items use unique IDs for LLM operations (add_task, move_task, remove_task, add_code, remove_code)\n",
        ]

        # Current task
        current_task = self.memory_ops.get_current_task()
        if current_task:
            content.extend(
                [
                    "CURRENT TASK:",
                    f"ID: {current_task.id}",
                    f"Description: {current_task.description}",
                    "",
                ]
            )

        # Pending tasks
        pending_tasks = self.memory_ops.get_tasks_by_status(TaskStatus.PENDING)
        if pending_tasks:
            content.extend(["PENDING TASKS:", ""])
            for task in pending_tasks:
                content.append(f"ID: {task.id}")
                content.append(f"Description: {task.description}")
                content.append("")

        # Completed tasks (recent ones)
        completed_tasks = self.memory_ops.get_tasks_by_status(TaskStatus.COMPLETED)
        if completed_tasks:
            recent_completed = sorted(
                completed_tasks, key=lambda t: t.updated_at, reverse=True
            )[:5]
            content.extend(["RECENTLY COMPLETED TASKS:", ""])
            for task in recent_completed:
                content.append(f"ID: {task.id}")
                content.append(f"Description: {task.description}")
                content.append("")

        # Code snippets
        if self.memory_ops.code_snippets:
            content.extend(["STORED CODE SNIPPETS:", ""])
            content.extend(self._format_code_snippets_section())

        # Recent file changes
        if self.memory_ops.file_changes:
            recent_changes = sorted(
                self.memory_ops.file_changes, key=lambda f: f.timestamp, reverse=True
            )[:10]
            content.extend(["RECENT FILE CHANGES:", ""])
            for change in recent_changes:
                content.append(f"- {change.operation.upper()}: {change.path}")
            content.append("")

        # Recent history (last 20 entries)
        recent_history = self.memory_ops.get_recent_history()
        if recent_history:
            content.extend(["RECENT HISTORY:", ""])
            for i, entry in enumerate(reversed(recent_history), 1):
                content.append(f"{i}. {entry.summary}")
            content.append("")

        feedback_section = self.memory_ops.get_feedback_section()
        if feedback_section:
            content.extend(["", feedback_section])

        return "\n".join(content)

    def _format_code_with_line_numbers(self, content: str, start_line: int) -> str:
        """
        Format code content with line numbers.

        Args:
            content: The raw code content
            start_line: Starting line number for the code snippet

        Returns:
            str: Formatted code with line numbers
        """
        if not content:
            return ""

        # Check if content already has line numbers (from process_code_with_line_filtering)
        lines = content.split("\n")
        if lines and " | " in lines[0]:
            # Content already has line numbers, strip them and re-number correctly
            stripped_lines = []
            for line in lines:
                if " | " in line:
                    # Remove existing line number prefix (e.g., "  3 | content" -> "content")
                    stripped_line = " | ".join(line.split(" | ")[1:])
                    stripped_lines.append(stripped_line)
                else:
                    stripped_lines.append(line)
            lines = stripped_lines

        formatted_lines = []

        # Calculate the width needed for line numbers (for proper alignment)
        end_line = start_line + len(lines) - 1
        max_line_width = len(str(end_line))

        for i, line in enumerate(lines):
            line_number = start_line + i
            # Format: "  5 | content" with proper padding
            formatted_line = f"{line_number:>{max_line_width}} | {line}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def _format_code_snippets_section(self) -> List[str]:
        """
        Format code snippets section using the same format as sutra memory.

        Returns:
            List of formatted lines
        """
        content = []
        for code in self.memory_ops.code_snippets.values():
            content.extend(
                [
                    f"Code {code.id}: {code.file_path} (lines {code.start_line}-{code.end_line})",
                    f"  Description: {code.description}",
                ]
            )

            # Include actual code content if available with line numbers
            if code.content:
                content.extend(
                    [
                        "  Code:",
                        "  ```",
                    ]
                )
                # Add each line of code with line numbers and proper indentation
                formatted_code = self._format_code_with_line_numbers(
                    code.content, code.start_line
                )
                for line in formatted_code.split("\n"):
                    content.append(f"  {line}")
                content.extend(
                    [
                        "  ```",
                        "",
                    ]
                )
            else:
                content.append("")

        return content

    def get_code_snippets_for_llm(self) -> str:
        """
        Get only the code snippets formatted for LLM context using the same format as sutra memory.

        Returns:
            str: Formatted code snippets only
        """
        if not self.memory_ops.code_snippets:
            return ""

        # Use the same formatting as sutra memory
        content = self._format_code_snippets_section()
        return "\n".join(content)


def clean_sutra_memory_content(content: str) -> str:
    """
    Clean Sutra memory content by removing extra whitespace and normalizing format.

    Args:
        content: Raw memory content

    Returns:
        Cleaned memory content
    """
    # Split into lines and clean each line
    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        # Remove trailing whitespace
        cleaned_line = line.rstrip()
        cleaned_lines.append(cleaned_line)

    # Join lines and normalize line endings
    return "\n".join(cleaned_lines)
