"""
State Persistence Module

Handles import/export of memory state for persistence.
"""

from datetime import datetime
from typing import Any, Dict

from .memory_operations import MemoryOperations
from .models import CodeSnippet, FileChange, HistoryEntry, Task, TaskStatus


class StatePersistence:
    """Handles state persistence operations for memory data"""

    def __init__(self, memory_ops: MemoryOperations):
        self.memory_ops = memory_ops

    def export_memory_state(self) -> Dict[str, Any]:
        """
        Export current memory state to dictionary for persistence.

        Returns:
            Dict containing serializable memory state
        """
        return {
            "tasks": {
                task_id: {
                    "id": task.id,
                    "description": task.description,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }
                for task_id, task in self.memory_ops.tasks.items()
            },
            "code_snippets": {
                code_id: {
                    "id": code.id,
                    "file_path": code.file_path,
                    "start_line": code.start_line,
                    "end_line": code.end_line,
                    "description": code.description,
                    "content": code.content,
                    "created_at": code.created_at.isoformat(),
                }
                for code_id, code in self.memory_ops.code_snippets.items()
            },
            "history": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "summary": entry.summary,
                    "iteration_id": entry.iteration_id,
                }
                for entry in self.memory_ops.history
            ],
            "file_changes": [
                {
                    "path": change.path,
                    "operation": change.operation,
                    "timestamp": change.timestamp.isoformat(),
                }
                for change in self.memory_ops.file_changes
            ],
            "counters": {
                "task_id_counter": self.memory_ops.task_id_counter,
                "code_id_counter": self.memory_ops.code_id_counter,
            },
        }

    def import_memory_state(self, state: Dict[str, Any]) -> bool:
        """
        Import memory state from dictionary.

        Args:
            state: Dictionary containing memory state

        Returns:
            bool: True if import was successful
        """
        try:
            # Import tasks
            for task_id, task_data in state.get("tasks", {}).items():
                task = Task(
                    id=task_data["id"],
                    description=task_data["description"],
                    status=TaskStatus(task_data["status"]),
                    created_at=datetime.fromisoformat(task_data["created_at"]),
                    updated_at=datetime.fromisoformat(task_data["updated_at"]),
                )
                self.memory_ops.tasks[task_id] = task

            # Import code snippets
            for code_id, code_data in state.get("code_snippets", {}).items():
                code = CodeSnippet(
                    id=code_data["id"],
                    file_path=code_data["file_path"],
                    start_line=code_data["start_line"],
                    end_line=code_data["end_line"],
                    description=code_data["description"],
                    content=code_data.get(
                        "content", ""
                    ),  # Handle backward compatibility
                    created_at=datetime.fromisoformat(code_data["created_at"]),
                )
                self.memory_ops.code_snippets[code_id] = code

            # Import history
            for entry_data in state.get("history", []):
                entry = HistoryEntry(
                    timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                    summary=entry_data["summary"],
                    iteration_id=entry_data.get("iteration_id"),
                )
                self.memory_ops.history.append(entry)

            # Import file changes
            for change_data in state.get("file_changes", []):
                change = FileChange(
                    path=change_data["path"],
                    operation=change_data["operation"],
                    timestamp=datetime.fromisoformat(change_data["timestamp"]),
                )
                self.memory_ops.file_changes.append(change)

            # Import counters
            counters = state.get("counters", {})
            self.memory_ops.task_id_counter = counters.get("task_id_counter", 0)
            self.memory_ops.code_id_counter = counters.get("code_id_counter", 0)

            return True

        except Exception as e:
            print(f"Error importing memory state: {e}")
            return False
