import json
from typing import Any, Dict, Iterator, Optional
from loguru import logger
from services.agent.memory_management.models import TaskStatus
from src.utils.debug_utils import get_user_confirmation_for_llm_call


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
        cross_indexing,
        task_manager,
        action_executor,
        session_manager,
        graph_ops,
    ):
        self.cross_indexing = cross_indexing
        self.task_manager = task_manager
        self.action_executor = action_executor
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

            yield {
                "type": "cross_index_start",
                "project_id": project_id,
                "project_path": project_path,
                "message": "Starting cross-indexing analysis",
            }

            # Initialize and reset to Phase 1
            self.cross_indexing.reset_to_phase(1)
            self.task_manager.set_current_phase(1)
            logger.debug("Reset to Phase 1 and cleared memory for new analysis")

            analysis_query = f"Analyze project connections for: {project_path}"
            current_iteration = 0
            max_iterations = 100
            last_tool_result = None

            while current_iteration < max_iterations:
                current_iteration += 1
                current_phase = self.cross_indexing.current_phase

                logger.debug(
                    f"Cross-indexing iteration {current_iteration} - Phase {current_phase}"
                )

                yield {
                    "type": "iteration_start",
                    "iteration": current_iteration,
                    "phase": current_phase,
                    "message": f"Phase {current_phase} - Iteration {current_iteration}",
                }

                # Get BAML response for current phase
                baml_response = self._get_baml_response(
                    analysis_query, current_iteration, last_tool_result, project_path
                )

                # Handle user cancellation
                if isinstance(baml_response, dict) and baml_response.get(
                    "user_cancelled"
                ):
                    yield {
                        "type": "user_cancelled",
                        "iteration": current_iteration,
                        "message": "User cancelled the operation",
                    }
                    return

                # Process BAML response - use it directly if it has the right structure
                task_complete = False

                # BAML responses come as raw JSON, use them directly
                for event in self.action_executor.process_json_response(
                    baml_response, analysis_query
                ):
                    event_type = event.get("type", "unknown")

                    if event_type == "thinking":
                        yield {
                            "type": "thinking",
                            "iteration": current_iteration,
                            "phase": current_phase,
                            "content": event.get("content", "analyzing..."),
                        }

                    elif event_type == "tool_use":
                        tool_name = event.get("tool_name", "unknown")

                        # Update last_tool_result first (this is the tool result that was just processed)
                        last_tool_result = event

                        self._memory_needs_update = True

                        yield event

                    elif event_type == "sutra_memory_update":
                        self._memory_needs_update = True
                        yield {
                            "type": "memory_update",
                            "iteration": current_iteration,
                            "phase": current_phase,
                            "message": "Memory updated with connection data",
                        }

                        # Run code manager after processing sutra memory in Phase 3
                        # Use the last_tool_result (the database/search_keyword result that was just processed)
                        if current_phase == 3 and last_tool_result:
                            logger.debug(
                                f"Code manager check: last_tool_result type = {type(last_tool_result)}"
                            )

                            if isinstance(
                                last_tool_result, dict
                            ) and last_tool_result.get("tool_name") in [
                                "database",
                                "search_keyword",
                            ]:
                                logger.debug(
                                    f"Running code manager after sutra memory update in Phase 3 using {last_tool_result.get('tool_name')} result"
                                )
                                self._process_tool_with_code_manager(last_tool_result)
                            else:
                                logger.warning(
                                    f"Skipping code manager - invalid last_tool_result: type={type(last_tool_result)}, is_dict={isinstance(last_tool_result, dict)}"
                                )
                                if isinstance(last_tool_result, dict):
                                    logger.warning(
                                        f"Tool name: {last_tool_result.get('tool_name')}"
                                    )

                    elif event_type in ["completion", "task_complete"]:
                        tool_name = event.get("tool_name", "attempt_completion")
                        # CRITICAL FIX: Only mark task complete if there's actually an attempt_completion
                        # Don't trigger phase completion for other tool completions
                        if (
                            tool_name == "attempt_completion"
                            and event_type == "completion"
                        ):
                            task_complete = True
                            logger.debug(
                                f"Phase {current_phase} marked complete due to attempt_completion"
                            )
                            break
                        elif event_type == "task_complete":
                            task_complete = True
                            logger.debug(
                                f"Phase {current_phase} marked complete due to task_complete event"
                            )
                            break
                        else:
                            logger.debug(
                                f"Ignoring completion event: tool_name={tool_name}, event_type={event_type}"
                            )

                    elif event_type == "tool_error":
                        last_tool_result = event
                        yield event

                    else:
                        yield event

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

                            yield {
                                "type": "phase_complete",
                                "iteration": current_iteration,
                                "completed_phase": current_phase,
                                "next_phase": self.cross_indexing.current_phase,
                                "message": f"Phase {current_phase} complete - advancing to Phase {self.cross_indexing.current_phase}",
                            }

                            last_tool_result = None
                            continue
                        else:
                            yield {
                                "type": "phase_error",
                                "iteration": current_iteration,
                                "phase": current_phase,
                                "message": f"Phase {current_phase} completion failed",
                            }
                            return

                    elif current_phase == 3:
                        # Phase 3 complete - advance to Phase 4 (preserve memory)
                        self.cross_indexing.current_phase = 4
                        # Don't call task_manager.set_current_phase to preserve memory

                        yield {
                            "type": "phase_complete",
                            "iteration": current_iteration,
                            "completed_phase": 3,
                            "next_phase": 4,
                            "message": "Phase 3 complete - advancing to Phase 4 (memory preserved)",
                        }

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

            # Build tool status
            tool_status = self._build_tool_status(last_tool_result)

            # Combine memory and tool status
            if tool_status and tool_status.strip():
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
                # Convert BAML response object to dictionary
                baml_results = response.get("results")
                return self._convert_baml_object_to_dict(baml_results)
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

    def _build_tool_status(self, last_tool_result: Optional[Dict[str, Any]]) -> str:
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

        error = result.get("error", "Unknown error")
        if error:
            status += f"ERROR: {error}\n"

        query = result.get("query")
        if query:
            status += f"Query: '{query}'\n"

        query_name = result.get("query_name")
        if query_name:
            status += f"Query Name: '{query_name}'\n"

        success = result.get("success")
        if success is not None:
            status += f"Status: {'success' if success else 'failed'}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"
        return status.rstrip()

    def _process_tool_with_code_manager(self, event: Dict[str, Any]) -> None:
        """
        Process tool results with code manager to extract connection code.
        Only processes database and search_keyword tools.

        Args:
            event: Tool execution event with results from current iteration
        """
        try:
            logger.debug(f"Code manager processing - event type: {type(event)}")
            logger.debug(
                f"Code manager processing - event keys: {list(event.keys()) if isinstance(event, dict) else 'N/A'}"
            )

            # Validate that event is a dictionary
            if not isinstance(event, dict):
                logger.warning(f"Code manager received non-dict event: {type(event)}")
                return

            logger.debug("Step 1: Getting tool_name")
            tool_name = event.get("tool_name", "unknown")
            logger.debug(f"Step 1 complete: tool_name = {tool_name}")

            logger.debug("Step 2: Getting tool_result")
            tool_result = event.get("data", "")
            logger.debug(
                f"Step 2 complete: tool_result length = {len(str(tool_result))}"
            )

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

            logger.debug(
                f"Processing tool results with code manager for tool: {tool_name}"
            )

            logger.debug("Step 3: Calling _format_tool_for_code_manager")
            formatted_tool_results = self._format_tool_for_code_manager(event)
            logger.debug(
                f"Step 3 complete: formatted_tool_results length = {len(formatted_tool_results)}"
            )

            logger.debug("Step 4: Calling cross_indexing.run_code_manager")
            # Use BAML code manager instead of old LLM call
            baml_result = self.cross_indexing.run_code_manager(formatted_tool_results)
            logger.debug(
                f"Step 4 complete: baml_result success = {baml_result.get('success') if isinstance(baml_result, dict) else 'N/A'}"
            )

            if baml_result.get("success"):
                logger.debug("Step 5: Processing successful BAML result")
                # Process code manager response to extract connection code
                baml_response = baml_result.get("results")
                self._add_code_snippets_to_memory(baml_response)
                logger.debug("BAML code manager processing completed")
            else:
                error_msg = baml_result.get("error", "BAML code manager failed")
                logger.warning(f"BAML code manager error: {error_msg}")

        except Exception as e:
            logger.error(f"Error processing tool results with code manager: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

    def _format_tool_for_code_manager(self, event: Dict[str, Any]) -> str:
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

    def _add_code_snippets_to_memory(self, baml_response) -> None:
        """
        Process BAML code manager response and extract connection code with deduplication.

        Args:
            baml_response: BAML CodeManagerResponse object
        """
        try:
            logger.debug("Processing BAML code manager response for connection code")
            logger.debug(f"BAML response type: {type(baml_response)}")

            if not baml_response:
                logger.debug("No BAML code manager response to process")
                return

            # Process connection code from BAML response (correct field name)
            connection_code_list = None

            # Try different ways to access the connection code
            if hasattr(baml_response, "connection_code"):
                connection_code_list = baml_response.connection_code
                logger.debug(
                    f"Found connection_code attribute with {len(connection_code_list) if connection_code_list else 0} items"
                )
            else:
                logger.debug(
                    f"No connection_code or code_snippets found in BAML response. Available attributes: {[attr for attr in dir(baml_response) if not attr.startswith('_')]}"
                )

            if connection_code_list:
                code_snippets_added = 0
                code_snippets_skipped = 0

                for code_connection in connection_code_list:
                    logger.debug(f"Processing connection: {code_connection}")

                    # Extract fields from CodeConnection object
                    file_path = getattr(code_connection, "file", None)
                    start_line = getattr(code_connection, "start_line", None)
                    end_line = getattr(code_connection, "end_line", None)
                    description = getattr(code_connection, "description", None)

                    if not all([file_path, start_line, end_line, description]):
                        logger.warning(
                            f"Incomplete code connection data: file={file_path}, start={start_line}, end={end_line}, desc={description}"
                        )
                        continue

                    # Check for duplicates before adding
                    if self._is_duplicate_code_snippet(file_path, start_line, end_line):
                        code_snippets_skipped += 1
                        logger.debug(
                            f"Skipped duplicate code snippet: {file_path} lines {start_line}-{end_line}"
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
                        f"Successfully processed BAML code manager: {code_snippets_added} code snippets added, {code_snippets_skipped} duplicates skipped"
                    )
                elif code_snippets_skipped > 0:
                    logger.debug(
                        f"BAML code manager processing: {code_snippets_skipped} duplicate code snippets skipped (already in memory)"
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
        Check if a code snippet already exists in memory.

        Args:
            file_path: Path to the file
            start_line: Starting line number
            end_line: Ending line number

        Returns:
            True if duplicate exists, False otherwise
        """
        try:
            if (
                not hasattr(self.task_manager, "memory_ops")
                or not self.task_manager.memory_ops.code_snippets
            ):
                return False

            for existing_snippet in self.task_manager.memory_ops.code_snippets.values():
                # Check for exact match: same file and overlapping or identical line ranges
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
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking for duplicate code snippet: {e}")
            return False  # If we can't check, allow the addition

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

            # Get tasks created for the next phase
            next_phase = phase + 1
            tasks_to_filter = []

            # Get all pending tasks that were created in this phase for next phase
            for task in self.task_manager.get_tasks_by_status(TaskStatus.PENDING):
                if task:
                    metadata = self.task_manager._task_phase_metadata.get(task.id, {})
                    created_in_phase = metadata.get("created_in_phase")
                    target_phase = metadata.get("target_phase")

                    if created_in_phase == phase and target_phase == next_phase:
                        tasks_to_filter.append(task)

            logger.debug(
                f"Found {len(tasks_to_filter)} tasks to filter from Phase {phase} to Phase {next_phase}"
            )

            if tasks_to_filter:
                logger.debug(f"Running task filtering on {len(tasks_to_filter)} tasks")

                # Run task filtering
                filtered_tasks = self.cross_indexing.filter_tasks(tasks_to_filter)

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

    def _convert_baml_object_to_dict(self, baml_obj) -> Dict[str, Any]:
        """Convert BAML response object to dictionary format."""
        try:
            if not baml_obj:
                return {}

            # If already a dictionary, return as is
            if isinstance(baml_obj, dict):
                return baml_obj

            # Convert object attributes to dictionary
            result_dict = {}

            # Handle thinking
            if hasattr(baml_obj, "thinking"):
                result_dict["thinking"] = baml_obj.thinking

            # Handle tool_call
            if hasattr(baml_obj, "tool_call"):
                tool_call = baml_obj.tool_call
                if tool_call:
                    result_dict["tool_call"] = {
                        "tool_name": getattr(tool_call, "tool_name", None),
                        "parameters": getattr(tool_call, "parameters", {}),
                    }

            # Handle sutra_memory
            if hasattr(baml_obj, "sutra_memory"):
                sutra_memory = baml_obj.sutra_memory
                if sutra_memory and hasattr(sutra_memory, "__dict__"):
                    result_dict["sutra_memory"] = {
                        "add_history": getattr(sutra_memory, "add_history", None),
                        "tasks": getattr(sutra_memory, "tasks", []),
                    }
                elif sutra_memory:
                    result_dict["sutra_memory"] = sutra_memory

            # Handle attempt_completion
            if hasattr(baml_obj, "attempt_completion"):
                attempt_completion = baml_obj.attempt_completion
                if attempt_completion:
                    result_dict["attempt_completion"] = {
                        "result": getattr(
                            attempt_completion, "result", str(attempt_completion)
                        )
                    }

            # Handle reasoning (fallback for thinking)
            if "thinking" not in result_dict and hasattr(baml_obj, "reasoning"):
                result_dict["thinking"] = baml_obj.reasoning

            # Handle next_steps (fallback for attempt_completion)
            if "attempt_completion" not in result_dict and hasattr(
                baml_obj, "next_steps"
            ):
                result_dict["attempt_completion"] = {"result": baml_obj.next_steps}

            logger.debug(
                f"Converted BAML object to dict with keys: {list(result_dict.keys())}"
            )
            return result_dict

        except Exception as e:
            logger.error(f"Error converting BAML object to dict: {e}")
            return {"thinking": f"Error converting BAML response: {str(e)}"}

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

            # Get the analysis result from connection splitting and convert BAML object to dict
            baml_analysis_result = splitting_result.get("results")
            analysis_result = self._convert_connection_splitting_to_dict(
                baml_analysis_result
            )

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
                    # Apply corrections to analysis result
                    corrected_analysis = self._apply_technology_corrections(
                        analysis_result, correction_result.get("results")
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

    def _convert_connection_splitting_to_dict(self, baml_response) -> Dict[str, Any]:
        """Convert BAML ConnectionSplittingResponse to dictionary format."""
        try:
            if not baml_response:
                return {}

            # If already a dictionary, return as is
            if isinstance(baml_response, dict):
                return baml_response

            result = {}

            # Extract incoming connections
            if hasattr(baml_response, "incoming_connections"):
                result["incoming_connections"] = []
                incoming = baml_response.incoming_connections
                if incoming:
                    # Convert BAML object structure to expected dictionary format
                    for tech_name, files_data in incoming.items():
                        for file_path, connections in files_data.items():
                            for conn in connections:
                                result["incoming_connections"].append(
                                    {
                                        "description": getattr(conn, "description", ""),
                                        "file_path": file_path,
                                        "snippet_lines": self._parse_snippet_lines(
                                            getattr(conn, "snippet_lines", "")
                                        ),
                                        "technology": {
                                            "name": tech_name,
                                            "type": "unknown",
                                        },
                                    }
                                )

            # Extract outgoing connections
            if hasattr(baml_response, "outgoing_connections"):
                result["outgoing_connections"] = []
                outgoing = baml_response.outgoing_connections
                if outgoing:
                    # Convert BAML object structure to expected dictionary format
                    for tech_name, files_data in outgoing.items():
                        for file_path, connections in files_data.items():
                            for conn in connections:
                                result["outgoing_connections"].append(
                                    {
                                        "description": getattr(conn, "description", ""),
                                        "file_path": file_path,
                                        "snippet_lines": self._parse_snippet_lines(
                                            getattr(conn, "snippet_lines", "")
                                        ),
                                        "technology": {
                                            "name": tech_name,
                                            "type": "unknown",
                                        },
                                    }
                                )

            # Extract summary if available
            if hasattr(baml_response, "summary"):
                result["summary"] = baml_response.summary

            logger.debug(
                f"Converted connection splitting response: {len(result.get('incoming_connections', []))} incoming, {len(result.get('outgoing_connections', []))} outgoing"
            )
            return result

        except Exception as e:
            logger.error(f"Error converting connection splitting response: {e}")
            return {
                "incoming_connections": [],
                "outgoing_connections": [],
                "error": str(e),
            }

    def _parse_snippet_lines(self, snippet_range: str) -> list:
        """Parse snippet lines from range format (e.g., '15-20') to list of line numbers."""
        try:
            if not snippet_range or "-" not in snippet_range:
                return []

            start, end = snippet_range.split("-")
            return list(range(int(start), int(end) + 1))
        except (ValueError, AttributeError):
            return []

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
                matches = matching_result.get("results", {}).get("matches", [])

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
                    print(
                        f"✅ Stored {len(db_matches)} connection mappings in database"
                    )
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
        """Get list of technology names that don't match valid enums."""
        valid_enums = {
            "GraphQL",
            "HTTP/HTTPS",
            "MessageQueue",
            "Unknown",
            "WebSockets",
            "gRPC",
        }
        unmatched = set()

        # Check incoming connections
        for connection in analysis_result.get("incoming_connections", []):
            tech_name = connection.get("technology", {}).get("name")
            if tech_name and tech_name not in valid_enums:
                unmatched.add(tech_name)

        # Check outgoing connections
        for connection in analysis_result.get("outgoing_connections", []):
            tech_name = connection.get("technology", {}).get("name")
            if tech_name and tech_name not in valid_enums:
                unmatched.add(tech_name)

        return list(unmatched)

    def _apply_technology_corrections(
        self, analysis_result: Dict[str, Any], baml_corrections
    ) -> Dict[str, Any]:
        """Apply technology corrections to analysis result."""
        try:
            # Convert BAML response to dictionary if needed
            if hasattr(baml_corrections, "corrections"):
                corrections_list = baml_corrections.corrections
            else:
                corrections_list = baml_corrections.get("corrections", [])

            if not corrections_list:
                logger.debug("No corrections provided by technology correction")
                return analysis_result

            # Build correction mapping
            correction_map = {}
            for correction in corrections_list:
                if hasattr(correction, "original_name") and hasattr(
                    correction, "corrected_name"
                ):
                    correction_map[correction.original_name] = correction.corrected_name
                elif isinstance(correction, dict):
                    correction_map[correction.get("original_name")] = correction.get(
                        "corrected_name"
                    )

            logger.debug(f"Applying technology corrections: {correction_map}")

            # Apply corrections to incoming connections
            for connection in analysis_result.get("incoming_connections", []):
                tech_name = connection.get("technology", {}).get("name")
                if tech_name in correction_map:
                    connection["technology"]["name"] = correction_map[tech_name]
                    connection["technology"]["type"] = "corrected"

            # Apply corrections to outgoing connections
            for connection in analysis_result.get("outgoing_connections", []):
                tech_name = connection.get("technology", {}).get("name")
                if tech_name in correction_map:
                    connection["technology"]["name"] = correction_map[tech_name]
                    connection["technology"]["type"] = "corrected"

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
