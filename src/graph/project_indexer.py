"""Incremental indexing for efficient database updates when code changes."""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
from loguru import logger

from graph.sqlite_client import SQLiteConnection, GraphOperations
from graph.converter import ASTToSqliteConverter
from embeddings import get_embedding_engine

from utils.helpers import load_json_file
from config.settings import config

# Import will be done lazily to avoid circular imports

# Import indexer functions for file processing
from indexer import (
    compute_file_hash,
    compute_directory_hashes,
    load_previous_results,
    extract_from_directory,
    export_to_json,
)
from indexer.ast_parser import ASTParser
from utils.file_utils import (
    get_extraction_file_path,
    get_last_extraction_file_path,
)

from models.schema import (
    Project,
    File,
    FileData,
    BlockType,
    CodeBlock,
    Relationship,
    ExtractionData,
)


class ProjectIndexer:
    """
    Handles all project indexing operations - both full and incremental.
    Provides unified interface for parsing, storing to SQL, and generating embeddings.
    """

    def __init__(
        self,
        sutra_memory_manager=None,
    ):
        """Initialize with optional shared memory manager."""
        self.connection = SQLiteConnection()
        self.converter = ASTToSqliteConverter()
        self.graphOperations = GraphOperations()
        self.embedding_engine = get_embedding_engine(
            max_tokens=config.embedding.max_tokens,
            overlap_tokens=config.embedding.overlap_tokens,
        )

        # Use provided memory manager or create new one (lazy import to avoid circular imports)
        if sutra_memory_manager:
            self.sutra_memory = sutra_memory_manager
        else:
            from services.agent.memory_management import SutraMemoryManager

            self.sutra_memory = SutraMemoryManager()
        logger.debug("🔄 ProjectIndexer initialized")

    def full_index_project(self, project_name: str, project_path: Path) -> None:
        """Perform complete indexing of a project from scratch.

        This includes:
        1. Parsing the entire repository
        2. Storing all data to SQL tables
        3. Generating embeddings for all files and blocks

        Args:
            project_name: Name of the project
            project_path: Path to the project directory
        """
        try:
            print(f"⚠️  Project '{project_name}' not found in database")
            print("🔄 Starting automatic indexing...")
            print(
                "   This will analyze the codebase and generate embeddings for better responses."
            )
            print("   Please wait while the project is being indexed...\n")

            # Phase 1: Parse repository
            parser_output_path = self._parse_repository(project_name, project_path)

            # Phase 2: Store to database and generate embeddings
            print("\nPHASE 2: Generating Knowledge Graph & Embeddings")
            print("-" * 40)

            # Step 1: Store parsed data to SQL tables
            print("   Step 1: Storing parsed data to SQL tables...")
            self._store_to_database(parser_output_path, project_name)

            # Step 2: Generate embeddings for the stored data
            print("   Step 2: Generating embeddings for semantic search...")
            self._generate_embeddings_for_project(parser_output_path, project_name)

            print("\n✅ Project indexing completed successfully!")
            print("   The agent is now ready to provide intelligent assistance.\n")

        except Exception as e:
            logger.error(f"Error during full indexing: {e}")
            print(f"❌ Full indexing failed: {e}")
            print("   Continuing with limited functionality.")
            raise

    def incremental_index_project(self, project_name: str) -> Dict[str, Any]:
        """Perform incremental indexing by updating only changed files.

        This function performs incremental parsing for a project by:
        1. Computing current file content hashes for the project directory
        2. Comparing with stored hashes in the database to identify changes
        3. Parsing only changed files using the indexer
        4. Replacing changed files in previous extraction result and saving new file
        5. Recomputing relationships for changed files only
        6. Updating the database by deleting old data and inserting new data

        Args:
            project_name: Name of the project/codebase

        Returns:
            Dictionary with update statistics
        """
        logger.debug(f"🔄 Starting incremental reindexing for project: {project_name}")

        try:
            # Get project and validate
            project = self.connection.get_project(project_name=project_name)
            if not project:
                logger.error(f"Project not found: {project_name}")
                return {
                    "status": "failed",
                    "error": f"Project not found: {project_name}",
                }

            project_id = project.id
            project_dir = Path(project.path)
            if not project_dir.exists():
                logger.error(f"Project directory does not exist: {project_dir}")
                return {
                    "status": "failed",
                    "error": f"Project directory does not exist: {project_dir}",
                }

            # Step 1: Compute current file content hashes for the project directory
            logger.debug(f"📊 Computing current file hashes for: {project_dir}")
            current_file_hashes = self._compute_current_file_hashes(project_dir)
            logger.debug(
                f"📊 Found {len(current_file_hashes)} files in project directory"
            )

            # Step 2: Get stored file hashes from database
            logger.debug(f"📊 Getting stored file hashes from database")
            db_file_hashes = self._get_db_file_hashes(project_id)
            logger.debug(f"📊 Found {len(db_file_hashes)} files in database")

            # Step 3: Identify changed files by comparing hashes
            changes = self._identify_file_changes(current_file_hashes, db_file_hashes)
            logger.debug(
                f"📊 Changes identified: {len(changes['changed_files'])} changed, "
                f"{len(changes['new_files'])} new, {len(changes['deleted_files'])} deleted"
            )

            # If no changes, return early
            if not any(changes.values()):
                logger.debug("✅ No changes detected, skipping reindexing")
                return {
                    "status": "success",
                    "files_changed": 0,
                    "files_added": 0,
                    "files_deleted": 0,
                    "nodes_deleted": 0,
                    "relationships_deleted": 0,
                    "nodes_added": 0,
                    "relationships_added": 0,
                    "memory_updates": {
                        "codes_updated": 0,
                        "codes_removed": 0,
                        "files_processed": 0,
                    },
                }

            # Step 4: Parse changed files and update extraction results
            logger.debug(f"🔄 Parsing changed files and updating extraction results")
            updated_extraction_file = self._parse_and_update_extraction_results(
                changes, project_name
            )

            # Step 5: Load the updated extraction data and convert to database format
            logger.debug(
                f"📦 Loading updated extraction data from: {updated_extraction_file}"
            )
            json_data = load_json_file(updated_extraction_file)
            extraction_data = ExtractionData(**json_data)

            # Step 6: Process changes in database (delete old, insert new)
            stats = self._process_database_changes(
                changes, extraction_data, project_id, project_name
            )

            # Step 7: Update Sutra memory for file changes
            memory_updates = self._update_sutra_memory_for_changes(changes, project_id)

            logger.debug(f"✅ Incremental reindexing completed successfully!")
            return {
                "status": "success",
                "extraction_file": str(updated_extraction_file),
                "files_changed": len(changes["changed_files"]),
                "files_added": len(changes["new_files"]),
                "files_deleted": len(changes["deleted_files"]),
                "nodes_deleted": stats["nodes_deleted"],
                "relationships_deleted": stats["relationships_deleted"],
                "nodes_added": stats["nodes_added"],
                "relationships_added": stats["relationships_added"],
                "memory_updates": memory_updates,
            }

        except Exception as e:
            logger.error(f"Incremental reindexing failed: {e}")
            return {"status": "failed", "error": str(e)}

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

    def _compute_current_file_hashes(self, project_dir: Path) -> Dict[Path, str]:
        """
        Compute current file content hashes for all files in the project directory.
        Uses the indexer's compute_directory_hashes function.

        Args:
            project_dir: Path to the project directory

        Returns:
            Dictionary mapping absolute file Path objects to their content hashes
        """
        try:
            file_hashes = compute_directory_hashes(project_dir)
            logger.debug(f"📊 Computed hashes for {len(file_hashes)} files")
            return file_hashes

        except Exception as e:
            logger.error(f"Error computing current file hashes: {e}")
            return {}

    def _identify_file_changes(
        self, current_hashes: Dict[Path, str], db_hashes: Dict[Path, str]
    ) -> Dict[str, Set[Path]]:
        """
        Identify changed, new, and deleted files by comparing file hashes.

        Args:
            current_hashes: Current file hashes from project directory
            db_hashes: File hashes stored in database

        Returns:
            Dictionary with sets of changed_files, new_files, and deleted_files (all Path objects)
        """
        changed_files = set()
        new_files = set()

        # Check each current file
        for file_path, current_hash in current_hashes.items():
            if file_path in db_hashes:
                if db_hashes[file_path] != current_hash:
                    # File exists but hash changed (modified)
                    changed_files.add(file_path)
            else:
                # File doesn't exist in database (new)
                new_files.add(file_path)

        # Identify deleted files (in DB but not in current directory)
        deleted_files = set(db_hashes.keys()) - set(current_hashes.keys())

        return {
            "changed_files": changed_files,
            "new_files": new_files,
            "deleted_files": deleted_files,
        }

    def _parse_and_update_extraction_results(
        self, changes: Dict[str, Set[Path]], project_name: str
    ) -> Path:
        """
        Parse changed files and update extraction results.

        This function:
        1. Loads previous extraction results
        2. Parses only changed/new files
        3. Replaces changed files in previous results
        4. Saves updated results to a new file with timestamp

        Args:
            changes: Dictionary containing changed_files, new_files, deleted_files
            project_dir: Path to the project directory
            project_name: Name of the project

        Returns:
            Path to the updated extraction file
        """
        from datetime import datetime

        try:
            # Get the most recent extraction file
            previous_extraction_file = get_last_extraction_file_path(project_name)

            # Load previous results if available
            previous_extraction_data = None
            if previous_extraction_file and previous_extraction_file.exists():
                logger.debug(
                    f"📦 Loading previous extraction results from: {previous_extraction_file}"
                )
                json_data = load_json_file(previous_extraction_file)
                previous_extraction_data = ExtractionData(**json_data)
                logger.debug(
                    f"📦 Loaded {len(previous_extraction_data.files)} files from previous results"
                )
            else:
                logger.debug("📦 No previous extraction results found, starting fresh")
                # Create empty extraction data
                previous_extraction_data = ExtractionData(
                    metadata={
                        "export_timestamp": datetime.now().isoformat(),
                        "total_files": 0,
                        "extractor_version": "1.0.0",
                    },
                    files={},
                )

            # Start with previous files as base
            updated_files = previous_extraction_data.files.copy()

            # Remove deleted files from results
            for deleted_file in changes["deleted_files"]:
                deleted_file_str = str(deleted_file)
                if deleted_file_str in updated_files:
                    del updated_files[deleted_file_str]
                    logger.debug(f"🗑️ Removed deleted file from results: {deleted_file}")

            # Get all changed and new files that need parsing
            files_to_parse = list(changes["changed_files"].union(changes["new_files"]))

            if files_to_parse:
                logger.debug(f"🔄 Parsing {len(files_to_parse)} changed/new files")

                # Parse each changed file individually using the existing parse_and_extract method
                parser = ASTParser()
                parsed_results = {}

                for file_path in files_to_parse:
                    try:
                        # file_path is already a Path object from compute_directory_hashes
                        # Parse and extract from this single file
                        result = parser.parse_and_extract(file_path)

                        if result.get("ast") or result.get("error"):
                            # Use string representation for results dict (consistent with existing format)
                            file_path_str = str(file_path)
                            parsed_results[file_path_str] = result
                            logger.debug(f"✅ Parsed file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error parsing file {file_path}: {e}")
                        continue

                # Extract relationships for the changed files
                if parsed_results:
                    logger.debug(
                        f"🔗 Extracting relationships for {len(files_to_parse)} changed files"
                    )

                    # Create ID to path mapping for all files (needed for relationship resolution)
                    id_to_path = {}
                    for file_path_str, result in parsed_results.items():
                        file_id = result.get("id")
                        if file_id:
                            id_to_path[file_id] = file_path_str

                    # Process relationships only for the changed files
                    parser.process_relationships(parsed_results, id_to_path)

                # Convert parsed results to FileData objects and update the files dict
                for file_path_str, result in parsed_results.items():
                    if not result.get("error"):
                        file_data = FileData(
                            id=result["id"],
                            file_path=file_path_str,
                            language=result["language"],
                            content=result["content"],
                            content_hash=result["content_hash"],
                            blocks=result["blocks"],
                            relationships=result.get("relationships", []),
                        )
                        updated_files[file_path_str] = file_data
                        logger.debug(f"✅ Updated FileData for: {file_path_str}")

            # Create updated extraction data
            updated_extraction_data = ExtractionData(
                metadata={
                    "export_timestamp": datetime.now().isoformat(),
                    "total_files": len(updated_files),
                    "extractor_version": "1.0.0",
                },
                files=updated_files,
            )

            # Save the complete updated results to a new file
            output_file = get_extraction_file_path(project_name)
            logger.debug(f"💾 Saving updated extraction results to: {output_file}")

            # Convert to JSON-serializable format and save
            from utils.json_serializer import make_json_serializable

            serializable_data = make_json_serializable(updated_extraction_data.dict())

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"✅ Successfully saved {len(updated_files)} files to extraction results"
            )
            return output_file

        except Exception as e:
            logger.error(f"Error parsing and updating extraction results: {e}")
            raise

    def _get_db_file_hashes(self, project_id: int) -> Dict[Path, str]:
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
                # Convert string path from database to Path object
                file_path = Path(row["file_path"])
                file_hashes[file_path] = row["content_hash"]

            logger.debug(f"📊 Retrieved {len(file_hashes)} file hashes from database")
            return file_hashes
        except Exception as e:
            logger.error(f"Error getting file hashes from database: {e}")
            return {}

    def _process_database_changes(
        self,
        changes: Dict[str, Set[Path]],
        extraction_data: ExtractionData,
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
            # Convert Path to string for database operations
            file_path_str = str(file_path)
            deleted = self._delete_file_nodes_and_relationships(
                file_path_str, project_id
            )
            nodes_deleted += deleted["nodes"]
            relationships_deleted += deleted["relationships"]

        # Process changed and new files (add their nodes and relationships)
        files_to_add = changes["changed_files"].union(changes["new_files"])
        if files_to_add:
            logger.debug(
                f"🔄 Processing {len(files_to_add)} changed/new files for database insertion"
            )

            # Create a filtered extraction data with only the changed/new files
            filtered_files = {}
            for file_path in files_to_add:
                # Convert Path to string to match extraction_data.files keys
                file_path_str = str(file_path)
                if file_path_str in extraction_data.files:
                    filtered_files[file_path_str] = extraction_data.files[file_path_str]

            if filtered_files:
                # Create filtered extraction data
                filtered_extraction_data = ExtractionData(
                    metadata=extraction_data.metadata, files=filtered_files
                )

                # Insert the filtered data using graph operations
                logger.debug(f"📦 Inserting {len(filtered_files)} files into database")
                self.graphOperations.insert_extraction_data(
                    filtered_extraction_data, project_id
                )

                # Count nodes and relationships added
                for file_data in filtered_files.values():
                    nodes_added += len(file_data.blocks)
                    relationships_added += len(file_data.relationships)

                # Generate embeddings for changed file nodes
                self._generate_embeddings_for_changed_files(
                    list(filtered_files.values()), project_id, project_name
                )

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

    def _update_sutra_memory_for_changes(
        self, changes: Dict[str, Set[Path]], project_id: int
    ) -> Dict[str, Any]:
        """
        Update Sutra memory when files change during incremental indexing.

        Args:
            changes: Dictionary containing changed_files, new_files, and deleted_files
            project_id: Project ID for database queries

        Returns:
            Dictionary with memory update statistics
        """
        try:
            logger.debug("🧠 Updating Sutra memory for file changes...")

            # Call the memory updater to handle the changes
            memory_updates = self.sutra_memory.update_memory_for_file_changes(
                changed_files=changes["changed_files"],
                deleted_files=changes["deleted_files"],
                project_id=project_id,
            )

            if (
                memory_updates["codes_updated"] > 0
                or memory_updates["codes_removed"] > 0
            ):
                logger.debug(
                    f"🧠 Sutra memory updated: "
                    f"{memory_updates['codes_updated']} codes updated, "
                    f"{memory_updates['codes_removed']} codes removed, "
                    f"{memory_updates['files_processed']} files processed"
                )
            else:
                logger.debug("🧠 No Sutra memory updates required")

            return memory_updates

        except Exception as e:
            logger.error(f"Error updating Sutra memory: {e}")
            return {
                "codes_updated": 0,
                "codes_removed": 0,
                "line_number_updates": 0,
                "content_updates": 0,
                "files_processed": 0,
                "error": str(e),
            }

    def _generate_embeddings_for_changed_files(
        self, changed_file_data: List[FileData], project_id: int, project_name: str
    ) -> None:
        """Generate strategic embeddings for changed file data and their code blocks."""
        try:
            # Use the new strategic embedding engine
            stats = self.embedding_engine.process_multiple_files(
                changed_file_data, project_id
            )
            logger.info(
                f"Generated embeddings for {len(changed_file_data)} changed files: "
                f"{stats['total_chunks']} total chunks, "
                f"{stats['blocks_processed']} blocks processed"
            )

        except Exception as e:
            logger.error(f"Error generating embeddings for changed files: {e}")

    def _parse_repository(self, project_name: str, project_path: Path) -> Path:
        """Parse the entire repository and return path to extraction file."""
        print("PHASE 1: Parsing Repository")
        print("-" * 40)

        try:
            print(f"   Parsing directory: {project_path}")

            from config import config

            output_dir = Path(config.storage.parser_results_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            import time

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            parser_output_path = Path(
                output_dir / f"{project_name}_{timestamp}.json"
            ).absolute()

            # Use the indexer to extract and export directory data
            from indexer import extract_and_export_directory

            success = extract_and_export_directory(
                dir_path=project_path, output_file=parser_output_path, indent=2
            )

            if not success:
                raise Exception(f"Failed to parse repository: {project_name}")

            print(f"✅ Repository parsed successfully")
            print(f"   Generated analysis for project: {project_name}")
            print(f"   Output file: {parser_output_path}")

            return parser_output_path

        except Exception as e:
            logger.error(f"Parser error: {e}")
            print(f"❌ Failed to parse repository: {e}")
            raise

    def _store_to_database(
        self, parser_output_path: Path, project_name: str
    ) -> Dict[str, Any]:
        """Store parsed data to SQL tables."""
        from graph import ASTToSqliteConverter

        converter = ASTToSqliteConverter()

        # Convert to database - returns stats dict or raises exception
        stats = converter.convert_json_to_graph(
            parser_output_path,
            project_name=project_name,
            clear_existing=False,
        )

        print(f"   ✅ SQL storage completed!")
        print(
            f"      Processed: {stats.get('total_nodes', 0)} nodes, {stats.get('total_relationships', 0)} relationships"
        )
        return stats

    def _generate_embeddings_for_project(
        self, parser_output_path: Path, project_name: str
    ):
        """Generate embeddings for all files in the project."""
        # Get project ID from database
        project = self.connection.get_project(project_name)
        if not project:
            raise Exception(
                f"Project '{project_name}' not found in database after SQL storage"
            )
        project_id = project.id

        # Load the parsed data for embedding generation
        from utils import load_json_file

        json_data = load_json_file(parser_output_path)
        # ExtractionData already imported at top

        extraction_data = ExtractionData(**json_data)

        # Generate embeddings using the embedding engine
        # Convert dictionary to list of FileData objects
        file_data_list = list(extraction_data.files.values())
        embedding_stats = self.embedding_engine.process_multiple_files(
            file_data_list, project_id
        )

        print(f"   ✅ Embeddings generated successfully!")
        print(f"      Files processed: {embedding_stats['files_processed']}")
        print(f"      Total chunks: {embedding_stats['total_chunks']}")
        print(f"      Blocks embedded: {embedding_stats['blocks_processed']}")

    # Backward compatibility
    def reindex_database(self, project_name: str) -> Dict[str, Any]:
        """Backward compatibility method for incremental indexing."""
        return self.incremental_index_project(project_name)
