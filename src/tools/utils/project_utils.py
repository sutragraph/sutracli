"""
Project utilities for auto-detection and path resolution.
"""

from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from loguru import logger

from graph.sqlite_client import SQLiteConnection


def auto_detect_project_from_paths(paths: List[str]) -> Optional[Tuple[str, List[str]]]:
    """
    Auto-detect project name from absolute file paths by matching against known project base paths.

    Args:
        paths: List of file/directory paths to check

    Returns:
        Tuple of (project_name, list_of_matched_paths) if found, None otherwise
    """
    try:
        db_connection = SQLiteConnection()
        all_projects = db_connection.list_all_projects()

        if not all_projects:
            return None

        best_match_project = None
        longest_match_length = 0

        # First pass: find the project with the longest matching path (most specific)
        for path in paths:
            path_obj = Path(path)
            if path_obj.is_absolute():
                for project in all_projects:
                    if (
                        project.path
                        and str(path_obj).startswith(project.path)
                        and len(project.path.strip("/")) > 0
                    ):  # Filter out root paths
                        match_length = len(project.path)
                        if match_length > longest_match_length:
                            longest_match_length = match_length
                            best_match_project = project

        # Second pass: collect all paths that match the best project
        if best_match_project:
            matched_paths = []
            for path in paths:
                path_obj = Path(path)
                if path_obj.is_absolute() and str(path_obj).startswith(
                    best_match_project.path
                ):
                    matched_paths.append(path)

            if matched_paths:
                return (best_match_project.name, matched_paths)

    except Exception as e:
        logger.debug(f"Failed to auto-detect project from paths: {str(e)}")

    return None


def resolve_project_base_path(project_name: str) -> Optional[str]:
    """
    Get the base path for a given project name.

    Args:
        project_name: Name of the project

    Returns:
        Project base path if found, None otherwise
    """
    try:
        db_connection = SQLiteConnection()
        project = db_connection.get_project(project_name)
        if project and project.path:
            return project.path
    except Exception as e:
        logger.debug(
            f"Failed to resolve project base path for '{project_name}': {str(e)}"
        )

    return None
