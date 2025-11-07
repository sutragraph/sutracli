from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from loguru import logger

from agent_management.core.agent_graph import AgentGraph, IndexingRequirement
from agent_management.core.registry import AgentRegistry
from agent_management.handlers.indexing_handler import IndexingHandler
from baml_client.types import Agent
from services.agent.memory_management import SutraMemoryManager
from services.agent.memory_management.models import MemorySection
from services.agent_service import AgentService
from src.agent_management.types.agent import AgentData
from tools import AllToolParams


class BaseAgent(ABC):
    def __init__(
        self,
        agent_type: Agent,
        project_path: Path,
        parent_key: Optional[Tuple[Agent, Path]] = None,
    ):
        self.agent_type = agent_type
        self.memory = SutraMemoryManager()
        self.project_path = project_path
        self.parent_key = parent_key  # Registry key of the parent agent
        self.indexing_handler = IndexingHandler()
        self.file_content_map: Dict[str, Dict[str, str]] = {}

        AgentRegistry.register(self)

    @abstractmethod
    def from_upstream(self, data: AgentData) -> None:
        pass

    @abstractmethod
    def from_downstream(self, data: AgentData) -> None:
        pass

    def send_to_downstream(
        self, data: AgentData, target_project_path: Optional[Path] = None
    ) -> None:
        downstream_type = AgentGraph.get_downstream(self.agent_type)

        if downstream_type:
            lookup_path = (
                target_project_path if target_project_path else self.project_path
            )
            downstream = AgentRegistry.get(downstream_type, lookup_path)
            if downstream is None:
                # Create downstream with parent key pointing to this agent
                parent_key = AgentRegistry._make_key(self.agent_type, self.project_path)
                downstream = AgentRegistry.get_or_create(
                    downstream_type, lookup_path, parent_key=parent_key
                )
                logger.debug(
                    f"[{self.agent_type.name}] auto-registered downstream [{downstream_type.name}] at {lookup_path}"
                )

            logger.debug(f"[{self.agent_type.name}] → [{downstream_type.name}]")
            downstream.from_upstream(data)
        else:
            logger.debug(f"[{self.agent_type.name}] End of flow")

    def send_to_upstream(self, data: AgentData) -> None:
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        upstream_type = AgentGraph.get_upstream(self.agent_type)

        if upstream_type:
            upstream = AgentRegistry.get(upstream_type, self.project_path)
            if upstream is None:
                upstream = AgentRegistry.get_or_create(upstream_type, self.project_path)
                logger.debug(
                    f"[{self.agent_type.name}] auto-registered upstream [{upstream_type.name}] at {self.project_path}"
                )

            logger.debug(f"[{self.agent_type.name}] → [{upstream_type.name}]")
            upstream.from_downstream(data)
        else:
            logger.debug(f"[{self.agent_type.name}] No upstream agent")

    def run_agent_loop(self, problem_query: str) -> AllToolParams:
        agent_service = AgentService(
            agent_name=self.agent_type,
            project_path=self.project_path,
            sutra_memory=self.memory,
            file_content_map=self.file_content_map,
        )

        try:
            return agent_service.solve_problem(problem_query)
        except RuntimeError as e:
            error_type = getattr(e, "error_type", None)
            if error_type:
                logger.error(
                    f"[{self.agent_type.name}] Agent error: {error_type} - {str(e)}"
                )
            raise

    def run_with_user_role(self, input_data: str) -> None:
        """Run agent with user role and maintain normal downstream/upstream flow.

        Args:
            input_data: String input that will be treated as coming from USER role.
        """
        # Create AgentData with USER role
        data = AgentData.from_context(input_data, "USER")

        # Process the user input and follow normal flow
        self.from_upstream(data)

    def copy_memory_from_agent(
        self,
        agent_key: Optional[Tuple[Agent, Path]] = None,
        sections_to_copy: Optional[Set[MemorySection]] = None,
        project_path: Optional[Path] = None,
    ) -> bool:
        """
        Copy memory sections from another agent to this agent.

        Args:
            agent_key: The registry key (Agent, Path) of the agent to copy memory from.
                      If None, uses the parent_key if available.
            sections_to_copy: Specific memory sections to copy. If None, copies all sections.
            project_path: Project path context for the operation. If None, uses this agent's project_path.

        Returns:
            bool: True if memory copy was successful, False otherwise.

        Raises:
            ValueError: If project_path is not set or provided.
        """
        target_path = project_path or self.project_path
        if not target_path:
            raise ValueError(
                f"Project path must be set or provided for {self.agent_type.name}"
            )

        # If no agent_key provided, use the parent_key
        if agent_key is None:
            agent_key = self.parent_key
            if not agent_key:
                logger.warning(
                    f"[{self.agent_type.name}] No agent_key or parent_key found for memory copy"
                )
                return False

        source_agent = AgentRegistry._instances.get(agent_key)
        if not source_agent:
            logger.warning(
                f"[{self.agent_type.name}] Source agent not found for key {agent_key}"
            )
            return False

        if sections_to_copy:
            # Filter code snippets by project path when copying
            filtered_state = source_agent.memory.filter_sections(
                sections_to_copy, str(target_path)
            )
            return self.memory.import_memory_state(filtered_state)

        # Filter code snippets by project path when copying all sections
        source_state = source_agent.memory.export_memory_state(str(target_path))
        return self.memory.import_memory_state(source_state)

    def clear_memory_sections(self, sections: Set[MemorySection]) -> None:
        self.memory.clear_sections(sections)

    def clear_file_content_map(self) -> None:
        """Clear the file content map."""
        logger.debug(
            f"[{self.agent_type.name}] Clearing file content map with {len(self.file_content_map)} entries"
        )
        self.file_content_map.clear()

    def run_prerequisites(self) -> bool:
        if not self.project_path:
            raise ValueError(f"Project path must be set for {self.agent_type.name}")

        agent_config = AgentGraph.get_config(self.agent_type)
        if not agent_config:
            logger.error(f"Agent config not found for {self.agent_type.name}")
            return False

        prerequisites = agent_config.prerequisites

        if not prerequisites:
            logger.debug(f"No prerequisites for {self.agent_type.name}")
            return True

        try:
            if IndexingRequirement.INDEXING in prerequisites:
                logger.debug(
                    f"Running INDEXING prerequisite for {self.agent_type.name}"
                )
                self.indexing_handler.run_full_indexing(self.project_path)

            if IndexingRequirement.MULTI_PROJECT_INCREMENTAL_INDEXING in prerequisites:
                logger.debug(
                    f"Running MULTI_PROJECT_INCREMENTAL_INDEXING prerequisite for {self.agent_type.name}"
                )
                changes_by_project = (
                    self.indexing_handler.run_multi_project_incremental_indexing()
                )

                if (
                    IndexingRequirement.INCREMENTAL_CROSS_INDEXING in prerequisites
                    and changes_by_project
                ):
                    logger.debug(
                        f"Running INCREMENTAL_CROSS_INDEXING prerequisite for {self.agent_type.name}"
                    )
                    self.indexing_handler.run_incremental_cross_indexing(
                        changes_by_project
                    )

            if IndexingRequirement.INCREMENTAL_INDEXING in prerequisites:
                logger.debug(
                    f"Running INCREMENTAL_INDEXING prerequisite for {self.agent_type.name}"
                )
                self.indexing_handler.run_single_project_incremental_indexing(
                    self.project_path
                )

            if IndexingRequirement.CROSS_INDEXING in prerequisites:
                logger.debug(
                    f"Running CROSS_INDEXING prerequisite for {self.agent_type.name}"
                )
                self.indexing_handler.run_cross_indexing(self.project_path)

            logger.debug(f"All prerequisites completed for {self.agent_type.name}")
            return True

        except Exception as e:
            logger.error(f"Error running prerequisites for {self.agent_type.name}: {e}")
            return False
