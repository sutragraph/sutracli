from baml_client.types import ConnectionMatchingResponse
from loguru import logger
from typing import Any, Dict

def format_connections(connections, connection_type):
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


def validate_and_process_baml_results(
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
