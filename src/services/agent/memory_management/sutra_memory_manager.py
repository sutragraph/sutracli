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

from loguru import logger

from baml_client.types import (
    CodeStorageAction,
    SutraMemoryParams,
    TaskOperationAction,
    TracedElement,
    UntracedElement,
)

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
        is_traced: bool = False,
        root_elements: Optional[List[TracedElement]] = None,
        needs_tracing: Optional[List[UntracedElement]] = None,
        call_chain_summary: Optional[str] = None,
    ) -> bool:
        """Add code snippet to memory with optional tracing information (code_id is ignored, counter+1 used instead)"""
        return self.memory_ops.add_code_snippet(
            code_id,
            file_path,
            start_line,
            end_line,
            description,
            is_traced,
            root_elements,
            needs_tracing,
            call_chain_summary,
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
                        # Convert BAML TaskStatus to internal TaskStatus
                        status = (
                            TaskStatus(task_op.to_status.value.lower())
                            if task_op.to_status
                            else TaskStatus.PENDING
                        )

                        # add_task will use counter+1 internally and ignore the LLM provided ID
                        if task_op.description and self.add_task(
                            task_op.id, task_op.description, status
                        ):
                            # Get the actual ID that was assigned (current counter value)
                            actual_task_id = str(self.memory_ops.task_id_counter)
                            results["changes_applied"]["tasks"].append(
                                f"Added task {actual_task_id}: {task_op.description} (LLM ID {task_op.id} ignored)"
                            )
                        else:
                            if task_op.description:
                                results["errors"].append(
                                    f"Failed to add task (LLM ID {task_op.id})"
                                )
                            else:
                                results["errors"].append(
                                    f"Failed to add task - missing description (LLM ID {task_op.id})"
                                )

                    elif task_op.action == TaskOperationAction.Move:
                        # Convert BAML TaskStatus to internal TaskStatus
                        if task_op.to_status:
                            target_status = TaskStatus(task_op.to_status.value.lower())

                            if self.move_task(task_op.id, target_status):
                                results["changes_applied"]["tasks"].append(
                                    f"Moved task {task_op.id} to {target_status.value}"
                                )
                            else:
                                results["errors"].append(
                                    f"Failed to move task {task_op.id}"
                                )
                        else:
                            results["errors"].append(
                                f"Failed to move task {task_op.id} - missing to_status"
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
                        # Extract tracing information from BAML code operation
                        is_traced = code_op.is_traced if code_op.is_traced else False
                        call_chain_summary = (
                            code_op.call_chain_summary
                            if code_op.call_chain_summary
                            else None
                        )

                        # Use BAML root elements directly
                        root_elements = (
                            [code_op.root_element] if code_op.root_element else None
                        )

                        # Use BAML needs_tracing array directly
                        needs_tracing = (
                            code_op.needs_tracing if code_op.needs_tracing else []
                        )

                        # add_code_snippet will use counter+1 internally and ignore the LLM provided ID
                        if (
                            code_op.file
                            and code_op.start_line is not None
                            and code_op.end_line is not None
                            and code_op.description
                            and self.add_code_snippet(
                                code_op.id,
                                code_op.file,
                                code_op.start_line,
                                code_op.end_line,
                                code_op.description,
                                is_traced,
                                root_elements,
                                needs_tracing,
                                call_chain_summary,
                            )
                        ):
                            # Get the actual ID that was assigned (current counter value)
                            actual_code_id = str(self.memory_ops.code_id_counter)
                            results["changes_applied"]["code"].append(
                                f"Added code {actual_code_id}: {code_op.description} (LLM ID {code_op.id} ignored)"
                            )
                        else:
                            missing_fields = []
                            if not code_op.file:
                                missing_fields.append("file")
                            if code_op.start_line is None:
                                missing_fields.append("start_line")
                            if code_op.end_line is None:
                                missing_fields.append("end_line")
                            if not code_op.description:
                                missing_fields.append("description")

                            if missing_fields:
                                results["errors"].append(
                                    f"Failed to add code snippet - missing fields: {', '.join(missing_fields)} (LLM ID {code_op.id})"
                                )
                            else:
                                results["errors"].append(
                                    f"Failed to add code snippet (LLM ID {code_op.id})"
                                )

                    # elif code_op.action == CodeStorageAction.Remove:
                    #     if self.remove_code_snippet(code_op.id):
                    #         results["changes_applied"]["code"].append(
                    #             f"Removed code {code_op.id}"
                    #         )
                    #     else:
                    #         results["errors"].append(
                    #             f"Failed to remove code snippet {code_op.id}"
                    #         )

                    elif code_op.action == CodeStorageAction.UpdateTracingStatus:
                        # Update the tracing status of an existing code snippet
                        existing_snippet = self.get_code_snippet(code_op.id)
                        if existing_snippet:
                            existing_snippet.is_traced = (
                                code_op.is_traced if code_op.is_traced else False
                            )
                            results["changes_applied"]["code"].append(
                                f"Updated tracing status for code {code_op.id}: {existing_snippet.is_traced}"
                            )
                        else:
                            results["errors"].append(
                                f"Code snippet {code_op.id} not found for status update"
                            )

                    elif code_op.action == CodeStorageAction.MoveToTraced:
                        # Add an element to the hierarchical tree structure
                        existing_snippet = self.get_code_snippet(code_op.id)
                        if existing_snippet and code_op.traced_element:
                            traced_element = code_op.traced_element
                            element_name = traced_element.name
                            element_path = (
                                code_op.element_path if code_op.element_path else []
                            )

                            # Auto-generate ID if not provided
                            if not traced_element.id:
                                traced_element.id = (
                                    self.memory_ops.generate_element_id_from_signature(
                                        traced_element.name,
                                        traced_element.element_type,
                                        existing_snippet.file_path,
                                        getattr(traced_element, "start_line", 0),
                                        getattr(traced_element, "end_line", 0),
                                    )
                                )
                                # Recursively generate IDs for child elements
                                self.memory_ops._generate_ids_for_hierarchy(
                                    traced_element, existing_snippet.file_path
                                )

                            element_id = traced_element.id

                            # Check for duplicate elements by ID (hash-based IDs prevent duplicates automatically)
                            if any(
                                self._element_already_exists(root_elem, element_id)
                                for root_elem in existing_snippet.root_elements
                            ):
                                results["warnings"].append(
                                    f"Element {element_name} (ID: {element_id}) already exists in hierarchy for code {code_op.id} - skipping duplicate"
                                )
                                # Still remove from needs_tracing if source_element_id provided
                                source_element_id = code_op.source_element_id
                                if source_element_id:
                                    original_count = len(existing_snippet.needs_tracing)
                                    existing_snippet.needs_tracing = [
                                        ute
                                        for ute in existing_snippet.needs_tracing
                                        if ute.id != source_element_id
                                    ]
                                    if (
                                        len(existing_snippet.needs_tracing)
                                        < original_count
                                    ):
                                        results["changes_applied"]["code"].append(
                                            f"Removed {element_name} from needs_tracing for code {code_op.id} (duplicate element)"
                                        )
                                continue

                            # Find and remove the element from needs_tracing by ID
                            source_element_id = code_op.source_element_id
                            original_count = len(existing_snippet.needs_tracing)
                            if source_element_id:
                                existing_snippet.needs_tracing = [
                                    ute
                                    for ute in existing_snippet.needs_tracing
                                    if ute.id != source_element_id
                                ]
                            else:
                                # Fallback to name+type matching if no source_element_id provided
                                existing_snippet.needs_tracing = [
                                    ute
                                    for ute in existing_snippet.needs_tracing
                                    if not (
                                        ute.name == element_name
                                        and ute.element_type
                                        == traced_element.element_type
                                    )
                                ]

                            # Add to hierarchical structure
                            if not element_path:
                                # This is a root-level element
                                existing_snippet.root_elements.append(traced_element)
                                results["changes_applied"]["code"].append(
                                    f"Added {element_name} as root element for code {code_op.id}"
                                )
                            else:
                                # Add as child element following the element_path (using IDs)
                                # Find the correct root element to add to
                                target_root = None
                                for root_elem in existing_snippet.root_elements:
                                    if root_elem.id == element_path[0]:
                                        target_root = root_elem
                                        break

                                if target_root:
                                    self._add_to_hierarchy(
                                        target_root,
                                        traced_element,
                                        # Remove first element as we found the root
                                        element_path[1:],
                                    )
                                    results["changes_applied"]["code"].append(
                                        f"Added {element_name} to hierarchy for code {code_op.id}"
                                    )
                                else:
                                    logger.warning(
                                        f"Could not find root element with ID {element_path[0]} for element {element_name}"
                                    )
                                    results["warnings"].append(
                                        f"Could not find parent element for {element_name}"
                                    )

                            if len(existing_snippet.needs_tracing) < original_count:
                                results["changes_applied"]["code"].append(
                                    f"Removed {element_name} from needs_tracing for code {code_op.id}"
                                )
                        else:
                            results["errors"].append(
                                f"Code snippet {code_op.id} not found or traced_element missing"
                            )

                    elif code_op.action == CodeStorageAction.AddToNeedsTracing:
                        # Add elements to needs_tracing list
                        existing_snippet = self.get_code_snippet(code_op.id)
                        if existing_snippet and code_op.needs_tracing:
                            # Auto-generate IDs for new untraced elements if not provided
                            processed_needs_tracing = []
                            for ute in code_op.needs_tracing:
                                if not ute.id:
                                    ute.id = self.memory_ops.generate_element_id_from_signature(
                                        ute.name,
                                        ute.element_type,
                                        existing_snippet.file_path,
                                        0,  # UntracedElements don't have line numbers
                                        0,
                                    )
                                processed_needs_tracing.append(ute)

                            existing_snippet.needs_tracing.extend(
                                processed_needs_tracing
                            )
                            element_names = [
                                ute.name for ute in processed_needs_tracing
                            ]
                            results["changes_applied"]["code"].append(
                                f"Added {', '.join(element_names)} to needs_tracing for code {code_op.id}"
                            )
                        else:
                            results["errors"].append(
                                f"Code snippet {code_op.id} not found or needs_tracing missing"
                            )

                    elif code_op.action == CodeStorageAction.UpdateCallChainSummary:
                        # Update the call chain summary
                        existing_snippet = self.get_code_snippet(code_op.id)
                        if existing_snippet and code_op.call_chain_summary:
                            existing_snippet.call_chain_summary = (
                                code_op.call_chain_summary
                            )
                            results["changes_applied"]["code"].append(
                                f"Updated call chain summary for code {code_op.id}"
                            )
                        else:
                            results["errors"].append(
                                f"Code snippet {code_op.id} not found or call_chain_summary missing"
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

    def _add_to_hierarchy(
        self, root: TracedElement, new_element: TracedElement, element_path: List[str]
    ) -> None:
        """Add element to hierarchical tree structure following the element_path (using element IDs)"""
        # Prevent self-referencing
        if root.id and new_element.id and root.id == new_element.id:
            return

        if not element_path:
            # Add as direct child of root
            if root.accessed_elements is None:
                root.accessed_elements = []
            # Check for duplicates before adding (by ID if available, otherwise by name+type)
            if new_element.id:
                duplicate_exists = any(
                    child.id == new_element.id
                    for child in root.accessed_elements
                    if child.id
                )
            else:
                duplicate_exists = any(
                    child.name == new_element.name
                    and child.element_type == new_element.element_type
                    for child in root.accessed_elements
                )

            if not duplicate_exists:
                root.accessed_elements.append(new_element)
        else:
            # Navigate to the correct parent using element_path (IDs)
            current = root
            for path_element_id in element_path:
                if current.accessed_elements:
                    found = False
                    for child in current.accessed_elements:
                        if child.id and child.id == path_element_id:
                            current = child
                            found = True
                            break
                    if not found:
                        # Path element not found, add to root instead
                        current = root
                        break

            # Prevent adding element as child of itself
            if current.id and new_element.id and current.id == new_element.id:
                return

            # Add new_element as child of current
            if current.accessed_elements is None:
                current.accessed_elements = []
            # Check for duplicates before adding (by ID if available, otherwise by name+type)
            if new_element.id:
                duplicate_exists = any(
                    child.id == new_element.id
                    for child in current.accessed_elements
                    if child.id
                )
            else:
                duplicate_exists = any(
                    child.name == new_element.name
                    and child.element_type == new_element.element_type
                    for child in current.accessed_elements
                )

            if not duplicate_exists:
                current.accessed_elements.append(new_element)

    def _element_already_exists(self, root: TracedElement, element_id: str) -> bool:
        """Check if an element already exists in the hierarchy (using element ID)"""
        if root.id and root.id == element_id:
            return True

        if hasattr(root, "accessed_elements") and root.accessed_elements:
            for child in root.accessed_elements:
                if self._element_already_exists(child, element_id):
                    return True
        return False

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

    def set_project_info(self, project_info_content: str) -> bool:
        """Set project info content in memory operations"""
        return self.memory_ops.set_project_info(project_info_content)

    def get_project_info(self) -> Optional[str]:
        """Get project info content from memory operations"""
        return self.memory_ops.get_project_info()
