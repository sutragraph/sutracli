"""
Cross-Index Integration Service

Main integration point for cross-indexing analysis and connection matching workflow.
This service orchestrates the complete process from analysis to connection matching and storage.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .cross_index_service import CrossIndexService
from .connection_matching_service import ConnectionMatchingService
from ....graph.sqlite_client import SQLiteConnection

logger = logging.getLogger(__name__)

class CrossIndexIntegration:
    """
    Main integration service for cross-indexing analysis and connection matching.
    
    This service provides the complete workflow:
    1. Run cross-indexing analysis to discover connections
    2. Extract incoming and outgoing connections with IDs
    3. Run connection matching analysis
    4. Store matched connections in database
    5. Return comprehensive results
    """

    def __init__(self):
        self.cross_index_service = CrossIndexService()
        self.connection_matching_service = ConnectionMatchingService()
        self.db_client = SQLiteConnection()

    def run_complete_analysis(self, project_path: str, project_id: str = None) -> Dict[str, Any]:
        """
        Run complete cross-indexing analysis and connection matching workflow.
        
        Args:
            project_path: Path to the project/repository to analyze
            project_id: Optional project identifier for database storage
            
        Returns:
            Dict containing complete analysis results and matching data
        """
        try:
            logger.info(f"Starting complete cross-indexing analysis for project: {project_path}")

            # Step 1: Run cross-indexing analysis
            logger.info("Step 1: Running cross-indexing analysis...")
            analysis_results = self.cross_index_service.analyze_project(project_path)

            if not analysis_results.get("success", False):
                return {
                    "success": False,
                    "error": "Cross-indexing analysis failed",
                    "analysis_results": analysis_results
                }

            # Step 2: Extract connections with IDs
            logger.info("Step 2: Extracting connections...")
            incoming_connections = self._extract_connections(
                analysis_results.get("incoming_connections", []), "incoming"
            )
            outgoing_connections = self._extract_connections(
                analysis_results.get("outgoing_connections", []), "outgoing"
            )

            logger.info(f"Extracted {len(incoming_connections)} incoming and {len(outgoing_connections)} outgoing connections")

            # Step 3: Run connection matching if we have connections
            matching_results = None
            if incoming_connections or outgoing_connections:
                logger.info("Step 3: Running connection matching...")
                matching_results = self.connection_matching_service.match_connections(
                    incoming_connections, outgoing_connections, project_id
                )
            else:
                logger.info("Step 3: Skipping connection matching - no connections found")
                matching_results = {
                    "success": True,
                    "matching_results": {"matches": [], "total_matches": 0},
                    "statistics": {"total_incoming": 0, "total_outgoing": 0, "total_matches": 0}
                }

            # Step 4: Compile comprehensive results
            complete_results = {
                "success": True,
                "project_id": project_id,
                "project_path": project_path,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "cross_indexing_results": analysis_results,
                "connection_matching_results": matching_results,
                "summary": {
                    "total_incoming_connections": len(incoming_connections),
                    "total_outgoing_connections": len(outgoing_connections),
                    "total_matched_connections": matching_results.get("statistics", {}).get("total_matches", 0),
                    "match_rate_percentage": matching_results.get("statistics", {}).get("match_rate", 0),
                    "analysis_success": analysis_results.get("success", False),
                    "matching_success": matching_results.get("success", False)
                }
            }

            logger.info(f"Complete analysis finished successfully. Found {len(incoming_connections)} incoming, {len(outgoing_connections)} outgoing, {matching_results.get('statistics', {}).get('total_matches', 0)} matches")

            return complete_results

        except Exception as e:
            logger.error(f"Error in complete analysis workflow: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path,
                "project_id": project_id
            }

    def _extract_connections(self, connections_data: List[Dict], connection_type: str) -> List[Dict]:
        """
        Simple extraction of connections with IDs for matching analysis.
        
        Args:
            connections_data: Raw connection data from cross-indexing analysis
            connection_type: "incoming" or "outgoing"
            
        Returns:
            List of formatted connection objects with IDs
        """
        formatted_connections = []

        for conn in connections_data:
            # Just use the connection data as-is with the database ID
            formatted_conn = {
                "id": conn.get("id"),  # Use existing database ID
                "type": conn.get("type", "HTTP_API"),
                "endpoint": conn.get("endpoint", conn.get("url", conn.get("path", ""))),
                "method": conn.get("method", conn.get("http_method", "")),
                "file_path": conn.get("file_path", ""),
                "line_number": conn.get("line_number", ""),
                "description": conn.get("description", ""),
                "technology": conn.get("technology", conn.get("framework", "")),
            }

            formatted_connections.append(formatted_conn)

        return formatted_connections

    def get_project_connection_matches(
        self, confidence_filter: str = None
    ) -> List[Dict]:
        """
        Get connection matches for a project.
        
        Args:
            project_id: Optional project filter
            confidence_filter: Optional confidence level filter
            
        Returns:
            List of connection matches
        """
        return self.connection_matching_service.get_connection_matches(
            confidence_filter
        )

    def get_connection_statistics(self, project_id: str = None) -> Dict[str, Any]:
        """
        Get connection matching statistics.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Statistics dictionary
        """
        try:
            if project_id:
                sql = "SELECT * FROM connection_matching_stats WHERE project_id = ?"
                values = (project_id,)
            else:
                sql = "SELECT * FROM connection_matching_stats"
                values = ()

            results = self.db_client.fetch_all(sql, values)

            if results:
                return results[0]  # Return first result
            else:
                return {
                    "total_matches": 0,
                    "high_confidence_matches": 0,
                    "medium_confidence_matches": 0,
                    "low_confidence_matches": 0,
                    "http_api_matches": 0,
                    "graphql_matches": 0,
                    "webhook_matches": 0,
                    "message_queue_matches": 0,
                    "file_based_matches": 0
                }

        except Exception as e:
            logger.error(f"Error fetching connection statistics: {str(e)}")
            return {"error": str(e)}

# Example usage function
def analyze_project_connections(project_path: str, project_id: str = None) -> Dict[str, Any]:
    """
    Main function to analyze a project's connections and store results.
    
    Args:
        project_path: Path to the project to analyze
        project_id: Optional project identifier
        
    Returns:
        Complete analysis results
    """
    integration = CrossIndexIntegration()
    return integration.run_complete_analysis(project_path, project_id)

# CLI integration function
def run_connection_analysis_cli(project_path: str, project_id: str = None, output_file: str = None):
    """
    CLI function for running connection analysis.
    
    Args:
        project_path: Path to project
        project_id: Optional project ID
        output_file: Optional output file for results
    """
    import json
    
    # Connection analysis starting - handled by commands.py
    
    results = analyze_project_connections(project_path, project_id)
    
    if results.get("success"):
        # Analysis results handled by commands.py
        pass
    else:
        # Analysis errors handled by commands.py
        pass
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        # Results saving handled by commands.py
    
    return results
