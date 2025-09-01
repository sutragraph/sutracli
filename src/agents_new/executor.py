from typing import Dict, Optional, NamedTuple, Union, cast
from loguru import logger

from baml_client.types import (
    Agent,
    ProjectContext,
    RoadmapAgentParams,
    RoadmapPromptParams,
    BasePromptParams,
    RoadmapResponse,


)
from services.baml_service import BAMLService
from .utils import get_project_context_for_agent, get_system_info


AgentContentType = Union[RoadmapResponse]


class AgentResponse(NamedTuple):
    """Structured response from agent execution including agent type.
    """

    agent_type: Agent
    content: AgentContentType


def execute_agent(agent_name: Agent, context: str) -> AgentResponse:
    """
    Execute an agent using BAMLService.

    Args:
        agent_name: The type of agent to execute
        context: The context/query for the agent

    Returns:
        The response from the executed agent with properly typed content

    Raises:
        ValueError: If agent_name is not supported
        Exception: If agent execution fails
    """
    # Map agent types to their BAML function names
    agent_function_mapping = {Agent.ROADMAP: "RoadmapAgent"}

    try:
        # Validate agent name
        if agent_name not in agent_function_mapping:
            available_agents = list(agent_function_mapping.keys())
            raise ValueError(
                f"Unsupported agent: {agent_name}. Available: {
                    [
                        a.value for a in available_agents]}"
            )

        system_info = get_system_info()
        project_context = get_project_context_for_agent()
        if project_context is None:
            logger.warning("No project context available")
            project_context = ProjectContext(projects=[])

        # Get the base function name
        function_name = agent_function_mapping[agent_name]

        # Prepare parameters based on agent type
        if agent_name == Agent.ROADMAP:
            base_params = BasePromptParams(
                system_info=system_info, project_context=project_context
            )
            prompt_params = RoadmapPromptParams(base_params=base_params)
            params = RoadmapAgentParams(context=context, prompt_params=prompt_params)
        else:
            raise ValueError(
                f"Agent type {agent_name} not implemented yet")

        logger.debug(f"Executing {agent_name.value} agent using BAMLService")

        # Initialize BAMLService and execute
        baml_service = BAMLService()
        baml_response = baml_service.call(
            function_name=function_name, params=params)

        logger.debug("Agent execution completed successfully")

        return AgentResponse(
            agent_type=agent_name,
            content=baml_response,
        )

    except Exception as e:
        logger.error(f"Error executing agent {agent_name.value}: {str(e)}")
        raise
