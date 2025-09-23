import os
from typing import Optional

from loguru import logger

from baml_client.types import Project, ProjectContext
from graph.sqlite_client import SQLiteConnection


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
            # Check if current directory matches project path
            project_name = project.name
            if os.getcwd() == project.path:
                project_name += " [CURRENT]"

            baml_project = Project(
                name=project_name,
                path=project.path,
                description=getattr(project, "description", "No description available"),
            )
            baml_projects.append(baml_project)

        # Create and return ProjectContext
        return ProjectContext(projects=baml_projects)

    except Exception as e:
        logger.error(f"Error getting dynamic project context: {str(e)}")
        return None
