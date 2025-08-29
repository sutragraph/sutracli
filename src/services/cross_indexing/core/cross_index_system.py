"""
Cross-Index System for coordinating analysis using existing agent tools

Enhanced version that integrates with Sutra memory and uses the new folder structure.
"""

from typing import Optional
# from loguru import logger
# from services.project_manager import ProjectManager
# from services.agent.xml_service.xml_parser import XMLParser
# from ...agent.session_management import SessionManager
# from ...agent.memory_management.sutra_memory_manager import SutraMemoryManager
# from .cross_index_prompt_manager_5phase import CrossIndex5PhasePromptManager
# from .cross_index_service import CrossIndexService
# from src.graph.graph_operations import GraphOperations


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
        pass

    #     self.project_manager = project_manager

    #     # Store project name for incremental indexing
    #     self.project_name = project_name

    #     self.session_manager = SessionManager.get_or_create_session(session_id)

    #     # Initialize shared memory manager for cross-indexing (like agent service)
    #     self.memory_manager = SutraMemoryManager()
    #     self.graph_ops = GraphOperations()

    #     # Check if cross-indexing is already completed for this project
    #     if self.project_name:
    #         if self.graph_ops.is_cross_indexing_done(self.project_name):
    #             logger.info(
    #                 f"✅ Cross-indexing already completed for project '{self.project_name}'"
    #             )
    #             logger.info(
    #                 "📊 Skipping cross-indexing analysis - project already analyzed"
    #             )
    #             self._skip_cross_indexing = True
    #         else:
    #             print(f"🔄 Starting cross-indexing for project '{self.project_name}'")
    #             self._skip_cross_indexing = False

    #             try:
    #                 # Run incremental indexing synchronously during initialization
    #                 self._perform_initialization_incremental_indexing()
    #                 print(
    #                     f"✅ Incremental indexing completed for project '{self.project_name}'"
    #                 )
    #             except Exception as e:
    #                 logger.error(
    #                     f"Error during initialization incremental indexing: {e}"
    #                 )
    #                 # Continue with initialization even if incremental indexing fails
    #     else:
    #         logger.debug(
    #             "No project name provided, skipping incremental indexing during initialization"
    #         )
    #         self._skip_cross_indexing = False

    #     self.cross_index_service = CrossIndexService(
    #         project_manager, self.memory_manager, self.session_manager
    #     )
    #     self.prompt_manager = CrossIndex5PhasePromptManager()
    #     self.xml_parser = XMLParser()

    # def _perform_initialization_incremental_indexing(self):
    #     """
    #     Perform incremental indexing synchronously during cross-indexing system initialization.
    #     This ensures the database is up-to-date before cross-indexing analysis begins.
    #     """
    #     try:
    #         logger.debug(
    #             f"Starting incremental indexing for project: {self.project_name}"
    #         )

    #         # Use project manager to perform incremental indexing
    #         # We consume the iterator to run it synchronously during initialization
    #         indexing_events = list(
    #             self.project_manager.perform_incremental_indexing(self.project_name)
    #         )

    #         # Check if indexing completed successfully
    #         indexing_success = False
    #         for event in indexing_events:
    #             if event.get("type") == "indexing_complete":
    #                 indexing_success = True
    #                 break
    #             elif event.get("type") == "error":
    #                 logger.warning(
    #                     f"Incremental indexing error: {event.get('message', 'Unknown error')}"
    #                 )

    #         if indexing_success:
    #             self.memory_manager.add_history(
    #                 f"Performed incremental indexing for project '{self.project_name}' before cross-indexing analysis"
    #             )
    #         else:
    #             logger.warning(
    #                 f"Incremental indexing may not have completed fully for project: {self.project_name}"
    #             )

    #     except Exception as e:
    #         logger.error(f"Error during initialization incremental indexing: {e}")
    #         raise

    # def _update_session_memory(self):
    #     """Update session memory with current memory state (like agent service)."""
    #     try:
    #         # Get the rich formatted memory from task manager (includes code snippets)
    #         # Task manager is the authoritative source for cross-indexing memory
    #         memory_summary = self.prompt_manager.task_manager.get_memory_for_llm()
    #         code_snippets_count = len(
    #             self.prompt_manager.task_manager.get_all_code_snippets()
    #         )

    #         # Update session manager with the rich memory content
    #         self.session_manager.update_sutra_memory(memory_summary)
    #         logger.debug(
    #             f"Updated Cross-Index Sutra Memory in session: {len(memory_summary)} characters"
    #         )
    #         logger.debug(f"Memory includes {code_snippets_count} code snippets")
    #     except Exception as e:
    #         logger.error(f"Error updating cross-index session memory: {e}")

    # def clear_session(self) -> None:
    #     """Clear the current cross-indexing session."""
    #     self.session_manager.clear_session()

    # def mark_cross_indexing_phase_completed(self, phase: str) -> None:
    #     """Mark a specific phase of cross-indexing as completed."""
    #     if not self.project_name:
    #         return

    #     db_connection = self.project_manager.connection

    #     if phase == "phase4":
    #         db_connection.update_cross_indexing_status(
    #             self.project_name, "phase4_completed"
    #         )
    #         logger.info(
    #             f"✅ Phase 4 completed for project '{self.project_name}' - basic cross-indexing done"
    #         )
    #     elif phase == "phase5" or phase == "completed":
    #         db_connection.update_cross_indexing_status(self.project_name, "completed")
    #         logger.info(
    #             f"✅ Cross-indexing fully completed for project '{self.project_name}'"
    #         )

    # def should_skip_cross_indexing(self) -> bool:
    #     """Check if cross-indexing should be skipped for this project."""
    #     return getattr(self, "_skip_cross_indexing", False)
