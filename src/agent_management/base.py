from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional

from baml_client.types import Agent

from .agent_graph import AgentGraph
from .registry import AgentRegistry


@dataclass
class AgentData:
    """Data structure for agent communication"""

    context: str


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, agent_type: Agent):
        self.agent_type = agent_type
        AgentRegistry.register(self)

    @abstractmethod
    def from_upstream(self, data: AgentData) -> None:
        """Handle data from upstream agent"""
        pass

    @abstractmethod
    def from_downstream(self, data: AgentData) -> None:
        """Handle data from downstream agent"""
        pass

    def send_to_downstream(self, data: AgentData) -> None:
        """Send data to next agent in flow"""
        downstream_type = AgentGraph.get_downstream(self.agent_type)

        if downstream_type:
            downstream = AgentRegistry.get(downstream_type)
            if downstream:
                print(f"[{self.agent_type.name}] → [{downstream_type.name}]")
                downstream.from_upstream(data)
        else:
            print(f"[{self.agent_type.name}] End of flow")

    def send_to_upstream(self, data: AgentData) -> None:
        """Send data back to previous agent"""
        upstream_type = AgentGraph.get_upstream(self.agent_type)

        if upstream_type:
            upstream = AgentRegistry.get(upstream_type)
            if upstream:
                print(f"[{self.agent_type.name}] ← [{upstream_type.name}]")
                upstream.from_downstream(data)
        else:
            print(f"[{self.agent_type.name}] No upstream agent")
