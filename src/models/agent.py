"""Agent data models for agentic operations."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class AgentAction:
    """Represents an action the agent wants to take.

    Tools use parameters dict for accessing tool-specific data.
    Query data flows through parameters.get("query") from XML-parsed tool calls.
    """

    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)  # Primary source for XML-parsed tool parameters


@dataclass
class AgentThought:
    """Represents a single thought in the agent's reasoning process."""

    thought_id: str
    analysis: str  # What was discovered/understood (from LLM summary)
    user_message: Optional[str]  # User-friendly message (from LLM user_message)
    timestamp: float
