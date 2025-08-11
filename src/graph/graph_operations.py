"""
GraphOperations class for high-level database operations.

This module contains the GraphOperations class which provides high-level
operations for inserting and querying code extraction data in the SQLite database.
It handles insertion of extraction data from JSON exports and provides various
query methods for retrieving code structure, relationships, and connections.
"""

import re
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


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

    def get_agent_context_for_semantic_results(
        self, semantic_block_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Agent-centric context extraction from semantic search results.

        Flow:
        1. Agent does semantic search → gets block_ids (file_28403, block_238408)
        2. Resolve nodes to get concrete data (file info, block info)
        3. For blocks: add file context and check if file connections overlap with block lines
        4. For files: get all relevant connections
        5. Return intuitive, actionable data for the agent

        Args:
            semantic_block_ids: List of node IDs from semantic search (e.g., ["block_123", "file_456"])

        Returns:
            Dictionary with agent-friendly context for each semantic result
        """
        try:
            if not semantic_block_ids:
                return {}

            context_results = {}

            for i, block_id in enumerate(semantic_block_ids):
                result_key = f"semantic_result_{i}"

                if block_id.startswith("block_"):
                    # Handle block context
                    block_id = int(block_id.split("_")[1])
                    block_data = self.resolve_block(block_id)

                    if block_data:
                        # Get connections that overlap with this block's line range
                        connections = self._get_connections_for_file_and_lines(
                            block_data["file_id"],
                            block_data["start_line"],
                            block_data["end_line"],
                        )

                        context_results[result_key] = {
                            "node_type": "block",
                            "block_id": block_id,
                            "block_info": block_data,
                            "file_context": {
                                "file_path": block_data["file_path"],
                                "file_id": block_data["file_id"],
                                "language": block_data["language"],
                                "project_name": block_data["project_name"],
                            },
                            "relevant_connections": connections,
                            "summary": f"Block '{block_data['name']}' ({block_data['type']}) in {block_data['file_path']} lines {block_data['start_line']}-{block_data['end_line']}",
                        }

                elif block_id.startswith("file_"):
                    # Handle file context
                    file_id = int(block_id.split("_")[1])
                    file_data = self.resolve_file(file_id)

                    if file_data:
                        # Get all connections for this file
                        connections = self._get_connections_for_file_and_lines(
                            file_id, None, None
                        )
                        file_blocks = self.get_file_block_summary(file_id)

                        context_results[result_key] = {
                            "node_type": "file",
                            "block_id": block_id,
                            "file_info": file_data,
                            "blocks_summary": file_blocks,
                            "all_connections": connections,
                            "summary": f"File '{file_data['file_path']}' ({file_data['language']}) with {file_data['block_count']} blocks",
                        }

            return context_results

        except Exception as e:
            logger.error(f"Error getting agent context for semantic results: {e}")
            return {}

    def get_agent_context_for_single_node(
        self, block_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive context for a single semantic search node.

        Args:
            block_id: Single node ID from semantic search (e.g., "block_123" or "file_456")

        Returns:
            Dictionary with comprehensive context or None if not found
        """
        try:
            results = self.get_agent_context_for_semantic_results([block_id])
            if results:
                return list(results.values())[0]
            return None
        except Exception as e:
            logger.error(f"Error getting agent context for node {block_id}: {e}")
            return None

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
                            file_id = row["id"]
                            logger.debug(
                                f"Found file_id {file_id} by filename match for {filename} -> {row['file_path']}"
                            )
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

    def get_agent_connection_summary(
        self, connections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create structured connection summary for agent consumption.

        Args:
            connections: Connection information dictionary

        Returns:
            Structured summary for agent decision-making
        """
        try:
            if not connections:
                return {"summary": "No connections found", "details": {}}

            incoming = connections.get("incoming", [])
            outgoing = connections.get("outgoing", [])

            summary = {
                "total_connections": len(incoming) + len(outgoing),
                "incoming_count": len(incoming),
                "outgoing_count": len(outgoing),
                "technologies": set(),
                "impact_areas": [],
            }

            details = {"incoming": [], "outgoing": []}

            # Process incoming connections
            for conn in incoming:
                tech = conn.get("technology_name", "Unknown")
                summary["technologies"].add(tech)

                details["incoming"].append(
                    {
                        "description": conn.get("description", "No description"),
                        "technology": tech,
                        "has_code": bool(conn.get("code_snippet")),
                        "mapped_connections": len(conn.get("mapped_connections", [])),
                    }
                )

            # Process outgoing connections
            for conn in outgoing:
                tech = conn.get("technology_name", "Unknown")
                summary["technologies"].add(tech)

                details["outgoing"].append(
                    {
                        "description": conn.get("description", "No description"),
                        "technology": tech,
                        "has_code": bool(conn.get("code_snippet")),
                        "mapped_connections": len(conn.get("mapped_connections", [])),
                    }
                )

            summary["technologies"] = list(summary["technologies"])

            return {"summary": summary, "details": details}

        except Exception as e:
            logger.error(f"Error creating agent connection summary: {e}")
            return {"summary": "Error processing connections", "details": {}}

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

            # Get connections overlapping with this block
            connections = self._get_connections_for_file_and_lines(
                block_data["file_id"], block_data["start_line"], block_data["end_line"]
            )

            # Get parent/child relationships
            parent_info = None
            if block_data.get("parent_block_id"):
                parent_info = self.resolve_block(block_data["parent_block_id"])

            child_blocks = self.get_block_children(block_id)

            return {
                "block": block_data,
                "connections": connections,
                "connection_summary": self.get_agent_connection_summary(connections),
                "parent_block": parent_info,
                "child_blocks": child_blocks,
                "file_context": {
                    "file_path": block_data["file_path"],
                    "language": block_data["language"],
                    "project_name": block_data["project_name"],
                },
            }

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

            # Get all connections for this file
            connections = self._get_connections_for_file_and_lines(file_id, None, None)

            # Get file blocks summary
            blocks_summary = self.get_file_block_summary(file_id)

            # Get import relationships
            imports = self.get_imports(file_id)
            importers = self.get_importers(file_id)

            return {
                "file": file_data,
                "blocks_summary": blocks_summary,
                "connections": connections,
                "connection_summary": self.get_agent_connection_summary(connections),
                "imports": imports,
                "importers": importers,
                "dependency_context": {
                    "imports_count": len(imports),
                    "importers_count": len(importers),
                    "has_external_connections": bool(
                        connections.get("incoming") or connections.get("outgoing")
                    ),
                },
            }

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
            return [
                {
                    "id": result["id"],
                    "type": result["type"],
                    "name": result["name"],
                    "start_line": result["start_line"],
                    "end_line": result["end_line"],
                    "parent_block_id": result["parent_block_id"],
                }
                for result in results
            ]
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

            # Get parent block if exists
            parent = None
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
                        "file_path": parent_result["file_path"],
                    }

            # Get connections overlapping this block's range
            connections = self.get_connections_overlapping_range(
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
                "parent": parent,
                "connections_in_range": connections,
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

    def get_blocks_by_type_in_file(
        self, file_id: int, block_type: str
    ) -> List[Dict[str, Any]]:
        """Retrieve all blocks of a given type in a file."""
        try:
            blocks = self.get_file_block_summary(file_id)
            return [block for block in blocks if block["type"] == block_type]
        except Exception as e:
            logger.error(
                f"Error getting blocks by type {block_type} in file {file_id}: {e}"
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

    def get_file_impact_scope(self, file_id: int) -> List[Dict[str, Any]]:
        """Importers + dependencies in one view."""
        try:
            results = self.connection.execute_query(
                GET_FILE_IMPACT_SCOPE, (file_id, file_id)
            )
            return [
                {
                    "relationship_type": result["relationship_type"],
                    "file_path": result["file_path"],
                    "language": result["language"],
                    "project_name": result["project_name"],
                    "import_content": result["import_content"],
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error getting file impact scope for file {file_id}: {e}")
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

    def get_files_using_symbol(
        self, symbol_pattern: str, paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Usage sites across the codebase - delegates to search_keyword tool."""
        return {
            "tool_required": "search_keyword",
            "action": "Search for symbol usage across codebase",
            "symbol_pattern": symbol_pattern,
            "paths": paths,
            "suggestion": f'Use search_keyword tool with pattern "{symbol_pattern}"'
            + (f" scoped to {len(paths)} files" if paths else " across all files"),
        }

    def get_search_scope_by_import_graph(
        self, anchor_file_id: int, direction: str = "both", max_depth: int = 2
    ) -> Dict[str, Any]:
        """Compute a small set of file paths likely impacted based on imports/importers."""
        try:
            anchor_file = self.resolve_file(anchor_file_id)
            if not anchor_file:
                return {"anchor_file_path": None, "paths": []}

            paths = set([anchor_file["file_path"]])

            if direction in ["both", "dependencies"]:
                # Get files this file imports
                imports = self.get_imports(anchor_file_id)
                for imp in imports:
                    paths.add(imp["file_path"])

            if direction in ["both", "importers"]:
                # Get files that import this file
                importers = self.get_importers(anchor_file_id)
                for imp in importers:
                    paths.add(imp["file_path"])

            # For depth > 1, expand recursively (simplified implementation)
            if max_depth > 1:
                dependency_chain = self.get_dependency_chain(anchor_file_id, max_depth)
                for dep in dependency_chain:
                    paths.add(dep["file_path"])
                    paths.add(dep["target_path"])

            return {
                "anchor_file_path": anchor_file["file_path"],
                "paths": sorted(list(paths)),
            }
        except Exception as e:
            logger.error(f"Error getting search scope for file {anchor_file_id}: {e}")
            return {"anchor_file_path": None, "paths": []}

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
                    "connection_type": result["connection_type"],
                    "description": result["description"],
                    "match_confidence": result["match_confidence"],
                    "impact_type": result["impact_type"],
                    "other_file": result["other_file"],
                    "technology": result["technology"],
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
    # CONNECTION OPERATIONS
    # ============================================================================

    def store_incoming_connection(
        self,
        description: str,
        file_id: int,
        snippet_lines: List[int],
        technology_name: str,
        code_snippet: str,
    ) -> int:
        """Store an incoming connection."""
        try:
            import json

            cursor = self.connection.connection.execute(
                """INSERT INTO incoming_connections
                   (description, file_id, snippet_lines, technology_name, code_snippet)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    description,
                    file_id,
                    json.dumps(snippet_lines),
                    technology_name,
                    code_snippet,
                ),
            )

            connection_id = cursor.lastrowid
            self.connection.connection.commit()
            logger.debug(f"Stored incoming connection for file {file_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Error storing incoming connection: {e}")
            raise

    def store_outgoing_connection(
        self,
        description: str,
        file_id: int,
        snippet_lines: List[int],
        technology_name: str,
        code_snippet: str,
    ) -> int:
        """Store an outgoing connection."""
        try:
            import json

            cursor = self.connection.connection.execute(
                """INSERT INTO outgoing_connections
                   (description, file_id, snippet_lines, technology_name, code_snippet)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    description,
                    file_id,
                    json.dumps(snippet_lines),
                    technology_name,
                    code_snippet,
                ),
            )

            connection_id = cursor.lastrowid
            self.connection.connection.commit()
            logger.debug(f"Stored outgoing connection for file {file_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Error storing outgoing connection: {e}")
            raise

    def store_connections_batch(
        self, connections_data: Dict[str, Any]
    ) -> Dict[str, List[int]]:
        """Store multiple connections in a batch operation."""
        try:
            import json

            stored_incoming = []
            stored_outgoing = []

            # Store incoming connections
            for conn in connections_data.get("incoming_connections", []):
                file_id = conn["file_id"]
                snippet_lines = conn.get("snippet_lines", [])
                code_snippet = conn.get("code_snippet", "")

                cursor = self.connection.connection.execute(
                    """INSERT INTO incoming_connections
                       (description, file_id, snippet_lines, technology_name, code_snippet)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        conn["description"],
                        file_id,
                        json.dumps(snippet_lines),
                        conn.get("technology", {}).get("name", "unknown"),
                        code_snippet,
                    ),
                )
                stored_incoming.append(cursor.lastrowid)

            # Store outgoing connections
            for conn in connections_data.get("outgoing_connections", []):
                file_id = conn["file_id"]
                snippet_lines = conn.get("snippet_lines", [])
                code_snippet = conn.get("code_snippet", "")

                cursor = self.connection.connection.execute(
                    """INSERT INTO outgoing_connections
                       (description, file_id, snippet_lines, technology_name, code_snippet)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        conn["description"],
                        file_id,
                        json.dumps(snippet_lines),
                        conn.get("technology", {}).get("name", "unknown"),
                        code_snippet,
                    ),
                )
                stored_outgoing.append(cursor.lastrowid)

            self.connection.connection.commit()
            logger.info(
                f"Stored {len(stored_incoming)} incoming and {len(stored_outgoing)} outgoing connections"
            )

            return {"incoming_ids": stored_incoming, "outgoing_ids": stored_outgoing}

        except Exception as e:
            logger.error(f"Error storing connections batch: {e}")
            raise

    def store_connection_mapping(
        self,
        sender_id: int,
        receiver_id: int,
        connection_type: str,
        description: str,
        match_confidence: float,
    ) -> int:
        """Store a connection mapping between sender and receiver."""
        try:
            import time

            cursor = self.connection.connection.execute(
                """INSERT INTO connection_mappings (sender_id, receiver_id, connection_type, description, match_confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    sender_id,
                    receiver_id,
                    connection_type,
                    description,
                    match_confidence,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

            mapping_id = cursor.lastrowid
            self.connection.connection.commit()
            logger.debug(
                f"Stored connection mapping between {sender_id} and {receiver_id}"
            )
            return mapping_id

        except Exception as e:
            logger.error(f"Error storing connection mapping: {e}")
            raise

    def store_connection_mappings_batch(
        self, matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store multiple connection mappings in a batch operation."""
        try:
            created_mappings = []

            for match in matches:
                cursor = self.connection.connection.execute(
                    """INSERT INTO connection_mappings (sender_id, receiver_id, connection_type, description, match_confidence)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        match.get("sender_id"),
                        match.get("receiver_id"),
                        match.get("connection_type", "unknown"),
                        match.get("description", "Auto-detected connection"),
                        match.get("match_confidence", 0.0),
                    ),
                )
                created_mappings.append(cursor.lastrowid)

            self.connection.connection.commit()

            return {
                "success": True,
                "mapping_ids": created_mappings,
                "message": f"Created {len(created_mappings)} connection mappings",
            }

        except Exception as e:
            logger.error(f"Error storing connection mappings batch: {e}")
            raise

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

        for block_id in embedding_results:
            if block_id.startswith("block_"):
                block_id = int(block_id.split("_")[1])
                block = self.resolve_block(block_id)
                if block:
                    resolved.append(block)
            elif block_id.startswith("file_"):
                file_id = int(block_id.split("_")[1])
                file_data = self.resolve_file(file_id)
                if file_data:
                    resolved.append(file_data)

        return resolved
