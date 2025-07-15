"""
Sutra Memory Manager Operations

Core operations for managing tasks, code snippets, and file changes.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import os
from pathlib import Path

from .models import Task, TaskStatus, CodeSnippet, FileChange, HistoryEntry
from .code_fetcher import CodeFetcher


class MemoryOperations:
    """Handles core memory operations for tasks, code snippets, and file changes"""

    def __init__(self, db_connection: Optional[Any] = None):
        self.tasks: Dict[str, Task] = {}
        self.code_snippets: Dict[str, CodeSnippet] = {}
        self.history: List[HistoryEntry] = []
        self.file_changes: List[FileChange] = []
        self.task_id_counter = 0
        self.code_id_counter = 0
        self.max_history_entries = 20
        self.code_fetcher = CodeFetcher(db_connection)

    def get_next_task_id(self) -> str:
        """Generate next unique task ID"""
        self.task_id_counter += 1
        return str(self.task_id_counter)

    def get_next_code_id(self) -> str:
        """Generate next unique code ID"""
        self.code_id_counter += 1
        return str(self.code_id_counter)

    # Task Management Methods
    def add_task(self, task_id: str, description: str, status: TaskStatus) -> bool:
        """
        Add a new task with validation.

        Args:
            task_id: Unique task identifier
            description: Task description
            status: Task status

        Returns:
            bool: True if task was added successfully

        Raises:
            ValueError: If task_id already exists or if trying to add multiple current tasks
        """
        if task_id in self.tasks:
            raise ValueError(f"Task ID {task_id} already exists")

        if status == TaskStatus.CURRENT and self.get_current_task() is not None:
            raise ValueError("Only one current task is allowed at a time")

        self.tasks[task_id] = Task(id=task_id, description=description, status=status)

        # Update counter if task_id is numeric and higher than current counter
        try:
            task_num = int(task_id)
            if task_num > self.task_id_counter:
                self.task_id_counter = task_num
        except ValueError:
            pass

        return True

    def move_task(self, task_id: str, new_status: TaskStatus) -> bool:
        """
        Move task to new status with validation.

        Args:
            task_id: Task identifier
            new_status: New status for the task

        Returns:
            bool: True if task was moved successfully

        Raises:
            ValueError: If task doesn't exist or if trying to create multiple current tasks
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task ID {task_id} does not exist")

        if new_status == TaskStatus.CURRENT and self.get_current_task() is not None:
            current_task = self.get_current_task()
            if current_task.id != task_id:
                raise ValueError("Only one current task is allowed at a time")

        self.tasks[task_id].status = new_status
        self.tasks[task_id].updated_at = datetime.now()
        return True

    def remove_task(self, task_id: str) -> bool:
        """
        Remove task from memory.

        Args:
            task_id: Task identifier

        Returns:
            bool: True if task was removed successfully
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def get_current_task(self) -> Optional[Task]:
        """Get the current task if any"""
        for task in self.tasks.values():
            if task.status == TaskStatus.CURRENT:
                return task
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with specific status"""
        return [task for task in self.tasks.values() if task.status == status]

    def clear_completed_tasks(self) -> int:
        """Remove all completed tasks and return count of removed tasks"""
        completed_tasks = [
            task_id
            for task_id, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        ]

        for task_id in completed_tasks:
            del self.tasks[task_id]

        return len(completed_tasks)

    # Code Snippet Management Methods
    def add_code_snippet(
        self,
        code_id: str,
        file_path: str,
        start_line: int,
        end_line: int,
        description: str,
    ) -> bool:
        """
        Add code snippet to memory.

        Args:
            code_id: Unique code identifier
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number
            description: Description of the code snippet

        Returns:
            bool: True if code snippet was added successfully
        """
        try:
            # Check if code_id already exists and use next available integer ID
            if code_id in self.code_snippets:
                code_id = str(self.code_id_counter + 1)
                while code_id in self.code_snippets:
                    self.code_id_counter += 1
                    code_id = str(self.code_id_counter + 1)

            # Fetch code content using the code fetcher
            code_content = self.code_fetcher.fetch_code_from_file(
                file_path, start_line, end_line
            )

            # Update counter if code_id is numeric and higher than current counter
            try:
                code_num = int(code_id)
                if code_num > self.code_id_counter:
                    self.code_id_counter = code_num
            except ValueError:
                pass

            # Create and store the code snippet
            self.code_snippets[code_id] = CodeSnippet(
                id=code_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                description=description,
                content=code_content,
            )

            logger.debug(f"Code snippet {code_id} added successfully")
            return True

        except Exception as e:
            logger.error(f"Error adding code snippet {code_id}: {str(e)}")
            return False

    def remove_code_snippet(self, code_id: str) -> bool:
        """
        Remove code snippet from memory.

        Args:
            code_id: Code identifier

        Returns:
            bool: True if code snippet was removed successfully
        """
        if code_id in self.code_snippets:
            del self.code_snippets[code_id]
            return True
        return False

    def get_code_snippet(self, code_id: str) -> Optional[CodeSnippet]:
        """
        Get code snippet by ID.

        Args:
            code_id: Code identifier

        Returns:
            CodeSnippet or None if not found
        """
        return self.code_snippets.get(code_id)

    def get_all_code_snippets(self) -> Dict[str, CodeSnippet]:
        """
        Get all stored code snippets.

        Returns:
            Dictionary of code snippets
        """
        return self.code_snippets.copy()

    def get_code_snippets_by_file(self, file_path: str) -> List[CodeSnippet]:
        """
        Get all code snippets for a specific file.

        Args:
            file_path: Path to the file (can be relative or absolute)

        Returns:
            List of code snippets for the file
        """
        # Normalize the input file path
        normalized_input = os.path.normpath(file_path)
        
        matching_snippets = []
        for snippet in self.code_snippets.values():
            # Normalize the stored file path
            normalized_stored = os.path.normpath(snippet.file_path)
            
            # Check for exact match first
            if normalized_stored == normalized_input:
                matching_snippets.append(snippet)
                continue
            
            # Check if one is absolute and other is relative but point to same file
            try:
                # Convert both to absolute paths for comparison
                abs_input = str(Path(file_path).resolve())
                abs_stored = str(Path(snippet.file_path).resolve())
                
                if abs_input == abs_stored:
                    matching_snippets.append(snippet)
                    continue
                    
            except Exception:
                # If path resolution fails, fall back to basename comparison
                pass
            
            # Fall back to basename comparison (filename only)
            if os.path.basename(normalized_stored) == os.path.basename(normalized_input):
                # Additional check: ensure they're likely the same file
                # by checking if the relative path ends with the same structure
                if normalized_input.endswith(normalized_stored) or normalized_stored.endswith(os.path.basename(normalized_input)):
                    matching_snippets.append(snippet)
        
        return matching_snippets

    # File Change Tracking Methods
    def track_file_change(self, file_path: str, operation: str) -> bool:
        """
        Track file change.

        Args:
            file_path: Path to the file
            operation: Type of operation (modified, deleted, added)

        Returns:
            bool: True if file change was tracked successfully
        """
        if operation not in ["modified", "deleted", "added"]:
            raise ValueError(f"Invalid operation: {operation}")

        self.file_changes.append(FileChange(path=file_path, operation=operation))
        return True

    # History Management Methods
    def add_history(self, summary: str) -> bool:
        """
        Add history entry (mandatory in every response).

        Args:
            summary: Summary of current iteration actions and findings

        Returns:
            bool: True if history was added successfully
        """
        self.history.append(HistoryEntry(timestamp=datetime.now(), summary=summary))

        # Keep only last 20 entries
        if len(self.history) > self.max_history_entries:
            self.history = self.history[-self.max_history_entries :]

        return True
    
    def add_history_entry(self, history_entry: HistoryEntry) -> bool:
        """
        Add enhanced history entry with full details.

        Args:
            history_entry: Enhanced history entry with tool details

        Returns:
            bool: True if history was added successfully
        """
        self.history.append(history_entry)

        # Keep only last 20 entries
        if len(self.history) > self.max_history_entries:
            self.history = self.history[-self.max_history_entries :]

        return True

    def get_recent_history(self, count: int = 5) -> List[HistoryEntry]:
        """Get recent history entries"""
        return self.history[-count:] if count <= len(self.history) else self.history

    # Memory State Methods
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current memory state.

        Returns:
            Dict containing memory statistics and current state
        """
        current_task = self.get_current_task()

        return {
            "tasks": {
                "total": len(self.tasks),
                "current": current_task.description if current_task else None,
                "pending": len(self.get_tasks_by_status(TaskStatus.PENDING)),
                "completed": len(self.get_tasks_by_status(TaskStatus.COMPLETED)),
            },
            "code_snippets": {
                "total": len(self.code_snippets),
                "files": list(
                    set(code.file_path for code in self.code_snippets.values())
                ),
            },
            "history": {
                "total_entries": len(self.history),
                "recent_entries": len(self.get_recent_history()),
            },
            "file_changes": {
                "total": len(self.file_changes),
                "recent": [
                    (change.path, change.operation) for change in self.file_changes[-5:]
                ],
            },
        }

    def validate_memory_state(self) -> Dict[str, Any]:
        """
        Validate current memory state and return any issues.

        Returns:
            Dict containing validation results
        """
        issues = []
        warnings = []

        # Check for multiple current tasks
        current_tasks = self.get_tasks_by_status(TaskStatus.CURRENT)
        if len(current_tasks) > 1:
            issues.append(
                f"Multiple current tasks found: {[t.id for t in current_tasks]}"
            )

        # Check for missing history
        if not self.history:
            warnings.append(
                "No history entries found - history should be updated in every iteration"
            )

        # Check for stale completed tasks
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)
        if len(completed_tasks) > 10:
            warnings.append(
                f"Many completed tasks ({len(completed_tasks)}) - consider cleaning up"
            )

        # Check for too many code snippets
        if len(self.code_snippets) > 20:
            warnings.append(
                f"Many code snippets ({len(self.code_snippets)}) - consider cleanup"
            )

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def reset_memory(self) -> bool:
        """
        Reset all memory state (use with caution).

        Returns:
            bool: True if memory was reset successfully
        """
        self.tasks.clear()
        self.code_snippets.clear()
        self.history.clear()
        self.file_changes.clear()
        self.task_id_counter = 0
        self.code_id_counter = 0
        return True