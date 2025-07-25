"""
Cross-Index Service for analyzing and managing inter-service connections
"""

import json
from typing import Dict, List, Any, Optional, Iterator
from loguru import logger

from graph.sqlite_client import SQLiteConnection
from services.project_manager import ProjectManager
from services.agent.xml_service.xml_parser import XMLParser
from services.agent.xml_service.xml_repair import XMLRepair

from ...agent.memory_management.sutra_memory_manager import SutraMemoryManager
from ...agent.memory_management.code_fetcher import CodeFetcher
from ..prompts.cross_index_prompt_manager import CrossIndexPromptManager
from ..utils import infer_technology_type
from ...agent.tool_action_executor.tool_action_executor import ActionExecutor

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
        session_manager=None,
        llm_client=None,
    ):
        self.db_connection = db_connection
        self.project_manager = project_manager
        self.memory_manager = memory_manager
        self.session_manager = session_manager
        self.llm_client = llm_client
        self.xml_parser = XMLParser()
        self.xml_repair = XMLRepair(llm_client)
        self.prompt_manager = CrossIndexPromptManager()
        self.code_fetcher = CodeFetcher(db_connection)
        self.action_executor = ActionExecutor(
            db_connection, self.project_manager.vector_db, self.memory_manager
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

            # Track last tool result for context
            last_tool_result = None

            # Analysis loop similar to agent service
            current_iteration = 0
            max_iterations = 50

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

                            # Check if this is attempt_completion tool specifically
                            if tool_name == "attempt_completion":
                                # Handle attempt_completion tool specifically for cross-indexing
                                completion_result = event.get("result", "")
                                yield {
                                    "type": "analysis_complete",
                                    "iteration": current_iteration,
                                    "message": "Cross-indexing analysis completed with attempt_completion",
                                }

                                # Parse the attempt_completion JSON format
                                analysis_result = self._parse_attempt_completion_json(
                                    completion_result
                                )
                                task_complete = True
                                break
                            else:
                                # Handle other tool_use events
                                # Store tool result for next iteration context
                                last_tool_result = event

                                # Update Sutra memory with tool results
                                self._update_cross_index_memory(event)

                                # Mark memory for update (like agent service)
                                self._memory_needs_update = True

                                # Yield the original event as-is (like agent service)
                                yield event

                        elif event_type == "task_complete":
                            completion = event.get("completion", {})
                            result_text = completion.get("result", "")

                            # Try to parse the result_text as JSON first
                            try:
                                import json

                                # Try to parse as JSON directly
                                if result_text.strip().startswith("{"):
                                    json_data = json.loads(result_text)
                                    if (
                                        "incoming_connections" in json_data
                                        or "outgoing_connections" in json_data
                                    ):
                                        logger.debug(
                                            "Found JSON format in task_complete result"
                                        )
                                        analysis_result = (
                                            self._parse_attempt_completion_json(
                                                result_text
                                            )
                                        )
                                        task_complete = True
                                        yield {
                                            "type": "analysis_complete",
                                            "iteration": current_iteration,
                                            "message": "Cross-indexing analysis completed via task_complete with JSON",
                                        }
                                        break
                            except (json.JSONDecodeError, Exception) as e:
                                logger.debug(
                                    f"Could not parse task_complete result as JSON: {e}"
                                )

                            # If not JSON, treat as regular completion without attempt_completion
                            yield {
                                "type": "analysis_complete",
                                "iteration": current_iteration,
                                "message": "Cross-indexing analysis completed - but no attempt_completion found",
                            }

                            # No XML parsing - only attempt_completion is supported
                            logger.warning(
                                "Task completed without attempt_completion tool - no connections found"
                            )
                            analysis_result = {
                                "incoming_connections": [],
                                "outgoing_connections": [],
                                "potential_matches": [],
                                "error": "Analysis completed without proper attempt_completion format",
                            }
                            task_complete = True
                            break

                        elif event_type == "error":
                            error_msg = event.get("error", "Unknown error")
                            # Yield error update
                            yield {
                                "type": "tool_error",
                                "iteration": current_iteration,
                                "error": error_msg,
                                "message": f"Tool error in iteration {current_iteration}, continuing...",
                            }

                            # Continue with next iteration instead of failing immediately
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

                    # Break if task completed
                    if task_complete and analysis_result:
                        if "error" not in analysis_result:
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
                        else:
                            # Don't retry on errors - run only once
                            logger.warning(
                                f"Analysis completed with errors: {analysis_result.get('error')}"
                            )
                            yield {
                                "type": "analysis_error",
                                "iteration": current_iteration,
                                "error": analysis_result.get("error"),
                                "message": "Analysis completed with errors - no retry",
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
            # Get cross-index system prompt
            system_prompt = self.prompt_manager.cross_index_system_prompt()

            # Build tool status from last tool result
            tool_status = self._build_cross_index_tool_status(last_tool_result)

            # Get rich sutra memory from session manager first (for persistence), then memory manager
            session_memory = ""
            if self.session_manager:
                session_memory = self.session_manager.get_sutra_memory()

            # If session has memory, use it; otherwise use memory manager
            if session_memory and session_memory.strip():
                sutra_memory_rich = session_memory
                logger.debug("Using persisted session memory for cross-indexing")
            else:
                sutra_memory_rich = self.memory_manager.get_memory_for_llm()
                logger.debug("Using memory manager memory for cross-indexing")

            user_message_parts = []

            # Add analysis query
            user_message_parts.append(
                f"====\nCross-Index Analysis Query: {analysis_query}"
            )

            # Add sutra memory - check for meaningful content
            logger.debug(
                f"Cross-Index Sutra memory length: {len(sutra_memory_rich) if sutra_memory_rich else 0}"
            )

            # Check if this is first iteration (no memory) or has existing memory
            if current_iteration == 1:
                user_message_parts.append(
                    f"\n====\nSUTRA MEMORY STATUS\n\nNo previous memory available. Starting cross-indexing analysis."
                )
                logger.debug("Cross-Index: First iteration with empty memory")
            elif sutra_memory_rich and sutra_memory_rich.strip():
                user_message_parts.append(
                    f"\n====\nSUTRA MEMORY STATUS\n\n{sutra_memory_rich}"
                )
                logger.debug(
                    "Cross-Index: Using existing Sutra memory from previous iterations"
                )
            else:
                user_message_parts.append(
                    f"\n====\nSUTRA MEMORY STATUS\n\nNo previous memory available."
                )
                logger.debug("Cross-Index: No memory available")

            # Add tool status
            user_message_parts.append(f"\n====\nTOOL STATUS\n\n{tool_status}\n====")

            # Add reasoning prompt from memory manager
            reasoning_prompt = self.memory_manager.generate_reasoning_prompt(
                analysis_query
            )
            if reasoning_prompt != "No previous tool executions found.":
                user_message_parts.append(
                    f"\n====\nREASONING CHECKPOINT\n\n{reasoning_prompt}\n===="
                )

            user_message = "\n".join(user_message_parts)

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

        query = result.get("query")
        if query and query != "fetch_next_code":
            status += f"Query: '{query}'\n"

        count = result.get("count") or result.get("total_nodes")
        if count is not None:
            status += f"Found {count} nodes for connection analysis\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store all connection-related code snippets in Sutra memory, as search results will not persist to subsequent iterations."
        return status.rstrip()

    def _build_search_keyword_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build keyword search status for cross-indexing."""
        status = "Tool: search_keyword\n"

        keyword = result.get("keyword")
        if keyword:
            status += f"Keyword: '{keyword}'\n"

        matches_found = result.get("matches_found")
        if matches_found:
            matches_status = "Found" if matches_found else "Not Found"
            status += f"Matches Status: '{matches_status}'\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store all connection-related code snippets in Sutra memory, as search results will not persist to subsequent iterations."
        return status.rstrip()

    def _build_list_files_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build list files status for cross-indexing."""
        status = "Tool: list_files\n"

        directory = result.get("directory")
        if directory:
            status += f"Directory: {directory}\n"

        count = result.get("count")
        if count is not None:
            status += f"Files: {count} found\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store relevant file/folder information in Sutra memory's history section for connection analysis, as directory listings will not persist to subsequent iterations."
        return status.rstrip()

    def _build_database_status_cross_index(self, result: Dict[str, Any]) -> str:
        """Build database status for cross-indexing."""
        status = "Tool: database\n"

        query_name = result.get("query_name")
        if query_name:
            status += f"Query Name: {query_name}\n"

        query = result.get("query")
        if query:
            status += f"Query: {query}\n"

        count = result.get("count") or result.get("total_results")
        if count is not None:
            status += f"Results: {count} found\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store all connection-related code snippets in Sutra memory, as database query results will not persist to subsequent iterations."
        return status.rstrip()

    def _build_generic_status_cross_index(
        self, result: Dict[str, Any], tool_name: str
    ) -> str:
        """Build generic status for unknown tools in cross-indexing."""
        status = f"Tool: {tool_name}\n"

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
                    memory_entry = f"Cross-Index: Found {count} nodes for query '{query}' - analyzing for connection patterns"
                    self.memory_manager.add_history(memory_entry)

            elif tool_name == "search_keyword":
                keyword = event.get("keyword", "")
                matches = event.get("matches_found", False)
                if matches:
                    memory_entry = f"Cross-Index: Found keyword '{keyword}' - potential connection indicator"
                    self.memory_manager.add_history(memory_entry)

            elif tool_name == "list_files":
                directory = event.get("directory", "")
                count = event.get("count", 0)
                memory_entry = f"Cross-Index: Listed {count} files in {directory} - scanning for connection files"
                self.memory_manager.add_history(memory_entry)

        except Exception as e:
            logger.error(f"Error updating cross-index memory: {e}")

    def _update_session_memory(self):
        """Update session memory with current memory state (like agent service)."""
        if not self.session_manager:
            logger.warning(
                "No session manager available for cross-index memory persistence"
            )
            return

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

    def _parse_attempt_completion_json(self, completion_content: str) -> Dict[str, Any]:
        """
        Parse attempt_completion JSON format for cross-indexing.

        Args:
            completion_content: Content from attempt_completion tool

        Returns:
            Parsed analysis data in the expected format
        """
        try:
            # Extract JSON from attempt_completion XML tags or raw JSON
            import re

            # Try to find JSON in attempt_completion tags first
            pattern = r"<attempt_completion>\s*(\{.*?\})\s*</attempt_completion>"
            match = re.search(pattern, completion_content, re.DOTALL)

            if match:
                json_content = match.group(1)
            else:
                # Try to find raw JSON in the content
                json_pattern = r"(\{[^{}]*\"incoming_connections\"[^{}]*\})"
                json_match = re.search(json_pattern, completion_content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                else:
                    # If no JSON found, try to parse the entire content as JSON
                    json_content = completion_content.strip()

            # Parse JSON
            try:
                json_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON, trying to extract from text: {e}"
                )
                # If JSON parsing fails, return empty result but don't error
                return {
                    "incoming_connections": [],
                    "outgoing_connections": [],
                    "potential_matches": [],
                    "error": f"Could not parse completion format: {str(e)}",
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
                f"Parsed attempt_completion: {len(result['incoming_connections'])} incoming, {len(result['outgoing_connections'])} outgoing connections"
            )
            return result

        except Exception as e:
            logger.error(f"Error parsing attempt_completion JSON: {e}")
            logger.error(f"Raw content: {completion_content}")
            return {
                "error": str(e),
                "raw_content": completion_content,
                "incoming_connections": [],
                "outgoing_connections": [],
                "potential_matches": [],
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

            return {
                "incoming": incoming_results,
                "outgoing": outgoing_results
            }

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
                    # Get file_hash_id from file path if not provided
                    file_hash_id = self._get_file_hash_id(
                        project_id, conn.get("file_path")
                    ) if "file_hash_id" not in conn else conn["file_hash_id"]

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
                    # Get file_hash_id from file path if not provided
                    file_hash_id = self._get_file_hash_id(
                        project_id, conn.get("file_path")
                    ) if "file_hash_id" not in conn else conn["file_hash_id"]

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
                "message": f"Successfully stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections"
            }

        except Exception as e:
            logger.error(f"Error storing connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store connections"
            }

    def create_connection_mappings_by_ids(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                        match.get("match_confidence", 0.0)
                    )
                )
                created_mappings.append(cursor.lastrowid)

            self.db_connection.connection.commit()

            return {
                "success": True,
                "mapping_ids": created_mappings,
                "message": f"Created {len(created_mappings)} connection mappings"
            }

        except Exception as e:
            logger.error(f"Error creating connection mappings: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create connection mappings"
            }

    def _get_file_hash_id(self, project_id: int, file_path: str) -> Optional[int]:
        """Get file_hash_id for a given project and file path."""
        try:
            result = self.db_connection.execute_query(
                "SELECT id FROM file_hashes WHERE project_id = ? AND file_path = ?",
                (project_id, file_path),
            )
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Error getting file_hash_id: {e}")
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

            # Build connection matching prompt
            matching_prompt = self.prompt_manager.get_connection_matching_prompt(
                incoming_connections, outgoing_connections
            )

            # Call LLM for connection matching - no system prompt needed, return raw response
            logger.debug("🔗 Starting connection matching analysis...")
            logger.debug(
                f"📊 Analyzing {len(incoming_connections)} incoming and {len(outgoing_connections)} outgoing connections"
            )
            response = self.llm_client.call_llm("", matching_prompt, return_raw=True)

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

            # Validate and process matching results
            is_valid, processed_results = (
                self.prompt_manager.validate_and_process_matching_results(
                    response_json, incoming_connections, outgoing_connections
                )
            )

            if not is_valid:
                logger.error(f"Invalid matching response: {processed_results}")
                return {
                    "success": False,
                    "error": processed_results,
                    "message": "Connection matching failed due to invalid response",
                }

            # Create connection mappings in database
            matches = processed_results.get("matches", [])
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
                        "endpoint": self._extract_endpoint_from_description(
                            result["description"]
                        ),
                        "method": self._extract_method_from_description(
                            result["description"]
                        ),
                        "file_path": result["file_path"],
                        "line_number": "N/A",  # Could be extracted from snippet_lines if needed
                        "technology": result["technology_name"],
                        "description": result["description"],
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error getting connections by IDs: {e}")
            return []

    def _extract_endpoint_from_description(self, description: str) -> str:
        """Extract endpoint path from connection description."""
        import re

        # Look for patterns like "/api/users", "/health", etc.
        endpoint_match = re.search(r"(/[a-zA-Z0-9/_-]+)", description)
        return endpoint_match.group(1) if endpoint_match else "N/A"

    def _extract_method_from_description(self, description: str) -> str:
        """Extract HTTP method from connection description."""
        description_upper = description.upper()
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            if method in description_upper:
                return method
        return "N/A"

    def _convert_confidence_to_float(self, confidence: str) -> float:
        """Convert confidence level string to float."""
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        return confidence_map.get(confidence.lower(), 0.5)
