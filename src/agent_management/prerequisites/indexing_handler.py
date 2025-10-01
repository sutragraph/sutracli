"""
Prerequisites indexing handler for roadmap agent.
Handles incremental indexing of all projects before roadmap agent execution.
"""

import difflib
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from src.graph.graph_operations import GraphOperations
from src.graph.project_indexer import ProjectIndexer
from src.graph.sqlite_client import SQLiteConnection
from src.models.schema import Project
from src.utils.console import console


class IndexingPrerequisitesHandler:
    def __init__(self):
        """Initialize the indexing prerequisites handler."""
        self.connection = SQLiteConnection()
        self.graph_ops = GraphOperations()
        self.indexer = ProjectIndexer()
        logger.debug("🔧 IndexingPrerequisitesHandler initialized")

    def run_incremental_cross_indexing(self):
        """Run incremental cross-indexing with simplified checkpointing functionality."""
        console.print()
        console.info("Starting incremental cross-indexing")

        try:
            # 1. Load last checkpoint from incremental cross-indexing
            checkpoint = self.indexer._load_cross_indexing_checkpoint()

            # 2. Calculate diff between checkpoint and current state
            diff = self.indexer._create_diff_from_checkpoint(checkpoint)

            # 3. Process only the changed cross-references
            if diff["added"] or diff["modified"] or diff["deleted"]:
                total_to_process = len(diff["added"]) + len(diff["modified"])
                console.info(f"Processing {total_to_process} accumulated changes")
                console.dim(
                    "   • This includes all NET changes since last successful processing"
                )
                console.dim(
                    "   • Files changed multiple times between runs are processed once"
                )

                # Display detailed git-style diff
                self._display_detailed_diff(diff)

                # Display comprehensive summary
                self._display_diff_summary(diff)

                success = self.indexer._process_incremental_cross_indexing(diff)

                if success:
                    # 4. Reset checkpoint baseline to current state (clears the diff)
                    self.indexer._save_cross_indexing_checkpoint_reset_baseline()
                    console.success("Incremental cross-indexing completed successfully")
                    console.dim(
                        "   • Checkpoint baseline reset - next diff will start fresh"
                    )
                else:
                    console.error("Incremental cross-indexing failed during processing")
            else:
                console.info(
                    "No changes detected - skipping incremental cross-indexing"
                )

        except Exception as e:
            console.error(f"Error during incremental cross-indexing: {e}")

    def create_checkpoint_from_incremental_changes(self, changes_by_project):
        """Create checkpoint from actual incremental indexing changes."""
        try:
            total_changes = 0
            for project_id, changes in changes_by_project.items():
                if (
                    changes["changed_files"]
                    or changes["new_files"]
                    or changes["deleted_files"]
                ):
                    success = self.indexer.create_checkpoint_from_incremental_indexing(
                        changes, project_id
                    )
                    if success:
                        change_count = (
                            len(changes["changed_files"])
                            + len(changes["new_files"])
                            + len(changes["deleted_files"])
                        )
                        total_changes += change_count

            if total_changes > 0:
                console.success(f"Checkpoint created with {total_changes} changes")
                return True
            else:
                return True

        except Exception as e:
            console.error(f"Error creating checkpoint from changes: {e}")
            return False

    def _display_detailed_diff(self, diff):
        """Display detailed git-style diff information with line numbers."""
        console.print()
        console.print("[bold underline]📋 Detailed Changes[/bold underline]")
        console.print()

        # Display added files
        if diff["added"]:
            console.print(f"[success]➕ Added Files ({len(diff['added'])})[/success]")
            for file_key, file_data in diff["added"].items():
                panel = Panel(
                    self._build_added_summary(file_data),
                    title=f"📄 {file_key}",
                    title_align="left",
                    border_style="success",
                )
                console.print(panel)
                console.print()

        # Display modified files with detailed diffs
        if diff["modified"]:
            console.print(
                f"[warning]📝 Modified Files ({len(diff['modified'])})[/warning]"
            )
            for file_key, file_data in diff["modified"].items():
                baseline_content = file_data.get("baseline_content", "")
                current_content = file_data.get("current_content", "")

                if baseline_content and current_content:
                    baseline_lines = baseline_content.splitlines()
                    current_lines = current_content.splitlines()

                    # Generate unified diff
                    diff_lines = list(
                        difflib.unified_diff(
                            baseline_lines,
                            current_lines,
                            fromfile=f"a/{file_key}",
                            tofile=f"b/{file_key}",
                            lineterm="",
                            n=3,  # 3 lines of context
                        )
                    )

                    rendered_diff = self._render_diff_panel(file_key, diff_lines)
                    console.print(rendered_diff)
                else:
                    console.print(
                        Panel(
                            Text(
                                "Content changed (no baseline or current content available)",
                                style="dim",
                            ),
                            title=f"📄 {file_key}",
                            title_align="left",
                            border_style="warning",
                        )
                    )
                console.print()

        # Display deleted files
        if diff["deleted"]:
            console.print(f"[error]🗑️  Deleted Files ({len(diff['deleted'])})[/error]")
            for file_key, file_data in diff["deleted"].items():
                baseline_content = file_data.get("baseline_content", "")
                if baseline_content:
                    summary = self._build_deleted_summary(baseline_content)
                    console.print(
                        Panel(
                            summary,
                            title=f"📄 {file_key}",
                            title_align="left",
                            border_style="error",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            Text("File deleted", style="error"),
                            title=f"🗑️  {file_key}",
                            title_align="left",
                            border_style="error",
                        )
                    )
                console.print()

        console.print(Rule(style="dim"))
        console.print()

    def _build_added_summary(self, file_data: Dict[str, Any]) -> Text:
        """Summarize newly added file without dumping the entire content."""
        current_content = file_data.get("current_content", "")
        lines = current_content.splitlines()
        text = Text()
        text.append("File added", style="success")
        if lines:
            text.append(f" • {len(lines)} lines", style="dim")
        if file_data.get("sha"):
            text.append(f" • sha {file_data['sha'][:7]}", style="dim")
        return text if text.plain else Text("File added", style="success")

    @staticmethod
    def _build_diff_stats(diff_lines: List[str]) -> Table | None:
        """Construct a Rich table with diff statistics."""
        added_lines = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed_lines = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        if added_lines == 0 and removed_lines == 0:
            return None

        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        if added_lines:
            table.add_row(f"[success]＋ {added_lines} lines[/success]")
        if removed_lines:
            table.add_row(f"[error]－ {removed_lines} lines[/error]")
        return table

    @staticmethod
    def _build_deleted_summary(content: str) -> Text:
        """Summarize deleted file."""
        lines = content.splitlines()
        text = Text("File deleted", style="error")
        if lines:
            text.append(f" • {len(lines)} lines removed", style="dim")
        return text

    def _render_diff_panel(self, file_key: str, diff_lines: List[str]) -> Panel:
        diff_text = "\n".join(diff_lines)
        syntax = Syntax(
            diff_text,
            "diff",
            theme="github-dark",
            line_numbers=False,
            word_wrap=True,
        )
        stats = self._build_diff_stats(diff_text)
        renderable = Group(stats, syntax) if stats else syntax

        return Panel(
            renderable,
            title=f"📄 {file_key}",
            title_align="left",
            border_style="warning",
        )

    def _display_diff_summary(self, diff):
        """Display comprehensive summary of changes with statistics."""
        console.print("📊 Change Summary")
        console.print()

        total_files = len(diff["added"]) + len(diff["modified"]) + len(diff["deleted"])
        added_count = len(diff["added"])
        modified_count = len(diff["modified"])
        deleted_count = len(diff["deleted"])

        # Calculate line statistics
        total_lines_added = 0
        total_lines_removed = 0
        total_lines_modified = 0

        # Count lines in added files
        for file_data in diff["added"].values():
            content = file_data.get("current_content", "")
            if content:
                total_lines_added += len(content.splitlines())

        # Count lines in deleted files
        for file_data in diff["deleted"].values():
            content = file_data.get("baseline_content", "")
            if content:
                total_lines_removed += len(content.splitlines())

        # Count changed lines in modified files
        for file_data in diff["modified"].values():
            baseline_content = file_data.get("baseline_content", "")
            current_content = file_data.get("current_content", "")

            if baseline_content and current_content:
                baseline_lines = baseline_content.splitlines()
                current_lines = current_content.splitlines()

                diff_lines = list(
                    difflib.unified_diff(
                        baseline_lines,
                        current_lines,
                        lineterm="",
                        n=0,  # No context lines for counting
                    )
                )

                added_in_file = sum(
                    1
                    for line in diff_lines
                    if line.startswith("+") and not line.startswith("+++")
                )
                removed_in_file = sum(
                    1
                    for line in diff_lines
                    if line.startswith("-") and not line.startswith("---")
                )

                total_lines_added += added_in_file
                total_lines_removed += removed_in_file
                total_lines_modified += added_in_file + removed_in_file

        # Display file statistics
        console.print(f"   📁 Total files affected: {total_files}")
        if added_count > 0:
            console.print(f"   ➕ Files added: {added_count}")
        if modified_count > 0:
            console.print(f"   📝 Files modified: {modified_count}")
        if deleted_count > 0:
            console.print(f"   🗑️  Files deleted: {deleted_count}")

        console.print()

        # Display line statistics
        console.print("   📈 Line Changes:")
        if total_lines_added > 0:
            console.print(f"      +{total_lines_added} lines added")
        if total_lines_removed > 0:
            console.print(f"      -{total_lines_removed} lines removed")
        console.print()

        # Display change types summary
        if diff["added"] or diff["modified"] or diff["deleted"]:
            console.print("   🔄 Change Types:")

            if diff["added"]:
                sample_added = list(diff["added"].keys())[:3]
                if len(sample_added) == len(diff["added"]):
                    console.print(f"      ➕ New files: {', '.join(sample_added)}")
                else:
                    console.print(
                        f"      ➕ New files: {', '.join(sample_added)} "
                        f"and {len(diff['added']) - len(sample_added)} more"
                    )

            if diff["modified"]:
                sample_modified = list(diff["modified"].keys())[:3]
                if len(sample_modified) == len(diff["modified"]):
                    console.print(
                        f"      📝 Updated files: {', '.join(sample_modified)}"
                    )
                else:
                    console.print(
                        f"      📝 Updated files: {', '.join(sample_modified)} "
                        f"and {len(diff['modified']) - len(sample_modified)} more"
                    )

            if diff["deleted"]:
                sample_deleted = list(diff["deleted"].keys())[:3]
                if len(sample_deleted) == len(diff["deleted"]):
                    console.print(
                        f"      🗑️  Removed files: {', '.join(sample_deleted)}"
                    )
                else:
                    console.print(
                        f"      🗑️  Removed files: {', '.join(sample_deleted)} "
                        f"and {len(diff['deleted']) - len(sample_deleted)} more"
                    )

        console.print()
        console.print("═" * 60)
        console.print()

    def has_incremental_cross_indexing_changes(self) -> bool:
        """Check if there are changes for incremental cross-indexing without processing them."""
        try:
            # Load last checkpoint from incremental cross-indexing
            checkpoint = self.indexer._load_cross_indexing_checkpoint()

            # Calculate diff between checkpoint and current state
            diff = self.indexer._create_diff_from_checkpoint(checkpoint)

            # Check if there are any changes
            return bool(diff["added"] or diff["modified"] or diff["deleted"])

        except Exception as e:
            logger.debug(f"Error checking incremental cross-indexing changes: {e}")
            return True  # If we can't check, assume there are changes to be safe

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
                                "project_id": project.id,
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
                                "project_id": project.id,
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
                                "project_id": project.id,
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
                            "project_id": project.id,
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

    def handle_multiple_project_indexing_with_old_content(self) -> Dict[str, Any]:
        """
        Handle incremental indexing with old content fetching for checkpoint creation.

        This method:
        1. Identifies changes for each project
        2. Fetches old content from database before incremental indexing
        3. Runs incremental indexing
        4. Returns results with old/new content for checkpoint creation
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

                    # Step 1: Run incremental indexing (which detects changes internally)
                    indexing_result = self.indexer.incremental_index_project(
                        project.name
                    )

                    if indexing_result.get("status") == "success":
                        indexed_count += 1
                        changes = indexing_result.get(
                            "changes",
                            {
                                "changed_files": set(),
                                "new_files": set(),
                                "deleted_files": set(),
                            },
                        )

                        if not any(changes.values()):
                            # No changes detected
                            results.append(
                                {
                                    "project_id": project.id,
                                    "project_path": project.path,
                                    "status": "success",
                                    "changes": changes,
                                }
                            )
                            continue

                        # Step 2: Fetch old content for changed/deleted files after indexing
                        old_content = self._fetch_old_content_for_changes(
                            changes, project.name
                        )

                        # Add old content to the changes
                        enhanced_changes = dict(changes)
                        enhanced_changes["old_content"] = old_content

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

    def _fetch_old_content_for_changes(self, changes, project_name):
        """Fetch old content from database for changed and deleted files."""
        old_content = {}

        try:
            project = self.graph_ops.get_project_id_by_name(project_name)
            if not project:
                return old_content

            # Get old content for changed files
            for file_path in changes["changed_files"]:
                try:
                    content = self.indexer._get_file_content_before_changes(
                        str(file_path), project_name
                    )
                    old_content[str(file_path)] = content
                except Exception:
                    old_content[str(file_path)] = ""

            # Get old content for deleted files
            for file_path in changes["deleted_files"]:
                try:
                    content = self.indexer._get_file_content_before_changes(
                        str(file_path), project_name
                    )
                    old_content[str(file_path)] = content
                except Exception:
                    old_content[str(file_path)] = ""

        except Exception as e:
            logger.debug(f"Error fetching old content: {e}")

        return old_content

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
