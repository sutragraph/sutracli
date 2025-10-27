from dataclasses import dataclass
from typing import NamedTuple, Union

from baml_client.types import (
    Agent,
    DeveloperResponse,
    QAEngineerResponse,
    RoadmapResponse,
)

AgentContentType = Union[RoadmapResponse, DeveloperResponse, QAEngineerResponse]


class AgentResponse(NamedTuple):
    """Structured response from agent execution including agent type."""

    agent_type: Agent
    content: AgentContentType


@dataclass
class AgentData:
    context: str
    success: bool = True
