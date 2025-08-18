"""
Connection Matching Manager

Manages the connection matching process that runs after cross-indexing analysis.
Handles the workflow of matching incoming and outgoing connections and storing results.
"""

from ..prompts.phase5_connection_matching.connection_matching_prompt import (
    CONNECTION_MATCHING_PROMPT,
)
from graph.sqlite_client import SQLiteConnection


class ConnectionMatchingManager:
    """
    Manages the connection matching workflow that runs after cross-indexing analysis.

    This class handles:
    1. Processing incoming and outgoing connection lists
    2. Formatting data for the LLM prompt
    3. Managing the matching analysis
    4. Processing JSON responses
    5. Storing matched connections in database
    """

    def __init__(self):
        self.matching_prompt = CONNECTION_MATCHING_PROMPT
        self.db_client = SQLiteConnection()

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

    def build_matching_prompt(
        self, incoming_connections=None, outgoing_connections=None
    ):
        """
        Build the complete prompt for connection matching analysis.
        Fetches data directly from database if connections are not provided.

        Args:
            incoming_connections (list, optional): List of incoming connection objects
            outgoing_connections (list, optional): List of outgoing connection objects
            project_id (int, optional): Project ID to fetch connections from database

        Returns:
            str: Complete prompt for LLM analysis
        """

        # If connections are not provided, fetch from database
        if incoming_connections is None:
            incoming_connections = self.fetch_incoming_connections_from_db()

        if outgoing_connections is None:
            outgoing_connections = self.fetch_outgoing_connections_from_db()

        # Format incoming connections
        incoming_formatted = self._format_connections(incoming_connections, "INCOMING")

        # Format outgoing connections
        outgoing_formatted = self._format_connections(outgoing_connections, "OUTGOING")

        # Build complete prompt - avoid duplicate headers since CONNECTION_MATCHING_PROMPT already has them
        complete_prompt = f"""{self.matching_prompt}

### INCOMING CONNECTIONS
{incoming_formatted}

### OUTGOING CONNECTIONS
{outgoing_formatted}

Analyze the above incoming and outgoing connections and return a JSON response with matched connection pairs according to the specified format and matching criteria.

Remember: Return ONLY valid JSON with no additional text or explanations.
"""

        return complete_prompt

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

    def validate_matching_response(self, response_json):
        """
        Validate the JSON response from connection matching analysis.

        Args:
            response_json (dict): JSON response from LLM

        Returns:
            tuple: (is_valid, error_message)
        """
        required_fields = ["matches"]

        # Check required top-level fields
        for field in required_fields:
            if field not in response_json:
                return False, f"Missing required field: {field}"

        # Validate matches structure
        if not isinstance(response_json["matches"], list):
            return False, "Matches field must be a list"

        for match in response_json["matches"]:
            required_match_fields = [
                "outgoing_id",
                "incoming_id",
                "match_confidence",
                "match_reason",
                "connection_type",
            ]
            for field in required_match_fields:
                if field not in match:
                    return False, f"Missing required match field: {field}"

            # Validate confidence level
            if match["match_confidence"] not in ["high", "medium", "low"]:
                return False, f"Invalid confidence level: {match['match_confidence']}"

        return True, None

    def process_matching_results(
        self, response_json, incoming_connections, outgoing_connections
    ):
        """
        Process and validate matching results against original connection data.

        Args:
            response_json (dict): JSON response from LLM
            incoming_connections (list): Original incoming connections
            outgoing_connections (list): Original outgoing connections

        Returns:
            dict: Processed and validated matching results
        """
        # Create ID lookup maps
        incoming_map = {conn["id"]: conn for conn in incoming_connections}
        outgoing_map = {conn["id"]: conn for conn in outgoing_connections}

        # Validate and enrich matches
        validated_matches = []
        for i, match in enumerate(response_json["matches"]):
            outgoing_id_raw = match["outgoing_id"]
            incoming_id_raw = match["incoming_id"]

            # Convert string IDs to integers for lookup
            try:
                outgoing_id = int(outgoing_id_raw)
                incoming_id = int(incoming_id_raw)
            except (ValueError, TypeError):
                print(
                    f"⚠️  Match {i+1}: Invalid ID format - outgoing: {outgoing_id_raw}, incoming: {incoming_id_raw}"
                )
                continue

            # Check if IDs exist in our connection maps
            if outgoing_id not in outgoing_map:
                print(
                    f"⚠️  Match {i+1}: Outgoing ID {outgoing_id} not found in outgoing connections"
                )
                print(f"   Available outgoing IDs: {list(outgoing_map.keys())}")
                continue
            if incoming_id not in incoming_map:
                print(
                    f"⚠️  Match {i+1}: Incoming ID {incoming_id} not found in incoming connections"
                )
                print(f"   Available incoming IDs: {list(incoming_map.keys())}")
                continue

            # Enrich match with connection details
            enriched_match = {
                **match,
                "outgoing_id": outgoing_id,  # Use the converted integer ID
                "incoming_id": incoming_id,  # Use the converted integer ID
                "outgoing_connection": outgoing_map[outgoing_id],
                "incoming_connection": incoming_map[incoming_id],
            }
            validated_matches.append(enriched_match)

        # Update response with validated matches
        processed_response = {
            **response_json,
            "matches": validated_matches,
            "validation_status": "processed",
        }

        return processed_response

    def validate_and_process_matching_results(
        self, response_json, incoming_connections, outgoing_connections
    ):
        """
        Validate and process connection matching results.

        Args:
            response_json (dict): JSON response from LLM
            incoming_connections (list): Original incoming connections
            outgoing_connections (list): Original outgoing connections

        Returns:
            tuple: (is_valid, processed_results_or_error)
        """
        # Validate response format
        is_valid, error = self.validate_matching_response(response_json)
        if not is_valid:
            return False, error

        # Process and enrich results
        processed_results = self.process_matching_results(
            response_json, incoming_connections, outgoing_connections
        )

        return True, processed_results


