"""
Memory Formatter Module

Handles formatting of memory state for LLM context and other display purposes.
"""

from typing import List

from baml_client.types import ElementType, TracedElement

from .memory_operations import MemoryOperations
from .models import TaskStatus


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

        # Code snippets
        if self.memory_ops.code_snippets:
            content.extend(["STORED CODE SNIPPETS:", ""])
            content.extend(self._format_code_snippets_section())

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
            content.extend(["COMPLETED TASKS:", ""])
            for task in recent_completed:
                content.append(f"ID: {task.id}")
                content.append(f"Description: {task.description}")
                content.append("")

        # Recent file changes
        if self.memory_ops.file_changes:
            recent_changes = sorted(
                self.memory_ops.file_changes, key=lambda f: f.timestamp, reverse=True
            )[:10]
            content.extend(["FILES CHANGED:", ""])
            for change in recent_changes:
                content.append(f"- {change.operation.upper()}: {change.path}")
            content.append("")

        # Recent history (last 20 entries)
        recent_history = self.memory_ops.get_recent_history()
        if recent_history:
            content.extend(["HISTORY:", ""])
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
        Format code snippets section with call chain tracing information.

        Returns:
            List of formatted lines
        """
        content = []
        for code in self.memory_ops.code_snippets.values():
            # Add tracing status indicator
            trace_status = "yes" if code.is_traced else "no"
            content.extend(
                [
                    f"SNIPPET {code.id}: {code.file_path}(lines {code.start_line} - {code.end_line})[TRACED: {trace_status}]",
                    f"  Description: {code.description}",
                ]
            )

            # Add call chain summary if available
            if code.call_chain_summary:
                content.append(f"  call_chain: {code.call_chain_summary}")

            # Add traced elements section - handle both old and new format
            content.append("  traced_elements:")
            if code.root_elements:
                for root_element in code.root_elements:
                    content.extend(
                        self._format_element_hierarchy(
                            root_element, code.file_path, indent="    "
                        )
                    )
            else:
                content.append("    [] (none)")

            # Add needs tracing section - always show header
            content.append("  needs_tracing:")
            if code.needs_tracing:
                for ute in code.needs_tracing:
                    reason_text = f" ({ute.reason})" if ute.reason else ""
                    accessed_from_text = (
                        f" [accessed from {ute.accessed_from}]"
                        if ute.accessed_from
                        else ""
                    )
                    element_display = self._format_element_name_with_type(
                        ute.name, ute.element_type
                    )
                    element_id_display = (
                        f" [ID: {ute.id}]" if (ute.id and ute.id.strip()) else ""
                    )
                    content.append(
                        f"    - {element_display}{reason_text}{accessed_from_text}{element_id_display}"
                    )
            else:
                content.append("    [] (none)")

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

    def _format_element_hierarchy(
        self, element: TracedElement, file_path: str, indent: str = "    "
    ) -> List[str]:
        """
        Format element hierarchy in tree structure like:
        processData (lines 292-328) [✓] [ID: elem_1]
          ├── service.getData (lines 103-105) [✓] [ID: elem_2]
          ├── service.checkStatus (lines 107-112) [✓] [ID: elem_3]
          │   └── obj.property (lines 39-41) [✓] [ID: elem_4]
          └── logger.info [✓] [ID: elem_5]

        Args:
            element: TracedElement to format
            indent: Current indentation level

        Returns:
            List of formatted lines
        """
        lines = []

        # Format current element with ID
        status = "yes" if element.is_fully_traced else "no"
        element_display = self._format_element_name_with_type(
            element.name, element.element_type
        )
        element_id_display = (
            f" [ID: {element.id}]" if (element.id and element.id.strip()) else ""
        )
        lines.append(
            f"{indent}{element_display} (lines {element.start_line}-{element.end_line}) [traced: {status}]{element_id_display}"
        )

        # Show complete code content if available, otherwise show key code lines
        if element.content:
            lines.append(f"{indent}  Code:")
            lines.append(
                f"{indent}  ```{file_path}#L{element.start_line}-{element.end_line}"
            )
            # Split content into lines and add proper indentation
            content_lines = element.content.split("\n")
            for line in content_lines:
                lines.append(f"{indent}  {line}")
            lines.append(f"{indent}  ```")
        elif element.signature:
            # Show signature or basic info if no code content available
            lines.append(f"{indent}  Signature: {element.signature}")

        # Recursively format child elements with tree structure
        if element.accessed_elements:
            for i, child in enumerate(element.accessed_elements):
                is_last = i == len(element.accessed_elements) - 1
                child_prefix = "└── " if is_last else "├── "
                continuation_indent = "    " if is_last else "│   "

                child_lines = self._format_element_hierarchy(child, file_path, "")
                if child_lines:
                    # Add the tree prefix to the first line
                    first_line = child_lines[0].lstrip()
                    lines.append(f"{indent}  {child_prefix}{first_line}")

                    # Add continuation lines with proper indentation
                    for line in child_lines[1:]:
                        lines.append(f"{indent}  {continuation_indent}{line}")

        return lines

    def _format_element_name_with_type(
        self, name: str, element_type: ElementType
    ) -> str:
        """Format element name with appropriate notation based on element type"""
        if not element_type:
            return name

        type_value = element_type.value.lower()

        if type_value:
            return f"{name} [{type_value}]"
        return name


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
