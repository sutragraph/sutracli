"""
Prerequisites executor for roadmap agent.
Main entry point for executing prerequisites before roadmap agent runs.
"""

from typing import Any, Dict, Optional

from loguru import logger

from src.agent_management.prerequisites.indexing_handler import (
    IndexingPrerequisitesHandler,
)
from src.agents_new import Agent


class PrerequisitesExecutor:
    """Main executor for agent prerequisites."""

    def __init__(self):
        """Initialize the prerequisites executor."""
        self.indexing_handler = IndexingPrerequisitesHandler()
        logger.debug("🔧 PrerequisitesExecutor initialized")

    def execute_prerequisites_for_agent(self, agent: Agent) -> Dict[str, Any]:
        """
        Execute prerequisites for specified agent.

        Args:
            agent: The agent that will be executed

        Returns:
            Dictionary with prerequisites execution results
        """
        logger.info(f"🚀 Executing prerequisites for agent: {agent.value}")

        try:
            if agent == Agent.ROADMAP:
                return self._execute_roadmap_prerequisites()
            else:
                # For other agents, no prerequisites needed currently
                return {
                    "status": "completed",
                    "message": f"No prerequisites required for agent: {agent.value}",
                    "agent": agent.value,
                }

        except Exception as e:
            logger.error(f"❌ Error executing prerequisites for {agent.value}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to execute prerequisites for {agent.value}: {e}",
                "agent": agent.value,
            }

    def _execute_roadmap_prerequisites(self) -> Dict[str, Any]:
        """
        Execute prerequisites specific to roadmap agent.

        Returns:
            Dictionary with roadmap prerequisites results
        """
        logger.info("🔄 Executing roadmap agent prerequisites")

        try:
            # Execute incremental indexing for all projects
            indexing_result = self.indexing_handler.execute_prerequisites()

            logger.info(
                f"✅ Roadmap prerequisites completed: {indexing_result['message']}"
            )

            return {
                "status": indexing_result["status"],
                "message": f"Roadmap prerequisites completed: {indexing_result['message']}",
                "agent": Agent.ROADMAP.value,
                "indexing_results": indexing_result,
                "total_projects": indexing_result.get("total_projects", 0),
                "indexed_projects": indexing_result.get("indexed_projects", 0),
                "failed_projects": indexing_result.get("failed_projects", 0),
                "skipped_projects": indexing_result.get("skipped_projects", 0),
            }

        except Exception as e:
            logger.error(f"❌ Error executing roadmap prerequisites: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to execute roadmap prerequisites: {e}",
                "agent": Agent.ROADMAP.value,
            }

    def validate_prerequisites(self, agent: Agent) -> Dict[str, Any]:
        """
        Validate that prerequisites can be executed for specified agent.

        Args:
            agent: The agent to validate prerequisites for

        Returns:
            Dictionary with validation results
        """
        logger.debug(f"🔍 Validating prerequisites for agent: {agent.value}")

        try:
            if agent == Agent.ROADMAP:
                return self._validate_roadmap_prerequisites()
            else:
                return {
                    "valid": True,
                    "message": f"No prerequisites validation needed for {agent.value}",
                    "agent": agent.value,
                }

        except Exception as e:
            logger.error(f"❌ Error validating prerequisites for {agent.value}: {e}")
            return {
                "valid": False,
                "error": str(e),
                "message": f"Failed to validate prerequisites for {agent.value}: {e}",
                "agent": agent.value,
            }

    def _validate_roadmap_prerequisites(self) -> Dict[str, Any]:
        """
        Validate prerequisites specific to roadmap agent.

        Returns:
            Dictionary with validation results
        """
        try:
            # Check if we can access the database and get projects
            projects = self.indexing_handler.get_projects_requiring_indexing()

            if not projects:
                return {
                    "valid": True,
                    "message": "No projects found - prerequisites validation passed",
                    "agent": Agent.ROADMAP.value,
                    "projects_count": 0,
                }

            # Validate project paths exist
            validation_result = self.indexing_handler.validate_project_paths(projects)

            valid_count = len(validation_result["valid_projects"])
            invalid_count = len(validation_result["invalid_projects"])

            if invalid_count > 0:
                logger.warning(f"⚠️  Found {invalid_count} projects with invalid paths")

            return {
                "valid": True,  # Always valid, just report issues
                "message": f"Prerequisites validation completed - {valid_count} valid projects, {invalid_count} invalid",
                "agent": Agent.ROADMAP.value,
                "projects_count": len(projects),
                "valid_projects": valid_count,
                "invalid_projects": invalid_count,
                "validation_details": validation_result,
            }

        except Exception as e:
            logger.error(f"❌ Error validating roadmap prerequisites: {e}")
            return {
                "valid": False,
                "error": str(e),
                "message": f"Failed to validate roadmap prerequisites: {e}",
                "agent": Agent.ROADMAP.value,
            }

    def get_prerequisites_status(self, agent: Agent) -> Dict[str, Any]:
        """
        Get current status of prerequisites for specified agent.

        Args:
            agent: The agent to get status for

        Returns:
            Dictionary with prerequisites status
        """
        try:
            if agent == Agent.ROADMAP:
                projects = self.indexing_handler.get_projects_requiring_indexing()
                validation = self.indexing_handler.validate_project_paths(projects)

                return {
                    "agent": agent.value,
                    "has_prerequisites": True,
                    "total_projects": len(projects),
                    "valid_projects": len(validation["valid_projects"]),
                    "invalid_projects": len(validation["invalid_projects"]),
                    "prerequisites_ready": len(validation["valid_projects"]) > 0,
                }
            else:
                return {
                    "agent": agent.value,
                    "has_prerequisites": False,
                    "prerequisites_ready": True,
                }

        except Exception as e:
            logger.error(f"❌ Error getting prerequisites status: {e}")
            return {
                "agent": agent.value,
                "has_prerequisites": True,
                "prerequisites_ready": False,
                "error": str(e),
            }


# Global instance for easy access
_prerequisites_executor: Optional[PrerequisitesExecutor] = None


def get_prerequisites_executor() -> PrerequisitesExecutor:
    """Get global prerequisites executor instance."""
    global _prerequisites_executor
    if _prerequisites_executor is None:
        _prerequisites_executor = PrerequisitesExecutor()
    return _prerequisites_executor
