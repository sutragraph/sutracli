from typing import Any, Dict
from loguru import logger
from baml_client.types import Agent
from models.agent import AgentAction
from tools.guidance_builder import GuidanceRegistry
from tools.tool_action import get_tool_action
from tools.build_tool_status import build_tool_status
from tools.delivery_actions import register_delivery_queue_and_get_first_batch


def execute_tool(agent: Agent, tool_name: str, tool_params: Dict[str, Any]) -> str:
    """
    Execute a tool action for a given agent.

    Args:
        agent: The agent type
        tool_name: The name of the tool to execute
        tool_params: Parameters for the tool action

    Yields:
        Results from the tool action as dictionaries

    Raises:
        ImportError: If the tool module cannot be imported
        AttributeError: If the tool module lacks the required function
    """
    tool_function = get_tool_action(agent, tool_name)
    action = AgentAction(description=tool_name, parameters=tool_params)

    tool_has_guidance = GuidanceRegistry.get_guidance(tool_name)
    delivery_items = []

    for event in tool_function(action):
        event_type = event.get("type")

        if event_type == "tool_use" or event_type == "tool_error":
            if tool_has_guidance:
                event = tool_has_guidance.on_event(event, action)

            delivery_items.append(event)

    if len(delivery_items):
        delivery_result = register_delivery_queue_and_get_first_batch(
            tool_name=tool_name,
            action_type=tool_name,
            delivery_items=delivery_items,
            action_parameters=action.parameters
        )

        if delivery_result:
            return build_tool_status(tool_name, delivery_result, agent)

    return f"No result for {tool_name}"
