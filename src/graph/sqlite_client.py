"""
SQLite database connection and operations for code extraction data.
Stores files, code blocks, and relationships from code parsing.
"""

import json
import os
import sqlite3
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from loguru import logger
from config import config
from models import File, Project, CodeBlock, Relationship, ExtractionData
from utils import chunk_list
from queries.creation_queries import CREATE_TABLES, CREATE_INDEXES


class SQLiteConnection:
    """Manages SQLite database connections and operations."""

    _instance: Optional["SQLiteConnection"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the connection - only called once due to singleton pattern."""
        if not hasattr(self, "initialized"):
            self.database_path = config.sqlite.knowledge_graph_db
            self.connection = self._connect()
            self._create_tables()
            self.initialized = True
            logger.debug("✅ SQLiteConnection initialized")

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.debug("🔧 Creating new SQLiteConnection singleton instance")
                    cls._instance = super(SQLiteConnection, cls).__new__(cls)
        else:
            logger.debug("♻️ Reusing existing SQLiteConnection singleton instance")
        return cls._instance

    def _connect(self) -> sqlite3.Connection:
        """Establish connection to SQLite database."""
        try:
            db_path = Path(self.database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            connection = sqlite3.connect(
                self.database_path,
                timeout=config.sqlite.connection_timeout,
                check_same_thread=False,
            )

            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute("PRAGMA cache_size = 10000")
            connection.execute("SELECT 1")

            logger.debug(
                f"Successfully connected to SQLite database: {self.database_path}"
            )
            return connection

        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise

    def _create_tables(self) -> None:
        """Create necessary tables for storing code extraction data."""
        try:
            for query in CREATE_TABLES:
                self.connection.execute(query)

            for query in CREATE_INDEXES:
                self.connection.execute(query)

            self.connection.commit()
            logger.debug("Database tables and indexes created/verified")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to create tables: {e}")
            raise

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, "connection") and self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(
        self, query: str, parameters: tuple | None = None
    ) -> List[Dict[str, Any]]:
        """Execute a simple query and return results."""
        try:
            cursor = self.connection.cursor()
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)

            # Get column names
            columns = (
                [description[0] for description in cursor.description]
                if cursor.description
                else []
            )

            # Fetch all results and convert to dict
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists in the database."""
        try:
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM projects WHERE name = ?", (project_name,)
            )
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error(f"Failed to check project existence: {e}")
            return False

    def get_project(self, project_name: str) -> Union[Project, None]:
        """Get project details by name."""
        try:
            result = self.execute_query(
                "SELECT id, name, path, created_at, updated_at FROM projects WHERE name = ?",
                (project_name,),
            )
            if result:
                row = result[0]
                return Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get project '{project_name}': {e}")
            return None

    def delete_project(self, project_name: str) -> None:
        """Delete a project and all associated data."""
        try:
            self.connection.execute(
                "DELETE FROM projects WHERE name = ?", (project_name,)
            )
            self.connection.commit()
            logger.info(f"Deleted project '{project_name}' and associated data")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to delete project '{project_name}': {e}")
            raise

    def insert_project(self, project: Project) -> int:
        """Insert or replace a project. Returns project ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO projects (name, path, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (project.name, project.path, project.created_at, project.updated_at),
            )

            # Get the project ID
            cursor.execute("SELECT id FROM projects WHERE name = ?", (project.name,))
            result = cursor.fetchone()
            project_id = result[0] if result else cursor.lastrowid

            self.connection.commit()
            logger.debug(f"Inserted project '{project.name}' with ID: {project_id}")

            if not project_id:
                logger.error(f"Failed to retrieve project ID for '{project.name}'")
                raise ValueError("Failed to retrieve project ID after insertion")

            return project_id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert project: {e}")
            raise

    def insert_file(self, file: File) -> int:
        """Insert a new file. Returns file ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO files (id, project_id, file_path, language, content, content_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    file.id,
                    file.project_id,
                    file.file_path,
                    file.language,
                    file.content,
                    file.content_hash,
                ),
            )
            self.connection.commit()
            logger.debug(f"Inserted file '{file.file_path}' with ID: {file.id}")
            return file.id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert file: {e}")
            raise

    def insert_code_block(self, block: CodeBlock) -> int:
        """Insert a new code block. Returns block ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO code_blocks (id, type, name, content, start_line, end_line, start_col, end_col, file_id, parent_block_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    block.id,
                    block.type.value,
                    block.name,
                    block.content,
                    block.start_line,
                    block.end_line,
                    block.start_col,
                    block.end_col,
                    block.file_id,
                    block.parent_block_id,
                ),
            )
            self.connection.commit()
            logger.debug(
                f"Inserted code block '{block.name}' with ID: {block.id}, file_id: {block.file_id}, parent_id: {block.parent_block_id}"
            )
            return block.id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert code block: {e}")
            raise

    def insert_relationship(self, relationship: Relationship) -> int:
        """Insert a new relationship. Returns relationship ID."""
        try:
            cursor = self.connection.cursor()
            # Convert symbols list to JSON string for storage
            symbols_json = json.dumps(relationship.symbols)

            cursor.execute(
                "INSERT OR IGNORE INTO relationships (source_id, target_id, import_content, symbols, type) VALUES (?, ?, ?, ?, ?)",
                (
                    relationship.source_id,
                    relationship.target_id,
                    relationship.import_content,
                    symbols_json,
                    relationship.type,
                ),
            )
            self.connection.commit()
            relationship_id = cursor.lastrowid
            logger.debug(f"Inserted relationship with ID: {relationship_id}")

            if not relationship_id:
                logger.error("Failed to retrieve relationship ID after insertion")
                raise ValueError("Failed to retrieve relationship ID after insertion")

            return relationship_id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to insert relationship: {e}")
            raise

    def get_file_blocks(
        self, file_path: str, project_name: Optional[str] = None
    ) -> List[CodeBlock]:
        """Get all code blocks from a specific file with proper nested structure."""
        try:
            query = """
                SELECT cb.id, cb.type, cb.name, cb.content,
                       cb.start_line, cb.end_line, cb.start_col, cb.end_col,
                       cb.file_id, cb.parent_block_id
                FROM code_blocks cb
                JOIN files f ON cb.file_id = f.id
                LEFT JOIN projects p ON f.project_id = p.id
                WHERE f.file_path = ? AND (? IS NULL OR p.name = ?)
                ORDER BY cb.start_line
            """
            params = (file_path, project_name, project_name)

            results = self.execute_query(query, params)

            # Convert to CodeBlock objects and build nested structure
            from models.schema import BlockType

            # First pass: create all blocks
            blocks_by_id = {}
            top_level_blocks = []

            for row in results:
                block = CodeBlock(
                    id=row["id"],
                    type=BlockType(row["type"]),
                    name=row["name"],
                    content=row["content"],
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    start_col=row["start_col"],
                    end_col=row["end_col"],
                    file_id=row["file_id"],
                    parent_block_id=row["parent_block_id"],
                    children=[],
                )
                blocks_by_id[block.id] = block

                # If no parent, it's a top-level block
                if block.parent_block_id is None:
                    top_level_blocks.append(block)

            # Second pass: build parent-child relationships
            for block in blocks_by_id.values():
                if block.parent_block_id is not None:
                    parent = blocks_by_id.get(block.parent_block_id)
                    if parent:
                        parent.children.append(block)

            return top_level_blocks

        except Exception as e:
            logger.error(f"Failed to get file blocks: {e}")
            return []

    def list_all_projects(self) -> List[Project]:
        """List all projects in the database."""
        try:
            rows = self.execute_query(
                "SELECT id, name, path, created_at, updated_at FROM projects ORDER BY name"
            )
            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []

    def clear_database(self) -> None:
        """Completely clear the database by dropping all tables."""
        try:
            # Drop all tables
            tables_to_drop = [
                "connection_mappings",
                "outgoing_connections",
                "incoming_connections",
                "relationships",
                "code_blocks",
                "files",
                "projects",
            ]

            for table in tables_to_drop:
                self.connection.execute(f"DROP TABLE IF EXISTS {table}")

            self.connection.commit()

            # Recreate tables
            self._create_tables()

            logger.info("Database cleared and tables recreated")

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to clear database: {e}")
            raise

    def get_project_block_count(self, project_name: str) -> int:
        """Get count of code blocks for a specific project."""
        try:
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM code_blocks cb JOIN files f ON f.project_id = (SELECT id FROM projects WHERE name = ?)",
                (project_name,),
            )
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get project block count: {e}")
            return 0

    def delete_project_data(self, project_name: str) -> int:
        """Delete all data for a specific project and return count deleted."""
        try:
            # Get count first
            block_count = self.get_project_block_count(project_name)

            if block_count == 0:
                return 0

            # Delete project data (cascading deletes will handle related data)
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM projects WHERE name = ?", (project_name,))

            self.connection.commit()

            logger.info(
                f"Deleted {block_count} code blocks for project '{project_name}'"
            )
            return block_count

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to delete project data: {e}")
            raise

    def get_project_id_by_name(self) -> Optional[int]:
        """Get project ID by project name."""
        project_name = ""
        try:
            current_directory = Path.cwd().absolute()
            project_name = current_directory.stem
            result = self.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            if result:
                return result[0]["id"]
            return None
        except Exception as e:
            logger.debug(f"Failed to get project ID for '{project_name}': {e}")
            return None


class GraphOperations:
    """High-level operations for inserting code extraction data."""

    def __init__(self):
        self.connection = SQLiteConnection()

    def insert_extraction_data_from_dict(
        self, extraction_data: Dict[str, Any], project_id: int
    ) -> None:
        """Insert extraction data from raw dictionary (for backward compatibility)."""
        # Convert dict to ExtractionData model
        extraction_model = ExtractionData(**extraction_data)
        self.insert_extraction_data(extraction_model, project_id)

    def insert_extraction_data(
        self, extraction_data: ExtractionData, project_id: int
    ) -> None:
        """Insert complete extraction data (files, blocks, relationships) from JSON export."""
        logger.info(f"🏗️ Inserting extraction data for project ID: {project_id}")

        files_data = extraction_data.files
        logger.info(f"📁 Processing {len(files_data)} files...")

        for file_path, file_data in files_data.items():
            # Create File object for database
            file_record = File(
                id=file_data.id,
                project_id=project_id,
                file_path=file_path,
                language=file_data.language,
                content=file_data.content,
                content_hash=file_data.content_hash,
            )
            self.connection.insert_file(file_record)

            blocks = file_data.blocks
            logger.debug(f"📦 Inserting {len(blocks)} code blocks for {file_path}")

            # Insert blocks with proper file_id and parent_block_id relationships
            self._insert_blocks_recursively(blocks, file_data.id, None)

            relationships = file_data.relationships
            logger.debug(
                f"🔗 Inserting {len(relationships)} relationships for {file_path}"
            )

            for rel in relationships:
                # Relationship is already the correct type from indexer models
                self.connection.insert_relationship(rel)

        logger.info("✅ Extraction data insertion completed")

    def _insert_blocks_recursively(
        self, blocks: List[CodeBlock], file_id: int, parent_block_id: Optional[int]
    ) -> None:
        """Insert code blocks recursively, handling nested structure properly."""
        for block in blocks:
            # Set the file_id if not already set (should already be set from JSON)
            if block.file_id is None:
                block.file_id = file_id

            # Set parent_block_id for nested blocks
            block.parent_block_id = parent_block_id

            # Insert the current block
            self.connection.insert_code_block(block)

            # Recursively insert children with this block as parent
            if block.children:
                self._insert_blocks_recursively(block.children, file_id, block.id)

    def get_file_count(self) -> int:
        """Get total number of files in the database."""
        try:
            result = self.connection.execute_query(
                "SELECT COUNT(*) as count FROM files"
            )
            return result[0]["count"] if result else 0
        except Exception:
            # Table might not exist
            return 0

    def get_block_count(self) -> int:
        """Get total number of code blocks in the database."""
        try:
            result = self.connection.execute_query(
                "SELECT COUNT(*) as count FROM code_blocks"
            )
            return result[0]["count"] if result else 0
        except Exception:
            # Table might not exist
            return 0

    def get_relationship_count(self) -> int:
        """Get total number of relationships in the database."""
        try:
            result = self.connection.execute_query(
                "SELECT COUNT(*) as count FROM relationships"
            )
            return result[0]["count"] if result else 0
        except Exception:
            # Table might not exist
            return 0

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get comprehensive extraction statistics."""
        try:
            # Block counts by type
            block_stats_result = self.connection.execute_query(
                """
                SELECT cb.type, COUNT(*) as count
                FROM code_blocks cb
                GROUP BY cb.type
                ORDER BY count DESC
                """
            )
            block_stats = {row["type"]: row["count"] for row in block_stats_result}

            # Relationship counts by type
            rel_stats_result = self.connection.execute_query(
                "SELECT type, COUNT(*) as count FROM relationships GROUP BY type ORDER BY count DESC"
            )
            rel_stats = {row["type"]: row["count"] for row in rel_stats_result}

            # Files by language
            files_by_language_result = self.connection.execute_query(
                """
                SELECT language, COUNT(*) as count
                FROM files
                GROUP BY language
                ORDER BY count DESC
                """
            )
            files_by_language = {
                row["language"]: row["count"] for row in files_by_language_result
            }

            # Files by project
            files_by_project_result = self.connection.execute_query(
                """
                SELECT p.name as project_name, COUNT(f.id) as count
                FROM projects p
                LEFT JOIN files f ON p.id = f.project_id
                GROUP BY p.id, p.name
                ORDER BY count DESC
                """
            )
            files_by_project = {
                row["project_name"]: row["count"] for row in files_by_project_result
            }

            return {
                "total_files": self.get_file_count(),
                "total_blocks": self.get_block_count(),
                "total_relationships": self.get_relationship_count(),
                "block_types": block_stats,
                "relationship_types": rel_stats,
                "files_by_language": files_by_language,
                "files_by_project": files_by_project,
            }
        except Exception as e:
            logger.error(f"Error getting extraction stats: {e}")
            return {
                "total_files": 0,
                "total_blocks": 0,
                "total_relationships": 0,
                "block_types": {},
                "relationship_types": {},
                "files_by_language": {},
                "files_by_project": {},
            }

    def get_connections_for_query_results(
        self, query_results: List[Dict[str, Any]], project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get connection information for database query results.

        Args:
            query_results: List of database query results
            project_id: Optional project ID filter

        Returns:
            Dictionary with connection information for each result
        """
        try:
            if not query_results:
                return {}

            connection_info = {}

            for i, result in enumerate(query_results):
                result_key = f"result_{i}"
                file_hash_id = result.get("file_hash_id")
                lines_data = result.get("lines")
                file_path = result.get("file_path", "")

                if not file_hash_id:
                    # Try to get file_hash_id from file_path if available
                    if file_path:
                        file_hash_id = self._get_file_hash_id_by_path(file_path)

                if file_hash_id:
                    # Parse line information
                    start_line, end_line = self._parse_line_info(lines_data)

                    # Get connections for this file_hash_id and line range
                    connections = self._get_connections_for_file_and_lines(
                        file_hash_id, start_line, end_line
                    )

                    if connections["incoming"] or connections["outgoing"]:
                        connection_info[result_key] = {
                            "file_hash_id": file_hash_id,
                            "file_path": file_path,
                            "line_range": (
                                [start_line, end_line]
                                if start_line and end_line
                                else None
                            ),
                            "connections": connections,
                            "note": self._generate_connection_note(connections),
                        }

            return connection_info

        except Exception as e:
            logger.error(f"Error getting connections for query results: {e}")
            return {}

    def _get_file_hash_id_by_path(self, file_path: str) -> Optional[int]:
        """Get file_hash_id by file path with robust path resolution."""
        try:
            if not file_path:
                logger.warning("Empty file_path provided to _get_file_hash_id_by_path")
                return None

            # Convert to absolute path if it's relative
            if not os.path.isabs(file_path):
                absolute_file_path = str(Path(file_path).resolve())
                logger.debug(
                    f"Resolved relative path {file_path} to absolute path {absolute_file_path}"
                )
            else:
                absolute_file_path = file_path

            # Try with absolute path first
            result = self.connection.execute_query(
                "SELECT id FROM files WHERE file_path = ?",
                (absolute_file_path,),
            )

            if result:
                file_hash_id = result[0]["id"]
                logger.debug(
                    f"Found file_hash_id {file_hash_id} for {absolute_file_path}"
                )
                return file_hash_id

            if absolute_file_path != file_path:
                result = self.connection.execute_query(
                    "SELECT id FROM files WHERE file_path = ?",
                    (file_path,),
                )

                if result:
                    file_hash_id = result[0]["id"]
                    logger.debug(
                        f"Found file_hash_id {file_hash_id} for {file_path} (original path)"
                    )
                    return file_hash_id

            filename = os.path.basename(file_path)
            if filename:
                result = self.connection.execute_query(
                    "SELECT id, file_path FROM files WHERE file_path LIKE ?",
                    (f"%{filename}",),
                )

                if result:
                    # If multiple matches, prefer exact filename match
                    for row in result:
                        if os.path.basename(row["file_path"]) == filename:
                            file_hash_id = row["id"]
                            logger.debug(
                                f"Found file_hash_id {file_hash_id} by filename match for {filename} -> {row['file_path']}"
                            )
                            return file_hash_id

            logger.warning(
                f"No file_hash_id found for {file_path} (absolute: {absolute_file_path})"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting file_hash_id for {file_path}: {e}")
            return None

    def _parse_line_info(self, lines_data: Any) -> Tuple[Optional[int], Optional[int]]:
        """Parse line information from database result."""
        try:
            if not lines_data:
                return None, None

            if isinstance(lines_data, str):
                lines_parsed = json.loads(lines_data)
            elif isinstance(lines_data, list):
                lines_parsed = lines_data
            else:
                return None, None

            if isinstance(lines_parsed, list) and len(lines_parsed) >= 2:
                return int(lines_parsed[0]), int(lines_parsed[1])

            return None, None

        except Exception as e:
            logger.debug(f"Error parsing line info: {e}")
            return None, None

    def _get_connections_for_file_and_lines(
        self,
        file_hash_id: int,
        start_line: Optional[int],
        end_line: Optional[int],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get incoming and outgoing connections for a specific file and line range.

        Args:
            file_hash_id: File hash ID to search for
            start_line: Start line of the fetched code
            end_line: End line of the fetched code
            project_id: Optional project ID filter

        Returns:
            Dictionary with 'incoming' and 'outgoing' connection lists
        """
        try:
            connections = {"incoming": [], "outgoing": []}

            # Get incoming connections
            incoming_connections = self._get_connections_by_type(
                "incoming", file_hash_id
            )

            # Get outgoing connections
            outgoing_connections = self._get_connections_by_type(
                "outgoing", file_hash_id
            )

            # Filter connections based on line overlap if line info is available
            if start_line is not None and end_line is not None:
                connections["incoming"] = self._filter_connections_by_lines(
                    incoming_connections, start_line, end_line
                )
                connections["outgoing"] = self._filter_connections_by_lines(
                    outgoing_connections, start_line, end_line
                )
            else:
                # If no line info, return all connections for the file
                connections["incoming"] = incoming_connections
                connections["outgoing"] = outgoing_connections

            # Add mapped connections for each connection
            connections["incoming"] = self._add_mapped_connections(
                connections["incoming"], "incoming"
            )
            connections["outgoing"] = self._add_mapped_connections(
                connections["outgoing"], "outgoing"
            )

            return connections

        except Exception as e:
            logger.error(
                f"Error getting connections for file_hash_id {file_hash_id}: {e}"
            )
            return {"incoming": [], "outgoing": []}

    def _get_connections_by_type(
        self,
        connection_type: str,
        file_hash_id: int,
    ) -> List[Dict[str, Any]]:
        """Get connections of a specific type for a file."""
        try:
            table_name = f"{connection_type}_connections"

            base_query = f"""
                SELECT c.id, c.description, c.snippet_lines, c.technology_name, 
                      c.code_snippet, c.created_at,
                      files.file_path, files.language, p.name as project_name
                FROM {table_name} c
                JOIN files ON c.file_id = files.id
                JOIN projects p ON c.project_id = p.id
                WHERE c.file_id = ?
            """

            params = [file_hash_id]

            base_query += " ORDER BY c.created_at DESC"

            results = self.connection.execute_query(base_query, tuple(params))

            # Parse snippet_lines JSON
            for result in results:
                if result.get("snippet_lines"):
                    try:
                        result["snippet_lines_parsed"] = json.loads(
                            result["snippet_lines"]
                        )
                    except:
                        result["snippet_lines_parsed"] = []
                else:
                    result["snippet_lines_parsed"] = []

            return results

        except Exception as e:
            logger.error(f"Error getting {connection_type} connections: {e}")
            return []

    def _filter_connections_by_lines(
        self, connections: List[Dict[str, Any]], start_line: int, end_line: int
    ) -> List[Dict[str, Any]]:
        """
        Filter connections based on line overlap with fetched code.

        Args:
            connections: List of connections
            start_line: Start line of fetched code
            end_line: End line of fetched code

        Returns:
            Filtered list of connections that overlap with the line range
        """
        try:
            filtered_connections = []

            for conn in connections:
                snippet_lines = conn.get("snippet_lines_parsed", [])

                if not snippet_lines:
                    # If no line info in connection, include it
                    filtered_connections.append(conn)
                    continue

                # Check if connection lines overlap with fetched code lines
                if self._lines_overlap(snippet_lines, start_line, end_line):
                    filtered_connections.append(conn)

            return filtered_connections

        except Exception as e:
            logger.error(f"Error filtering connections by lines: {e}")
            return connections

    def _lines_overlap(
        self, snippet_lines: List[int], start_line: int, end_line: int
    ) -> bool:
        """
        Check if snippet lines overlap with the given line range.

        Args:
            snippet_lines: List of line numbers from connection
            start_line: Start line of fetched code
            end_line: End line of fetched code

        Returns:
            True if there's overlap, False otherwise
        """
        try:
            if not snippet_lines:
                return False

            snippet_start = min(snippet_lines)
            snippet_end = max(snippet_lines)

            # Check for overlap: ranges overlap if start1 <= end2 and start2 <= end1
            return snippet_start <= end_line and start_line <= snippet_end

        except Exception as e:
            logger.debug(f"Error checking line overlap: {e}")
            return False

    def _add_mapped_connections(
        self, connections: List[Dict[str, Any]], connection_type: str
    ) -> List[Dict[str, Any]]:
        """
        Add mapped connections (incoming->outgoing or outgoing->incoming) for each connection.
        Return all connections with mapped_connections field added (empty list if no mappings).

        Args:
            connections: List of connections
            connection_type: "incoming" or "outgoing"

        Returns:
            All connections with mapped_connections field added
        """
        try:
            for conn in connections:
                conn_id = conn["id"]
                mapped_connections = self._get_mapped_connections(
                    conn_id, connection_type
                )
                conn["mapped_connections"] = mapped_connections

                if mapped_connections:
                    logger.debug(
                        f"Connection {conn_id} has {len(mapped_connections)} mappings"
                    )
                else:
                    logger.debug(f"Connection {conn_id} has no mappings")

            return connections

        except Exception as e:
            logger.error(f"Error adding mapped connections: {e}")
            return connections

    def _get_mapped_connections(
        self, connection_id: int, connection_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get mapped connections for a specific connection ID.

        Args:
            connection_id: ID of the connection
            connection_type: "incoming" or "outgoing"

        Returns:
            List of mapped connections
        """
        try:
            if connection_type == "incoming":
                # For incoming connections, find outgoing connections that map to it
                query = """
                    SELECT cm.id as mapping_id, cm.connection_type, cm.description as mapping_description,
                          cm.match_confidence, cm.created_at as mapping_created_at,
                          oc.id as outgoing_id, oc.description as outgoing_description,
                          oc.code_snippet as outgoing_code_snippet, oc.technology_name as outgoing_technology,
                          files.file_path as outgoing_file_path, files.language as outgoing_language
                    FROM connection_mappings cm
                    JOIN outgoing_connections oc ON cm.sender_id = oc.id
                    LEFT JOIN files ON oc.file_id = files.id
                    WHERE cm.receiver_id = ?
                    ORDER BY cm.match_confidence DESC, cm.created_at DESC
                """
                params = (connection_id,)
            else:
                # For outgoing connections, find incoming connections that it maps to
                query = """
                    SELECT cm.id as mapping_id, cm.connection_type, cm.description as mapping_description,
                          cm.match_confidence, cm.created_at as mapping_created_at,
                          ic.id as incoming_id, ic.description as incoming_description,
                          ic.code_snippet as incoming_code_snippet, ic.technology_name as incoming_technology,
                          files.file_path as incoming_file_path, files.language as incoming_language
                    FROM connection_mappings cm
                    JOIN incoming_connections ic ON cm.receiver_id = ic.id
                    LEFT JOIN files ON ic.file_id = files.id
                    WHERE cm.sender_id = ?
                    ORDER BY cm.match_confidence DESC, cm.created_at DESC
                """
                params = (connection_id,)

            results = self.connection.execute_query(query, params)
            return results

        except Exception as e:
            logger.error(f"Error getting mapped connections for {connection_id}: {e}")
            return []

    def _generate_connection_note(
        self, connections: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Generate a note about connections and their implications for code changes.

        Args:
            connections: Dictionary with incoming and outgoing connections

        Returns:
            Note string for the user
        """
        try:
            incoming_count = len(connections.get("incoming", []))
            outgoing_count = len(connections.get("outgoing", []))

            if incoming_count == 0 and outgoing_count == 0:
                return ""

            note_parts = []

            if incoming_count > 0:
                note_parts.append(f"{incoming_count} incoming connection(s)")

            if outgoing_count > 0:
                note_parts.append(f"{outgoing_count} outgoing connection(s)")

            connection_summary = " and ".join(note_parts)

            # Check if any connections have mappings
            has_mappings = False
            for conn_list in connections.values():
                for conn in conn_list:
                    if conn.get("mapped_connections"):
                        has_mappings = True
                        break
                if has_mappings:
                    break

            note = f"CONNECTIONS FOUND: This code has {connection_summary}."

            if has_mappings:
                note += " Some connections have mapped relationships."

            note += " If you make changes to this code, consider updating the related connections to maintain system consistency."

            return note

        except Exception as e:
            logger.error(f"Error generating connection note: {e}")
            return "🔗 Connection information available but could not generate note."

    def format_connections_for_display(self, connection_info: Dict[str, Any]) -> str:
        """
        Format connection information for display in database results.

        Args:
            connection_info: Connection information dictionary

        Returns:
            Formatted string for display
        """
        try:
            if not connection_info:
                return ""

            output_parts = []

            for result_key, info in connection_info.items():
                result_num = result_key.replace("result_", "")
                output_parts.append(f"\n=== CONNECTIONS FOR RESULT {result_num} ===")

                if info.get("note"):
                    output_parts.append(info["note"])

                # Format incoming connections
                incoming = info.get("connections", {}).get("incoming", [])
                if incoming:
                    output_parts.append(f"\n📥 INCOMING CONNECTIONS ({len(incoming)}):")
                    for i, conn in enumerate(incoming, 1):
                        output_parts.append(
                            f"  {i}. {conn.get('description', 'No description')}"
                        )
                        output_parts.append(
                            f"     Technology: {conn.get('technology_name', 'Unknown')}"
                        )
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")

                        # Show mapped connections
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(
                                f"     ↔️ Mapped to {len(mapped)} outgoing connection(s)"
                            )

                # Format outgoing connections
                outgoing = info.get("connections", {}).get("outgoing", [])
                if outgoing:
                    output_parts.append(f"\n📤 OUTGOING CONNECTIONS ({len(outgoing)}):")
                    for i, conn in enumerate(outgoing, 1):
                        output_parts.append(
                            f"  {i}. {conn.get('description', 'No description')}"
                        )
                        output_parts.append(
                            f"     Technology: {conn.get('technology_name', 'Unknown')}"
                        )
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")

                        # Show mapped connections
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(
                                f"     ↔️ Mapped to {len(mapped)} incoming connection(s)"
                            )

            return "\n".join(output_parts)

        except Exception as e:
            logger.error(f"Error formatting connections for display: {e}")
            return "\n🔗 Connection information available but could not format for display."
