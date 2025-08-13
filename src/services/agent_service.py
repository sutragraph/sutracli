"""Agent Service with unified tool status handling."""

import time
from typing import Dict, Any, List, Optional, Iterator, Union
from loguru import logger
from .llm_clients.llm_factory import llm_client_factory
from tools import ActionExecutor
from .agent.session_management import SessionManager
from .agent.memory_management import SutraMemoryManager
from .agent.error_handler import ErrorHandler, ResultVerifier
from .project_manager import ProjectManager
from utils.xml_parsing_exceptions import (
    XMLParsingFailedException,
    UserCancelledException,
)
from utils.performance_monitor import get_performance_monitor, performance_timer
from utils.debug_utils import get_user_confirmation_for_llm_call
from agents import get_agent_system_prompt, AgentName


class AgentService:
    """Agent Service with unified tool status handling."""

    def __init__(
        self, session_id: Optional[str] = None, project_path: Optional[str] = None
    ):
        """Initialize the Agent Service.

        Args:
            session_id: Optional session ID for conversation continuity
            project_path: Optional path to the project directory. If None, uses current directory.
        """
        self.llm_client = llm_client_factory()

        self.session_manager = SessionManager.get_or_create_session(session_id)
        self.memory_manager = SutraMemoryManager()

        self.session_data: List[Dict[str, Any]] = []

        # Store project path for future reference
        self.project_path = project_path

        # Initialize project manager for centralized project operations
        self.project_manager = ProjectManager(self.memory_manager)

        # XML-based action executor with shared sutra memory manager and shared project indexer
        self.action_executor = ActionExecutor(
            self.memory_manager,
        )

        # Track last tool result for context -
        self.last_tool_result = None

        # Memory update optimization flag
        self._memory_needs_update = False

        # Consecutive failures tracking
        self._consecutive_failures = 0

        # Initialize error handler and result verifier
        self.error_handler = ErrorHandler()
        self.result_verifier = ResultVerifier()

        # Determine current project name from specified or working directory
        from pathlib import Path

        if project_path:
            project_path_obj = Path(project_path)
        else:
            project_path_obj = Path.cwd()

        self.current_project_name = self.project_manager.determine_project_name(
            project_path_obj
        )

        # Performance monitoring
        self.performance_monitor = get_performance_monitor()

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens_used = 0
        self.llm_call_count = 0

        # Check if project exists in database and auto-index if needed
        self.project_manager.ensure_project_indexed(
            self.current_project_name, project_path_obj
        )

    def _perform_incremental_indexing(self) -> Iterator[Dict[str, Any]]:
        """Perform incremental reindexing of the database using the current project name."""
        yield from self.project_manager.perform_incremental_indexing(
            self.current_project_name
        )

    def _update_session_memory(self):
        """Update session memory with current memory state."""
        try:
            # Get the rich formatted memory from memory manager (includes code snippets)
            memory_summary = (
                self.action_executor.sutra_memory_manager.get_memory_for_llm()
            )
            # Update session manager with the rich memory content
            self.session_manager.update_sutra_memory(memory_summary)
            logger.debug(
                f"Updated Sutra Memory in session: {len(memory_summary)} characters"
            )
            logger.debug(
                f"Memory includes {len(self.action_executor.sutra_memory_manager.get_all_code_snippets())} code snippets"
            )
        except Exception as e:
            logger.error(f"Error updating session memory: {e}")

    def _is_critical_tool_failure(self, event: Dict[str, Any]) -> bool:
        """Determine if a tool failure is critical enough to stop execution."""
        tool_name = event.get("tool_name", "")
        error_msg = event.get("error", event.get("message", "")).lower()

        # Critical tool failures that should stop execution
        critical_tools = ["write_to_file", "apply_diff", "execute_command"]
        critical_errors = [
            "permission denied",
            "file not found",
            "directory not found",
            "invalid path",
            "access denied",
            "command not found",
            "syntax error",
            "compilation error",
        ]

        # Stop if critical tool fails
        if tool_name in critical_tools:
            return True

        # Stop if error message indicates critical failure
        for critical_error in critical_errors:
            if critical_error in error_msg:
                return True

        # Stop if multiple consecutive failures (indicates systemic issue)
        if hasattr(self, "_consecutive_failures"):
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                return True
        else:
            self._consecutive_failures = 1

        return False

    def _detect_simple_completion(self, event: Dict[str, Any], user_query: str) -> bool:
        """Detect if a simple task has been completed successfully."""
        tool_name = event.get("tool_name", "")
        query_lower = user_query.lower()

        # Simple completion patterns
        simple_completions = {
            # "list_files": ["list", "show", "find files", "what files"],
            # "search_keyword": ["search", "find", "look for"],
            # "semantic_search": ["find", "search", "look for", "where is"],
            # "write_to_file": ["create", "write", "make", "generate"],
            # "execute_command": ["run", "execute", "create", "copy", "clone"]
        }

        # Check if this tool typically completes the user's query
        if tool_name in simple_completions:
            patterns = simple_completions[tool_name]
            for pattern in patterns:
                if pattern in query_lower:
                    # Check if tool was successful
                    if event.get("success", True) and event.get("type") != "error":
                        logger.debug(f"Detected simple completion for {tool_name}")
                        return True

        return False

    def solve_problem(
        self, problem_query: str, project_id: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """Main entry point for the agent to solve a problem autonomously."""
        # Always perform incremental indexing to catch external code changes
        yield from self._perform_incremental_indexing()
        query_id = self.session_manager.start_new_query(problem_query)
        self.session_manager.set_problem_context(problem_query)

        # Set reasoning context in memory manager
        self.memory_manager.set_reasoning_context(problem_query)

        # Add user query to sutra memory at the start
        # Get rich memory from memory manager
        current_memory_rich = self.memory_manager.get_memory_for_llm()

        if current_memory_rich and current_memory_rich.strip():
            updated_memory = f"{current_memory_rich}\n\nUSER QUERY: {problem_query}"
        else:
            updated_memory = f"USER QUERY: {problem_query}"
        self.session_manager.update_sutra_memory(updated_memory)

        yield {
            "type": "session_start",
            "session_id": self.session_manager.session_id,
            "query_id": query_id,
            "problem": problem_query,
            "timestamp": time.time(),
        }

        yield from self._solving_loop(problem_query)

    def continue_conversation(
        self, query: str, project_id: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """Continue conversation in existing session with a new query."""
        # Start new query in session
        query_id = self.session_manager.start_new_query(query)

        # Clear session data for the new query to ensure clean state
        self.session_manager.clear_session_data_for_current_query()
        self.last_tool_result = None

        # Reset consecutive failures for new query
        self._consecutive_failures = 0

        # Clear reasoning context in memory manager
        self.memory_manager.clear_reasoning_context()

        # Clear error handler and result verifier history
        self.error_handler.clear_history()
        self.result_verifier.clear_history()

        # Set new reasoning context for continuation
        self.memory_manager.set_reasoning_context(query)

        # Add user query to sutra memory for continuation
        # Get rich memory from memory manager
        current_memory_rich = self.memory_manager.get_memory_for_llm()

        if current_memory_rich and current_memory_rich.strip():
            updated_memory = f"{current_memory_rich}\n\nUSER QUERY: {query}"
        else:
            updated_memory = f"USER QUERY: {query}"
        self.session_manager.update_sutra_memory(updated_memory)

        yield {
            "type": "query_start",
            "session_id": self.session_manager.session_id,
            "query_id": query_id,
            "query": query,
            "timestamp": time.time(),
            "sutra_memory_length": len(self.session_manager.get_sutra_memory()),
        }

        # Perform incremental indexing before processing the continuation query
        yield from self._perform_incremental_indexing()

        yield from self._solving_loop(query)

    def _solving_loop(self, user_query: str) -> Iterator[Dict[str, Any]]:
        """Main solving loop using XML-based responses."""
        current_iteration = 0
        max_iterations = 20  # Reduced from 50 to 20 for faster completion

        while current_iteration < max_iterations:
            current_iteration += 1

            # Show progress for each iteration
            print(f"Iteration {current_iteration}/{max_iterations}")

            # User confirmation every 15 iterations
            if current_iteration % 15 == 0:
                print(
                    f"\nWarning: This process has been running for {current_iteration} iterations."
                )
                user_input = (
                    input("Do you want to continue? (yes/no): ").lower().strip()
                )
                if user_input != "yes":
                    yield {
                        "type": "info",
                        "message": f"Process terminated by user after {current_iteration} iterations",
                    }
                    return

            try:
                # Get XML response from LLM
                xml_response = self._get_xml_response(user_query, current_iteration)

                # Handle error responses from LLM
                if isinstance(xml_response, dict) and xml_response.get("type") == "error":
                    yield xml_response
                    break

                # Ensure xml_response is a list for processing
                if isinstance(xml_response, str):
                    # If it's a string, we need to parse it as XML first
                    # This shouldn't normally happen but handle it gracefully
                    yield {
                        "type": "error",
                        "error": "Received string response instead of parsed XML",
                        "iteration": current_iteration,
                    }
                    break

                # Process XML response using XML action executor
                task_complete = False
                tool_failed = False
                # Ensure xml_response is a list for processing
                if not isinstance(xml_response, list):
                    xml_response = []
                for event in self.action_executor.process_xml_response(
                    xml_response, user_query
                ):
                    yield event

                    # Track completion status
                    if event.get("type") == "task_complete":
                        task_complete = True
                        event["iteration"] = current_iteration

                    # : Capture ANY tool result - no complex event type checking
                    elif event.get("type") not in [
                        "thinking",
                        "sutra_memory_update",
                        "task_complete",
                    ]:
                        # Store ANY non-thinking, non-memory event as tool result
                        self.last_tool_result = event

                        # Improve tool call visibility - extract tool name from event
                        tool_name = event.get("tool_name", "unknown")

                        # Show tool execution for all relevant events
                        event_type = event.get("type", "unknown")

                        # BUGFIX: Only log the main tool_use events, not individual search results
                        # This prevents multiple log entries for semantic search individual results
                        # Only log once per tool execution, not for each individual result
                        should_log = False
                        if event_type == "tool_use":
                            # For semantic_search, only log if this is the first result or has batch_info
                            if tool_name == "semantic_search":
                                node_index = event.get("node_index", 1)
                                batch_info = event.get("batch_info")
                                # Only log for first node or when batch info is present
                                should_log = node_index == 1 or batch_info is not None
                            else:
                                # For other tools, always log tool_use events
                                should_log = True
                        elif tool_name != "semantic_search":
                            # For non-semantic_search tools, log other event types
                            should_log = True

                        if should_log:
                            print(f"🔧 Tool: {tool_name} ({event_type})")

                        # Validate tool result using SutraMemoryManager
                        validation_result = self.memory_manager.validate_tool_result(
                            tool_name, event, user_query
                        )

                        # Verify result using result verifier
                        verification_result = self.result_verifier.verify_result(
                            tool_name, event
                        )

                        # Show validation results
                        if not validation_result["valid"]:
                            print(
                                f"Warning: Tool validation failed: {validation_result['issues']}"
                            )
                            if validation_result["suggestions"]:
                                print(
                                    f"💡 Suggestions: {validation_result['suggestions']}"
                                )

                        # Show verification results
                        if not verification_result["verified"]:
                            print(
                                f"Error: Result verification failed: {verification_result['issues']}"
                            )
                            if verification_result["recommendations"]:
                                print(
                                    f"📝 Recommendations: {verification_result['recommendations']}"
                                )

                        # # Show data preview for successful tool use
                        # if event_type == "tool_use" and "data" in event:
                        #     data_preview = str(event["data"])[:200]
                        #     print(f"   Result: {data_preview}...")
                        # elif "results" in event:
                        #     results_preview = str(event["results"])[:200]
                        #     print(f"   Result: {results_preview}...")
                        # elif "output" in event:
                        #     output_preview = str(event["output"])[:200]
                        #     print(f"   Output: {output_preview}...")

                        # Check for tool failures and stop if critical
                        if (
                            event.get("type") == "error"
                            or event.get("success") is False
                            or event.get("type") == "tool_error"
                        ):
                            error_msg = event.get(
                                "error", event.get("message", "Unknown error")
                            )
                            logger.error(f"Tool {tool_name} failed: {error_msg}")
                            print(f"Error: Tool {tool_name} failed: {error_msg}")

                            # Stop on critical tool failures
                            if self._is_critical_tool_failure(event):
                                tool_failed = True
                                yield {
                                    "type": "critical_error",
                                    "message": f"Critical tool failure: {error_msg}",
                                    "tool": tool_name,
                                    "iteration": current_iteration,
                                }
                                break
                        else:
                            # Reset consecutive failures on success
                            self._consecutive_failures = 0

                            # Check for simple completion
                            if self._detect_simple_completion(event, user_query):
                                print(f"Target: Simple task completed with {tool_name}")
                                task_complete = True

                        # Check if execution should continue based on validation
                        if not self.memory_manager.should_continue_execution(
                            validation_result, self._consecutive_failures
                        ):
                            logger.warning(
                                f"🛑 Stopping execution due to validation failure"
                            )
                            tool_failed = True
                            yield {
                                "type": "validation_failure",
                                "message": f"Execution stopped due to validation failure",
                                "tool": tool_name,
                                "validation": validation_result,
                                "iteration": current_iteration,
                            }
                            break

                    # Handle Sutra Memory updates
                    elif event.get("type") == "sutra_memory_update":
                        memory_result = event.get("result", {})
                        if memory_result.get("success"):
                            # Defer memory formatting to reduce overhead
                            # Only format memory when really needed
                            self._memory_needs_update = True
                            logger.debug("Marked memory for update")
                        else:
                            logger.warning(
                                f"Sutra Memory update failed: {memory_result.get('errors', [])}"
                            )

                # Update memory if needed before next iteration
                if self._memory_needs_update:
                    self._update_session_memory()
                    self._memory_needs_update = False

                # Check if task is likely complete using SutraMemoryManager
                if not task_complete:
                    completion_analysis = self.memory_manager.analyze_task_completion(
                        user_query
                    )
                    if completion_analysis["likely_complete"]:
                        print(
                            f"Target: Task likely complete: {completion_analysis['reason']}"
                        )
                        task_complete = True

                # Break if tool failed critically
                if tool_failed:
                    logger.error(
                        f"💥 Critical tool failure in iteration {current_iteration}, stopping loop"
                    )
                    yield {
                        "type": "execution_stopped",
                        "reason": "critical_tool_failure",
                        "iteration": current_iteration,
                    }
                    break

                # Break if task was completed
                if task_complete:
                    logger.debug(
                        f"Target: Task completed in iteration {current_iteration}, stopping loop"
                    )
                    print(
                        f"Success: Task completed successfully in {current_iteration} iterations"
                    )
                    # Log performance summary
                    self.performance_monitor.log_performance_summary()
                    # Log token usage summary
                    self.log_token_usage_summary()
                    break

            except UserCancelledException as e:
                logger.info(
                    f"User cancelled operation in iteration {current_iteration}"
                )
                yield {
                    "type": "user_cancelled",
                    "message": str(e),
                    "iteration": current_iteration,
                    "session_id": self.session_manager.session_id,
                }
                break

            except Exception as e:
                logger.error(
                    f"Error: Error in solving loop iteration {current_iteration}: {e}"
                )
                yield {
                    "type": "error",
                    "error": str(e),
                    "iteration": current_iteration,
                    "session_id": self.session_manager.session_id,
                }
                # Log token usage summary even when there's an error
                self.log_token_usage_summary()
                break

        if current_iteration >= max_iterations:
            yield {
                "type": "warning",
                "message": f"Maximum iterations ({max_iterations}) reached. Terminating session.",
            }
            # Log token usage summary when max iterations reached
            self.log_token_usage_summary()

    @performance_timer("get_xml_response")
    def _get_xml_response(
        self, user_query: str, current_iteration: int
    ) -> Union[List[Dict[str, Any]], str, Dict[str, Any]]:
        """Get XML response from LLM using the new prompt system with retry on XML parsing failures."""
        if not get_user_confirmation_for_llm_call():
            logger.info("User cancelled Agent LLM call in debug mode")
            raise UserCancelledException("User cancelled the operation in debug mode")

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Get base system prompt
                system_prompt = get_agent_system_prompt(AgentName.ROADMAP)

                # Build tool status from last tool result -
                tool_status = self._build_tool_status(self.last_tool_result)

                # Build user message with context
                # Get rich sutra memory from memory manager (includes code snippets and file modifications)
                sutra_memory_rich = (
                    self.action_executor.sutra_memory_manager.get_memory_for_llm()
                )
                task_progress = self.session_manager.get_task_progress_history()

                user_message_parts = []

                # Add user query
                user_message_parts.append(f"User Query: {user_query}")
                # Add sutra memory from memory manager - check iteration for better logic
                if current_iteration == 1:
                    user_message_parts.append(
                        f"\n====\nSUTRA MEMORY STATUS\n\nNo previous memory available. This is first message from user."
                    )
                    logger.debug("Agent: First iteration with empty memory")
                elif sutra_memory_rich and sutra_memory_rich.strip():
                    user_message_parts.append(
                        f"\n====\nSUTRA MEMORY STATUS\n\n{sutra_memory_rich}\n===="
                    )
                    logger.debug(
                        "Agent: Using existing Sutra memory from previous iterations"
                    )
                else:
                    user_message_parts.append(
                        f"\n====\nSUTRA MEMORY STATUS\n\nNo previous memory available.\n===="
                    )
                    logger.debug("Agent: No memory available")

                # Add task progress if available
                if task_progress:
                    user_message_parts.append(
                        f"\nTask Progress History:\n{task_progress}"
                    )

                # Add tool status -  FORMAT
                user_message_parts.append(f"\n====\nTOOL STATUS\n\n{tool_status}\n====")

                user_message = "\n".join(user_message_parts)

                logger.debug(
                    f"Debug: Iteration {current_iteration}: Sending prompt to LLM (attempt {retry_count + 1})"
                )

                logger.debug(
                    f"Debug: Iteration {current_iteration}: System prompt length: {len(system_prompt)}"
                )
                logger.debug(
                    f"Debug: Iteration {current_iteration}: User message length: {len(user_message)}"
                )

                # Use call_llm_with_usage to get token information
                llm_response = self.llm_client.call_llm_with_usage(system_prompt, user_message)
                response = llm_response.content

                # Track token usage
                self.llm_call_count += 1
                if llm_response.token_usage:
                    self.total_input_tokens += llm_response.token_usage.input_tokens
                    self.total_output_tokens += llm_response.token_usage.output_tokens
                    self.total_tokens_used += llm_response.token_usage.total_tokens

                    call_msg = f"Token LLM Call #{self.llm_call_count} - Input: {llm_response.token_usage.input_tokens}, Output: {llm_response.token_usage.output_tokens}, Total: {llm_response.token_usage.total_tokens}"
                    session_msg = f"Stats Session Total - Input: {self.total_input_tokens}, Output: {self.total_output_tokens}, Total: {self.total_tokens_used} (across {self.llm_call_count} calls)"
                    logger.info(call_msg)
                    logger.info(session_msg)
                else:
                    logger.warning(f"Token LLM Call #{self.llm_call_count} - No token usage information available")

                logger.debug(f"RESPONSE: {response}")
                logger.debug(
                    f"Debug: Iteration {current_iteration}: Got XML response from LLM"
                )
                return response

            except XMLParsingFailedException as xml_error:
                retry_count += 1
                # Handle XML parsing error
                error_info = self.error_handler.handle_error(
                    xml_error,
                    {
                        "context": "XML parsing",
                        "iteration": current_iteration,
                        "retry_count": retry_count,
                    },
                )

                logger.warning(
                    f"XML parsing failed on attempt {retry_count}/{max_retries}: {xml_error.message}"
                )
                if retry_count >= max_retries:
                    logger.error(
                        f"XML parsing failed after {max_retries} attempts, giving up"
                    )
                    raise Exception(
                        f"XML parsing failed after {max_retries} attempts: {xml_error.message}"
                    )
                else:
                    logger.info(
                        f"Retrying LLM call due to XML parsing failure (attempt {retry_count + 1}/{max_retries})"
                    )
                    continue

            except Exception as e:
                # Handle general errors
                error_info = self.error_handler.handle_error(
                    e,
                    {
                        "context": "LLM response generation",
                        "iteration": current_iteration,
                        "user_query": user_query,
                    },
                )

                logger.error(f"Failed to get valid response from LLM: {e}")
                if self.error_handler.should_stop_execution(error_info):
                    logger.error("Stopping execution due to critical error")
                    raise
                else:
                    logger.warning("Attempting to continue despite error")
                    raise

        # Fallback return for all code paths
        return {"type": "error", "message": "Failed to get valid response after all retries"}

    def _build_tool_status(self, last_tool_result: Optional[Dict[str, Any]]) -> str:
        """
        Clean tool status builder - handles each tool with specific if-else logic.
        """
        if not last_tool_result:
            return "No previous tool execution"

        tool_name = last_tool_result.get("tool_name", "unknown_tool")

        # Build tool-specific status using if-else statements
        if tool_name == "database":
            return self._build_database_status(last_tool_result)
        elif tool_name == "semantic_search":
            return self._build_semantic_status(last_tool_result)
        elif tool_name == "terminal":
            return self._build_terminal_status(last_tool_result)
        elif tool_name == "write_to_file":
            return self._build_write_to_file_status(last_tool_result)
        elif tool_name == "apply_diff":
            return self._build_apply_diff_status(last_tool_result)
        elif tool_name == "search_keyword":
            return self._build_search_keyword_status(last_tool_result)
        elif tool_name == "list_files":
            return self._build_list_files_status(last_tool_result)
        elif tool_name == "web_search":
            return self._build_web_search_status(last_tool_result)
        elif tool_name == "web_scrap":
            return self._build_web_scrap_status(last_tool_result)
        elif tool_name == "web_scraper":  # Handle both web_scrap and web_scraper
            return self._build_web_scrap_status(last_tool_result)
        elif tool_name == "attempt_completion":
            return self._build_completion_status(last_tool_result)
        else:
            # Fallback for unknown tools
            return self._build_generic_status(last_tool_result, tool_name)

    def _build_database_status(self, result: Dict[str, Any]) -> str:
        """Build status for database tool."""
        status = "Tool: database\n"

        query_name = result.get("query_name")
        if query_name:
            status += f"Query Name: {query_name}\n"

        query = result.get("query")
        if query:
            if isinstance(query, dict):
                query_copy = query.copy()
                query_copy.pop("project_id", None)
                status += f"Query: {query_copy}\n"
            else:
                status += f"Query: '{query}'\n"

        count = result.get("count") or result.get("total_results")
        if count is not None:
            status += f"Results: {count} found\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            # Clean up duplicate guidance messages in the data
            cleaned_data = self._remove_duplicate_guidance_messages(data)
            status += f"Results:\n{cleaned_data}"

        status += "\n\nNOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration."

        return status.rstrip()

    def _remove_duplicate_guidance_messages(self, data: str) -> str:
        """Remove duplicate guidance messages from tool result data."""
        lines = data.split("\n")
        cleaned_lines = []
        guidance_seen = False
        skip_until_empty = False

        for line in lines:
            # Skip duplicate guidance messages
            if (
                line.startswith("Found ")
                and ("nodes" in line or "node" in line)
                and "total lines" in line
            ):
                if guidance_seen:
                    skip_until_empty = True
                    continue
                else:
                    guidance_seen = True
                    cleaned_lines.append(line)
            elif line.startswith("NOTE: There are more results"):
                if not skip_until_empty:
                    cleaned_lines.append(line)
                continue
            elif skip_until_empty and line.strip() == "":
                skip_until_empty = False
                continue
            elif not skip_until_empty:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _build_semantic_status(self, result: Dict[str, Any]) -> str:
        """Build status for semantic search tool."""
        status = "Tool: semantic_search\n"

        query = result.get("query")
        if query and query != "fetch_next_code":
            status += f"Query: '{query}'\n"

        count = result.get("count") or result.get("total_nodes")
        if count is not None:
            batch_info = result.get("batch_info", {})
            if batch_info:
                delivered = batch_info.get("delivered_count", 0)
                remaining = batch_info.get("remaining_count", 0)
                if delivered > 0:
                    start_node = count - remaining - delivered + 1
                    end_node = count - remaining
                    status += f"Found {count} nodes from semantic search. Showing nodes {start_node}-{end_node} of {count}\n"
                else:
                    status += f"Found {count} nodes from semantic search\n"
            else:
                status += f"Found {count} nodes from semantic search\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration."

        return status.rstrip()

    def _build_terminal_status(self, result: Dict[str, Any]) -> str:
        """Build status for terminal tool."""
        status = "Tool: terminal\n"

        cwd = result.get("cwd", ".")
        if cwd:
            status += f"Working Directory: {cwd}\n"

        command = result.get("command")
        if command:
            status += f"Command: {command}\n"

        session_id = result.get("session_id")
        if session_id:
            status += f"Session ID: {session_id}\n"

        mode = result.get("mode")
        if mode:
            status += f"Mode: {mode}\n"

        exit_code = result.get("exit_code")
        if exit_code is not None:  # Check for None instead of falsy
            status += f"Exit Code: {exit_code}\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        output = result.get("output", "")
        if output:
            status += f"Output:\n{output}"

        return status.rstrip()

    def _build_write_to_file_status(self, result: Dict[str, Any]) -> str:
        """Build status for write_to_file tool."""
        status = "Tool: write_to_file\n"

        successful_files = result.get("successful_files")
        if successful_files:
            status += f"Success File: {successful_files}\n"

        failed_files = result.get("failed_files")
        if failed_files:
            status += f"Failed File: {failed_files}\n"

        summary = result.get("summary")
        if summary:
            status += f"Summary: {summary}\n"

        extra_status = result.get("status")
        if extra_status:
            status += f"Status: {extra_status}\n"

        message = result.get("message")
        if message:
            status += f"Message: {message}\n"

        original_request = result.get("original_request")
        if original_request:
            status += f"Failed Content: {original_request}\n"

        return status.rstrip()

    def _build_web_search_status(self, result: Dict[str, Any]) -> str:
        """Build status for web_search tool."""
        status = "Tool: web_search\n"

        query = result.get("query")
        if query:
            status += f"Query: '{query}'\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("results", [])

        if data:
            status += "Results:\n"
            for i, item in enumerate(data, 1):
                status += f"\nResult {i}:\n"
                status += f"  Title: {item.get('title', 'N/A')}\n"
                status += f"  URL: {item.get('url', 'N/A')}\n"
                status += f"  Description: {item.get('description', 'N/A')}\n"

        return status.rstrip()

    def _build_web_scrap_status(self, result: Dict[str, Any]) -> str:
        """Build status for web_scrap tool."""
        status = "Tool: web_scrap\n"

        url = result.get("url")
        if url:
            status += f"URL: {url}\n"
        else:
            status += "URL: No URL provided\n"

        content = result.get("content")
        if content:
            status += f"Content: {content}\n"
        else:
            status += "Content: No content scraped\n"

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        return status.rstrip()

    def _build_apply_diff_status(self, result: Dict[str, Any]) -> str:
        """Build status for apply_diff tool."""
        status = "Tool: apply_diff\n"

        successful_files = result.get("successful_files")
        if successful_files:
            status += f"Success File: {successful_files}\n"

        failed_files = result.get("failed_files")
        if failed_files:
            status += f"Failed File: {failed_files}\n"

        failed_diffs = result.get("failed_diffs")
        if failed_diffs:
            status += f"Failed Diff File: {failed_diffs}\n"

        summary = result.get("summary")
        if summary:
            status += f"Summary: {summary}\n"

        extra = result.get("status")
        if extra:
            status += f"Status: {extra}\n"

        return status.rstrip()

    def _build_search_keyword_status(self, result: Dict[str, Any]) -> str:
        """Build status for search_keyword tool."""
        status = "Tool: search_keyword\n"

        keyword = result.get("keyword")
        if keyword:
            status += f"Keyword: '{keyword}'\n"

        matches_found = result.get("matches_found")
        if matches_found:
            status += (
                f"Matches Status: '{"Found" if matches_found else "Not Found" }'\n"
            )

        error = result.get("error")
        if error:
            status += f"ERROR: {error}\n"

        data = result.get("data", "")
        if data:
            status += f"Results:\n{data}"

        return status.rstrip()

    def _build_list_files_status(self, result: Dict[str, Any]) -> str:
        """Build status for list_files tool."""
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

        return status.rstrip()

    def _build_completion_status(self, result: Dict[str, Any]) -> str:
        """Build status for completion tool."""
        status = "Tool: attempt_completion\n"

        if result.get("type") == "task_complete":
            status += "Status: Task completed successfully\n"
        elif result.get("type") == "completion":
            status += "Status: Completion requested\n"

        completion_result = result.get("result", "")
        if completion_result:
            status += f"Result: {completion_result}"

        return status.rstrip()

    def _build_generic_status(self, result: Dict[str, Any], tool_name: str) -> str:
        """Build generic status for unknown tools."""
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

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        return self.session_manager.get_conversation_summary()

    def clear_session(self) -> None:
        """Clear the current session."""
        self.session_manager.clear_session()

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """List all available sessions."""
        return SessionManager.list_sessions()

    @classmethod
    def get_session(cls, session_id: str) -> Optional["AgentService"]:
        """Get an existing session by ID."""
        try:
            return cls(session_id=session_id)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def get_token_usage_summary(self) -> Dict[str, Any]:
        """Get summary of token usage for the current session.

        Returns:
            Dict[str, Any]: Dictionary containing token usage statistics
        """
        return {
            "llm_call_count": self.llm_call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens_used": self.total_tokens_used,
            "average_tokens_per_call": (
                self.total_tokens_used / self.llm_call_count
                if self.llm_call_count > 0 else 0
            ),
            "input_output_ratio": (
                self.total_input_tokens / self.total_output_tokens
                if self.total_output_tokens > 0 else 0
            )
        }

    def log_token_usage_summary(self) -> None:
        """Log a summary of token usage for the current session."""
        summary = self.get_token_usage_summary()
        logger.info(
            f"Stats Token Usage Summary - "
            f"Calls: {summary['llm_call_count']}, "
            f"Total: {summary['total_tokens_used']} tokens "
            f"({summary['total_input_tokens']} input + {summary['total_output_tokens']} output), "
            f"Avg per call: {summary['average_tokens_per_call']:.1f}"
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
