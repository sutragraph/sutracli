from typing import Any, Dict

from baml_client.types import Agent

from .base import AgentData, BaseAgent


class QAEngineerAgent(BaseAgent):
    """
    QA Engineer Agent that:
    - Receives data from Developer agent (upstream)
    - Runs QA agent loop
    - Sends results back upstream to Developer
    - Does not send data downstream
    """

    def __init__(self):
        super().__init__(Agent.QAEngineer)

    def from_upstream(self, data: AgentData) -> None:
        """
        Handle data received from Developer agent (upstream in the flow).
        This is where QA Engineer receives the code/features to test.

        Args:
            data: AgentData containing context from Developer
        """
        print(f"\n[{self.agent_type.name}] Received data from Developer")
        print(f"[{self.agent_type.name}] Context: {data.context[:100]}...")

        # Send results back upstream to Developer
        result_data = AgentData(context="summary")
        print(f"\n[{self.agent_type.name}] Sending QA results back to Developer")
        self.send_to_upstream(result_data)

    def from_downstream(self, data: AgentData) -> None:
        """
        Handle data received from downstream agent.
        QA Engineer does not have a downstream agent, so this should not be called.

        Args:
            data: AgentData from downstream (not expected)
        """
        pass
