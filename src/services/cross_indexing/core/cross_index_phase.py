from typing import Dict, Any
from src.utils.baml_utils import call_baml
from src.utils.system_utils import get_home_and_current_directories
from loguru import logger
from src.graph.graph_operations import GraphOperations
from ..utils import format_connections, validate_and_process_baml_results

# Code Manager Prompt
def run_code_manager(tool_results: str) -> Dict[str, Any]:
    """
    Run code manager analysis using BAML.

    Args:
        tool_results: Raw tool results from cross-indexing analysis

    Returns:
        dict: Results from BAML code manager analysis
    """
    try:
        # Call BAML function
        baml_response = call_baml(
            function_name="CodeManager",
            tool_results=tool_results,
            system_info=get_home_and_current_directories(),
        )

        # Extract the actual response content from BAMLResponse
        response = (
            baml_response.content
            if hasattr(baml_response, "content")
            else baml_response
        )

        logger.info("✅ BAML Code Manager: Code extraction analysis completed")

        return {
            "success": True,
            "results": response,
            "message": "Code manager analysis completed successfully using BAML",
        }

    except Exception as e:
        logger.error(f"❌ BAML Code Manager error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "BAML code manager analysis failed due to unexpected error",
        }


# Phase 1: Package Discovery Prompt


def run_package_discovery(
    analysis_query: str,
    memory_context: str = "",
) -> Dict[str, Any]:
    """
    Run package discovery analysis using BAML.

    Args:
        analysis_query: The analysis query/request
        memory_context: Current memory context from sutra memory

    Returns:
        dict: Results from BAML package discovery analysis
    """
    try:
        baml_response = call_baml(
            function_name="PackageDiscovery",
            analysis_query=analysis_query,
            memory_context=memory_context or "No previous context",
            system_info=get_home_and_current_directories(),
        )

        # Extract the actual response content from BAMLResponse
        response = (
            baml_response.content
            if hasattr(baml_response, "content")
            else baml_response
        )

        logger.info("✅ BAML Phase 1: Package discovery analysis completed")

        return {
            "success": True,
            "results": response,
            "message": "Package discovery analysis completed successfully using BAML",
        }

    except Exception as e:
        logger.error(f"❌ BAML Phase 1 package discovery error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "BAML package discovery analysis failed due to unexpected error",
        }


# Phase 2: Import Pattern Discovery Prompt


def run_import_discovery(
    analysis_query: str, memory_context: str = ""
) -> Dict[str, Any]:
    """
    Run import pattern discovery analysis using BAML.

    Args:
        analysis_query: The analysis query/request
        memory_context: Current memory context from sutra memory

    Returns:
        dict: Results from BAML import discovery analysis
    """
    try:
        # Call BAML function
        baml_response = call_baml(
            function_name="ImportDiscovery",
            analysis_query=analysis_query,
            memory_context=memory_context or "No previous context",
            system_info=get_home_and_current_directories(),
        )

        # Extract the actual response content from BAMLResponse
        response = (
            baml_response.content
            if hasattr(baml_response, "content")
            else baml_response
        )

        logger.info("✅ BAML Phase 2: Import discovery analysis completed")

        return {
            "success": True,
            "results": response,
            "message": "Import discovery analysis completed successfully using BAML",
        }

    except Exception as e:
        logger.error(f"❌ BAML Phase 2 import discovery error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "BAML import discovery analysis failed due to unexpected error",
        }


# Phase 3: Implementation Discovery Prompt


def run_implementation_discovery_baml(
    analysis_query: str, memory_context: str = ""
) -> Dict[str, Any]:
    """
    Run implementation discovery analysis using BAML.

    Args:
        analysis_query: The analysis query/request
        memory_context: Current memory context from sutra memory

    Returns:
        dict: Results from BAML implementation discovery analysis
    """
    try:
        # Call BAML function
        baml_response = call_baml(
            function_name="ImplementationDiscovery",
            analysis_query=analysis_query,
            memory_context=memory_context or "No previous context",
            system_info=get_home_and_current_directories(),
        )

        # Extract the actual response content from BAMLResponse
        response = (
            baml_response.content
            if hasattr(baml_response, "content")
            else baml_response
        )

        logger.info("✅ BAML Phase 3: Implementation discovery analysis completed")

        return {
            "success": True,
            "results": response,
            "message": "Implementation discovery analysis completed successfully using BAML",
        }

    except Exception as e:
        logger.error(f"❌ BAML Phase 3 implementation discovery error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "BAML implementation discovery analysis failed due to unexpected error",
        }