def run_connection_matching(
    llm_client=None,
):
    """
    Main function to run connection matching analysis.
    Fetches data directly from database if connections are not provided.

    Args:
        incoming_connections (list, optional): List of incoming connection objects
        outgoing_connections (list, optional): List of outgoing connection objects
        llm_client: LLM client instance for making API calls
        project_id (int, optional): Project ID to fetch connections from database
        db_client: Database client instance for fetching connections

    Returns:
        dict: Matching results ready for database storage
    """
    manager = ConnectionMatchingManager()

    # Get the actual connections for validation (fetch from DB if needed)
    incoming_connections = manager.fetch_incoming_connections_from_db()
    outgoing_connections = manager.fetch_outgoing_connections_from_db()

    # Build prompt - will fetch from database if connections not provided
    prompt = manager.build_matching_prompt(incoming_connections, outgoing_connections)

    # Add logging to show what connections we're trying to match
    print(
        f"🔗 Phase 5: Attempting to match {len(incoming_connections)} incoming with {len(outgoing_connections)} outgoing connections"
    )
    if llm_client:
        try:
            # Call LLM service for connection matching - no system prompt needed, return raw response
            print("🤖 Calling LLM for Phase 5 connection matching...")
            response = llm_client.call_llm("", prompt, return_raw=True)
            print(f"📋 LLM Response length: {len(str(response))} characters")

            # Parse JSON response from raw text
            import json

            # Handle both string response and dict response
            if isinstance(response, str):
                response_text = response
            else:
                response_text = (
                    response.get("content", "")
                    if isinstance(response, dict)
                    else str(response)
                )

            # Clean up response text - remove any markdown formatting
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif response_text.startswith("```"):
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()

            response_json = json.loads(response_text)
            print(
                f"🔍 Parsed JSON response: {len(response_json.get('matches', []))} matches found"
            )

            # Validate and process results
            is_valid, processed_results = manager.validate_and_process_matching_results(
                response_json, incoming_connections, outgoing_connections
            )

            if is_valid:
                matches_count = len(processed_results.get("matches", []))
                print(
                    f"✅ Phase 5 validation successful: {matches_count} matches found"
                )
                return {
                    "success": True,
                    "results": processed_results,
                    "message": f"Successfully matched {matches_count} connections",
                }
            else:
                print(f"❌ Phase 5 validation failed: {processed_results}")
                return {
                    "success": False,
                    "error": processed_results,
                    "message": "Connection matching failed due to invalid response",
                }

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"📄 Raw response: {response}")
            return {
                "success": False,
                "error": f"Invalid JSON response from LLM: {str(e)}",
                "message": "Connection matching failed due to invalid response format",
            }
        except Exception as e:
            print(f"❌ Phase 5 connection matching error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection matching failed due to unexpected error",
            }
    else:
        # Fallback: return prompt if no LLM client provided (for testing)
        return {
            "success": False,
            "error": "No LLM client provided",
            "prompt": prompt,
            "message": "Connection matching skipped - no LLM client available",
        }
