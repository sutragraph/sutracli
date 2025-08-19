"""
BAML-based Connection Matching Prompt Manager

This module integrates BAML with dynamic provider selection based on configuration.
Uses the existing config system and llm_factory pattern for provider selection.
"""

from typing import Dict, Any
from loguru import logger
from baml_client.sync_client import b as baml
from baml_client.types import ConnectionMatchingResponse
from graph.sqlite_client import SQLiteConnection
from config import config


class Phase5PromptManager:
    """
    BAML-based connection matching manager with dynamic provider selection.
    Uses the existing config system to determine which provider and function to use.
    """

    # Provider mapping from config to BAML function prefix
    PROVIDER_MAPPING = {
        "aws": "Aws",
        "openai": "ChatGPT",
        "anthropic": "Anthropic",
        "gcp": "Gemini",
    }

    def __init__(self):
        self.db_client = SQLiteConnection()
        self.provider = config.llm.provider.lower()
        self.function_prefix = self.PROVIDER_MAPPING.get(self.provider, "Aws")

        logger.info(
            f"🤖 Phase5PromptManager initialized with provider: {self.provider}"
        )
        logger.info(f"🔧 Using function prefix: {self.function_prefix}")

    def fetch_incoming_connections_from_db(self):
        """
        Fetch incoming connections directly from database.

        Args:
            project_id (int, optional): Project ID to filter connections

        Returns:
            list: List of incoming connection objects from database
        """
        if not self.db_client:
            print("Error: No database client provided to ConnectionMatchingManager")
            return []

        try:
            query = """
            SELECT ic.id, ic.description, ic.technology_name as technology,
                    ic.code_snippet, ic.snippet_lines, files.file_path, files.language
            FROM incoming_connections ic
            LEFT JOIN files ON ic.file_id = files.id
            ORDER BY ic.id
            """
            results = self.db_client.execute_query(query)
            return results or []
        except Exception as e:
            print(f"Error fetching incoming connections: {e}")
            return []

    def fetch_outgoing_connections_from_db(self):
        """
        Fetch outgoing connections directly from database.

        Args:
            project_id (int, optional): Project ID to filter connections

        Returns:
            list: List of outgoing connection objects from database
        """
        if not self.db_client:
            print("Error: No database client provided to ConnectionMatchingManager")
            return []

        try:
            query = """
            SELECT oc.id, oc.description, oc.technology_name as technology,
                    oc.code_snippet, oc.snippet_lines, files.file_path, files.language
            FROM outgoing_connections oc
            LEFT JOIN files ON oc.file_id = files.id
            ORDER BY oc.id
            """
            results = self.db_client.execute_query(query)
            return results or []
        except Exception as e:
            print(f"Error fetching outgoing connections: {e}")
            return []

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

    def run_connection_matching(self) -> Dict[str, Any]:
        """
        Run connection matching analysis using BAML.

        This is the main entry point that replaces the old prompt-based system.

        Returns:
            dict: Matching results ready for database storage
        """
        try:
            # Fetch connections from database
            incoming_connections = self.fetch_incoming_connections_from_db()
            outgoing_connections = self.fetch_outgoing_connections_from_db()

            logger.info(
                f"🔗 BAML Phase 5: Attempting to match {len(incoming_connections)} incoming with {len(outgoing_connections)} outgoing connections"
            )

            # Format connections for BAML
            incoming_formatted = self._format_connections(
                incoming_connections, "INCOMING"
            )
            outgoing_formatted = self._format_connections(
                outgoing_connections, "OUTGOING"
            )

            # Get the provider-specific function name
            function_name = f"{self.function_prefix}ConnectionMatching"

            # Call BAML function with role-based caching and token tracking
            logger.info(
                f"🤖 Calling BAML {function_name} (provider: {self.provider}) with role-based caching..."
            )

            # Get the function dynamically based on provider
            if not hasattr(baml, function_name):
                raise AttributeError(
                    f"Function {function_name} not found in BAML client. Available providers: {list(self.PROVIDER_MAPPING.keys())}"
                )

            baml_function = getattr(baml, function_name)

            # Call the provider-specific function
            response: ConnectionMatchingResponse = baml_function(
                incoming_connections=incoming_formatted,
                outgoing_connections=outgoing_formatted,
            )

            # Process and validate results
            is_valid, processed_results = self._validate_and_process_baml_results(
                response, incoming_connections, outgoing_connections
            )

            if is_valid:
                matches_count = len(processed_results.get("matches", []))
                logger.info(
                    f"✅ BAML Phase 5 validation successful: {matches_count} matches found"
                )
                return {
                    "success": True,
                    "results": processed_results,
                    "message": f"Successfully matched {matches_count} connections using BAML",
                }
            else:
                logger.error(f"❌ BAML Phase 5 validation failed: {processed_results}")
                return {
                    "success": False,
                    "error": processed_results,
                    "message": "BAML connection matching failed due to invalid response",
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
            if not hasattr(response, "matches") or not isinstance(
                response.matches, list
            ):
                return False, {
                    "error": "Invalid response format: missing or invalid matches"
                }

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
                        "connection_type",
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
                        "connection_type": match.connection_type,
                        "provider": self.provider,
                    }
                )

            return True, {
                "matches": processed_matches,
                "total_matches": len(processed_matches),
                "provider": self.provider,
                "function_used": f"{self.function_prefix}ConnectionMatching",
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
