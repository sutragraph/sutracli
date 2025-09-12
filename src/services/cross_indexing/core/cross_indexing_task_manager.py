"""
Cross-indexing task manager with proper phase management.
"""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from services.agent.memory_management.models import TaskStatus
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager


class CrossIndexingTaskManager(SutraMemoryManager):
    """
    Task manager for cross-indexing with proper phase management.

    Phase Flow:
    - Phase 1 & 2: Tasks are filtered and memory is cleared on phase transition
    - Phase 3, 4, 5: Memory is preserved across phases for code snippets
    """

    def __init__(self):
        super().__init__()
        self.current_phase = 1
        self._task_phase_metadata = {}
        self._initialize_default_tasks()

    def _initialize_default_tasks(self):
        """Initialize default tasks for Phase 1."""
        # Add default Phase 1 task - parent class will use counter-based ID
        super().add_task(
            "1",
            "Use list_files tool to find package files in this project that list all used packages. Store them in sutra memory history with file paths for future findings.",
            TaskStatus.CURRENT,
        )
        # Get the actual ID that was assigned (current counter value)
        task1_id = str(self.memory_ops.task_id_counter)

        super().add_task(
            "2",
            "Open each package file one by one by checking history to find all connection-related packages used for data communication. Create tasks for import pattern discovery based on findings. (NOTE: only mark this task completed after creating all tasks for finding imports based on packages in current files)",
            TaskStatus.PENDING,
        )
        # Get the actual ID that was assigned (current counter value)
        task2_id = str(self.memory_ops.task_id_counter)

        self._task_phase_metadata[task1_id] = {
            "created_in_phase": 1,
            "target_phase": 1,
            "is_default": True,
            "created_at": datetime.now().isoformat(),
        }
        self._task_phase_metadata[task2_id] = {
            "created_in_phase": 1,
            "target_phase": 1,
            "is_default": True,
            "created_at": datetime.now().isoformat(),
        }

    def set_current_phase(self, phase: int):
        """Set current phase and handle phase transitions."""
        if not (1 <= phase <= 5):
            raise ValueError(f"Invalid phase: {phase}. Must be 1-5.")

        old_phase = getattr(self, "current_phase", None)

        if old_phase is not None and old_phase != phase:
            logger.debug(f"Phase transition: {old_phase} → {phase}")

            # Clear memory for Phase 1→2 and Phase 2→3 transitions only
            if old_phase in [1, 2] and phase == old_phase + 1:
                self._clear_phase_memory()
                logger.debug(
                    f"Memory cleared for phase transition: {old_phase} → {phase}"
                )
            else:
                logger.debug(
                    f"Memory preserved for phase transition: {old_phase} → {phase}"
                )

        self.current_phase = phase

    def clear_phase_memory(self):
        """Public method to clear phase memory."""
        self._clear_phase_memory()

    def _clear_phase_memory(self):
        """Clear memory for phase transitions (only for Phase 1→2 and Phase 2→3)."""
        if hasattr(self, "memory_ops"):
            history_count = len(self.memory_ops.history)
            code_count = len(self.memory_ops.code_snippets)

            logger.debug(
                f"Clearing memory: {history_count} history entries, {code_count} code snippets"
            )

            self.memory_ops.history.clear()
            self.memory_ops.code_snippets.clear()
            self.memory_ops.code_id_counter = 0

    def get_tasks_for_phase(self, phase: int) -> Dict[str, List]:
        """Get tasks for a specific phase."""
        pending_tasks = self.get_tasks_by_status(TaskStatus.PENDING)
        current_task = self.get_current_task()
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)

        all_tasks = {
            "pending": pending_tasks,
            "current": [current_task] if current_task else [],
            "completed": completed_tasks,
        }

        phase_tasks = {"pending": [], "current": [], "completed": []}

        for category, tasks in all_tasks.items():
            for task in tasks:
                if task is None:
                    continue

                metadata = self._task_phase_metadata.get(task.id, {})
                target_phase = metadata.get("target_phase", phase)

                if target_phase == phase:
                    phase_tasks[category].append(task)

        return phase_tasks

    def add_task(
        self,
        task_id: str,
        description: str,
        status: TaskStatus = TaskStatus.PENDING,
        target_phase: Optional[int] = None,
    ) -> bool:
        """Add task with phase metadata (task_id is ignored, counter+1 used instead)."""
        # For phases 1 and 2, force status to PENDING to ensure proper phase transitions
        if self.current_phase in [1, 2]:
            actual_status = TaskStatus.PENDING
            logger.debug(
                f"Forcing task status to PENDING in phase {self.current_phase} (original status: {status})"
            )
        else:
            actual_status = status

        success = super().add_task(task_id, description, actual_status)

        if success:
            # Get the actual counter-based ID that was assigned by parent class
            actual_task_id = str(self.memory_ops.task_id_counter)

            # Set target phase based on your expected flow:
            # Phase 1 creates tasks → visible in Phase 2
            # Phase 2 creates tasks → visible in Phase 3
            # Phase 3 creates tasks → visible in Phase 3 (different rule)
            if target_phase is not None:
                actual_target_phase = target_phase
            elif self.current_phase == 3:
                # Phase 3 tasks are visible in Phase 3 (same phase)
                actual_target_phase = 3
            else:
                # Phase 1 & 2 tasks are visible in next phase
                actual_target_phase = self.current_phase + 1

            # Set metadata for new task using actual counter-based ID
            self._task_phase_metadata[actual_task_id] = {
                "created_in_phase": self.current_phase,
                "target_phase": actual_target_phase,
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            }

            logger.debug(
                f"Added task {actual_task_id} in Phase {self.current_phase} targeting Phase {actual_target_phase} "
                f"with status {actual_status} (LLM ID {task_id} ignored)"
            )

        return success

    def move_task(self, task_id: str, new_status: TaskStatus) -> bool:
        """Move task to new status while preserving phase metadata."""
        # Phase validation for phases 1 and 2 only
        if self.current_phase in [1, 2]:
            # Check if task exists and get its metadata
            if hasattr(self, "memory_ops") and task_id in self.memory_ops.tasks:
                metadata = self._task_phase_metadata.get(task_id, {})
                target_phase = metadata.get("target_phase", self.current_phase)

                # If task doesn't belong to current phase, silently ignore the operation
                if target_phase != self.current_phase:
                    logger.debug(
                        f"Silently ignoring move request for task {task_id} (target_phase={target_phase}) "
                        f"in current phase {self.current_phase}"
                    )
                    return True  # Return True to avoid showing error to LLM
            elif hasattr(self, "memory_ops") and task_id not in self.memory_ops.tasks:
                # Task doesn't exist at all, silently ignore
                logger.debug(
                    f"Silently ignoring move request for non-existent task {task_id} in phase {self.current_phase}"
                )
                return True  # Return True to avoid showing error to LLM

        # Call parent move_task method
        success = super().move_task(task_id, new_status)

        # Always update phase metadata for moved tasks, even if parent method returns False
        # This handles cases where LLM tries to move task to same status (e.g., current->current)
        if success or (
            task_id in self.memory_ops.tasks if hasattr(self, "memory_ops") else False
        ):
            # Ensure phase metadata is preserved for moved tasks
            if task_id not in self._task_phase_metadata:
                # If metadata is missing, create default metadata for current phase
                self._task_phase_metadata[task_id] = {
                    "created_in_phase": self.current_phase,
                    "target_phase": self.current_phase,
                    "is_default": False,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                # Special handling for completed tasks: they should remain visible in current phase only
                if new_status == TaskStatus.COMPLETED:
                    # Completed tasks remain visible in the phase where they were completed
                    self._task_phase_metadata[task_id][
                        "target_phase"
                    ] = self.current_phase
                    self._task_phase_metadata[task_id][
                        "completed_in_phase"
                    ] = self.current_phase
                else:
                    # For current/pending tasks, they remain visible in current phase
                    self._task_phase_metadata[task_id][
                        "target_phase"
                    ] = self.current_phase

            # If parent method failed but task exists, return True to indicate we handled the metadata update
            if not success and task_id in self.memory_ops.tasks:
                return True

        return success

    def get_memory_for_llm(self) -> str:
        """Get memory context for LLM including tasks for current phase."""
        content = [
            "ID FORMAT: All items use unique IDs for LLM operations (add_task, move_task, remove_task, add_code, remove_code)\n"
        ]

        # Get tasks for current phase
        phase_tasks = self.get_tasks_for_phase(self.current_phase)

        # Add current tasks
        current_tasks = phase_tasks.get("current", [])
        if current_tasks:
            content.append("CURRENT TASK:")
            task = current_tasks[0]  # Should only be one current task
            content.append(f"ID: {task.id}")
            content.append(f"Description: {task.description}")
            content.append("")

        # Add pending tasks for current phase
        pending_tasks = phase_tasks.get("pending", [])

        if pending_tasks:
            content.append("PENDING TASKS:")
            for task in pending_tasks:
                content.append(f"ID: {task.id}")
                content.append(f"Description: {task.description}")
                content.append("")

        # Add completed tasks for current phase (completed in this phase)
        completed_tasks = phase_tasks.get("completed", [])
        if completed_tasks:
            content.append("COMPLETED TASKS:")
            for task in completed_tasks:
                content.append(f"ID: {task.id}")
                content.append(f"Description: {task.description}")
                content.append("")

        # Add history from memory operations
        if hasattr(self, "memory_ops") and self.memory_ops.history:
            content.append("RECENT HISTORY:")
            recent_history = self.memory_ops.get_recent_history()
            for i, entry in enumerate(recent_history, 1):
                content.append(f"{i}. {entry.summary}")
            content.append("")

        # Add code snippets if any
        if hasattr(self, "memory_ops") and self.memory_ops.code_snippets:
            content.append("STORED CODE SNIPPETS:")
            content.append("")
            for code_id, snippet in self.memory_ops.code_snippets.items():
                content.append(f"ID: {code_id}")
                content.append(
                    f"File: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})"
                )
                content.append(f"Description: {snippet.description}")
                if snippet.content:
                    for line in snippet.content.split("\n"):
                        content.append(f"  {line}")
                    content.append("")
                else:
                    content.append("")

        return "\n".join(content)

    def clear_all_tasks_for_filtering(self):
        """Clear all tasks and metadata for task filtering."""
        # Log current state before clearing
        if hasattr(self, "memory_ops"):
            task_count = len(self.memory_ops.tasks)
            logger.debug(f"Clearing {task_count} tasks for filtering")
            self.memory_ops.tasks.clear()

        # Clear metadata
        metadata_count = len(self._task_phase_metadata)
        logger.debug(f"Clearing {metadata_count} task metadata entries")
        self._task_phase_metadata.clear()

        # Reset task counter
        self._reset_task_counter()
        logger.debug("Task counter reset to 0")

    def _reset_task_counter(self):
        """Reset task counter to 0."""
        if hasattr(self, "memory_ops"):
            self.memory_ops.task_id_counter = 0

    def add_filtered_task(
        self, task_id: str, description: str, created_in_phase: int, target_phase: int
    ) -> bool:
        """Add a filtered task with proper metadata (task_id is ignored, counter+1 used instead)."""
        success = super().add_task(task_id, description, TaskStatus.PENDING)

        if success:
            # Get the actual counter-based ID that was assigned by parent class
            actual_task_id = str(self.memory_ops.task_id_counter)

            self._task_phase_metadata[actual_task_id] = {
                "created_in_phase": created_in_phase,
                "target_phase": target_phase,
                "is_default": False,
                "is_filtered": True,
                "created_at": datetime.now().isoformat(),
            }

            logger.debug(
                f"Added filtered task {actual_task_id} (LLM ID {task_id} ignored)"
            )

        return success

    def get_current_phase_summary(self) -> str:
        """Get summary of current phase tasks."""
        phase_tasks = self.get_tasks_for_phase(self.current_phase)

        pending_count = len(phase_tasks.get("pending", []))
        current_count = len(phase_tasks.get("current", []))
        completed_count = len(phase_tasks.get("completed", []))

        return f"Phase {self.current_phase}: {pending_count} pending, {current_count} current, {completed_count} completed"

    def debug_log_tasks(self):
        """Log all tasks for debugging."""
        logger.debug(f"=== TASK DEBUG - Phase {self.current_phase} ===")

        all_pending = self.get_tasks_by_status(TaskStatus.PENDING)
        all_current = [self.get_current_task()] if self.get_current_task() else []
        all_completed = self.get_tasks_by_status(TaskStatus.COMPLETED)

        logger.debug(
            f"All tasks: pending={len(all_pending)}, current={len(all_current)}, completed={len(all_completed)}"
        )

        for task in all_pending:
            if task:
                metadata = self._task_phase_metadata.get(task.id, {})
                logger.debug(
                    f"Pending task {task.id}: created_in_phase={metadata.get('created_in_phase')}, target_phase={metadata.get('target_phase')}, completed_in_phase={metadata.get('completed_in_phase')}"
                )

        for task in all_current:
            if task:
                metadata = self._task_phase_metadata.get(task.id, {})
                logger.debug(
                    f"Current task {task.id}: created_in_phase={metadata.get('created_in_phase')}, target_phase={metadata.get('target_phase')}, completed_in_phase={metadata.get('completed_in_phase')}"
                )

        # Show filtered tasks for current phase
        phase_tasks = self.get_tasks_for_phase(self.current_phase)
        logger.debug(
            f"Filtered tasks for phase {self.current_phase}: pending={len(phase_tasks.get('pending', []))}, current={len(phase_tasks.get('current', []))}, completed={len(phase_tasks.get('completed', []))}"
        )
