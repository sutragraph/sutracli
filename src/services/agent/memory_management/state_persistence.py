"""
State Persistence Module

Handles import/export of memory state for persistence.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Set

from .memory_operations import MemoryOperations
from .models import (
    CodeSnippet,
    FileChange,
    HistoryEntry,
    MemorySection,
    MemorySectionData,
    Task,
    TaskStatus,
)


class StatePersistence:
    """Handles state persistence operations for memory data"""

    def __init__(self, memory_ops: MemoryOperations):
        self.memory_ops = memory_ops

    def export_memory_state(
        self,
        sections: Optional[Set[MemorySection]] = None,
        project_path: Optional[str] = None,
    ) -> MemorySectionData:
        """
        Export current memory state as MemorySectionData.

        Args:
            sections: Optional set of MemorySection enums to export. If None, exports all sections.
            project_path: Optional project path to filter code snippets. If provided, only code snippets
                         whose files are within this project path will be exported.

        Returns:
            MemorySectionData containing memory state data for specified sections
        """
        # Determine which sections to collect data for
        if sections is not None:
            # Only collect data for specified sections
            tasks_data = {}
            code_snippets_data = {}
            history_data = []
            file_changes_data = []
            counters_data = {}
            feedback_section_data = None
            project_info_data = None

            if MemorySection.TASKS in sections:
                tasks_data = (
                    self.memory_ops.tasks.copy() if self.memory_ops.tasks else {}
                )
            if MemorySection.CODE_SNIPPETS in sections:
                if project_path:
                    # Filter code snippets by project path
                    filtered_snippets = (
                        self.memory_ops.get_code_snippets_by_project_path(project_path)
                    )
                    code_snippets_data = {
                        snippet.id: snippet for snippet in filtered_snippets
                    }
                else:
                    code_snippets_data = (
                        self.memory_ops.code_snippets.copy()
                        if self.memory_ops.code_snippets
                        else {}
                    )
            if MemorySection.HISTORY in sections:
                history_data = (
                    self.memory_ops.history.copy() if self.memory_ops.history else []
                )
            if MemorySection.FILE_CHANGES in sections:
                file_changes_data = (
                    self.memory_ops.file_changes.copy()
                    if self.memory_ops.file_changes
                    else []
                )
            if MemorySection.COUNTERS in sections:
                counters_data = {
                    "task_id_counter": self.memory_ops.task_id_counter,
                    "code_id_counter": self.memory_ops.code_id_counter,
                }
            if MemorySection.FEEDBACK_SECTION in sections:
                feedback_section_data = self.memory_ops.feedback_section
            if MemorySection.PROJECT_INFO in sections:
                project_info_data = self.memory_ops.project_info
        else:
            # Collect all available data - use actual dataclass objects
            tasks_data = self.memory_ops.tasks.copy() if self.memory_ops.tasks else {}

            # Handle code snippets with optional project path filtering
            if project_path:
                filtered_snippets = self.memory_ops.get_code_snippets_by_project_path(
                    project_path
                )
                code_snippets_data = {
                    snippet.id: snippet for snippet in filtered_snippets
                }
            else:
                code_snippets_data = (
                    self.memory_ops.code_snippets.copy()
                    if self.memory_ops.code_snippets
                    else {}
                )

            history_data = (
                self.memory_ops.history.copy() if self.memory_ops.history else []
            )
            file_changes_data = (
                self.memory_ops.file_changes.copy()
                if self.memory_ops.file_changes
                else []
            )

            counters_data = {
                "task_id_counter": self.memory_ops.task_id_counter,
                "code_id_counter": self.memory_ops.code_id_counter,
            }

            feedback_section_data = self.memory_ops.feedback_section
            project_info_data = self.memory_ops.project_info

        # Return MemorySectionData with the requested data
        return MemorySectionData(
            tasks=tasks_data,
            code_snippets=code_snippets_data,
            history=history_data,
            file_changes=file_changes_data,
            counters=counters_data,
            feedback_section=feedback_section_data,
            project_info=project_info_data,
        )

    def import_memory_state(self, state: MemorySectionData) -> bool:
        """
        Import memory state from MemorySectionData.

        Args:
            state: MemorySectionData to import

        Returns:
            bool: True if import was successful
        """
        try:
            # Import all available data from MemorySectionData
            # Import tasks if available - they are already Task objects
            if state.tasks:
                self.memory_ops.tasks.clear()
                self.memory_ops.tasks.update(state.tasks)

            # Import code snippets if available - they are already CodeSnippet objects
            if state.code_snippets:
                self.memory_ops.code_snippets.clear()
                self.memory_ops.code_snippets.update(state.code_snippets)

            # Import history if available - they are already HistoryEntry objects
            if state.history:
                self.memory_ops.history.clear()
                self.memory_ops.history.extend(state.history)

            # Import file changes if available - they are already FileChange objects
            if state.file_changes:
                self.memory_ops.file_changes.clear()
                self.memory_ops.file_changes.extend(state.file_changes)

            # Import feedback section if available
            if state.feedback_section is not None:
                self.memory_ops.feedback_section = state.feedback_section

            # Import project info if available
            if state.project_info is not None:
                self.memory_ops.project_info = state.project_info

            # Import counters if available
            if state.counters:
                counters = state.counters
                self.memory_ops.task_id_counter = counters.get("task_id_counter", 0)
                self.memory_ops.code_id_counter = counters.get("code_id_counter", 0)

            return True

        except Exception as e:
            print(f"Error importing memory state: {e}")
            return False
