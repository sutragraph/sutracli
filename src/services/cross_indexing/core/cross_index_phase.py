from typing import Dict, Any
from src.utils.baml_utils import call_baml
from src.utils.system_utils import get_home_and_current_directories
from loguru import logger


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


# 
