from pathlib import Path
from typing import Optional

from baml_client.types import Agent

from .base import AgentData, BaseAgent


class RoadmapAgent(BaseAgent):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(Agent.ROADMAP, project_path)

    def start_project(self, project_data: str) -> None:
        print(f"\n[{self.agent_type.name}] Starting project planning...")

        self.run_agent_loop("Create project roadmap")

        data = AgentData(context=project_data)
        print(f"\n[{self.agent_type.name}] Spawning developers for projects")
        self.send_to_downstream(data)

    def from_upstream(self, data: AgentData) -> None:
        pass

    def from_downstream(self, data: AgentData) -> None:
        print(f"\n[{self.agent_type.name}] Received results from Developer")

        if "success" in data.context:
            print(f"[{self.agent_type.name}] Project completed successfully!")
        else:
            print(f"[{self.agent_type.name}] Developer is working on fixes...")
