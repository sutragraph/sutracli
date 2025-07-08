"""
Modular Sutra Memory Manager

A refactored version of the original SutraMemoryManager that uses separated components
for better maintainability and modularity.

This is the main interface that combines all the modular components:
- Models (Task, CodeSnippet, etc.)
- Memory Operations (task/code management)
- XML Processing (parsing and processing XML data)
- State Persistence (import/export)
- Memory Formatting (LLM context formatting)
"""

from typing import Dict, List, Optional, Any

from .models import Task, TaskStatus, CodeSnippet, FileChange, HistoryEntry
from .memory_operations import MemoryOperations
from .xml_processor import XMLProcessor
from .state_persistence import StatePersistence
from .memory_formatter import MemoryFormatter


class SutraMemoryManager:
    """
    Modular Sutra Memory Manager that orchestrates all memory management components.
    
    This class provides the same interface as the original SutraMemoryManager
    but uses separated, modular components internally.
    """

    def __init__(self, db_connection: Optional[Any] = None):
        # Initialize core components
        self.memory_ops = MemoryOperations(db_connection)
        self.xml_processor = XMLProcessor(self.memory_ops)
        self.state_persistence = StatePersistence(self.memory_ops)
        self.memory_formatter = MemoryFormatter(self.memory_ops)

    # ID Generation Methods
    def get_next_task_id(self) -> str:
        """Generate next unique task ID"""
        return self.memory_ops.get_next_task_id()

    def get_next_code_id(self) -> str:
        """Generate next unique code ID"""
        return self.memory_ops.get_next_code_id()

    # Task Management Methods
    def add_task(self, task_id: str, description: str, status: TaskStatus) -> bool:
        """Add a new task with validation"""
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
        """Add code snippet to memory"""
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

    def get_recent_history(self, count: int = 5) -> List[HistoryEntry]:
        """Get recent history entries"""
        return self.memory_ops.get_recent_history(count)

    # XML Processing Methods
    def process_sutra_memory_data(
        self, parsed_xml_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process already parsed Sutra Memory XML data from xmltodict"""
        return self.xml_processor.process_sutra_memory_data(parsed_xml_data)

    def extract_and_process_sutra_memory(
        self, xml_response: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract and process sutra memory from parsed XML response"""
        return self.xml_processor.extract_and_process_sutra_memory(xml_response)

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

    # Property Access for Backward Compatibility
    @property
    def tasks(self) -> Dict[str, Task]:
        """Access to tasks dictionary for backward compatibility"""
        return self.memory_ops.tasks

    @property
    def code_snippets(self) -> Dict[str, CodeSnippet]:
        """Access to code snippets dictionary for backward compatibility"""
        return self.memory_ops.code_snippets

    @property
    def history(self) -> List[HistoryEntry]:
        """Access to history list for backward compatibility"""
        return self.memory_ops.history

    @property
    def file_changes(self) -> List[FileChange]:
        """Access to file changes list for backward compatibility"""
        return self.memory_ops.file_changes

    @property
    def task_id_counter(self) -> int:
        """Access to task ID counter for backward compatibility"""
        return self.memory_ops.task_id_counter

    @property
    def code_id_counter(self) -> int:
        """Access to code ID counter for backward compatibility"""
        return self.memory_ops.code_id_counter

    @property
    def max_history_entries(self) -> int:
        """Access to max history entries for backward compatibility"""
        return self.memory_ops.max_history_entries

    @property
    def db_connection(self) -> Optional[Any]:
        """Access to database connection for backward compatibility"""
        return self.memory_ops.code_fetcher.db_connection


# Re-export models and utility functions for backward compatibility
from .models import TaskStatus, Task, CodeSnippet, FileChange, HistoryEntry
from .memory_formatter import clean_sutra_memory_content

__all__ = [
    'SutraMemoryManager',
    'TaskStatus',
    'Task', 
    'CodeSnippet',
    'FileChange',
    'HistoryEntry',
    'clean_sutra_memory_content'
]