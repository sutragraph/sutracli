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
            "ID FORMAT: All items use unique IDs for LLM operations (add_task, move_task, remove_task, add_code, remove_code)",
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
            for code in self.memory_ops.code_snippets.values():
                content.extend(
                    [
                        f"Code {code.id}: {code.file_path} (lines {code.start_line}-{code.end_line})",
                        f"  Description: {code.description}",
                    ]
                )

                # Include actual code content if available
                if code.content:
                    content.extend(
                        [
                            "  Code:",
                            "  ```",
                        ]
                    )
                    # Add each line of code with proper indentation
                    for line in code.content.split("\n"):
                        content.append(f"  {line}")
                    content.extend(
                        [
                            "  ```",
                            "",
                        ]
                    )
                else:
                    content.append("")

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
        recent_history = self.memory_ops.get_recent_history(20)
        if recent_history:
            content.extend(["RECENT HISTORY:", ""])
            for i, entry in enumerate(reversed(recent_history), 1):
                content.append(f"{i}. {entry.summary}")
            content.append("")

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