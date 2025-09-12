"""Project Manager - Centralized project management functionality."""

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from graph.graph_operations import GraphOperations
from graph.project_indexer import ProjectIndexer
from graph.sqlite_client import SQLiteConnection
from models import Project


class ProjectManager:
    """Centralized project management for creation, indexing, and directory management."""

    def __init__(
        self,
        memory_manager=None,
    ):
        """Initialize the project manager.

        Args:
            db_connection: Database connection for project operations

            memory_manager: Optional memory manager for incremental indexing
        """
        self.db_connection = SQLiteConnection()

        self.memory_manager = memory_manager

        # Initialize project indexer with memory manager if provided
        self.project_indexer = ProjectIndexer(self.memory_manager)

        # Use the converter from project indexer to avoid duplication
        self.converter = self.project_indexer.converter

        # Cache for project directories to avoid repeated calculations
        self._project_dir_cache: Dict[str, Optional[Path]] = {}

        self.graph_ops = GraphOperations()

    def create_project_name(self, project_path: Path) -> str:
        """Create a project name based on the provided path using a custom readable algorithm.

        Args:
            project_path: Absolute path to the project directory

        Returns:
            A readable project name derived from the path
        """
        if not project_path or not isinstance(project_path, Path):
            raise ValueError("Invalid project path provided")

        # Convert to absolute path to ensure consistency
        abs_path = project_path.resolve()
        path_str = str(abs_path)

        # Get the directory name as base
        dir_name = abs_path.name or "project"

        # Clean and normalize the directory name
        clean_dir = re.sub(r"[^a-zA-Z0-9]", "", dir_name.lower())

        # Create a custom "hash" using path characteristics
        path_signature = self._generate_path_signature(path_str)

        # Combine for final name
        return f"{clean_dir}_{path_signature}"

    def _generate_path_signature(self, path_str: str) -> str:
        """Generate a readable signature from path string."""

        # Convert path to numbers based on character positions and values
        char_sum = sum(ord(c) for c in path_str)
        char_count = len(path_str)

        # Create meaningful components
        depth = path_str.count("/")  # Unix-style, adjust for Windows if needed
        vowel_count = sum(1 for c in path_str.lower() if c in "aeiou")
        consonant_count = sum(
            1 for c in path_str.lower() if c.isalpha() and c not in "aeiou"
        )

        # Generate readable components
        # Use modulo operations to create bounded, meaningful values

        # Size indicator (xs, s, m, l, xl based on path length)
        size_map = ["xs", "s", "m", "l", "xl", "xxl"]
        size = size_map[min(char_count // 10, len(size_map) - 1)]

        # Location indicator based on depth
        depth_names = ["root", "sub", "deep", "nested", "buried", "hidden"]
        location = depth_names[min(depth, len(depth_names) - 1)]

        # Pattern based on character distribution
        ratio = (
            (vowel_count * 100) // max(consonant_count, 1) if consonant_count > 0 else 0
        )
        pattern_map = {
            range(0, 25): "compact",
            range(25, 50): "balanced",
            range(50, 75): "flowing",
            range(75, 150): "verbose",
        }

        pattern = "unique"
        for r, name in pattern_map.items():
            if ratio in r:
                pattern = name
                break

        # Version number based on character sum (keeps it deterministic)
        version = (char_sum % 99) + 1

        return f"{size}{location}{pattern}v{version}"

    def determine_project_name(self, project_path: Path) -> str:
        """Determine the correct project name from the database or specified directory.

        Args:
            project_path: Path object to the project directory (required).

        Raises:
            ValueError: If project_path is not provided or is invalid.
        """
        if not project_path:
            raise ValueError("project_path is required and cannot be None")

        if not isinstance(project_path, Path):
            raise ValueError("project_path must be a Path object")

        target_path = project_path.absolute()

        if not target_path.exists():
            raise ValueError(f"Project path does not exist: {target_path}")

        try:
            projects = self.db_connection.list_all_projects()
            if projects:
                # Check if target directory is a subdirectory of any existing project
                existing_project = self.find_parent_project(projects, target_path)
                if existing_project:
                    logger.debug(f"Found parent project: {existing_project}")
                    return existing_project

            # If no parent project found or no projects exist, create a new project name
            # using the custom hashing algorithm instead of just directory name
            target_name = self.create_project_name(target_path)
            logger.debug(f"Generated new project name: {target_name}")
            return target_name

        except Exception as e:
            logger.error(f"Error determining project name: {e}")
            raise

    def find_parent_project(
        self, projects: List[Project], target_path: Path
    ) -> Optional[str]:
        """Find if target directory is a subdirectory of any existing project.

        Args:
            projects: List of existing projects from database
            target_path: Path to check. If None, uses current directory.
        """

        for project in projects:
            project_name = project.name
            try:
                # Get the project's root directory by finding the common root of all file paths
                project_dir = self.get_project_directory(project_name)
                if project_dir and target_path.is_relative_to(project_dir):
                    logger.debug(
                        f"Directory {target_path} is within project {project_name} at {project_dir}"
                    )
                    return project_name
            except Exception as e:
                logger.debug(f"Error checking project {project_name}: {e}")
                continue

        return None

    def get_project_name_from_path(self, project_path: Path) -> str:
        """Get or create a project name for the given path.

        This is a convenience method that combines path resolution and project name creation.

        Args:
            project_path: Path object to the project directory (required).

        Returns:
            A project name for the given path

        Raises:
            ValueError: If project_path is not provided or is invalid.
        """
        if not project_path:
            raise ValueError("project_path is required and cannot be None")

        if not isinstance(project_path, Path):
            raise ValueError("project_path must be a Path object")

        target_path = project_path.absolute()

        if not target_path.exists():
            raise ValueError(f"Project path does not exist: {target_path}")

        return self.create_project_name(target_path)

    def get_project_directory(self, project_name: str) -> Union[Path, None]:
        """Get the root directory of a project by analyzing its file paths.

        Args:
            project_name: Name of the project (required)

        Returns:
            Path to the project directory or None if not found

        Raises:
            ValueError: If project_name is not provided or is invalid
        """
        if not project_name:
            raise ValueError("project_name is required and cannot be None or empty")

        if not isinstance(project_name, str):
            raise ValueError("project_name must be a string")

        # Check cache first
        if project_name in self._project_dir_cache:
            return self._project_dir_cache[project_name]

        try:
            file_paths_list = self.graph_ops.get_project_file_paths(project_name)
            file_paths = [{"file_path": path} for path in file_paths_list]

            if not file_paths:
                self._project_dir_cache[project_name] = None
                return None

            # Convert to Path objects and find common root
            paths = [Path(row["file_path"]).absolute() for row in file_paths]

            # Find the common root directory
            if len(paths) == 1:
                result = paths[0].parent
            else:
                # Find the longest common path
                common_path = paths[0]
                for path in paths[1:]:
                    # Find common parts between current common_path and this path
                    common_parts = []
                    for part1, part2 in zip(common_path.parts, path.parts):
                        if part1 == part2:
                            common_parts.append(part1)
                        else:
                            break

                    if common_parts:
                        common_path = Path(*common_parts)
                    else:
                        # No common path found
                        result = None
                        break
                else:
                    result = common_path

            # Cache the result
            self._project_dir_cache[project_name] = result
            return result

        except Exception as e:
            logger.error(f"Error getting project directory for {project_name}: {e}")
            # Cache the failure to avoid repeated queries
            self._project_dir_cache[project_name] = None
            raise

    def check_project_exists(self, project_name: str) -> bool:
        """Check if a project exists in the database.

        Args:
            project_name: Name of the project to check

        Returns:
            True if project exists, False otherwise
        """
        try:
            return self.db_connection.project_exists(project_name)
        except Exception as e:
            logger.error(f"Error checking if project exists {project_name}: {e}")
            return False

    def auto_index_project(self, project_name: str, project_path: Path) -> None:
        """Automatically index the specified project if not found in database.

        Args:
            project_name: Name of the project
            project_path: Path to the project directory
        """
        try:
            # Delegate to ProjectIndexer for full indexing
            self.project_indexer.full_index_project(project_name, project_path)

            # Clear cache for this project since we just indexed it
            self._project_dir_cache.pop(project_name, None)

        except Exception as e:
            logger.error(f"Error during auto-indexing: {e}")
            print(f"❌ Auto-indexing failed: {e}")
            print("   Continuing with limited functionality.")

    def perform_incremental_indexing(self, project_name: str) -> Dict[str, Any]:
        """Perform incremental reindexing of the database for the specified project.

        Args:
            project_name: Name of the project to reindex

        Returns:
            Indexing status and statistics
        """
        logger.debug(f"🔄 Running incremental indexing for project {project_name}")
        stats = self.project_indexer.incremental_index_project(project_name)

        if stats.get("status") == "success":
            return {
                "type": "indexing_complete",
                "stats": stats,
                "timestamp": time.time(),
            }
        else:
            return {
                "type": "error",
                "message": stats.get("error", "Unknown indexing error"),
                "stats": stats,
                "timestamp": time.time(),
            }

    def list_projects(self) -> List[Project]:
        """List all projects in the database.

        Returns:
            List of Project objects
        """
        try:
            return self.db_connection.list_all_projects()
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []

    def delete_project(self, project_name: str) -> Dict[str, Any]:
        """Delete a project and all its associated data.

        Args:
            project_name: Name of the project to delete

        Returns:
            Dictionary with deletion result
        """
        try:
            # Check if project exists
            if not self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found",
                }

            # Delete project (assuming SQLiteConnection has a method for this)
            # Note: This might need to be adjusted based on actual SQLiteConnection API
            self.db_connection.delete_project(project_name)

            # Clear cache for this project
            self._project_dir_cache.pop(project_name, None)

            print(f"Deleted project '{project_name}'")

            return {"success": True, "project_name": project_name}

        except Exception as e:
            logger.error(f"Error deleting project {project_name}: {e}")
            return {"success": False, "error": str(e)}

    def clear_cache(self) -> None:
        """Clear the project directory cache."""
        self._project_dir_cache.clear()
        logger.debug("Cleared project directory cache")

    def index_project_at_path(
        self, project_path: str, project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Index a project at the specified path.

        Args:
            project_path: Path to the project directory to index
            project_name: Optional custom project name. If None, uses directory name.

        Returns:
            Result dictionary with indexing status
        """
        try:
            target_path = Path(project_path).absolute()

            # Validate path exists
            if not target_path.exists():
                return {
                    "success": False,
                    "error": f"Project path does not exist: {project_path}",
                }

            if not target_path.is_dir():
                return {
                    "success": False,
                    "error": f"Project path is not a directory: {project_path}",
                }

            # Determine project name
            if project_name is None:
                project_name = self.determine_project_name(target_path)

            # Check if project already exists
            if self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' already exists in database",
                }

            # Perform the indexing
            self.auto_index_project(project_name, target_path)

            return {
                "success": True,
                "project_name": project_name,
                "project_path": str(target_path),
                "message": f"Successfully indexed project '{project_name}'",
            }

        except Exception as e:
            logger.error(f"Error indexing project at {project_path}: {e}")
            return {"success": False, "error": f"Failed to index project: {str(e)}"}

    def get_or_create_project_id(self, project_name: str, project_path: Path) -> int:
        """Get existing project ID or create a new project and return its ID.

        Args:
            project_name: Name of the project
            project_path: Absolute path to the project directory

        Returns:
            Project ID (integer)

        Raises:
            Exception: If project creation fails
        """
        try:
            project_id = self.graph_ops.get_project_id_by_name(project_name)
            if project_id:
                logger.debug(
                    f"Found existing project '{project_name}' with ID {project_id}"
                )
                return project_id

            project_data = Project(
                id=0,  # Will be set by database
                name=project_name,
                path=str(project_path),
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            project_id = self.db_connection.insert_project(project_data)
            print(f"Created new project '{project_name}' with ID {project_id}")

            return project_id

        except Exception as e:
            logger.error(f"Error getting or creating project {project_name}: {e}")
            raise
