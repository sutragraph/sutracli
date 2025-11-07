"""Exception types for agent management."""

from enum import Enum


class AgentErrorType(Enum):
    """Error types for agent management operations."""

    USER_CANCELLED = "user_cancelled"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    COMPLETION_WITHOUT_RESULT = "completion_without_result"
