import json
from typing import Any, Dict, Iterator, Optional

from loguru import logger

from baml_client.types import Agent
from services.agent.memory_management.models import TaskStatus
from services.agent.session_management import SessionManager
from src.graph.graph_operations import GraphOperations
from src.tools.tool_executor import execute_tool
from src.utils.debug_utils import get_user_confirmation_for_llm_call

from .cross_index_phase import CrossIndexing
from .cross_indexing_task_manager import CrossIndexingTaskManager


class CrossIndexService:
    """
    Cross-indexing service with proper phase management.

    Phase Flow:
    1. Phase 1: Loop until attempt_completion → task filtering → memory clear → Phase 2
    2. Phase 2: Loop until attempt_completion → task filtering → memory clear → Phase 3
    3. Phase 3: Loop with code manager until attempt_completion → Phase 4 (memory preserved)
    4. Phase 4: Technology correction → Phase 5 (memory preserved)
    5. Phase 5: Connection matching → complete
    """

    def __init__(
        self,
        cross_indexing: CrossIndexing,
        task_manager: CrossIndexingTaskManager,
        session_manager: SessionManager,
        graph_ops: GraphOperations,
    ):
        self.cross_indexing = cross_indexing
        self.task_manager = task_manager
        self.session_manager = session_manager
        self.graph_ops = graph_ops
        self._memory_needs_update = False

    def analyze_project_connections(
        self, project_path: str, project_id: int
    ) -> Iterator[Dict[str, Any]]:
        """
        Perform cross-indexing analysis with proper phase management.
        """
        try:
            logger.debug(
                f"Starting cross-indexing analysis for project {project_id} at {project_path}"
            )
            # Initialize and reset to Phase 1
            self.cross_indexing.reset_to_phase(1)
            self.task_manager.set_current_phase(1)
            logger.debug("Reset to Phase 1 and cleared memory for new analysis")

            analysis_query = f"Analyze project connections for: {project_path}"
            current_iteration = 0
            max_iterations = 100
            last_tool_result = None
            pending_code_manager_result = None

            while current_iteration < max_iterations:
                current_iteration += 1
                current_phase = self.cross_indexing.current_phase

                logger.debug(
                    f"Cross-indexing iteration {current_iteration} - Phase {current_phase}"
                )

                # Iteration start - no yield needed
                logger.debug(f"Phase {current_phase} - Iteration {current_iteration}")

                # Get BAML response for current phase
                baml_response = self._get_baml_response(
                    analysis_query, current_iteration, last_tool_result, project_path
                )

                # Handle user cancellation
                if isinstance(baml_response, dict) and baml_response.get(
                    "user_cancelled"
                ):
                    logger.debug("User cancelled the operation")
                    return

                # Process BAML response using model_dump() directly
                task_complete = False

                # Convert BAML response to dictionary using model_dump()
                response_dict = (
                    baml_response.model_dump()
                    if hasattr(baml_response, "model_dump")
                    else baml_response
                )

                # Process tool_call if present
                if response_dict.get("tool_call"):
                    tool_call = response_dict["tool_call"]
                    tool_name = tool_call.get("tool_name")
                    tool_params = tool_call.get("parameters", {})

                    if tool_name and tool_name != "attempt_completion":
                        # Run code manager with previous tool result before executing new tool
                        if (
                            current_phase == 3
                            and pending_code_manager_result is not None
                            and pending_code_manager_result["tool_name"]
                            in ["database", "search_keyword"]
                        ):
                            logger.debug(
                                f"Running code manager with previous tool result: {pending_code_manager_result['tool_name']}"
                            )
                            self._process_tool_with_code_manager_from_status(
                                pending_code_manager_result["tool_status"],
                                pending_code_manager_result["tool_name"],
                            )
                            pending_code_manager_result = None

                        # Execute tool using execute_tool function (handles tool execution and status building)
                        tool_status = execute_tool(
                            Agent.CrossIndexing, tool_name, tool_params
                        )

                        # Store tool status for memory context (no yielding needed)
                        last_tool_result = {
                            "tool_name": tool_name,
                            "tool_status": tool_status,
                        }
                        self._memory_needs_update = True

                        # Store result for code manager processing before next tool (in Phase 3)
                        if current_phase == 3 and tool_name in [
                            "database",
                            "search_keyword",
                        ]:
                            logger.debug(
                                f"Storing tool result for code manager processing: {tool_name}"
                            )
                            pending_code_manager_result = {
                                "tool_name": tool_name,
                                "tool_status": tool_status,
                            }

                    elif tool_name == "attempt_completion":
                        task_complete = True
                        logger.debug(
                            f"Phase {current_phase} marked complete due to attempt_completion"
                        )

                        # Extract and store project info from Phase 1 completion
                        if current_phase == 1:
                            completion_result = tool_params.get("result", "")
                            if completion_result:
                                self.task_manager.set_project_info(completion_result)
                                logger.debug(
                                    "Project info extracted and stored from Phase 1 completion"
                                )

                # Process sutra_memory updates using original BAML object
                if (
                    hasattr(baml_response, "sutra_memory")
                    and baml_response.sutra_memory
                ):
                    try:
                        # Use the original BAML sutra_memory object directly
                        # No need to convert to dict and back to object
                        memory_result = self.task_manager.process_sutra_memory_params(
                            baml_response.sutra_memory
                        )

                        if memory_result.get("success"):
                            logger.debug(
                                f"Sutra memory processed successfully: {memory_result.get('changes_applied', {})}"
                            )
                        else:
                            logger.warning(
                                f"Sutra memory processing had errors: {memory_result.get('errors', [])}"
                            )

                        self._memory_needs_update = True

                    except Exception as e:
                        logger.error(f"Error processing sutra memory: {e}")
                        self._memory_needs_update = True

                # Handle phase completion and advancement
                if task_complete:
                    if current_phase in [1, 2]:
                        # Phase 1 or 2 complete - run task filtering and advance
                        success = self._handle_phase_12_completion(current_phase)
                        if success:
                            self.cross_indexing.advance_phase()
                            self.task_manager.set_current_phase(
                                self.cross_indexing.current_phase
                            )

                            logger.debug(
                                f"Phase {current_phase} complete - advancing to Phase {self.cross_indexing.current_phase}"
                            )

                            last_tool_result = None
                            pending_code_manager_result = None
                            continue
                        else:
                            logger.error(f"Phase {current_phase} completion failed")
                            return

                    elif current_phase == 3:
                        # Process any remaining code manager result before Phase 3 completion
                        if (
                            pending_code_manager_result is not None
                            and pending_code_manager_result["tool_name"]
                            in ["database", "search_keyword"]
                        ):
                            logger.debug(
                                f"Processing final code manager result before Phase 3 completion: {pending_code_manager_result['tool_name']}"
                            )
                            self._process_tool_with_code_manager_from_status(
                                pending_code_manager_result["tool_status"],
                                pending_code_manager_result["tool_name"],
                            )
                            pending_code_manager_result = None

                        # Phase 3 complete - advance to Phase 4 (preserve memory)
                        self.cross_indexing.current_phase = 4
                        # Don't call task_manager.set_current_phase to preserve memory

                        logger.debug(
                            "Phase 3 complete - advancing to Phase 4 (memory preserved)"
                        )

                        # Execute Phase 4
                        phase4_result = self._execute_phase_4()
                        if phase4_result.get("success"):
                            analysis_result = phase4_result.get("analysis_result", {})

                            # Execute Phase 5
                            phase5_result = self._execute_phase_5(
                                analysis_result, project_id
                            )

                            yield {
                                "type": "cross_index_success",
                                "iteration": current_iteration,
                                "analysis_result": analysis_result,
                                "phase4_result": phase4_result,
                                "phase5_result": phase5_result,
                                "message": "Cross-indexing analysis completed successfully",
                            }
                        else:
                            yield {
                                "type": "cross_index_error",
                                "iteration": current_iteration,
                                "error": phase4_result.get("error", "Phase 4 failed"),
                                "message": "Phase 4 execution failed",
                            }
                        return

                # Update memory if needed
                if self._memory_needs_update:
                    self._update_session_memory()
                    self._memory_needs_update = False

            # Analysis didn't complete within iteration limit
            logger.error(f"Analysis did not complete after {max_iterations} iterations")
            yield {
                "type": "cross_index_failure",
                "iterations_completed": max_iterations,
                "message": f"Analysis did not complete after {max_iterations} iterations",
            }

        except Exception as e:
            logger.error(f"Error during cross-indexing analysis: {e}")
            yield {
                "type": "cross_index_error",
                "error": str(e),
                "message": "Critical error during cross-indexing analysis",
            }

    def _get_baml_response(
        self,
        analysis_query: str,
        current_iteration: int,
        last_tool_result: Optional[Dict[str, Any]],
        project_path: str,
    ) -> Dict[str, Any]:
        """Get BAML response for current phase."""
        try:
            if not get_user_confirmation_for_llm_call():
                return {
                    "user_cancelled": True,
                    "message": "User cancelled the operation in debug mode",
                }

            current_phase = self.cross_indexing.current_phase

            # Get memory context
            memory_context = self._get_memory_context()

            # Combine memory and tool status (tool status now handled by execute_tool)
            if last_tool_result and last_tool_result.get("tool_status"):
                tool_status = last_tool_result["tool_status"]
                full_context = f"{memory_context}\n\nTOOL STATUS\n\n{tool_status}\n===="
            else:
                full_context = memory_context

            logger.debug(
                f"Phase {current_phase} - Memory context length: {len(full_context)}"
            )

            # Execute phase using centralized method
            response = self._execute_phase_baml(
                current_phase, analysis_query, full_context
            )

            if response.get("success"):
                baml_results = response.get("results")
                return baml_results
            else:
                # Handle BAML error
                error_msg = response.get("error", "BAML execution failed")
                logger.error(f"Phase {current_phase} BAML error: {error_msg}")
                return {
                    "type": "error",
                    "thinking": f"Phase {current_phase} failed: {error_msg}",
                    "attempt_completion": {"result": f"Phase {current_phase} failed"},
                }

        except Exception as e:
            logger.error(f"Error getting BAML response: {e}")
            return {
                "type": "error",
                "thinking": f"Error: {str(e)}",
                "attempt_completion": {"result": "BAML request failed"},
            }

    def _get_memory_context(self) -> str:
        """Get memory context for current phase."""
        current_phase = self.cross_indexing.current_phase

        # Get tasks for current phase
        current_tasks = self.task_manager.get_tasks_by_status(TaskStatus.CURRENT)
        pending_tasks = self.task_manager.get_tasks_by_status(TaskStatus.PENDING)

        # Filter tasks for current phase
        phase_current = []
        phase_pending = []

        for task in current_tasks:
            if task:
                metadata = self.task_manager._task_phase_metadata.get(task.id, {})
                target_phase = metadata.get("target_phase", current_phase)
                if target_phase == current_phase:
                    phase_current.append(task)

        for task in pending_tasks:
            if task:
                metadata = self.task_manager._task_phase_metadata.get(task.id, {})
                target_phase = metadata.get("target_phase", current_phase)
                if target_phase == current_phase:
                    phase_pending.append(task)

        # Build memory context - let task manager handle all task display
        return self.task_manager.get_memory_for_llm()

    def _process_tool_with_code_manager_from_status(
        self, tool_status: str, tool_name: str
    ) -> None:
        """
        Process tool results with code manager using tool status string.
        Only processes database and search_keyword tools.

        Args:
            tool_status: Tool status string from execute_tool
            tool_name: Name of the tool that was executed
        """
        try:
            if tool_name not in ["database", "search_keyword"]:
                logger.debug(
                    f"Skipping code manager processing for tool: {tool_name} (not database or search_keyword)"
                )
                return

            if not tool_status or tool_status.strip() == "":
                logger.debug(
                    f"Skipping code manager processing for tool: {tool_name} (no status data)"
                )
                return

            logger.debug(
                f"Processing tool results with code manager for tool: {tool_name}"
            )

            # Format tool status for code manager
            formatted_tool_results = f"""
Tool Results:
{tool_status}
"""

            # Use BAML code manager
            baml_result = self.cross_indexing.run_code_manager(formatted_tool_results)
            logger.debug(
                f"BAML code manager result success = {baml_result.get('success') if isinstance(baml_result, dict) else 'N/A'}"
            )

            if baml_result.get("success"):
                logger.debug("Processing successful BAML code manager result")
                # Process code manager response to extract connection code using model_dump()
                baml_response = baml_result.get("results")
                response_data = (
                    baml_response.model_dump()
                    if hasattr(baml_response, "model_dump")
                    else baml_response
                )
                self._add_code_snippets_to_memory(response_data)
                logger.debug("BAML code manager processing completed")
            else:
                error_msg = baml_result.get("error", "BAML code manager failed")
                logger.warning(f"BAML code manager error: {error_msg}")

        except Exception as e:
            logger.error(f"Error processing tool results with code manager: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

    def _add_code_snippets_to_memory(self, response_data) -> None:
        """
        Process code manager response and extract connection code with deduplication.

        Args:
            response_data: Code manager response data (from model_dump())
        """
        try:
            logger.debug("Processing code manager response for connection code")
            logger.debug(f"Response data type: {type(response_data)}")

            if not response_data:
                logger.debug("No code manager response to process")
                return

            # Get connection code from response data
            connection_code_list = response_data.get("connection_code", None) or []
            logger.debug(f"Found {len(connection_code_list)} connection code items")

            if connection_code_list:
                code_snippets_added = 0
                code_snippets_skipped = 0

                for code_connection in connection_code_list:
                    logger.debug(f"Processing connection: {code_connection}")

                    # Extract fields from code connection dictionary
                    file_path = code_connection.get("file")
                    start_line = code_connection.get("start_line")
                    end_line = code_connection.get("end_line")
                    description = code_connection.get("description")

                    if not all([file_path, start_line, end_line, description]):
                        logger.warning(
                            f"Incomplete code connection data: file={file_path}, start={start_line}, end={end_line}, desc={description}"
                        )
                        continue

                    # Check for duplicates before adding
                    if self._is_duplicate_code_snippet(file_path, start_line, end_line):
                        code_snippets_skipped += 1
                        logger.debug(
                            f"Processed overlapping/duplicate code snippet: {file_path} lines {start_line}-{end_line}"
                        )
                        continue

                    # Add code snippet to task manager
                    try:
                        snippet_id = self.task_manager.add_code_snippet(
                            code_id="dummy_id",  # Will be replaced with counter+1
                            file_path=file_path,
                            start_line=start_line,
                            end_line=end_line,
                            description=description,
                        )
                        if snippet_id:
                            code_snippets_added += 1
                            logger.debug(
                                f"Added code snippet {snippet_id}: {description}"
                            )
                    except Exception as snippet_error:
                        logger.warning(f"Failed to add code snippet: {snippet_error}")

                if code_snippets_added > 0:
                    logger.debug(
                        f"Successfully processed BAML code manager: {code_snippets_added} code snippets added, {code_snippets_skipped} overlapping/duplicates processed"
                    )
                elif code_snippets_skipped > 0:
                    logger.debug(
                        f"BAML code manager processing: {code_snippets_skipped} overlapping/duplicate code snippets processed (merged or already in memory)"
                    )
                else:
                    logger.warning(
                        "No code snippets were added from BAML code manager response"
                    )
            else:
                logger.debug("No connection_code found in BAML code manager response")

        except Exception as e:
            logger.error(f"Error processing BAML code manager response: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

    def _is_duplicate_code_snippet(
        self, file_path: str, start_line: int, end_line: int
    ) -> bool:
        """
        Check if a code snippet already exists in memory and handle merging of overlapping ranges.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            True if duplicate exists (exact match), False otherwise
        """
        try:
            if (
                not hasattr(self.task_manager, "memory_ops")
                or not self.task_manager.memory_ops.code_snippets
            ):
                return False

            for existing_snippet in self.task_manager.memory_ops.code_snippets.values():
                # Check for exact match: same file and identical line ranges
                if (
                    existing_snippet.file_path == file_path
                    and existing_snippet.start_line == start_line
                    and existing_snippet.end_line == end_line
                ):
                    return True

                # Check for overlapping ranges in the same file
                if existing_snippet.file_path == file_path and not (
                    end_line < existing_snippet.start_line
                    or start_line > existing_snippet.end_line
                ):
                    logger.debug(
                        f"Found overlapping code snippet in {file_path}: existing {existing_snippet.start_line}-{existing_snippet.end_line}, new {start_line}-{end_line}"
                    )

                    # Merge the overlapping ranges by expanding the existing snippet
                    merged_start = min(existing_snippet.start_line, start_line)
                    merged_end = max(existing_snippet.end_line, end_line)

                    logger.debug(
                        f"Merging code snippets: removing existing {existing_snippet.start_line}-{existing_snippet.end_line} and new {start_line}-{end_line}, replacing with merged {merged_start}-{merged_end}"
                    )

                    # Update the existing snippet with merged range
                    self._update_code_snippet_range(
                        existing_snippet, merged_start, merged_end
                    )

                    return True  # Return True to skip adding the new snippet since we merged it

            return False

        except Exception as e:
            logger.warning(f"Error checking for duplicate code snippet: {e}")
            return False  # If we can't check, allow the addition

    def _update_code_snippet_range(
        self, existing_snippet, new_start_line: int, new_end_line: int
    ):
        """
        Update an existing code snippet with a new line range and fetch updated content.

        Args:
            existing_snippet: The existing CodeSnippet object
            new_start_line: New starting line number
            new_end_line: New ending line number
        """
        try:
            # Update the snippet's line range
            existing_snippet.start_line = new_start_line
            existing_snippet.end_line = new_end_line

            # Fetch the updated content for the expanded range
            if hasattr(self.task_manager.memory_ops, "code_fetcher"):
                updated_content = (
                    self.task_manager.memory_ops.code_fetcher.fetch_code_from_file(
                        existing_snippet.file_path, new_start_line, new_end_line
                    )
                )
                existing_snippet.content = updated_content

            logger.debug(
                f"Successfully updated code snippet {existing_snippet.id} to range {new_start_line}-{new_end_line}"
            )

        except Exception as e:
            logger.warning(f"Error updating code snippet range: {e}")

    def _update_session_memory(self):
        """Update session memory with current state."""
        try:
            if self.session_manager:
                memory_summary = self.task_manager.get_memory_for_llm()
                self.session_manager.update_sutra_memory(memory_summary)
                logger.debug(
                    f"Updated Cross-Index Sutra Memory in session: {len(memory_summary)} characters"
                )
                logger.debug(
                    f"Memory includes {len(self.task_manager.get_all_code_snippets())} code snippets"
                )
        except Exception as e:
            logger.error(f"Error updating cross-index session memory: {e}")

    def _handle_phase_12_completion(self, phase: int) -> bool:
        """Handle completion of Phase 1 or 2 with task filtering."""
        try:
            logger.debug(f"Phase {phase} completed - running task filtering")

            # Debug task state before filtering
            self.task_manager.debug_log_tasks()

            # Get tasks created for the next phase
            next_phase = phase + 1
            tasks_to_filter = []

            # Get all pending tasks that were created in this phase for next phase
            # ONLY include PENDING tasks - completed tasks should stay in their completion phase
            for task in self.task_manager.get_tasks_by_status(TaskStatus.PENDING):
                if task:
                    metadata = self.task_manager._task_phase_metadata.get(task.id, {})
                    created_in_phase = metadata.get("created_in_phase")
                    target_phase = metadata.get("target_phase")

                    # Double-check: only include tasks that are both pending AND targeting next phase
                    if created_in_phase == phase and target_phase == next_phase:
                        tasks_to_filter.append(task)
                        logger.debug(
                            f"Including task {task.id} for filtering: created_in_phase={created_in_phase}, target_phase={target_phase}, status={task.status}"
                        )
                    else:
                        logger.debug(
                            f"Excluding task {task.id} from filtering: created_in_phase={created_in_phase}, target_phase={target_phase}, status={task.status}"
                        )

            logger.debug(
                f"Found {len(tasks_to_filter)} tasks to filter from Phase {phase} to Phase {next_phase}"
            )

            # Debug the tasks that will be filtered
            if tasks_to_filter:
                logger.debug("Tasks selected for filtering:")
                for i, task in enumerate(tasks_to_filter):
                    metadata = self.task_manager._task_phase_metadata.get(task.id, {})
                    logger.debug(
                        f"  Task {i+1}: ID={task.id}, status={task.status}, created_in_phase={metadata.get('created_in_phase')}, target_phase={metadata.get('target_phase')}, description='{task.description[:60]}...'"
                    )
            else:
                logger.debug("No tasks selected for filtering")

            if tasks_to_filter:
                logger.debug(f"Running task filtering on {len(tasks_to_filter)} tasks")

                # Run task filtering
                filtering_result = self.cross_indexing.filter_tasks(tasks_to_filter)

                # Extract filtered tasks using model_dump() if it's a BAML response
                if hasattr(filtering_result, "model_dump"):
                    filter_data = filtering_result.model_dump()
                    filtered_tasks = filter_data.get("tasks", [])
                elif isinstance(filtering_result, dict):
                    filtered_tasks = filtering_result.get("tasks", [])
                else:
                    filtered_tasks = filtering_result

                if not filtered_tasks:
                    logger.warning(
                        "Task filtering returned no results, keeping original tasks"
                    )
                    filtered_tasks = tasks_to_filter  # Keep original if filtering fails

                logger.debug(
                    f"Task filtering result: {len(tasks_to_filter)} → {len(filtered_tasks)} tasks"
                )

                # Clear all tasks and reset counter
                self.task_manager.clear_all_tasks_for_filtering()

                # Add filtered tasks back with proper metadata
                for i, task in enumerate(filtered_tasks):
                    new_task_id = str(i + 1)  # Use sequential IDs starting from 1
                    success = self.task_manager.add_task(
                        new_task_id,
                        task.description,
                        TaskStatus.PENDING,
                        target_phase=next_phase,
                    )

                    if success:
                        logger.debug(
                            f"Added filtered task {new_task_id} for Phase {next_phase}: {task.description[:50]}..."
                        )
                    else:
                        logger.error(f"Failed to add filtered task {new_task_id}")

                logger.debug(
                    f"Task filtering completed: {len(filtered_tasks)} tasks ready for Phase {next_phase}"
                )
            else:
                logger.debug(f"No tasks to filter from Phase {phase}")
                # Still clear tasks and reset for clean transition
                self.task_manager.clear_all_tasks_for_filtering()

            # Clear memory for phase transition (history and code snippets)
            logger.debug(
                f"Clearing memory for phase transition: {phase} → {next_phase}"
            )
            self.task_manager.clear_phase_memory()

            return True

        except Exception as e:
            logger.error(f"Error handling Phase {phase} completion: {e}")
            return False

    def _execute_phase_baml(
        self, phase: int, analysis_query: str, memory_context: str
    ) -> Dict[str, Any]:
        """Execute BAML for specific phase."""
        try:
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
            else:
                return {
                    "success": False,
                    "error": f"Invalid phase for BAML execution: {phase}",
                }
        except Exception as e:
            return {"success": False, "error": f"BAML execution error: {str(e)}"}

    def _execute_phase_4(self) -> Dict[str, Any]:
        """Execute Phase 4 - Data Splitting."""
        try:
            logger.debug("Executing Phase 4 - Data Splitting")

            # Get only code snippets from task manager (not full memory context)
            code_snippets_context = self._get_code_snippets_only_context()

            # Run connection splitting first to generate connection data
            # Pass only code snippets, not tasks or tool results
            splitting_result = self.cross_indexing.run_connection_splitting(
                code_snippets_context
            )

            if not splitting_result.get("success"):
                return {
                    "success": False,
                    "error": f"Connection splitting failed: {splitting_result.get('error')}",
                }

            # Get the analysis result from connection splitting using model_dump()
            baml_analysis_result = splitting_result.get("results")

            # Add logging to diagnose the response format issue
            logger.debug(f"BAML analysis result type: {type(baml_analysis_result)}")
            logger.debug(f"BAML analysis result: {baml_analysis_result}")

            # Handle both object and string responses
            if hasattr(baml_analysis_result, "model_dump"):
                analysis_result = baml_analysis_result.model_dump()
                logger.debug("Used model_dump() to convert BAML response")
            elif isinstance(baml_analysis_result, str):
                # Parse JSON string if BAML returned a string
                try:
                    analysis_result = json.loads(baml_analysis_result)
                    logger.debug("Parsed JSON string from BAML response")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse BAML JSON response: {e}")
                    return {
                        "success": False,
                        "error": f"Invalid JSON response from connection splitting: {str(e)}",
                    }
            else:
                analysis_result = baml_analysis_result
                logger.debug("Used BAML response directly")

            logger.debug(f"Final analysis result type: {type(analysis_result)}")

            # Ensure analysis_result is a dictionary before proceeding
            if not isinstance(analysis_result, dict):
                logger.error(
                    f"Analysis result is not a dictionary: {type(analysis_result)}"
                )
                return {
                    "success": False,
                    "error": f"Connection splitting returned invalid format: {type(analysis_result)}",
                }

            # Check if technology correction is needed
            unmatched_technologies = self._get_unmatched_technologies(analysis_result)

            if unmatched_technologies:
                logger.debug(
                    f"🔧 Technology Correction: Processing {len(unmatched_technologies)} unmatched names: {unmatched_technologies}"
                )

                # Run technology correction with only technology names
                correction_result = self.cross_indexing.run_technology_correction(
                    json.dumps(unmatched_technologies),
                    json.dumps(
                        [
                            "GraphQL",
                            "HTTP/HTTPS",
                            "MessageQueue",
                            "Unknown",
                            "WebSockets",
                            "gRPC",
                        ]
                    ),
                )

                if correction_result.get("success"):
                    # Apply corrections to analysis result using model_dump()
                    correction_results = correction_result.get("results")
                    correction_data = (
                        correction_results.model_dump()
                        if hasattr(correction_results, "model_dump")
                        else correction_results
                    )
                    corrected_analysis = self._apply_technology_corrections(
                        analysis_result, correction_data
                    )
                    if corrected_analysis:
                        analysis_result = corrected_analysis
                        logger.debug("Technology correction completed successfully")
                else:
                    logger.warning(
                        f"Technology correction failed: {correction_result.get('error')}"
                    )
            else:
                logger.debug(
                    "✅ All technologies already match valid enums - skipping technology correction"
                )

            return {
                "success": True,
                "analysis_result": analysis_result,
                "message": "Phase 4 completed successfully",
            }

        except Exception as e:
            logger.error(f"Error in Phase 4 execution: {e}")
            return {"success": False, "error": f"Phase 4 execution error: {str(e)}"}

    def _get_code_snippets_only_context(self) -> str:
        """Get only code snippets for Phase 4 connection splitting."""
        try:
            content = []

            # Add only code snippets if any exist
            if (
                hasattr(self.task_manager, "memory_ops")
                and self.task_manager.memory_ops.code_snippets
            ):
                content.append("CODE SNIPPETS:")
                content.append("")
                for (
                    code_id,
                    snippet,
                ) in self.task_manager.memory_ops.code_snippets.items():
                    content.append(f"ID: {code_id}")
                    content.append(
                        f"File: {snippet.file_path} (lines {snippet.start_line}-{snippet.end_line})"
                    )
                    content.append(f"Description: {snippet.description}")
                    if snippet.content:
                        for line in snippet.content.split("\n"):
                            content.append(f"  {line}")
                    else:
                        content.append("")
            else:
                content.append("No code snippets available for connection splitting.")

            result = "\n".join(content)
            logger.debug(
                f"Phase 4 code snippets context length: {len(result)} characters"
            )
            return result

        except Exception as e:
            logger.error(f"Error building code snippets context: {e}")
            return "Error retrieving code snippets for connection splitting."

    def _execute_phase_5(
        self, analysis_result: Dict[str, Any], project_id: int
    ) -> Dict[str, Any]:
        """Execute Phase 5 - Connection Matching."""
        try:
            logger.debug("Executing Phase 5 - Connection Matching")

            # Store connections and summary in database first
            storage_result = self.graph_ops.store_connections_with_commit(
                project_id, analysis_result
            )

            if not storage_result.get("success"):
                return {
                    "success": False,
                    "error": f"Connection storage failed: {storage_result.get('error')}",
                }

            print("✅ Connections and summary stored in database successfully")

            # Run comprehensive connection matching for all technology types
            # The method handles fetching and processing all connections internally
            print(
                "🔍 Starting comprehensive connection matching for all technology types"
            )

            matching_result = self.cross_indexing.run_connection_matching()

            if matching_result.get("success"):
                matching_data = matching_result.get("results", {})
                if hasattr(matching_data, "model_dump"):
                    matching_data = matching_data.model_dump()
                matches = matching_data.get("matches", [])

                # Store mappings if matches found
                if matches:
                    db_matches = []
                    for match in matches:
                        db_matches.append(
                            {
                                "sender_id": match.get("outgoing_id"),
                                "receiver_id": match.get("incoming_id"),
                                "description": match.get(
                                    "match_reason", "Auto-detected connection"
                                ),
                                "match_confidence": self._convert_confidence_to_float(
                                    match.get("match_confidence", "medium")
                                ),
                            }
                        )

                    mapping_result = self.graph_ops.create_connection_mappings(
                        db_matches
                    )
                    print(f"✅ Stored {len(db_matches)} connection mappings in database")
                else:
                    mapping_result = {"success": True, "mapping_ids": []}
                    print("ℹ️  No connection matches found")

                # Mark cross-indexing as complete
                self.graph_ops.mark_cross_indexing_done_by_id(project_id)

                return {
                    "success": True,
                    "matching_result": matching_result.get("results", {}),
                    "storage_result": storage_result,
                    "mapping_result": mapping_result,
                    "message": "Phase 5 completed successfully with comprehensive connection matching",
                }
            else:
                logger.warning(
                    f"Connection matching failed: {matching_result.get('error')}"
                )
                # Mark as complete even if matching fails
                self.graph_ops.mark_cross_indexing_done_by_id(project_id)
                return {
                    "success": True,
                    "storage_result": storage_result,
                    "message": f"Phase 5 completed - connection matching failed but data stored",
                }

        except Exception as e:
            logger.error(f"Error in Phase 5 execution: {e}")
            return {"success": False, "error": f"Phase 5 execution error: {str(e)}"}

    def get_existing_connections_with_ids(self) -> Dict[str, Any]:
        """Get existing connections with IDs for matching."""
        try:
            return self.graph_ops.get_existing_connections()
        except Exception as e:
            logger.error(f"Error getting existing connections: {e}")
            return {"incoming": [], "outgoing": []}

    def _convert_confidence_to_float(self, confidence: str) -> float:
        """Convert confidence string to float."""
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        return confidence_map.get(confidence.lower(), 0.5)

    def _get_unmatched_technologies(self, analysis_result: Dict[str, Any]) -> list:
        """Get list of technology names that don't match valid enums from BAML format."""
        valid_enums = {
            "GraphQL",
            "HTTP/HTTPS",
            "MessageQueue",
            "Unknown",
            "WebSockets",
            "gRPC",
        }
        unmatched = set()

        # Check incoming connections - BAML format: {"tech_name": {"file": [details]}}
        incoming_connections = analysis_result.get("incoming_connections")
        if incoming_connections is not None:
            for tech_name in incoming_connections.keys():
                if tech_name and tech_name not in valid_enums:
                    unmatched.add(tech_name)

        # Check outgoing connections - BAML format: {"tech_name": {"file": [details]}}
        outgoing_connections = analysis_result.get("outgoing_connections")
        if outgoing_connections is not None:
            for tech_name in outgoing_connections.keys():
                if tech_name and tech_name not in valid_enums:
                    unmatched.add(tech_name)

        return list(unmatched)

    def _apply_technology_corrections(
        self, analysis_result: Dict[str, Any], baml_corrections
    ) -> Dict[str, Any]:
        """Apply technology corrections to analysis result in BAML format."""
        try:
            # Use model_dump() to get corrections data
            if hasattr(baml_corrections, "model_dump"):
                corrections_data = baml_corrections.model_dump()
            else:
                corrections_data = baml_corrections

            corrections_list = corrections_data.get("corrections", [])

            if not corrections_list:
                logger.debug("No corrections provided by technology correction")
                return analysis_result

            # Build correction mapping
            correction_map = {}
            for correction in corrections_list:
                original_name = correction.get("original_name")
                corrected_name = correction.get("corrected_name")
                if original_name and corrected_name:
                    correction_map[original_name] = corrected_name

            logger.debug(f"Applying technology corrections: {correction_map}")

            # Apply corrections to incoming connections - BAML format
            incoming_connections = analysis_result.get("incoming_connections")
            if incoming_connections is not None:
                corrected_incoming = {}
                for tech_name, files_dict in incoming_connections.items():
                    corrected_tech_name = correction_map.get(tech_name, tech_name)
                    corrected_incoming[corrected_tech_name] = files_dict
                analysis_result["incoming_connections"] = corrected_incoming

            # Apply corrections to outgoing connections - BAML format
            outgoing_connections = analysis_result.get("outgoing_connections")
            if outgoing_connections is not None:
                corrected_outgoing = {}
                for tech_name, files_dict in outgoing_connections.items():
                    corrected_tech_name = correction_map.get(tech_name, tech_name)
                    corrected_outgoing[corrected_tech_name] = files_dict
                analysis_result["outgoing_connections"] = corrected_outgoing

            return analysis_result

        except Exception as e:
            logger.error(f"Error applying technology corrections: {e}")
            return analysis_result

    def _get_connections_with_unknown_types(self) -> Dict[str, Any]:
        """Get existing connections that have unknown technology types for matching."""
        try:
            all_connections = self.get_existing_connections_with_ids()
            unknown_connections = {"incoming": [], "outgoing": []}

            # Filter incoming connections with unknown types
            for connection in all_connections.get("incoming", []):
                tech_type = connection.get("technology_type", "").lower()
                if tech_type in ["unknown", ""]:
                    unknown_connections["incoming"].append(connection)

            # Filter outgoing connections with unknown types
            for connection in all_connections.get("outgoing", []):
                tech_type = connection.get("technology_type", "").lower()
                if tech_type in ["unknown", ""]:
                    unknown_connections["outgoing"].append(connection)

            logger.debug(
                f"Found {len(unknown_connections['incoming'])} incoming and {len(unknown_connections['outgoing'])} outgoing connections with unknown types"
            )
            return unknown_connections

        except Exception as e:
            logger.error(f"Error getting connections with unknown types: {e}")
            return {"incoming": [], "outgoing": []}
