"""
Cross-Index System for coordinating analysis using existing agent tools

Enhanced version that integrates with Sutra memory and uses the new folder structure.
"""

from typing import Dict, Any, Optional
from loguru import logger

from graph.sqlite_client import SQLiteConnection
from services.project_manager import ProjectManager
from services.agent.xml_service.xml_parser import XMLParser

from ...agent.memory_management.sutra_memory_manager import SutraMemoryManager
from ..prompts.cross_index_prompt_manager import CrossIndexPromptManager
from .cross_index_service import CrossIndexService
from ..utils import infer_technology_type

class CrossIndexSystem:
    """
    Enhanced system for cross-index analysis using existing agent tools and Sutra memory.
    
    Coordinates the entire cross-indexing workflow with proper memory integration.
    """

    def __init__(
        self,
        db_connection: SQLiteConnection,
        project_manager: ProjectManager,
        session_id: Optional[str] = None,
        project_name: Optional[str] = None,
    ):
        self.db_connection = db_connection
        self.project_manager = project_manager

        # Store project name for incremental indexing
        self.project_name = project_name

        # Initialize session manager for cross-indexing (like agent service)
        from ...agent.session_management import SessionManager

        self.session_manager = SessionManager.get_or_create_session(session_id)

        # Initialize shared memory manager for cross-indexing (like agent service)
        self.memory_manager = SutraMemoryManager(db_connection=db_connection)

        # Set reasoning context for cross-indexing
        self.memory_manager.set_reasoning_context(
            "Cross-indexing analysis for incoming/outgoing connections"
        )

        # Perform incremental indexing once during initialization if project name is provided
        if self.project_name:
            logger.info(
                f"Performing incremental indexing for project '{self.project_name}' before cross-indexing initialization"
            )
            try:
                # Run incremental indexing synchronously during initialization
                self._perform_initialization_incremental_indexing()
                logger.info(
                    f"Incremental indexing completed for project '{self.project_name}'"
                )
            except Exception as e:
                logger.error(f"Error during initialization incremental indexing: {e}")
                # Continue with initialization even if incremental indexing fails
        else:
            logger.debug(
                "No project name provided, skipping incremental indexing during initialization"
            )

        # Initialize LLM client
        from ...llm_clients.llm_factory import llm_client_factory
        llm_client = llm_client_factory()

        # Initialize components with shared cross-index memory and session manager
        self.cross_index_service = CrossIndexService(
            db_connection, project_manager, self.memory_manager, self.session_manager, llm_client
        )
        self.prompt_manager = CrossIndexPromptManager()
        self.xml_parser = XMLParser()

    def _perform_initialization_incremental_indexing(self):
        """
        Perform incremental indexing synchronously during cross-indexing system initialization.
        This ensures the database is up-to-date before cross-indexing analysis begins.
        """
        try:
            logger.debug(
                f"Starting incremental indexing for project: {self.project_name}"
            )

            # Use project manager to perform incremental indexing
            # We consume the iterator to run it synchronously during initialization
            indexing_events = list(
                self.project_manager.perform_incremental_indexing(self.project_name)
            )

            # Check if indexing completed successfully
            indexing_success = False
            for event in indexing_events:
                if event.get("type") == "indexing_complete":
                    indexing_success = True
                    break
                elif event.get("type") == "error":
                    logger.warning(
                        f"Incremental indexing error: {event.get('message', 'Unknown error')}"
                    )

            if indexing_success:
                logger.info(
                    f"Incremental indexing completed successfully for project: {self.project_name}"
                )
                # Add to memory that incremental indexing was performed
                self.memory_manager.add_history(
                    f"Performed incremental indexing for project '{self.project_name}' before cross-indexing analysis"
                )
            else:
                logger.warning(
                    f"Incremental indexing may not have completed fully for project: {self.project_name}"
                )

        except Exception as e:
            logger.error(f"Error during initialization incremental indexing: {e}")
            raise

    def _update_session_memory(self):
        """Update session memory with current memory state (like agent service)."""
        try:
            # Get the rich formatted memory from memory manager (includes code snippets)
            memory_summary = self.memory_manager.get_memory_for_llm()
            # Update session manager with the rich memory content
            self.session_manager.update_sutra_memory(memory_summary)
            logger.debug(
                f"Updated Cross-Index Sutra Memory in session: {len(memory_summary)} characters"
            )
            logger.debug(
                f"Memory includes {len(self.memory_manager.get_all_code_snippets())} code snippets"
            )
        except Exception as e:
            logger.error(f"Error updating cross-index session memory: {e}")

    def start_cross_index_session(self, analysis_query: str) -> str:
        """Start a new cross-indexing analysis session (like agent service)."""
        query_id = self.session_manager.start_new_query(analysis_query)
        self.session_manager.set_problem_context(analysis_query)

        # Set reasoning context in memory manager
        self.memory_manager.set_reasoning_context(analysis_query)

        # Add analysis query to sutra memory at the start
        current_memory_rich = self.memory_manager.get_memory_for_llm()

        if current_memory_rich and current_memory_rich.strip():
            updated_memory = (
                f"{current_memory_rich}\n\nCROSS-INDEX ANALYSIS QUERY: {analysis_query}"
            )
        else:
            updated_memory = f"CROSS-INDEX ANALYSIS QUERY: {analysis_query}"
        self.session_manager.update_sutra_memory(updated_memory)

        return query_id

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current cross-indexing session."""
        return self.session_manager.get_conversation_summary()

    def clear_session(self) -> None:
        """Clear the current cross-indexing session."""
        self.session_manager.clear_session()

    def get_cross_index_system_prompt(self) -> str:
        """
        Generate the comprehensive cross-index system prompt for complete analysis.

        Args:
            existing_connections: Existing connections context string

        Returns:
            Complete system prompt for comprehensive cross-index analysis
        """

        return self.prompt_manager.cross_index_system_prompt()

    def store_connections(self, project_id: int, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store connections using the enhanced service with file_hash_id support.
        
        Args:
            project_id: Project ID
            analysis_result: Parsed analysis result
            
        Returns:
            Storage result
        """
        try:
            # Store connections with file_hash_id references
            result = self.cross_index_service.store_connections_with_file_hash_id(
                project_id, analysis_result
            )

            # Store potential matches if any
            if analysis_result.get("potential_matches"):
                matches_result = self.cross_index_service.create_connection_mappings_by_ids(
                    analysis_result["potential_matches"]
                )
                result["matches_result"] = matches_result

            # Add to Sutra memory
            if result.get("success"):
                summary = f"Stored cross-index connections for project {project_id}: "
                summary += f"{len(result.get('incoming_ids', []))} incoming, "
                summary += f"{len(result.get('outgoing_ids', []))} outgoing"
                self.memory_manager.add_history(summary)

            return result

        except Exception as e:
            logger.error(f"Error storing connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store connections"
            }

    def _process_parsed_analysis(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parsed XML data into the expected format.
        
        Args:
            parsed_data: Raw parsed XML data
            
        Returns:
            Processed analysis data
        """
        try:
            result = {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": []
            }

            # Extract cross_index_analysis root
            analysis_data = parsed_data.get("cross_index_analysis", {})

            # Process incoming connections
            incoming = analysis_data.get("incoming_connections", {})
            if incoming:
                connections = incoming.get("connection", [])
                if not isinstance(connections, list):
                    connections = [connections] if connections else []

                for conn in connections:
                    if isinstance(conn, dict):
                        # Parse snippet_lines
                        snippet_lines_str = conn.get("snippet_lines", "")
                        snippet_lines = []
                        if snippet_lines_str:
                            try:
                                snippet_lines = [int(x.strip()) for x in snippet_lines_str.split(",")]
                            except ValueError:
                                snippet_lines = []

                        result["incoming_connections"].append({
                            "description": conn.get("description", ""),
                            "file_path": conn.get("file_path", ""),
                            "snippet_lines": snippet_lines,
                            "technology": {
                                "name": conn.get("technology", "unknown"),
                                "type": infer_technology_type(conn.get("technology", ""))
                            }
                        })

            # Process outgoing connections
            outgoing = analysis_data.get("outgoing_connections", {})
            if outgoing:
                connections = outgoing.get("connection", [])
                if not isinstance(connections, list):
                    connections = [connections] if connections else []

                for conn in connections:
                    if isinstance(conn, dict):
                        # Parse snippet_lines
                        snippet_lines_str = conn.get("snippet_lines", "")
                        snippet_lines = []
                        if snippet_lines_str:
                            try:
                                snippet_lines = [int(x.strip()) for x in snippet_lines_str.split(",")]
                            except ValueError:
                                snippet_lines = []

                        result["outgoing_connections"].append({
                            "description": conn.get("description", ""),
                            "file_path": conn.get("file_path", ""),
                            "snippet_lines": snippet_lines,
                            "technology": {
                                "name": conn.get("technology", "unknown"),
                                "type": infer_technology_type(conn.get("technology", ""))
                            }
                        })

            # Process potential matches
            matches = analysis_data.get("potential_matches", {})
            if matches:
                match_list = matches.get("match", [])
                if not isinstance(match_list, list):
                    match_list = [match_list] if match_list else []

                for match in match_list:
                    if isinstance(match, dict):
                        try:
                            confidence = float(match.get("match_confidence", "0.0"))
                        except ValueError:
                            confidence = 0.0

                        result["potential_matches"].append({
                            "sender_id": match.get("sender_id"),
                            "receiver_id": match.get("receiver_id"),
                            "match_confidence": confidence,
                            "description": match.get("description", "")
                        })

            return result

        except Exception as e:
            logger.error(f"Error processing parsed analysis: {e}")
            return {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
                "error": str(e)
            }
