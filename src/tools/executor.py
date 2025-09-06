"""
JSON-based Action Executor for processing LLM responses in JSON format.
Handles thinking, tool execution, and sutra memory updates.
"""

from typing import Optional
from graph.sqlite_client import SQLiteConnection
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from graph.project_indexer import ProjectIndexer


class ActionExecutor:
    """
    JSON-based action executor that processes LLM responses in JSON format.
    Each response contains: thinking, 1 tool, sutra memory updates
    """

    def __init__(
        self,
        sutra_memory_manager: Optional[SutraMemoryManager] = None,
        context: str = "agent",
    ):
        self.db_connection = SQLiteConnection()

        self.sutra_memory_manager = sutra_memory_manager or SutraMemoryManager()
        self.context = context  # Store context for database operations

        # Use shared project indexer if provided, otherwise create new one
        self.project_indexer = ProjectIndexer(self.sutra_memory_manager)

   