# Phase 4: Connection Splitting Prompt


def run_connection_splitting_baml(memory_context: str) -> Dict[str, Any]:
    """
    Run connection splitting analysis using BAML.

    Args:
        memory_context: Code snippets collected by the code manager from Phase 3

    Returns:
        dict: Results from BAML connection splitting analysis
    """
    try:
        # Call BAML function
        baml_response = call_baml(
            function_name="ConnectionSplitting", memory_context=memory_context
        )

        # Extract the actual response content from BAMLResponse
        response = (
            baml_response.content
            if hasattr(baml_response, "content")
            else baml_response
        )

        logger.info("✅ BAML Phase 4: Connection splitting analysis completed")

        return {
            "success": True,
            "results": response,
            "message": "Connection splitting analysis completed successfully using BAML",
        }

    except Exception as e:
        logger.error(f"❌ BAML Phase 4 connection splitting error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "BAML connection splitting analysis failed due to unexpected error",
        }


# Phase 5: Cross-Indexing Summary Prompt


def run_connection_matching() -> Dict[str, Any]:
    """
    Run connection matching analysis using BAML with optimized approach.

    OPTIMIZATION: Fetch unknown connections once, then for each technology type,
    fetch its connections and add unknown connections to it.

    Returns:
        dict: Matching results ready for database storage
    """
    try:
        graph_ops = GraphOperations()
        # First, get all technology types to check if Unknown exists
        all_types_including_unknown = graph_ops.get_all_technology_types()
        has_unknown = "Unknown" in all_types_including_unknown

        # Only fetch unknown connections if they exist
        unknown_connections = {"incoming": [], "outgoing": []}
        if has_unknown:
            logger.info("🔄 Fetching Unknown connections...")
            unknown_connections = graph_ops.fetch_connections_by_technology("Unknown")
            logger.info(
                f"   Found {len(unknown_connections['incoming'])} incoming and {len(unknown_connections['outgoing'])} outgoing Unknown connections"
            )
        else:
            logger.info("ℹ️ No Unknown connections found, skipping Unknown fetch")

        # Get all distinct technology types (excluding Unknown)
        all_tech_types = graph_ops.get_available_technology_types()

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
            tech_connections = graph_ops.fetch_connections_by_technology(tech_type)

            # Add unknown connections to this technology type
            connections = {
                "incoming": tech_connections["incoming"]
                + unknown_connections["incoming"],
                "outgoing": tech_connections["outgoing"]
                + unknown_connections["outgoing"],
            }

            logger.info(
                f"   Combined {len(tech_connections['incoming'])} + {len(unknown_connections['incoming'])} = {len(connections['incoming'])} incoming connections"
            )
            logger.info(
                f"   Combined {len(tech_connections['outgoing'])} + {len(unknown_connections['outgoing'])} = {len(connections['outgoing'])} outgoing connections"
            )

            incoming_connections = connections["incoming"]
            outgoing_connections = connections["outgoing"]

            # Skip if no connections for this technology type
            if not incoming_connections and not outgoing_connections:
                logger.debug(f"   No connections found for {tech_type}, skipping...")
                continue

            logger.info(
                f"   Matching {len(incoming_connections)} incoming with {len(outgoing_connections)} outgoing connections for {tech_type}"
            )

            # Format connections for BAML
            incoming_formatted = format_connections(incoming_connections, "INCOMING")
            outgoing_formatted = format_connections(outgoing_connections, "OUTGOING")

            # Call BAML function for this technology type
            try:
                baml_response = call_baml(
                    function_name="ConnectionMatching",
                    incoming_connections=incoming_formatted,
                    outgoing_connections=outgoing_formatted,
                )

                # Extract the actual response content from BAMLResponse
                response = (
                    baml_response.content
                    if hasattr(baml_response, "content")
                    else baml_response
                )

                # Process and validate results for this technology type
                is_valid, tech_results = validate_and_process_baml_results(
                    response, incoming_connections, outgoing_connections
                )

                if is_valid:
                    matches = tech_results.get("matches", [])
                    all_matches.extend(matches)
                    logger.info(f"   ✅ Found {len(matches)} matches for {tech_type}")
                    total_incoming_processed += len(incoming_connections)
                    total_outgoing_processed += len(outgoing_connections)
                else:
                    logger.warning(
                        f"   ⚠️ Failed to process {tech_type}: {tech_results}"
                    )

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
                    "technology_types_found": len(all_tech_types),
                },
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
