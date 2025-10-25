from typing import NamedTuple, Union

from loguru import logger

from baml_client.types import (
    Agent,
    DeveloperPromptParams,
    DeveloperResponse,
    ProjectContext,
    QAEngineerPromptParams,
    QAEngineerResponse,
    RoadmapPromptParams,
    RoadmapResponse,
)
from services.baml_service import BAMLService

from .utils import get_project_context_for_agent, get_system_info

AgentContentType = Union[RoadmapResponse, DeveloperResponse, QAEngineerResponse]


class AgentResponse(NamedTuple):
    """Structured response from agent execution including agent type."""

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
    agent_function_mapping = {
        Agent.Roadmap: "RoadmapAgent",
        Agent.Developer: "DeveloperAgent",
        Agent.QAEngineer: "QAEngineerAgent",
    }

    try:
        # Validate agent name
        if agent_name not in agent_function_mapping:
            available_agents = list(agent_function_mapping.keys())
            available_names = [a.value for a in available_agents]
            raise ValueError(
                f"Unsupported agent: {agent_name}. Available: {available_names}"
            )

        # Get the base function name
        function_name = agent_function_mapping[agent_name]

        # Prepare parameters based on agent type
        params = get_agent_params(agent_name, context)

        logger.debug(f"Executing {agent_name.value} agent using BAMLService")

        # Initialize BAMLService and execute
        baml_service = BAMLService()
        baml_response = baml_service.call(function_name=function_name, params=params)

        logger.debug("Agent execution completed successfully")

        return AgentResponse(
            agent_type=agent_name,
            content=baml_response,
        )

    except Exception as e:
        logger.error(f"Error executing agent {agent_name.value}: {str(e)}")
        raise


def get_agent_params(
    agent: Agent, context: str
) -> Union[RoadmapPromptParams, DeveloperPromptParams, QAEngineerPromptParams]:
    system_info = get_system_info()
    project_context = get_project_context_for_agent()
    if project_context is None:
        logger.warning("No project context available")
        project_context = ProjectContext(projects=[])

    match agent:
        case Agent.Roadmap:
            return RoadmapPromptParams(
                context=context,
                system_info=system_info,
                project_context=project_context,
            )
        case Agent.Developer:
            return DeveloperPromptParams(
                context=context,
                system_info=system_info,
            )
        case Agent.QAEngineer:
            return QAEngineerPromptParams(
                context=context,
                system_info=system_info,
            )
        case _:
            raise ValueError(f"Agent type {agent} not implemented yet")
