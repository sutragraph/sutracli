"""Agentic core classes and enums for agentic operations."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class AgentAction:
    """Represents an action the agent wants to take."""
    tool_type: str  # "terminal", "database", "semantic_search"
    description: str
    command: Optional[str] = None
    query: Optional[str] = None  # For database/semantic_search queries
    parameters: Optional[Dict[str, Any]] = None
    priority: int = 1

@dataclass
class AgentThought:
    """Represents a single thought in the agent's reasoning process."""
    thought_id: str
    analysis: str  # What was discovered/understood (from LLM summary)
    user_message: Optional[str]  # User-friendly message (from LLM user_message)
    confidence: float
    timestamp: float
