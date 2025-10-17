import difflib
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from loguru import logger

from src.graph.graph_operations import GraphOperations
from src.graph.sqlite_client import SQLiteConnection
from src.queries.graph_queries import (
    DELETE_ALL_CHECKPOINTS,
    DELETE_CHECKPOINTS_BY_IDS,
    GET_ALL_CHECKPOINTS,
    GET_CONNECTIONS_BY_FILE_ID,
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
        """Load the checkpoint from incremental cross-indexing database."""

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
                self._cross_indexing.run_connection_matching()
            return True

        except Exception as e:
            console.error(f"Error during incremental cross-indexing: {e}")
            logger.exception(e)
            return False

    def _group_files_by_project(self, diff) -> Dict[int, Dict[str, Dict]]:
        """
        Group files by project_id from diff.
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
        """Clear checkpoint after successful incremental cross-indexing processing."""
        try:
            if checkpoint_ids:
                # Delete only the specific checkpoints that were used for indexing
                if len(checkpoint_ids) > 0:
                    placeholders = ",".join(["?"] * len(checkpoint_ids))
                    query = DELETE_CHECKPOINTS_BY_IDS.format(placeholders=placeholders)
                    self.connection.connection.execute(query, tuple(checkpoint_ids))
            else:
                # Delete all checkpoint entries from database
                self.connection.connection.execute(DELETE_ALL_CHECKPOINTS)

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

                # Read current content from database
                current_content = self._read_file_content_from_db(file_path)

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

                # Read new file content from database
                new_content = self._read_file_content_from_db(file_path)

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
                # Display comprehensive summary
                self._display_diff_summary(diff)

                success = self._process_incremental_cross_indexing(diff)

                if success:
                    # 4. Reset checkpoint baseline - delete only the checkpoints used in this run
                    self._save_cross_indexing_checkpoint_reset_baseline(checkpoint_ids)
                    console.print()
                    console.success("Incremental cross-indexing completed successfully")
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

    def _get_connections_for_file(
        self, file_id: int, connection_type: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get connections for a file.
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

    def _parse_diff_lines(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Parse diff between old and new content and create line mapping.
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
                    # Lines completely replaced - track BOTH old and new ranges
                    old_replaced_start = i1 + 1  # Convert to 1-based
                    old_replaced_end = i2  # Convert to 1-based
                    new_replaced_start = j1 + 1  # Convert to 1-based
                    new_replaced_end = j2  # Convert to 1-based
                    replaced_ranges.append(
                        (
                            old_replaced_start,
                            old_replaced_end,
                            new_replaced_start,
                            new_replaced_end,
                        )
                    )

                    logger.debug(
                        f"Content replaced in range {old_replaced_start}-{old_replaced_end}"
                    )

                    # Old lines in replaced range map to None (will be deleted)
                    for line_num in range(i1 + 1, i2 + 1):  # Convert to 1-based
                        line_mapping[line_num] = None
                        removed_lines.append(line_num)
                        logger.debug(
                            f"Replaced (removed) line {line_num}: {old_lines[line_num - 1].strip()}"
                        )

                    # Log new lines in replacement (handled by resplitting, NOT added to added_lines)
                    for line_num in range(j1 + 1, j2 + 1):  # Convert to 1-based
                        logger.debug(
                            f"Replaced (added) line {line_num}: {new_lines[line_num - 1].strip()}"
                        )
                    # NOTE: Replacement lines are NOT added to added_lines - they're handled by resplitting logic only

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
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Update connection records after file modifications using line mapping.
        """
        if not connections:
            return connections, []

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

            # First, collect all overlapping OR adjacent replacements to merge them
            # Adjacent replacements are likely part of the same logical change
            ADJACENCY_THRESHOLD = 3  # Lines within this distance are considered related
            overlapping_replacements = []

            for (
                old_replaced_start,
                old_replaced_end,
                new_replaced_start,
                new_replaced_end,
            ) in replaced_ranges:
                # Check if there's any overlap OR adjacency with this replaced range (using OLD line numbers)
                # This catches both direct overlaps and nearby replacements that are part of the same change
                if (
                    start_line <= old_replaced_end + ADJACENCY_THRESHOLD
                    and end_line >= old_replaced_start - ADJACENCY_THRESHOLD
                ):
                    overlapping_replacements.append(
                        (
                            old_replaced_start,
                            old_replaced_end,
                            new_replaced_start,
                            new_replaced_end,
                        )
                    )

            # If there are overlapping replacements, merge them and determine action
            if overlapping_replacements:
                # Find the min/max of all overlapping replacements (in NEW file coordinates)
                min_new_start = min(r[2] for r in overlapping_replacements)
                max_new_end = max(r[3] for r in overlapping_replacements)

                # Check old coordinates to determine overlap type
                min_old_start = min(r[0] for r in overlapping_replacements)
                max_old_end = max(r[1] for r in overlapping_replacements)

                if min_old_start <= start_line and max_old_end >= end_line:
                    # Case 1: Replacements completely cover connection
                    should_delete = True
                    needs_splitting_range = (
                        min_new_start,
                        max_new_end,
                        conn.get("description", ""),
                    )
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} completely covered by replacement(s) {min_old_start}-{max_old_end}"
                    )

                elif min_old_start < start_line or max_old_end > end_line:
                    # Case 2: Replacements extend beyond connection boundaries
                    # Map connection boundaries to new positions
                    should_delete = True

                    mapped_start = line_mapping.get(start_line)
                    mapped_end = line_mapping.get(end_line)

                    # Calculate extended range using NEW line numbers
                    if mapped_start is not None and mapped_end is not None:
                        extended_start = min(min_new_start, mapped_start)
                        extended_end = max(max_new_end, mapped_end)
                    elif mapped_start is not None:
                        extended_start = min(min_new_start, mapped_start)
                        extended_end = max_new_end
                    elif mapped_end is not None:
                        extended_start = min_new_start
                        extended_end = max(max_new_end, mapped_end)
                    else:
                        # Connection boundaries completely deleted, use merged replacement range
                        extended_start = min_new_start
                        extended_end = max_new_end

                    # Also check for adjacent added lines that should be included
                    # These are often part of the same logical change (e.g., new error handling)
                    added_lines_data = diff_data.get("added", [])
                    for added_line in added_lines_data:
                        # If added line is within or immediately after the extended range, include it
                        if (
                            extended_start
                            <= added_line
                            <= extended_end + ADJACENCY_THRESHOLD
                        ):
                            extended_end = max(extended_end, added_line)

                    needs_splitting_range = (
                        extended_start,
                        extended_end,
                        conn.get("description", ""),
                    )
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} extends beyond replacement(s) {min_old_start}-{max_old_end}, extended range: {extended_start}-{extended_end}"
                    )

                else:
                    # Case 3: Replacements are completely within connection
                    conn["needs_resplitting"] = True
                    conn["old_description"] = conn.get("description", "")
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} contains replacement(s) {min_old_start}-{max_old_end} - marking for resplitting due to code change"
                    )

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
                    # Store old code snippet before updating
                    conn["old_code_snippet"] = conn.get("code_snippet", "")
                    conn["start_line"] = new_start
                    conn["end_line"] = new_end
                    conn["needs_db_update"] = True
                    conn["needs_code_update"] = True
                    # Don't mark for resplitting yet - will check after code update
                    logger.debug(
                        f"  Updated connection {conn.get('id', 'unknown')}: {start_line}-{end_line} -> {new_start}-{new_end}"
                    )

        # Update code snippets for affected connections
        self._update_code_snippets(connections, updated_file_content, file_path)

        # Check if code actually changed for connections that were line-shifted
        # Only mark for resplitting if code content changed, not just line numbers
        for conn in connections:
            if conn.get("old_code_snippet") is not None and conn.get(
                "needs_code_update"
            ):
                old_code = conn.get("old_code_snippet", "").strip()
                new_code = conn.get("code_snippet", "").strip()

                if old_code != new_code:
                    # Code content actually changed - needs resplitting
                    conn["needs_resplitting"] = True
                    conn["old_description"] = conn.get("description", "")
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} code changed - marking for resplitting"
                    )
                else:
                    # Only line numbers changed, code is identical - just update DB
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} only line numbers changed - no resplitting needed"
                    )

                # Clean up temporary field
                del conn["old_code_snippet"]

        # Collect all connections that need resplitting (both overlapping and updated)
        connections_for_resplitting = []

        for conn in connections:
            # Case 1: Overlapping ranges - marked as deleted with splitting range
            if conn.get("is_deleted", False) and conn.get("needs_splitting", False):
                splitting_range = conn.get("splitting_range")
                if splitting_range:
                    start_line, end_line, old_description = splitting_range
                    connections_for_resplitting.append(
                        {
                            "id": conn.get("id"),
                            "direction": conn.get("direction"),
                            "start_line": start_line,
                            "end_line": end_line,
                            "old_description": old_description,
                        }
                    )
                    logger.debug(
                        f"  Connection {conn.get('id', 'unknown')} marked for resplitting (overlapping): lines {start_line}-{end_line}"
                    )

            # Case 2: Internal changes - marked for resplitting with updated range
            elif conn.get("needs_resplitting", False):
                connections_for_resplitting.append(
                    {
                        "id": conn.get("id"),
                        "direction": conn.get("direction"),
                        "start_line": conn.get("start_line"),
                        "end_line": conn.get("end_line"),
                        "old_description": conn.get("old_description", ""),
                    }
                )
                logger.debug(
                    f"  Connection {conn.get('id', 'unknown')} marked for resplitting (internal change): lines {conn.get('start_line')}-{conn.get('end_line')}"
                )

        # Filter out deleted connections and those marked for resplitting
        connections = [
            c
            for c in connections
            if not c.get("is_deleted", False) and not c.get("needs_resplitting", False)
        ]

        return connections, connections_for_resplitting

    def _delete_connections_from_db(self, connections_to_delete: List[Dict]) -> None:
        """
        Delete connections from database.
        """
        if not connections_to_delete:
            return

        for conn in connections_to_delete:
            table_name = (
                "incoming_connections"
                if conn["direction"] == "incoming"
                else "outgoing_connections"
            )
            query = f"DELETE FROM {table_name} WHERE id = ?"
            self.connection.connection.execute(query, (conn["id"],))
            logger.debug(f"  Deleted connection {conn['id']} from {table_name}")

        # Commit all deletions at once
        self.connection.connection.commit()
        logger.debug(
            f"  Committed deletion of {len(connections_to_delete)} connections"
        )

    def _prepare_connections_for_phase4(
        self,
        connections_for_resplitting: List[Dict],
        file_key: str,
        updated_connections: List[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Prepare connections for Phase 4 re-splitting.
        """
        snippet_infos = []

        for conn_info in connections_for_resplitting:
            start_line = conn_info["start_line"]
            end_line = conn_info["end_line"]
            old_description = conn_info["old_description"]

            # Create line range for phase 4 processing
            range_lines = list(range(start_line, end_line + 1))

            file_snippet_infos = self._handle_added_lines_collect(
                file_key,
                range_lines,
                updated_connections,
                old_description=old_description,
            )
            snippet_infos.extend(file_snippet_infos)

            logger.debug(
                f"  Prepared lines {start_line}-{end_line} for Phase 4 with old description"
            )

        return snippet_infos

    def _process_modified_files(
        self, modified_files: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process modified files using comprehensive database line number updating logic.
        """
        try:
            snippet_infos = []

            for file_key, file_data in modified_files.items():
                parts = file_key.split(":", 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid file_key format: {file_key}")
                    continue

                project_id = int(parts[0])
                file_path = parts[1]
                file_id = self._graph_ops._get_file_id_by_path(file_path)
                if not file_id:
                    console.warning(f"File ID not found for path: {file_path}")
                    continue

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
                            file_key,
                            added_lines,
                            [],  # No existing connections
                        )
                        snippet_infos.extend(file_snippet_infos)

                    continue

                # Parse diff to get line mapping and change info
                diff_data = self._parse_diff_lines(old_content, new_content)

                if not diff_data.get("line_mapping") and not diff_data.get("added"):
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
                    connections_for_resplitting,
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

                # Delete connections that were completely removed (no resplitting needed)
                if deleted_connections:
                    self._delete_connections_from_db(deleted_connections)

                # Delete connections that need resplitting and prepare for Phase 4
                if connections_for_resplitting:
                    # Delete old connections from database
                    self._delete_connections_from_db(connections_for_resplitting)

                    # Prepare for Phase 4 processing with old descriptions
                    resplit_snippet_infos = self._prepare_connections_for_phase4(
                        connections_for_resplitting,
                        file_key,
                        updated_connections,
                    )
                    snippet_infos.extend(resplit_snippet_infos)

                # Commit all database changes
                self.connection.connection.commit()

                # Identify new lines that need phase 4 processing
                # These are lines that were added but are not within any existing connection range
                # OR within connections marked for resplitting (to avoid duplicates)
                added_lines = diff_data.get("added", [])

                if added_lines:
                    # Filter out added lines that fall within updated connection ranges
                    # or within resplitting connection ranges
                    new_lines_for_phase4 = []
                    for line_num in added_lines:
                        is_within_existing = False

                        # Check against updated connections
                        for conn in updated_connections:
                            if not conn.get("is_deleted", False):
                                if conn["start_line"] <= line_num <= conn["end_line"]:
                                    is_within_existing = True
                                    logger.debug(
                                        f"  Skipping line {line_num} - within updated connection {conn['start_line']}-{conn['end_line']}"
                                    )
                                    break

                        # Also check against resplitting connections to avoid duplicates
                        if not is_within_existing:
                            for resplit_conn in connections_for_resplitting:
                                if (
                                    resplit_conn["start_line"]
                                    <= line_num
                                    <= resplit_conn["end_line"]
                                ):
                                    is_within_existing = True
                                    logger.debug(
                                        f"  Skipping line {line_num} - within resplitting connection {resplit_conn['start_line']}-{resplit_conn['end_line']}"
                                    )
                                    break

                        if not is_within_existing:
                            new_lines_for_phase4.append(line_num)

                    # Collect snippet info for new lines
                    if new_lines_for_phase4:
                        file_snippet_infos = self._handle_added_lines_collect(
                            file_key,
                            new_lines_for_phase4,
                            updated_connections,
                        )
                        snippet_infos.extend(file_snippet_infos)

            return snippet_infos

        except Exception as e:
            logger.error(f"Error processing modified files: {e}")
            self.connection.connection.rollback()
            raise

    def _handle_added_lines_collect(
        self,
        file_key: str,
        added_lines: List[int],
        connections: List[Dict],
        old_description: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Handle added lines by collecting snippet info for later batching.
        """
        try:
            if not added_lines:
                return []

            # Extract file path from file_key (format: "project_id:file_path")
            file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key

            added_lines_for_phase4 = []

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

                for start_line, end_line in line_ranges:
                    line_count = end_line - start_line + 1
                    snippet_infos.append(
                        {
                            "file_path": file_path,
                            "start_line": start_line,
                            "end_line": end_line,
                            "line_count": line_count,
                            "description": old_description,
                        }
                    )

            return snippet_infos

        except Exception as e:
            logger.error(f"Error collecting added lines: {e}")
            self.connection.connection.rollback()
            raise

    def _collect_new_files_info(
        self, added_files: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Collect info about new files for batching.
        """
        try:
            file_infos = []
            max_lines = CROSS_INDEXING_CONFIG["phase4_max_lines_per_batch"]

            for file_key, file_data in added_files.items():
                file_path = file_key.split(":", 1)[1] if ":" in file_key else file_key
                current_content = file_data.get("current_content", "")

                if not current_content:
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
                else:
                    # File is too large, split into chunks
                    num_chunks = (
                        line_count + max_lines - 1
                    ) // max_lines  # Ceiling division

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

            for batch_idx, batch in enumerate(batches, 1):
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

        except Exception as e:
            logger.error(f"Error running Phase 4 in batches: {e}")
            raise

    def _group_consecutive_lines(
        self, line_numbers: List[int]
    ) -> List[Tuple[int, int]]:
        """
        Group consecutive line numbers into ranges.
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
        """
        try:
            # Get code snippets context
            code_snippets_context = self._get_code_snippets_only_context()

            if not code_snippets_context or code_snippets_context.strip() == "":
                return

            # For incremental cross-indexing, include project description in context
            project_description = self._graph_ops.get_project_description(project_id)
            if project_description and project_description.strip():
                code_snippets_context = f"EXISTING PROJECT SUMMARY:\n{project_description}\n\nIMPORTANT NOTE: You are in incremental indexing mode. You need to update the summary and provide a new connection list if available. The above project summary is the current summary. After analyzing the new connection data below, determine if the current changes warrant an update to the project summary. If the changes add significant new functionality, architecture patterns, or integrations that aren't reflected in the current summary, provide an updated summary in the 'summary' field. If no significant updates are needed, you may leave the 'summary' field blank without any text.\n\nNOTE FOR CHANGED CONNECTIONS: Some code snippets below may include an 'Old Description' field. This is the previous description of the connection before the code was modified. When you see an 'Old Description', use it as reference context to understand what changed and provide an updated description that reflects the current state of the code. Analyze the differences between the old description and the new code to create an accurate, updated description.\n\nCODE SNIPPETS:\n{code_snippets_context}"

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
                snippet_text = (
                    f"File: {snippet.file_path}\n"
                    f"Lines: {snippet.start_line}-{snippet.end_line}\n"
                )

                # Include old description if present
                if hasattr(snippet, "description") and snippet.description:
                    snippet_text += f"Old Description: {snippet.description}\n"

                snippet_text += f"Code:\n{snippet.content}\n"
                formatted_snippets.append(snippet_text)

            return "\n".join(formatted_snippets)

        except Exception as e:
            logger.error(f"Error getting code snippets context: {e}")
            return ""

    def _read_file_content_from_db(self, file_path: str) -> str:
        """
        Read file content from database.
        """
        try:
            # Ensure graph_ops is initialized
            if self._graph_ops is None:
                self._initialize_cross_indexing_components()

            # Get file_id first using graph_operations
            file_id = self._graph_ops._get_file_id_by_path(str(file_path))
            if not file_id:
                logger.warning(f"File not found in database: {file_path}")
                return ""

            # Use graph_operations to get file content
            file_data = self._graph_ops.resolve_file(file_id)
            if not file_data:
                logger.warning(f"No file data found for file_id: {file_id}")
                return ""

            # Extract and return code content
            return file_data.get("content", "")

        except Exception as e:
            logger.warning(f"Error reading file from database: {file_path}, {e}")
            return ""
