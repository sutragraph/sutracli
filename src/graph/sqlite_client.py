"""
SQLite database connection and operations for code extraction data.
Stores files, code blocks, and relationships from code parsing.
"""

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# This block is only read by type checkers, not at runtime
if TYPE_CHECKING:
    import sqlite3
# This block is only executed at runtime, not by type checkers
else:
    import pysqlite3 as sqlite3

from loguru import logger

from config import config
from models import CodeBlock, File, Project, Relationship
from queries.creation_queries import CREATE_INDEXES, CREATE_TABLES


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

            # Enable WAL mode for better concurrency
            connection.execute("PRAGMA journal_mode=WAL")

            # Set busy timeout to handle concurrent access
            connection.execute(
                f"PRAGMA busy_timeout={config.sqlite.connection_timeout * 1000}"
            )

            # Enable foreign key constraints
            connection.execute("PRAGMA foreign_keys=ON")

            # Optimize for concurrent reads
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA cache_size=10000")
            connection.execute("PRAGMA temp_store=memory")

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
            logger.debug("Database connection closed")

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
                "SELECT id, name, path, description, created_at, updated_at, cross_indexing_done FROM projects WHERE name = ?",
                (project_name,),
            )
            if result:
                row = result[0]
                return Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    cross_indexing_done=bool(row.get("cross_indexing_done", 0)),
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
            logger.debug(f"Deleted project '{project_name}' and associated data")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to delete project '{project_name}': {e}")
            raise

    def insert_project(self, project: Project) -> int:
        """Insert or replace a project. Returns project ID."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO projects
                   (name, path, created_at, updated_at, cross_indexing_done)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    project.name,
                    project.path,
                    project.created_at,
                    project.updated_at,
                    project.cross_indexing_done,
                ),
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
                "SELECT id, name, path, description, created_at, updated_at, cross_indexing_done FROM projects ORDER BY name"
            )
            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    cross_indexing_done=bool(row.get("cross_indexing_done", 0)),
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

            logger.debug("Database cleared and tables recreated")

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

            logger.debug(
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
