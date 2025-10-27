"""
Prerequisites indexing handler for roadmap agent.
Handles incremental indexing of all projects before roadmap agent execution.
"""

import time
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from rich.panel import Panel
from rich.prompt import Confirm

from agent_management.core.exceptions import UserCancelledError
from graph.cross_project_indexer import CrossProjectIndexer
from graph.graph_operations import GraphOperations
from graph.project_indexer import ProjectIndexer
from graph.sqlite_client import SQLiteConnection
from models.schema import Project
from utils.console import console


class IndexingPrerequisitesHandler:
    def __init__(self):
        """Initialize the indexing prerequisites handler."""
        self.connection = SQLiteConnection()
        self.graph_ops = GraphOperations()
        self.indexer = ProjectIndexer()
        self.cross_project_indexer = CrossProjectIndexer()
        logger.debug("🔧 IndexingPrerequisitesHandler initialized")

    def run_full_indexing(self, project_path: Path) -> None:
        """Run full indexing for a project."""
        from services.project_manager import ProjectManager

        project_manager = ProjectManager()

        console.print()
        console.info(f"Starting indexing for: {project_path}")
        console.dim("   • Analyzing code structure and relationships")
        console.dim("   • Generating embeddings for semantic search")
        console.print()

        try:
            project_name = project_manager.determine_project_name(project_path)

            # Check if project exists
            if not project_manager.check_project_exists(project_name):
                # Full indexing needed
                project_manager.auto_index_project(project_name, project_path)
                console.success("Indexing completed successfully!")
            else:
                logger.debug(f"Project {project_name} already indexed")

        except Exception as e:
            console.error(f"Indexing failed: {e}")
            raise

    def run_single_project_incremental_indexing(
        self, project_path: Path
    ) -> Dict[str, Any]:
        """Run incremental indexing for a single project and return changes."""
        from services.project_manager import ProjectManager

        project_manager = ProjectManager()

        console.print()
        console.info("Running incremental indexing for current project")

        try:
            project_name = project_manager.determine_project_name(project_path)
            result = project_manager.perform_incremental_indexing(project_name)

            if result.get("type") == "indexing_complete":
                stats = result.get("stats", {})
                changes = stats.get("changes", {})

                console.success("Incremental indexing completed!")
                return changes
            else:
                console.warning("No changes detected")
                return {}

        except Exception as e:
            console.error(f"Incremental indexing failed: {e}")
            return {}

    def run_multi_project_incremental_indexing(self) -> Dict[str, Any]:
        """Run incremental indexing for all projects and return changes by project."""
        console.print()
        console.info("Starting incremental indexing for all projects")

        try:
            result = self.handle_multiple_project_indexing_with_old_content()

            changes_by_project = {}

            if result["status"] in ["completed", "partial"]:
                if "results" in result:
                    for project_info in result["results"]:
                        if (
                            isinstance(project_info, dict)
                            and project_info.get("status") == "success"
                        ):
                            project_id = project_info.get("project_id")
                            changes = project_info.get("changes", {})
                            if changes:
                                changes_by_project[str(project_id)] = changes

                console.success(
                    f"Incremental indexing completed for {result['indexed_count']} projects"
                )
            elif result["status"] == "skipped":
                console.info("No changes detected for incremental indexing")
            else:
                console.error(f"Incremental indexing failed: {result.get('message')}")
                if result.get("error"):
                    console.print(f"   Error: {result['error']}")

            return changes_by_project

        except Exception as e:
            console.error(f"Error during incremental indexing: {e}")
            return {}

    def run_cross_indexing(self, project_path: Path) -> None:
        """Run cross-indexing for the project."""
        from services.project_manager import ProjectManager

        project_manager = ProjectManager()

        # Check if cross-indexing is already completed
        try:
            project_name = project_manager.determine_project_name(project_path)

            if self.graph_ops.is_cross_indexing_done(project_name):
                logger.debug(
                    f"Cross-indexing already completed for project {project_name}"
                )
                return

        except Exception as e:
            logger.debug(f"Could not verify cross-indexing status: {e}")

        warning_text = """
• ⏱️  Time: May take 5-30 minutes based on codebase size
• 🔥 Tokens: Will consume LLM tokens for deep analysis
• 🔄 Process: This is a one-time setup for this project
• 💻 Session: Do not close the terminal during this process

This analysis will create detailed inter-service connection mappings
for advanced code understanding and agent capabilities.
Closing the terminal or interrupting may lead to incomplete data and token wastage.
        """

        warning_panel = Panel(
            warning_text.strip(),
            title="⚠️  Cross-Indexing Analysis",
            border_style="yellow",
            title_align="left",
        )

        console.print()
        console.print(warning_panel)
        console.print()

        # Ask for user confirmation
        proceed = Confirm.ask(
            "[bold yellow]Do you want to proceed with cross-indexing analysis?[/bold yellow]",
            default=True,
        )

        if not proceed:
            console.warning("Cross-indexing declined by user.")
            console.dim(
                "💡 Tip: You can run this later when you're ready to spend the time and tokens."
            )
            console.dim("📝 To continue later, simply run the same command again.")

            raise UserCancelledError("User declined cross-indexing analysis")

        console.process("Starting cross-indexing analysis...")

        try:
            from cli.commands import handle_cross_indexing_command

            # Mock args object for cross-indexing
            class Args:
                directory = str(project_path)
                project_name = None
                log_level = "INFO"
                auto = False

            args = Args()
            handle_cross_indexing_command(args)

            console.success("Cross-indexing completed successfully!")

        except Exception as e:
            console.error(f"Cross-indexing failed: {e}")

    def handle_multiple_project_indexing_with_old_content(self) -> Dict[str, Any]:
        """
        Handle incremental indexing for all projects.

        This method:
        1. Gets all projects from database
        2. Runs incremental indexing for each project
        3. Returns results with changes and diffs (fetched internally by incremental_index_project)

        Note: The incremental_index_project method now handles:
        - Detecting changes
        - Fetching old content from database before updating
        - Generating diffs
        """
        try:
            # Get all projects from database
            projects = self.connection.list_all_projects()

            if not projects:
                return {
                    "status": "completed",
                    "total_projects": 0,
                    "indexed_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "results": [],
                    "message": "No projects found to index",
                }

            # Track results
            results = []
            indexed_count = 0
            failed_count = 0
            skipped_count = 0

            # Process each project
            for project in projects:
                try:
                    # Check if project directory exists
                    project_path = Path(project.path)
                    if not project_path.exists() or not project_path.is_dir():
                        skipped_count += 1
                        results.append(
                            {
                                "project_id": project.id,
                                "project_path": project.path,
                                "status": "skipped",
                                "reason": "Project directory not found",
                            }
                        )
                        continue

                    # Run incremental indexing (which now handles change detection,
                    # old content fetching, and diff generation internally)
                    indexing_result = self.indexer.incremental_index_project(
                        project.name
                    )

                    if indexing_result.get("status") == "success":
                        indexed_count += 1

                        # Enhance changes with old_content like the old code
                        enhanced_changes = dict(indexing_result.get("changes", {}))
                        enhanced_changes["old_content"] = indexing_result.get(
                            "old_content", {}
                        )

                        results.append(
                            {
                                "project_id": project.id,
                                "project_path": project.path,
                                "status": "success",
                                "changes": enhanced_changes,
                            }
                        )
                    else:
                        failed_count += 1
                        results.append(
                            {
                                "project_id": project.id,
                                "project_path": project.path,
                                "status": "failed",
                                "error": indexing_result.get("error", "Unknown error"),
                            }
                        )

                except Exception as e:
                    failed_count += 1
                    results.append(
                        {
                            "project_id": project.id,
                            "project_path": project.path,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            # Determine overall status
            if failed_count == 0 and skipped_count == 0:
                status = "completed"
            elif indexed_count > 0:
                status = "partial"
            else:
                status = "failed" if failed_count > 0 else "skipped"

            return {
                "status": status,
                "total_projects": len(projects),
                "indexed_count": indexed_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "results": results,
                "message": f"Processed {indexed_count}/{len(projects)} projects",
            }

        except Exception as e:
            return {
                "status": "error",
                "indexed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "results": [],
                "error": str(e),
                "message": f"Critical error: {e}",
            }

    def handle_single_project_indexing(
        self, project_path: str, project_name: str = "", force: bool = False
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
            project_manager = ProjectManager()

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
                console.success(f"{success_msg}")
                return {
                    "status": "success",
                    "project_name": project_name,
                    "project_path": str(project_path_obj),
                    "duration": duration,
                    "message": success_msg,
                }
            else:
                error_msg = result.get("error", "Unknown error")
                console.error(f"Failed to index project: {error_msg}")
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

    def run_incremental_cross_indexing(self, changes_by_project: Dict[str, Any]):
        # Create checkpoint from actual incremental indexing changes
        self.cross_project_indexer.create_checkpoint_from_incremental_changes(
            changes_by_project
        )

        # Check if there are changes for incremental cross-indexing
        if self.cross_project_indexer.has_incremental_cross_indexing_changes():
            # Show informative panel about detected changes
            console.print()
            change_info = """
[bold]Incremental Cross-Indexing:[/bold] Analyzes relationships between your
modified code components and updates service connection mappings.

⚠️  [bold]Will consume LLM tokens[/bold]

✅ [bold]Run if:[/bold] You're confident with your changes and want agents to understand them
❌ [dim]Skip if:[/dim] Still making changes or want to save tokens for later
            """

            info_panel = Panel(
                change_info.strip(),
                title=f"🔍 [bold]Code Changes Detected![bold]",
                border_style="blue",
                title_align="left",
            )
            console.print(info_panel)
            console.print()

            # Prompt for incremental cross-indexing after incremental indexing
            if Confirm.ask(
                "⚡ Run incremental cross-indexing before running the agent?",
                default=False,
            ):
                console.print()
                console.process("Starting incremental cross-indexing analysis...")
                self.cross_project_indexer.run_incremental_cross_indexing()
            else:
                console.print()
                console.info("⏭️  Skipping incremental cross-indexing")
                console.dim("   • You can run this later when you're ready")
                console.dim(
                    "   • Your changes are saved and will be analyzed next time"
                )
        else:
            # No changes detected, skip silently
            console.info("No changes detected for incremental cross-indexing")
            console.dim("   • Skipping incremental cross-indexing")
