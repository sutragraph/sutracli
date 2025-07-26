"""
Agent-specific connection enhancement for database queries.
This module provides connection information specifically for agent service mode,
without affecting cross-indexing service operations.
"""

import json
from typing import Dict, List, Any, Optional
from loguru import logger
from .connection_utils import get_connection_retriever


class AgentConnectionEnhancer:
    """
    Enhances database query results with connection information specifically for agent service.
    
    This service:
    1. Only activates when called from agent service context
    2. Adds connection information to database results
    3. Provides clean formatting without emojis for prompts
    4. Does not interfere with cross-indexing service operations
    """

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.connection_retriever = get_connection_retriever(db_connection)

    def enhance_database_results(
        self, 
        results: List[Dict[str, Any]], 
        project_id: Optional[int] = None,
        context: str = "agent"
    ) -> str:
        """
        Enhance database results with connection information for agent service.
        
        Args:
            results: Database query results
            project_id: Optional project ID
            context: Context of the call ("agent" or "cross_index")
            
        Returns:
            Formatted connection information string (empty if context is not "agent")
        """
        try:
            # Only enhance for agent context, not cross-indexing
            if context != "agent":
                return ""

            if not results:
                return ""

            # Get connection information for all results
            connection_info = self.connection_retriever.get_connections_for_query_results(
                results, project_id
            )

            if not connection_info:
                return ""

            # Format connection information for agent service (no emojis)
            formatted_connections = self._format_connections_for_agent(connection_info)

            return formatted_connections

        except Exception as e:
            logger.error(f"Error enhancing database results: {e}")
            return ""

    def _format_connections_for_agent(self, connection_info: Dict[str, Any]) -> str:
        """
        Format connection information specifically for agent service (no emojis).
        
        Args:
            connection_info: Connection information dictionary
            
        Returns:
            Formatted string for agent service display
        """
        try:
            if not connection_info:
                return ""

            output_parts = []

            for result_key, info in connection_info.items():
                result_num = result_key.replace("result_", "")
                output_parts.append(f"\n=== CONNECTIONS FOR RESULT {result_num} ===")

                # Add clean note without emojis
                note = self._generate_clean_connection_note(info.get("connections", {}))
                if note:
                    output_parts.append(note)

                # Format incoming connections
                incoming = info.get("connections", {}).get("incoming", [])
                if incoming:
                    output_parts.append(f"\nINCOMING CONNECTIONS ({len(incoming)}):")
                    for i, conn in enumerate(incoming, 1):
                        output_parts.append(f"  {i}. {conn.get('description', 'No description')}")
                        output_parts.append(f"     Technology: {conn.get('technology_name', 'Unknown')}")
                        output_parts.append(f"     File: {conn.get('file_path', 'Unknown')}")
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")

                        # Show mapped connections with details
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(f"     Connected to {len(mapped)} outgoing connection(s):")
                            for j, mapped_conn in enumerate(mapped, 1):
                                output_parts.append(f"       {j}. {mapped_conn.get('outgoing_description', 'No description')}")
                                output_parts.append(f"          File: {mapped_conn.get('outgoing_file_path', 'Unknown')}")
                                output_parts.append(f"          Technology: {mapped_conn.get('outgoing_technology', 'Unknown')}")
                                if mapped_conn.get("outgoing_code_snippet"):
                                    mapped_snippet = mapped_conn[
                                        "outgoing_code_snippet"
                                    ]
                                    output_parts.append(f"          Code: {mapped_snippet}")

                # Format outgoing connections
                outgoing = info.get("connections", {}).get("outgoing", [])
                if outgoing:
                    output_parts.append(f"\nOUTGOING CONNECTIONS ({len(outgoing)}):")
                    for i, conn in enumerate(outgoing, 1):
                        output_parts.append(f"  {i}. {conn.get('description', 'No description')}")
                        output_parts.append(f"     Technology: {conn.get('technology_name', 'Unknown')}")
                        output_parts.append(f"     File: {conn.get('file_path', 'Unknown')}")
                        if conn.get("code_snippet"):
                            snippet_preview = conn["code_snippet"]
                            output_parts.append(f"     Code: {snippet_preview}")

                        # Show mapped connections with details
                        mapped = conn.get("mapped_connections", [])
                        if mapped:
                            output_parts.append(f"     Connected to {len(mapped)} incoming connection(s):")
                            for j, mapped_conn in enumerate(mapped, 1):
                                output_parts.append(f"       {j}. {mapped_conn.get('incoming_description', 'No description')}")
                                output_parts.append(f"          File: {mapped_conn.get('incoming_file_path', 'Unknown')}")
                                output_parts.append(f"          Technology: {mapped_conn.get('incoming_technology', 'Unknown')}")
                                if mapped_conn.get("incoming_code_snippet"):
                                    mapped_snippet = mapped_conn[
                                        "incoming_code_snippet"
                                    ]
                                    output_parts.append(f"          Code: {mapped_snippet}")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error(f"Error formatting connections for agent: {e}")
            return "\nConnection information available but could not format for display."

    def _generate_clean_connection_note(self, connections: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate a clean note about connections without emojis.
        
        Args:
            connections: Dictionary with incoming and outgoing connections
            
        Returns:
            Clean note string for the agent
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
                note += " These connections are linked to other parts of the system."

            note += " If you are making changes to this code, make sure to update its connected connection code also to maintain consistency."
            note += " If you want to know how that connected code is working, consider fetching those file codes to get better understanding of the codebase."
            note += " Use database search to get data of that file or function for deeper analysis."
            note += " If your changes are not related to these connections, ignore this message."

            return note

        except Exception as e:
            logger.error(f"Error generating clean connection note: {e}")
            return "Connection information available but could not generate note."


def get_agent_connection_enhancer(db_connection) -> AgentConnectionEnhancer:
    """Factory function to create an AgentConnectionEnhancer instance."""
    return AgentConnectionEnhancer(db_connection)
