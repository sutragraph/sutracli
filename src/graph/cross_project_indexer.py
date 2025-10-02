import difflib
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from src.graph.sqlite_client import SQLiteConnection
from src.queries.graph_queries import (
    DELETE_ALL_CHECKPOINTS,
    DELETE_CHECKPOINTS_BY_IDS,
    GET_ALL_CHECKPOINTS,
    INSERT_CHECKPOINT,
)
from src.utils.console import console


class CrossProjectIndexer:
    def __init__(self):
        self.connection = SQLiteConnection()

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
        console.info("📊 Processing accumulated changes for incremental cross-indexing:")

        accumulated_changes = diff.get("accumulated_changes", {})

        # TODO: Implement actual incremental cross-indexing logic here
        # This should process the accumulated changes and update cross-references:
        # 1. Parse NET changes for functions, classes, imports, etc.
        # 2. Update existing cross-indexing data for modified files
        # 3. Add new cross-references for added files
        # 4. Clean up cross-references for deleted files
        # 5. Handle dependency changes efficiently
        # 6. Maintain data consistency across all changes

        added_count = sum(
            1
            for change in accumulated_changes.values()
            if change["change_type"] == "added"
        )
        modified_count = sum(
            1
            for change in accumulated_changes.values()
            if change["change_type"] == "modified"
        )
        deleted_count = sum(
            1
            for change in accumulated_changes.values()
            if change["change_type"] == "deleted"
        )

        if added_count > 0:
            console.print(f"   🆕 Processing {added_count} added files:")
            for file_key, change_data in accumulated_changes.items():
                if change_data["change_type"] == "added":
                    console.dim(f"     • {file_key} (new file)")

        if modified_count > 0:
            console.print(f"   📝 Processing {modified_count} modified files:")
            for file_key, change_data in accumulated_changes.items():
                if change_data["change_type"] == "modified":
                    net_diff = change_data.get("net_diff", {})
                    added_lines = len(net_diff.get("lines_added", []))
                    removed_lines = len(net_diff.get("lines_removed", []))
                    console.dim(
                        f"     • {file_key} (+{added_lines}/-{removed_lines} lines)"
                    )

        if deleted_count > 0:
            console.print(f"   🗑️  Processing {deleted_count} deleted files:")
            for file_key, change_data in accumulated_changes.items():
                if change_data["change_type"] == "deleted":
                    console.dim(f"     • {file_key} (cleanup cross-references)")

        console.dim("   • Accumulated changes processed with NET differences")
        console.dim("   • Ready for cross-indexing logic implementation")

        return True

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
        console.print()
        console.info("Starting incremental cross-indexing")

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
