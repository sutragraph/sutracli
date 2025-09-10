"""
Technology Name Validator

This module provides functionality to validate technology names against the predefined
enum list from the connection splitting prompt and correct mismatched names.
"""

from typing import List, Dict, Tuple
from loguru import logger


class TechnologyValidator:
    """
    Validates technology names against predefined enums and provides correction functionality.
    """

    # The 6 predefined technology enums from connection_splitting_prompt.py
    VALID_TECHNOLOGY_ENUMS = {
        "HTTP/HTTPS",
        "WebSockets",
        "gRPC",
        "GraphQL",
        "MessageQueue",
        "Unknown",
    }

    def __init__(self):
        """Initialize the technology validator."""
        pass

    def validate_technology_names(
        self, connections_data: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Validate all technology names in connections data against valid enums.

        Args:
            connections_data: Dictionary containing incoming_connections and outgoing_connections

        Returns:
            Tuple of (all_valid: bool, unmatched_names: List[str])
        """
        try:
            unmatched_names = set()

            # Check incoming connections
            if "incoming_connections" in connections_data:
                for conn in connections_data["incoming_connections"]:
                    tech_name = conn.get("technology", {}).get("name", "")
                    if tech_name and tech_name not in self.VALID_TECHNOLOGY_ENUMS:
                        unmatched_names.add(tech_name)

            # Check outgoing connections
            if "outgoing_connections" in connections_data:
                for conn in connections_data["outgoing_connections"]:
                    tech_name = conn.get("technology", {}).get("name", "")
                    if tech_name and tech_name not in self.VALID_TECHNOLOGY_ENUMS:
                        unmatched_names.add(tech_name)

            unmatched_list = list(unmatched_names)
            all_valid = len(unmatched_list) == 0

            if not all_valid:
                logger.warning(
                    f"Found {len(unmatched_list)} unmatched technology names: {unmatched_list}"
                )
            else:
                logger.debug("All technology names are valid")

            return all_valid, unmatched_list

        except Exception as e:
            logger.error(f"Error validating technology names: {e}")
            return False, []

    def extract_technology_names_from_json_response(self, json_data: Dict) -> List[str]:
        """
        Extract all technology names from the JSON response format.

        Args:
            json_data: Raw JSON data from connection splitting prompt

        Returns:
            List of unique technology names found
        """
        try:
            tech_names = set()

            # Extract from incoming connections
            incoming_data = json_data.get("incoming_connections", {})
            if isinstance(incoming_data, dict):
                for tech_name in incoming_data.keys():
                    if tech_name:
                        tech_names.add(tech_name)

            # Extract from outgoing connections
            outgoing_data = json_data.get("outgoing_connections", {})
            if isinstance(outgoing_data, dict):
                for tech_name in outgoing_data.keys():
                    if tech_name:
                        tech_names.add(tech_name)

            return list(tech_names)

        except Exception as e:
            logger.error(f"Error extracting technology names from JSON: {e}")
            return []

    def validate_json_technology_names(self, json_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate technology names directly from JSON response format.

        Args:
            json_data: Raw JSON data from connection splitting prompt

        Returns:
            Tuple of (all_valid: bool, unmatched_names: List[str])
        """
        try:
            tech_names = self.extract_technology_names_from_json_response(json_data)
            unmatched_names = []

            for tech_name in tech_names:
                if tech_name not in self.VALID_TECHNOLOGY_ENUMS:
                    unmatched_names.append(tech_name)

            all_valid = len(unmatched_names) == 0

            if not all_valid:
                logger.warning(
                    f"Found {len(unmatched_names)} unmatched technology names in JSON: {unmatched_names}"
                )
            else:
                logger.debug("All technology names in JSON are valid")

            return all_valid, unmatched_names

        except Exception as e:
            logger.error(f"Error validating JSON technology names: {e}")
            return False, []

    def get_valid_enums_list(self) -> List[str]:
        """
        Get the list of valid technology enums.

        Returns:
            List of valid technology enum names
        """
        return sorted(list(self.VALID_TECHNOLOGY_ENUMS))

    def apply_corrected_names(
        self, json_data: Dict, corrections: Dict[str, str]
    ) -> Dict:
        """
        Apply corrected technology names to the JSON data.

        Args:
            json_data: Original JSON data with incorrect names
            corrections: Dictionary mapping old_name -> corrected_name

        Returns:
            Updated JSON data with corrected technology names
        """
        try:
            corrected_data = json_data.copy()

            # Apply corrections to incoming connections
            if "incoming_connections" in corrected_data:
                incoming_data = corrected_data["incoming_connections"]
                if isinstance(incoming_data, dict):
                    # Create new dict with corrected keys
                    new_incoming = {}
                    for old_tech_name, files_data in incoming_data.items():
                        new_tech_name = corrections.get(old_tech_name, old_tech_name)
                        new_incoming[new_tech_name] = files_data
                    corrected_data["incoming_connections"] = new_incoming

            # Apply corrections to outgoing connections
            if "outgoing_connections" in corrected_data:
                outgoing_data = corrected_data["outgoing_connections"]
                if isinstance(outgoing_data, dict):
                    # Create new dict with corrected keys
                    new_outgoing = {}
                    for old_tech_name, files_data in outgoing_data.items():
                        new_tech_name = corrections.get(old_tech_name, old_tech_name)
                        new_outgoing[new_tech_name] = files_data
                    corrected_data["outgoing_connections"] = new_outgoing

            print(f"Applied {len(corrections)} technology name corrections")
            return corrected_data

        except Exception as e:
            logger.error(f"Error applying corrected names: {e}")
            return json_data
