"""
JSON-based Action Executor for processing LLM responses in JSON format.
Handles thinking, tool execution, and sutra memory updates.
"""

import time
from typing import Iterator, Dict, Any, Optional
from loguru import logger


from graph.sqlite_client import SQLiteConnection
from models.agent import AgentAction
from services.agent.memory_management.sutra_memory_manager import SutraMemoryManager
from baml_client.types import (
    SutraMemoryParams,
    TaskOperation,
    TaskOperationAction,
)
from graph.project_indexer import ProjectIndexer
from tools import get_tool_action, ToolName, TOOL_NAME_MAPPING
from tools.guidance_builder import get_tool_guidance
from tools.delivery_actions import (
    handle_fetch_next_request,
    register_delivery_queue_and_get_first_batch,
)


class ActionExecutor:
    """
    JSON-based action executor that processes LLM responses in JSON format.
    Each response contains: thinking, 1 tool, sutra memory updates
    """

    def __init__(
        self,
        sutra_memory_manager: Optional[SutraMemoryManager] = None,
        context: str = "agent",
    ):
        self.db_connection = SQLiteConnection()

        self.sutra_memory_manager = sutra_memory_manager or SutraMemoryManager()
        self.context = context  # Store context for database operations

        # Use shared project indexer if provided, otherwise create new one
        self.project_indexer = ProjectIndexer(self.sutra_memory_manager)

    def process_json_response(
        self, json_response: Dict[str, Any], user_query: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Process JSON response from BAML containing thinking, tool, and sutra memory.

        Args:
            json_response: JSON response from BAML (already parsed)
            user_query: Original user query

        Yields:
            Processing updates including thinking, tool execution, and memory updates
        """
        try:
            # Direct access to JSON components (no extraction needed)
            thinking_content = json_response.get("thinking")
            completion_data = json_response.get("attempt_completion")
            sutra_memory_update = json_response.get("sutra_memory")

            # Debug logging for tool detection (matching XML processor)
            logger.debug(f"JSON Response keys: {list(json_response.keys())}")
            logger.debug(f"Thinking content found: {thinking_content is not None}")
            logger.debug(f"Completion data found: {completion_data is not None}")
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
                # Process sutra memory directly from JSON
                try:
                    # Create SutraMemoryParams object from JSON with required fields
                    add_history = sutra_memory_update.get("add_history", "")
                    sutra_params = SutraMemoryParams(add_history=add_history)

                    # Handle tasks (initialize empty list if no tasks)
                    sutra_params.tasks = []
                    if "tasks" in sutra_memory_update and sutra_memory_update["tasks"]:
                        for task_data in sutra_memory_update["tasks"]:
                            # Direct access to class object attributes
                            action_str = getattr(task_data, "action", "").lower()
                            action_enum = None
                            if action_str == "add":
                                action_enum = TaskOperationAction.Add
                            elif action_str == "move":
                                action_enum = TaskOperationAction.Move
                            elif action_str == "remove":
                                action_enum = TaskOperationAction.Remove

                            # Get status string - BAML expects uppercase enum values
                            to_status_str = getattr(task_data, "to_status", "").upper()

                            # Create TaskOperation with required fields
                            task_id = getattr(task_data, "id", "")
                            task_desc = getattr(task_data, "description", "")

                            logger.debug(
                                f"Processing task operation: action={action_str}, id={task_id}, desc='{task_desc}', to_status={to_status_str}"
                            )

                            # For Add operations, description is required; for Move/Remove, it's optional
                            if (
                                action_enum
                                and task_id
                                and (
                                    task_desc or action_enum != TaskOperationAction.Add
                                )
                            ):
                                task_op = TaskOperation(
                                    action=action_enum,
                                    id=task_id,
                                    description=task_desc,
                                    to_status=to_status_str,  # Pass string directly
                                )
                                sutra_params.tasks.append(task_op)
                                logger.debug(
                                    f"Added task operation to sutra_params: {task_op}"
                                )
                            else:
                                logger.debug(
                                    f"Skipped task operation - condition failed: action_enum={action_enum}, task_id='{task_id}', task_desc='{task_desc}'"
                                )

                    memory_result = (
                        self.sutra_memory_manager.process_sutra_memory_params(
                            sutra_params
                        )
                    )
                except Exception as e:
                    logger.error(f"Error processing sutra memory: {e}")
                    memory_result = {
                        "success": False,
                        "errors": [f"Failed to process sutra memory: {str(e)}"],
                        "warnings": [],
                        "changes_applied": {
                            "tasks": [],
                            "code": [],
                            "files": [],
                            "history": [],
                        },
                    }
                yield {
                    "type": "sutra_memory_update",
                    "result": memory_result,
                    "timestamp": time.time(),
                }

            # Handle attempt_completion specially - it's both a tool and completion
            if completion_data:
                tool_data = {
                    "_tool_name": "attempt_completion",
                    "result": completion_data,
                }
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

            # Check for tool_call structure in JSON response
            tool_found = False
            if "tool_call" in json_response:
                tool_call = json_response["tool_call"]
                logger.debug(f"Found tool_call: {tool_call}")
                if isinstance(tool_call, dict) and "tool_name" in tool_call:
                    tool_name = tool_call["tool_name"]
                    raw_parameters = tool_call.get("parameters", {})

                    # Convert BAML parameter objects to dict
                    if hasattr(raw_parameters, "__dict__"):
                        parameters = raw_parameters.__dict__
                    elif hasattr(raw_parameters, "model_dump"):
                        parameters = raw_parameters.model_dump()
                    elif isinstance(raw_parameters, dict):
                        parameters = raw_parameters
                    else:
                        # Convert to dict by trying to access common attributes
                        parameters = {}
                        for attr in [
                            "path",
                            "recursive",
                            "project_name",
                            "query",
                            "content",
                        ]:
                            if hasattr(raw_parameters, attr):
                                parameters[attr] = getattr(raw_parameters, attr)

                    logger.debug(f"Converted parameters: {parameters}")

                    # Fix relative path issue: if path is "." and we have project path in user_query, use it
                    file_tools = ["list_files", "search_keyword", "write_to_file"]
                    if (
                        tool_name in file_tools
                        and parameters.get("path") == "."
                        and "Analyze project connections for:" in user_query
                    ):
                        # Extract project path from user query
                        project_path = user_query.split(
                            "Analyze project connections for:", 1
                        )[1].strip()
                        parameters = parameters.copy()
                        parameters["path"] = project_path
                        logger.debug(
                            f"Substituted relative path '.' with project path: {project_path} for tool: {tool_name}"
                        )

                    logger.debug(
                        f"Executing tool: {tool_name} with parameters: {parameters}"
                    )

                    # Create tool data structure
                    tool_data = (
                        parameters.copy() if isinstance(parameters, dict) else {}
                    )
                    tool_data["_tool_name"] = tool_name

                    yield from self._execute_tool(tool_name, tool_data, user_query)
                    tool_found = True

            # Fallback: Check for other tools as direct keys in the JSON response
            if not tool_found:
                for tool_tag in TOOL_NAME_MAPPING.keys():
                    if tool_tag in json_response and tool_tag != "attempt_completion":
                        tool_data = json_response[tool_tag]
                        if isinstance(tool_data, dict):
                            tool_data["_tool_name"] = tool_tag
                        else:
                            tool_data = {"_tool_name": tool_tag, "content": tool_data}

                        yield from self._execute_tool(tool_tag, tool_data, user_query)
                        tool_found = True
                        break

            # If no tool is present but we have thinking or sutra_memory,
            # we still need to ensure one tool is executed per iteration
            if not tool_found and not completion_data:
                if thinking_content:
                    yield {
                        "type": "tool_use",
                        "used_tool": "none",
                        "status": "failed",
                        "message": "You didn't provide a tool call. You must use at least one tool in every response. Please use a tool like semantic_search, database, execute_command, apply_diff, write_to_file, list_files, search_keyword, or attempt_completion.",
                        "summary": "No tool was used - violates one-tool-per-iteration rule",
                        "timestamp": time.time(),
                    }

        except Exception as e:
            logger.error(f"Error processing JSON response: {e}")
            yield {
                "type": "error",
                "error": f"Failed to process JSON response: {str(e)}",
                "timestamp": time.time(),
            }

    def _execute_tool(
        self, tool_name: str, tool_data: Dict[str, Any], user_query: str
    ) -> Iterator[Dict[str, Any]]:
        """Execute the specified tool with given parameters."""
        try:
            logger.debug(
                f"_execute_tool called with tool_name='{tool_name}', tool_data={tool_data}"
            )
            # Create AgentAction from tool data
            action = self._create_agent_action(tool_name, tool_data, user_query)
            logger.debug(f"Created AgentAction: {action}")

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
                        # Only collect items for delivery if they don't have internal_delivery_handled flag
                        # and are actual tool results (not info messages)
                        if not event.get("internal_delivery_handled") and event.get("type") == "tool_use":
                            delivery_items.append(event)
                        yield event

                has_internal_delivery = any(
                    item.get("internal_delivery_handled") is True for item in events
                )

                # Skip delivery queue registration for tools that don't need it
                tools_without_delivery = [ToolName.APPLY_DIFF,
                                        ToolName.COMPLETION, ToolName.TERMINAL_COMMANDS, ToolName.WEB_SCRAP,
                                        ToolName.WEB_SEARCH, ToolName.WRITE_TO_FILE]

                if has_internal_delivery:
                    logger.debug(f"📦 Skipping delivery registration for {tool_name} - already handled internally")
                elif tool_enum in tools_without_delivery:
                    logger.debug(f"📦 Skipping delivery registration for {tool_name} - tool doesn't use delivery queues")
                elif delivery_items:
                    # Try to register delivery queue for tools that don't handle delivery internally
                    delivery_result = register_delivery_queue_and_get_first_batch(
                        tool_name, action.parameters, delivery_items, tool_enum
                    )
                    if delivery_result:
                        yield delivery_result
                    logger.debug(f"📦 Registered delivery queue for {tool_name} with {len(delivery_items)} items")
                else:
                    logger.debug(f"📦 No delivery items to register for {tool_name}")

            else:
                logger.error(
                    f"Tool '{tool_name}' not found in TOOL_NAME_MAPPING. Available tools: {list(TOOL_NAME_MAPPING.keys())}"
                )
                yield {
                    "type": "tool_error",
                    "error": f"Unknown tool: {tool_name}",
                    "tool_name": tool_name,
                }

        except Exception as e:
            logger.error(f"❌ Tool execution error for {tool_name}: {e}", exc_info=True)
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
