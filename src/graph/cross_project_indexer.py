import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from src.graph.graph_operations import GraphOperations
from src.graph.sqlite_client import SQLiteConnection
from src.queries.graph_queries import (
    DELETE_ALL_CHECKPOINTS,
    DELETE_CHECKPOINTS_BY_IDS,
    DELETE_CONNECTIONS_BY_FILE_ID,
    GET_ALL_CHECKPOINTS,
    GET_CONNECTIONS_BY_FILE_ID,
    GET_FILE_ID_BY_PATH,
    INSERT_CHECKPOINT,
    UPDATE_CONNECTION_CODE_AND_LINES,
    UPDATE_CONNECTION_LINES,
)
from src.services.agent.session_management import SessionManager
from src.services.cross_indexing.core.cross_index_phase import CrossIndexing
from src.services.cross_indexing.core.cross_indexing_task_manager import (
    CrossIndexingTaskManager,
)
from src.tools.utils.constants import CROSS_INDEXING_CONFIG
from src.utils.console import console


class CrossProjectIndexer:
    def __init__(self):
        self.connection = SQLiteConnection()
        # Initialize cross-indexing components for incremental updates
        self._cross_indexing = None
        self._task_manager = None
        self._session_manager = None
        self._graph_ops = None

    def _initialize_cross_indexing_components(self):
        """Lazy initialization of cross-indexing components."""
        if self._cross_indexing is None:
            self._cross_indexing = CrossIndexing()
            self._task_manager = CrossIndexingTaskManager()
            self._session_manager = SessionManager()
            self._graph_ops = GraphOperations()

            # Set phase 4 directly (skip phases 1-3 for incremental updates)
            self._cross_indexing.current_phase = 4
            self._task_manager.set_current_phase(4)

    def _load_cross_indexing_checkpoint(self):
        """Load the checkpoint from incremental cross-indexing database.

        Returns tuple of (checkpoint_data, checkpoint_ids) where checkpoint_ids
        is the list of database IDs for the loaded checkpoints, used for selective deletion.
        """

        try:
            # Get all checkpoint changes from database
            checkpoint_results = self.connection.execute_query(GET_ALL_CHECKPOINTS)

            if not checkpoint_results:
                return None

            # Build changes dictionary from database results and track IDs
            changes = {}
            checkpoint_ids = []
            latest_timestamp = None

            for row in checkpoint_results:
                # Track checkpoint ID for selective deletion
                checkpoint_ids.append(row["id"])

                # Build file_key from project_id and file_path
                file_key = f"{row['project_id']}:{row['file_path']}"
                change_data = {
                    "change_type": row["change_type"],
                }

                if row["old_code"] is not None:
                    change_data["old_code"] = row["old_code"]
                if row["new_code"] is not None:
                    change_data["new_code"] = row["new_code"]

                changes[file_key] = change_data

                # Track latest timestamp
                if row["updated_at"]:
                    if latest_timestamp is None or row["updated_at"] > latest_timestamp:
                        latest_timestamp = row["updated_at"]

            # Build checkpoint data structure
            checkpoint_data = {
                "version": "1.0",
                "timestamp": latest_timestamp or datetime.now().isoformat(),
                "changes": changes,
                "checkpoint_ids": checkpoint_ids,  # Include IDs in checkpoint data
                "metadata": {
                    "total_changes": len(changes),
                    "created_by": "sutra_cli_incremental_cross_indexing",
                    "last_updated": latest_timestamp or datetime.now().isoformat(),
                },
            }

            return checkpoint_data

        except Exception as e:
            console.error(
                f"   • Unexpected error loading checkpoint from database: {e}"
            )
            return None

    def _process_incremental_cross_indexing(self, diff):
        """Process incremental cross-indexing with accumulated changes."""
        console.print(
            "📊 Processing accumulated changes for incremental cross-indexing:"
        )

        try:
            # Initialize cross-indexing components once
            self._initialize_cross_indexing_components()

            # Group files by project_id
            files_by_project = self._group_files_by_project(diff)

            if not files_by_project:
                console.warning("No files to process in diff")
                return False

            console.print(
                f"   • Processing changes across {len(files_by_project)} project(s)"
            )

            # Process each project separately
            for project_id, project_diff in files_by_project.items():
                console.print(f"\n📦 Processing Project ID: {project_id}")

                # Process deleted files
                deleted_files = project_diff.get("deleted", {})
                if deleted_files:
                    console.print(f"   🗑️  {len(deleted_files)} file(s) deleted")

                # Process modified files and collect snippet info (don't add to task_manager yet)
                modified_files = project_diff.get("modified", {})
                modified_snippet_infos = []
                if modified_files:
                    console.print(
                        f"   📝 Processing {len(modified_files)} modified files..."
                    )
                    modified_snippet_infos = self._process_modified_files(
                        modified_files
                    )

                # Process new files and collect file info
                added_files = project_diff.get("added", {})
                new_file_infos = []
                if added_files:
                    console.print(
                        f"   ➕ Collecting {len(added_files)} new files info..."
                    )
                    new_file_infos = self._collect_new_files_info(added_files)

                # Batch and run Phase 4 for all collected snippets
                total_snippets = len(modified_snippet_infos)
                total_files = len(new_file_infos)

                if total_snippets > 0 or total_files > 0:
                    self._run_phase_4_in_batches(
                        project_id,
                        modified_snippet_infos,
                        new_file_infos,
                    )

            # Run Phase 5 once at the end for all projects
            if files_by_project:
                console.print(f"\n🔗 Running Connection Matching for all projects...")
                self._cross_indexing.run_connection_matching()
            return True

        except Exception as e:
            console.error(f"Error during incremental cross-indexing: {e}")
            logger.exception(e)
            return False

    def _group_files_by_project(self, diff) -> Dict[int, Dict[str, Dict]]:
        """
        Group files by project_id from diff.

        Args:
            diff: Dictionary with 'deleted', 'modified', 'added' categories

        Returns:
            Dictionary mapping project_id to project-specific diff
            Format: {project_id: {'deleted': {}, 'modified': {}, 'added': {}}}
        """
        try:
            files_by_project = {}

            # Process each category (deleted, modified, added)
            for category in ["deleted", "modified", "added"]:
                files = diff.get(category, {})

                for file_key, file_data in files.items():
                    # Extract project_id from file_key (format: "project_id:file_path")
                    if ":" not in file_key:
                        logger.warning(
                            f"Invalid file_key format (missing project_id): {file_key}"
                        )
                        continue

                    try:
                        project_id = int(file_key.split(":", 1)[0])
                    except ValueError:
                        logger.warning(f"Invalid project_id in file_key: {file_key}")
                        continue

                    # Initialize project entry if needed
                    if project_id not in files_by_project:
                        files_by_project[project_id] = {
                            "deleted": {},
                            "modified": {},
                            "added": {},
                        }

                    # Add file to appropriate category for this project
                    files_by_project[project_id][category][file_key] = file_data

            return files_by_project

        except Exception as e:
            logger.error(f"Error grouping files by project: {e}")
            return {}

    def _save_cross_indexing_checkpoint_reset_baseline(self, checkpoint_ids=None):
        """Clear checkpoint after successful incremental cross-indexing processing.

        Args:
            checkpoint_ids: Optional list of specific checkpoint IDs to delete.
                          If None, deletes all checkpoints.
        """
        try:
            if checkpoint_ids:
                # Delete only the specific checkpoints that were used for indexing
                if len(checkpoint_ids) > 0:
                    placeholders = ",".join(["?"] * len(checkpoint_ids))
                    query = DELETE_CHECKPOINTS_BY_IDS.format(placeholders=placeholders)
                    self.connection.connection.execute(query, tuple(checkpoint_ids))
                    console.dim(
                        f"   • Deleted {len(checkpoint_ids)} processed checkpoint entries"
                    )
            else:
                # Delete all checkpoint entries from database
                self.connection.connection.execute(DELETE_ALL_CHECKPOINTS)
                console.dim("   • Deleted all checkpoint entries")

            self.connection.connection.commit()

            return True

        except Exception as e:
            console.error(f"   • Error clearing checkpoint from database: {e}")
            logger.exception(e)
            return False

    def _create_diff_from_checkpoint(self, checkpoint=None):
        """Create diff from checkpoint changes that only tracks actual file changes."""

        try:
            if checkpoint is None:
                console.dim("   • No checkpoint found, no accumulated changes")
                return {
                    "added": {},
                    "modified": {},
                    "deleted": {},
                    "accumulated_changes": {},
                }

            # Get tracked changes from checkpoint
            checkpoint_changes = checkpoint.get("changes", {})

            # Separate changes by type for the expected format
            added = {}
            modified = {}
            deleted = {}

            for file_key, change_data in checkpoint_changes.items():
                change_type = change_data.get("change_type")
                if change_type == "added":
                    added[file_key] = {
                        "change_type": "added",
                        "current_content": change_data.get("new_code", ""),
                    }
                elif change_type == "modified":
                    modified[file_key] = {
                        "change_type": "modified",
                        "baseline_content": change_data.get("old_code", ""),
                        "current_content": change_data.get("new_code", ""),
                    }
                elif change_type == "deleted":
                    deleted[file_key] = {
                        "change_type": "deleted",
                        "baseline_content": change_data.get("old_code", ""),
                    }

            return {
                "added": added,
                "modified": modified,
                "deleted": deleted,
                "accumulated_changes": checkpoint_changes,
            }

        except Exception as e:
            console.error(f"   • Error creating diff: {e}")
            return {
                "added": {},
                "modified": {},
                "deleted": {},
                "accumulated_changes": {},
            }

    def create_checkpoint_from_incremental_indexing(
        self, incremental_changes, project_id
    ):
        """Create or update checkpoint from actual incremental indexing changes."""

        try:
            # Load existing checkpoint
            checkpoint = self._load_cross_indexing_checkpoint()
            existing_changes = checkpoint.get("changes", {}) if checkpoint else {}

            # Get pre-fetched old content
            old_content = incremental_changes.get("old_content", {})

            # Process incremental indexing changes
            updated_changes = dict(existing_changes)  # Copy existing changes

            # Handle changed files (modified)
            for file_path in incremental_changes.get("changed_files", set()):
                file_key = f"{project_id}:{file_path}"

                # Read current content
                current_content = ""
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        current_content = f.read()
                except Exception:
                    current_content = ""

                if file_key in existing_changes:
                    # File was already changed, just update new_code, keep original old_code
                    updated_changes[file_key] = {
                        "change_type": "modified",
                        "old_code": existing_changes[file_key].get("old_code", ""),
                        "new_code": current_content,
                    }
                else:
                    # First time this file is changed, use pre-fetched old content
                    old_code = old_content.get(str(file_path), "")
                    updated_changes[file_key] = {
                        "change_type": "modified",
                        "old_code": old_code,
                        "new_code": current_content,
                    }

            # Handle new files (added)
            for file_path in incremental_changes.get("new_files", set()):
                file_key = f"{project_id}:{file_path}"

                # Read new file content
                new_content = ""
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        new_content = f.read()
                except Exception:
                    new_content = ""

                if file_key in existing_changes:
                    # Previously deleted file is now re-added, convert to modified
                    old_code = existing_changes[file_key].get("old_code", "")
                    updated_changes[file_key] = {
                        "change_type": "modified",
                        "old_code": old_code,
                        "new_code": new_content,
                    }
                else:
                    # Truly new file
                    updated_changes[file_key] = {
                        "change_type": "added",
                        "new_code": new_content,
                    }

            # Handle deleted files
            for file_path in incremental_changes.get("deleted_files", set()):
                file_key = f"{project_id}:{file_path}"

                if file_key in existing_changes:
                    # File was previously changed and now deleted
                    updated_changes[file_key] = {
                        "change_type": "deleted",
                        "old_code": existing_changes[file_key].get("old_code", ""),
                    }
                else:
                    # File was not in checkpoint, use pre-fetched old content
                    old_code = old_content.get(str(file_path), "")
                    updated_changes[file_key] = {
                        "change_type": "deleted",
                        "old_code": old_code,
                    }

            # Save updated checkpoint
            return self._save_checkpoint_with_changes(updated_changes)

        except Exception as e:
            console.error(
                f"   • Error creating checkpoint from incremental indexing: {e}"
            )
            return False

    def _save_checkpoint_with_changes(self, changes):
        """Save checkpoint with tracked file changes to database."""

        try:
            current_timestamp = datetime.now().isoformat()

            # Save each change to the checkpoints table
            cursor = self.connection.connection.cursor()

            for file_key, change_data in changes.items():
                # Parse file_key to get project_id and file_path
                parts = file_key.split(":", 1)
                if len(parts) == 2:
                    project_id = parts[0]
                    file_path = parts[1]
                else:
                    console.warning(f"   • Invalid file_key format: {file_key}")
                    continue

                change_type = change_data.get("change_type")
                old_code = change_data.get("old_code")
                new_code = change_data.get("new_code")

                # Insert or replace checkpoint entry
                cursor.execute(
                    INSERT_CHECKPOINT,
                    (
                        project_id,
                        file_path,
                        change_type,
                        old_code,
                        new_code,
                        current_timestamp,
                    ),
                )

            self.connection.connection.commit()

            return True

        except Exception as e:
            console.error(f"   • Error saving checkpoint to database: {e}")
            logger.exception(e)
            return False

    def run_incremental_cross_indexing(self):
        """Run incremental cross-indexing with simplified checkpointing functionality."""
        try:
            # 1. Load last checkpoint from incremental cross-indexing
            checkpoint = self._load_cross_indexing_checkpoint()

            # Extract checkpoint IDs for selective deletion after processing
            checkpoint_ids = checkpoint.get("checkpoint_ids", []) if checkpoint else []

            # 2. Calculate diff between checkpoint and current state
            diff = self._create_diff_from_checkpoint(checkpoint)

            # 3. Process only the changed cross-references
            if diff["added"] or diff["modified"] or diff["deleted"]:
                # Display detailed git-style diff
                # self._display_detailed_diff(diff)

                # Display comprehensive summary
                self._display_diff_summary(diff)

                success = self._process_incremental_cross_indexing(diff)

                if success:
                    # 4. Reset checkpoint baseline - delete only the checkpoints used in this run
                    self._save_cross_indexing_checkpoint_reset_baseline(checkpoint_ids)
                    console.success("Incremental cross-indexing completed successfully")
                    console.dim(
                        "   • Checkpoint baseline reset - processed entries cleared"
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
                    success = self.create_checkpoint_from_incremental_indexing(
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
        stats = self._build_diff_stats(diff_lines)
        renderable = Group(stats, syntax) if stats else syntax

        return Panel(
            renderable,
            title=f"📄 {file_key}",
            title_align="left",
            border_style="warning",
        )

    def _display_diff_summary(self, diff):
        """Display comprehensive summary of changes with statistics."""
        console.print()
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
            console.print(f"      [success]＋{total_lines_added} lines added[/success]")
        if total_lines_removed > 0:
            console.print(f"      [error]－{total_lines_removed} lines removed[error]")
        console.print()

    def has_incremental_cross_indexing_changes(self) -> bool:
        """Check if there are changes for incremental cross-indexing without processing them."""
        try:
            # Load last checkpoint from incremental cross-indexing
            checkpoint = self._load_cross_indexing_checkpoint()

            # Calculate diff between checkpoint and current state
            diff = self._create_diff_from_checkpoint(checkpoint)

            # Check if there are any changes
            return bool(diff["added"] or diff["modified"] or diff["deleted"])

        except Exception as e:
            logger.debug(f"Error checking incremental cross-indexing changes: {e}")
            return True  # If we can't check, assume there are changes to be safe

    # ========================================================================
    # Incremental Cross-Indexing Helper Methods
    # ========================================================================

    def _get_file_id_from_path(self, file_key: str) -> Optional[Tuple[int, int]]:
        """
        Get file_id and project_id from file_key.

        Args:
            file_key: Format "project_id:file_path"

        Returns:
            Tuple of (file_id, project_id) or None if not found
        """
        try:
            parts = file_key.split(":", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid file_key format: {file_key}")
                return None

            project_id = int(parts[0])
            file_path = parts[1]

            result = self.connection.execute_query(
                GET_FILE_ID_BY_PATH, (file_path, project_id)
            )

            if result and len(result) > 0:
                return result[0]["id"], project_id

            logger.warning(
                f"File not found in database: {file_path} (project: {project_id})"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting file_id from path {file_key}: {e}")
            return None

    def _get_connections_for_file(
        self, file_id: int, connection_type: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get connections for a file.

        Args:
            file_id: File ID to query
            connection_type: "incoming", "outgoing", or "both"

        Returns:
            List of connection dictionaries
        """
        try:
            connections = []

            if connection_type in ["incoming", "both"]:
                query = GET_CONNECTIONS_BY_FILE_ID.format(
                    table_name="incoming_connections"
                )
                incoming = self.connection.execute_query(query, (file_id,))
                for conn in incoming:
                    conn["direction"] = "incoming"
                    connections.append(conn)

            if connection_type in ["outgoing", "both"]:
                query = GET_CONNECTIONS_BY_FILE_ID.format(
                    table_name="outgoing_connections"
                )
                outgoing = self.connection.execute_query(query, (file_id,))
                for conn in outgoing:
                    conn["direction"] = "outgoing"
                    connections.append(conn)

            return connections

        except Exception as e:
            logger.error(f"Error getting connections for file {file_id}: {e}")
            return []

    def _delete_connections_for_file(self, file_id: int) -> int:
        """
        Delete all incoming and outgoing connections for a file.

        Args:
            file_id: File ID

        Returns:
            Number of connections deleted
        """
        try:
            deleted_count = 0

            # Delete incoming connections
            query_incoming = DELETE_CONNECTIONS_BY_FILE_ID.format(
                table_name="incoming_connections"
            )
            cursor = self.connection.connection.execute(query_incoming, (file_id,))
            deleted_count += cursor.rowcount

            # Delete outgoing connections
            query_outgoing = DELETE_CONNECTIONS_BY_FILE_ID.format(
                table_name="outgoing_connections"
            )
            cursor = self.connection.connection.execute(query_outgoing, (file_id,))
            deleted_count += cursor.rowcount

            self.connection.connection.commit()

            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting connections for file {file_id}: {e}")
            self.connection.connection.rollback()
            return 0

    def _parse_diff_lines(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Parse diff between old and new content and create line mapping.

        Args:
            old_content: Original content
            new_content: New content

        Returns:
            Dictionary with line mapping and change information
        """
        try:
            old_lines = old_content.splitlines() if old_content else []
            new_lines = new_content.splitlines() if new_content else []

            # Use SequenceMatcher for accurate line mapping
            matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

            # Create line mapping: old_line_number -> new_line_number (or None if deleted)
            line_mapping = {}
            added_lines = []
            removed_lines = []
            replaced_ranges = []  # Track ranges that were completely replaced

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    # Lines that stayed the same - create 1:1 mapping
                    for i in range(i2 - i1):
                        old_line = i1 + i + 1  # Convert to 1-based
                        new_line = j1 + i + 1  # Convert to 1-based
                        line_mapping[old_line] = new_line

                elif tag == "delete":
                    # Lines removed from old file - map to None
                    for line_num in range(i1 + 1, i2 + 1):  # Convert to 1-based
                        line_mapping[line_num] = None
                        removed_lines.append(line_num)
                        logger.debug(
                            f"Removed line {line_num}: {old_lines[line_num - 1].strip()}"
                        )

                elif tag == "insert":
                    # Lines added to new file - record for phase 4
                    for line_num in range(j1 + 1, j2 + 1):  # Convert to 1-based
                        added_lines.append(line_num)
                        logger.debug(
                            f"Added line {line_num}: {new_lines[line_num - 1].strip()}"
                        )

                elif tag == "replace":
                    # Lines completely replaced - track the replaced range
                    replaced_start = i1 + 1  # Convert to 1-based
                    replaced_end = i2  # Convert to 1-based
                    replaced_ranges.append((replaced_start, replaced_end))

                    logger.debug(
                        f"Content replaced in range {replaced_start}-{replaced_end}"
                    )

                    # Old lines in replaced range map to None (will be deleted)
                    for line_num in range(i1 + 1, i2 + 1):  # Convert to 1-based
                        line_mapping[line_num] = None
                        removed_lines.append(line_num)
                        logger.debug(
                            f"Replaced (removed) line {line_num}: {old_lines[line_num - 1].strip()}"
                        )

                    # New lines in replacement are recorded for phase 4
                    for line_num in range(j1 + 1, j2 + 1):  # Convert to 1-based
                        added_lines.append(line_num)
                        logger.debug(
                            f"Replaced (added) line {line_num}: {new_lines[line_num - 1].strip()}"
                        )

            logger.debug(
                f"Diff analysis: {len(removed_lines)} removed lines, {len(added_lines)} added lines, {len(replaced_ranges)} replaced ranges"
            )
            logger.debug(f"Created line mapping for {len(line_mapping)} old lines")
            logger.debug(f"Removed lines: {removed_lines}")
            logger.debug(f"Added lines: {added_lines}")
            logger.debug(f"Replaced ranges: {replaced_ranges}")

            return {
                "line_mapping": line_mapping,
                "added": added_lines,
                "removed": removed_lines,
                "replaced_ranges": replaced_ranges,
            }

        except Exception as e:
            logger.error(f"Error parsing diff: {e}")
            return {
                "line_mapping": {},
                "added": [],
                "removed": [],
                "replaced_ranges": [],
            }

    def _update_code_snippets(
        self, connections: List[Dict], file_content: str, file_path: str
    ):
        """
        Update code snippets for connections that need code updates.

        Args:
            connections: List of connections to update
            file_content: Updated file content
            file_path: File path for fetching code
        """
        for connection in connections:
            if connection.get("needs_code_update") and not connection.get("is_deleted"):
                # Fetch new code from file
                lines = file_content.split("\n")
                start = connection["start_line"] - 1  # Convert to 0-based index
                end = connection["end_line"]  # Exclusive upper bound

                if start >= 0 and start < len(lines) and end <= len(lines):
                    connection["code_snippet"] = "\n".join(lines[start:end])
                else:
                    # Handle edge case where line numbers are out of bounds
                    connection["code_snippet"] = ""

    def _update_connections_after_file_changes(
        self,
        connections: List[Dict],
        diff_data: Dict[str, Any],
        updated_file_content: str,
        file_path: str,
    ) -> List[Dict]:
        """
        Update connection records after file modifications using line mapping.
        """
        if not connections:
            return connections

        line_mapping = diff_data.get("line_mapping", {})
        replaced_ranges = diff_data.get("replaced_ranges", [])

        # Add tracking fields to connections
        for conn in connections:
            conn["needs_db_update"] = False
            conn["needs_code_update"] = False
            conn["is_deleted"] = False

        # Update each connection using line mapping
        for conn in connections:
            start_line = conn.get("start_line")
            end_line = conn.get("end_line")

            if start_line is None or end_line is None:
                continue

            logger.debug(
                f"Processing connection {conn.get('id', 'unknown')}: lines {start_line}-{end_line}"
            )

            # Check if connection needs to be deleted based on replacement boundaries
            should_delete = False
            needs_splitting_range = None

            for replaced_start, replaced_end in replaced_ranges:
                # Check if there's any overlap with this replaced range
                if start_line <= replaced_end and end_line >= replaced_start:
                    # There's overlap - now determine the action based on boundaries

                    if replaced_start <= start_line and replaced_end >= end_line:
                        # Case 1: Replacement completely covers connection (e.g., conn 5-10, replace 2-11)
                        # Action: Delete connection + send replacement range for splitting
                        should_delete = True
                        needs_splitting_range = (replaced_start, replaced_end)
                        logger.debug(
                            f"  Connection {conn.get('id', 'unknown')} completely covered by replacement {replaced_start}-{replaced_end}"
                        )
                        break

                    elif replaced_start < start_line or replaced_end > end_line:
                        # Case 2: Replacement extends beyond connection boundaries (e.g., conn 5-10, replace 3-7 or 8-12)
                        # Action: Delete connection + send extended range for splitting
                        should_delete = True
                        extended_start = min(replaced_start, start_line)
                        extended_end = max(replaced_end, end_line)
                        needs_splitting_range = (extended_start, extended_end)
                        logger.debug(
                            f"  Connection {conn.get('id', 'unknown')} extends beyond replacement {replaced_start}-{replaced_end}, extended range: {extended_start}-{extended_end}"
                        )
                        break

                    else:
                        # Case 3: Replacement is completely within connection (e.g., conn 5-10, replace 6-7)
                        # Action: Keep connection and update via line mapping
                        logger.debug(
                            f"  Connection {conn.get('id', 'unknown')} contains replacement {replaced_start}-{replaced_end} - keeping with line mapping"
                        )
                        # Continue to normal line mapping below

            if should_delete:
                conn["is_deleted"] = True
                conn["needs_db_update"] = True
                if needs_splitting_range:
                    conn["needs_splitting"] = True
                    conn["splitting_range"] = needs_splitting_range
                logger.debug(
                    f"  Connection {conn.get('id', 'unknown')} deleted due to boundary extension"
                )
                continue

            # Map the connection's line range using line mapping
            new_start = None
            new_end = None

            # Find the first valid mapped line (new start)
            for old_line in range(start_line, end_line + 1):
                if old_line in line_mapping and line_mapping[old_line] is not None:
                    new_start = line_mapping[old_line]
                    logger.debug(
                        f"  Found new start: old line {old_line} -> new line {new_start}"
                    )
                    break

            # Find the last valid mapped line (new end)
            for old_line in range(end_line, start_line - 1, -1):
                if old_line in line_mapping and line_mapping[old_line] is not None:
                    new_end = line_mapping[old_line]
                    logger.debug(
                        f"  Found new end: old line {old_line} -> new line {new_end}"
                    )
                    break

            if new_start is None or new_end is None:
                # Connection was completely deleted
                conn["is_deleted"] = True
                conn["needs_db_update"] = True
                logger.debug(
                    f"  Connection {conn.get('id', 'unknown')} completely deleted"
                )
            else:
                # Update line numbers if they changed
                if new_start != start_line or new_end != end_line:
                    conn["start_line"] = new_start
                    conn["end_line"] = new_end
                    conn["needs_db_update"] = True
                    conn["needs_code_update"] = True
                    logger.debug(
                        f"  Updated connection {conn.get('id', 'unknown')}: {start_line}-{end_line} -> {new_start}-{new_end}"
                    )

        # Update code snippets for affected connections
        self._update_code_snippets(connections, updated_file_content, file_path)

        # Collect splitting ranges from deleted connections that need splitting
        splitting_ranges = []
        for conn in connections:
            if conn.get("is_deleted", False) and conn.get("needs_splitting", False):
                splitting_range = conn.get("splitting_range")
                if splitting_range:
                    splitting_ranges.append(splitting_range)
                    logger.debug(
                        f"  Collected splitting range {splitting_range[0]}-{splitting_range[1]} from connection {conn.get('id', 'unknown')}"
                    )

        # Filter out deleted connections
        connections = [c for c in connections if not c.get("is_deleted", False)]

        return connections, splitting_ranges

    def _process_modified_files(
        self, modified_files: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process modified files using comprehensive database line number updating logic.

        This is the main entry point for processing file modifications. It replaces
        the previous simple line number updating approach with a comprehensive
        algorithm that handles all edge cases and maintains database consistency.

        ## Processing Steps:
        1. **No Connections**: If file has no existing connections, treat all changes as new
        2. **With Connections**: Apply comprehensive update algorithm
        3. **Database Updates**: Update connections with line/code changes transactionally
        4. **New Code Detection**: Identify added lines not within existing connections
        5. **Phase 4 Collection**: Collect snippet info for truly new code sections

        ## Database Operations:
        - **Code + Lines**: UPDATE with new code_snippet, start_line, end_line
        - **Lines Only**: UPDATE with new start_line, end_line
        - **Deletions**: DELETE completely removed connections
        - **Commits**: All changes committed transactionally

        ## Phase 4 Integration:
        - Only new code sections (not within existing connections) go to Phase 4
        - Existing connections are updated in-place without re-processing
        - Preserves existing connection relationships and metadata

        Args:
            modified_files: Dictionary of modified files from diff

        Returns:
            List of snippet info dictionaries for Phase 4 batching (new code only)
        """
        try:
            snippet_infos = []

            for file_key, file_data in modified_files.items():
                result = self._get_file_id_from_path(file_key)
                if not result:
                    continue

                file_id, project_id = result
                old_content = file_data.get("baseline_content", "")
                new_content = file_data.get("current_content", "")

                # Extract file path from file_key
                file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key

                # Get all existing connections for this file
                connections = self._get_connections_for_file(file_id)

                if not connections:
                    # No existing connections - treat all changes as new code for phase 4
                    diff_lines = self._parse_diff_lines(old_content, new_content)
                    added_lines = diff_lines.get("added", [])

                    if added_lines:
                        file_snippet_infos = self._handle_added_lines_collect(
                            file_id,
                            project_id,
                            file_key,
                            added_lines,
                            new_content,
                            [],  # No existing connections
                        )
                        snippet_infos.extend(file_snippet_infos)

                    console.dim(
                        f"      • No existing connections in {file_key}, collected {len(added_lines)} new lines"
                    )
                    continue

                # Parse diff to get line mapping and change info
                diff_data = self._parse_diff_lines(old_content, new_content)

                if not diff_data.get("line_mapping") and not diff_data.get("added"):
                    console.dim(f"      • No changes detected in {file_key}")
                    continue

                logger.debug(
                    f"Before updates - {len(connections)} connections in {file_key}"
                )
                for i, conn in enumerate(connections):
                    logger.debug(
                        f"  Connection {i}: {conn.get('id', 'unknown')} lines {conn.get('start_line')}-{conn.get('end_line')}"
                    )

                # Apply line mapping based connection updates
                (
                    updated_connections,
                    splitting_ranges,
                ) = self._update_connections_after_file_changes(
                    connections, diff_data, new_content, file_path
                )

                logger.debug(
                    f"After updates - {len(updated_connections)} connections in {file_key}"
                )
                for i, conn in enumerate(updated_connections):
                    if conn.get("is_deleted"):
                        logger.debug(
                            f"  Connection {i}: {conn.get('id', 'unknown')} DELETED"
                        )
                    else:
                        logger.debug(
                            f"  Connection {i}: {conn.get('id', 'unknown')} lines {conn.get('start_line')}-{conn.get('end_line')}"
                        )

                # Update database for modified connections
                connections_needing_update = [
                    c for c in updated_connections if c.get("needs_db_update")
                ]
                connections_needing_code_update = [
                    c for c in connections_needing_update if c.get("needs_code_update")
                ]
                connections_needing_lines_only = [
                    c
                    for c in connections_needing_update
                    if not c.get("needs_code_update")
                ]
                deleted_connections = [c for c in connections if c.get("is_deleted")]

                # Update connections with code + line changes
                if connections_needing_code_update:
                    for conn in connections_needing_code_update:
                        table_name = (
                            "incoming_connections"
                            if conn["direction"] == "incoming"
                            else "outgoing_connections"
                        )
                        query = UPDATE_CONNECTION_CODE_AND_LINES.format(
                            table_name=table_name
                        )
                        self.connection.connection.execute(
                            query,
                            (
                                conn.get("code_snippet", ""),
                                conn["start_line"],
                                conn["end_line"],
                                conn["id"],
                            ),
                        )

                    console.dim(
                        f"      • Updated {len(connections_needing_code_update)} connections (code + lines)"
                    )

                # Update connections with line-only changes
                if connections_needing_lines_only:
                    for conn in connections_needing_lines_only:
                        table_name = (
                            "incoming_connections"
                            if conn["direction"] == "incoming"
                            else "outgoing_connections"
                        )
                        query = UPDATE_CONNECTION_LINES.format(table_name=table_name)
                        self.connection.connection.execute(
                            query, (conn["start_line"], conn["end_line"], conn["id"])
                        )

                    console.dim(
                        f"      • Updated {len(connections_needing_lines_only)} connections (lines only)"
                    )

                # Delete connections that were completely removed
                if deleted_connections:
                    for conn in deleted_connections:
                        table_name = (
                            "incoming_connections"
                            if conn["direction"] == "incoming"
                            else "outgoing_connections"
                        )
                        query = f"DELETE FROM {table_name} WHERE id = ?"
                        self.connection.connection.execute(query, (conn["id"],))

                    console.dim(
                        f"      • Deleted {len(deleted_connections)} connections (completely removed)"
                    )

                # Commit database changes
                self.connection.connection.commit()

                # Identify new lines that need phase 4 processing
                # These are lines that were added but are not within any existing connection range
                added_lines = diff_data.get("added", [])

                if added_lines:
                    # Filter out added lines that fall within updated connection ranges
                    new_lines_for_phase4 = []
                    for line_num in added_lines:
                        is_within_existing = False
                        for conn in updated_connections:
                            if not conn.get("is_deleted", False):
                                if conn["start_line"] <= line_num <= conn["end_line"]:
                                    is_within_existing = True
                                    break

                        if not is_within_existing:
                            new_lines_for_phase4.append(line_num)

                    # Collect snippet info for new lines
                    if new_lines_for_phase4:
                        file_snippet_infos = self._handle_added_lines_collect(
                            file_id,
                            project_id,
                            file_key,
                            new_lines_for_phase4,
                            new_content,
                            updated_connections,
                        )
                        snippet_infos.extend(file_snippet_infos)

                        console.dim(
                            f"      • Collected {len(new_lines_for_phase4)} new lines for phase 4 processing"
                        )

                # Add splitting ranges to phase 4 processing
                if splitting_ranges:
                    for start_line, end_line in splitting_ranges:
                        # Add all lines in the splitting range for phase 4 processing
                        range_lines = list(range(start_line, end_line + 1))
                        file_snippet_infos = self._handle_added_lines_collect(
                            file_id,
                            project_id,
                            file_key,
                            range_lines,
                            new_content,
                            updated_connections,
                        )
                        snippet_infos.extend(file_snippet_infos)

                        console.dim(
                            f"      • Collected {len(range_lines)} lines from splitting range {start_line}-{end_line} for phase 4 processing"
                        )

                console.dim(f"      • Processed comprehensive updates for {file_key}")

            return snippet_infos

        except Exception as e:
            logger.error(f"Error processing modified files: {e}")
            self.connection.connection.rollback()
            raise

    def _handle_removed_lines(
        self,
        file_id: int,
        connections: List[Dict],
        removed_lines: List[int],
        old_content: str,
        new_content: str,
    ):
        """Handle connections affected by removed lines."""
        try:
            if not removed_lines:
                return

            min_removed = min(removed_lines)
            max_removed = max(removed_lines)
            num_removed = len(removed_lines)

            connections_to_delete = []
            connections_to_update_lines = []
            connections_to_update_code = []

            for conn in connections:
                start_line = conn.get("start_line")
                end_line = conn.get("end_line")

                if start_line is None or end_line is None:
                    continue

                # Check if removed lines are FROM the connection code (overlap)
                if start_line <= max_removed and end_line >= min_removed:
                    # Check if connection range is completely within removed range
                    if start_line >= min_removed and end_line <= max_removed:
                        # Entire connection is deleted - remove it
                        connections_to_delete.append(conn)
                    else:
                        # Partial overlap - removed lines are FROM connection code
                        # Update connection code and line numbers
                        new_start = start_line
                        new_end = end_line - num_removed

                        # Adjust if start is within removed range
                        if start_line >= min_removed and start_line <= max_removed:
                            new_start = min_removed

                        # Ensure valid range
                        if new_end >= new_start:
                            connections_to_update_code.append(
                                {
                                    "id": conn["id"],
                                    "direction": conn["direction"],
                                    "file_path": conn.get("file_path", ""),
                                    "new_start": new_start,
                                    "new_end": new_end,
                                }
                            )
                        else:
                            # Invalid range after removal - delete connection
                            connections_to_delete.append(conn)
                elif start_line > max_removed:
                    # Connection is after removed lines - update line numbers only
                    line_delta = -num_removed
                    connections_to_update_lines.append(
                        {
                            "id": conn["id"],
                            "direction": conn["direction"],
                            "new_start": start_line + line_delta,
                            "new_end": end_line + line_delta,
                        }
                    )

            # Delete connections completely in removed ranges
            for conn in connections_to_delete:
                table_name = (
                    "incoming_connections"
                    if conn["direction"] == "incoming"
                    else "outgoing_connections"
                )
                query = f"DELETE FROM {table_name} WHERE id = ?"
                self.connection.connection.execute(query, (conn["id"],))

            # Update connections with code changes (removed lines were FROM connection code)
            for update in connections_to_update_code:
                # Fetch updated code from file
                new_code = self._fetch_code_from_file(
                    update["file_path"], update["new_start"], update["new_end"]
                )

                if new_code:
                    table_name = (
                        "incoming_connections"
                        if update["direction"] == "incoming"
                        else "outgoing_connections"
                    )
                    query = UPDATE_CONNECTION_CODE_AND_LINES.format(
                        table_name=table_name
                    )
                    self.connection.connection.execute(
                        query,
                        (
                            new_code,
                            update["new_start"],
                            update["new_end"],
                            update["id"],
                        ),
                    )

            # Update line numbers for connections after removed lines
            for update in connections_to_update_lines:
                table_name = (
                    "incoming_connections"
                    if update["direction"] == "incoming"
                    else "outgoing_connections"
                )
                query = UPDATE_CONNECTION_LINES.format(table_name=table_name)
                self.connection.connection.execute(
                    query, (update["new_start"], update["new_end"], update["id"])
                )

            self.connection.connection.commit()

            if connections_to_delete:
                console.dim(
                    f"      • Deleted {len(connections_to_delete)} connections completely in removed ranges"
                )
            if connections_to_update_code:
                console.dim(
                    f"      • Updated {len(connections_to_update_code)} connections (code + lines) with removed lines FROM connection"
                )
            if connections_to_update_lines:
                console.dim(
                    f"      • Updated {len(connections_to_update_lines)} connections (lines only) after removed section"
                )

        except Exception as e:
            logger.error(f"Error handling removed lines: {e}")
            self.connection.connection.rollback()
            raise

    def _handle_added_lines_collect(
        self,
        file_id: int,
        project_id: int,
        file_key: str,
        added_lines: List[int],
        new_content: str,
        connections: List[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Handle added lines by collecting snippet info for later batching.

        Args:
            file_id: File ID
            project_id: Project ID
            file_key: File key (format: "project_id:file_path")
            added_lines: List of added line numbers
            new_content: New file content
            connections: Existing connections for the file

        Returns:
            List of snippet info dictionaries for batching
        """
        try:
            if not added_lines:
                return []

            min_added = min(added_lines)
            max_added = max(added_lines)
            num_added = len(added_lines)

            # Extract file path from file_key (format: "project_id:file_path")
            file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key

            connections_inside_existing = []  # Added lines INSIDE connection code
            connections_after_added = []  # Connections after added lines
            added_lines_for_phase4 = []  # Added lines NOT inside any connection
            # Note: Connections have already been updated with correct line numbers via line mapping
            # We only need to collect new lines that are not within existing connections for phase 4

            # Filter added lines to find those NOT within any existing connection
            for line_num in added_lines:
                is_within_existing = False
                for conn in connections:
                    conn_start = conn.get("start_line")
                    conn_end = conn.get("end_line")
                    if conn_start is not None and conn_end is not None:
                        if conn_start <= line_num <= conn_end:
                            is_within_existing = True
                            break

                if not is_within_existing:
                    added_lines_for_phase4.append(line_num)

            # Collect snippet info for added lines NOT inside any connection
            snippet_infos = []
            if added_lines_for_phase4:
                line_ranges = self._group_consecutive_lines(added_lines_for_phase4)

                console.dim(
                    f"         • Collected {len(added_lines_for_phase4)} new lines in {len(line_ranges)} ranges"
                )

                # Collect snippet info (don't add to task_manager yet)
                for start_line, end_line in line_ranges:
                    line_count = end_line - start_line + 1
                    snippet_infos.append(
                        {
                            "file_path": file_path,
                            "start_line": start_line,
                            "end_line": end_line,
                            "line_count": line_count,
                            "description": "",
                        }
                    )

            return snippet_infos

        except Exception as e:
            logger.error(f"Error collecting added lines: {e}")
            self.connection.connection.rollback()
            raise

    def _handle_added_lines(
        self,
        file_id: int,
        project_id: int,
        file_key: str,
        added_lines: List[int],
        new_content: str,
        run_cross_indexing: bool = True,
    ) -> int:
        """
        Handle added lines by updating existing connections or collecting snippets.

        Args:
            file_id: File ID
            project_id: Project ID
            file_key: File key (format: "project_id:file_path")
            added_lines: List of added line numbers
            new_content: New file content
            run_cross_indexing: If False, only collect snippets, don't run Phase 4

        Returns:
            Number of snippets collected for Phase 4
        """
        try:
            if not added_lines:
                return 0

            min_added = min(added_lines)
            max_added = max(added_lines)
            num_added = len(added_lines)

            # Extract file path from file_key (format: "project_id:file_path")
            file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key

            # Get existing connections for this file
            connections = self._get_connections_for_file(file_id)

            connections_inside_existing = []  # Added lines INSIDE connection code
            connections_after_added = (
                []
            )  # Connections after added lines (line number updates only)
            added_lines_for_phase4 = []  # Added lines NOT inside any connection

            # Categorize connections and added lines
            if connections:
                for conn in connections:
                    start_line = conn.get("start_line")
                    end_line = conn.get("end_line")

                    if start_line is None or end_line is None:
                        continue

                    # Check if added lines are INSIDE this connection range
                    if (
                        start_line <= min_added <= end_line
                        or start_line <= max_added <= end_line
                    ):
                        # Added lines are inside connection code - update code and lines
                        connections_inside_existing.append(
                            {
                                "id": conn["id"],
                                "direction": conn["direction"],
                                "file_path": file_path,
                                "old_start": start_line,
                                "old_end": end_line,
                                "new_start": start_line,
                                "new_end": end_line + num_added,
                            }
                        )
                    elif start_line > max_added:
                        # Connection is after added lines - update line numbers only
                        connections_after_added.append(
                            {
                                "id": conn["id"],
                                "direction": conn["direction"],
                                "new_start": start_line + num_added,
                                "new_end": end_line + num_added,
                            }
                        )

            # If added lines are NOT inside any connection, they go to phase 4
            if not connections_inside_existing:
                added_lines_for_phase4 = added_lines

            # Update connections where added lines are INSIDE connection code
            if connections_inside_existing:
                for update in connections_inside_existing:
                    # Fetch updated code from file with expanded range
                    new_code = self._fetch_code_from_file(
                        update["file_path"], update["new_start"], update["new_end"]
                    )

                    if new_code:
                        table_name = (
                            "incoming_connections"
                            if update["direction"] == "incoming"
                            else "outgoing_connections"
                        )
                        query = UPDATE_CONNECTION_CODE_AND_LINES.format(
                            table_name=table_name
                        )
                        self.connection.connection.execute(
                            query,
                            (
                                new_code,
                                update["new_start"],
                                update["new_end"],
                                update["id"],
                            ),
                        )

                self.connection.connection.commit()
                console.dim(
                    f"      • Updated {len(connections_inside_existing)} connections (code + lines) with added lines inside"
                )

            # Update connections that are after added lines (line numbers only)
            if connections_after_added:
                for update in connections_after_added:
                    table_name = (
                        "incoming_connections"
                        if update["direction"] == "incoming"
                        else "outgoing_connections"
                    )
                    query = UPDATE_CONNECTION_LINES.format(table_name=table_name)
                    self.connection.connection.execute(
                        query, (update["new_start"], update["new_end"], update["id"])
                    )

                self.connection.connection.commit()
                console.dim(
                    f"      • Updated {len(connections_after_added)} connections (lines only) after added section"
                )

            # Collect snippets for added lines NOT inside any connection
            snippets_added = 0
            if added_lines_for_phase4:
                line_ranges = self._group_consecutive_lines(added_lines_for_phase4)

                console.dim(
                    f"      • Detected {len(added_lines_for_phase4)} new lines in {len(line_ranges)} ranges (not inside existing connections)"
                )

                # Add code snippets for each added line range
                for start_line, end_line in line_ranges:
                    snippet_id = self._task_manager.add_code_snippet(
                        code_id="dummy_id",
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        description="",  # Empty as per requirement
                    )
                    if snippet_id:
                        snippets_added += 1

                if snippets_added > 0:
                    console.dim(
                        f"      • Collected {snippets_added} code snippets for Phase 4"
                    )

            return snippets_added

        except Exception as e:
            logger.error(f"Error handling added lines: {e}")
            self.connection.connection.rollback()
            raise

    def _collect_new_files_info(
        self, added_files: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Collect info about new files for batching.

        For files > 2000 lines: Split into 2000-line chunks
        For files <= 2000 lines: Add as-is (will be batched together)

        Args:
            added_files: Dictionary of added files from diff

        Returns:
            List of file info dictionaries for batching
        """
        try:
            file_infos = []
            max_lines = CROSS_INDEXING_CONFIG["phase4_max_lines_per_batch"]

            for file_key, file_data in added_files.items():
                file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key
                current_content = file_data.get("current_content", "")

                if not current_content:
                    console.dim(f"      • Skipping empty file: {file_key}")
                    continue

                # Get line count
                line_count = len(current_content.splitlines())

                if line_count <= max_lines:
                    # File is small enough, add as-is
                    file_infos.append(
                        {
                            "file_path": file_path,
                            "start_line": 1,
                            "end_line": line_count,
                            "line_count": line_count,
                            "description": "",
                        }
                    )
                    console.dim(
                        f"      • Collected file {file_key} ({line_count} lines)"
                    )
                else:
                    # File is too large, split into chunks
                    num_chunks = (
                        line_count + max_lines - 1
                    ) // max_lines  # Ceiling division
                    console.dim(
                        f"      • Splitting large file {file_key} ({line_count} lines) into {num_chunks} chunks"
                    )

                    for chunk_idx in range(num_chunks):
                        start_line = chunk_idx * max_lines + 1
                        end_line = min((chunk_idx + 1) * max_lines, line_count)
                        chunk_line_count = end_line - start_line + 1

                        file_infos.append(
                            {
                                "file_path": file_path,
                                "start_line": start_line,
                                "end_line": end_line,
                                "line_count": chunk_line_count,
                                "description": "",
                            }
                        )
                        console.dim(
                            f"         • Chunk {chunk_idx + 1}/{num_chunks}: lines {start_line}-{end_line} ({chunk_line_count} lines)"
                        )

            return file_infos

        except Exception as e:
            logger.error(f"Error collecting new files info: {e}")
            raise

    def _run_phase_4_in_batches(
        self,
        project_id: int,
        modified_snippet_infos: List[Dict[str, Any]],
        new_file_infos: List[Dict[str, Any]],
    ):
        """
        Run Phase 4 in batches respecting the line limit.

        Args:
            project_id: Project ID
            modified_snippet_infos: List of snippet info from modified files
            new_file_infos: List of file info from new files
        """
        try:
            max_lines = CROSS_INDEXING_CONFIG["phase4_max_lines_per_batch"]

            # Combine all snippet/file infos
            all_infos = modified_snippet_infos + new_file_infos

            if not all_infos:
                return

            # Create batches respecting line limit
            batches = []
            current_batch = []
            current_batch_lines = 0

            for info in all_infos:
                line_count = info["line_count"]

                # If adding this would exceed limit, start new batch
                if current_batch and (current_batch_lines + line_count > max_lines):
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_lines = 0

                current_batch.append(info)
                current_batch_lines += line_count

            # Add the last batch if not empty
            if current_batch:
                batches.append(current_batch)

            # Process each batch
            total_batches = len(batches)
            console.print(
                f"      • Created {total_batches} batch(es) with {max_lines} lines limit per batch"
            )

            for batch_idx, batch in enumerate(batches, 1):
                batch_line_count = sum(info["line_count"] for info in batch)
                console.print(
                    f"      • Processing batch {batch_idx}/{total_batches} ({len(batch)} items, {batch_line_count} lines)..."
                )

                # Add batch items to task_manager
                for info in batch:
                    self._task_manager.add_code_snippet(
                        code_id="dummy_id",
                        file_path=info["file_path"],
                        start_line=info["start_line"],
                        end_line=info["end_line"],
                        description=info["description"],
                    )

                # Run Phase 4 for this batch
                self._run_phase_4_with_incremental(project_id)

            console.dim(f"      • Completed Phase 4 for all {total_batches} batch(es)")

        except Exception as e:
            logger.error(f"Error running Phase 4 in batches: {e}")
            raise

    def _group_consecutive_lines(
        self, line_numbers: List[int]
    ) -> List[Tuple[int, int]]:
        """
        Group consecutive line numbers into ranges.

        Args:
            line_numbers: List of line numbers

        Returns:
            List of (start_line, end_line) tuples
        """
        if not line_numbers:
            return []

        sorted_lines = sorted(line_numbers)
        ranges = []
        start = sorted_lines[0]
        end = sorted_lines[0]

        for i in range(1, len(sorted_lines)):
            if sorted_lines[i] == end + 1:
                # Consecutive line, extend range
                end = sorted_lines[i]
            else:
                # Gap found, save current range and start new one
                ranges.append((start, end))
                start = sorted_lines[i]
                end = sorted_lines[i]

        # Add the last range
        ranges.append((start, end))

        return ranges

    def _run_phase_4_with_incremental(self, project_id: int):
        """
        Run Phase 4 (Data Splitting) and store connections.

        Args:
            project_id: Project ID for storing connections
        """
        try:
            # Get code snippets context
            code_snippets_context = self._get_code_snippets_only_context()

            if not code_snippets_context or code_snippets_context.strip() == "":
                console.dim("      • No code snippets to process")
                return

            # For incremental cross-indexing, include project description in context
            project_description = self._graph_ops.get_project_description(project_id)
            if project_description and project_description.strip():
                code_snippets_context = f"EXISTING PROJECT SUMMARY:\n{project_description}\n\nIMPORTANT NOTE: You are in incremental indexing mode. You need to update the summary and provide a new connection list if available. The above project summary is the current summary. After analyzing the new connection data below, determine if the current changes warrant an update to the project summary. If the changes add significant new functionality, architecture patterns, or integrations that aren't reflected in the current summary, provide an updated summary in the 'summary' field. If no significant updates are needed, you may leave the 'summary' field blank without any text.\n\nCODE SNIPPETS:\n{code_snippets_context}"

            # Run connection splitting
            splitting_result = self._cross_indexing.run_connection_splitting(
                code_snippets_context
            )

            if not splitting_result.get("success"):
                console.warning(
                    f"        Phase 4 failed: {splitting_result.get('error', 'Unknown error')}"
                )
                return

            # Get analysis result
            baml_analysis_result = splitting_result.get("results")

            if hasattr(baml_analysis_result, "model_dump"):
                analysis_result = baml_analysis_result.model_dump()
            elif isinstance(baml_analysis_result, dict):
                analysis_result = baml_analysis_result
            else:
                try:
                    analysis_result = json.loads(str(baml_analysis_result))
                except:
                    console.warning("       Could not parse Phase 4 results")
                    return

            # Store connections in database
            storage_result = self._graph_ops.store_connections_with_commit(
                project_id, analysis_result
            )

            if not storage_result.get("success"):
                console.warning(
                    f"       Connection storage failed: {storage_result.get('error', 'Unknown error')}"
                )
                return

            # Clear code snippets from memory after successful Phase 4
            self._task_manager.clear_code_snippets()
            console.dim("      • Connections stored and snippets cleared")

        except Exception as e:
            logger.error(f"Error running Phase 4: {e}")
            console.warning(f"       Error during Phase 4: {e}")

    def _get_code_snippets_only_context(self) -> str:
        """Get formatted code snippets context for Phase 4."""
        try:
            if not self._task_manager:
                return ""

            code_snippets = self._task_manager.get_all_code_snippets()

            if not code_snippets:
                return ""

            formatted_snippets = []
            for snippet in code_snippets.values():
                formatted_snippets.append(
                    f"File: {snippet.file_path}\n"
                    f"Lines: {snippet.start_line}-{snippet.end_line}\n"
                    f"Code:\n{snippet.content}\n"
                )

            return "\n".join(formatted_snippets)

        except Exception as e:
            logger.error(f"Error getting code snippets context: {e}")
            return ""

    def _fetch_code_from_file(
        self, file_path: str, start_line: int, end_line: int
    ) -> Optional[str]:
        """
        Fetch code from a file for a given line range.

        Args:
            file_path: Path to the file
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based, inclusive)

        Returns:
            Code content as string, or None if unable to fetch
        """
        try:
            # Handle absolute and relative paths
            path = Path(file_path)
            if not path.is_absolute():
                # Try to resolve relative path from workspace
                path = Path.cwd() / file_path

            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Convert to 0-based index
            start_idx = start_line - 1
            end_idx = end_line  # end_line is inclusive, so no -1

            # Validate line range
            if start_idx < 0 or end_idx > len(lines):
                logger.warning(
                    f"Invalid line range {start_line}-{end_line} for file with {len(lines)} lines: {file_path}"
                )
                return None

            # Extract and join lines
            code_lines = lines[start_idx:end_idx]
            return "".join(code_lines)

        except Exception as e:
            logger.error(
                f"Error fetching code from {file_path} lines {start_line}-{end_line}: {e}"
            )
            return None
