"""
Connection utilities for database queries.
Provides connection information for fetched code snippets.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class ConnectionRetriever:
    """
    Service to retrieve and match connections for database query results.
    
    This service:
    1. Takes database query results with file_hash_id and line information
    2. Finds matching incoming/outgoing connections based on file_hash_id and line overlap
    3. Returns connection information with mapped connections if they exist
    4. Adds notes about updating connections when making changes
    """
    
    def __init__(self, db_connection):
        self.db_connection = db_connection
    
    def get_connections_for_query_results(
        self, 
        query_results: List[Dict[str, Any]], 
        project_id: Optional[int] = None
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
                    if file_path and project_id:
                        file_hash_id = self._get_file_hash_id_by_path(file_path, project_id)
                
                if file_hash_id:
                    # Parse line information
                    start_line, end_line = self._parse_line_info(lines_data)
                    
                    # Get connections for this file_hash_id and line range
                    connections = self._get_connections_for_file_and_lines(
                        file_hash_id, start_line, end_line, project_id
                    )
                    
                    if connections["incoming"] or connections["outgoing"]:
                        connection_info[result_key] = {
                            "file_hash_id": file_hash_id,
                            "file_path": file_path,
                            "line_range": [start_line, end_line] if start_line and end_line else None,
                            "connections": connections,
                            "note": self._generate_connection_note(connections)
                        }
            
            return connection_info
            
        except Exception as e:
            logger.error(f"Error getting connections for query results: {e}")
            return {}
    
    def _get_file_hash_id_by_path(self, file_path: str, project_id: int) -> Optional[int]:
        """Get file_hash_id by file path and project_id."""
        try:
            result = self.db_connection.execute_query(
                "SELECT id FROM file_hashes WHERE project_id = ? AND file_path = ?",
                (project_id, file_path)
            )
            return result[0]["id"] if result else None
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
        project_id: Optional[int] = None
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
                "incoming", file_hash_id, project_id
            )
            
            # Get outgoing connections  
            outgoing_connections = self._get_connections_by_type(
                "outgoing", file_hash_id, project_id
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
            logger.error(f"Error getting connections for file_hash_id {file_hash_id}: {e}")
            return {"incoming": [], "outgoing": []}
    
    def _get_connections_by_type(
        self, 
        connection_type: str, 
        file_hash_id: int, 
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get connections of a specific type for a file."""
        try:
            table_name = f"{connection_type}_connections"
            
            base_query = f"""
                SELECT c.id, c.description, c.snippet_lines, c.technology_name, 
                       c.code_snippet, c.created_at,
                       fh.file_path, fh.language, p.name as project_name
                FROM {table_name} c
                JOIN file_hashes fh ON c.file_hash_id = fh.id
                JOIN projects p ON c.project_id = p.id
                WHERE c.file_hash_id = ?
            """
            
            params = [file_hash_id]
            
            if project_id:
                base_query += " AND c.project_id = ?"
                params.append(project_id)
            
            base_query += " ORDER BY c.created_at DESC"
            
            results = self.db_connection.execute_query(base_query, tuple(params))
            
            # Parse snippet_lines JSON
            for result in results:
                if result.get("snippet_lines"):
                    try:
                        result["snippet_lines_parsed"] = json.loads(result["snippet_lines"])
                    except:
                        result["snippet_lines_parsed"] = []
                else:
                    result["snippet_lines_parsed"] = []
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting {connection_type} connections: {e}")
            return []
    
    def _filter_connections_by_lines(
        self, 
        connections: List[Dict[str, Any]], 
        start_line: int, 
        end_line: int
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
        self, 
        snippet_lines: List[int], 
        start_line: int, 
        end_line: int
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
        self,
        connections: List[Dict[str, Any]],
        connection_type: str
    ) -> List[Dict[str, Any]]:
        """
        Add mapped connections (incoming->outgoing or outgoing->incoming) for each connection.
        Only return connections that have mappings.
        
        Args:
            connections: List of connections
            connection_type: "incoming" or "outgoing"
            
        Returns:
            Connections with mapped_connections field added, filtered to only include connections with mappings
        """
        try:
            connections_with_mappings = []
            
            for conn in connections:
                conn_id = conn["id"]
                mapped_connections = self._get_mapped_connections(conn_id, connection_type)
                conn["mapped_connections"] = mapped_connections
                
                # Only include connections that have mappings
                if mapped_connections:
                    connections_with_mappings.append(conn)
                    logger.debug(f"Connection {conn_id} has {len(mapped_connections)} mappings - including")
                else:
                    logger.debug(f"Connection {conn_id} has no mappings - excluding")
            
            return connections_with_mappings
            
        except Exception as e:
            logger.error(f"Error adding mapped connections: {e}")
            return connections
    
    def _get_mapped_connections(
        self, 
        connection_id: int, 
        connection_type: str
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
                           fh.file_path as outgoing_file_path, fh.language as outgoing_language
                    FROM connection_mappings cm
                    JOIN outgoing_connections oc ON cm.sender_id = oc.id
                    JOIN file_hashes fh ON oc.file_hash_id = fh.id
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
                           fh.file_path as incoming_file_path, fh.language as incoming_language
                    FROM connection_mappings cm
                    JOIN incoming_connections ic ON cm.receiver_id = ic.id
                    JOIN file_hashes fh ON ic.file_hash_id = fh.id
                    WHERE cm.sender_id = ?
                    ORDER BY cm.match_confidence DESC, cm.created_at DESC
                """
                params = (connection_id,)
            
            results = self.db_connection.execute_query(query, params)
            return results
            
        except Exception as e:
            logger.error(f"Error getting mapped connections for {connection_id}: {e}")
            return []
    
    def _generate_connection_note(self, connections: Dict[str, List[Dict[str, Any]]]) -> str:
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
            
            note = f"🔗 CONNECTIONS FOUND: This code has {connection_summary}."
            
            if has_mappings:
                note += " Some connections have mapped relationships."
            
            note += " If you make changes to this code, consider updating the related connections to maintain system consistency."
            
            return note
            
        except Exception as e:
            logger.error(f"Error generating connection note: {e}")
            return "🔗 Connection information available but could not generate note."
    
    def format_connections_for_display(
        self, 
        connection_info: Dict[str, Any]
    ) -> str:
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
                        output_parts.append(f"  {i}. {conn.get('description', 'No description')}")
                        output_parts.append(f"     Technology: {conn.get('technology_name', 'Unknown')}")
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"][:100] + "..." if len(conn["code_snippet"]) > 100 else conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")
                        
                        # Show mapped connections
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(f"     ↔️ Mapped to {len(mapped)} outgoing connection(s)")
                
                # Format outgoing connections
                outgoing = info.get("connections", {}).get("outgoing", [])
                if outgoing:
                    output_parts.append(f"\n📤 OUTGOING CONNECTIONS ({len(outgoing)}):")
                    for i, conn in enumerate(outgoing, 1):
                        output_parts.append(f"  {i}. {conn.get('description', 'No description')}")
                        output_parts.append(f"     Technology: {conn.get('technology_name', 'Unknown')}")
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"][:100] + "..." if len(conn["code_snippet"]) > 100 else conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")
                        
                        # Show mapped connections
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(f"     ↔️ Mapped to {len(mapped)} incoming connection(s)")
            
            return "\n".join(output_parts)
            
        except Exception as e:
            logger.error(f"Error formatting connections for display: {e}")
            return "\n🔗 Connection information available but could not format for display."


def get_connection_retriever(db_connection) -> ConnectionRetriever:
    """Factory function to create a ConnectionRetriever instance."""
    return ConnectionRetriever(db_connection)