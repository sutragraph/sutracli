"""
Task Filter Prompt Manager

Orchestrates all prompt components for task filtering and deduplication.
"""

from loguru import logger
from .identity import TASK_FILTER_IDENTITY
from .objective import TASK_FILTER_OBJECTIVE
from .rules import TASK_FILTER_RULES
from .examples import TASK_FILTER_EXAMPLES
from services.agent.xml_service.xml_service import XMLService
from services.llm_clients.llm_factory import llm_client_factory
from typing import List
from services.agent.memory_management.models import Task


class TaskFilterPromptManager:
    """
    Prompt manager for task filtering and deduplication operations.
    
    Orchestrates all prompt components for task filtering:
    - Identity and role definition
    - Filtering objectives and rules
    - Examples and guidelines
    - Task analysis and output formatting
    """

    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        """
        Get the complete system prompt for task filtering.
        
        Returns:
            Complete system prompt string
        """
        return f"""{TASK_FILTER_IDENTITY}

{TASK_FILTER_OBJECTIVE}

{TASK_FILTER_RULES}

{TASK_FILTER_EXAMPLES}

# Sutra Memory Usage

You must use Sutra memory to create the filtered task list. Use this format:

<sutra_memory>
<task>
<add id="1" to="pending">First filtered task description</add>
<add id="2" to="pending">Second filtered task description</add>
<!-- Add more tasks as needed -->
</task>
<add_history>Brief summary of filtering actions performed</add_history>
</sutra_memory>

Always provide a complete filtered task list that eliminates duplicates while preserving all necessary functionality."""

    def get_user_prompt(self, tasks: List[Task], phase_info: str = "") -> str:
        """
        Get the user prompt for task filtering.
        
        Args:
            tasks: List of tasks to filter
            phase_info: Information about the current phase context
            
        Returns:
            User prompt string
        """
        # Format tasks for display
        task_list = self._format_tasks_for_prompt(tasks)
        
        user_prompt = f"""# Task Filtering Request

{phase_info}

## Tasks to Filter

The following tasks were created by the previous phase and need to be filtered for duplicates and optimized:

{task_list}

## Instructions

1. Analyze the above tasks for duplicates and similarities
2. Merge similar tasks while preserving all functionality
3. Optimize task descriptions for clarity and completeness
4. Create a clean, deduplicated task list using Sutra memory format
5. Provide a summary of filtering actions performed

Please provide the filtered task list now."""

        return user_prompt

    def _format_tasks_for_prompt(self, tasks: List[Task]) -> str:
        """
        Format tasks for display in the prompt.
        
        Args:
            tasks: List of tasks to format
            
        Returns:
            Formatted task string
        """
        if not tasks:
            return "No tasks to filter."
        
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append(f"- Task {task.id}: {task.description}")
        
        return "\n".join(formatted_tasks)

    def validate_response(self, response: str) -> bool:
        """
        Validate that the response contains proper Sutra memory format.
        
        Args:
            response: LLM response to validate
            
        Returns:
            True if response contains valid Sutra memory XML, False otherwise
        """
        try:
            xml_service = XMLService(llm_client_factory())
            xml_blocks = xml_service.parse_xml_response(response)

            # Check if any XML block contains sutra_memory with tasks
            for block in xml_blocks:
                if isinstance(block, dict) and "sutra_memory" in block:
                    sutra_memory = block["sutra_memory"]
                    if isinstance(sutra_memory, dict) and "task" in sutra_memory:
                        return True

            return False
        except Exception:
            # Fallback to simple string check if XML parsing fails
            return "sutra_memory" in response.lower() and "task" in response.lower()

    def extract_filtered_tasks(self, response: str) -> List[dict]:
        """
        Extract filtered tasks from the LLM response.

        Args:
            response: LLM response containing Sutra memory XML

        Returns:
            List of task dictionaries with id and description
        """
        try:
            xml_service = XMLService(llm_client_factory())
            xml_blocks = xml_service.parse_xml_response(response)

            for block in xml_blocks:
                if isinstance(block, dict) and "sutra_memory" in block:
                    sutra_memory = block["sutra_memory"]
                    if isinstance(sutra_memory, dict) and "task" in sutra_memory:
                        task_data = sutra_memory["task"]

                        # Handle both single task and multiple tasks
                        if isinstance(task_data, dict) and "add" in task_data:
                            add_data = task_data["add"]
                            if isinstance(add_data, list):
                                # Multiple tasks
                                tasks = []
                                for task_item in add_data:
                                    if isinstance(task_item, dict):
                                        # Extract description (ignore LLM-provided ID)
                                        description = (
                                            task_item.get("#text") or
                                            task_item.get("content") or
                                            task_item.get("text") or
                                            ""
                                        )
                                        if description.strip():
                                            tasks.append({
                                                "id": None,  # Will be assigned by task manager
                                                "description": description,
                                                "status": "pending"
                                            })
                                return tasks
                            elif isinstance(add_data, dict):
                                # Single task
                                description = (
                                    add_data.get("#text") or
                                    add_data.get("content") or
                                    add_data.get("text") or
                                    ""
                                )
                                if description.strip():
                                    return [{
                                        "id": None,  # Will be assigned by task manager
                                        "description": description,
                                        "status": "pending"
                                    }]

            return []
        except Exception as e:
            logger.error(f"Error extracting filtered tasks: {e}")
            return []
