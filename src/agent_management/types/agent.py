from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Union

from baml_client.types import (
    Agent,
    DeveloperResponse,
    QAEngineerResponse,
    RoadmapResponse,
)

AgentContentType = Union[RoadmapResponse, DeveloperResponse, QAEngineerResponse]

# Union type for roles - can be Agent or User
Role = Union[Agent, str]  # Using str for "USER" since User might not be in Agent enum


class AgentResponse(NamedTuple):
    """Structured response from agent execution including agent type."""

    agent_type: Agent
    content: AgentContentType


@dataclass
class AgentData:
    conversation: List[Dict[Role, str]]
    success: bool = True

    def add_message(self, role: Role, message: str) -> None:
        """Add a message to the conversation history."""
        self.conversation.append({role: message})

    def format_conversation(
        self, include_roles: List[Role] | None = None, current_agent: Role | None = None
    ) -> str:
        """Format the conversation into a string for agent consumption.

        Args:
            include_roles: If provided, only include messages from these role types.
                          If None, include all messages.
            current_agent: If provided, this agent's messages will be displayed as "YOU".

        Returns:
            Formatted conversation string.
        """
        formatted_messages = []

        for msg in self.conversation:
            for role, message in msg.items():
                if include_roles is None or role in include_roles:
                    # Use "YOU" for the current agent's messages
                    if current_agent is not None and role == current_agent:
                        role_name = "YOU"
                    else:
                        if isinstance(role, str):
                            role_name = role
                        else:
                            role_name = role.name
                    formatted_messages.append(f"{role_name}:\n{message}")

        return "\n\n".join(formatted_messages) if formatted_messages else ""

    def get_last_message(self, role: Role = "USER") -> Dict[Role, str] | None:
        """Get the last message from the conversation.

        Args:
            role: If provided, get the last message from this specific role.

        Returns:
            The last message dict, or None if no messages exist.
        """
        if not self.conversation:
            return None

        if role is None:
            return self.conversation[-1]

        # Find the last message from the specified role
        for msg in reversed(self.conversation):
            if role in msg:
                return msg
        return None

    @classmethod
    def from_context(cls, context: str, initial_role: Role = "USER") -> "AgentData":
        """Create an AgentData instance from a simple context string.

        Args:
            context: Initial context string.
            initial_role: The role type to attribute the context to.

        Returns:
            AgentData instance with the context as the first message.
        """
        return cls(conversation=[{initial_role: context}])
