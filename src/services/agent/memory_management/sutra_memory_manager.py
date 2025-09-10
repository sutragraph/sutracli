"""
Modular Sutra Memory Manager

A refactored version of the original SutraMemoryManager that uses separated components
for better maintainability and modularity.

This is the main interface that combines all the modular components:
- Memory Operations (task/code management)
- State Persistence (import/export)
- Memory Formatting (LLM context formatting)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from baml_client.types import CodeStorageAction, SutraMemoryParams, TaskOperationAction

from .memory_formatter import MemoryFormatter
from .memory_operations import MemoryOperations
from .memory_updater import MemoryUpdater
from .models import CodeSnippet, HistoryEntry, Task, TaskStatus
from .state_persistence import StatePersistence


class SutraMemoryManager:
    """
    Modular Sutra Memory Manager that orchestrates all memory management components.

    This class provides the same interface as the original SutraMemoryManager
    but uses separated, modular components internally.
    """

    def __init__(self, session_manager=None):
        # Initialize core components
        self.memory_ops = MemoryOperations()
        # session_manager kept for backward compatibility but not used
        self._init_components()

    def _init_components(self):
        """Initialize components - can be overridden by subclasses"""
        self.state_persistence = StatePersistence(self.memory_ops)
        self.memory_formatter = MemoryFormatter(self.memory_ops)
        self.memory_updater = MemoryUpdater(self.memory_ops)

    # ID Generation Methods
    def get_next_task_id(self) -> str:
        """Generate next unique task ID"""
        return self.memory_ops.get_next_task_id()

    def get_next_code_id(self) -> str:
        """Generate next unique code ID"""
        return self.memory_ops.get_next_code_id()

    # Task Management Methods
    def add_task(self, task_id: str, description: str, status: TaskStatus) -> bool:
        """Add a new task with validation (task_id is ignored, counter+1 used instead)"""
        return self.memory_ops.add_task(task_id, description, status)

    def move_task(self, task_id: str, new_status: TaskStatus) -> bool:
        """Move task to new status with validation"""
        return self.memory_ops.move_task(task_id, new_status)

    def remove_task(self, task_id: str) -> bool:
        """Remove task from memory"""
        return self.memory_ops.remove_task(task_id)

    def get_current_task(self) -> Optional[Task]:
        """Get the current task if any"""
        return self.memory_ops.get_current_task()

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with specific status"""
        return self.memory_ops.get_tasks_by_status(status)

    def clear_completed_tasks(self) -> int:
        """Remove all completed tasks and return count of removed tasks"""
        return self.memory_ops.clear_completed_tasks()

    # Code Snippet Management Methods
    def add_code_snippet(
        self,
        code_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        description: str,
    ) -> bool:
        """Add code snippet to memory (code_id is ignored, counter+1 used instead)"""
        return self.memory_ops.add_code_snippet(
            code_id, file_path, start_line, end_line, description
        )

    def remove_code_snippet(self, code_id: str) -> bool:
        """Remove code snippet from memory"""
        return self.memory_ops.remove_code_snippet(code_id)

    def get_code_snippet(self, code_id: str) -> Optional[CodeSnippet]:
        """Get code snippet by ID"""
        return self.memory_ops.get_code_snippet(code_id)

    def get_all_code_snippets(self) -> Dict[str, CodeSnippet]:
        """Get all stored code snippets"""
        return self.memory_ops.get_all_code_snippets()

    def get_code_snippets_by_file(self, file_path: str) -> List[CodeSnippet]:
        """Get all code snippets for a specific file"""
        return self.memory_ops.get_code_snippets_by_file(file_path)

    # File Change Tracking Methods
    def track_file_change(self, file_path: str, operation: str) -> bool:
        """Track file change"""
        return self.memory_ops.track_file_change(file_path, operation)

    # History Management Methods
    def add_history(self, summary: str) -> bool:
        """Add history entry (mandatory in every response)"""
        return self.memory_ops.add_history(summary)

    def get_recent_history(self) -> List[HistoryEntry]:
        """Get recent history entries"""
        return self.memory_ops.get_recent_history()

    def get_tool_history(self) -> List[HistoryEntry]:
        """Get recent tool execution history with validation results"""
        history = self.get_recent_history()
        return [h for h in history if h.tool_name is not None]

    # Structured Object Processing Methods
    def process_sutra_memory_params(
        self, sutra_memory: SutraMemoryParams
    ) -> Dict[str, Any]:
        """
        Process sutra memory changes from SutraMemoryParams object directly.

        Args:
            sutra_memory: SutraMemoryParams object from agent response

        Returns:
            Dict containing processing results and any errors
        """
        results = {
            "success": True,
            "errors": [],
            "warnings": [],
            "changes_applied": {"tasks": [], "code": [], "files": [], "history": []},
        }

        try:
            # Process mandatory history (required in every response)
            if sutra_memory.add_history:
                if self.add_history(sutra_memory.add_history):
                    results["changes_applied"]["history"].append(
                        f"Added: {sutra_memory.add_history}"
                    )
                else:
                    results["errors"].append("Failed to add history entry")
            else:
                results["warnings"].append(
                    "No history entry found - history is mandatory in every response"
                )

            # Process task operations (optional field)
            if hasattr(sutra_memory, "tasks") and sutra_memory.tasks:
                for task_op in sutra_memory.tasks:
                    if task_op.action == TaskOperationAction.Add:
                        # Convert BAML status to TaskStatus enum
                        try:
                            if task_op.to_status:
                                if isinstance(task_op.to_status, str):
                                    # BAML sends uppercase (CURRENT), convert to lowercase for our enum
                                    status = TaskStatus(task_op.to_status.lower())
                                else:
                                    # Handle TaskStatus enum directly
                                    status = task_op.to_status
                            else:
                                status = TaskStatus.PENDING

                            # add_task will use counter+1 internally and ignore the LLM provided ID
                            if self.add_task(task_op.id, task_op.description, status):
                                # Get the actual ID that was assigned (current counter value)
                                actual_task_id = str(self.memory_ops.task_id_counter)
                                results["changes_applied"]["tasks"].append(
                                    f"Added task {actual_task_id}: {task_op.description} (LLM ID {task_op.id} ignored)"
                                )
                            else:
                                results["errors"].append(
                                    f"Failed to add task (LLM ID {task_op.id})"
                                )
                        except ValueError as e:
                            results["errors"].append(
                                f"Invalid status '{task_op.to_status}' for new task (LLM ID {task_op.id}): {e}"
                            )

                    elif task_op.action == TaskOperationAction.Move:
                        # Convert BAML status to TaskStatus enum
                        try:
                            if isinstance(task_op.to_status, str):
                                # BAML sends uppercase (CURRENT), convert to lowercase for our enum
                                target_status = TaskStatus(task_op.to_status.lower())
                            else:
                                # Handle TaskStatus enum directly
                                target_status = task_op.to_status

                            if self.move_task(task_op.id, target_status):
                                results["changes_applied"]["tasks"].append(
                                    f"Moved task {task_op.id} to {target_status.value}"
                                )
                            else:
                                results["errors"].append(
                                    f"Failed to move task {task_op.id}"
                                )
                        except ValueError as e:
                            results["errors"].append(
                                f"Invalid status '{task_op.to_status}' for task {task_op.id}: {e}"
                            )

                    # elif task_op.action == TaskOperationAction.Remove:
                    #     if self.remove_task(task_op.id):
                    #         results["changes_applied"]["tasks"].append(f"Removed task {task_op.id}")
                    #     else:
                    #         results["errors"].append(f"Failed to remove task {task_op.id}")

            # Process code operations (optional field)
            if hasattr(sutra_memory, "code") and sutra_memory.code:
                for code_op in sutra_memory.code:
                    if code_op.action == CodeStorageAction.Add:
                        # add_code_snippet will use counter+1 internally and ignore the LLM provided ID
                        if self.add_code_snippet(
                            code_op.id,
                            code_op.file,
                            code_op.start_line,
                            code_op.end_line,
                            code_op.description,
                        ):
                            # Get the actual ID that was assigned (current counter value)
                            actual_code_id = str(self.memory_ops.code_id_counter)
                            results["changes_applied"]["code"].append(
                                f"Added code {actual_code_id}: {code_op.description} (LLM ID {code_op.id} ignored)"
                            )
                        else:
                            results["errors"].append(
                                f"Failed to add code snippet (LLM ID {code_op.id})"
                            )

                    elif code_op.action == CodeStorageAction.Remove:
                        if self.remove_code_snippet(code_op.id):
                            results["changes_applied"]["code"].append(
                                f"Removed code {code_op.id}"
                            )
                        else:
                            results["errors"].append(
                                f"Failed to remove code snippet {code_op.id}"
                            )

            # Process file changes (optional field)
            # if hasattr(sutra_memory, "files") and sutra_memory.files:
            #     if sutra_memory.files.modified:
            #         for file_path in sutra_memory.files.modified:
            #             if self.track_file_change(file_path, "modified"):
            #                 results["changes_applied"]["files"].append(f"Tracked modification: {file_path}")
            #             else:
            #                 results["errors"].append(f"Failed to track file modification: {file_path}")

            #     if sutra_memory.files.added:
            #         for file_path in sutra_memory.files.added:
            #             if self.track_file_change(file_path, "added"):
            #                 results["changes_applied"]["files"].append(f"Tracked addition: {file_path}")
            #             else:
            #                 results["errors"].append(f"Failed to track file addition: {file_path}")

            #     if sutra_memory.files.deleted:
            #         for file_path in sutra_memory.files.deleted:
            #             if self.track_file_change(file_path, "deleted"):
            #                 results["changes_applied"]["files"].append(f"Tracked deletion: {file_path}")
            #             else:
            #                 results["errors"].append(f"Failed to track file deletion: {file_path}")

            return results

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error processing sutra memory: {str(e)}")
            return results

    # State Management Methods
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of current memory state"""
        return self.memory_ops.get_memory_summary()

    def validate_memory_state(self) -> Dict[str, Any]:
        """Validate current memory state and return any issues"""
        return self.memory_ops.validate_memory_state()

    def reset_memory(self) -> bool:
        """Reset all memory state (use with caution)"""
        return self.memory_ops.reset_memory()

    # State Persistence Methods
    def export_memory_state(self) -> Dict[str, Any]:
        """Export current memory state to dictionary for persistence"""
        return self.state_persistence.export_memory_state()

    def import_memory_state(self, state: Dict[str, Any]) -> bool:
        """Import memory state from dictionary"""
        return self.state_persistence.import_memory_state(state)

    # Memory Formatting Methods
    def get_memory_for_llm(self) -> str:
        """Get current memory state formatted for LLM context in text format"""
        return self.memory_formatter.get_memory_for_llm()

    def get_code_snippets_for_llm(self) -> str:
        """Get only the code snippets formatted for LLM context"""
        return self.memory_formatter.get_code_snippets_for_llm()

    # Memory Update Methods
    def update_memory_for_file_changes(
        self, changed_files: Set[Path], deleted_files: Set[Path], project_id: int
    ) -> Dict[str, Any]:
        """Update Sutra memory when files change during incremental indexing"""
        return self.memory_updater.update_memory_for_file_changes(
            changed_files, deleted_files, project_id
        )

    # Feedback Management Methods
    def set_feedback_section(self, feedback_content: str) -> bool:
        """Set feedback section content in memory operations"""
        return self.memory_ops.set_feedback_section(feedback_content)

    def get_feedback_section(self) -> Optional[str]:
        """Get feedback section content from memory operations"""
        return self.memory_ops.get_feedback_section()

    def clear_feedback_section(self) -> bool:
        """Clear feedback section content from memory operations"""
        return self.memory_ops.clear_feedback_section()
