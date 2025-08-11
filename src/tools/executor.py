"""
XML-based Action Executor for processing LLM responses in XML format.
Handles thinking, tool execution, and sutra memory updates.
"""

import time
from typing import Iterator, Dict, Any, List, Optional
from loguru import logger
from pathlib import Path


from graph.sqlite_client import SQLiteConnection
from models.agent import AgentAction
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from graph.project_indexer import ProjectIndexer
from tools import get_tool_action, ToolName, TOOL_NAME_MAPPING
from tools.guidance_builder import get_tool_guidance
from tools.delivery_actions import (
    handle_fetch_next_request,
    register_delivery_queue_and_get_first_batch,
)


class ActionExecutor:
    """
    New XML-based action executor that processes LLM responses in xmltodict format.
    Each response contains: thinking, 1 tool, sutra memory updates
    """

    def __init__(
        self,
        sutra_memory_manager: Optional[SutraMemoryManager] = None,
        context: str = "agent",
    ):
        self.db_connection = SQLiteConnection()

        self.sutra_memory_manager = sutra_memory_manager or SutraMemoryManager()
        self.project_id = None  # Will be set when needed
        self.context = context  # Store context for database operations

        # Use shared project indexer if provided, otherwise create new one
        self.project_indexer = ProjectIndexer(self.sutra_memory_manager)

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
            logger.debug(
                f"Tool name: {tool_data.get('_tool_name') if tool_data else 'None'}"
            )
            logger.debug(
                f"Sutra memory update found: {sutra_memory_update is not None}"
            )

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
                memory_result = (
                    self.sutra_memory_manager.extract_and_process_sutra_memory(
                        xml_response
                    )
                )
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
                action = self._create_agent_action(
                    "attempt_completion", tool_data, user_query
                )
                tool_action = get_tool_action(ToolName.COMPLETION)
                yield from tool_action(action)
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
                tool_name = tool_data.get("_tool_name", "unknown")
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
                            "type": "tool_use",
                            "used_tool": "none",
                            "status": "failed",
                            "message": "You didn't provide a tool call. You must use at least one tool in every response. Please use a tool like semantic_search, database, execute_command, apply_diff, write_to_file, list_files, search_keyword, or attempt_completion.",
                            "summary": "No tool was used - violates one-tool-per-iteration rule",
                            "timestamp": time.time(),
                        }

        except Exception as e:
            logger.error(f"Error processing XML response: {e}")
            yield {
                "type": "error",
                "error": f"Failed to process XML response: {str(e)}",
                "timestamp": time.time(),
            }

    def _execute_tool(
        self, tool_name: str, tool_data: Dict[str, Any], user_query: str
    ) -> Iterator[Dict[str, Any]]:
        """Execute the specified tool with given parameters."""
        try:
            # Create AgentAction from tool data
            action = self._create_agent_action(tool_name, tool_data, user_query)
            action.parameters["project_id"] = self.project_id

            # Use tool name mapping from tools module
            if tool_name in TOOL_NAME_MAPPING:
                tool_enum = TOOL_NAME_MAPPING[tool_name]

                if action.parameters.get("fetch_next_code", False):
                    fetch_response = handle_fetch_next_request(action, tool_enum)
                    if fetch_response:
                        yield fetch_response
                        return

                guidance = get_tool_guidance(tool_enum)

                if guidance:
                    start_result = guidance.on_start(action)
                    if start_result:
                        yield start_result

                tool_action = get_tool_action(tool_enum)

                events = []
                delivery_items = []

                for event in tool_action(action):
                    if guidance:
                        event = guidance.on_event(event, action)
                    if event:  # Only yield if guidance didn't filter it out
                        events.append(event)
                        # Always collect potential delivery items - let delivery system decide
                        delivery_items.append(event)
                        yield event

                # Always try to register delivery queue - let delivery system decide if it should handle it

                register_delivery_queue_and_get_first_batch(
                    tool_name, action.parameters, delivery_items, tool_enum
                )
                logger.debug(
                    f"📦 Attempted to register delivery queue for {tool_name} with {len(delivery_items)} items"
                )

            else:
                yield {
                    "type": "tool_error",
                    "error": f"Unknown tool: {tool_name}",
                    "tool_name": tool_name,
                }

        except Exception as e:
            logger.error(f"❌ Tool execution error for {tool_name}: {e}")
            yield {
                "type": "tool_error",
                "tool_name": tool_name,
                "error": str(e),
                "timestamp": time.time(),
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
            description=f"Execute {tool_name}",
            parameters=parameters if isinstance(parameters, dict) else {},
        )

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

    def _extract_completion(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract completion data from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for completion tag
                if "completion" in xml_block:
                    return xml_block["completion"]
        return None

    def _extract_tool(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract tool data from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                for tool_tag in TOOL_NAME_MAPPING.keys():
                    if tool_tag in xml_block:
                        tool_data = xml_block[tool_tag]
                        if isinstance(tool_data, dict):
                            tool_data["_tool_name"] = tool_tag
                            return tool_data
                        elif isinstance(tool_data, str):
                            return {"_tool_name": tool_tag, "content": tool_data}
        return None

    def _extract_sutra_memory(
        self, xml_response: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract sutra memory update from XML response."""
        for xml_block in xml_response:
            if isinstance(xml_block, dict):
                # Check for sutra_memory tag
                if "sutra_memory" in xml_block:
                    return xml_block["sutra_memory"]
        return None
