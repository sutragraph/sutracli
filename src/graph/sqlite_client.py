"""
SQLite database connection and operations for code extraction data.
Stores files, code blocks, and relationships from code parsing.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from loguru import logger

from config import config
from models import File, Project, CodeBlock, Relationship, ExtractionData
from utils import chunk_list
from queries.creation_queries import CREATE_TABLES, CREATE_INDEXES


class SQLiteConnection:
    """Manages SQLite database connections and operations."""

    def __init__(self):
        self.database_path = config.sqlite.knowledge_graph_db
        self.connection = self._connect()
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

    def get_project(self, project_name: str) -> Union[Project | None]:
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
            logger.debug(f"Inserted code block '{block.name}' with ID: {block.id}, file_id: {block.file_id}, parent_id: {block.parent_block_id}")
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

    # Duplicate method removed - already defined above

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
                    self.connection.rollback()
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


# Duplicate method removed - already defined above


class GraphOperations:
    """High-level operations for inserting code extraction data."""

    def __init__(self, connection: SQLiteConnection):
        self.connection = connection

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
