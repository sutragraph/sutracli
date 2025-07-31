"""
SQLite database connection and operations for code extraction data.
Stores files, code blocks, and relationships from code parsing.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger

from config import config
from queries.extraction_queries import (
    CREATE_PROJECTS_TABLE,
    CREATE_FILES_TABLE,
    CREATE_CODE_BLOCKS_TABLE,
    CREATE_RELATIONSHIPS_TABLE,
    CREATE_INDEXES,
    INSERT_PROJECT,
    INSERT_FILE,
    INSERT_CODE_BLOCK,
    INSERT_RELATIONSHIP,
    GET_ALL_PROJECTS,
    GET_FILE_BY_PATH,
    GET_BLOCKS_BY_FILE,
    GET_PROJECT_BLOCK_COUNT,
    DELETE_PROJECT_RELATIONSHIPS,
    DELETE_PROJECT_BLOCKS,
    DELETE_PROJECT_FILES,
    GET_BLOCK_STATS_BY_TYPE,
    GET_RELATIONSHIP_STATS_BY_TYPE,
    GET_FILES_BY_LANGUAGE,
    GET_FILES_BY_PROJECT,
)


class SQLiteConnection:
    """Manages SQLite database connections and operations."""

    def __init__(self):
        self.database_path = config.sqlite.knowledge_graph_db
        self.connection = self._connect()
        if config.sqlite.create_tables:
            self._create_tables()

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
        tables_sql = [
            # Projects table
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                language TEXT,
                version TEXT,
                created_at TEXT,
                updated_at TEXT,
                source_file TEXT
            )
            """,
            # File hashes table - tracks file content changes
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_size INTEGER,
                language TEXT,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, file_path),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """,
            # Nodes table - stores all tree-sitter nodes
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                node_type TEXT NOT NULL,
                name TEXT,
                name_lower TEXT,
                file_hash_id INTEGER,
                lines TEXT,
                code_snippet TEXT,
                properties TEXT,
                UNIQUE(node_id, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (file_hash_id) REFERENCES file_hashes(id) ON DELETE SET NULL
            )
            """,
            # Relationships table - stores edges between nodes
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node_id INTEGER NOT NULL,
                to_node_id INTEGER,
                project_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                properties TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (from_node_id, project_id) REFERENCES nodes(node_id, project_id) ON DELETE CASCADE,
                FOREIGN KEY (to_node_id, project_id) REFERENCES nodes(node_id, project_id) ON DELETE CASCADE
            )
            """,
            # Cross-index tables for connection tracking (updated schema)
            """
            CREATE TABLE IF NOT EXISTS incoming_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                file_hash_id INTEGER,
                snippet_lines TEXT,
                technology_name TEXT,
                code_snippet TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (file_hash_id) REFERENCES file_hashes(id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS outgoing_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                file_hash_id INTEGER,
                snippet_lines TEXT,
                technology_name TEXT,
                code_snippet TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (file_hash_id) REFERENCES file_hashes(id) ON DELETE SET NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS connection_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                connection_type TEXT NOT NULL,
                description TEXT,
                match_confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES outgoing_connections(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES incoming_connections(id) ON DELETE CASCADE
            )
            """,
        ]

        for sql in tables_sql:
            self.connection.execute(sql)

        # Handle database migrations for existing tables
        self._handle_database_migrations()

        self.connection.commit()
        logger.debug("Database tables created/verified")

    def _handle_database_migrations(self) -> None:
        """Handle database schema migrations for existing databases."""
        try:
            # Check if code_snippet column exists in incoming_connections table
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA table_info(incoming_connections)")
            incoming_columns = [row[1] for row in cursor.fetchall()]

            if "code_snippet" not in incoming_columns:
                logger.info("Adding code_snippet column to incoming_connections table")
                self.connection.execute(
                    "ALTER TABLE incoming_connections ADD COLUMN code_snippet TEXT"
                )

            # Check if code_snippet column exists in outgoing_connections table
            cursor.execute("PRAGMA table_info(outgoing_connections)")
            outgoing_columns = [row[1] for row in cursor.fetchall()]

            if "code_snippet" not in outgoing_columns:
                logger.info("Adding code_snippet column to outgoing_connections table")
                self.connection.execute(
                    "ALTER TABLE outgoing_connections ADD COLUMN code_snippet TEXT"
                )

            logger.debug("Database migrations completed")

        except Exception as e:
            logger.warning(f"Database migration failed (tables may not exist yet): {e}")

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

    def insert_project(self, project_data: Dict[str, Any]) -> int:
        """Insert or replace a project. Returns project ID."""
        try:
            cursor = self.connection.execute(
                """
                INSERT OR REPLACE INTO projects (name, description, language, version, created_at, updated_at, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project_data["name"],
                    project_data.get("description"),
                    project_data.get("language"),
                    project_data.get("version"),
                    project_data.get("created_at"),
                    project_data.get("updated_at"),
                    project_data.get("source_file"),
                ),
            )

            self.connection.commit()
            project_id = cursor.lastrowid
            if project_id is None:
                raise ValueError("Failed to get project ID after insertion")
            print(f"Inserted project '{project_data['name']}' with ID: {project_id}")
            return project_id

        except Exception as e:
            logger.error(f"Error inserting project {project_data['name']}: {e}")
            raise

    def list_all_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the database."""
        try:
            return self.execute_query("SELECT * FROM projects ORDER BY name")
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []

    def clear_database(self, force_clear: bool = False) -> None:
        """
        Completely clear the database by dropping all tables.

        Args:
            force_clear: If True, will clear even if data exists.
                        If False, will check for data first.
        """
        try:
            # Check if there's data in the database first (unless forced)
            if not force_clear:
                try:
                    # Quick check for any data
                    cursor = self.connection.cursor()
                    cursor.execute("SELECT COUNT(*) FROM code_blocks LIMIT 1")
                    block_count = cursor.fetchone()[0]
                    if block_count > 0:
                        logger.warning(
                            f"Database contains {block_count} code blocks. Use force_clear=True to override."
                        )
                        return
                except Exception:
                    # Tables might not exist, that's okay - proceed with clearing
                    pass

            # Disable foreign key constraints temporarily to allow dropping tables
            self.connection.execute("PRAGMA foreign_keys = OFF")

            # Get list of all tables
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            if not tables:
                logger.info("No tables found in database")
                # Re-enable foreign key constraints
                self.connection.execute("PRAGMA foreign_keys = ON")
                return

            # Drop all tables
            for table in tables:
                logger.debug(f"Attempting to drop table: {table}")
                table_name = table[0]
                if (
                    table_name != "sqlite_sequence"
                ):  # Don't drop SQLite's internal table
                    try:
                        self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                        logger.debug(f"Dropped table: {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to drop table {table_name}: {e}")

            # Re-enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")

            # Reset SQLite sequence table if it exists
            try:
                self.connection.execute("DELETE FROM sqlite_sequence")
            except Exception:
                # sqlite_sequence might not exist, that's okay
                pass

            self.connection.commit()
            print("🗑️ Database completely cleared - all tables dropped")

        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            # Don't re-raise the exception, just log it
            # This allows the operation to continue even if clearing partially fails

    def create_indexes(self) -> None:
        """Create indexes for better performance (indexes are now created in _create_tables)."""
        logger.debug("Indexes are automatically created with tables")

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

    def execute_batch_insert(self, query: str, parameters_list: List[tuple]) -> None:
        """Execute a query with multiple parameter sets in batches."""
        total_batches = len(list(chunk_list(parameters_list, config.sqlite.batch_size)))

        for batch_idx, batch_params in enumerate(
            chunk_list(parameters_list, config.sqlite.batch_size)
        ):
            retry_count = 0

            while retry_count < config.sqlite.max_retry_attempts:
                try:
                    cursor = self.connection.cursor()
                    cursor.executemany(query, batch_params)
                    self.connection.commit()

                    logger.debug(f"Completed batch {batch_idx + 1}/{total_batches}")
                    break

                except Exception as e:
                    retry_count += 1
                    if retry_count >= config.sqlite.max_retry_attempts:
                        logger.error(
                            f"Failed to execute batch after {config.sqlite.max_retry_attempts} retries: {e}"
                        )
                        raise

                    logger.warning(
                        f"Batch execution failed, retrying ({retry_count}/{config.sqlite.max_retry_attempts}): {e}"
                    )
                    time.sleep(1)  # Brief delay before retry

    def get_project_block_count(self, project_name: str) -> int:
        """Get count of code blocks for a specific project."""
        try:
            # First get project_id from project_name
            project_result = self.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            if not project_result:
                return 0

            project_id = project_result[0]["id"]
            result = self.execute_query(GET_PROJECT_BLOCK_COUNT, (project_id,))
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

            # Get project_id from project_name
            project_result = self.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            if not project_result:
                return 0

            project_id = project_result[0]["id"]

            # Delete relationships first (foreign key constraints)
            self.connection.execute(
                DELETE_PROJECT_RELATIONSHIPS, (project_id, project_id)
            )

            # Delete code blocks (will cascade to delete relationships)
            self.connection.execute(DELETE_PROJECT_BLOCKS, (project_id,))

            # Delete files
            self.connection.execute(DELETE_PROJECT_FILES, (project_id,))

            self.connection.commit()

            logger.info(
                f"Deleted {block_count} code blocks for project '{project_name}'"
            )
            return block_count

        except Exception as e:
            logger.error(f"Failed to delete project data: {e}")
            raise

    def list_all_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the database."""
        try:
            return self.execute_query(GET_ALL_PROJECTS)
        except Exception as e:
            logger.debug(f"Failed to list projects (table might not exist): {e}")
            return []

    def get_project_id_by_name(self) -> Optional[int]:
        """Get project ID by project name."""
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

    def insert_project(self, project_data: Dict[str, Any]) -> int:
        """Insert or replace a project. Returns project ID."""
        try:
            cursor = self.connection.execute(
                INSERT_PROJECT,
                (
                    project_data["name"],
                    project_data.get("version", "1.0.0"),
                ),
            )

            self.connection.commit()
            project_id = cursor.lastrowid
            if project_id is None:
                raise ValueError("Failed to get project ID after insertion")
            print(f"🏷️ Inserted project '{project_data['name']}' with ID: {project_id}")
            return project_id

        except Exception as e:
            logger.error(f"Error inserting project {project_data['name']}: {e}")
            raise

    def insert_file(self, file_data: Dict[str, Any]) -> int:
        """Insert a new file. Returns file ID."""
        try:
            cursor = self.connection.execute(
                INSERT_FILE,
                (
                    file_data["id"],
                    file_data["project_id"],
                    file_data["file_path"],
                    file_data["language"],
                    file_data["content"],
                    file_data["content_hash"],
                ),
            )

            self.connection.commit()
            logger.debug(
                f"Inserted file {file_data['file_path']} with ID: {file_data['id']}"
            )
            return file_data["id"]

        except Exception as e:
            logger.error(f"Error inserting file {file_data['file_path']}: {e}")
            raise

    def get_file_by_path(
        self, project_id: int, file_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get file information by file path.

        Args:
            project_id: Project ID
            file_path: File path to lookup

        Returns:
            File information dictionary or None
        """
        try:
            result = self.execute_query(
                """
                SELECT id, project_id, file_path, language, content, content_hash
                FROM files
                WHERE project_id = ? AND file_path = ?
                """,
                (project_id, file_path),
            )
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error getting file for {file_path}: {e}")
            return None

    def insert_code_block(self, block_data: Dict[str, Any]) -> int:
        """Insert a new code block. Returns block ID."""
        try:
            cursor = self.connection.execute(
                INSERT_CODE_BLOCK,
                (
                    block_data["id"],
                    block_data["file_id"],
                    block_data.get("parent_block_id"),
                    block_data["type"],
                    block_data["name"],
                    block_data["content"],
                    block_data["start_line"],
                    block_data["end_line"],
                    block_data["start_col"],
                    block_data["end_col"],
                ),
            )

            self.connection.commit()
            logger.debug(
                f"Inserted code block {block_data['name']} with ID: {block_data['id']}"
            )
            return block_data["id"]

        except Exception as e:
            logger.error(f"Error inserting code block {block_data['name']}: {e}")
            raise

    def insert_relationship(self, relationship_data: Dict[str, Any]) -> int:
        """Insert a new relationship. Returns relationship ID."""
        try:
            cursor = self.connection.execute(
                INSERT_RELATIONSHIP,
                (
                    relationship_data["source_id"],
                    relationship_data["target_id"],
                    relationship_data["type"],
                    relationship_data.get("metadata"),
                ),
            )

            self.connection.commit()
            relationship_id = cursor.lastrowid
            logger.debug(f"Inserted relationship with ID: {relationship_id}")
            return relationship_id

        except Exception as e:
            logger.error(f"Error inserting relationship: {e}")
            raise

    def get_all_blocks_from_file(
        self, file_path: str, project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all code blocks from a specific file."""
        try:
            if project_id:
                query = """
                SELECT cb.id, cb.type, cb.name, cb.content, cb.start_line, cb.end_line,
                       cb.start_col, cb.end_col, cb.parent_block_id, f.file_path, f.language
                FROM code_blocks cb
                JOIN files f ON cb.file_id = f.id
                WHERE f.file_path = ? AND f.project_id = ?
                ORDER BY cb.start_line
                """
                result = self.execute_query(query, (file_path, project_id))
            else:
                query = """
                SELECT cb.id, cb.type, cb.name, cb.content, cb.start_line, cb.end_line,
                       cb.start_col, cb.end_col, cb.parent_block_id, f.file_path, f.language
                FROM code_blocks cb
                JOIN files f ON cb.file_id = f.id
                WHERE f.file_path = ?
                ORDER BY cb.start_line
                """
                result = self.execute_query(query, (file_path,))

            logger.info(f"📂 Found {len(result)} code blocks in file '{file_path}'")
            return result

        except Exception as e:
            logger.error(f"Error getting blocks from file: {e}")
            return []


class GraphOperations:
    """High-level graph operations for inserting code extraction data."""

    def __init__(self, connection: SQLiteConnection):
        self.connection = connection

    def insert_extraction_data(
        self, extraction_data: Dict[str, Any], project_id: int
    ) -> None:
        """Insert complete extraction data (files, blocks, relationships) from JSON export."""
        print(f"🏗️ Inserting extraction data for project ID: {project_id}")

        files_data = ast_data.get("files", {})
        print(f"📁 Processing {len(files_data)} files...")

        # Prepare insert query
        insert_sql = """
        INSERT OR REPLACE INTO nodes (
            node_id, project_id, node_type, name, name_lower, file_hash_id, lines,
            code_snippet, properties
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        parameters_list = []
        for node in nodes:
            # Convert lists and dicts to JSON strings
            lines_json = json.dumps(node.lines) if node.lines else None
            properties_json = json.dumps(node.properties) if node.properties else None

            # Use file_hash_id as is - database foreign key constraint will handle invalid references
            file_hash_id = node.file_hash_id

            # Debug logging for file_hash_id
            if file_hash_id is not None:
                logger.debug(f"Node {node.node_id} has file_hash_id: {file_hash_id}")

            parameters_list.append(
                (
                    node.node_id,
                    project_id,
                    node.node_type,
                    node.name,  # Keep original case for name
                    (
                        node.name.lower() if node.name else None
                    ),  # Store lowercase version for case-insensitive search
                    file_hash_id,
                    lines_json,
                    node.code_snippet,
                    properties_json,
                )
            )

        try:
            self.connection.execute_batch_insert(insert_sql, parameters_list)
            print(f"✅ Successfully inserted {len(nodes)} nodes")
        except Exception as e:
            logger.error(f"Failed to insert nodes: {e}")
            # Log some sample data for debugging
            if parameters_list:
                logger.error(f"Sample node data: {parameters_list[0]}")
            raise

    def insert_relationships(
        self, relationships: List[SQLiteRelationship], project_id: int
    ) -> None:
        """Insert relationships into the database."""
        if not relationships:
            return

        print(f"🔗 Inserting {len(relationships)} relationships...")

        # Prepare insert query
        insert_sql = """
        INSERT OR REPLACE INTO relationships (
            from_node_id, to_node_id, project_id, relationship_type, properties
        ) VALUES (?, ?, ?, ?, ?)
        """

        parameters_list = []
        for rel in relationships:
            properties_json = json.dumps(rel.properties) if rel.properties else None

            # Debug: Log each relationship being prepared for insertion
            logger.debug(
                f"🔗 Preparing relationship: {rel.from_node_id} -> {rel.to_node_id} ({rel.relationship_type})"
            )

            # Debug: Check if nodes exist before insertion
            from_exists = self.connection.execute_query(
                "SELECT 1 FROM nodes WHERE node_id = ? AND project_id = ?",
                (rel.from_node_id, project_id),
            )
            to_exists = True  # Assume external refs are OK
            if rel.to_node_id is not None:
                to_exists = self.connection.execute_query(
                    "SELECT 1 FROM nodes WHERE node_id = ? AND project_id = ?",
                    (rel.to_node_id, project_id),
                )

            if not from_exists:
                logger.error(f"❌ FROM node {rel.from_node_id} does not exist!")
            if rel.to_node_id is not None and not to_exists:
                logger.error(f"❌ TO node {rel.to_node_id} does not exist!")

            parameters_list.append(
                (
                    rel.from_node_id,
                    rel.to_node_id,
                    project_id,
                    rel.relationship_type,
                    properties_json,
                )
            )

        self.connection.execute_batch_insert(insert_sql, parameters_list)
        print(f"✅ Successfully inserted {len(relationships)} relationships")

    def insert_graph_data(
        self, graph_data: GraphData, project_data: Dict[str, Any]
    ) -> None:
        """Insert complete graph data (nodes and relationships)."""
        print(
            f"🏗️ Inserting graph with {len(graph_data.nodes)} nodes and {len(graph_data.relationships)} relationships"
        )

        # Get the project ID from the graph data (it should already be set correctly)
        if graph_data.nodes:
            project_id = graph_data.nodes[0].project_id
            print(f"🆔 Using existing project ID from graph data: {project_id}")
        else:
            # Fallback: Insert project and get its ID
            project_id = self.connection.insert_project(project_data)
            print(f"🏷️ Created new project with ID: {project_id}")

        # Verify project exists
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

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get comprehensive extraction statistics."""
        try:
            # Block counts by type
            block_stats_result = self.connection.execute_query(GET_BLOCK_STATS_BY_TYPE)
            block_stats = {row["type"]: row["count"] for row in block_stats_result}

            # Relationship counts by type
            rel_stats_result = self.connection.execute_query(
                GET_RELATIONSHIP_STATS_BY_TYPE
            )
            rel_stats = {row["type"]: row["count"] for row in rel_stats_result}

            # Files by language
            file_lang_result = self.connection.execute_query(GET_FILES_BY_LANGUAGE)
            file_by_language = {
                row["language"]: row["count"] for row in file_lang_result
            }

            # Files by project
            file_by_project_result = self.connection.execute_query(GET_FILES_BY_PROJECT)
            file_by_project = {
                row["project_name"]: row["count"] for row in file_by_project_result
            }

            return {
                "total_files": self.get_file_count(),
                "total_blocks": self.get_block_count(),
                "total_relationships": self.get_relationship_count(),
                "block_types": block_stats,
                "relationship_types": rel_stats,
                "files_by_language": file_by_language,
                "files_by_project": file_by_project,
            }
        except Exception:
            # Tables might not exist (e.g., after clearing database)
            return {
                "total_files": 0,
                "total_blocks": 0,
                "total_relationships": 0,
                "block_types": {},
                "relationship_types": {},
                "files_by_language": {},
                "files_by_project": {},
            }
