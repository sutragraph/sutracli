"""
GraphOperations class for high-level database operations.

This module contains the GraphOperations class which provides high-level
operations for inserting and querying code extraction data in the SQLite database.
It handles insertion of extraction data from JSON exports and provides various
query methods for retrieving code structure, relationships, and connections.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from queries.graph_queries import (
    GET_EXISTING_INCOMING_CONNECTIONS,
    GET_EXISTING_OUTGOING_CONNECTIONS,
    GET_CONNECTIONS_BY_IDS,
    INSERT_INCOMING_CONNECTION,
    INSERT_OUTGOING_CONNECTION,
    INSERT_CONNECTION_MAPPING,
    UPDATE_PROJECT_DESCRIPTION,
)
from models import File, CodeBlock, ExtractionData
from queries.agent_queries import (
    GET_CODE_BLOCK_BY_ID,
    GET_FILE_BY_ID,
    GET_FILE_BLOCK_SUMMARY,
    GET_CHILD_BLOCKS,
    GET_PARENT_BLOCK,
    GET_FILE_IMPACT_SCOPE,
    GET_FILE_IMPORTS,
    GET_DEPENDENCY_CHAIN,
    GET_EXTERNAL_CONNECTIONS,
    GET_PROJECT_EXTERNAL_CONNECTIONS,
    GET_CONNECTION_IMPACT,
    GET_EXTERNAL_CONNECTIONS_OVERLAPPING_RANGE,
    GET_IMPLEMENTATION_CONTEXT,
    GET_INCOMING_CONNECTIONS,
    GET_OUTGOING_CONNECTIONS,
)
from .sqlite_client import SQLiteConnection


class GraphOperations:
    """High-level operations for inserting code extraction data."""

    def __init__(self):
        # Import here to avoid circular import

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
        logger.debug(f"🏗️ Inserting extraction data for project ID: {project_id}")

        files_data = extraction_data.files
        print(f"📁 Processing {len(files_data)} files...")

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
                self.connection.insert_relationship(rel)

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

    def _get_file_id_by_path(self, file_path: str) -> Optional[int]:
        """Get file_id by file path with robust path resolution."""
        try:
            if not file_path:
                logger.warning("Empty file_path provided to _get_file_id_by_path")
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
                file_id = result[0]["id"]
                logger.debug(f"Found file_id {file_id} for {absolute_file_path}")
                return file_id

            if absolute_file_path != file_path:
                result = self.connection.execute_query(
                    "SELECT id FROM files WHERE file_path = ?",
                    (file_path,),
                )

                if result:
                    file_id = result[0]["id"]
                    logger.debug(
                        f"Found file_id {file_id} for {file_path} (original path)"
                    )
                    return file_id

            if file_path:
                result = self.connection.execute_query(
                    "SELECT id, file_path FROM files WHERE file_path LIKE ?",
                    (f"%{file_path}",),
                )

                if result:
                    file_id = result[0]["id"]
                    logger.debug(f"Found file_id {file_id} by filepath")
                    return file_id

            logger.warning(
                f"No file_id found for {file_path} (absolute: {absolute_file_path})"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting file_id for {file_path}: {e}")
            return None

    def _validate_line_range(
        self, start_line: Optional[int], end_line: Optional[int]
    ) -> Tuple[Optional[int], Optional[int]]:
        """Validate and normalize line range values."""
        try:
            if start_line is None or end_line is None:
                return None, None

            start_line = int(start_line)
            end_line = int(end_line)

            if start_line < 1 or end_line < 1 or start_line > end_line:
                return None, None

            return start_line, end_line
        except (ValueError, TypeError):
            return None, None

    def _get_connections_for_file_and_lines(
        self,
        file_id: int,
        start_line: Optional[int],
        end_line: Optional[int],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get incoming and outgoing connections for a specific file and line range.

        Args:
            file_id: File ID to search for
            start_line: Start line of the fetched code
            end_line: End line of the fetched code
            project_id: Optional project ID filter

        Returns:
            Dictionary with 'incoming' and 'outgoing' connection lists
        """
        try:
            connections = {"incoming": [], "outgoing": []}

            # Get incoming connections
            incoming_connections = self._get_connections_by_type("incoming", file_id)

            # Get outgoing connections
            outgoing_connections = self._get_connections_by_type("outgoing", file_id)

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
            logger.error(f"Error getting connections for file_id {file_id}: {e}")
            return {"incoming": [], "outgoing": []}

    def _get_connections_by_type(
        self,
        connection_type: str,
        file_id: int,
    ) -> List[Dict[str, Any]]:
        """Get connections of a specific type for a file."""
        try:
            # Use proper queries from agent_queries
            if connection_type == "incoming":
                query = GET_INCOMING_CONNECTIONS
            elif connection_type == "outgoing":
                query = GET_OUTGOING_CONNECTIONS
            else:
                logger.error(f"Unknown connection type: {connection_type}")
                return []

            results = self.connection.execute_query(query, (file_id,))

            # Parse snippet_lines JSON
            for result in results:
                if result.get("snippet_lines"):
                    try:
                        result["snippet_lines_parsed"] = json.loads(
                            result["snippet_lines"]
                        )
                    except BaseException:
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
                    SELECT cm.id as mapping_id, oc.technology_name, cm.description as mapping_description,
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
                    SELECT cm.id as mapping_id, ic.technology_name, cm.description as mapping_description,
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

    def _get_connection_mappings_for_display(
        self,
        file_id: int,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get connection mappings for display formatting with sender/receiver details.

        Args:
            file_id: File ID to get mappings for
            start_line: Optional start line filter
            end_line: Optional end line filter

        Returns:
            List of connection mappings with full sender/receiver details
        """
        try:
            # Query to get all mappings where either sender or receiver belongs to the file
            query = """
                SELECT
                    cm.id as mapping_id,
                    COALESCE(oc.technology_name, ic.technology_name) as technology_name,
                    cm.description as mapping_description,
                    cm.match_confidence,

                    -- Sender (outgoing) details
                    oc.id as sender_id,
                    oc.description as sender_description,
                    oc.code_snippet as sender_code_snippet,
                    oc.technology_name as sender_technology,
                    oc.snippet_lines as sender_snippet_lines,
                    sender_file.file_path as sender_file_path,
                    sender_file.language as sender_language,
                    sender_project.name as sender_project,

                    -- Receiver (incoming) details
                    ic.id as receiver_id,
                    ic.description as receiver_description,
                    ic.code_snippet as receiver_code_snippet,
                    ic.technology_name as receiver_technology,
                    ic.snippet_lines as receiver_snippet_lines,
                    receiver_file.file_path as receiver_file_path,
                    receiver_file.language as receiver_language,
                    receiver_project.name as receiver_project

                FROM connection_mappings cm
                JOIN outgoing_connections oc ON cm.sender_id = oc.id
                JOIN incoming_connections ic ON cm.receiver_id = ic.id
                LEFT JOIN files sender_file ON oc.file_id = sender_file.id
                LEFT JOIN files receiver_file ON ic.file_id = receiver_file.id
                LEFT JOIN projects sender_project ON sender_file.project_id = sender_project.id
                LEFT JOIN projects receiver_project ON receiver_file.project_id = receiver_project.id

                WHERE (oc.file_id = ? OR ic.file_id = ?)
                ORDER BY cm.match_confidence DESC, cm.created_at DESC
            """

            results = self.connection.execute_query(query, (file_id, file_id))

            # Filter by line range if specified
            if start_line is not None and end_line is not None:
                filtered_results = []
                for result in results:
                    # Check if either sender or receiver overlaps with the line range
                    sender_lines = self._parse_snippet_lines(
                        result.get("sender_snippet_lines") or ""
                    )
                    receiver_lines = self._parse_snippet_lines(
                        result.get("receiver_snippet_lines") or ""
                    )

                    # Include if either sender or receiver overlaps with the requested range
                    sender_overlaps = (
                        result.get("sender_file_path")
                        and sender_lines
                        and self._lines_overlap(sender_lines, start_line, end_line)
                    )
                    receiver_overlaps = (
                        result.get("receiver_file_path")
                        and receiver_lines
                        and self._lines_overlap(receiver_lines, start_line, end_line)
                    )

                    if sender_overlaps or receiver_overlaps:
                        filtered_results.append(result)

                return filtered_results
            else:
                return results

        except Exception as e:
            logger.error(f"Error getting connection mappings for display: {e}")
            return []

    def _parse_snippet_lines(self, snippet_lines_json: Optional[str]) -> List[int]:
        """Parse snippet_lines JSON string into list of integers."""
        try:
            if snippet_lines_json:
                import json

                return json.loads(snippet_lines_json)
            return []
        except BaseException:
            return []

    def get_enriched_block_context(self, block_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive context for a code block including file info and connections.

        Args:
            block_id: Database ID of the code block

        Returns:
            Dictionary with enriched block context or None if not found
        """
        try:
            block_data = self.resolve_block(block_id)
            if not block_data:
                return None

            # Get both connection mappings and basic connections
            connection_mappings = self._get_connection_mappings_for_display(
                block_data["file_id"], block_data["start_line"], block_data["end_line"]
            )
            basic_connections = self._get_connections_for_file_and_lines(
                block_data["file_id"], block_data["start_line"], block_data["end_line"]
            )

            # Filter out basic connections that are already represented in mappings
            filtered_connections = self._filter_unmapped_connections(
                basic_connections, connection_mappings, block_data["file_path"]
            )

            # Combine mappings and remaining basic connections
            connections = {}
            if connection_mappings:
                connections["mappings"] = connection_mappings
            if filtered_connections.get("incoming"):
                connections["incoming"] = filtered_connections["incoming"]
            if filtered_connections.get("outgoing"):
                connections["outgoing"] = filtered_connections["outgoing"]

            # Get parent/child relationships
            parent_info = None
            if block_data.get("parent_block_id"):
                parent_info = self.resolve_block(block_data["parent_block_id"])

            child_blocks = self.get_block_children(block_id)

            result = {
                "block": block_data,
                "connections": connections,
                "parent_block": parent_info,
                "child_blocks": child_blocks,
                "file_context": {
                    "file_path": block_data["file_path"],
                    "language": block_data["language"],
                    "project_name": block_data["project_name"],
                },
            }

            # Add connection mappings to the result if available
            if connection_mappings:
                result["connection_mappings"] = connection_mappings

            return result

        except Exception as e:
            logger.error(f"Error getting enriched block context for {block_id}: {e}")
            return None

    def get_enriched_file_context(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive context for a file including blocks and connections.

        Args:
            file_id: Database ID of the file

        Returns:
            Dictionary with enriched file context or None if not found
        """
        try:
            file_data = self.resolve_file(file_id)
            if not file_data:
                return None

            # Get both connection mappings and basic connections
            connection_mappings = self._get_connection_mappings_for_display(file_id, None, None)
            basic_connections = self._get_connections_for_file_and_lines(file_id, None, None)

            # Filter out basic connections that are already represented in mappings
            filtered_connections = self._filter_unmapped_connections(
                basic_connections, connection_mappings, file_data["file_path"]
            )

            # Combine mappings and remaining basic connections
            connections = {}
            if connection_mappings:
                connections["mappings"] = connection_mappings
            if filtered_connections.get("incoming"):
                connections["incoming"] = filtered_connections["incoming"]
            if filtered_connections.get("outgoing"):
                connections["outgoing"] = filtered_connections["outgoing"]



            result = {
                "file": file_data,
                "connections": connections,
            }

            # Add connection mappings to the result if available
            if connection_mappings:
                result["connection_mappings"] = connection_mappings

            return result

        except Exception as e:
            logger.error(f"Error getting enriched file context for {file_id}: {e}")
            return None

    # ============================================================================
    # ROADMAP AGENT QUERY METHODS
    # ============================================================================

    def resolve_block(self, block_id: int) -> Optional[Dict[str, Any]]:
        """Convert an embedding-derived block reference to full details."""
        try:
            results = self.connection.execute_query(GET_CODE_BLOCK_BY_ID, (block_id,))
            if not results:
                return None

            result = results[0]
            return {
                "id": result["id"],
                "type": result["type"],
                "name": result["name"],
                "content": result["content"],
                "start_line": result["start_line"],
                "end_line": result["end_line"],
                "start_col": result["start_col"],
                "end_col": result["end_col"],
                "parent_block_id": result["parent_block_id"],
                "file_id": result["file_id"],
                "file_path": result["file_path"],
                "language": result["language"],
                "project_name": result["project_name"],
                "project_id": result["project_id"],
            }
        except Exception as e:
            logger.error(f"Error resolving block {block_id}: {e}")
            return None

    def resolve_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Convert a file reference to file metadata and block count."""
        try:
            results = self.connection.execute_query(GET_FILE_BY_ID, (file_id,))
            if not results:
                return None

            result = results[0]
            return {
                "id": result["id"],
                "file_path": result["file_path"],
                "language": result["language"],
                "content": result["content"],
                "content_hash": result["content_hash"],
                "project_name": result["project_name"],
                "project_id": result["project_id"],
                "block_count": result["block_count"],
            }
        except Exception as e:
            logger.error(f"Error resolving file {file_id}: {e}")
            return None

    def get_implementation_context(self, file_id: int) -> List[Dict[str, Any]]:
        """Lightweight structure view for a file (ordered by lines)."""
        try:
            results = self.connection.execute_query(
                GET_IMPLEMENTATION_CONTEXT, (file_id,)
            )
            return [
                {
                    "id": result["id"],
                    "type": result["type"],
                    "name": result["name"],
                    "start_line": result["start_line"],
                    "end_line": result["end_line"],
                    "parent_name": result["parent_name"],
                    "parent_type": result["parent_type"],
                    "file_path": result["file_path"],
                    "language": result["language"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(
                f"Error getting implementation context for file {file_id}: {e}"
            )
            return []

    def get_connections_overlapping_range(
        self, file_id: int, start_line: int, end_line: int
    ) -> List[Dict[str, Any]]:
        """Fetch incoming/outgoing connections whose snippet_lines overlap the given line range."""
        try:
            results = self.connection.execute_query(
                GET_EXTERNAL_CONNECTIONS_OVERLAPPING_RANGE,
                (
                    file_id,
                    start_line,
                    end_line,
                    start_line,
                    end_line,
                    start_line,
                    end_line,
                    file_id,
                    start_line,
                    end_line,
                    start_line,
                    end_line,
                    start_line,
                    end_line,
                ),
            )
            return [
                {
                    "direction": result["direction"],
                    "description": result["description"],
                    "technology_name": result["technology_name"],
                    "snippet_lines": result["snippet_lines"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(
                f"Error getting connections overlapping range for file {file_id}: {e}"
            )
            return []

    def get_file_block_summary(self, file_id: int) -> List[Dict[str, Any]]:
        """Overview of classes/functions in a file (no content)."""
        try:
            results = self.connection.execute_query(GET_FILE_BLOCK_SUMMARY, (file_id,))
            summary_results = []

            for result in results:
                hierarchy_path = self.get_block_hierarchy_path(result["id"])
                summary_results.append(
                    {
                        "id": result["id"],
                        "type": result["type"],
                        "name": result["name"],
                        "start_line": result["start_line"],
                        "end_line": result["end_line"],
                        "parent_block_id": result["parent_block_id"],
                        "file_path": result["file_path"],
                        "project_name": result["project_name"],
                        "project_id": result["project_id"],
                        "hierarchy_path": hierarchy_path,
                    }
                )

            return summary_results
        except Exception as e:
            logger.error(f"Error getting file block summary for file {file_id}: {e}")
            return []

    def get_block_children(self, block_id: int) -> List[Dict[str, Any]]:
        """Methods/nested blocks of a parent."""
        try:
            results = self.connection.execute_query(GET_CHILD_BLOCKS, (block_id,))
            return [
                {
                    "id": result["id"],
                    "type": result["type"],
                    "name": result["name"],
                    "start_line": result["start_line"],
                    "end_line": result["end_line"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting block children for block {block_id}: {e}")
            return []

    def get_block_details(self, block_id: int) -> Optional[Dict[str, Any]]:
        """Single-call enrichment for discovered blocks."""
        try:
            # Get the block details
            block = self.resolve_block(block_id)
            if not block:
                return None

            # Get parent block details and all its children if parent exists
            parent = None
            parent_children = []
            if block["parent_block_id"]:
                parent_results = self.connection.execute_query(
                    GET_PARENT_BLOCK, (block_id,)
                )
                if parent_results:
                    parent_result = parent_results[0]
                    parent = {
                        "id": parent_result["id"],
                        "type": parent_result["type"],
                        "name": parent_result["name"],
                        "start_line": parent_result["start_line"],
                        "end_line": parent_result["end_line"],
                        "file_path": parent_result.get("file_path", block["file_path"]),
                    }

                    # Get all children of the parent block
                    parent_children = self.get_block_children(parent["id"])

            # Get connection mappings overlapping this block's range
            connection_mappings = self._get_connection_mappings_for_display(
                block["file_id"], block["start_line"], block["end_line"]
            )

            return {
                "id": block["id"],
                "type": block["type"],
                "name": block["name"],
                "file_path": block["file_path"],
                "language": block["language"],
                "start_line": block["start_line"],
                "end_line": block["end_line"],
                "start_col": block["start_col"],
                "end_col": block["end_col"],
                "content": block["content"],
                "parent": parent,
                "parent_children": parent_children,
                "connection_mappings": connection_mappings,
            }
        except Exception as e:
            logger.error(f"Error getting block details for block {block_id}: {e}")
            return None

    def get_block_hierarchy_path(self, block_id: int) -> List[Dict[str, Any]]:
        """Full nesting path (root → target)."""
        try:
            path = []
            current_id = block_id

            while current_id:
                block = self.resolve_block(current_id)
                if not block:
                    break

                path.insert(
                    0,
                    {
                        "id": block["id"],
                        "type": block["type"],
                        "name": block["name"],
                        "start_line": block["start_line"],
                        "end_line": block["end_line"],
                    },
                )

                current_id = block["parent_block_id"]

            return path
        except Exception as e:
            logger.error(
                f"Error getting block hierarchy path for block {block_id}: {e}"
            )
            return []

    def get_imports(self, file_id: int) -> List[Dict[str, Any]]:
        """What this file imports."""
        try:
            results = self.connection.execute_query(GET_FILE_IMPORTS, (file_id,))
            return [
                {
                    "import_content": result["import_content"],
                    "file_path": result["file_path"],
                    "language": result["language"],
                    "project_name": result["project_name"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting imports for file {file_id}: {e}")
            return []

    def get_importers(self, file_id: int) -> List[Dict[str, Any]]:
        """Who imports this file."""
        try:
            results = self.connection.execute_query(
                GET_FILE_IMPACT_SCOPE, (file_id, file_id)
            )
            return [
                {
                    "file_path": result["file_path"],
                    "language": result["language"],
                    "project_name": result["project_name"],
                    "import_content": result["import_content"],
                }
                for result in results
                if result["relationship_type"] == "importer"
            ]
        except Exception as e:
            logger.error(f"Error getting importers for file {file_id}: {e}")
            return []

    def get_dependency_chain(
        self, file_id: int, depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Multi-hop dependency path."""
        try:
            results = self.connection.execute_query(
                GET_DEPENDENCY_CHAIN, (file_id, depth)
            )
            return [
                {
                    "file_id": result["file_id"],
                    "file_path": result["file_path"],
                    "target_id": result["target_id"],
                    "target_path": result["target_path"],
                    "depth": result["depth"],
                    "path": result["path"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting dependency chain for file {file_id}: {e}")
            return []

    def get_search_scope_by_import_graph(
        self, anchor_file_id: int, direction: str = "both", max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Compute a small set of file paths likely impacted based on imports/importers and connection impacts.

        Args:
            anchor_file_id: ID of the file to analyze
            direction: Direction of dependencies to consider ("both", "dependencies", or "importers")
            max_depth: Maximum depth to traverse the dependency graph

        Returns:
            Dictionary with:
            - anchor_file_path: Path of the anchor file
            - imports: List of files this file imports with import content
            - importers: List of files that import this file with import content
            - dependency_chain: List of path rows including full path string
            - connection_impacts: List of connection impact details (incl. code and snippet lines)
            - max_depth: The max traversal depth used
        """
        try:
            anchor_file = self.resolve_file(anchor_file_id)
            if not anchor_file:
                return {
                    "anchor_file_path": None,
                    "imports": [],
                    "importers": [],
                    "dependency_chain": [],
                    "connection_impacts": [],
                    "max_depth": max_depth,
                }

            # Collect data for formatted output (do not aggregate paths here)
            connection_impacts = self.get_connection_impact(anchor_file_id)

            imports: List[Dict[str, Any]] = []
            importers: List[Dict[str, Any]] = []
            if direction in ["both", "dependencies"]:
                imports = self.get_imports(anchor_file_id)

            if direction in ["both", "importers"]:
                importers = self.get_importers(anchor_file_id)

            dependency_chain: List[Dict[str, Any]] = []
            if max_depth > 1:
                dependency_chain = self.get_dependency_chain(anchor_file_id, max_depth)

            return {
                "anchor_file_path": anchor_file["file_path"],
                "imports": imports,
                "importers": importers,
                "dependency_chain": dependency_chain,
                "connection_impacts": connection_impacts,
                "max_depth": max_depth,
            }
        except Exception as e:
            logger.error(f"Error getting search scope for file {anchor_file_id}: {e}")
            return {
                "anchor_file_path": None,
                "imports": [],
                "importers": [],
                "dependency_chain": [],
                "connection_impacts": [],
                "max_depth": max_depth,
            }

    def get_external_connections(self, file_id: int) -> List[Dict[str, Any]]:
        """Incoming/outgoing integrations for a file."""
        try:
            results = self.connection.execute_query(
                GET_EXTERNAL_CONNECTIONS, (file_id, file_id)
            )
            return [
                {
                    "direction": result["direction"],
                    "description": result["description"],
                    "technology_name": result["technology_name"],
                    "snippet_lines": result["snippet_lines"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting external connections for file {file_id}: {e}")
            return []

    def get_project_external_connections(self, project_id: int) -> List[Dict[str, Any]]:
        """All external integrations in a project."""
        try:
            results = self.connection.execute_query(
                GET_PROJECT_EXTERNAL_CONNECTIONS, (project_id,)
            )
            return [
                {
                    "file_path": result["file_path"],
                    "language": result["language"],
                    "technology": result["technology"],
                    "description": result["description"],
                    "direction": result["direction"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(
                f"Error getting project external connections for project {project_id}: {e}"
            )
            return []

    def get_connection_impact(self, file_id: int) -> List[Dict[str, Any]]:
        """High-confidence mapped connections to/from this file."""
        try:
            results = self.connection.execute_query(
                GET_CONNECTION_IMPACT, (file_id, file_id, file_id, file_id)
            )
            return [
                {
                    "technology_name": result["technology_name"],
                    "description": result["description"],
                    "match_confidence": result["match_confidence"],
                    "impact_type": result["impact_type"],
                    "other_file_id": result.get("other_file_id"),
                    "other_file": result["other_file"],
                    "other_project_id": result.get("other_project_id"),
                    "other_project_name": result.get("other_project_name"),
                    "technology": result["technology"],
                    "anchor_code_snippet": result.get("anchor_code_snippet"),
                    "other_code_snippet": result.get("other_code_snippet"),
                    "anchor_snippet_lines": result.get("anchor_snippet_lines"),
                    "other_snippet_lines": result.get("other_snippet_lines"),
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting connection impact for file {file_id}: {e}")
            return []

    def find_similar_implementations(
        self, name_pattern: str, kind: str
    ) -> Dict[str, Any]:
        """Similar function/class names for reference - delegates to search_keyword tool."""
        # Build pattern based on kind
        if kind == "function":
            pattern = f"def.*{name_pattern}.*|function.*{name_pattern}.*"
        elif kind == "class":
            pattern = f"class.*{name_pattern}.*"
        else:
            pattern = name_pattern

        return {
            "tool_required": "search_keyword",
            "action": f"Search for similar {kind} implementations",
            "pattern": pattern,
            "name_pattern": name_pattern,
            "kind": kind,
            "suggestion": f'Use search_keyword tool with pattern "{pattern}" to find similar {kind} implementations',
        }

    def find_files_with_pattern(self, pattern: str) -> Dict[str, Any]:
        """Content pattern matches across files - delegates to search_keyword tool."""
        return {
            "tool_required": "search_keyword",
            "action": "Search for pattern matches in file content",
            "pattern": pattern,
            "suggestion": f'Use search_keyword tool with pattern "{pattern}" to find matching files',
        }

    # ============================================================================
    # PROJECT OPERATIONS
    # ============================================================================

    def get_project_file_paths(self, project_name: str) -> List[str]:
        """Get all file paths for a project."""
        try:
            results = self.connection.execute_query(
                """SELECT DISTINCT file_path
                   FROM files
                   WHERE project_id = (SELECT id FROM projects WHERE name = ?)""",
                (project_name,),
            )
            return [row["file_path"] for row in results]

        except Exception as e:
            logger.error(f"Error getting project file paths: {e}")
            return []

    def get_project_id_by_name(self, project_name: str) -> Optional[int]:
        """Get project ID by name."""
        try:
            result = self.connection.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )
            return result[0]["id"] if result else None

        except Exception as e:
            logger.error(f"Error getting project ID: {e}")
            return None

    def get_db_file_hashes(self, project_id: int) -> Dict[str, str]:
        """Get all file hashes from the database for a project."""
        try:
            results = self.connection.execute_query(
                """SELECT file_path, content_hash
                   FROM files
                   WHERE project_id = ?""",
                (project_id,),
            )

            file_hashes = {}
            for row in results:
                file_hashes[row["file_path"]] = row["content_hash"]

            return file_hashes

        except Exception as e:
            logger.error(f"Error getting database file hashes: {e}")
            return {}

    def resolve_embedding_nodes(
        self, embedding_results: List[str]
    ) -> List[Dict[str, Any]]:
        """Convert discovered `block_#` / `file_#` to concrete records."""
        resolved = []

        for node_id in embedding_results:
            if node_id.startswith("block_"):
                block_id = int(node_id.split("_")[1])
                block = self.resolve_block(block_id)
                if block:
                    resolved.append(block)
            elif node_id.startswith("file_"):
                file_id = int(node_id.split("_")[1])
                file_data = self.resolve_file(file_id)
                if file_data:
                    resolved.append(file_data)

        return resolved

    # ============================================================================
    # CROSS-INDEX CONNECTION WRAPPER FUNCTIONS
    # ============================================================================

    def get_existing_connections(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve existing connections with IDs and file references.

        Returns:
            Dictionary with 'incoming' and 'outgoing' connection lists including IDs
        """
        try:

            incoming_results = self.connection.execute_query(
                GET_EXISTING_INCOMING_CONNECTIONS
            )
            outgoing_results = self.connection.execute_query(
                GET_EXISTING_OUTGOING_CONNECTIONS
            )

            return {"incoming": incoming_results, "outgoing": outgoing_results}

        except Exception as e:
            logger.error(f"Error retrieving existing connections: {e}")
            return {"incoming": [], "outgoing": []}

    def get_connections_by_ids(
        self, connection_ids: List[int], connection_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get connection details by IDs from database.

        Args:
            connection_ids: List of connection IDs
            connection_type: "incoming" or "outgoing"

        Returns:
            List of connection dictionaries with details
        """
        try:
            if not connection_ids:
                return []

            table_name = f"{connection_type}_connections"
            placeholders = ",".join(["?" for _ in connection_ids])

            query = GET_CONNECTIONS_BY_IDS.format(
                table_name=table_name, placeholders=placeholders
            )

            results = self.connection.execute_query(query, (connection_ids,))

            # Format results for matching prompt
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": str(result["id"]),
                        "type": connection_type,
                        "file_path": result["file_path"],
                        "line_number": "N/A",
                        "technology": result["technology_name"],
                        "description": result["description"],
                        "code_snippet": result["code_snippet"],
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error getting connections by IDs: {e}")
            return []

    def update_project_description(self, project_id: int, description: str) -> None:
        """
        Update project description.

        Args:
            project_id: ID of the project to update
            description: New description for the project
        """
        try:
            print(f"Updating project {project_id} description: {description[:100]}...")

            self.connection.connection.execute(
                UPDATE_PROJECT_DESCRIPTION,
                (description, project_id),
            )
            print(f"Project description updated successfully for project {project_id}")

        except Exception as e:
            logger.error(f"Error updating project description: {e}")
            raise

    def insert_incoming_connection(
        self,
        description: str,
        file_id: int,
        snippet_lines: List[int],
        technology_name: str,
        code_snippet: str,
    ) -> int:
        """
        Insert an incoming connection.

        Args:
            description: Description of the connection
            file_id: ID of the file
            snippet_lines: List of line numbers
            technology_name: Name of the technology
            code_snippet: Code snippet

        Returns:
            ID of the inserted connection
        """
        try:

            cursor = self.connection.connection.execute(
                INSERT_INCOMING_CONNECTION,
                (
                    description,
                    file_id,
                    json.dumps(snippet_lines),
                    technology_name,
                    code_snippet,
                ),
            )

            connection_id = cursor.lastrowid
            logger.debug(
                f"Inserted incoming connection {connection_id} for file {file_id}"
            )
            return connection_id

        except Exception as e:
            logger.error(f"Error inserting incoming connection: {e}")
            raise

    def insert_outgoing_connection(
        self,
        description: str,
        file_id: int,
        snippet_lines: List[int],
        technology_name: str,
        code_snippet: str,
    ) -> int:
        """
        Insert an outgoing connection.

        Args:
            description: Description of the connection
            file_id: ID of the file
            snippet_lines: List of line numbers
            technology_name: Name of the technology
            code_snippet: Code snippet

        Returns:
            ID of the inserted connection
        """
        try:

            cursor = self.connection.connection.execute(
                INSERT_OUTGOING_CONNECTION,
                (
                    description,
                    file_id,
                    json.dumps(snippet_lines),
                    technology_name,
                    code_snippet,
                ),
            )

            connection_id = cursor.lastrowid
            logger.debug(
                f"Inserted outgoing connection {connection_id} for file {file_id}"
            )
            return connection_id

        except Exception as e:
            logger.error(f"Error inserting outgoing connection: {e}")
            raise

    def insert_connection_mapping(
        self,
        sender_id: int,
        receiver_id: int,
        description: str,
        match_confidence: float,
    ) -> int:
        """
        Insert a connection mapping.

        Args:
            sender_id: ID of the sender connection
            receiver_id: ID of the receiver connection
            description: Description of the mapping
            match_confidence: Confidence level of the match

        Returns:
            ID of the inserted mapping
        """
        try:

            cursor = self.connection.connection.execute(
                INSERT_CONNECTION_MAPPING,
                (
                    sender_id,
                    receiver_id,
                    description,
                    match_confidence,
                ),
            )

            mapping_id = cursor.lastrowid
            logger.debug(f"Inserted connection mapping {mapping_id}")
            return mapping_id

        except Exception as e:
            logger.error(f"Error inserting connection mapping: {e}")
            raise

    def store_connections_with_commit(
        self, project_id: int, connections_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store connections data and commit the transaction.

        Args:
            project_id: ID of the project
            connections_data: Dictionary containing connection data

        Returns:
            Result dictionary with success status and stored connection IDs
        """
        try:
            stored_incoming = []
            stored_outgoing = []

            # Update project description if present
            if isinstance(connections_data, dict):
                project_summary = connections_data.get("summary", "").strip()
                if project_summary:
                    print(
                        f"Found project summary to store: {len(project_summary)} characters"
                    )
                    self.update_project_description(project_id, project_summary)
                else:
                    logger.debug("No project summary found in connections_data")
            else:
                logger.warning(
                    f"connections_data is not a dict: {type(connections_data)}"
                )

            # Store incoming connections - Handle BAML format: {"tech_name": {"file": [details]}}
            if "incoming_connections" in connections_data:
                incoming_connections = connections_data["incoming_connections"]
                for tech_name, files_dict in incoming_connections.items():
                    for file_path, connection_details in files_dict.items():
                        for detail in connection_details:
                            file_id = self._get_file_id_by_path(file_path)

                            if not file_id:
                                logger.warning(
                                    f"File not found in database for incoming connection: {file_path}"
                                )
                                continue

                            # Parse snippet_lines from detail
                            snippet_lines_str = detail.get("snippet_lines", "")
                            snippet_lines = self._parse_snippet_lines_from_detail(snippet_lines_str)

                            code_snippet = (
                                self._fetch_code_snippet_from_lines(file_path, snippet_lines)
                                if snippet_lines and file_path
                                else ""
                            )

                            connection_id = self.insert_incoming_connection(
                                detail.get("description", ""),
                                file_id,
                                snippet_lines,
                                tech_name,
                                code_snippet,
                            )
                            stored_incoming.append(connection_id)

            # Store outgoing connections - Handle BAML format: {"tech_name": {"file": [details]}}
            if "outgoing_connections" in connections_data:
                outgoing_connections = connections_data["outgoing_connections"]
                for tech_name, files_dict in outgoing_connections.items():
                    for file_path, connection_details in files_dict.items():
                        for detail in connection_details:
                            file_id = self._get_file_id_by_path(file_path)

                            if not file_id:
                                logger.warning(f"File not found in database: {file_path}")
                                continue

                            # Parse snippet_lines from detail
                            snippet_lines_str = detail.get("snippet_lines", "")
                            snippet_lines = self._parse_snippet_lines_from_detail(snippet_lines_str)

                            code_snippet = (
                                self._fetch_code_snippet_from_lines(file_path, snippet_lines)
                                if snippet_lines and file_path
                                else ""
                            )

                            connection_id = self.insert_outgoing_connection(
                                detail.get("description", ""),
                                file_id,
                                snippet_lines,
                                tech_name,
                                code_snippet,
                            )
                            stored_outgoing.append(connection_id)

            # Commit all changes
            self.connection.connection.commit()

            print(
                f"Stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections"
            )

            return {
                "success": True,
                "incoming_ids": stored_incoming,
                "outgoing_ids": stored_outgoing,
                "message": f"Successfully stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections",
            }

        except Exception as e:
            logger.error(f"Error storing connections: {e}")
            # Rollback on error
            try:
                self.connection.connection.rollback()
            except BaseException:
                pass
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store connections",
            }

    def create_connection_mappings(
        self, matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create connection mappings using only IDs.

        Args:
            matches: List of matches with sender_id and receiver_id

        Returns:
            Result dictionary with mapping creation status
        """
        try:
            created_mappings = []

            for match in matches:
                mapping_id = self.insert_connection_mapping(
                    match.get("sender_id"),
                    match.get("receiver_id"),
                    match.get("description", "Auto-detected connection"),
                    match.get("match_confidence", 0.0),
                )
                created_mappings.append(mapping_id)

            # Commit all mappings
            self.connection.connection.commit()

            return {
                "success": True,
                "mapping_ids": created_mappings,
                "message": f"Created {len(created_mappings)} connection mappings",
            }

        except Exception as e:
            logger.error(f"Error creating connection mappings: {e}")
            # Rollback on error
            try:
                self.connection.connection.rollback()
            except BaseException:
                pass
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create connection mappings",
            }

    def _fetch_code_snippet_from_lines(
        self, file_path: str, snippet_lines: List[int]
    ) -> str:
        """
        Fetch actual code snippet from database using line numbers and beautify with line numbers.

        Args:
            file_path: Path to the file
            snippet_lines: List of line numbers to fetch

        Returns:
            str: Beautified code snippet from the specified lines with line numbers
        """
        try:
            if not snippet_lines:
                return ""

            # Get file_id from database using file path
            file_id = self._get_file_id_by_path(file_path)
            if not file_id:
                logger.warning(f"File not found in database: {file_path}")
                return ""

            # Get file content from database
            file_data = self.resolve_file(file_id)
            if not file_data or not file_data.get("content"):
                logger.warning(f"No content found for file: {file_path}")
                return ""

            # Get start and end line from the list
            start_line = min(snippet_lines)
            end_line = max(snippet_lines)

            # Import the processing utilities to avoid circular import
            from tools.utils.code_processing_utils import (
                process_code_with_line_filtering,
            )

            # Use existing beautify function to process code with line filtering
            result = process_code_with_line_filtering(
                code_snippet=file_data["content"],
                file_start_line=1,  # File content starts at line 1
                start_line=start_line,
                end_line=end_line,
            )

            if result and result.get("code"):
                logger.debug(
                    f"Fetched and beautified code snippet from {file_path} lines {start_line}-{end_line}: {
                        result['total_lines']} lines"
                )
                return result["code"]
            else:
                logger.warning(
                    f"No code returned for {file_path} lines {start_line}-{end_line}"
                )
                return ""

        except Exception as e:
            logger.error(
                f"Error fetching code snippet from database for {file_path}: {e}"
            )
            return ""

    def is_cross_indexing_done(self, project_name: str) -> bool:
        """Check if cross-indexing is completed for a project."""
        try:
            result = self.connection.execute_query(
                "SELECT cross_indexing_done FROM projects WHERE name = ?",
                (project_name,),
            )
            if result:
                return bool(result[0].get("cross_indexing_done", 0))
            return False

        except Exception as e:
            logger.error(f"Failed to check cross-indexing status: {e}")
            return False

    def mark_cross_indexing_done_by_id(self, project_id: int) -> None:
        """Mark cross-indexing as completed for a project by project ID."""
        try:
            cursor = self.connection.connection.cursor()
            cursor.execute(
                """UPDATE projects
                   SET cross_indexing_done = 1, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (project_id,),
            )
            self.connection.connection.commit()
            logger.debug(f"Marked cross-indexing as done for project ID {project_id}")

        except Exception as e:
            self.connection.connection.rollback()
            logger.error(
                f"Failed to mark cross-indexing as done for project ID {project_id}: {e}"
            )
            raise

    def get_all_technology_types(self) -> list:
        """
        Get all unique technology types from both incoming and outgoing connections.
        Returns all distinct technology types including Unknown.

        Returns:
            List of unique technology type names (including Unknown if exists)
        """
        try:
            query = """
                SELECT DISTINCT COALESCE(technology_name, 'Unknown') as technology
                FROM (
                    SELECT technology_name
                    FROM incoming_connections
                    UNION ALL
                    SELECT technology_name
                    FROM outgoing_connections
                ) combined_tech
                ORDER BY technology
                """
            results = self.connection.execute_query(query)
            return [row["technology"] for row in (results or [])]
        except Exception as e:
            logger.error(f"Error fetching technology types: {e}")
            return []

    def fetch_connections_by_technology(self, technology: str) -> Dict[str, list]:
        """
        Fetch both incoming and outgoing connections for a specific technology type.

        Args:
            technology: Technology type to fetch

        Returns:
            Dict with 'incoming' and 'outgoing' keys containing connection lists
        """
        try:
            where_clause = "WHERE technology_name = ? OR (technology_name IS NULL AND ? = 'Unknown')"
            params = (technology, technology)

            # Fetch incoming connections
            incoming_query = f"""
            SELECT ic.id, ic.description, COALESCE(ic.technology_name, 'Unknown') as technology,
                   ic.code_snippet, ic.snippet_lines, files.file_path, files.language
            FROM incoming_connections ic
            LEFT JOIN files ON ic.file_id = files.id
            {where_clause}
            ORDER BY ic.id
            """

            # Fetch outgoing connections
            outgoing_query = f"""
            SELECT oc.id, oc.description, COALESCE(oc.technology_name, 'Unknown') as technology,
                   oc.code_snippet, oc.snippet_lines, files.file_path, files.language
            FROM outgoing_connections oc
            LEFT JOIN files ON oc.file_id = files.id
            {where_clause}
            ORDER BY oc.id
            """

            incoming_results = (
                self.connection.execute_query(incoming_query, params) or []
            )
            outgoing_results = (
                self.connection.execute_query(outgoing_query, params) or []
            )

            return {"incoming": incoming_results, "outgoing": outgoing_results}

        except Exception as e:
            logger.error(f"Error fetching connections for technology {technology}: {e}")
            return {"incoming": [], "outgoing": []}

    def get_available_technology_types(self) -> list:
        """
        Get all unique technology types excluding Unknown.

        Returns:
            List of unique technology type names (excluding Unknown)
        """
        all_types = self.get_all_technology_types()
        return [t for t in all_types if t != "Unknown"]

    def _filter_unmapped_connections(
        self,
        basic_connections: Dict[str, Any],
        connection_mappings: List[Dict[str, Any]],
        current_file_path: str
    ) -> Dict[str, Any]:
        """
        Filter out basic connections that are already represented in connection mappings.

        Args:
            basic_connections: Dict with incoming/outgoing connection lists
            connection_mappings: List of connection mapping dictionaries
            current_file_path: Path of the current file being processed

        Returns:
            Filtered basic connections excluding ones already in mappings
        """
        if not connection_mappings:
            return basic_connections

        # Create sets of mapped file paths for quick lookup
        mapped_incoming = set()  # Files that send to current file (current is receiver)
        mapped_outgoing = set()  # Files that current file sends to (current is sender)

        for mapping in connection_mappings:
            sender_file = mapping.get("sender_file_path", "")
            receiver_file = mapping.get("receiver_file_path", "")

            if receiver_file == current_file_path and sender_file:
                mapped_incoming.add(sender_file)
            elif sender_file == current_file_path and receiver_file:
                mapped_outgoing.add(receiver_file)

        # Filter basic connections
        filtered = {"incoming": [], "outgoing": []}

        # Filter incoming connections (remove if sender file is already mapped)
        for conn in basic_connections.get("incoming", []):
            source_file = conn.get("source_file_path", conn.get("connected_file_path", ""))
            if source_file not in mapped_incoming:
                filtered["incoming"].append(conn)

        # Filter outgoing connections (remove if target file is already mapped)
        for conn in basic_connections.get("outgoing", []):
            target_file = conn.get("target_file_path", conn.get("connected_file_path", ""))
            if target_file not in mapped_outgoing:
                filtered["outgoing"].append(conn)

        return filtered

    def _parse_snippet_lines_from_detail(self, snippet_lines_str: str) -> List[int]:
        """
        Parse snippet_lines from BAML detail format.

        Args:
            snippet_lines_str: String like "46-46" or "112-112" from BAML ConnectionDetail

        Returns:
            List of line numbers
        """
        try:
            if not snippet_lines_str or snippet_lines_str.strip() == "":
                return []

            # Handle range format like "46-46" or "112-115"
            if "-" in snippet_lines_str:
                parts = snippet_lines_str.split("-")
                if len(parts) == 2:
                    start_line = int(parts[0].strip())
                    end_line = int(parts[1].strip())
                    return list(range(start_line, end_line + 1))

            # Handle single line number
            return [int(snippet_lines_str.strip())]

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse snippet_lines '{snippet_lines_str}': {e}")
            return []
