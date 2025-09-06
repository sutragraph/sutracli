from loguru import logger
from typing import Optional
from graph.sqlite_client import SQLiteConnection
from baml_client.types import ProjectContext, Project


def get_project_context_for_agent() -> Optional[ProjectContext]:
    """
    Get dynamic project context based on the query using BAML functions.

    Returns:
        ProjectContext object with list of projects, or None if no projects found
    """
    try:
        connection = SQLiteConnection()
        projects = connection.list_all_projects()

        if not projects:
            logger.warning("No projects found in database")
            return None

        # Convert project objects to BAML Project format
        baml_projects = []
        for project in projects:
            baml_project = Project(
                name=project.name,
                path=project.path,
                description=getattr(project, "description", "No description available"),
            )
            baml_projects.append(baml_project)

        # Create and return ProjectContext
        return ProjectContext(projects=baml_projects)

    except Exception as e:
        logger.error(f"Error getting dynamic project context: {str(e)}")
        return None
