"""
XML-based Action Executor for processing LLM responses in XML format.
Handles thinking, tool execution, and sutra memory updates.
"""

import time
from typing import Iterator, Dict, Any, List, Optional
from loguru import logger
from pathlib import Path

from src.embeddings.vector_db import VectorDatabase
from src.graph.sqlite_client import SQLiteConnection
from src.services.agent.agentic_core import AgentAction
from src.services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from src.config import config
from src.graph.incremental_indexing import IncrementalIndexing

from .tools.semantic_search_action import execute_semantic_search_action
from .tools.database_executor import execute_database_action
from .tools.terminal_action import execute_terminal_action
from .tools.apply_diff_action import execute_apply_diff_action
from .tools.write_to_file_action import execute_write_to_file_action
from .tools.insert_content_action import execute_insert_content_action
from .tools.list_files_action import execute_list_files_action
from .tools.search_keyword_action import execute_search_keyword_action
from .tools.completion_action import execute_completion_action


class ActionExecutor:
    """
    New XML-based action executor that processes LLM responses in xmltodict format.
    Each response contains: thinking, 1 tool, sutra memory updates
    """

    def __init__(
        self,
        db_connection: Optional[SQLiteConnection] = None,
        vector_db: Optional[VectorDatabase] = None,
        sutra_memory_manager: Optional[SutraMemoryManager] = None,
    ):
        self.db_connection = db_connection or SQLiteConnection()
        self.vector_db = vector_db or VectorDatabase(config.sqlite.embeddings_db)
        self.sutra_memory_manager = sutra_memory_manager or SutraMemoryManager(
            db_connection=self.db_connection
        )

    def process_xml_response(
        self, xml_response: List[Dict[str, Any]], user_query: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Process XML response from LLM containing thinking, tool, and sutra memory.

        Args:
            xml_response: Parsed XML response from LLM (xmltodict format)
            user_query: Original user query

        Yields:
            Processing updates including thinking, tool execution, and memory updates
        """
        try:
            # Extract components from XML response
            thinking_content = self._extract_thinking(xml_response)
            completion_data = self._extract_completion(xml_response)
            tool_data = self._extract_tool(xml_response)
            sutra_memory_update = self._extract_sutra_memory(xml_response)
            
            # Debug logging for tool detection
            logger.debug(f"XML Response blocks: {len(xml_response)}")
            logger.debug(f"Thinking content found: {thinking_content is not None}")
            logger.debug(f"Completion data found: {completion_data is not None}")
            logger.debug(f"Tool data found: {tool_data is not None}")
            logger.debug(f"Tool name: {tool_data.get('_tool_name') if tool_data else 'None'}")
            logger.debug(f"Sutra memory update found: {sutra_memory_update is not None}")

            # Yield thinking information
            if thinking_content:
                yield {
                    "type": "thinking",
                    "content": thinking_content,
                    "timestamp": time.time(),
                }

            # Update sutra memory if present
            if sutra_memory_update:
                # Process sutra memory using the manager
                memory_result = self.sutra_memory_manager.extract_and_process_sutra_memory(xml_response)
                yield {
                    "type": "sutra_memory_update",
                    "result": memory_result,
                    "timestamp": time.time(),
                }

            # Handle attempt_completion specially - it's both a tool and completion
            if tool_data and tool_data.get("_tool_name") == "attempt_completion":
                yield {
                    "type": "tool",
                    "tool_result": tool_data,
                    "timestamp": time.time(),
                }
                # Execute the completion tool
                yield from self._execute_completion(self._create_agent_action("attempt_completion", tool_data, user_query))
                # Then mark as task complete
                yield {
                    "type": "task_complete",
                    "completion": tool_data,
                    "timestamp": time.time(),
                }
                return

            # Handle other completion types if present
            elif completion_data:
                yield {
                    "type": "task_complete",
                    "completion": completion_data,
                    "timestamp": time.time(),
                }
                return

            # Execute other tools if present
            elif tool_data:
                yield {
                    "type": "tool",
                    "tool_result": tool_data,
                    "timestamp": time.time(),
                }
                tool_name = tool_data.get("name") or self._get_tool_name_from_xml(
                    tool_data
                )
                yield from self._execute_tool(tool_name, tool_data, user_query)
            else:
                # If no tool is present but we have thinking or sutra_memory,
                # we still need to ensure one tool is executed per iteration
                if thinking_content and not completion_data:
                    # Check if there's any attempt_completion in the raw XML that wasn't detected
                    has_attempt_completion = any(
                        isinstance(xml_block, dict)
                        and "attempt_completion" in xml_block
                        for xml_block in xml_response
                    )

                    if not has_attempt_completion:
                        yield {
                            "type": "tool_status",
                            "used_tool": "none",
                            "status": "failed",
                            "message": "You didn't provide a tool call. You must use at least one tool in every response. Please use a tool like semantic_search, database, execute_command, apply_diff, write_to_file, insert_content, list_files, search_keyword, or attempt_completion.",
                            "summary": "No tool was used - violates one-tool-per-iteration rule",
                            "timestamp": time.time(),
                        }
                    else:
                        # Found attempt_completion but it wasn't extracted properly, try to handle it
                        for xml_block in xml_response:
                            if (
                                isinstance(xml_block, dict)
                                and "attempt_completion" in xml_block
                            ):
                                completion_tool_data = xml_block["attempt_completion"]
                                if isinstance(completion_tool_data, dict):
                                    completion_tool_data["_tool_name"] = (
                                        "attempt_completion"
                                    )
                                    yield {
                                        "type": "tool",
                                        "tool_result": completion_tool_data,
                                        "timestamp": time.time(),
                                    }
                                    yield from self._execute_completion(
                                        self._create_agent_action(
                                            "attempt_completion",
                                            completion_tool_data,
                                            user_query,
                                        )
                                    )
                                    yield {
                                        "type": "task_complete",
                                        "completion": completion_tool_data,
                                        "timestamp": time.time(),
                                    }
                                    return

        except Exception as e:
            logger.error(f"Error processing XML response: {e}")
            yield {
                "type": "error",
                "error": f"Failed to process XML response: {str(e)}",
                "timestamp": time.time(),
            }

    def _extract_thinking(self, xml_response: List[Dict[str, Any]]) -> Optional[str]:
        """Extract thinking content from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for thinking tag
                if "thinking" in xml_block:
                    thinking_data = xml_block["thinking"]
                    if isinstance(thinking_data, str):
                        return thinking_data
                    elif isinstance(thinking_data, dict) and "#text" in thinking_data:
                        return thinking_data["#text"]
        return None

    def _extract_tool(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract tool data from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for various tool tags
                tool_tags = [
                    "semantic_search",
                    "database",
                    "execute_command",
                    "apply_diff",
                    "write_to_file",
                    "insert_content",
                    "list_files",
                    "search_keyword",
                    "attempt_completion",
                ]

                for tag in tool_tags:
                    if tag in xml_block:
                        tool_data = xml_block[tag]
                        # Handle both dict and string formats for tool data
                        if isinstance(tool_data, dict):
                            tool_data["_tool_name"] = tag
                            return tool_data
                        elif isinstance(tool_data, str) and tag == "attempt_completion":
                            # Handle string format for attempt_completion
                            return {"_tool_name": tag, "result": tool_data}
        return None

    def _extract_sutra_memory(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Extract sutra memory update from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for sutra_memory tag
                if "sutra_memory" in xml_block:
                    memory_data = xml_block["sutra_memory"]
                    if isinstance(memory_data, str):
                        return memory_data
                    elif isinstance(memory_data, dict):
                        # Handle nested structure like {'add_history': '...'}
                        if "#text" in memory_data:
                            return memory_data["#text"]
                        elif "add_history" in memory_data:
                            return memory_data["add_history"]
                        elif "content" in memory_data:
                            return memory_data["content"]
                        # If it's a dict but no recognized keys, try to get first value
                        elif len(memory_data) == 1:
                            return list(memory_data.values())[0]
        return None

    def _get_tool_name_from_xml(self, tool_data: Dict[str, Any]) -> str:
        """Get tool name from XML tool data."""
        return tool_data.get("_tool_name", "unknown")

    def _extract_completion(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract completion data from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for both completion and attempt_completion tags
                if "completion" in xml_block:
                    comp = xml_block["completion"]
                    if isinstance(comp, dict):
                        return comp
                elif "attempt_completion" in xml_block:
                    comp = xml_block["attempt_completion"]
                    if isinstance(comp, dict):
                        return comp
        return None

    def _execute_tool(
        self, tool_name: str, tool_data: Dict[str, Any], user_query: str
    ) -> Iterator[Dict[str, Any]]:
        """Execute the specified tool with given parameters."""
        try:
            # Create AgentAction from tool data
            action = self._create_agent_action(tool_name, tool_data, user_query)

            # Route to appropriate executor
            if tool_name == "semantic_search":
                yield from self._execute_semantic_search(action)
            elif tool_name == "database":
                yield from self._execute_database(action)
            elif tool_name == "execute_command":
                yield from self._execute_terminal(action)
            elif tool_name == "apply_diff":
                yield from self._execute_apply_diff(action)
            elif tool_name == "write_to_file":
                yield from self._execute_write_to_file(action)
            elif tool_name == "insert_content":
                yield from self._execute_insert_content(action)
            elif tool_name == "list_files":
                yield from self._execute_list_files(action)
            elif tool_name == "search_keyword":
                yield from self._execute_search_keyword(action)
            elif tool_name == "search_and_replace":
                yield from self._execute_search_and_replace(action)
            elif tool_name == "attempt_completion":
                yield from self._execute_completion(action)
            else:
                yield {
                    "type": "tool_error",
                    "error": f"Unknown tool: {tool_name}",
                    "tool_name": tool_name,
                }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            yield {
                "type": "tool_error",
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name,
            }

    def _create_agent_action(
        self, tool_name: str, tool_data: Dict[str, Any], user_query: str
    ) -> AgentAction:
        """Create AgentAction from tool data."""
        # Remove internal tool name marker
        clean_data = {k: v for k, v in tool_data.items() if not k.startswith("_")}

        # Special handling for attempt_completion
        if tool_name == "attempt_completion":
            # If clean_data is empty or only has result, use the result directly
            if not clean_data or (len(clean_data) == 1 and "result" in clean_data):
                parameters = clean_data.get("result", "Task completed")
            else:
                parameters = clean_data
        else:
            parameters = clean_data

        return AgentAction(
            tool_type=tool_name,
            description=f"Execute {tool_name}",
            query=clean_data.get("query", user_query) if isinstance(clean_data, dict) else user_query,
            parameters=parameters,
            priority=1,
        )

    def _execute_semantic_search(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute semantic search tool using existing comprehensive executor."""
        yield from execute_semantic_search_action(
            action, self.vector_db, self.db_connection
        )

    def _execute_database(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute database tool using existing comprehensive executor."""
        yield from execute_database_action(action, self.db_connection)

    def _execute_terminal(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute terminal command tool using existing executor."""
        yield from execute_terminal_action(action)

    def _execute_apply_diff(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute apply diff tool using existing comprehensive executor."""
        yield from execute_apply_diff_action(action)
        # Trigger incremental indexing after diff apply
        indexer = IncrementalIndexing(self.db_connection)
        stats = indexer.reindex_database(Path.cwd().name)
        yield {"type": "incremental_indexing", "stats": stats, "timestamp": time.time()}

    def _execute_write_to_file(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute write to file tool using separate executor."""
        yield from execute_write_to_file_action(action)
        # Trigger incremental indexing after write
        indexer = IncrementalIndexing(self.db_connection)
        stats = indexer.reindex_database(Path.cwd().name)
        yield {"type": "incremental_indexing", "stats": stats, "timestamp": time.time()}

    def _execute_insert_content(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute insert content tool using separate executor."""
        yield from execute_insert_content_action(action)
        # Trigger incremental indexing after content insert
        indexer = IncrementalIndexing(self.db_connection)
        stats = indexer.reindex_database(Path.cwd().name)
        yield {"type": "incremental_indexing", "stats": stats, "timestamp": time.time()}

    def _execute_list_files(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute list files tool using separate executor."""
        yield from execute_list_files_action(action)

    def _execute_search_keyword(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute search keyword tool using separate executor."""
        yield from execute_search_keyword_action(action)

    def _execute_completion(self, action: AgentAction) -> Iterator[Dict[str, Any]]:
        """Execute completion tool using separate executor."""
        yield from execute_completion_action(action)
