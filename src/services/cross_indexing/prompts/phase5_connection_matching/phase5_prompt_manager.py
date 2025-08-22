from typing import Dict, Any
from loguru import logger
from baml_client.types import ConnectionMatchingResponse
from graph.sqlite_client import SQLiteConnection
from services.cross_indexing.utils.baml_utils import call_baml


class Phase5PromptManager:

    def __init__(self):
        self.db_client = SQLiteConnection()


    def _format_connections(self, connections, connection_type):
        """
        Format connection list for prompt display.

        Args:
            connections (list): List of connection objects
            connection_type (str): "INCOMING" or "OUTGOING"

        Returns:
            str: Formatted connection list
        """
        if not connections:
            return f"No {connection_type.lower()} connections found."

        formatted_list = []
        for conn in connections:
            formatted_conn = f"""ID: {conn.get('id', 'N/A')}
description: "{conn.get('description', 'N/A')}"
technology: {conn.get('technology', 'N/A')}"""

            code_snippet = conn.get("code_snippet", "")
            if code_snippet and code_snippet.strip():
                formatted_conn += f"""
code_snippet:
{code_snippet}"""
            formatted_list.append(formatted_conn)

        return "\n\n".join(formatted_list)

    def get_all_technology_types(self) -> list:
        """
        Get all unique technology types from both incoming and outgoing connections.
        Returns all distinct technology types including Unknown.
        
        Returns:
            List of unique technology type names (including Unknown if exists)
        """
        if not self.db_client:
            logger.error("No database client available")
            return []
            
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
            results = self.db_client.execute_query(query)
            return [row['technology'] for row in (results or [])]
        except Exception as e:
            logger.error(f"Error fetching technology types: {e}")
            return []

    def get_available_technology_types(self) -> list:
        """
        Get all unique technology types excluding Unknown.
        
        Returns:
            List of unique technology type names (excluding Unknown)
        """
        all_types = self.get_all_technology_types()
        return [t for t in all_types if t != 'Unknown']
    
    def fetch_connections_by_technology(self, technology: str) -> Dict[str, list]:
        """
        Fetch both incoming and outgoing connections for a specific technology type.
        
        Args:
            technology: Technology type to fetch
            
        Returns:
            Dict with 'incoming' and 'outgoing' keys containing connection lists
        """
        if not self.db_client:
            logger.error("No database client available")
            return {'incoming': [], 'outgoing': []}
            
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
            
            incoming_results = self.db_client.execute_query(incoming_query, params) or []
            outgoing_results = self.db_client.execute_query(outgoing_query, params) or []
            
            return {
                'incoming': incoming_results,
                'outgoing': outgoing_results
            }
            
        except Exception as e:
            logger.error(f"Error fetching connections for technology {technology}: {e}")
            return {'incoming': [], 'outgoing': []}

    def run_connection_matching(self) -> Dict[str, Any]:
        """
        Run connection matching analysis using BAML with optimized approach.
        
        OPTIMIZATION: Fetch unknown connections once, then for each technology type,
        fetch its connections and add unknown connections to it.

        Returns:
            dict: Matching results ready for database storage
        """
        try:
            # First, get all technology types to check if Unknown exists
            all_types_including_unknown = self.get_all_technology_types()
            has_unknown = 'Unknown' in all_types_including_unknown
            
            # Only fetch unknown connections if they exist
            unknown_connections = {'incoming': [], 'outgoing': []}
            if has_unknown:
                logger.info("🔄 Fetching Unknown connections...")
                unknown_connections = self.fetch_connections_by_technology('Unknown')
                logger.info(f"   Found {len(unknown_connections['incoming'])} incoming and {len(unknown_connections['outgoing'])} outgoing Unknown connections")
            else:
                logger.info("ℹ️ No Unknown connections found, skipping Unknown fetch")
            
            # Get all distinct technology types (excluding Unknown)
            all_tech_types = self.get_available_technology_types()
            
            logger.info(
                f"🔗 BAML Phase 5: Starting connection matching for {len(all_tech_types)} technology types"
            )
            logger.info(f"📊 Found technology types: {', '.join(sorted(all_tech_types))}")
            
            # Collect all matches from each technology type
            all_matches = []
            total_incoming_processed = 0
            total_outgoing_processed = 0
            
            # Process each technology type one by one
            for tech_type in sorted(all_tech_types):
                logger.info(f"🔄 Processing {tech_type} connections...")
                
                # Fetch specific technology type connections
                tech_connections = self.fetch_connections_by_technology(tech_type)
                
                # Add unknown connections to this technology type
                connections = {
                    'incoming': tech_connections['incoming'] + unknown_connections['incoming'],
                    'outgoing': tech_connections['outgoing'] + unknown_connections['outgoing']
                }
                
                logger.info(f"   Combined {len(tech_connections['incoming'])} + {len(unknown_connections['incoming'])} = {len(connections['incoming'])} incoming connections")
                logger.info(f"   Combined {len(tech_connections['outgoing'])} + {len(unknown_connections['outgoing'])} = {len(connections['outgoing'])} outgoing connections")
                
                incoming_connections = connections['incoming']
                outgoing_connections = connections['outgoing']
                
                # Skip if no connections for this technology type
                if not incoming_connections and not outgoing_connections:
                    logger.debug(f"   No connections found for {tech_type}, skipping...")
                    continue
                    
                logger.info(
                    f"   Matching {len(incoming_connections)} incoming with {len(outgoing_connections)} outgoing connections for {tech_type}"
                )
                
                # Format connections for BAML
                incoming_formatted = self._format_connections(
                    incoming_connections, "INCOMING"
                )
                outgoing_formatted = self._format_connections(
                    outgoing_connections, "OUTGOING"
                )
                
                # Call BAML function for this technology type
                try:
                    baml_response = call_baml(
                        function_name="ConnectionMatching",
                        incoming_connections=incoming_formatted,
                        outgoing_connections=outgoing_formatted,
                    )
                    
                    # Extract the actual response content from BAMLResponse
                    response = baml_response.content if hasattr(baml_response, 'content') else baml_response
                    
                    # Process and validate results for this technology type
                    is_valid, tech_results = self._validate_and_process_baml_results(
                        response, incoming_connections, outgoing_connections
                    )
                    
                    if is_valid:
                        matches = tech_results.get("matches", [])
                        all_matches.extend(matches)
                        logger.info(f"   ✅ Found {len(matches)} matches for {tech_type}")
                        total_incoming_processed += len(incoming_connections)
                        total_outgoing_processed += len(outgoing_connections)
                    else:
                        logger.warning(f"   ⚠️ Failed to process {tech_type}: {tech_results}")
                        
                except Exception as tech_error:
                    logger.error(f"   ❌ Error processing {tech_type}: {tech_error}")
                    continue
            
            # Return combined results
            logger.info(
                f"✅ BAML Phase 5 completed: {len(all_matches)} total matches found"
            )
            
            return {
                "success": True,
                "results": {
                    "matches": all_matches,
                    "total_matches": len(all_matches),
                    "technology_types_processed": all_tech_types,
                    "stats": {
                        "total_incoming_connections_processed": total_incoming_processed,
                        "total_outgoing_connections_processed": total_outgoing_processed,
                        "technology_types_found": len(all_tech_types)
                    }
                },
                "message": f"Successfully matched {len(all_matches)} connections across {len(all_tech_types)} technology types",
            }

        except Exception as e:
            logger.error(f"❌ BAML Phase 5 connection matching error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "BAML connection matching failed due to unexpected error",
            }

    def _validate_and_process_baml_results(
        self,
        response: ConnectionMatchingResponse,
        incoming_connections: list,
        outgoing_connections: list,
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Validate and process BAML response results.

        Args:
            response: BAML ConnectionMatchingResponse object
            incoming_connections: List of incoming connections for validation
            outgoing_connections: List of outgoing connections for validation

        Returns:
            tuple: (is_valid, processed_results)
        """
        try:

            processed_matches = []
            incoming_ids = {str(conn.get("id")) for conn in incoming_connections}
            outgoing_ids = {str(conn.get("id")) for conn in outgoing_connections}

            for match in response.matches:
                # Validate match structure
                if not all(
                    hasattr(match, attr)
                    for attr in [
                        "incoming_id",
                        "outgoing_id",
                        "match_confidence",
                        "match_reason",
                    ]
                ):
                    logger.warning(f"Invalid match structure: {match}")
                    continue

                # Validate IDs exist in the original data
                if str(match.incoming_id) not in incoming_ids:
                    logger.warning(f"Invalid incoming_id: {match.incoming_id}")
                    continue

                if str(match.outgoing_id) not in outgoing_ids:
                    logger.warning(f"Invalid outgoing_id: {match.outgoing_id}")
                    continue

                processed_matches.append(
                    {
                        "incoming_id": str(match.incoming_id),
                        "outgoing_id": str(match.outgoing_id),
                        "match_confidence": match.match_confidence,
                        "match_reason": match.match_reason,
                    }
                )

            return True, {
                "matches": processed_matches,
                "total_matches": len(processed_matches),
            }

        except Exception as e:
            logger.error(f"Error validating BAML results: {e}")
            return False, {"error": f"Validation error: {str(e)}"}

    # Backward compatibility methods (deprecated)
    def get_system_prompt(self) -> str:
        """
        DEPRECATED: This method is kept for backward compatibility.
        The new BAML-based system doesn't use raw system prompts.

        Returns:
            str: Deprecation notice
        """
        return "DEPRECATED: This system now uses BAML. Use run_connection_matching() instead."


def run_connection_matching() -> Dict[str, Any]:
    """
    Run the connection matching analysis using the Phase 5 prompt manager.

    This is the entry point for external calls to perform connection matching.

    Returns:
        dict: Results of the connection matching analysis
    """
    manager = Phase5PromptManager()
    return manager.run_connection_matching()
