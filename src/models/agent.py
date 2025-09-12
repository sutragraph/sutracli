"""Agent data models for agentic operations."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class AgentAction:
    """Represents an action the agent wants to take.

    Tools use parameters dict for accessing tool-specific data.
    Query data flows through parameters.get("query") from XML-parsed tool calls.
    """

    description: str
    parameters: Dict[str, Any] = field(
        default_factory=dict
    )  # Primary source for XML-parsed tool parameters
