"""
Cross-Index Service for analyzing and managing inter-service connections
"""

import json
from typing import Dict, List, Any, Optional, Iterator
from loguru import logger

from graph.sqlite_client import SQLiteConnection
from services.agent.session_management import SessionManager
from services.project_manager import ProjectManager
from services.llm_clients.llm_client_base import LLMClientBase
from services.agent.xml_service.xml_parser import XMLParser
from services.agent.xml_service.xml_repair import XMLRepair
from services.agent.xml_service import XMLService
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from services.agent.memory_management.code_fetcher import CodeFetcher
from services.agent.memory_management.models import TaskStatus
from ..prompts.cross_index_prompt_manager_5phase import CrossIndex5PhasePromptManager
from ...agent.tool_action_executor.tool_action_executor import ActionExecutor
from ..utils import infer_technology_type
from utils.debug_utils import get_user_confirmation_for_llm_call
from services.cross_indexing.code_manager.prompts.code_manager_prompt_manager import (
    CodeManagerPromptManager,
)


class CrossIndexService:
    """
    Enhanced service for managing cross-project connection analysis and storage.

    Key improvements:
    - Uses file_hash_id as foreign key instead of file paths
    - Stores only technology field, not library field
    - Returns only IDs in match responses
    - Integrates with Sutra memory for context
    - Uses existing XML response parser
    """

    def __init__(
        self,
        db_connection: SQLiteConnection,
        project_manager: ProjectManager,
        memory_manager: SutraMemoryManager,
        session_manager: SessionManager,
        llm_client: LLMClientBase,
    ):
        self.db_connection = db_connection
        self.project_manager = project_manager
        self.memory_manager = memory_manager
        self.session_manager = session_manager
        self.llm_client = llm_client
        self.xml_parser = XMLParser()
        self.xml_repair = XMLRepair(llm_client)
        self.xml_service = XMLService(llm_client)
        self.prompt_manager = CrossIndex5PhasePromptManager(db_connection)
        self.code_manager_prompt_manager = CodeManagerPromptManager()
        self.code_fetcher = CodeFetcher(db_connection)
        self.action_executor = ActionExecutor(
            db_connection,
            self.project_manager.vector_db,
            self.prompt_manager.task_manager,  # Use task manager instead of memory manager
            "cross_index",
        )
        self._memory_needs_update = False

    def analyze_project_connections(
        self, project_path: str, project_id: int
    ) -> Iterator[Dict[str, Any]]:
        """
        Perform cross-indexing analysis with streaming updates using yield.

        Args:
            project_path: Path to the project directory
            project_id: ID of the project in the database

        Yields:
            Progress updates and final analysis result
        """
        try:
            logger.debug(
                f"Starting cross-indexing analysis for project {project_id} at {project_path}"
            )

            # Yield initial status
            yield {
                "type": "cross_index_start",
                "project_id": project_id,
                "project_path": project_path,
                "message": "Starting cross-indexing analysis",
            }

            # Initialize analysis context
            analysis_query = f"Analyze project connections for: {project_path}"
            self.memory_manager.set_reasoning_context(analysis_query)

            # Clear memory at the start of new cross-indexing analysis
            logger.debug("Clearing memory for new cross-indexing analysis")
            # Reset to Phase 1 and clear memory
            self.prompt_manager.reset_to_phase(1)
            logger.debug("Reset to Phase 1 and cleared memory for new analysis")

            # Track last tool result for context
            last_tool_result = None

            # Analysis loop similar to agent service
            current_iteration = 0
            max_iterations = 100

            while current_iteration < max_iterations:
                current_iteration += 1
                logger.debug(f"Cross-indexing iteration {current_iteration}")

                # Yield iteration progress
                yield {
                    "type": "iteration_start",
                    "iteration": current_iteration,
                    "max_iterations": max_iterations,
                    "message": f"Starting iteration {current_iteration}",
                }

                try:
                    # Get XML response with proper context
                    xml_response = self._get_cross_index_xml_response(
                        analysis_query,
                        current_iteration,
                        last_tool_result,
                        project_path,
                    )

                    if last_tool_result and last_tool_result.get("tool_name") in [
                        "database",
                        "search_keyword",
                    ]:
                        # Only run code manager processing in phase 3 (Implementation Discovery)
                        if self.prompt_manager.current_phase == 3:
                            logger.debug(
                                f"Processing previous tool result ({last_tool_result.get('tool_name')}) with code manager after XML response but before processing (Phase 3)"
                            )
                            self._process_previous_tool_results_with_code_manager(
                                last_tool_result
                            )
                            # Update session memory immediately after code manager processing
                            # to ensure code snippets are available in the next iteration
                            logger.debug(
                                "Updating session memory after code manager processing"
                            )
                            self._update_session_memory()
                        else:
                            logger.debug(
                                f"Skipping code manager processing for tool {last_tool_result.get('tool_name')} - only runs in Phase 3 (current phase: {self.prompt_manager.current_phase})"
                            )

                    # Check if user cancelled the operation
                    if isinstance(xml_response, dict) and xml_response.get(
                        "user_cancelled"
                    ):
                        yield {
                            "type": "user_cancelled",
                            "iteration": current_iteration,
                            "message": xml_response.get(
                                "message", "User cancelled the operation"
                            ),
                        }
                        return

                    # Process XML response using action executor
                    task_complete = False
                    analysis_result = None

                    for event in self.action_executor.process_xml_response(
                        xml_response, analysis_query
                    ):
                        event_type = event.get("type", "unknown")

                        if event_type == "thinking":
                            yield {
                                "type": "thinking",
                                "iteration": current_iteration,
                                "content": event.get("content", "analyzing..."),
                            }

                        elif event_type == "tool_use":
                            tool_name = event.get("tool_name", "unknown")

                            last_tool_result = event

                            # Update Sutra memory with tool results
                            self._update_cross_index_memory(event)

                            # Mark memory for update (like agent service)
                            self._memory_needs_update = True

                            # Yield the original event as-is (like agent service)
                            yield event

                        elif event_type in ["completion", "task_complete"]:
                            # Handle completion events from attempt_completion tool
                            tool_name = event.get("tool_name", "attempt_completion")

                            if (
                                tool_name == "attempt_completion"
                                or event_type == "task_complete"
                            ):
                                # Mark that we need to check for phase advancement in the next iteration
                                # This ensures all XML processing (including task creation) is complete
                                task_complete = True
                                # Break out of the event processing loop immediately
                                break

                            # For Phase 3 completion, we'll handle Phase 4 transition later
                            # after all XML processing is complete

                        elif event_type == "tool_error":
                            error_msg = event.get("error", "Unknown error")
                            # Yield error update
                            yield {
                                "type": "tool_error",
                                "iteration": current_iteration,
                                "error": error_msg,
                                "message": f"Tool error in iteration {current_iteration}, continuing...",
                            }

                            # Update last_tool_result with the error event so it shows in next iteration's tool status
                            last_tool_result = event

                        elif event_type == "sutra_memory_update":
                            memory_result = event.get("result", {})
                            if memory_result.get("success"):
                                # Yield single memory update event
                                yield {
                                    "type": "memory_update",
                                    "iteration": current_iteration,
                                    "message": "Sutra memory updated with connection data",
                                }
                                # Mark memory for update (like agent service)
                                self._memory_needs_update = True

                        else:
                            # Yield other events as-is
                            yield event

                    # Handle phase advancement after all XML processing is complete
                    if task_complete:
                        current_phase = self.prompt_manager.current_phase

                        if current_phase < 3:
                            # Check if there are pending tasks for the next phase before advancing
                            next_phase = current_phase + 1
                            next_phase_tasks = (
                                self.prompt_manager.task_manager.get_tasks_for_phase(
                                    next_phase
                                )
                            )
                            pending_tasks = next_phase_tasks.get("pending", [])

                            # Debug logging
                            all_tasks = (
                                self.prompt_manager.task_manager.get_tasks_by_status(
                                    TaskStatus.PENDING
                                )
                            )
                            logger.debug(
                                f"Phase advancement check: current_phase={current_phase}, next_phase={next_phase}"
                            )
                            logger.debug(
                                f"All pending tasks in system: {len(all_tasks)} - {[task.id + ': ' + task.description[:30] + '...' for task in all_tasks]}"
                            )
                            logger.debug(
                                f"Tasks for phase {next_phase}: pending={len(pending_tasks)}, current={len(next_phase_tasks.get('current', []))}, completed={len(next_phase_tasks.get('completed', []))}"
                            )
                            if pending_tasks:
                                logger.debug(
                                    f"Pending tasks for phase {next_phase}: {[task.id + ': ' + task.description[:50] + '...' for task in pending_tasks]}"
                                )
                            else:
                                logger.debug(
                                    f"No pending tasks found for phase {next_phase}"
                                )

                            if pending_tasks:
                                # There are pending tasks for the next phase, advance to that phase
                                self.prompt_manager.advance_phase()
                                next_phase = self.prompt_manager.current_phase

                                # Clear last_tool_result when starting new phase
                                last_tool_result = None

                                print(
                                    f"🎯 Phase {current_phase} complete - advancing to Phase {next_phase}"
                                )
                                yield {
                                    "type": "phase_complete",
                                    "iteration": current_iteration,
                                    "current_phase": current_phase,
                                    "next_phase": next_phase,
                                    "message": f"Phase {current_phase} completed, advancing to Phase {next_phase}",
                                }
                                # Continue to next iteration to execute the tasks
                                continue
                            else:
                                # No pending tasks for next phase, skip to Phase 3
                                # Advance without adding history entries for skipped phases
                                while self.prompt_manager.current_phase < 3:
                                    self.prompt_manager.current_phase += 1
                                    # Set phase without adding history entry for skipped phases
                                    self.prompt_manager.task_manager.set_current_phase(
                                        self.prompt_manager.current_phase,
                                        add_history_entry=False,
                                    )

                                final_phase = self.prompt_manager.current_phase
                                # Clear last_tool_result when starting new phase
                                last_tool_result = None

                                print(
                                    f"🎯 Phase {current_phase} complete - no tasks for Phase {next_phase}, advancing to Phase {final_phase}"
                                )
                                yield {
                                    "type": "phase_complete",
                                    "iteration": current_iteration,
                                    "current_phase": current_phase,
                                    "next_phase": final_phase,
                                    "message": f"Phase {current_phase} completed, no tasks for Phase {next_phase}, advancing to Phase {final_phase}",
                                }
                                # Continue to next iteration in the new phase
                                continue

                    # Exit main loop if task completed (regardless of analysis_result success)
                    if task_complete:
                        # Only proceed with connection storage if we have analysis_result from Phase 4
                        if (
                            analysis_result
                            and isinstance(analysis_result, dict)
                            and "error" not in analysis_result
                        ):
                            # Check if both incoming and outgoing connections exist before proceeding
                            incoming_count = len(
                                analysis_result.get("incoming_connections", [])
                            )
                            outgoing_count = len(
                                analysis_result.get("outgoing_connections", [])
                            )

                            if incoming_count > 0 or outgoing_count > 0:
                                # Store connections in database with actual code snippets
                                storage_result = (
                                    self.store_connections_with_file_hash_id(
                                        project_id, analysis_result
                                    )
                                )

                                if storage_result.get("success"):
                                    logger.debug(
                                        f"Successfully stored connections: {storage_result.get('message')}"
                                    )

                                    # Get ALL existing connections from database (including old data)
                                    all_connections = (
                                        self.get_existing_connections_with_ids()
                                    )
                                    all_incoming = all_connections.get("incoming", [])
                                    all_outgoing = all_connections.get("outgoing", [])
                                    all_incoming_ids = [
                                        conn["id"] for conn in all_incoming
                                    ]
                                    all_outgoing_ids = [
                                        conn["id"] for conn in all_outgoing
                                    ]

                                    # Run connection matching if we have both types
                                    if (
                                        len(all_incoming_ids) > 0
                                        and len(all_outgoing_ids) > 0
                                    ):
                                        yield {
                                            "type": "connection_matching_start",
                                            "iteration": current_iteration,
                                            "message": f"🔗 Starting connection matching analysis...",
                                        }

                                        try:
                                            matching_result = (
                                                self._run_connection_matching(
                                                    all_incoming_ids,
                                                    all_outgoing_ids,
                                                )
                                            )

                                            # Check if user cancelled connection matching
                                            if matching_result.get("user_cancelled"):
                                                yield {
                                                    "type": "user_cancelled",
                                                    "iteration": current_iteration,
                                                    "message": "User cancelled connection matching",
                                                }
                                                return

                                            if matching_result.get("success"):
                                                yield {
                                                    "type": "cross_index_success",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_result": storage_result,
                                                    "matching_result": matching_result,
                                                    "message": f"🎉 Cross-indexing analysis completed successfully in {current_iteration} iterations",
                                                }
                                            else:
                                                yield {
                                                    "type": "cross_index_partial_success",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_result": storage_result,
                                                    "matching_error": matching_result.get(
                                                        "error"
                                                    ),
                                                    "message": f"Analysis and storage completed successfully, but connection matching failed: {matching_result.get('error')}",
                                                }
                                        except Exception as matching_error:
                                            logger.error(
                                                f"Error during connection matching: {matching_error}"
                                            )
                                            yield {
                                                "type": "cross_index_partial_success",
                                                "iteration": current_iteration,
                                                "analysis_result": analysis_result,
                                                "storage_result": storage_result,
                                                "matching_error": str(matching_error),
                                                "message": f"Analysis and storage completed successfully, but connection matching failed: {str(matching_error)}",
                                            }
                                    else:
                                        # Show results even with only one type of connection
                                        yield {
                                            "type": "cross_index_partial_success",
                                            "iteration": current_iteration,
                                            "analysis_result": analysis_result,
                                            "storage_result": storage_result,
                                            "message": f"Analysis completed with {incoming_count} incoming and {outgoing_count} outgoing connections. Connection matching skipped (requires both types).",
                                        }
                                else:
                                    logger.error(
                                        f"Failed to store connections: {storage_result.get('error')}"
                                    )
                                    yield {
                                        "type": "cross_index_storage_error",
                                        "iteration": current_iteration,
                                        "analysis_result": analysis_result,
                                        "storage_error": storage_result.get("error"),
                                        "message": f"Analysis completed but storage failed: {storage_result.get('error')}",
                                    }
                                return
                            else:
                                # No connections found at all
                                yield {
                                    "type": "cross_index_no_connections",
                                    "iteration": current_iteration,
                                    "message": f"No connections found in analysis.",
                                    "analysis_result": analysis_result,
                                }
                                return
                        elif analysis_result:
                            # We have analysis_result but it has errors
                            logger.info(
                                f"Analysis completed with some issues: {analysis_result.get('error')}"
                            )
                            yield {
                                "type": "analysis_warning",
                                "iteration": current_iteration,
                                "warning": analysis_result.get("error"),
                                "message": "Analysis completed with warnings but continuing",
                            }
                            return
                        else:
                            # Phase 3 completed but no analysis_result yet - need to proceed to Phase 4
                            current_phase = self.prompt_manager.current_phase
                            if current_phase == 3:
                                # Phase 3 complete - start Phase 4 (Data Splitting)
                                print(
                                    "🎯 Phase 3 complete - starting Phase 4 (Data Splitting)..."
                                )
                                yield {
                                    "type": "implementation_complete",
                                    "iteration": current_iteration,
                                    "message": "Implementation discovery completed, starting data splitting",
                                }

                                # Run Phase 4 - Data Splitting
                                splitting_result = self._run_phase4_data_splitting()

                                if splitting_result.get("success"):
                                    analysis_result = splitting_result.get(
                                        "analysis_result"
                                    )
                                    yield {
                                        "type": "data_splitting_complete",
                                        "iteration": current_iteration,
                                        "message": "Data splitting completed successfully",
                                    }

                                    # Now process the analysis_result for connection storage
                                    if (
                                        analysis_result
                                        and isinstance(analysis_result, dict)
                                        and "error" not in analysis_result
                                    ):
                                        # Check if both incoming and outgoing connections exist before proceeding
                                        incoming_count = len(
                                            analysis_result.get(
                                                "incoming_connections", []
                                            )
                                        )
                                        outgoing_count = len(
                                            analysis_result.get(
                                                "outgoing_connections", []
                                            )
                                        )

                                        if incoming_count > 0 or outgoing_count > 0:
                                            # Store connections in database with actual code snippets
                                            storage_result = self.store_connections_with_file_hash_id(
                                                project_id, analysis_result
                                            )

                                            if storage_result.get("success"):
                                                logger.debug(
                                                    f"Successfully stored connections: {storage_result.get('message')}"
                                                )
                                                yield {
                                                    "type": "connections_stored",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_result": storage_result,
                                                    "message": f"Connections stored successfully with {incoming_count} incoming and {outgoing_count} outgoing connections",
                                                }

                                                # Start Phase 5 - Connection Matching
                                                print(
                                                    "🎯 Phase 4 complete - starting Phase 5 (Connection Matching)..."
                                                )
                                                yield {
                                                    "type": "connection_matching_start",
                                                    "iteration": current_iteration,
                                                    "message": "Starting Phase 5 connection matching analysis",
                                                }

                                                # Run Phase 5 - Connection Matching
                                                matching_result = self._run_phase5_connection_matching(
                                                    project_id
                                                )

                                                if matching_result.get("success"):
                                                    yield {
                                                        "type": "cross_index_success",
                                                        "iteration": current_iteration,
                                                        "analysis_result": analysis_result,
                                                        "storage_result": storage_result,
                                                        "matching_result": matching_result,
                                                        "message": f"Cross-indexing completed successfully with connection matching: {matching_result.get('message')}",
                                                    }
                                                else:
                                                    yield {
                                                        "type": "cross_index_partial_success",
                                                        "iteration": current_iteration,
                                                        "analysis_result": analysis_result,
                                                        "storage_result": storage_result,
                                                        "matching_error": matching_result.get(
                                                            "error"
                                                        ),
                                                        "message": f"Analysis and storage completed successfully, but connection matching failed: {matching_result.get('error')}",
                                                    }
                                            else:
                                                yield {
                                                    "type": "cross_index_storage_error",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_error": storage_result.get(
                                                        "error"
                                                    ),
                                                    "message": f"Analysis completed but storage failed: {storage_result.get('error')}",
                                                }
                                        else:
                                            yield {
                                                "type": "cross_index_no_connections",
                                                "iteration": current_iteration,
                                                "message": "No connections found in analysis.",
                                                "analysis_result": analysis_result,
                                            }
                                else:
                                    yield {
                                        "type": "splitting_error",
                                        "iteration": current_iteration,
                                        "error": splitting_result.get("error"),
                                        "message": "Data splitting failed",
                                    }
                                return
                            else:
                                # Task completed in other phases without analysis_result
                                yield {
                                    "type": "phase_complete",
                                    "iteration": current_iteration,
                                    "current_phase": current_phase,
                                    "message": f"Phase {current_phase} completed",
                                }
                                return

                except Exception as iteration_error:
                    logger.error(
                        f"Error in cross-indexing iteration {current_iteration}: {iteration_error}"
                    )
                    yield {
                        "type": "iteration_error",
                        "iteration": current_iteration,
                        "error": str(iteration_error),
                        "message": f"Error in iteration {current_iteration}, continuing...",
                    }
                    # Continue to next iteration
                    continue

                # Update memory if needed before next iteration (like agent service)
                if self._memory_needs_update:
                    self._update_session_memory()
                    self._memory_needs_update = False

            # If we reach here, analysis didn't complete successfully
            yield {
                "type": "cross_index_failure",
                "iterations_completed": max_iterations,
                "error": f"Cross-indexing analysis did not complete after {max_iterations} iterations",
                "message": "Analysis failed to complete within iteration limit",
            }

        except Exception as e:
            logger.error(f"Error during cross-indexing analysis: {e}")
            yield {
                "type": "cross_index_error",
                "error": str(e),
                "message": "Critical error during cross-indexing analysis",
            }

    def _get_cross_index_xml_response(
        self,
        analysis_query: str,
        current_iteration: int,
        last_tool_result: Optional[Dict[str, Any]],
        project_path: str,
    ) -> Dict[str, Any]:
        """
        Get XML response from LLM with proper Sutra memory and tool status context.

        Args:
            analysis_query: The analysis query
            current_iteration: Current iteration number
            last_tool_result: Last tool execution result
            project_path: Path to the project being analyzed

        Returns:
            LLM response
        """
        try:
            if not get_user_confirmation_for_llm_call():
                logger.info("User cancelled Cross-indexing LLM call in debug mode")
                # Return a special marker to indicate user cancellation
                return {
                    "user_cancelled": True,
                    "message": "User cancelled the operation in debug mode",
                }

            # Get system prompt for current phase
            current_phase = self.prompt_manager.current_phase
            system_prompt = self.prompt_manager.get_system_prompt(current_phase)

            # Build tool status from last tool result
            tool_status = self._build_cross_index_tool_status(last_tool_result)

            # Get rich sutra memory from session manager first (for persistence), then memory manager
            session_memory = ""
            if self.session_manager:
                session_memory = self.session_manager.get_sutra_memory()

            # Use session memory if available, otherwise use task manager memory
            if session_memory and session_memory.strip():
                sutra_memory_rich = session_memory
                logger.debug("Using persisted session memory for cross-indexing")
            else:
                sutra_memory_rich = (
                    self.prompt_manager.task_manager.get_memory_for_llm()
                )
                logger.debug("Using task manager memory for cross-indexing")

            # Prepare memory context for phase-specific user prompt
            memory_context_parts = []

            # Add sutra memory - check for meaningful content
            logger.debug(
                f"Cross-Index Sutra memory length: {len(sutra_memory_rich) if sutra_memory_rich else 0}"
            )

            # Use task manager's memory context directly (includes base memory + tasks)
            old_phase = self.prompt_manager.task_manager.current_phase
            self.prompt_manager.task_manager.set_current_phase(
                self.prompt_manager.current_phase
            )
            try:
                memory_context = self.prompt_manager.task_manager.get_memory_for_llm()

                # Add tool status and reasoning checkpoint to task manager memory
                memory_context += f"\n\nTOOL STATUS:\n{tool_status}"

                reasoning_prompt = self.memory_manager.generate_reasoning_prompt(
                    analysis_query
                )
                if reasoning_prompt != "No previous tool executions found.":
                    memory_context += f"\n\nREASONING CHECKPOINT:\n{reasoning_prompt}"

                logger.debug(
                    f"Using task manager memory context: {len(memory_context)} characters"
                )
            finally:
                self.prompt_manager.task_manager.set_current_phase(old_phase)

            # Get phase-specific user prompt
            user_message = self.prompt_manager.get_user_prompt(
                analysis_query, memory_context
            )

            logger.debug(
                f"Cross-index iteration {current_iteration}: Sending prompt to LLM"
            )
            logger.debug(f"System prompt length: {len(system_prompt)}")
            logger.debug(f"User message length: {len(user_message)}")

            response = self.llm_client.call_llm(system_prompt, user_message)
            logger.debug(
                f"Cross-index iteration {current_iteration}: Got XML response from LLM"
            )

            # Try to repair malformed XML if needed
            if isinstance(response, str) and response.strip():
                try:
                    # Test if XML parsing would work
                    self.xml_parser.parse_single_xml_block(response)
                except Exception as xml_error:
                    logger.warning(
                        f"XML parsing failed, attempting repair: {xml_error}"
                    )
                    try:
                        repaired_response = (
                            self.xml_repair.repair_malformed_xml_in_text(response)
                        )
                        if repaired_response and repaired_response != response:
                            logger.info("Successfully repaired malformed XML")
                            return repaired_response
                        else:
                            logger.warning("XML repair did not improve the response")
                    except Exception as repair_error:
                        logger.error(f"XML repair failed: {repair_error}")
                        # Continue with original response

            return response

        except Exception as e:
            logger.error(f"Failed to get cross-index XML response: {e}")
            raise

    def _build_cross_index_tool_status(
        self, last_tool_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build tool status for cross-indexing context.

        Args:
            last_tool_result: Last tool execution result

        Returns:
            Formatted tool status string
        """
        if not last_tool_result:
            return "No previous tool execution in cross-indexing analysis"

        tool_name = last_tool_result.get("tool_name", "unknown_tool")

        if tool_name == "semantic_search":
            return self._build_semantic_status_cross_index(last_tool_result)
        elif tool_name == "search_keyword":
            return self._build_search_keyword_status_cross_index(last_tool_result)
        elif tool_name == "list_files":
            return self._build_list_files_status_cross_index(last_tool_result)
        elif tool_name == "database":
            return self._build_database_status_cross_index(last_tool_result)
        else:
            return self._build_generic_status_cross_index(last_tool_result, tool_name)

    def _build_semantic_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build semantic search status for cross-indexing."""
        status = "Tool: semantic_search\n"

        # Check if this is an error event (type: "tool_error") or success event (type: "tool_use")
        event_type = result.get("type", "unknown")

        if event_type == "tool_error":
            # Handle error events - they only have error and tool_name fields
            error = result.get("error", "Unknown error")
            status += f"ERROR: {error}\n"
        else:
            # Handle successful tool_use events
            query = result.get("query")
            if query and query != "fetch_next_code":
                status += f"Query: '{query}'\n"

            count = result.get("count") or result.get("total_nodes")
            if count is not None:
                status += f"Found {count} nodes for connection analysis\n"

            # Only check for error field if this is not already a tool_error event
            error = result.get("error")
            if error:
                status += f"ERROR: {error}\n"

            data = result.get("data", "")
            if data:
                status += f"Results:\n{data}"

        return status.rstrip()

    def _build_search_keyword_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build keyword search status for cross-indexing."""
        status = "Tool: search_keyword\n"

        event_type = result.get("type", "unknown")

        if event_type == "tool_error":
            error = result.get("error", "Unknown error")
            status += f"ERROR: {error}\n"
        else:
            # Handle successful tool_use events
            keyword = result.get("keyword")
            if keyword:
                status += f"Keyword: '{keyword}'\n"

            matches_found = result.get("matches_found")
            if matches_found is not None:
                matches_status = "Found" if matches_found else "Not Found"
                status += f"Matches Status: '{matches_status}'\n"

            # Only check for error field if this is not already a tool_error event
            error = result.get("error")
            if error:
                status += f"ERROR: {error}\n"

            data = result.get("data", "")
            if data:
                status += f"Results:\n{data}"

        return status.rstrip()

    def _build_list_files_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build list files status for cross-indexing."""
        status = "Tool: list_files\n"

        # Check if this is an error event (type: "tool_error") or success event (type: "tool_use")
        event_type = result.get("type", "unknown")

        if event_type == "tool_error":
            # Handle error events - they only have error and tool_name fields
            error = result.get("error", "Unknown error")
            status += f"ERROR: {error}\n"
        else:
            # Handle successful tool_use events
            directory = result.get("directory")
            if directory:
                status += f"Directory: {directory}\n"

            count = result.get("count")
            if count is not None:
                status += f"Files: {count} found\n"

            # Only check for error field if this is not already a tool_error event
            error = result.get("error")
            if error:
                status += f"ERROR: {error}\n"

            data = result.get("data", "")
            if data:
                status += f"Results:\n{data}"

        status += "\n\nNOTE: Store relevant file/folder information in Sutra memory's history section for connection analysis, as directory listings will not persist in next iterations."
        return status.rstrip()

    def _build_database_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build database status for cross-indexing."""
        status = "Tool: database\n"

        # Check if this is an error event (type: "tool_error") or success event (type: "tool_use")
        event_type = result.get("type", "unknown")

        if event_type == "tool_error":
            # Handle error events - they only have error and tool_name fields
            error = result.get("error", "Unknown error")
            status += f"ERROR: {error}\n"
        else:
            # Handle successful tool_use events
            query_name = result.get("query_name")
            if query_name:
                status += f"Query Name: {query_name}\n"

            query = result.get("query")
            if query:
                status += f"Query: {query}\n"

            count = result.get("count") or result.get("total_results")
            if count is not None:
                status += f"Results: {count} found\n"

            # Only check for error field if this is not already a tool_error event
            error = result.get("error")
            if error:
                status += f"ERROR: {error}\n"

            data = result.get("data", "")
            if data:
                status += f"Results:\n{data}"

        return status.rstrip()

    def _build_generic_status_cross_index(
        self, result: Dict[str, Any], tool_name: str
    ) -> str:
        """Build generic status for unknown tools in cross-indexing."""
        status = f"Tool: {tool_name}\n"

        # Check if this is an error event (type: "tool_error") or success event (type: "tool_use")
        event_type = result.get("type", "unknown")

        if event_type == "tool_error":
            # Handle error events - they only have error and tool_name fields
            error = result.get("error", "Unknown error")
            status += f"ERROR: {error}\n"
        else:
            # Handle successful tool_use events or other event types
            error = result.get("error")
            if error:
                status += f"ERROR: {error}\n"

            success = result.get("success")
            if success is not None:
                status += f"Status: {'success' if success else 'failed'}\n"

            data = result.get("data", "")
            if data:
                status += f"Results:\n{data}"

        return status.rstrip()

    def _update_cross_index_memory(self, event: Dict[str, Any]) -> None:
        """
        Update Sutra memory with cross-indexing specific context.

        Args:
            event: Tool execution event
        """
        try:
            tool_name = event.get("tool_name", "unknown")

            # Add cross-indexing context to memory updates
            if tool_name == "semantic_search":
                query = event.get("query", "")
                count = event.get("count", 0)
                if count > 0:
                    memory_entry = (
                        f"Cross-Index: Found {count} nodes for query '{query}'"
                    )
                    self.memory_manager.add_history(memory_entry)

            elif tool_name == "search_keyword":
                keyword = event.get("keyword", "")
                matches = event.get("matches_found", False)
                if matches:
                    memory_entry = f"Cross-Index: Found keyword '{keyword}'"
                    self.memory_manager.add_history(memory_entry)

            elif tool_name == "list_files":
                directory = event.get("directory", "")
                count = event.get("count", 0)
                memory_entry = f"Cross-Index: Listed {count} files in {directory}"
                self.memory_manager.add_history(memory_entry)

        except Exception as e:
            logger.error(f"Error updating cross-index memory: {e}")

    def _process_previous_tool_results_with_code_manager(
        self, event: Dict[str, Any]
    ) -> None:
        """
        Process previous tool results with code manager to extract connection code.
        Only processes database and search_keyword tools.

        Args:
            event: Tool execution event with results from previous iteration
        """
        try:
            tool_name = event.get("tool_name", "unknown")
            tool_result = event.get("data", "")

            if tool_name not in ["database", "search_keyword"]:
                logger.debug(
                    f"Skipping code manager processing for tool: {tool_name} (not database or search_keyword)"
                )
                return

            if not tool_result or tool_result.strip() == "":
                logger.debug(
                    f"Skipping code manager processing for tool: {tool_name} (no result data)"
                )
                return

            logger.info(
                f"Processing previous tool results with code manager for tool: {tool_name}"
            )

            formatted_tool_results = self._format_tool_results_for_code_manager(event)

            system_prompt = self.code_manager_prompt_manager.get_system_prompt()
            user_prompt = self.code_manager_prompt_manager.get_user_prompt(
                formatted_tool_results
            )

            logger.info(
                "Calling LLM with code manager prompt (separate system/user prompts)"
            )
            response = self.llm_client.call_llm(
                system_prompt, user_prompt, return_raw=True
            )

            if response:
                # Process code manager response to extract connection code
                self._process_code_manager_response(response)
                logger.info("Code manager processing completed")
            else:
                logger.warning("Empty response from code manager LLM call")

        except Exception as e:
            logger.error(
                f"Error processing previous tool results with code manager: {e}"
            )

    def _format_tool_results_for_code_manager(self, event: Dict[str, Any]) -> str:
        """
        Format tool execution event for code manager analysis.

        Args:
            event: Tool execution event

        Returns:
            Formatted tool results string
        """
        tool_result = event.get("data", "")

        result = f"""
Tool Results:
{tool_result}
"""

        return result

    def _process_code_manager_response(self, response: str) -> None:
        """
        Process code manager response and extract connection code XML.

        Args:
            response: Raw response from code manager LLM
        """
        try:
            logger.debug("Processing code manager response for connection code XML")

            # Parse XML response using existing XML service
            xml_blocks = self.xml_service.parse_xml_response(response)

            if xml_blocks:
                # Process connection code XML through task manager (not memory manager)
                # This ensures code snippets are added to the correct memory instance
                for xml_block in xml_blocks:
                    if isinstance(xml_block, dict) and "connection_code" in xml_block:
                        logger.info("Found connection_code XML from code manager")

                        result = self.prompt_manager.task_manager.xml_processor.process_sutra_memory_data(
                            xml_block
                        )

                        if result.get("success"):
                            logger.info(
                                f"Successfully processed connection code: {len(result.get('changes_applied', {}).get('code', []))} code snippets added"
                            )
                        else:
                            logger.warning(
                                f"Failed to process connection code: {result.get('errors', [])}"
                            )
            else:
                logger.debug("No connection code XML found in code manager response")

        except Exception as e:
            logger.error(f"Error processing code manager response: {e}")

    def _update_session_memory(self):
        """Update session memory with current memory state (like agent service)."""
        if not self.session_manager:
            logger.warning(
                "No session manager available for cross-index memory persistence"
            )
            return

        try:
            # Get the rich formatted memory from task manager (includes code snippets)
            # Use task manager instead of memory manager since that's where code snippets are stored
            memory_summary = self.prompt_manager.task_manager.get_memory_for_llm()
            # Update session manager with the rich memory content
            self.session_manager.update_sutra_memory(memory_summary)
            logger.debug(
                f"Updated Cross-Index Sutra Memory in session: {len(memory_summary)} characters"
            )
            logger.debug(
                f"Memory includes {len(self.prompt_manager.task_manager.get_all_code_snippets())} code snippets"
            )
        except Exception as e:
            logger.error(f"Error updating cross-index session memory: {e}")

    def _parse_connection_splitting_json(self, response_content: str) -> Dict[str, Any]:
        """
        Parse connection splitting JSON response format.

        Args:
            response_content: Raw JSON response from connection splitting prompt

        Returns:
            Parsed analysis data in the expected format
        """
        try:
            import re

            # Clean up response content - remove any markdown formatting
            response_text = response_content.strip()
            if response_text.startswith("```json"):
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif response_text.startswith("```"):
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()

            # Parse JSON directly
            try:
                json_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse connection splitting JSON: {e}")
                return {
                    "incoming_connections": [],
                    "outgoing_connections": [],
                    "potential_matches": [],
                    "error": f"Could not parse connection splitting response: {str(e)}",
                }

            # Convert the JSON format to our expected format
            result = {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
            }

            # Process incoming connections from JSON format
            incoming_data = json_data.get("incoming_connections", {})
            if isinstance(incoming_data, dict):
                for tech_name, files_data in incoming_data.items():
                    if isinstance(files_data, dict):
                        for file_path, connections in files_data.items():
                            if isinstance(connections, list):
                                for conn in connections:
                                    if isinstance(conn, dict):
                                        # Parse snippet_lines from range format (e.g., "15-20")
                                        snippet_lines = []
                                        snippet_range = conn.get("snippet_lines", "")
                                        if snippet_range and "-" in snippet_range:
                                            try:
                                                start, end = snippet_range.split("-")
                                                snippet_lines = list(
                                                    range(int(start), int(end) + 1)
                                                )
                                            except ValueError:
                                                snippet_lines = []

                                        result["incoming_connections"].append(
                                            {
                                                "description": conn.get(
                                                    "description", ""
                                                ),
                                                "file_path": file_path,
                                                "snippet_lines": snippet_lines,
                                                "technology": {
                                                    "name": tech_name,
                                                    "type": infer_technology_type(
                                                        tech_name
                                                    ),
                                                },
                                            }
                                        )

            # Process outgoing connections from JSON format
            outgoing_data = json_data.get("outgoing_connections", {})
            if isinstance(outgoing_data, dict):
                for tech_name, files_data in outgoing_data.items():
                    if isinstance(files_data, dict):
                        for file_path, connections in files_data.items():
                            if isinstance(connections, list):
                                for conn in connections:
                                    if isinstance(conn, dict):
                                        # Parse snippet_lines from range format (e.g., "15-20")
                                        snippet_lines = []
                                        snippet_range = conn.get("snippet_lines", "")
                                        if snippet_range and "-" in snippet_range:
                                            try:
                                                start, end = snippet_range.split("-")
                                                snippet_lines = list(
                                                    range(int(start), int(end) + 1)
                                                )
                                            except ValueError:
                                                snippet_lines = []

                                        result["outgoing_connections"].append(
                                            {
                                                "description": conn.get(
                                                    "description", ""
                                                ),
                                                "file_path": file_path,
                                                "snippet_lines": snippet_lines,
                                                "technology": {
                                                    "name": tech_name,
                                                    "type": infer_technology_type(
                                                        tech_name
                                                    ),
                                                },
                                            }
                                        )

            logger.debug(
                f"Parsed connection splitting response: {len(result['incoming_connections'])} incoming, {len(result['outgoing_connections'])} outgoing connections"
            )
            return result

        except Exception as e:
            logger.error(f"Error parsing connection splitting JSON: {e}")
            logger.error(f"Raw content: {response_content}")
            return {
                "error": str(e),
                "raw_content": response_content,
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
            }

    def _run_phase4_data_splitting(self) -> Dict[str, Any]:
        """
        Run Phase 4 - Data Splitting using the new 5-phase system.

        Returns:
            Result dictionary with splitting status and analysis data
        """
        try:
            logger.info("Starting Phase 4 - Data Splitting")

            # Get ONLY the code snippets stored by code manager (no tasks, no history)
            # Code snippets are stored in the task_manager, not memory_manager
            code_snippets = self.prompt_manager.task_manager.get_all_code_snippets()

            if not code_snippets:
                logger.warning(
                    "No code snippets found in task manager for Phase 4 data splitting"
                )
                return {
                    "success": False,
                    "error": "No code snippets available from code manager for data splitting",
                    "analysis_result": {
                        "incoming_connections": [],
                        "outgoing_connections": [],
                        "potential_matches": [],
                    },
                }

            # Format only the code snippets for Phase 4 processing
            formatted_snippets = []
            for code_id, snippet in code_snippets.items():
                formatted_snippets.append(
                    f"""Code {code_id}:
File: {snippet.file_path}
Lines: {snippet.start_line}-{snippet.end_line}
Description: {snippet.description}
Content:
{snippet.content}
---"""
                )

            memory_context = "\n".join(formatted_snippets)
            logger.debug(
                f"Phase 4 processing {len(code_snippets)} code snippets from code manager"
            )

            if not get_user_confirmation_for_llm_call():
                logger.info(
                    "User cancelled Phase 4 data splitting LLM call in debug mode"
                )
                return {
                    "success": False,
                    "user_cancelled": True,
                    "error": "User cancelled Phase 4 data splitting in debug mode",
                    "analysis_result": {
                        "incoming_connections": [],
                        "outgoing_connections": [],
                        "potential_matches": [],
                    },
                }

            # Get Phase 4 prompt manager
            phase4_manager = self.prompt_manager.phase4_manager

            # Get system and user prompts for Phase 4
            system_prompt = phase4_manager.get_system_prompt()
            user_prompt = phase4_manager.get_user_prompt(memory_context)

            # Retry logic for Phase 4 data splitting
            max_retries = 5
            last_error = None

            for attempt in range(max_retries):
                try:
                    logger.debug(
                        f"Phase 4 data splitting attempt {attempt + 1}/{max_retries}"
                    )

                    # Call LLM for Phase 4 data splitting
                    response = self.llm_client.call_llm(
                        system_prompt, user_prompt, return_raw=True
                    )

                    # Parse the JSON response directly
                    analysis_result = self._parse_connection_splitting_json(response)

                    # Check if we got valid results
                    if analysis_result and not analysis_result.get("error"):
                        logger.info(
                            f"Phase 4 data splitting completed successfully on attempt {attempt + 1}: "
                            f"{len(analysis_result['incoming_connections'])} incoming, "
                            f"{len(analysis_result['outgoing_connections'])} outgoing"
                        )

                        return {
                            "success": True,
                            "analysis_result": analysis_result,
                            "attempts_used": attempt + 1,
                        }
                    else:
                        last_error = analysis_result.get(
                            "error", "Invalid analysis result"
                        )
                        logger.warning(
                            f"Phase 4 data splitting attempt {attempt + 1} failed: {last_error}"
                        )

                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Phase 4 data splitting attempt {attempt + 1} failed with exception: {e}"
                    )

                # If not the last attempt, continue to retry
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying Phase 4 data splitting (attempt {attempt + 2}/{max_retries})"
                    )

            # All retries failed
            logger.error(
                f"Phase 4 data splitting failed after {max_retries} attempts. Last error: {last_error}"
            )
            return {
                "success": False,
                "error": f"Phase 4 data splitting failed after {max_retries} attempts. Last error: {last_error}",
                "analysis_result": {
                    "incoming_connections": [],
                    "outgoing_connections": [],
                    "potential_matches": [],
                },
                "attempts_used": max_retries,
            }

        except Exception as e:
            logger.error(f"Error during Phase 4 data splitting: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_result": {
                    "incoming_connections": [],
                    "outgoing_connections": [],
                    "potential_matches": [],
                },
            }

    def _run_phase5_connection_matching(self, project_id: int) -> Dict[str, Any]:
        """
        Run Phase 5 - Connection Matching using the new 5-phase system.
        Fetches all incoming and outgoing connections from database and performs matching.

        Args:
            project_id: Project ID to fetch connections for

        Returns:
            Result dictionary with matching status and results
        """
        try:
            logger.info("Starting Phase 5 - Connection Matching")

            # Fetch all incoming connections from database
            incoming_connections = self._get_all_incoming_connections(project_id)
            outgoing_connections = self._get_all_outgoing_connections(project_id)

            if not incoming_connections and not outgoing_connections:
                return {
                    "success": False,
                    "error": "No connections found in database for matching",
                    "message": "Phase 5 skipped - no connections to match",
                }

            if not incoming_connections:
                return {
                    "success": False,
                    "error": "No incoming connections found for matching",
                    "message": "Phase 5 skipped - no incoming connections",
                }

            if not outgoing_connections:
                return {
                    "success": False,
                    "error": "No outgoing connections found for matching",
                    "message": "Phase 5 skipped - no outgoing connections",
                }

            logger.info(
                f"Phase 5 processing {len(incoming_connections)} incoming and {len(outgoing_connections)} outgoing connections"
            )

            if not get_user_confirmation_for_llm_call():
                logger.info(
                    "User cancelled Phase 5 connection matching LLM call in debug mode"
                )
                return {
                    "success": False,
                    "user_cancelled": True,
                    "error": "User cancelled Phase 5 connection matching in debug mode",
                }

            # Get Phase 5 prompt manager
            phase5_manager = self.prompt_manager.phase5_manager

            # Get system and user prompts for Phase 5
            system_prompt = phase5_manager.get_system_prompt()
            user_prompt = phase5_manager.build_matching_prompt(
                incoming_connections, outgoing_connections, project_id
            )

            # Retry logic for Phase 5 connection matching
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    logger.debug(
                        f"Phase 5 connection matching attempt {attempt + 1}/{max_retries}"
                    )

                    # Call LLM for Phase 5 connection matching
                    response = self.llm_client.call_llm(
                        system_prompt, user_prompt, return_raw=True
                    )

                    # Parse and validate the matching response
                    matching_result = self._parse_connection_matching_json(response)

                    # Check if we got valid results
                    if matching_result and not matching_result.get("error"):
                        logger.info(
                            f"Phase 5 connection matching completed successfully on attempt {attempt + 1}"
                        )

                        if matching_result.get("matches"):
                            from services.cross_indexing.core.connection_matching_service import (
                                ConnectionMatchingService,
                            )

                            matching_service = ConnectionMatchingService()

                            # Store the matches in database
                            storage_result = matching_service._store_matching_results(
                                matching_result, project_id
                            )

                            if storage_result.get("success"):
                                logger.info(
                                    f"Stored {storage_result.get('total_stored', 0)} connection matches for project {project_id}"
                                )
                                # Add statistics to matching_result for CLI display
                                matching_result["statistics"] = {
                                    "total_matches": len(
                                        matching_result.get("matches", [])
                                    ),
                                    "stored_matches": storage_result.get(
                                        "total_stored", 0
                                    ),
                                }
                                return {
                                    "success": True,
                                    "matching_result": matching_result,
                                    "storage_result": storage_result,
                                    "attempts_used": attempt + 1,
                                    "message": f"Connection matching completed successfully with {len(matching_result['matches'])} matches",
                                }
                            else:
                                logger.error(
                                    f"Failed to store matches: {storage_result.get('error')}"
                                )
                                return {
                                    "success": False,
                                    "error": f"Matching completed but storage failed: {storage_result.get('error')}",
                                    "matching_result": matching_result,
                                }
                        else:
                            return {
                                "success": True,
                                "matching_result": matching_result,
                                "attempts_used": attempt + 1,
                                "message": "Connection matching completed - no matches found",
                            }
                    else:
                        last_error = matching_result.get(
                            "error", "Invalid matching result"
                        )
                        logger.warning(
                            f"Phase 5 connection matching attempt {attempt + 1} failed: {last_error}"
                        )

                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"Phase 5 connection matching attempt {attempt + 1} failed with exception: {e}"
                    )

                # If not the last attempt, continue to retry
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying Phase 5 connection matching (attempt {attempt + 2}/{max_retries})"
                    )

            # All retries failed
            logger.error(
                f"Phase 5 connection matching failed after {max_retries} attempts. Last error: {last_error}"
            )
            return {
                "success": False,
                "error": f"Phase 5 connection matching failed after {max_retries} attempts. Last error: {last_error}",
                "attempts_used": max_retries,
            }

        except Exception as e:
            logger.error(f"Error during Phase 5 connection matching: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Phase 5 connection matching failed due to unexpected error",
            }

    def _get_all_incoming_connections(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all incoming connections from database for a project.

        Args:
            project_id: Project ID

        Returns:
            List of incoming connection dictionaries
        """
        try:
            query = """
            SELECT id, technology_name, code_snippet, description, file_hash_id, snippet_lines
            FROM incoming_connections
            WHERE project_id = ?
            ORDER BY id
            """
            results = self.db_connection.execute_query(query, (project_id,))

            connections = []
            for row in results:
                connections.append(
                    {
                        "id": row["id"],
                        "technology": row["technology_name"],
                        "code_snippet": row["code_snippet"],
                        "description": row["description"],
                        "file_hash_id": row["file_hash_id"],
                        "snippet_lines": row["snippet_lines"],
                    }
                )

            logger.debug(
                f"Fetched {len(connections)} incoming connections for project {project_id}"
            )
            return connections

        except Exception as e:
            logger.error(f"Error fetching incoming connections: {e}")
            return []

    def _get_all_outgoing_connections(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all outgoing connections from database for a project.

        Args:
            project_id: Project ID

        Returns:
            List of outgoing connection dictionaries
        """
        try:
            query = """
            SELECT id, technology_name, code_snippet, description, file_hash_id, snippet_lines
            FROM outgoing_connections
            WHERE project_id = ?
            ORDER BY id
            """
            results = self.db_connection.execute_query(query, (project_id,))

            connections = []
            for row in results:
                connections.append(
                    {
                        "id": row["id"],
                        "technology": row[
                            "technology_name"
                        ],  # technology_name from DB mapped to technology
                        "code_snippet": row["code_snippet"],
                        "description": row["description"],
                        "file_hash_id": row["file_hash_id"],
                        "snippet_lines": row["snippet_lines"],
                    }
                )

            logger.debug(
                f"Fetched {len(connections)} outgoing connections for project {project_id}"
            )
            return connections

        except Exception as e:
            logger.error(f"Error fetching outgoing connections: {e}")
            return []

    def _parse_connection_matching_json(self, response: str) -> Dict[str, Any]:
        """
        Parse connection matching JSON response from LLM.

        Args:
            response: Raw LLM response

        Returns:
            Parsed matching result dictionary
        """
        try:
            import json

            # Clean the response
            response_content = response.strip()

            # Try to extract JSON from response if it's wrapped in other text
            if "```json" in response_content:
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                if end != -1:
                    response_content = response_content[start:end].strip()
            elif "{" in response_content and "}" in response_content:
                start = response_content.find("{")
                end = response_content.rfind("}") + 1
                response_content = response_content[start:end].strip()

            result = json.loads(response_content)

            # Validate structure
            if not isinstance(result, dict):
                return {"error": "Response is not a JSON object"}

            if "matches" not in result:
                return {"error": "Missing 'matches' field in response"}

            if not isinstance(result["matches"], list):
                return {"error": "'matches' field must be a list"}

            logger.debug(
                f"Successfully parsed connection matching JSON with {len(result['matches'])} matches"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing connection matching JSON: {e}")
            logger.error(f"Raw content: {response}")
            return {
                "error": str(e),
                "raw_content": response,
                "matches": [],
            }
        except Exception as e:
            logger.error(f"Error processing connection matching response: {e}")
            return {
                "error": str(e),
                "raw_content": response,
                "matches": [],
            }

    def get_existing_connections_with_ids(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve existing connections with IDs and file_hash_id references.

        Returns:
            Dictionary with 'incoming' and 'outgoing' connection lists including IDs
        """
        try:
            # Get incoming connections with file info
            incoming_query = """
                SELECT ic.id, ic.description, ic.project_id, 
                       fh.id as file_hash_id, fh.file_path, fh.language,
                       p.name as project_name
                FROM incoming_connections ic
                JOIN projects p ON ic.project_id = p.id
                LEFT JOIN file_hashes fh ON ic.file_hash_id = fh.id
                ORDER BY ic.created_at DESC
            """
            incoming_results = self.db_connection.execute_query(incoming_query)

            # Get outgoing connections with file info
            outgoing_query = """
                SELECT oc.id, oc.description, oc.project_id,
                       fh.id as file_hash_id, fh.file_path, fh.language,
                       p.name as project_name
                FROM outgoing_connections oc
                JOIN projects p ON oc.project_id = p.id
                LEFT JOIN file_hashes fh ON oc.file_hash_id = fh.id
                ORDER BY oc.created_at DESC
            """
            outgoing_results = self.db_connection.execute_query(outgoing_query)

            return {"incoming": incoming_results, "outgoing": outgoing_results}

        except Exception as e:
            logger.error(f"Error retrieving existing connections: {e}")
            return {"incoming": [], "outgoing": []}

    def store_connections_with_file_hash_id(
        self, project_id: int, connections_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store discovered connections using file_hash_id as foreign key.

        Args:
            project_id: ID of the project being analyzed
            connections_data: Dictionary containing connection data with file_hash_ids

        Returns:
            Result dictionary with success status and stored connection IDs
        """
        try:

            stored_incoming = []
            stored_outgoing = []

            # Store incoming connections
            if "incoming_connections" in connections_data:
                for conn in connections_data["incoming_connections"]:
                    # Get file_hash_id from file path - always retrieve from database
                    file_hash_id = self._get_file_hash_id(
                        project_id, conn.get("file_path")
                    )

                    # Fetch actual code snippet from line numbers
                    snippet_lines = conn.get("snippet_lines", [])
                    code_snippet = ""
                    if snippet_lines and conn.get("file_path"):
                        code_snippet = self._fetch_code_snippet_from_lines(
                            conn["file_path"], snippet_lines
                        )

                    cursor = self.db_connection.connection.execute(
                        """
                        INSERT INTO incoming_connections
                        (project_id, description, file_hash_id, snippet_lines, technology_name, code_snippet)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            conn["description"],
                            file_hash_id,
                            json.dumps(snippet_lines),
                            conn.get("technology", {}).get("name", "unknown"),
                            code_snippet,
                        ),
                    )
                    stored_incoming.append(cursor.lastrowid)

            # Store outgoing connections
            if "outgoing_connections" in connections_data:
                for conn in connections_data["outgoing_connections"]:
                    # Get file_hash_id from file path - always retrieve from database
                    file_hash_id = self._get_file_hash_id(
                        project_id, conn.get("file_path")
                    )

                    # Fetch actual code snippet from line numbers
                    snippet_lines = conn.get("snippet_lines", [])
                    code_snippet = ""
                    if snippet_lines and conn.get("file_path"):
                        code_snippet = self._fetch_code_snippet_from_lines(
                            conn["file_path"], snippet_lines
                        )

                    cursor = self.db_connection.connection.execute(
                        """
                        INSERT INTO outgoing_connections
                        (project_id, description, file_hash_id, snippet_lines, technology_name, code_snippet)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            conn["description"],
                            file_hash_id,
                            json.dumps(snippet_lines),
                            conn.get("technology", {}).get("name", "unknown"),
                            code_snippet,
                        ),
                    )
                    stored_outgoing.append(cursor.lastrowid)

            self.db_connection.connection.commit()

            logger.info(
                f"Stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections"
            )
            print(
                f"✅ Successfully stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections"
            )

            return {
                "success": True,
                "incoming_ids": stored_incoming,
                "outgoing_ids": stored_outgoing,
                "message": f"Successfully stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections",
            }

        except Exception as e:
            logger.error(f"Error storing connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store connections",
            }

    def create_connection_mappings_by_ids(
        self, matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create connection mappings using only IDs (no snippets or technology info).

        Args:
            matches: List of matches with sender_id and receiver_id

        Returns:
            Result dictionary with mapping creation status
        """
        try:
            created_mappings = []

            for match in matches:
                cursor = self.db_connection.connection.execute(
                    """
                    INSERT INTO connection_mappings (sender_id, receiver_id, connection_type, description, match_confidence)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        match.get("sender_id"),
                        match.get("receiver_id"),
                        match.get("connection_type", "unknown"),
                        match.get("description", "Auto-detected connection"),
                        match.get("match_confidence", 0.0),
                    ),
                )
                created_mappings.append(cursor.lastrowid)

            self.db_connection.connection.commit()

            return {
                "success": True,
                "mapping_ids": created_mappings,
                "message": f"Created {len(created_mappings)} connection mappings",
            }

        except Exception as e:
            logger.error(f"Error creating connection mappings: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create connection mappings",
            }

    def _get_file_hash_id(self, project_id: int, file_path: str) -> Optional[int]:
        """Get file_hash_id for a given project and file path."""
        try:
            if not file_path:
                logger.warning("Empty file_path provided to _get_file_hash_id")
                return None

            # Resolve relative paths to absolute paths
            import os
            from pathlib import Path

            # Convert to absolute path if it's relative
            if not os.path.isabs(file_path):
                absolute_file_path = str(Path(file_path).resolve())
                logger.debug(
                    f"Resolved relative path {file_path} to absolute path {absolute_file_path}"
                )
            else:
                absolute_file_path = file_path

            # Try with absolute path first
            result = self.db_connection.execute_query(
                "SELECT id FROM file_hashes WHERE project_id = ? AND file_path = ?",
                (project_id, absolute_file_path),
            )

            if result:
                file_hash_id = result[0]["id"]
                logger.debug(
                    f"Found file_hash_id {file_hash_id} for {absolute_file_path} in project {project_id}"
                )
                return file_hash_id

            # If not found with absolute path, try with original path (in case it was stored as relative)
            if absolute_file_path != file_path:
                result = self.db_connection.execute_query(
                    "SELECT id FROM file_hashes WHERE project_id = ? AND file_path = ?",
                    (project_id, file_path),
                )

                if result:
                    file_hash_id = result[0]["id"]
                    logger.debug(
                        f"Found file_hash_id {file_hash_id} for {file_path} (original path) in project {project_id}"
                    )
                    return file_hash_id

            # If still not found, try to find by filename match (fallback)
            filename = os.path.basename(file_path)
            if filename:
                result = self.db_connection.execute_query(
                    "SELECT id, file_path FROM file_hashes WHERE project_id = ? AND file_path LIKE ?",
                    (project_id, f"%{filename}"),
                )

                if result:
                    # If multiple matches, prefer exact filename match
                    for row in result:
                        if os.path.basename(row["file_path"]) == filename:
                            file_hash_id = row["id"]
                            logger.debug(
                                f"Found file_hash_id {file_hash_id} by filename match for {filename} -> {row['file_path']} in project {project_id}"
                            )
                            return file_hash_id

            logger.warning(
                f"No file_hash_id found for {file_path} (absolute: {absolute_file_path}) in project {project_id}"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting file_hash_id for {file_path}: {e}")
            return None

    def _fetch_code_snippet_from_lines(
        self, file_path: str, snippet_lines: List[int]
    ) -> str:
        """
        Fetch actual code snippet from file using line numbers.

        Args:
            file_path: Path to the file
            snippet_lines: List of line numbers to fetch

        Returns:
            str: Actual code snippet from the specified lines
        """
        try:
            if not snippet_lines:
                return ""

            # Get start and end line from the list
            start_line = min(snippet_lines)
            end_line = max(snippet_lines)

            # Use code fetcher to get actual code content
            code_snippet = self.code_fetcher.fetch_code_from_file(
                file_path, start_line, end_line
            )

            if code_snippet:
                logger.debug(
                    f"Fetched code snippet from {file_path} lines {start_line}-{end_line}: {len(code_snippet)} characters"
                )
                return code_snippet
            else:
                logger.warning(
                    f"No code content found for {file_path} lines {start_line}-{end_line}"
                )
                return ""

        except Exception as e:
            logger.error(f"Error fetching code snippet from {file_path}: {e}")
            return ""

    def _run_connection_matching(
        self, incoming_ids: List[int], outgoing_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Run connection matching analysis using LLM to match incoming and outgoing connections.

        Args:
            incoming_ids: List of stored incoming connection IDs
            outgoing_ids: List of stored outgoing connection IDs

        Returns:
            Result dictionary with matching status and created mappings
        """
        try:
            logger.info(
                f"📊 Analyzing {len(incoming_ids)} incoming and {len(outgoing_ids)} outgoing connections"
            )

            # Get connection details from database
            incoming_connections = self._get_connections_by_ids(
                incoming_ids, "incoming"
            )
            outgoing_connections = self._get_connections_by_ids(
                outgoing_ids, "outgoing"
            )

            if not incoming_connections or not outgoing_connections:
                return {
                    "success": False,
                    "error": "No connections found for matching",
                    "message": "Connection matching skipped - no connections to match",
                }

            # Get Phase 5 prompt manager and build prompts
            phase5_manager = self.prompt_manager.phase5_manager
            system_prompt = phase5_manager.get_system_prompt()
            user_prompt = phase5_manager.get_user_prompt(
                incoming_connections, outgoing_connections
            )

            if not get_user_confirmation_for_llm_call():
                logger.info(
                    "User cancelled Cross-indexing connection matching LLM call in debug mode"
                )
                return {
                    "success": False,
                    "user_cancelled": True,
                    "error": "User cancelled connection matching in debug mode",
                    "message": "Connection matching cancelled by user in debug mode",
                }

            # Call LLM for Phase 5 connection matching
            logger.debug("🔗 Starting Phase 5 connection matching analysis...")
            logger.debug(
                f"📊 Analyzing {len(incoming_connections)} incoming and {len(outgoing_connections)} outgoing connections"
            )
            response = self.llm_client.call_llm(
                system_prompt, user_prompt, return_raw=True
            )

            # Parse JSON response from raw text
            try:
                import json

                # Handle both string response and dict response
                if isinstance(response, str):
                    response_text = response
                else:
                    response_text = (
                        response.get("content", "")
                        if isinstance(response, dict)
                        else str(response)
                    )

                # Clean up response text - remove any markdown formatting
                response_text = response_text.strip()
                if response_text.startswith("```json"):
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()
                elif response_text.startswith("```"):
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    if end != -1:
                        response_text = response_text[start:end].strip()

                response_json = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse connection matching response as JSON: {e}"
                )
                logger.error(f"Raw response: {response}")
                return {
                    "success": False,
                    "error": f"Invalid JSON response from LLM: {str(e)}",
                    "message": "Connection matching failed due to invalid response format",
                }

            # Validate Phase 5 JSON response structure
            if not isinstance(response_json, dict) or "matches" not in response_json:
                logger.error(
                    f"Invalid Phase 5 matching response structure: {response_json}"
                )
                return {
                    "success": False,
                    "error": "Invalid response structure - missing 'matches' field",
                    "message": "Phase 5 connection matching failed due to invalid response structure",
                }

            # Create connection mappings in database
            matches = response_json.get("matches", [])
            if matches:
                # Convert matches to database format
                db_matches = []
                for match in matches:
                    db_matches.append(
                        {
                            "sender_id": match.get("outgoing_id"),
                            "receiver_id": match.get("incoming_id"),
                            "connection_type": match.get("connection_type", "api_call"),
                            "description": match.get(
                                "match_reason", "Auto-detected connection"
                            ),
                            "match_confidence": self._convert_confidence_to_float(
                                match.get("match_confidence", "medium")
                            ),
                        }
                    )

                # Store mappings in database
                mapping_result = self.create_connection_mappings_by_ids(db_matches)

                if mapping_result.get("success"):
                    print(f"🎯 Found {len(matches)} connection matches:")
                    for i, match in enumerate(matches, 1):
                        print(
                            f"   {i}. {match.get('match_reason', 'Unknown match')} (confidence: {match.get('match_confidence', 'unknown')})"
                        )
                    print(f"✅ Successfully created {len(matches)} connection mappings")
                    return {
                        "success": True,
                        "matches_found": len(matches),
                        "mappings_created": len(mapping_result.get("mapping_ids", [])),
                        "message": f"Successfully matched and stored {len(matches)} connections",
                    }
                else:
                    return {
                        "success": False,
                        "error": mapping_result.get("error"),
                        "message": "Connection matching completed but failed to store mappings",
                    }
            else:
                print(
                    "🔍 No connection matches found between incoming and outgoing connections"
                )
                return {
                    "success": True,
                    "matches_found": 0,
                    "mappings_created": 0,
                    "message": "Connection matching completed - no matches found",
                }

        except Exception as e:
            logger.error(f"Error during connection matching: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection matching failed due to unexpected error",
            }

    def _get_connections_by_ids(
        self, connection_ids: List[int], connection_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get connection details by IDs from database.

        Args:
            connection_ids: List of connection IDs
            connection_type: "incoming" or "outgoing"

        Returns:
            List of connection dictionaries with details
        """
        try:
            if not connection_ids:
                return []

            table_name = f"{connection_type}_connections"
            placeholders = ",".join(["?" for _ in connection_ids])

            query = f"""
                SELECT c.id, c.description, c.technology_name, c.code_snippet,
                       fh.file_path, fh.language, p.name as project_name
                FROM {table_name} c
                JOIN projects p ON c.project_id = p.id
                LEFT JOIN file_hashes fh ON c.file_hash_id = fh.id
                WHERE c.id IN ({placeholders})
            """

            results = self.db_connection.execute_query(query, connection_ids)

            # Format results for matching prompt
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": str(result["id"]),
                        "type": connection_type,
                        "file_path": result["file_path"],
                        "line_number": "N/A",
                        "technology": result["technology_name"],
                        "description": result["description"],
                        "code_snippet": result["code_snippet"],
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error getting connections by IDs: {e}")
            return []

    def _convert_confidence_to_float(self, confidence: str) -> float:
        """Convert confidence level string to float."""
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        return confidence_map.get(confidence.lower(), 0.5)
