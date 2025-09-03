"""
Cross-Index System for coordinating analysis using existing agent tools

Enhanced version that integrates with Sutra memory and uses the new folder structure.
"""

from typing import Optional
from loguru import logger
from services.agent.session_management import SessionManager
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from .cross_indexing_task_manager import CrossIndexingTaskManager
from .cross_index_service import CrossIndexService
from .cross_index_phase import CrossIndexing
from src.graph.graph_operations import GraphOperations


class CrossIndexSystem:
    """
    Enhanced system for cross-index analysis using existing agent tools and Sutra memory.

    Coordinates the entire cross-indexing workflow with proper memory integration.
    """

    def __init__(
        self,
        project_manager,
        session_id: Optional[str] = None,
        project_name: Optional[str] = None,
    ):
        self.project_manager = project_manager

        # Store project name for incremental indexing
        self.project_name = project_name

        self.session_manager = SessionManager.get_or_create_session(session_id)

        # Initialize shared memory manager for cross-indexing (like agent service)
        self.memory_manager = SutraMemoryManager()
        self.graph_ops = GraphOperations()

        # Check if cross-indexing is already completed for this project
        if self.project_name:
            if self.graph_ops.is_cross_indexing_done(self.project_name):
                print(
                    f"✅ Cross-indexing already completed for project '{self.project_name}'"
                )
                print("📊 Skipping cross-indexing analysis - project already analyzed")
                self._skip_cross_indexing = True
            else:
                print(f"🔄 Starting cross-indexing for project '{self.project_name}'")
                self._skip_cross_indexing = False

                try:
                    self.project_manager.perform_incremental_indexing(self.project_name)
                    print(
                        f"✅ Incremental indexing completed for project '{self.project_name}'"
                    )
                except Exception as e:
                    logger.error(
                        f"Error during initialization incremental indexing: {e}"
                    )
                    # Continue with initialization even if incremental indexing fails
        else:
            logger.debug(
                "No project name provided, skipping incremental indexing during initialization"
            )
            self._skip_cross_indexing = False

        self.task_manager = CrossIndexingTaskManager()
        self.cross_indexing = CrossIndexing()

        self.cross_index_service = CrossIndexService(
            cross_indexing=self.cross_indexing,
            task_manager=self.task_manager,
            session_manager=self.session_manager,
            graph_ops=self.graph_ops,
        )

    def clear_session(self) -> None:
        """Clear the current cross-indexing session."""
        self.session_manager.clear_session()
