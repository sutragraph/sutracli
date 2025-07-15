"""
SQLite database connection and operations for tree-sitter data.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger

from config import config
from models import SQLiteNode, SQLiteRelationship, GraphData
from utils import chunk_list
from queries.agent_queries import GET_ALL_NODES_FROM_FILE


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
        """Create necessary tables for storing tree-sitter data."""
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
                name_lower TEXT, -- For case-insensitive search
                file_hash_id INTEGER,
                lines TEXT, -- JSON array as text [start_line, end_line]
                code_snippet TEXT,
                properties TEXT, -- JSON object as text for additional properties
                UNIQUE(node_id, project_id), -- Ensure node_id is unique within project
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
                properties TEXT, -- JSON object as text for additional properties
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (from_node_id, project_id) REFERENCES nodes(node_id, project_id) ON DELETE CASCADE,
                FOREIGN KEY (to_node_id, project_id) REFERENCES nodes(node_id, project_id) ON DELETE CASCADE
            )
            """,
        ]

        for sql in tables_sql:
            self.connection.execute(sql)

        self.connection.commit()
        logger.debug("Database tables created/verified")

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, "connection") and self.connection:
            self.connection.close()
            logger.info("Database connection closed")

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
                    cursor.execute("SELECT COUNT(*) FROM nodes LIMIT 1")
                    node_count = cursor.fetchone()[0]
                    if node_count > 0:
                        logger.warning(
                            f"Database contains {node_count} nodes. Use force_clear=True to override."
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
        """Create indexes for better performance."""
        if not config.sqlite.enable_indexing:
            return

        indexes = [
            # Node indexes
            "CREATE INDEX IF NOT EXISTS idx_nodes_project_id ON nodes(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_node_type ON nodes(node_type)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_name_lower ON nodes(name_lower)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_file_hash_id ON nodes(file_hash_id)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_composite ON nodes(node_id, project_id)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_lines ON nodes(lines)",
            # Relationship indexes
            "CREATE INDEX IF NOT EXISTS idx_relationships_project_id ON relationships(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_from_node ON relationships(from_node_id)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_to_node ON relationships(to_node_id)",
            # File hashes indexes
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_project_id ON file_hashes(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_file_path ON file_hashes(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_file_hashes_name ON file_hashes(name)",
            # Project indexes
            "CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)",
            "CREATE INDEX IF NOT EXISTS idx_projects_language ON projects(language)",
        ]

        for index_sql in indexes:
            try:
                self.connection.execute(index_sql)
                logger.debug(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")

        self.connection.commit()
        logger.debug("✅ Database indexes created")

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

    def get_project_node_count(self, project_name: str) -> int:
        """Get count of nodes for a specific project."""
        try:
            # First get project_id from project_name
            project_result = self.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            if not project_result:
                return 0

            project_id = project_result[0]["id"]
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM nodes WHERE project_id = ?",
                (project_id,),
            )
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get project node count: {e}")
            return 0

    def delete_project_nodes(self, project_name: str) -> int:
        """Delete all nodes for a specific project and return count deleted."""
        try:
            # Get count first
            node_count = self.get_project_node_count(project_name)

            if node_count == 0:
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
                "DELETE FROM relationships WHERE project_id = ?", (project_id,)
            )

            # Delete nodes
            self.connection.execute(
                "DELETE FROM nodes WHERE project_id = ?", (project_id,)
            )

            # Delete file hashes for the project
            self.connection.execute(
                "DELETE FROM file_hashes WHERE project_id = ?", (project_id,)
            )

            self.connection.commit()

            logger.info(f"Deleted {node_count} nodes for project '{project_name}'")
            return node_count

        except Exception as e:
            logger.error(f"Failed to delete project nodes: {e}")
            raise

    def list_all_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the database."""
        try:
            return self.execute_query(
                """
                SELECT name, description, language, version, created_at
                FROM projects
                ORDER BY name
                """
            )
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
            print(f"🏷️ Inserted project '{project_data['name']}' with ID: {project_id}")
            return project_id

        except Exception as e:
            logger.error(f"Error inserting project {project_data['name']}: {e}")
            raise

    def insert_file_hash(
        self,
        project_id: int,
        file_path: str,
        content_hash: str,
        file_size: Optional[int] = None,
        language: Optional[str] = None,
        name: Optional[str] = None,
    ) -> int:
        """Insert a new file hash. Returns file hash ID."""
        try:
            # Use INSERT OR IGNORE to handle duplicates gracefully
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO file_hashes 
                (project_id, file_path, content_hash, file_size, language, name)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (project_id, file_path, content_hash, file_size, language, name),
            )

            self.connection.commit()

            # If lastrowid is None, it means the record already existed
            if cursor.lastrowid is None:
                # Get the existing record ID
                existing = self.get_file_hash_by_path(project_id, file_path)
                if existing:
                    file_hash_id = existing["file_hash_id"]
                    logger.debug(
                        f"Found existing file hash {file_hash_id} for {file_path} in project {project_id}"
                    )
                else:
                    logger.error(f"Could not find or create file hash for {file_path}")
                    return 0
            else:
                file_hash_id = cursor.lastrowid
                logger.debug(
                    f"Inserted new file hash {file_hash_id} for {file_path} in project {project_id}"
                )

            return int(file_hash_id) if file_hash_id else 0

        except Exception as e:
            logger.error(f"Error inserting file hash for {file_path}: {e}")
            raise

    def get_file_hash_by_path(
        self, project_id: int, file_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get file hash information by file path.

        Args:
            project_id: Project ID
            file_path: File path to lookup

        Returns:
            File hash information dictionary or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT id, content_hash, file_size, language, name, created_at, updated_at
                FROM file_hashes 
                WHERE project_id = ? AND file_path = ?
            """,
                (project_id, file_path),
            )

            result = cursor.fetchone()
            if result:
                return {
                    "file_hash_id": result[0],
                    "content_hash": result[1],
                    "file_size": result[2],
                    "language": result[3],
                    "name": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                }
            return None

        except Exception as e:
            logger.error(f"Error getting file hash for {file_path}: {e}")
            return None

    def get_or_create_file_hash(
        self,
        project_id: int,
        file_path: str,
        content_hash: str,
        file_size: Optional[int] = None,
        language: Optional[str] = None,
        name: Optional[str] = None,
    ) -> int:
        """Get existing file hash or create new one. Returns file hash ID."""
        try:
            # First try to get existing file hash
            existing = self.get_file_hash_by_path(project_id, file_path)

            if existing:
                # If content hash matches, return existing ID
                if existing["content_hash"] == content_hash:
                    logger.debug(
                        f"Found existing file hash {existing['file_hash_id']} for {file_path}"
                    )
                    return existing["file_hash_id"]
                else:
                    # Content changed, update the existing record
                    logger.debug(
                        f"Updating file hash for {file_path} due to content change"
                    )
                    cursor = self.connection.execute(
                        """
                        UPDATE file_hashes 
                        SET content_hash = ?, file_size = ?, language = ?, name = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE project_id = ? AND file_path = ?
                        """,
                        (
                            content_hash,
                            file_size,
                            language,
                            name,
                            project_id,
                            file_path,
                        ),
                    )
                    self.connection.commit()
                    return existing["file_hash_id"]
            else:
                # Create new file hash
                return self.insert_file_hash(
                    project_id=project_id,
                    file_path=file_path,
                    content_hash=content_hash,
                    file_size=file_size,
                    language=language,
                    name=name,
                )

        except Exception as e:
            logger.error(f"Error in get_or_create_file_hash for {file_path}: {e}")
            # Fallback to creating new entry
            try:
                return self.insert_file_hash(
                    project_id=project_id,
                    file_path=file_path,
                    content_hash=content_hash,
                    file_size=file_size,
                    language=language,
                    name=name,
                )
            except Exception as fallback_e:
                logger.error(
                    f"Fallback insert also failed for {file_path}: {fallback_e}"
                )
                return 0

    def get_all_nodes_from_file(
        self, file_path: str, project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all nodes from a specific file - faster than semantic search when you know the file."""
        try:
            cursor = self.connection.cursor()

            if project_id:
                query = GET_ALL_NODES_FROM_FILE + " AND n.project_id = ?"
                cursor.execute(query, (file_path, project_id))
            else:
                cursor.execute(GET_ALL_NODES_FROM_FILE, (file_path,))

            results = []
            for row in cursor.fetchall():
                # Parse lines JSON if available
                lines_data = row[3]
                start_line, end_line = None, None
                if lines_data:
                    try:
                        lines_parsed = json.loads(lines_data)
                        if isinstance(lines_parsed, list) and len(lines_parsed) >= 2:
                            start_line, end_line = lines_parsed[0], lines_parsed[1]
                    except:
                        pass

                results.append(
                    {
                        "node_id": row[0],
                        "node_type": row[1],
                        "name": row[2],
                        "start_line": start_line,
                        "end_line": end_line,
                        "content": row[4] or "",
                        "properties": row[5],
                        "file_path": row[6] or "",
                        "language": row[7],
                        "file_size": row[8],
                        "project_name": row[9],
                    }
                )

            logger.info(f"📂 Found {len(results)} nodes in file '{file_path}'")
            return results

        except Exception as e:
            logger.error(f"Error in file lookup: {e}")
            return []


class GraphOperations:
    """High-level graph operations for inserting nodes and relationships."""

    def __init__(self, connection: SQLiteConnection):
        self.connection = connection

    def insert_nodes(self, nodes: List[SQLiteNode], project_id: int) -> None:
        """Insert nodes into the database."""
        if not nodes:
            return

        print(f"🗃️ Inserting {len(nodes)} nodes...")

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
            logger.info(
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
                "SELECT id, name FROM projects WHERE id = ?", (project_id,)
            )
            if result:
                print(f"✅ Verified project exists: {result[0]}")
            else:
                logger.error(f"Project {project_id} not found!")
                raise ValueError(f"Project {project_id} not found")
        except Exception as e:
            logger.error(f"Error verifying project: {e}")
            raise

        # Insert nodes first
        self.insert_nodes(graph_data.nodes, project_id)

        # Then insert relationships
        self.insert_relationships(graph_data.relationships, project_id)

        print("📦 Graph data insertion completed")

    def get_node_count(self) -> int:
        """Get total number of nodes in the database."""
        try:
            result = self.connection.execute_query(
                "SELECT COUNT(*) as count FROM nodes"
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

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        try:
            # Node counts by type
            node_stats_result = self.connection.execute_query(
                """
                SELECT node_type, COUNT(*) as count
                FROM nodes
                GROUP BY node_type
                ORDER BY count DESC
            """
            )
            node_stats = {row["node_type"]: row["count"] for row in node_stats_result}

            # Relationship counts by type
            rel_stats_result = self.connection.execute_query(
                """
                SELECT relationship_type, COUNT(*) as count
                FROM relationships
                GROUP BY relationship_type
                ORDER BY count DESC
            """
            )
            rel_stats = {
                row["relationship_type"]: row["count"] for row in rel_stats_result
            }

            # File hash statistics
            file_hash_count_result = self.connection.execute_query(
                "SELECT COUNT(*) as count FROM file_hashes"
            )
            total_file_hashes = (
                file_hash_count_result[0]["count"] if file_hash_count_result else 0
            )

            # File hashes by project
            file_hash_by_project_result = self.connection.execute_query(
                """
                SELECT p.name as project_name, COUNT(fh.id) as count
                FROM projects p
                LEFT JOIN file_hashes fh ON p.id = fh.project_id
                GROUP BY p.id, p.name
                ORDER BY count DESC
                """
            )
            file_hash_by_project = {
                row["project_name"]: row["count"] for row in file_hash_by_project_result
            }

            return {
                "total_nodes": self.get_node_count(),
                "total_relationships": self.get_relationship_count(),
                "total_file_hashes": total_file_hashes,
                "node_types": node_stats,
                "relationship_types": rel_stats,
                "file_hashes_by_project": file_hash_by_project,
            }
        except Exception:
            # Tables might not exist (e.g., after clearing database)
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "total_file_hashes": 0,
                "node_types": {},
                "relationship_types": {},
                "file_hashes_by_project": {},
            }
