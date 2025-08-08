"""
Cross-Indexing Task Manager

Manages task flow between phases in the cross-indexing system.
Extends the actual sutra memory manager to handle task transitions between phases.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from services.agent.memory_management.models import Task, TaskStatus
from ..task_filter.task_filter_manager import TaskFilterManager


class CrossIndexingTaskManager(SutraMemoryManager):
    """
    Task manager for cross-indexing system that extends sutra memory manager.
    
    Handles task management between phases:
    - Tasks created in one phase are not shown in the current phase
    - Tasks are automatically transferred to the next phase
    - Maintains task history and context across phases
    - Provides phase-specific task filtering
    """

    def __init__(self):
        # Initialize phase-specific attributes before calling parent
        self.current_phase = 1
        self.phase_names = {
            1: "Package Discovery",
            2: "Import Discovery",
            3: "Implementation Discovery",
            4: "Data Splitting",
            5: "Connection Matching",
        }
        # Store phase metadata for tasks
        self._task_phase_metadata: Dict[str, Dict[str, Any]] = {}

        # Initialize task filter manager
        self.task_filter_manager = TaskFilterManager()

        # Store filtered tasks for each phase
        self._filtered_tasks_cache: Dict[int, Dict[str, List[Task]]] = {}

        # Call parent constructor (which will call our _init_components override)
        super().__init__()

        # Add default task for Phase 1
        self._add_default_phase1_task()

    def _add_default_phase1_task(self) -> None:
        """Add default tasks for Phase 1 package discovery."""
        # Task 1: Use list_files tool to find package files
        task1_id = "1"
        task1_description = "Use list_files tool to find package files in this project that list all used packages. Store them in sutra memory history with file paths for future findings."

        # Task 2: Open and analyze package files
        task2_id = "2"
        task2_description = "Open each package file one by one by checking history to find all connection-related packages used for data communication. Create tasks for import pattern discovery based on findings. (NOTE: only mark this task completed after creating all tasks for finding imports based on packages in current files)"

        try:
            # Add first task as current
            self.add_task(task1_id, task1_description, TaskStatus.CURRENT)
            self._task_phase_metadata[task1_id] = {
                "created_in_phase": 1,
                "target_phase": 1,
                "is_default": True,
                "created_at": datetime.now().isoformat(),
            }

            # Add second task as pending
            self.add_task(task2_id, task2_description, TaskStatus.PENDING)
            self._task_phase_metadata[task2_id] = {
                "created_in_phase": 1,
                "target_phase": 2,  # Task 2 should target Phase 2
                "is_default": True,
                "created_at": datetime.now().isoformat(),
            }
        except ValueError:
            # Tasks already exist, skip
            pass

    def set_current_phase(self, phase: int) -> None:
        """
        Set the current phase for task management and clear memory for new phase.

        Args:
            phase: Phase number (1-5)
        """
        if 1 <= phase <= 5:
            # Store previous phase for filtering
            previous_phase = getattr(self, "current_phase", None)

            # Filter tasks when transitioning from Phase 1 to 2 or Phase 2 to 3
            # This happens BEFORE clearing tasks so we have tasks to filter
            if (previous_phase is not None and previous_phase != phase and
                previous_phase in [1, 2] and phase == previous_phase + 1):

                from loguru import logger
                logger.info(f"Transitioning from Phase {previous_phase} to Phase {phase} - triggering task filtering")

                # Filter tasks from the completed phase
                self.filter_tasks_for_next_phase(previous_phase)

            # Clear memory when moving to a new phase (except when setting initial phase)
            if hasattr(self, "current_phase") and self.current_phase != phase:
                self.clear_phase_memory()
                # Note: Task counter reset is handled in filter_tasks_for_next_phase

            self.current_phase = phase
        else:
            raise ValueError(f"Invalid phase number: {phase}. Must be 1-5.")

    def _reset_task_counter(self) -> None:
        """
        Reset the task counter to start fresh task ID generation for the new phase.

        This ensures clean task IDs starting from 1 in each phase.
        """
        from loguru import logger

        old_counter = getattr(self.memory_ops, 'task_id_counter', 0)
        self.memory_ops.task_id_counter = 0

        logger.debug(f"Reset task counter from {old_counter} to 0 for new phase")

    def _clear_all_tasks(self) -> None:
        """
        Clear all tasks and task metadata when transitioning to a new phase.
        This prevents ID conflicts when adding filtered tasks.
        """
        from loguru import logger

        # Count tasks before clearing
        all_tasks = (
            self.get_tasks_by_status(TaskStatus.PENDING) +
            self.get_tasks_by_status(TaskStatus.COMPLETED) +
            ([self.get_current_task()] if self.get_current_task() else [])
        )
        task_count = len([t for t in all_tasks if t is not None])

        logger.debug(f"Clearing {task_count} tasks for phase transition")

        # Clear all tasks from memory operations
        if hasattr(self, "memory_ops"):
            self.memory_ops.tasks.clear()

        # Clear all task metadata
        self._task_phase_metadata.clear()

        logger.debug("All tasks and metadata cleared for new phase")

    def add_task(self, task_id: str, description: str, status: TaskStatus = TaskStatus.PENDING,
                 target_phase: Optional[int] = None) -> bool:
        """
        Add a task with phase information.

        Args:
            task_id: Unique task identifier
            description: Task description
            status: Task status (pending, current, completed)
            target_phase: Phase where this task should be executed
        """
        # Determine target phase based on current phase:
        # Phase 1 → Phase 2, Phase 2 → Phase 3, Phase 3 → Phase 3
        # Phase 4, 5 → no tasks created
        if target_phase is None:
            if self.current_phase == 1:
                target_phase = 2
            elif self.current_phase == 2:
                target_phase = 3
            elif self.current_phase == 3:
                target_phase = 3  # Phase 3 tasks stay in Phase 3
            else:
                # Phase 4, 5 don't create tasks
                return False

        # Add task using parent method
        success = super().add_task(task_id, description, status)

        if success:
            # Store additional phase metadata
            self._task_phase_metadata[task_id] = {
                "created_in_phase": self.current_phase,
                "target_phase": target_phase,
                "is_default": False,
                "created_at": datetime.now().isoformat()
            }

            # Debug logging
            from loguru import logger

            logger.debug(
                f"Created task {task_id} in phase {self.current_phase} with target_phase {target_phase}, status {status.value}"
            )

        return success

    def get_current_phase_tasks(self) -> Dict[str, List[Task]]:
        """
        Get tasks that should be visible in the current phase.

        Rules:
        - Tasks created in Phase 1 will be displayed in Phase 2
        - Tasks created in Phase 2 will be displayed in Phase 3
        - Tasks created in Phase 3 will be displayed in Phase 3
        - Completed tasks in current phase will be displayed only in current phase
        - After each phase change all history will be cleared

        Returns:
            Dictionary with task categories (pending, current, completed)
        """
        all_tasks = {
            "pending": self.get_tasks_by_status(TaskStatus.PENDING),
            "current": [self.get_current_task()] if self.get_current_task() else [],
            "completed": self.get_tasks_by_status(TaskStatus.COMPLETED)
        }

        # Filter tasks based on phase rules
        filtered_tasks = {
            "pending": [],
            "current": [],
            "completed": []
        }

        # Debug logging
        from loguru import logger

        logger.debug(f"Getting tasks for current phase {self.current_phase}")
        logger.debug(
            f"All tasks: pending={len(all_tasks['pending'])}, current={len(all_tasks['current'])}, completed={len(all_tasks['completed'])}"
        )

        # Phase 4 and 5 have no tasks
        if self.current_phase >= 4:
            return filtered_tasks

        for category, tasks in all_tasks.items():
            for task in tasks:
                if task is None:
                    continue

                task_metadata = self._task_phase_metadata.get(task.id, {})
                created_in_phase = task_metadata.get("created_in_phase", self.current_phase)
                target_phase = task_metadata.get("target_phase", self.current_phase)
                is_default = task_metadata.get("is_default", False)
                completed_in_phase = task_metadata.get("completed_in_phase", None)

                should_show = False

                if self.current_phase == 1:
                    # Phase 1: Only show default tasks and completed tasks that were completed in Phase 1
                    if category == "completed":
                        # Show completed tasks that were completed in Phase 1
                        should_show = completed_in_phase == 1
                    else:
                        # Only show default task (tasks created in Phase 1 will show in Phase 2)
                        should_show = is_default

                elif self.current_phase == 2:
                    # Phase 2: Show tasks created in Phase 1 (pending/current) + completed tasks completed in Phase 2
                    if category in ["pending", "current"]:
                        # Show tasks created in Phase 1 (they have target_phase = 2)
                        should_show = (created_in_phase == 1 and target_phase == 2)
                    elif category == "completed":
                        # Show tasks completed in Phase 2
                        should_show = completed_in_phase == 2

                elif self.current_phase == 3:
                    # Phase 3: Show tasks created in Phase 2 + tasks created in Phase 3 + completed tasks completed in Phase 3
                    if category in ["pending", "current"]:
                        # Show tasks created in Phase 2 (target_phase = 3) OR tasks created in Phase 3 (target_phase = 3)
                        should_show = (created_in_phase == 2 and target_phase == 3) or (
                            created_in_phase == 3 and target_phase == 3
                        )
                    elif category == "completed":
                        # Show tasks completed in Phase 3
                        should_show = completed_in_phase == 3

                if should_show:
                    filtered_tasks[category].append(task)
                    logger.debug(
                        f"Showing task {task.id} in {category}: created_in_phase={created_in_phase}, target_phase={target_phase}, completed_in_phase={completed_in_phase}"
                    )
                else:
                    logger.debug(
                        f"Hiding task {task.id} in {category}: created_in_phase={created_in_phase}, target_phase={target_phase}, completed_in_phase={completed_in_phase}"
                    )

        logger.debug(
            f"Filtered tasks for phase {self.current_phase}: pending={len(filtered_tasks['pending'])}, current={len(filtered_tasks['current'])}, completed={len(filtered_tasks['completed'])}"
        )
        return filtered_tasks

    def get_tasks_for_phase(self, phase: int) -> Dict[str, List[Task]]:
        """
        Get all tasks targeted for a specific phase.
        
        Args:
            phase: Target phase number
            
        Returns:
            Dictionary with task categories for the specified phase
        """
        all_tasks = {
            "pending": self.get_tasks_by_status(TaskStatus.PENDING),
            "current": [self.get_current_task()] if self.get_current_task() else [],
            "completed": self.get_tasks_by_status(TaskStatus.COMPLETED)
        }

        phase_tasks = {
            "pending": [],
            "current": [],
            "completed": []
        }

        for category, tasks in all_tasks.items():
            for task in tasks:
                if task is None:
                    continue

                task_metadata = self._task_phase_metadata.get(task.id, {})
                target_phase = task_metadata.get("target_phase", phase)

                if target_phase == phase:
                    phase_tasks[category].append(task)

        return phase_tasks

    def move_task(self, task_id: str, new_status: TaskStatus) -> bool:
        """
        Move a task between statuses with phase awareness.

        Args:
            task_id: Task identifier
            new_status: New status

        Returns:
            True if task was moved successfully
        """
        success = super().move_task(task_id, new_status)

        if success and task_id in self._task_phase_metadata:
            self._task_phase_metadata[task_id]["updated_at"] = datetime.now().isoformat()

            # Track when task is completed
            if new_status == TaskStatus.COMPLETED:
                self._task_phase_metadata[task_id][
                    "completed_in_phase"
                ] = self.current_phase

                # Debug logging
                from loguru import logger

                logger.debug(f"Task {task_id} completed in phase {self.current_phase}")

        return success

    def remove_task(self, task_id: str) -> bool:
        """
        Remove task from memory with metadata cleanup.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was removed successfully
        """
        success = super().remove_task(task_id)

        if success and task_id in self._task_phase_metadata:
            del self._task_phase_metadata[task_id]

        return success

    def get_task_summary(self) -> Dict[str, Any]:
        """
        Get a summary of tasks across all phases.
        
        Returns:
            Summary dictionary with task counts and phase information
        """
        summary = {
            "current_phase": self.current_phase,
            "current_phase_name": self.phase_names.get(self.current_phase, "Unknown"),
            "visible_tasks": self.get_current_phase_tasks(),
            "total_tasks_by_phase": {}
        }

        # Count tasks by target phase
        for phase in range(1, 6):
            phase_tasks = self.get_tasks_for_phase(phase)
            total_count = sum(len(tasks) for tasks in phase_tasks.values())
            summary["total_tasks_by_phase"][phase] = {
                "phase_name": self.phase_names.get(phase, "Unknown"),
                "total_tasks": total_count,
                "pending": len(phase_tasks["pending"]),
                "current": len(phase_tasks["current"]),
                "completed": len(phase_tasks["completed"])
            }

        return summary

    def clear_phase_tasks(self, phase: int) -> None:
        """
        Clear all tasks for a specific phase.

        Args:
            phase: Phase number to clear tasks for
        """
        tasks_to_remove = []
        for task_id, metadata in self._task_phase_metadata.items():
            if metadata.get("target_phase") == phase:
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            self.remove_task(task_id)

    def clear_phase_memory(self) -> None:
        """
        Clear memory (history and code snippets) when moving to a new phase.
        This ensures each phase starts with a clean slate.

        Args:
            add_history_entry: Whether to add the "Started {phase} - Memory cleared" entry
        """
        if hasattr(self, "memory_ops"):
            from loguru import logger

            # Log what we're clearing
            history_count = len(self.memory_ops.history)
            code_count = len(self.memory_ops.code_snippets)
            logger.debug(
                f"Clearing phase memory: {history_count} history entries, {code_count} code snippets"
            )

            # Clear history to start fresh for new phase
            self.memory_ops.history.clear()

            # Clear code snippets to start fresh for new phase
            self.memory_ops.code_snippets.clear()

            # Reset code ID counter for new phase
            self.memory_ops.code_id_counter = 0

    def get_memory_for_llm(self) -> str:
        """
        Override base method to provide cross-indexing specific memory format.

        Returns:
            Formatted memory context string with cross-indexing specific format
        """
        content = [
            "ID FORMAT: All items use unique IDs for LLM operations (add_task, move_task, remove_task, add_code, remove_code)",
        ]

        # Add code snippets from base memory operations
        if hasattr(self, "memory_ops") and self.memory_ops.code_snippets:
            content.extend(["", "STORED CODE SNIPPETS:", ""])
            for code in self.memory_ops.code_snippets.values():
                content.extend(
                    [
                        f"Code {code.id}: {code.file_path} (lines {code.start_line}-{code.end_line})",
                        f"  Description: {code.description}",
                    ]
                )
                if code.content:
                    content.extend(["  Code:", "  ```"])
                    for line in code.content.split("\n"):
                        content.append(f"  {line}")
                    content.extend(["  ```", ""])
                else:
                    content.append("")

        # Add phase-specific task information for current phase
        visible_tasks = self.get_current_phase_tasks()

        if any(visible_tasks.values()):
            content.extend(["", "TASKS:", ""])
            for status, tasks in visible_tasks.items():
                if tasks:
                    content.append(f"{status.upper()} TASKS:")
                    for task in tasks:
                        content.append(f"- ID {task.id}: {task.description}")
                    content.append("")

        # Add recent history (last 20 entries) - CRITICAL for phase-specific history
        if hasattr(self, "memory_ops") and self.memory_ops.history:
            recent_history = self.memory_ops.get_recent_history(20)
            if recent_history:
                content.extend(["", "HISTORY:", ""])
                for i, entry in enumerate(reversed(recent_history), 1):
                    content.append(f"{i}. {entry.summary}")
                content.append("")

        return "\n".join(content)

    def get_memory_context_for_phase(self, phase: int) -> str:
        """
        Get memory context formatted for a specific phase.

        Args:
            phase: Phase number

        Returns:
            Formatted memory context string
        """
        old_phase = self.current_phase
        self.set_current_phase(phase)

        try:
            # Get memory context which now includes tasks via get_memory_for_llm() override
            context = self.get_memory_for_llm()
            return context
        finally:
            self.set_current_phase(old_phase)

    def filter_tasks_for_next_phase(self, completed_phase: int) -> bool:
        """
        Filter and deduplicate tasks created by a completed phase for the next phase.

        This method runs after Phase 1 and Phase 2 to clean up duplicate and similar
        tasks before they are displayed in the next phase.

        Args:
            completed_phase: The phase that just completed (1 or 2)

        Returns:
            True if filtering was successful, False otherwise
        """
        from loguru import logger

        # Only filter after Phase 1 and Phase 2
        if completed_phase not in [1, 2]:
            logger.debug(f"No task filtering needed for phase {completed_phase}")
            return True

        next_phase = completed_phase + 1
        logger.info(f"Starting task filtering after Phase {completed_phase} for Phase {next_phase}")

        try:
            # Get tasks created by the completed phase that target the next phase
            tasks_to_filter = []
            for task in self.get_tasks_by_status(TaskStatus.PENDING):
                task_metadata = self._task_phase_metadata.get(task.id, {})
                created_in_phase = task_metadata.get("created_in_phase")
                target_phase = task_metadata.get("target_phase")

                if created_in_phase == completed_phase and target_phase == next_phase:
                    tasks_to_filter.append(task)

            if not tasks_to_filter:
                logger.info(f"No tasks to filter from Phase {completed_phase}")
                return True

            logger.info(f"Found {len(tasks_to_filter)} tasks to filter from Phase {completed_phase}")

            # Prepare phase context information
            phase_info = f"Filtering tasks created by {self.phase_names.get(completed_phase, f'Phase {completed_phase}')} for {self.phase_names.get(next_phase, f'Phase {next_phase}')}"

            # Filter tasks using the task filter manager
            try:
                filtered_tasks = self.task_filter_manager.filter_tasks(
                    tasks_to_filter, phase_info
                )

                if not filtered_tasks:
                    logger.warning(
                        f"Task filtering returned no tasks for Phase {completed_phase}"
                    )
                    # Keep original tasks if filtering returns empty
                    filtered_tasks = tasks_to_filter

            except Exception as filter_error:
                logger.error(f"Task filtering failed: {filter_error}")
                # Keep original tasks if filtering fails completely
                filtered_tasks = tasks_to_filter

            # Clear all tasks now that we have the filtered tasks ready
            # This prevents ID conflicts when adding new tasks
            self._clear_all_tasks()

            # Reset task counter to 0 so filtered tasks get IDs starting from 1
            self._reset_task_counter()

            # Add filtered tasks to memory with proper metadata
            for i, filtered_task in enumerate(filtered_tasks, 1):
                # Generate unique task ID using counter (ignore LLM-provided ID)
                new_task_id = self.get_next_task_id()

                success = super().add_task(
                    new_task_id, filtered_task.description, TaskStatus.PENDING
                )

                if success:
                    # Store phase metadata for filtered task
                    self._task_phase_metadata[new_task_id] = {
                        "created_in_phase": completed_phase,
                        "target_phase": next_phase,
                        "is_default": False,
                        "is_filtered": True,
                        "original_task_count": len(tasks_to_filter),
                        "created_at": datetime.now().isoformat(),
                    }

            logger.info(f"Successfully filtered tasks: {len(tasks_to_filter)} -> {len(filtered_tasks)} tasks")
            return True

        except Exception as e:
            logger.error(f"Error during task filtering for Phase {completed_phase}: {e}")
            return False
