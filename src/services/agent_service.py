"""Agent Service with unified tool status handling."""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from loguru import logger

from ..graph.sqlite_client import SQLiteConnection
from ..graph.incremental_indexing import IncrementalIndexing
from ..embeddings.vector_db import VectorDatabase
from .agent.agent_prompt.system import get_base_system_prompt
from .llm_clients.llm_factory import llm_client_factory
from .agent.tool_action_executor.tool_action_executor import ActionExecutor
from .agent.session_management import SessionManager
from .agent.memory_management import SutraMemoryManager
from ..config import config
from ..utils.xml_parsing_exceptions import XMLParsingFailedException


class AgentService:
    """Agent Service with unified tool status handling."""

    def __init__(self, session_id: Optional[str] = None):
        self.llm_client = llm_client_factory()
        self.db_connection = SQLiteConnection()
        self.vector_db = VectorDatabase(config.sqlite.embeddings_db)

        self.session_manager = SessionManager.get_or_create_session(session_id)
        self.memory_manager = SutraMemoryManager(db_connection=self.db_connection)

        self.session_data: List[Dict[str, Any]] = []

        # XML-based action executor with shared sutra memory manager
        self.xml_action_executor = ActionExecutor(
            self.db_connection, self.vector_db, self.memory_manager
        )

        # Track last tool result for context -
        self.last_tool_result = None

        # Initialize incremental indexing
        self.incremental_indexer = IncrementalIndexing(self.db_connection)

        # Determine current project name from working directory
        self.current_project_name = self._determine_project_name()

    def _perform_incremental_indexing(self) -> Iterator[Dict[str, Any]]:
        """Perform incremental reindexing of the database using the current project name."""
        logger.debug(
            f"🔄 Running database reindex for project {self.current_project_name}"
        )
        stats = self.incremental_indexer.reindex_database(self.current_project_name)
        yield {
            "type": "incremental_indexing",
            "stats": stats,
            "timestamp": time.time(),
        }

    def _determine_project_name(self) -> str:
        """Determine the correct project name from the database."""
        try:
            projects = self.db_connection.list_all_projects()
            if projects:
                project_name = projects[0]["name"]
                logger.debug(f"Using project from database: {project_name}")
                return project_name

            cwd_name = Path.cwd().name
            logger.warning(
                f"No projects found in database, falling back to directory name: {cwd_name}"
            )
            return cwd_name

        except Exception as e:
            logger.warning(f"Error determining project name: {e}")
            return Path.cwd().name

    def solve_problem(
        self, problem_query: str, project_id: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """Main entry point for the agent to solve a problem autonomously."""
        # Perform incremental indexing before processing the query
        yield from self._perform_incremental_indexing()
        query_id = self.session_manager.start_new_query(problem_query)
        self.session_manager.set_problem_context(problem_query)

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
        max_iterations = 50  # Safety limit

        while current_iteration < max_iterations:
            current_iteration += 1

            # User confirmation every 15 iterations
            if current_iteration % 15 == 0:
                print(
                    f"\n⚠️  This process has been running for {current_iteration} iterations."
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

                # Process XML response using XML action executor
                task_complete = False
                for event in self.xml_action_executor.process_xml_response(
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

                    # Handle Sutra Memory updates
                    elif event.get("type") == "sutra_memory_update":
                        memory_result = event.get("result", {})
                        if memory_result.get("success"):
                            # Get the rich formatted memory from memory manager (includes code snippets)
                            memory_summary = (
                                self.xml_action_executor.sutra_memory_manager.get_memory_for_llm()
                            )
                            # Update session manager with the rich memory content
                            self.session_manager.update_sutra_memory(memory_summary)
                            logger.debug(
                                f"Updated Sutra Memory in session: {len(memory_summary)} characters"
                            )
                            logger.debug(
                                f"Memory includes {len(self.xml_action_executor.sutra_memory_manager.code_snippets)} code snippets"
                            )
                        else:
                            logger.warning(
                                f"Sutra Memory update failed: {memory_result.get('errors', [])}"
                            )

                # Break if task was completed
                if task_complete:
                    logger.debug(
                        f"🎯 Task completed in iteration {current_iteration}, stopping loop"
                    )
                    break

            except Exception as e:
                logger.error(
                    f"❌ Error in solving loop iteration {current_iteration}: {e}"
                )
                yield {
                    "type": "error",
                    "error": str(e),
                    "iteration": current_iteration,
                    "session_id": self.session_manager.session_id,
                }
                break

        if current_iteration >= max_iterations:
            yield {
                "type": "warning",
                "message": f"Maximum iterations ({max_iterations}) reached. Terminating session.",
            }

    def _get_xml_response(
        self, user_query: str, current_iteration: int
    ) -> Dict[str, Any]:
        """Get XML response from LLM using the new prompt system with retry on XML parsing failures."""
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Get base system prompt
                system_prompt = get_base_system_prompt()

                # Build tool status from last tool result -
                tool_status = self._build_tool_status(self.last_tool_result)

                # Build user message with context
                # Get rich sutra memory from memory manager (includes code snippets and file modifications)
                sutra_memory_rich = (
                    self.xml_action_executor.sutra_memory_manager.get_memory_for_llm()
                )
                task_progress = self.session_manager.get_task_progress_history()

                user_message_parts = []

                # Add user query
                user_message_parts.append(f"User Query: {user_query}")

                # Add sutra memory from memory manager
                if sutra_memory_rich and sutra_memory_rich.strip():
                    user_message_parts.append(
                        f"\n====\nSUTRA MEMORY STATUS\n\n{sutra_memory_rich}\n===="
                    )
                else:
                    user_message_parts.append(
                        f"\n====\nSUTRA MEMORY STATUS\n\nNo previous memory available. This is first message from user.\n===="
                    )

                # Add task progress if available
                if task_progress:
                    user_message_parts.append(
                        f"\nTask Progress History:\n{task_progress}"
                    )

                # Add tool status -  FORMAT
                user_message_parts.append(f"\n====\nTOOL STATUS\n\n{tool_status}\n====")

                user_message = "\n".join(user_message_parts)

                logger.debug(
                    f"🔍 Iteration {current_iteration}: Sending prompt to LLM (attempt {retry_count + 1})"
                )

                logger.debug(
                    f"🔍 Iteration {current_iteration}: System prompt length: {len(system_prompt)}"
                )
                logger.debug(
                    f"🔍 Iteration {current_iteration}: User message length: {len(user_message)}"
                )

                response = self.llm_client.call_llm(system_prompt, user_message)
                logger.debug(f"RESPONSE: {response}")
                logger.debug(
                    f"🔍 Iteration {current_iteration}: Got XML response from LLM"
                )
                return response

            except XMLParsingFailedException as xml_error:
                retry_count += 1
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
                logger.error(f"Failed to get valid response from LLM: {e}")
                raise

    def _build_tool_status(self, last_tool_result: Optional[Dict[str, Any]]) -> str:
        """
        Clean tool status builder - handles each tool with specific if-else logic.
        """
        if not last_tool_result:
            return "No previous tool execution"

        logger.debug(f"Building tool status for last tool result: {last_tool_result}")
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
        elif tool_name == "insert_content":
            return self._build_insert_content_status(last_tool_result)
        elif tool_name == "apply_diff":
            return self._build_apply_diff_status(last_tool_result)
        elif tool_name == "search_keyword":
            return self._build_search_keyword_status(last_tool_result)
        elif tool_name == "list_files":
            return self._build_list_files_status(last_tool_result)
        else:
            # Fallback for unknown tools
            return self._build_generic_status(last_tool_result, tool_name)

    def _build_database_status(self, result: Dict[str, Any]) -> str:
        """Build status for database tool."""
        status = "Tool: database\n"

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
            status += f"Results:\n{data}"

        status += "\n\nNOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration."

        return status.rstrip()

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
                    status += f"Found {count} nodes from semantic search. Showing nodes {delivered} of {count}\n"
                    if remaining > 0:
                        status += f"Remaining nodes: {remaining}\n NOTE: Use <fetch_next_code>true</fetch_next_code> to get next codes as there are more results available for your current query. Use same query with fetch_next_code to get next code."
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

        return_code = result.get("return_code")
        if return_code:
            status += f"Return Code: {return_code}\n"

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

        file_path = result.get("applied_changes_to_files")
        if file_path:
            status += f"Suceess File: {file_path}\n"

        message = result.get("message")
        if message:
            status += f"Status: {message}\n"

        original_request = result.get("original_request")
        if original_request:
            status += f"Failed Content: {original_request}\n"

        return status.rstrip()

    def _build_insert_content_status(self, result: Dict[str, Any]) -> str:
        """Build status for insert_content tool."""
        status = "Tool: insert_content\n"

        file_path = result.get("applied_changes_to_files")
        if file_path:
            status += f"Success File: {file_path}\n"

        message = result.get("message")
        if message:
            status += f"Status: {message}\n"

        original_request = result.get("original_request")
        if original_request:
            status += f"Failed Content: {original_request}\n"

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

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self, "db_connection"):
            self.db_connection.__exit__(exc_type, exc_val, exc_tb)
        if hasattr(self, "vector_db"):
            self.vector_db.__exit__(exc_type, exc_val, exc_tb)
