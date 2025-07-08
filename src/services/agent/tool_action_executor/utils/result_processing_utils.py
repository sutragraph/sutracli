"""
Utility functions for result processing shared between executors.
"""

from typing import Dict, Any, List
from .formatting_utils import beautify_node_result_metadata_only


def clean_result_dict(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove unnecessary fields from result dictionary.
    
    Args:
        result_dict: Raw result dictionary
        
    Returns:
        Cleaned result dictionary
    """
    cleaned = result_dict.copy()
    
    # Remove unnecessary fields
    for field in ["project_id", "project_name", "language", "file_size"]:
        cleaned.pop(field, None)
    
    return cleaned


def process_metadata_only_results(
    results: List[Any],
    total_nodes: int
) -> List[str]:
    """
    Process results for metadata-only scenarios.
    
    Args:
        results: List of raw results
        total_nodes: Total number of nodes
        
    Returns:
        List of beautified result strings
    """
    processed_results = []
    
    for i, row in enumerate(results, 1):
        result_dict = dict(row) if hasattr(row, "keys") else row
        cleaned_dict = clean_result_dict(result_dict)
        
        beautified_result = beautify_node_result_metadata_only(
            cleaned_dict, i, total_nodes=total_nodes
        )
        processed_results.append(beautified_result)
    
    return processed_results
