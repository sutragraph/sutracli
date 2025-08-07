"""
Task Filter Manager

Main orchestrator for LLM-based task filtering and deduplication operations.
"""

from typing import List, Optional, Any
from loguru import logger
from services.agent.memory_management.models import Task, TaskStatus
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from services.llm_clients.llm_factory import llm_client_factory
from services.agent.xml_service.xml_service import XMLService
from .prompts.task_filter_prompt_manager import TaskFilterPromptManager


class TaskFilterManager:
    """
    Main manager for LLM-based task filtering and deduplication operations.

    Provides intelligent task filtering using LLM-based analysis to eliminate
    duplicate and redundant tasks while preserving all necessary functionality.
    """

    def __init__(self, db_connection: Optional[Any] = None):
        """
        Initialize the task filter manager.

        Args:
            db_connection: Optional database connection for memory operations
        """
        self.prompt_manager = TaskFilterPromptManager()
        self.memory_manager = SutraMemoryManager(db_connection)
        self.llm_client = llm_client_factory()
        self.xml_service = XMLService(self.llm_client)

    def filter_tasks(self, tasks: List[Task], phase_info: str = "") -> List[Task]:
        """
        Filter and deduplicate a list of tasks using LLM-based analysis.

        Args:
            tasks: List of tasks to filter
            phase_info: Context information about the current phase

        Returns:
            List of filtered and deduplicated tasks
        """
        if not tasks:
            logger.info("No tasks to filter")
            return []

        logger.info(f"Starting LLM-based task filtering for {len(tasks)} tasks")

        # Use LLM to perform intelligent filtering
        filtered_tasks = self._llm_filter_tasks(tasks, phase_info)

        logger.info(f"Task filtering completed: {len(tasks)} -> {len(filtered_tasks)} tasks")
        return filtered_tasks

    def _llm_filter_tasks(self, tasks: List[Task], phase_info: str) -> List[Task]:
        """
        Use LLM to intelligently filter and deduplicate tasks with retry mechanism for XML parsing failures.

        Args:
            tasks: List of tasks to filter
            phase_info: Context information about the current phase

        Returns:
            List of filtered tasks
        """
        max_retries = 5
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # Prepare prompts
                system_prompt = self.prompt_manager.get_system_prompt()
                user_prompt = self.prompt_manager.get_user_prompt(tasks, phase_info)

                logger.debug(f"Sending task filtering request to LLM (attempt {retry_count + 1}/{max_retries})")

                # Get LLM response
                response = self.llm_client.call_llm(
                    system_prompt=system_prompt,
                    user_message=user_prompt,
                    return_raw=True  # Get raw response for XML parsing
                )

                # Validate response
                if not self.prompt_manager.validate_response(response):
                    error_msg = "Invalid LLM response for task filtering - XML validation failed"
                    logger.warning(f"{error_msg} (attempt {retry_count + 1}/{max_retries})")

                    # Try to fix the XML if we have retries left
                    if retry_count < max_retries - 1:
                        fixed_response = self.xml_service.repair_malformed_xml_in_text(response)
                        if fixed_response and fixed_response != response and self.prompt_manager.validate_response(fixed_response):
                            logger.info(f"Successfully fixed XML response on attempt {retry_count + 1}")
                            response = fixed_response
                        else:
                            last_error = error_msg
                            retry_count += 1
                            continue
                    else:
                        raise ValueError(error_msg)

                # Extract filtered tasks
                filtered_task_data = self.prompt_manager.extract_filtered_tasks(response)

                if not filtered_task_data:
                    error_msg = "No filtered tasks extracted from LLM response"
                    logger.warning(f"{error_msg} (attempt {retry_count + 1}/{max_retries})")

                    if retry_count < max_retries - 1:
                        last_error = error_msg
                        retry_count += 1
                        continue
                    else:
                        raise ValueError(error_msg)

                # Convert to Task objects
                filtered_tasks = []
                for task_data in filtered_task_data:
                    task = Task(
                        id=task_data["id"],
                        description=task_data["description"],
                        status=TaskStatus.PENDING
                    )
                    filtered_tasks.append(task)

                logger.info(f"Successfully filtered tasks using LLM: {len(tasks)} -> {len(filtered_tasks)} (attempt {retry_count + 1})")
                return filtered_tasks

            except Exception as e:
                retry_count += 1
                last_error = str(e)
                logger.warning(f"Error during LLM task filtering (attempt {retry_count}/{max_retries}): {e}")

                if retry_count >= max_retries:
                    logger.error(f"Task filtering failed after {max_retries} attempts. Last error: {last_error}")
                    raise Exception(f"Task filtering failed after {max_retries} attempts: {last_error}")
                else:
                    logger.info(f"Retrying task filtering (attempt {retry_count + 1}/{max_retries})")
                    continue
