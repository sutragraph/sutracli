"""
Connection Matching Service

Handles the complete connection matching workflow including LLM analysis,
JSON validation, and database storage of matched connections using existing database schema.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..prompts.phase5_connection_matching.phase5_prompt_manager import (
    Phase5PromptManager,
)
from ...llm_clients.llm_factory import llm_client_factory
from graph.sqlite_client import SQLiteConnection

logger = logging.getLogger(__name__)


class ConnectionMatchingService:
    """
    Service for matching incoming and outgoing connections and storing results in database.

    This service:
    1. Takes lists of incoming and outgoing connections with IDs
    2. Uses LLM to analyze and match connections
    3. Validates JSON response format
    4. Stores matched connections in database
    5. Returns matching results and statistics
    """

    def __init__(self):
        self.db_client = SQLiteConnection()
        self.matching_manager = Phase5PromptManager()

    def match_connections(
        self,
        incoming_connections: List[Dict] = None,
        outgoing_connections: List[Dict] = None,
        project_id: str = None,
    ) -> Dict[str, Any]:
        """
        Main method to match connections and store results in database.
        Fetches data directly from database if connections are not provided.

        Args:
            incoming_connections: Optional list of incoming connection objects with IDs
            outgoing_connections: Optional list of outgoing connection objects with IDs
            project_id: Optional project identifier for database storage and fetching

        Returns:
            Dict containing matching results and database storage status
        """
        try:
            # Step 1: Build matching prompt - will fetch from database if connections not provided
            matching_prompt = self.matching_manager.build_matching_prompt(
                incoming_connections, outgoing_connections, project_id
            )

            # Get the actual connections for validation and logging (fetch from DB if needed)
            if incoming_connections is None:
                incoming_connections = (
                    self.matching_manager.fetch_incoming_connections_from_db(project_id)
                )
            if outgoing_connections is None:
                outgoing_connections = (
                    self.matching_manager.fetch_outgoing_connections_from_db(project_id)
                )

            logger.info(
                f"Starting connection matching for {len(incoming_connections)} incoming and {len(outgoing_connections)} outgoing connections"
            )

            # Step 2: Get LLM analysis with retry logic for malformed JSON
            llm_client = llm_client_factory()
            matching_results = None
            max_retries = 5
            last_error = None

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Connection matching attempt {attempt + 1}/{max_retries}"
                    )

                    # Get LLM response
                    llm_response = llm_client.call_llm(
                        "", matching_prompt, return_raw=True
                    )

                    # Parse and validate JSON response
                    matching_results = self._parse_and_validate_response(llm_response)

                    if matching_results:
                        logger.info(
                            f"Successfully parsed JSON response on attempt {attempt + 1}"
                        )
                        break
                    else:
                        last_error = f"Failed to parse or validate LLM response on attempt {attempt + 1}"
                        logger.warning(
                            f"{last_error}. Raw response: {llm_response[:200]}..."
                        )

                        if attempt < max_retries - 1:
                            logger.info(
                                f"Retrying connection matching (attempt {attempt + 2}/{max_retries})"
                            )

                except Exception as e:
                    last_error = (
                        f"Error during LLM analysis on attempt {attempt + 1}: {str(e)}"
                    )
                    logger.error(last_error)

                    if attempt < max_retries - 1:
                        logger.info(
                            f"Retrying connection matching due to error (attempt {attempt + 2}/{max_retries})"
                        )

            # Step 3: Check if we got valid results after all retries
            if not matching_results:
                return {
                    "success": False,
                    "error": f"Failed to get valid JSON response after {max_retries} attempts. Last error: {last_error}",
                    "attempts_made": max_retries,
                }

            # Step 4: Process and enrich results
            is_valid, processed_results = (
                self.matching_manager.validate_and_process_matching_results(
                    matching_results, incoming_connections, outgoing_connections
                )
            )

            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {processed_results}",
                    "raw_response": llm_response,
                }

            # Step 5: Store results in database
            storage_result = self._store_matching_results(processed_results, project_id)

            # Step 6: Return comprehensive results
            return {
                "success": True,
                "matching_results": processed_results,
                "database_storage": storage_result,
                "statistics": {
                    "total_incoming": len(incoming_connections),
                    "total_outgoing": len(outgoing_connections),
                    "total_matches": processed_results.get("total_matches", 0),
                    "match_rate": round(
                        (
                            processed_results.get("total_matches", 0)
                            / max(
                                len(incoming_connections) + len(outgoing_connections), 1
                            )
                        )
                        * 100,
                        2,
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error in connection matching: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "statistics": {
                    "total_incoming": len(incoming_connections),
                    "total_outgoing": len(outgoing_connections),
                    "total_matches": 0,
                },
                "attempts_made": 0,
            }

    def _parse_and_validate_response(self, llm_response: str) -> Optional[Dict]:
        """
        Parse and validate LLM response as JSON.

        Args:
            llm_response: Raw response from LLM

        Returns:
            Parsed JSON dict or None if invalid
        """
        try:
            # Try to extract JSON from response (in case there's extra text)
            response_text = llm_response.strip()

            # Look for JSON block if wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()

            # Parse JSON
            parsed_json = json.loads(response_text)

            # Validate required structure
            required_fields = ["matches", "total_matches"]

            for field in required_fields:
                if field not in parsed_json:
                    logger.error(f"Missing required field in JSON response: {field}")
                    return None

            # Additional validation for matches structure
            if not isinstance(parsed_json.get("matches"), list):
                logger.error("'matches' field must be a list")
                return None

            # Validate each match has required fields
            for i, match in enumerate(parsed_json["matches"]):
                required_match_fields = [
                    "outgoing_id",
                    "incoming_id",
                    "match_confidence",
                    "match_reason",
                    "connection_type",
                ]
                for field in required_match_fields:
                    if field not in match:
                        logger.error(f"Missing required field '{field}' in match {i}")
                        return None

            logger.debug(
                f"Successfully parsed and validated JSON response with {len(parsed_json['matches'])} matches"
            )
            return parsed_json

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.debug(f"Problematic response text: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            return None

    def _store_matching_results(
        self, matching_results: Dict, project_id: str = None
    ) -> Dict[str, Any]:
        """
        Store ONLY matching results in database, not the connection data itself.
        Connection data should already be stored during attempt_completion phase.

        Args:
            matching_results: Processed matching results
            project_id: Optional project identifier

        Returns:
            Dict with storage status and details
        """
        try:
            stored_matches = []
            matches = matching_results.get("matches", [])

            # Only store match data if matches are found, otherwise skip storage
            if not matches:
                logger.info("No matches found - skipping match storage")
                return {
                    "success": True,
                    "stored_matches": [],
                    "summary_id": None,
                    "total_stored": 0,
                    "message": "No matches found - storage skipped",
                }

            # Store only the match relationships, not the connection data
            for match in matches:
                # Prepare match data for database - only store match metadata
                match_data = {
                    "outgoing_connection_id": match["outgoing_id"],
                    "incoming_connection_id": match["incoming_id"],
                    "match_confidence": match["match_confidence"],
                    "match_reason": match["match_reason"],
                    "connection_type": match["connection_type"],
                    "project_id": project_id,
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Insert only match relationship into database
                match_id = self._insert_connection_match(match_data)
                if match_id:
                    stored_matches.append(
                        {
                            "match_id": match_id,
                            "outgoing_id": match["outgoing_id"],
                            "incoming_id": match["incoming_id"],
                            "confidence": match["match_confidence"],
                        }
                    )

            # Store summary statistics only if matches were found
            summary_data = {
                "project_id": project_id,
                "total_incoming": matching_results.get("total_incoming", 0),
                "total_outgoing": matching_results.get("total_outgoing", 0),
                "total_matches": len(stored_matches),
                "unmatched_incoming_count": len(
                    matching_results.get("unmatched_incoming", [])
                ),
                "unmatched_outgoing_count": len(
                    matching_results.get("unmatched_outgoing", [])
                ),
                "analysis_summary": matching_results.get("analysis_summary", ""),
                "created_at": datetime.utcnow().isoformat(),
            }

            summary_id = self._insert_matching_summary(summary_data)

            logger.info(
                f"Stored {len(stored_matches)} match relationships (no duplicate connection data)"
            )

            return {
                "success": True,
                "stored_matches": stored_matches,
                "summary_id": summary_id,
                "total_stored": len(stored_matches),
                "message": f"Stored {len(stored_matches)} match relationships only",
            }

        except Exception as e:
            logger.error(f"Error storing matching results: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stored_matches": [],
                "total_stored": 0,
            }

    def _insert_connection_match(self, match_data: Dict) -> Optional[str]:
        """
        Insert a single connection match into existing connection_mappings table.
        Only stores match relationship metadata, not connection data (to avoid duplicates).

        Args:
            match_data: Match data to insert

        Returns:
            Match ID if successful, None otherwise
        """
        try:
            # Insert only match relationship into connection_mappings table
            insert_sql = """
            INSERT INTO connection_mappings (
                sender_id, receiver_id, connection_type, description,
                match_confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """

            # Use the connection IDs directly (connections already stored during attempt_completion)
            outgoing_id = match_data["outgoing_connection_id"]
            incoming_id = match_data["incoming_connection_id"]

            # Convert confidence to numeric value
            confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
            confidence_score = confidence_map.get(match_data["match_confidence"], 0.5)

            values = (
                outgoing_id,  # sender_id (outgoing connection)
                incoming_id,  # receiver_id (incoming connection)
                match_data.get("connection_type", "HTTP_API"),
                match_data["match_reason"],
                confidence_score,
                match_data["created_at"],
            )

            cursor = self.db_client.connection.execute(insert_sql, values)
            self.db_client.connection.commit()

            logger.debug(
                f"Inserted match relationship: outgoing_id={outgoing_id} -> incoming_id={incoming_id}"
            )
            return cursor.lastrowid if cursor.lastrowid else None

        except Exception as e:
            logger.error(f"Error inserting connection match: {str(e)}")
            return None

    def _insert_matching_summary(self, summary_data: Dict) -> Optional[str]:
        """
        Insert matching summary as a project record or log entry.

        Args:
            summary_data: Summary data to insert

        Returns:
            Summary ID if successful, None otherwise
        """
        try:
            # Store summary as JSON in a simple log table or project metadata
            # For now, we'll log it and return a timestamp-based ID
            logger.info(
                f"Connection matching summary: {json.dumps(summary_data, indent=2)}"
            )

            # Create a simple summary ID based on timestamp
            summary_id = f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            return summary_id

        except Exception as e:
            logger.error(f"Error logging matching summary: {str(e)}")
            return None

    def get_matching_history(
        self, project_id: str = None, limit: int = 10
    ) -> List[Dict]:
        """
        Get connection matching history from existing connection_mappings table.

        Args:
            project_id: Optional project filter
            limit: Maximum number of records to return

        Returns:
            List of matching history records
        """
        try:
            sql = """
            SELECT cm.*,
                   oc.description as outgoing_description,
                   ic.description as incoming_description
            FROM connection_mappings cm
            LEFT JOIN outgoing_connections oc ON cm.sender_id = oc.id
            LEFT JOIN incoming_connections ic ON cm.receiver_id = ic.id
            ORDER BY cm.created_at DESC
            LIMIT ?
            """
            values = (limit,)

            results = self.db_client.execute_query(sql, values)
            return results or []

        except Exception as e:
            logger.error(f"Error fetching matching history: {str(e)}")
            return []

    def get_connection_matches(
        self, project_id: str = None, confidence_filter: float = None
    ) -> List[Dict]:
        """
        Get stored connection matches from existing connection_mappings table.

        Args:
            project_id: Optional project filter
            confidence_filter: Optional confidence level filter (0.0-1.0)

        Returns:
            List of connection matches
        """
        try:
            base_sql = """
            SELECT cm.*,
                   oc.description as outgoing_description,
                   oc.technology_name as outgoing_technology,
                   ic.description as incoming_description,
                   ic.technology_name as incoming_technology
            FROM connection_mappings cm
            LEFT JOIN outgoing_connections oc ON cm.sender_id = oc.id
            LEFT JOIN incoming_connections ic ON cm.receiver_id = ic.id
            """
            conditions = []
            values = []

            if project_id:
                conditions.append("(oc.project_id = ? OR ic.project_id = ?)")
                values.extend([project_id, project_id])

            if confidence_filter is not None:
                conditions.append("cm.match_confidence >= ?")
                values.append(confidence_filter)

            if conditions:
                sql = f"{base_sql} WHERE {' AND '.join(conditions)} ORDER BY cm.created_at DESC"
            else:
                sql = f"{base_sql} ORDER BY cm.created_at DESC"

            results = self.db_client.execute_query(sql, values)
            return results or []

        except Exception as e:
            logger.error(f"Error fetching connection matches: {str(e)}")
            return []
