"""Incremental indexing for efficient database updates when code changes."""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from loguru import logger

from ..graph.sqlite_client import SQLiteConnection, GraphOperations
from ..graph.converter import TreeSitterToSQLiteConverter
from ..processors.data_processor import GraphDataProcessor
from ..models.schema import ParsedCodebase, GraphData
from ..utils.helpers import load_json_file
from ..parser.analyzer.analyzer import Analyzer
from ..config.settings import config


class IncrementalIndexing:
    """Handles incremental indexing of code changes to update the database efficiently."""

    def __init__(self, sqlite_connection: Optional[SQLiteConnection] = None):
        """Initialize with optional connection."""
        self.connection = sqlite_connection or SQLiteConnection()
        self.converter = TreeSitterToSQLiteConverter(self.connection)
        self.processor = GraphDataProcessor(self.connection)
        self.graphOperations = GraphOperations(self.connection)
        logger.debug("🔄 IncrementalIndexing initialized")

    def reindex_database(self, project_name: str) -> Dict[str, Any]:
        """Update database with changes from new parser output.

        Args:
            project_name: Name of the project/codebase

        Returns:
            Dictionary with update statistics
        """
        logger.debug(f"🔄 Starting incremental update for project: {project_name}")

        try:
            # Get project ID
            project_id = self._get_project_id(project_name)
            if not project_id:
                logger.error(f"Project '{project_name}' not found in database")
                return {
                    "status": "failed",
                    "error": f"Project '{project_name}' not found",
                }

            # Create analyzer - no need for start_node_id with deterministic IDs
            analyzer = Analyzer(repo_id=project_id)

            # Determine the correct directory to analyze from existing file paths
            project_dir = self._get_project_directory(project_id)
            if not project_dir:
                logger.error(
                    f"Could not determine project directory for project {project_name}"
                )
                return {
                    "status": "failed",
                    "error": "Could not determine project directory",
                }

            logger.debug(f"🔄 Analyzing project directory: {project_dir}")

            # Run the async analyze_and_save method using configured parser results directory
            json_file_path = asyncio.run(
                analyzer.analyze_and_save(
                    directory_path=project_dir,
                    results_folder=config.storage.parser_results_dir,
                )
            )

            # Load and parse JSON data
            logger.debug(f"📦 Loading JSON data from {json_file_path}")
            json_data = load_json_file(json_file_path)

            parsed_data = self.converter._parse_json_data(
                json_data, project_name, json_file_path
            )

            # Compare file hashes and identify changes
            changes = self._identify_changes(parsed_data, project_id)

            # Process changes
            stats = self._process_changes(
                changes, parsed_data, project_id, project_name
            )

            logger.debug("🔢 Creating database indexes...")
            self.connection.create_indexes()

            logger.debug(f"✅ Incremental update completed successfully!")
            return {
                "status": "success",
                "input_file": json_file_path,
                "files_changed": len(changes["changed_files"]),
                "files_added": len(changes["new_files"]),
                "files_deleted": len(changes["deleted_files"]),
                "nodes_deleted": stats["nodes_deleted"],
                "relationships_deleted": stats["relationships_deleted"],
                "nodes_added": stats["nodes_added"],
                "relationships_added": stats["relationships_added"],
            }

        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return {"status": "failed", "error": str(e), "input_file": json_file_path}

    def _get_project_id(self, project_name: str) -> Optional[int]:
        """Get project ID from project name."""
        try:
            result = self.connection.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            return result[0]["id"] if result else None
        except Exception as e:
            logger.error(f"Error getting project ID: {e}")
            return None

    def _get_project_directory(self, project_id: int) -> Optional[str]:
        """
        Determine the project directory from existing file paths in the database.
        Returns the common root directory of all files in the project.
        """
        try:
            # Get all file paths for this project
            result = self.connection.execute_query(
                """SELECT DISTINCT file_path FROM file_hashes 
                   WHERE project_id = ? AND file_path IS NOT NULL""",
                (project_id,),
            )

            if not result:
                logger.warning(f"No file paths found for project {project_id}")
                return None

            file_paths = [row["file_path"] for row in result]

            # Find the common root directory
            if len(file_paths) == 1:
                # Single file - use its directory
                return str(Path(file_paths[0]).parent)

            # Multiple files - find common root
            common_path = Path(file_paths[0]).parent
            for file_path in file_paths[1:]:
                file_dir = Path(file_path).parent
                # Find common path between current common_path and this file's directory
                common_parts = []
                for part1, part2 in zip(common_path.parts, file_dir.parts):
                    if part1 == part2:
                        common_parts.append(part1)
                    else:
                        break
                common_path = Path(*common_parts) if common_parts else Path("/")

            project_dir = str(common_path)
            logger.debug(f"📁 Determined project directory: {project_dir}")
            return project_dir

        except Exception as e:
            logger.error(f"Error determining project directory: {e}")
            return None

    def _identify_changes(
        self, parsed_data: ParsedCodebase, project_id: int
    ) -> Dict[str, Set[str]]:
        """Identify changed, new, and deleted files by comparing file hashes."""
        # Get all file hashes from the database for this project
        db_file_hashes = self._get_db_file_hashes(project_id)

        # Extract file hashes from parsed data
        parser_file_hashes = self._get_parser_file_hashes(parsed_data)

        # Identify changed, new, and deleted files
        changed_files = set()
        new_files = set()

        for file_path, parser_hash in parser_file_hashes.items():
            if file_path in db_file_hashes:
                if db_file_hashes[file_path] != parser_hash:
                    # File exists but hash changed (modified)
                    changed_files.add(file_path)
            else:
                # File doesn't exist in database (new)
                new_files.add(file_path)

        # Identify deleted files (in DB but not in parser output)
        deleted_files = set(db_file_hashes.keys()) - set(parser_file_hashes.keys())

        logger.debug(
            f"📊 Changes identified: {len(changed_files)} changed, {len(new_files)} new, {len(deleted_files)} deleted"
        )
        return {
            "changed_files": changed_files,
            "new_files": new_files,
            "deleted_files": deleted_files,
        }

    def _get_db_file_hashes(self, project_id: int) -> Dict[str, str]:
        """Get all file hashes from the database for a project."""
        file_hashes = {}
        try:
            results = self.connection.execute_query(
                """SELECT file_path, content_hash
                   FROM file_hashes
                   WHERE project_id = ?""",
                (project_id,),
            )

            for row in results:
                file_hashes[row["file_path"]] = row["content_hash"]

            logger.debug(f"📊 Retrieved {len(file_hashes)} file hashes from database")
            return file_hashes
        except Exception as e:
            logger.error(f"Error getting file hashes from database: {e}")
            return {}

    def _get_parser_file_hashes(self, parsed_data: ParsedCodebase) -> Dict[str, str]:
        """Extract file hashes from parsed data."""
        file_hashes = {}

        for node in parsed_data.nodes:
            if node.type == "file" and node.path:
                # Use content_hash if available, otherwise compute it
                content_hash = (
                    node.content_hash
                    or hashlib.sha256(node.content.encode("utf-8")).hexdigest()
                    if node.content
                    else ""
                )

                file_hashes[node.path] = content_hash

        logger.debug(f"📊 Extracted {len(file_hashes)} file hashes from parser output")
        return file_hashes

    def _process_changes(
        self,
        changes: Dict[str, Set[str]],
        parsed_data: ParsedCodebase,
        project_id: int,
        project_name: str,
    ) -> Dict[str, int]:
        """Process identified changes by deleting and adding nodes and relationships."""
        # Initialize counters
        nodes_deleted = 0
        relationships_deleted = 0
        nodes_added = 0
        relationships_added = 0

        # Process changed and deleted files (delete their nodes and relationships)
        files_to_delete = changes["changed_files"].union(changes["deleted_files"])
        for file_path in files_to_delete:
            deleted = self._delete_file_nodes_and_relationships(file_path, project_id)
            nodes_deleted += deleted["nodes"]
            relationships_deleted += deleted["relationships"]

        # Process changed and new files (add their nodes and relationships)
        files_to_add = changes["changed_files"].union(changes["new_files"])
        if files_to_add:
            # Get nodes and their IDs from the changed/new files
            nodes_from_changed_files = [
                n for n in parsed_data.nodes if n.path in files_to_add
            ]
            node_ids_from_changed_files = {n.id for n in nodes_from_changed_files}

            # Get all relationships that start from one of the changed nodes
            relevant_edges = [
                edge
                for edge in parsed_data.edges
                if edge.from_id in node_ids_from_changed_files
            ]

            # --- START OF CORRECTED LOGIC ---

            # Gather all the target node IDs from these relationships to ensure they exist.
            target_node_ids = {edge.to_id for edge in relevant_edges}

            # The final set of node IDs to process includes the nodes from changed files
            # AND all the nodes they point to.
            all_relevant_node_ids = node_ids_from_changed_files.union(target_node_ids)

            # Filter the full parsed node list to get the complete set of node objects we need.
            final_nodes_to_process = [
                n for n in parsed_data.nodes if n.id in all_relevant_node_ids
            ]

            # --- END OF CORRECTED LOGIC ---

            # Create a filtered ParsedCodebase object with the complete set of required nodes and edges
            filtered_data = ParsedCodebase(
                nodes=final_nodes_to_process,
                edges=relevant_edges,
                project=parsed_data.project,
            )

            # Process the filtered data into a format ready for database insertion
            graph_data = self.processor.process_codebase(
                filtered_data, project_id, project_name
            )

            # Insert the processed data into the database
            # The underlying `insert_nodes` call should handle potential conflicts gracefully
            # (e.g., using 'INSERT OR IGNORE') for target nodes that may already exist.
            self._insert_graph_data(graph_data, project_id)

            nodes_added = len(graph_data.nodes)
            relationships_added = len(graph_data.relationships)

        logger.debug(
            f"📊 Processed changes: {nodes_deleted} nodes deleted, {relationships_deleted} relationships deleted"
        )
        logger.debug(
            f"📊 Processed changes: {nodes_added} nodes added, {relationships_added} relationships added"
        )

        return {
            "nodes_deleted": nodes_deleted,
            "relationships_deleted": relationships_deleted,
            "nodes_added": nodes_added,
            "relationships_added": relationships_added,
        }

    def _delete_file_nodes_and_relationships(
        self, file_path: str, project_id: int
    ) -> Dict[str, int]:
        """Delete all nodes and relationships for a specific file."""
        try:
            # Get file hash ID for the file path
            file_hash_result = self.connection.execute_query(
                "SELECT id FROM file_hashes WHERE project_id = ? AND file_path = ?",
                (project_id, file_path),
            )

            if not file_hash_result:
                logger.warning(f"File hash not found for {file_path}")
                return {"nodes": 0, "relationships": 0}

            file_hash_id = file_hash_result[0]["id"]

            # Get all node IDs for this file hash
            node_id_result = self.connection.execute_query(
                "SELECT node_id FROM nodes WHERE project_id = ? AND file_hash_id = ?",
                (project_id, file_hash_id),
            )

            if not node_id_result:
                logger.warning(f"No nodes found for file {file_path}")
                return {"nodes": 0, "relationships": 0}

            node_ids = [row["node_id"] for row in node_id_result]

            # Delete relationships involving these nodes
            # First, count them
            rel_count_result = self.connection.execute_query(
                """SELECT COUNT(*) as count FROM relationships
                   WHERE project_id = ? AND (from_node_id IN ({}) OR to_node_id IN ({}))""".format(
                    ",".join(["?" for _ in node_ids]), ",".join(["?" for _ in node_ids])
                ),
                (project_id, *node_ids, *node_ids),
            )

            rel_count = rel_count_result[0]["count"] if rel_count_result else 0

            # Then delete them
            self.connection.execute_query(
                """DELETE FROM relationships
                   WHERE project_id = ? AND (from_node_id IN ({}) OR to_node_id IN ({}))""".format(
                    ",".join(["?" for _ in node_ids]), ",".join(["?" for _ in node_ids])
                ),
                (project_id, *node_ids, *node_ids),
            )

            # Delete nodes
            self.connection.execute_query(
                "DELETE FROM nodes WHERE project_id = ? AND file_hash_id = ?",
                (project_id, file_hash_id),
            )

            # Delete file hash
            self.connection.execute_query(
                "DELETE FROM file_hashes WHERE id = ?", (file_hash_id,)
            )

            # Delete embeddings for these nodes
            self._delete_node_embeddings(node_ids, project_id)

            logger.debug(
                f"🗑️ Deleted {len(node_ids)} nodes and {rel_count} relationships for file {file_path}"
            )
            return {"nodes": len(node_ids), "relationships": rel_count}

        except Exception as e:
            logger.error(f"Error deleting nodes for file {file_path}: {e}")
            return {"nodes": 0, "relationships": 0}

    def _delete_node_embeddings(self, node_ids: List[int], project_id: int) -> None:
        """Delete embeddings for specified nodes."""
        try:
            # Check if vector_embeddings table exists
            table_check = self.connection.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='vector_embeddings'"
            )

            if not table_check:
                logger.debug(
                    "vector_embeddings table does not exist, skipping embedding deletion"
                )
                return

            # Delete embeddings for these nodes
            placeholders = ",".join(["?" for _ in node_ids])
            self.connection.execute_query(
                f"""DELETE FROM vector_embeddings
                   WHERE node_id IN ({placeholders}) AND project_id = ?""",
                (*node_ids, project_id),
            )

            logger.debug(f"Deleted embeddings for {len(node_ids)} nodes")

        except Exception as e:
            logger.error(f"Error deleting node embeddings: {e}")

    def _insert_graph_data(self, graph_data: GraphData, project_id: int) -> None:
        """Insert graph data into the database."""
        try:

            # Insert nodes
            if graph_data.nodes:
                self.graphOperations.insert_nodes(graph_data.nodes, project_id)

            # Insert relationships
            if graph_data.relationships:
                self.graphOperations.insert_relationships(
                    graph_data.relationships, project_id
                )

        except Exception as e:
            logger.error(f"Error inserting graph data: {e}")
            raise
