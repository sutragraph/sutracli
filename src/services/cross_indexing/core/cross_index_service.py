"""
Cross-Index Service for analyzing and managing inter-service connections
"""

import json
from typing import Dict, List, Any, Optional, Iterator
from loguru import logger
from services.agent.session_management import SessionManager
from services.project_manager import ProjectManager
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from services.agent.memory_management.code_fetcher import CodeFetcher
from services.agent.memory_management.models import TaskStatus
from .cross_indexing_task_manager import CrossIndexingTaskManager
from tools import ActionExecutor
from src.utils import infer_technology_type
from src.utils.debug_utils import get_user_confirmation_for_llm_call
from graph.graph_operations import GraphOperations
from .technology_validator import TechnologyValidator
from .cross_index_phase import CrossIndexing


class CrossIndexService:
    """
    Enhanced service for managing cross-project connection analysis and storage.

    Key improvements:
    - Uses file_id as foreign key instead of file paths
    - Stores only technology field, not library field
    - Returns only IDs in match responses
    - Integrates with Sutra memory for context
    - Uses BAML-based JSON prompts instead of XML parsing
    """

    def __init__(
        self,
        project_manager: ProjectManager,
        memory_manager: SutraMemoryManager,
        session_manager: SessionManager,
    ):
        self.project_manager = project_manager
        self.memory_manager = memory_manager
        self.session_manager = session_manager
        self.task_manager = CrossIndexingTaskManager()
        self.cross_indexing = CrossIndexing()
        self.code_fetcher = CodeFetcher()
        self.action_executor = ActionExecutor(
            self.task_manager,  # Use task manager directly
            context="cross_index",
        )
        self.graph_ops = GraphOperations()
        self._memory_needs_update = False
        # Technology validation and correction services
        self.technology_validator = TechnologyValidator()
        # BAML-based cross-indexing
        self.cross_indexing = CrossIndexing()

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

            # Clear memory at the start of new cross-indexing analysis
            logger.debug("Clearing memory for new cross-indexing analysis")
            # Reset to Phase 1 and clear memory
            self.cross_indexing.reset_to_phase(1)
            self.task_manager.set_current_phase(1)
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
                    # Get BAML response with proper context
                    baml_response = self._get_cross_index_baml_response(
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
                        if self.cross_indexing.current_phase == 3:
                            logger.debug(
                                f"Processing previous tool result ({last_tool_result.get('tool_name')}) with code manager after BAML response but before processing (Phase 3)"
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
                                f"Skipping code manager processing for tool {last_tool_result.get('tool_name')} - only runs in Phase 3 (current phase: {self.cross_indexing.current_phase})"
                            )

                    # Check if user cancelled the operation
                    if isinstance(baml_response, dict) and baml_response.get(
                        "user_cancelled"
                    ):
                        yield {
                            "type": "user_cancelled",
                            "iteration": current_iteration,
                            "message": baml_response.get(
                                "message", "User cancelled the operation"
                            ),
                        }
                        return

                    # Process BAML response using action executor
                    task_complete = False
                    analysis_result = None

                    for event in self.action_executor.process_json_response(
                        baml_response, analysis_query
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
                                task_complete = True
                                break

                            # For Phase 3 completion, we'll handle Phase 4 transition later
                            # after all response processing is complete

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

                    # Handle phase advancement after all response processing is complete
                    if task_complete:
                        current_phase = self.cross_indexing.current_phase

                        if current_phase < 3:
                            # Check if there are pending tasks for the next phase before advancing
                            next_phase = current_phase + 1
                            next_phase_tasks = self.task_manager.get_tasks_for_phase(
                                next_phase
                            )
                            pending_tasks = next_phase_tasks.get("pending", [])

                            # Debug logging
                            all_tasks = self.task_manager.get_tasks_by_status(
                                TaskStatus.PENDING
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
                                self.cross_indexing.advance_phase()
                                self.task_manager.set_current_phase(
                                    self.cross_indexing.current_phase
                                )
                                next_phase = self.cross_indexing.current_phase

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
                                while self.cross_indexing.current_phase < 3:
                                    self.cross_indexing.current_phase += 1
                                    # Set phase without adding history entry for skipped phases
                                    self.task_manager.set_current_phase(
                                        self.cross_indexing.current_phase,
                                        add_history_entry=False,
                                    )

                                final_phase = self.cross_indexing.current_phase
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
                        elif current_phase == 3:
                            # Phase 3 complete → run Phase 4 data splitting using collected code snippets
                            try:
                                # Advance internal phase state to 4. Do not call task_manager.set_current_phase(4)
                                # here because that would clear the code snippets we need for Phase 4.
                                self.cross_indexing.current_phase = 4

                                # Clear last_tool_result when starting new phase
                                last_tool_result = None

                                print(
                                    f"🎯 Phase {current_phase} complete - advancing to Phase 4"
                                )
                                yield {
                                    "type": "phase_complete",
                                    "iteration": current_iteration,
                                    "current_phase": current_phase,
                                    "next_phase": 4,
                                    "message": f"Phase {current_phase} completed, advancing to Phase 4",
                                }

                                # Execute Phase 4 using centralized method
                                phase4_result = self._execute_phase_baml(4)

                                # Handle user cancellation in debug mode
                                if phase4_result.get("user_cancelled"):
                                    yield {
                                        "type": "user_cancelled",
                                        "iteration": current_iteration,
                                        "message": "User cancelled Phase 4 data splitting",
                                    }
                                    return

                                # If successful, capture analysis_result so storage/matching path below can run
                                if phase4_result.get("success"):
                                    analysis_result = phase4_result.get(
                                        "analysis_result", {}
                                    )

                                    # Mark cross-indexing as done after completion
                                    self.graph_ops.mark_cross_indexing_done_by_id(
                                        project_id
                                    )
                                    logger.info(
                                        f"✅ Cross-indexing completed for project ID {project_id}"
                                    )
                                else:
                                    # Phase 4 failed; surface warning and end
                                    yield {
                                        "type": "analysis_warning",
                                        "iteration": current_iteration,
                                        "warning": phase4_result.get(
                                            "error", "Phase 4 failed"
                                        ),
                                        "message": "Phase 4 data splitting failed",
                                    }
                                    return
                            except Exception as phase4_error:
                                logger.error(
                                    f"Error during Phase 4 data splitting: {phase4_error}"
                                )
                                yield {
                                    "type": "analysis_error",
                                    "iteration": current_iteration,
                                    "error": str(phase4_error),
                                    "message": "Error while running Phase 4 data splitting",
                                }
                                return

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
                                    self.graph_ops.store_connections_with_commit(
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

                                    logger.info(
                                        f"Connection counts for Phase 5 check: {len(all_incoming_ids)} incoming, {len(all_outgoing_ids)} outgoing"
                                    )

                                    # Run connection matching if we have both types
                                    if (
                                        len(all_incoming_ids) > 0
                                        and len(all_outgoing_ids) > 0
                                    ):
                                        # Advance to Phase 5 - Connection Matching
                                        self.cross_indexing.current_phase = 5
                                        print(
                                            f"🎯 Phase 4 complete - advancing to Phase 5"
                                        )
                                        yield {
                                            "type": "phase_complete",
                                            "iteration": current_iteration,
                                            "current_phase": 4,
                                            "next_phase": 5,
                                            "message": f"Phase 4 completed, advancing to Phase 5",
                                        }

                                        logger.info(
                                            "Starting Phase 5 - Connection Matching"
                                        )
                                        yield {
                                            "type": "connection_matching_start",
                                            "iteration": current_iteration,
                                            "message": f"🔗 Starting Phase 5 connection matching analysis...",
                                        }

                                        try:
                                            # Execute Phase 5 using centralized method
                                            matching_exec = self._execute_phase_baml(5)

                                            # Check if user cancelled connection matching
                                            if matching_exec.get("user_cancelled"):
                                                yield {
                                                    "type": "user_cancelled",
                                                    "iteration": current_iteration,
                                                    "message": "User cancelled connection matching",
                                                }
                                                return

                                            if matching_exec.get("success"):
                                                results = matching_exec.get(
                                                    "results", {}
                                                )
                                                matches = results.get("matches", [])

                                                # Store mappings in database
                                                if matches:
                                                    db_matches = []
                                                    for match in matches:
                                                        db_matches.append(
                                                            {
                                                                "sender_id": match.get(
                                                                    "outgoing_id"
                                                                ),
                                                                "receiver_id": match.get(
                                                                    "incoming_id"
                                                                ),
                                                                "description": match.get(
                                                                    "match_reason",
                                                                    "Auto-detected connection",
                                                                ),
                                                                "match_confidence": self._convert_confidence_to_float(
                                                                    match.get(
                                                                        "match_confidence",
                                                                        "medium",
                                                                    )
                                                                ),
                                                            }
                                                        )

                                                    mapping_result = self.graph_ops.create_connection_mappings(
                                                        db_matches
                                                    )
                                                else:
                                                    mapping_result = {
                                                        "success": True,
                                                        "mapping_ids": [],
                                                    }

                                                yield {
                                                    "type": "cross_index_success",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_result": storage_result,
                                                    "matching_result": results,
                                                    "mappings_result": mapping_result,
                                                    "message": f"🎉 Cross-indexing analysis completed successfully in {current_iteration} iterations",
                                                }

                                                # Mark cross-indexing as completely done
                                                self.graph_ops.mark_cross_indexing_done_by_id(
                                                    project_id
                                                )
                                                logger.info(
                                                    f"✅ Cross-indexing fully completed for project ID {project_id}"
                                                )
                                            else:
                                                yield {
                                                    "type": "cross_index_partial_success",
                                                    "iteration": current_iteration,
                                                    "analysis_result": analysis_result,
                                                    "storage_result": storage_result,
                                                    "matching_error": matching_exec.get(
                                                        "error"
                                                    ),
                                                    "message": f"Analysis and storage completed successfully, but connection matching failed: {matching_exec.get('error')}",
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
                                        logger.info(
                                            f"Skipping Phase 5 - only {len(all_incoming_ids)} incoming and {len(all_outgoing_ids)} outgoing connections available"
                                        )
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
                            # No analysis_result - this shouldn't happen if phases completed properly
                            yield {
                                "type": "cross_index_incomplete",
                                "iteration": current_iteration,
                                "message": "Task completed but no analysis result available",
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

    def _get_cross_index_baml_response(
        self,
        analysis_query: str,
        current_iteration: int,
        last_tool_result: Optional[Dict[str, Any]],
        project_path: str,
    ) -> Dict[str, Any]:
        """
        Get BAML response with proper Sutra memory and tool status context.

        Args:
            analysis_query: The analysis query
            current_iteration: Current iteration number
            last_tool_result: Last tool execution result
            project_path: Path to the project being analyzed

        Returns:
            BAML response
        """
        try:
            if not get_user_confirmation_for_llm_call():
                logger.info("User cancelled Cross-indexing BAML call in debug mode")
                # Return a special marker to indicate user cancellation
                return {
                    "user_cancelled": True,
                    "message": "User cancelled the operation in debug mode",
                }

            # Get current phase
            current_phase = self.cross_indexing.current_phase

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
                sutra_memory_rich = self.task_manager.get_memory_for_llm()
                logger.debug("Using task manager memory for cross-indexing")

            # Add sutra memory - check for meaningful content
            logger.debug(
                f"Cross-Index Sutra memory length: {len(sutra_memory_rich) if sutra_memory_rich else 0}"
            )

            # Use task manager's memory context directly (includes base memory + tasks)
            old_phase = self.task_manager.current_phase
            self.task_manager.set_current_phase(self.cross_indexing.current_phase)
            try:
                memory_context = self.task_manager.get_memory_for_llm()

                logger.debug(
                    f"Using task manager memory context: {len(memory_context)} characters"
                )
            finally:
                self.task_manager.set_current_phase(old_phase)

            if (
                tool_status
                and tool_status.strip()
                != "No previous tool execution in cross-indexing analysis"
            ):
                memory_context_with_tool_status = (
                    f"{memory_context}\n\nTOOL STATUS\n\n{tool_status}\n===="
                )
            else:
                memory_context_with_tool_status = memory_context

            logger.debug(
                f"Cross-index iteration {current_iteration}: Sending request to BAML for Phase {current_phase}"
            )
            logger.debug(
                f"Memory context length: {len(memory_context_with_tool_status)}"
            )

            # Call appropriate BAML function based on current phase using centralized method
            response = self._execute_phase_baml(
                current_phase, analysis_query, memory_context_with_tool_status
            )

            if isinstance(response, dict) and response.get("error"):
                logger.warning(
                    f"Phase {current_phase} execution error: {response.get('error')}"
                )
                return response

            logger.debug(
                f"Cross-index iteration {current_iteration}: Got BAML response for Phase {current_phase}"
            )

            # Convert BAML response to JSON format
            # This uses modern JSON structure instead of legacy XML
            if response.get("success"):
                baml_results = response.get("results")

                # Extract meaningful information from BAML results for JSON response
                if baml_results and hasattr(baml_results, "reasoning"):
                    reasoning = baml_results.reasoning
                else:
                    reasoning = f"Phase {current_phase} analysis completed using BAML. {response.get('message', 'Analysis completed successfully.')}"

                if baml_results and hasattr(baml_results, "next_steps"):
                    next_steps = baml_results.next_steps
                else:
                    next_steps = response.get(
                        "message", f"Phase {current_phase} completed successfully"
                    )

                # Create proper JSON structure
                json_response = {
                    "type": "baml_response",
                    "phase": current_phase,
                    "status": "success",
                    "thinking": {
                        "content": f"{reasoning}\n\nBAML Analysis Results:\n- Phase: {current_phase}\n- Status: Success\n- Message: {response.get('message', 'Analysis completed')}"
                    },
                    "attempt_completion": {"result": next_steps},
                }
                return json_response
            else:
                # Handle BAML errors with proper JSON structure
                error_msg = response.get("error", "BAML analysis failed")
                logger.error(f"BAML Phase {current_phase} error: {error_msg}")
                json_response = {
                    "type": "baml_response",
                    "phase": current_phase,
                    "status": "error",
                    "thinking": {
                        "content": f"Phase {current_phase} analysis failed using BAML.\n\nError Details:\n- Phase: {current_phase}\n- Error: {error_msg}\n- Status: Failed\n\nNeed to retry or investigate the issue."
                    },
                    "attempt_completion": {
                        "result": f"Phase {current_phase} failed: {error_msg}. Please check the logs for more details."
                    },
                }
                return json_response

        except Exception as e:
            logger.error(f"Failed to get cross-index BAML response: {e}")
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

            # Add searched paths information
            file_paths = result.get("file_paths")
            if file_paths:
                if isinstance(file_paths, list) and file_paths:
                    paths_str = ", ".join(file_paths)
                    status += f"Searched in: {paths_str}\n"
                elif isinstance(file_paths, str):
                    status += f"Searched in: {file_paths}\n"

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

            # Use BAML code manager instead of old LLM call
            baml_result = self.cross_indexing.run_code_manager(formatted_tool_results)

            if baml_result.get("success"):
                # Process code manager response to extract connection code
                baml_response = baml_result.get("results")
                self._process_baml_code_manager_response(baml_response)
                logger.info("BAML code manager processing completed")
            else:
                error_msg = baml_result.get("error", "BAML code manager failed")
                logger.warning(f"BAML code manager error: {error_msg}")

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

    def _process_baml_code_manager_response(self, baml_response) -> None:
        """
        Process BAML code manager response and extract connection code.

        Args:
            baml_response: BAML CodeManagerResponse object
        """
        try:
            logger.debug("Processing BAML code manager response for connection code")

            if not baml_response:
                logger.debug("No BAML code manager response to process")
                return

            # Process code snippets from BAML response
            if hasattr(baml_response, "code_snippets"):
                code_snippets_added = 0
                for code_snippet in baml_response.code_snippets:
                    # Add code snippet to task manager
                    try:
                        snippet_id = self.task_manager.add_code_snippet(
                            file_path=code_snippet.file_path,
                            start_line=code_snippet.start_line,
                            end_line=code_snippet.end_line,
                            content=code_snippet.content,
                            description=code_snippet.description,
                        )
                        if snippet_id:
                            code_snippets_added += 1
                            logger.debug(
                                f"Added code snippet {snippet_id}: {code_snippet.description}"
                            )
                    except Exception as snippet_error:
                        logger.warning(f"Failed to add code snippet: {snippet_error}")

                if code_snippets_added > 0:
                    logger.info(
                        f"Successfully processed BAML code manager: {code_snippets_added} code snippets added"
                    )
                else:
                    logger.warning(
                        "No code snippets were added from BAML code manager response"
                    )
            else:
                logger.debug("No code snippets found in BAML code manager response")

        except Exception as e:
            logger.error(f"Error processing BAML code manager response: {e}")

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
            memory_summary = self.task_manager.get_memory_for_llm()
            # Update session manager with the rich memory content
            self.session_manager.update_sutra_memory(memory_summary)
            logger.debug(
                f"Updated Cross-Index Sutra Memory in session: {len(memory_summary)} characters"
            )
            logger.debug(
                f"Memory includes {len(self.task_manager.get_all_code_snippets())} code snippets"
            )
        except Exception as e:
            logger.error(f"Error updating cross-index session memory: {e}")

    def _parse_connection_splitting_json(self, response_content: str) -> Dict[str, Any]:
        """
        Parse connection splitting JSON response format with technology name validation and correction.

        Args:
            response_content: Raw JSON response from connection splitting prompt

        Returns:
            Parsed analysis data in the expected format with validated technology names
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

            # TECHNOLOGY NAME VALIDATION AND CORRECTION
            logger.info("Validating technology names against predefined enums")
            all_valid, unmatched_names = (
                self.technology_validator.validate_json_technology_names(json_data)
            )

            if not all_valid:
                logger.warning(
                    f"Found {len(unmatched_names)} unmatched technology names: {unmatched_names}"
                )

                # Get corrections for unmatched names
                corrections = self.cross_indexing.correct_technology_names(
                    unmatched_names
                )

                if corrections:
                    logger.info(
                        f"Applying {len(corrections)} technology name corrections"
                    )
                    # Apply corrections to the JSON data
                    json_data = self.technology_validator.apply_corrected_names(
                        json_data, corrections
                    )

                    # Log the corrections applied
                    for original, corrected in corrections.items():
                        logger.info(
                            f"Technology name corrected: '{original}' -> '{corrected}'"
                        )
                else:
                    logger.warning(
                        "No corrections could be generated for unmatched technology names"
                    )
            else:
                logger.info("All technology names are valid, no corrections needed")

            # Convert the JSON format to our expected format
            result = {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
            }

            # Extract project summary if present
            project_summary = json_data.get("summary", "").strip()
            if project_summary:
                result["summary"] = project_summary
                logger.info(
                    f"Extracted project summary from Phase 4: {len(project_summary)} characters"
                )

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
        Run Phase 4 - Data Splitting using BAML.

        Returns:
            Result dictionary with splitting status and analysis data
        """
        try:
            logger.info("Starting Phase 4 - Data Splitting using BAML")

            # Get ONLY the code snippets stored by code manager (no tasks, no history)
            # Code snippets are stored in the task_manager, not memory_manager
            code_snippets = self.task_manager.get_all_code_snippets()

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
                    "User cancelled Phase 4 data splitting BAML call in debug mode"
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

            # Call BAML for Phase 4 data splitting
            logger.debug("Calling BAML for Phase 4 data splitting")
            baml_result = self.cross_indexing.run_connection_splitting(memory_context)

            if not baml_result.get("success"):
                error_msg = baml_result.get("error", "BAML Phase 4 failed")
                logger.error(f"Phase 4 data splitting failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "analysis_result": {
                        "incoming_connections": [],
                        "outgoing_connections": [],
                        "potential_matches": [],
                    },
                }

            # Process BAML response
            baml_response = baml_result.get("results")
            if not baml_response:
                logger.error("Empty BAML response for Phase 4")
                return {
                    "success": False,
                    "error": "Empty BAML response for Phase 4",
                    "analysis_result": {
                        "incoming_connections": [],
                        "outgoing_connections": [],
                        "potential_matches": [],
                    },
                }

            # Convert BAML response to expected format
            analysis_result = self._convert_baml_splitting_response(baml_response)

            logger.info(
                f"Phase 4 data splitting completed successfully using BAML: "
                f"{len(analysis_result['incoming_connections'])} incoming, "
                f"{len(analysis_result['outgoing_connections'])} outgoing"
            )

            return {
                "success": True,
                "analysis_result": analysis_result,
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

    def _convert_baml_splitting_response(self, baml_response) -> Dict[str, Any]:
        """
        Convert BAML connection splitting response to expected format.

        Args:
            baml_response: BAML ConnectionSplittingResponse object

        Returns:
            Dictionary in expected format for analysis_result
        """
        try:
            result = {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
            }

            # Process incoming connections
            if hasattr(baml_response, "incoming_connections"):
                for conn in baml_response.incoming_connections:
                    result["incoming_connections"].append(
                        {
                            "description": conn.description,
                            "file_path": conn.file_path,
                            "snippet_lines": list(
                                range(conn.start_line, conn.end_line + 1)
                            ),
                            "technology": {
                                "name": conn.technology,
                                "type": infer_technology_type(conn.technology),
                            },
                        }
                    )

            # Process outgoing connections
            if hasattr(baml_response, "outgoing_connections"):
                for conn in baml_response.outgoing_connections:
                    result["outgoing_connections"].append(
                        {
                            "description": conn.description,
                            "file_path": conn.file_path,
                            "snippet_lines": list(
                                range(conn.start_line, conn.end_line + 1)
                            ),
                            "technology": {
                                "name": conn.technology,
                                "type": infer_technology_type(conn.technology),
                            },
                        }
                    )

            # Add summary if available
            if hasattr(baml_response, "summary"):
                result["summary"] = baml_response.summary

            logger.debug(
                f"Converted BAML response: {len(result['incoming_connections'])} incoming, {len(result['outgoing_connections'])} outgoing connections"
            )
            return result

        except Exception as e:
            logger.error(f"Error converting BAML splitting response: {e}")
            return {
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
                "error": f"Conversion error: {str(e)}",
            }

    def get_existing_connections_with_ids(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve existing connections with IDs and file references.

        Returns:
            Dictionary with 'incoming' and 'outgoing' connection lists including IDs
        """
        try:
            # Get incoming and outgoing connections using wrapper function
            connections = self.graph_ops.get_existing_connections()
            return connections

        except Exception as e:
            logger.error(f"Error retrieving existing connections: {e}")
            return {"incoming": [], "outgoing": []}

    def _execute_phase_baml(
        self, phase: int, analysis_query: str = "", memory_context: str = ""
    ) -> Dict[str, Any]:
        """
        Centralized method to execute any phase using BAML.

        Args:
            phase: Phase number (1-5)
            analysis_query: The analysis query (for phases 1-3)
            memory_context: Memory context with tool status

        Returns:
            BAML response dictionary
        """
        try:
            logger.debug(f"Executing Phase {phase} using centralized BAML method")

            if phase == 1:
                return self.cross_indexing.run_package_discovery(
                    analysis_query, memory_context
                )
            elif phase == 2:
                return self.cross_indexing.run_import_discovery(
                    analysis_query, memory_context
                )
            elif phase == 3:
                return self.cross_indexing.run_implementation_discovery(
                    analysis_query, memory_context
                )
            elif phase == 4:
                return self._run_phase4_data_splitting()
            elif phase == 5:
                return self.cross_indexing.run_connection_matching()
            else:
                return {"error": f"Invalid phase number: {phase}. Must be 1-5."}

        except Exception as e:
            logger.error(f"Error executing Phase {phase}: {e}")
            return {"error": f"Phase {phase} execution failed: {str(e)}"}

    def _convert_confidence_to_float(self, confidence: str) -> float:
        """Convert confidence level string to float."""
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        return confidence_map.get(confidence.lower(), 0.5)
