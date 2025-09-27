"""
Prerequisites indexing handler for roadmap agent.
Handles incremental indexing of all projects before roadmap agent execution.
"""

import time
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.graph.project_indexer import ProjectIndexer
from src.graph.sqlite_client import SQLiteConnection
from src.models.schema import Project
from src.utils.console import console


class IndexingPrerequisitesHandler:
    """Handles incremental indexing of all projects as prerequisite for roadmap agent."""

    def __init__(self):
        """Initialize the indexing prerequisites handler."""
        self.connection = SQLiteConnection()
        self.indexer = ProjectIndexer()
        logger.debug("🔧 IndexingPrerequisitesHandler initialized")

    def execute_prerequisites(self) -> Dict[str, Any]:
        """
        Execute incremental indexing for all projects in the database.

        This method:
        1. Gets all projects from the database
        2. Performs incremental indexing on each project
        3. Returns statistics about the indexing operation

        Returns:
            Dictionary with indexing results and statistics
        """
        console.print("🔄 Starting incremental indexing prerequisites for roadmap agent")

        try:
            # Get all projects from database
            projects = self.connection.list_all_projects()

            if not projects:
                logger.warning(
                    "⚠️  No projects found in database - skipping indexing prerequisites"
                )
                return {
                    "status": "completed",
                    "total_projects": 0,
                    "indexed_projects": 0,
                    "failed_projects": 0,
                    "skipped_projects": 0,
                    "results": [],
                    "message": "No projects found to index",
                }

            logger.debug(f"📊 Found {len(projects)} projects to reindex")

            # Track results
            results = []
            indexed_count = 0
            failed_count = 0
            skipped_count = 0

            # Process each project
            for i, project in enumerate(projects, 1):
                logger.debug(
                    f"🔄 Processing project {i}/{len(projects)}: {project.name}"
                )

                try:
                    # Check if project directory exists
                    project_path = Path(project.path)
                    if not project_path.exists():
                        logger.warning(
                            f"⚠️  Project directory not found: {project.path} - skipping"
                        )
                        skipped_count += 1
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "skipped",
                                "reason": "Project directory not found",
                            }
                        )
                        continue

                    # Perform incremental indexing
                    start_time = time.time()
                    indexing_result = self.indexer.incremental_index_project(
                        project.name
                    )
                    duration = time.time() - start_time

                    if indexing_result.get("status") == "success":
                        indexed_count += 1
                        logger.debug(
                            f"✅ Successfully indexed {project.name} in {duration:.2f}s"
                        )
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "success",
                                "duration": duration,
                                "files_changed": indexing_result.get(
                                    "files_changed", 0
                                ),
                                "files_added": indexing_result.get("files_added", 0),
                                "files_deleted": indexing_result.get(
                                    "files_deleted", 0
                                ),
                            }
                        )
                    else:
                        failed_count += 1
                        error_msg = indexing_result.get("error", "Unknown error")
                        console.error(f"Failed to index {project.name}: {error_msg}")
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "failed",
                                "error": error_msg,
                            }
                        )

                except Exception as e:
                    failed_count += 1
                    console.error(f"Exception while indexing {project.name}: {e}")
                    results.append(
                        {
                            "project_name": project.name,
                            "project_path": project.path,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            # Log summary
            total_projects = len(projects)
            console.print(f"📊 Indexing prerequisites completed:")
            console.print(f"   Total projects: {total_projects}")
            console.print(f"   Successfully indexed: {indexed_count}")
            console.print(f"   Failed: {failed_count}")
            console.print(f"   Skipped: {skipped_count}")

            # Determine overall status
            if failed_count == 0 and skipped_count == 0:
                status = "completed"
                message = f"All {indexed_count} projects indexed successfully"
            elif indexed_count > 0:
                status = "partial"
                message = (
                    f"Indexed {indexed_count}/{total_projects} projects successfully"
                )
            else:
                status = "failed"
                message = "No projects were indexed successfully"

            return {
                "status": status,
                "total_projects": total_projects,
                "indexed_projects": indexed_count,
                "failed_projects": failed_count,
                "skipped_projects": skipped_count,
                "results": results,
                "message": message,
            }

        except Exception as e:
            console.error(f"Critical error during indexing prerequisites: {e}")
            return {
                "status": "error",
                "total_projects": 0,
                "indexed_projects": 0,
                "failed_projects": 0,
                "skipped_projects": 0,
                "results": [],
                "error": str(e),
                "message": f"Critical error during indexing prerequisites: {e}",
            }

    def handle_multiple_project_indexing(self, force: bool = False) -> Dict[str, Any]:
        """
        Handle incremental indexing for all projects in database.

        This method performs incremental indexing (only changed files) for all projects
        stored in the database. It checks for file changes and only processes what's new/modified.

        Args:
            force: Whether to force re-indexing (currently not used for incremental indexing)

        Returns:
            Dictionary with indexing results and statistics
        """
        try:
            # Get all projects from database
            projects = self.connection.list_all_projects()

            if not projects:
                logger.warning("⚠️  No projects found in database")
                return {
                    "status": "completed",
                    "total_projects": 0,
                    "indexed_projects": 0,
                    "failed_projects": 0,
                    "skipped_projects": 0,
                    "results": [],
                    "message": "No projects found to index",
                }

            logger.debug(f"📊 Found {len(projects)} projects for incremental indexing")

            # Track results
            results = []
            indexed_count = 0
            failed_count = 0
            skipped_count = 0

            # Process each project
            for i, project in enumerate(projects, 1):
                console.print()
                console.print(
                    f"📁 Processing project {i}/{len(projects)}: {project.name}"
                )

                try:
                    # Check if project directory exists
                    project_path = Path(project.path)
                    if not project_path.exists():
                        console.print(
                            f"⚠️  Project directory not found: {project.path} - skipping"
                        )
                        skipped_count += 1
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "skipped",
                                "reason": "Project directory not found",
                            }
                        )
                        continue

                    if not project_path.is_dir():
                        console.print(
                            f"⚠️  Project path is not a directory: {project.path} - skipping"
                        )
                        skipped_count += 1
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "skipped",
                                "reason": "Project path is not a directory",
                            }
                        )
                        continue

                    # Perform incremental indexing
                    start_time = time.time()
                    logger.debug(
                        f"🔄 Incremental indexing project '{project.name}' at: {project.path}"
                    )

                    indexing_result = self.indexer.incremental_index_project(
                        project.name
                    )
                    duration = time.time() - start_time

                    if indexing_result.get("status") == "success":
                        # Count all successful projects as indexed, regardless of changes
                        indexed_count += 1

                        # Check if there were actual changes for reporting
                        files_changed = indexing_result.get("files_changed", 0)
                        files_added = indexing_result.get("files_added", 0)
                        files_deleted = indexing_result.get("files_deleted", 0)

                        if files_changed + files_added + files_deleted > 0:
                            console.print(
                                f"✅ Changes detected and indexed: "
                                f"{files_changed} changed, {files_added} added, {files_deleted} deleted "
                                f"(completed in {duration:.2f}s)"
                            )
                        else:
                            console.print(
                                f"✅ No changes detected - project up to date "
                                f"(completed in {duration:.2f}s)"
                            )

                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "success",
                                "duration": duration,
                                "files_changed": files_changed,
                                "files_added": files_added,
                                "files_deleted": files_deleted,
                                "nodes_added": indexing_result.get("nodes_added", 0),
                                "nodes_deleted": indexing_result.get(
                                    "nodes_deleted", 0
                                ),
                            }
                        )
                    else:
                        failed_count += 1
                        error_msg = indexing_result.get("error", "Unknown error")
                        console.print(
                            f"❌ Failed to incrementally index project '{project.name}': {error_msg}"
                        )
                        results.append(
                            {
                                "project_name": project.name,
                                "project_path": project.path,
                                "status": "failed",
                                "error": error_msg,
                            }
                        )

                except Exception as e:
                    failed_count += 1
                    console.error(f"Exception while indexing {project.name}: {e}")
                    results.append(
                        {
                            "project_name": project.name,
                            "project_path": project.path,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            # Log summary
            total_projects = len(projects)
            console.print(f"\n📊 Incremental indexing completed:")
            console.print(f"   Total projects: {total_projects}")
            console.print(f"   Successfully processed: {indexed_count}")
            console.print(f"   Failed: {failed_count}")
            console.print(f"   Skipped: {skipped_count}")
            console.print()

            # Determine overall status
            if failed_count == 0 and skipped_count == 0:
                status = "completed"
                message = f"All {indexed_count} projects processed successfully\n"
            elif indexed_count > 0:
                status = "partial"
                message = f"Processed {indexed_count}/{total_projects} projects successfully\n"
            else:
                status = "failed" if failed_count > 0 else "skipped"
                message = "No projects were processed successfully\n"

            return {
                "status": status,
                "total_projects": total_projects,
                "indexed_projects": indexed_count,
                "failed_projects": failed_count,
                "skipped_projects": skipped_count,
                "results": results,
                "message": message,
            }

        except Exception as e:
            console.error(f"Critical error during incremental indexing: {e}")
            return {
                "status": "error",
                "total_projects": 0,
                "indexed_projects": 0,
                "failed_projects": 0,
                "skipped_projects": 0,
                "results": [],
                "error": str(e),
                "message": f"Critical error during incremental indexing: {e}",
            }

    def handle_single_project_indexing(
        self, project_path: str, project_name: str = None, force: bool = False
    ) -> Dict[str, Any]:
        """
        Handle CLI-style single project indexing.

        This method performs full project indexing for a specific project path,
        similar to the original handle_index_command function.

        Args:
            project_path: Path to the project directory
            project_name: Optional project name (auto-detected if not provided)
            force: Whether to force re-indexing if project already exists

        Returns:
            Dictionary with indexing results
        """
        try:
            from src.services.project_manager import ProjectManager

            # Initialize project manager
            project_manager = ProjectManager(self.connection)

            # Validate project path
            project_path_obj = Path(project_path).absolute()
            if not project_path_obj.exists():
                error_msg = f"Project path does not exist: {project_path_obj}"
                console.print(f"❌ {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "project_path": str(project_path_obj),
                }

            if not project_path_obj.is_dir():
                error_msg = f"Project path is not a directory: {project_path_obj}"
                console.print(f"❌ {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "project_path": str(project_path_obj),
                }

            # Determine project name if not provided
            if not project_name:
                project_name = project_manager.determine_project_name(project_path_obj)

            console.print(f"📁 Indexing project '{project_name}' at: {project_path_obj}")

            # Check if project already exists and handle force flag
            if self.connection.project_exists(project_name):
                if not force:
                    error_msg = f"Project '{project_name}' already exists in database. Use force=True to re-index"
                    console.print(f"⚠️  {error_msg}")
                    return {
                        "status": "skipped",
                        "project_name": project_name,
                        "project_path": str(project_path_obj),
                        "message": error_msg,
                    }
                else:
                    console.print(
                        f"🔄 Force re-indexing existing project '{project_name}'"
                    )
                    try:
                        delete_result = project_manager.delete_project(project_name)
                        if delete_result["success"]:
                            console.print(f"   ✅ Cleared existing project data")
                        else:
                            console.print(
                                f"   ⚠️  Warning: Could not clear existing data: {delete_result['error']}"
                            )
                    except Exception as e:
                        console.print(
                            f"   ⚠️  Warning: Could not clear existing data: {e}"
                        )

            # Perform the indexing
            start_time = time.time()
            result = project_manager.index_project_at_path(
                str(project_path_obj), project_name
            )
            duration = time.time() - start_time

            if result["success"]:
                success_msg = f"{result['message']} (completed in {duration:.2f}s)"
                console.print(f"✅ {success_msg}")
                return {
                    "status": "success",
                    "project_name": project_name,
                    "project_path": str(project_path_obj),
                    "duration": duration,
                    "message": success_msg,
                }
            else:
                error_msg = result.get("error", "Unknown error")
                console.print(f"❌ Failed to index project: {error_msg}")
                return {
                    "status": "failed",
                    "project_name": project_name,
                    "project_path": str(project_path_obj),
                    "error": error_msg,
                }

        except Exception as e:
            error_msg = f"Unexpected error during single project indexing: {e}"
            console.error(error_msg)
            logger.error(error_msg)
            return {
                "status": "error",
                "project_name": project_name,
                "project_path": project_path,
                "error": str(e),
                "message": error_msg,
            }

    def get_projects_requiring_indexing(self) -> List[Project]:
        """
        Get list of projects that may require indexing.

        Returns:
            List of Project objects from the database
        """
        try:
            projects = self.connection.list_all_projects()
            logger.debug(f"📊 Found {len(projects)} projects in database")
            return projects
        except Exception as e:
            console.error(f"Error getting projects: {e}")
            return []

    def validate_project_paths(self, projects: List[Project]) -> Dict[str, Any]:
        """
        Validate that project paths exist on filesystem.

        Args:
            projects: List of Project objects to validate

        Returns:
            Dictionary with validation results
        """
        valid_projects = []
        invalid_projects = []

        for project in projects:
            project_path = Path(project.path)
            if project_path.exists() and project_path.is_dir():
                valid_projects.append(project)
            else:
                invalid_projects.append(
                    {
                        "name": project.name,
                        "path": project.path,
                        "reason": "Directory not found or not a directory",
                    }
                )

        logger.debug(
            f"📊 Path validation: {len(valid_projects)} valid, {len(invalid_projects)} invalid"
        )

        return {
            "valid_projects": valid_projects,
            "invalid_projects": invalid_projects,
            "total_projects": len(projects),
        }
