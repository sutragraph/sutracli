"""
Connection Processor for Cross-Index Analysis Results

Processes attempt_completion JSON output and stores connections in database.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionProcessor:
    """
    Processes cross-index analysis results and stores them in database.
    """
    
    def __init__(self, db_connection):
        """
        Initialize the connection processor.
        
        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
    
    def process_attempt_completion(self, attempt_completion_output: str, project_path: str) -> Dict[str, Any]:
        """
        Process attempt_completion output and store connections in database.
        
        Args:
            attempt_completion_output: Raw output from attempt_completion tool
            project_path: Path to the analyzed project
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            # Extract JSON from XML tags
            json_data = self._extract_json_from_xml(attempt_completion_output)
            
            # Validate JSON structure
            self._validate_json_structure(json_data)
            
            # Process and store connections
            results = self._store_connections(json_data, project_path)
            
            return {
                "success": True,
                "project_path": project_path,
                "timestamp": datetime.now().isoformat(),
                "statistics": results,
                "message": "Cross-index analysis results processed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "project_path": project_path,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Failed to process cross-index analysis results"
            }
    
    def _extract_json_from_xml(self, xml_output: str) -> Dict[str, Any]:
        """
        Extract JSON data from attempt_completion XML tags.
        
        Args:
            xml_output: Raw XML output with JSON inside
            
        Returns:
            Parsed JSON data as dictionary
        """
        # Find JSON content between XML tags
        pattern = r'<attempt_completion>\s*(\{.*?\})\s*</attempt_completion>'
        match = re.search(pattern, xml_output, re.DOTALL)
        
        if not match:
            raise ValueError("No valid attempt_completion XML tags found in output")
        
        json_content = match.group(1)
        
        try:
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in attempt_completion: {e}")
    
    def _validate_json_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate the JSON structure matches expected format.
        
        Args:
            data: Parsed JSON data
            
        Raises:
            ValueError: If structure is invalid
        """
        # At least one direction must be present
        if "incoming_connections" not in data and "outgoing_connections" not in data:
            raise ValueError("At least one of 'incoming_connections' or 'outgoing_connections' must be present")
        
        # Validate each present direction
        for direction in ["incoming_connections", "outgoing_connections"]:
            if direction in data:
                if not isinstance(data[direction], dict):
                    raise ValueError(f"Key '{direction}' must be a dictionary")
                
                # Validate structure for this direction
                for technology, files in data[direction].items():
                    if not isinstance(files, dict):
                        raise ValueError(f"Technology '{technology}' in '{direction}' must be a dictionary")
                    
                    for file_path, snippets in files.items():
                        if not isinstance(snippets, list):
                            raise ValueError(f"File '{file_path}' must contain a list of snippets")
                        
                        for snippet in snippets:
                            if not isinstance(snippet, dict):
                                raise ValueError("Each snippet must be a dictionary")
                            
                            if "snippet_lines" not in snippet or "description" not in snippet:
                                raise ValueError("Each snippet must have 'snippet_lines' and 'description'")
    
    def _store_connections(self, data: Dict[str, Any], project_path: str) -> Dict[str, int]:
        """
        Store connections in database.
        
        Args:
            data: Validated JSON data
            project_path: Project path
            
        Returns:
            Statistics about stored connections
        """
        stats = {
            "incoming_connections": 0,
            "outgoing_connections": 0,
            "total_technologies": 0,
            "total_files": 0,
            "total_snippets": 0
        }
        
        # Process incoming connections (if present)
        if "incoming_connections" in data:
            stats["incoming_connections"] = self._store_direction_connections(
                data["incoming_connections"], 
                "incoming", 
                project_path
            )
        
        # Process outgoing connections (if present)
        if "outgoing_connections" in data:
            stats["outgoing_connections"] = self._store_direction_connections(
                data["outgoing_connections"], 
                "outgoing", 
                project_path
            )
        
        # Calculate totals
        all_technologies = set()
        all_files = set()
        total_snippets = 0
        
        for direction in ["incoming_connections", "outgoing_connections"]:
            if direction in data:
                for technology, files in data[direction].items():
                    all_technologies.add(technology)
                    for file_path, snippets in files.items():
                        all_files.add(file_path)
                        total_snippets += len(snippets)
        
        stats["total_technologies"] = len(all_technologies)
        stats["total_files"] = len(all_files)
        stats["total_snippets"] = total_snippets
        
        return stats
    
    def _store_direction_connections(self, connections: Dict[str, Any], direction: str, project_path: str) -> int:
        """
        Store connections for a specific direction (incoming/outgoing).
        
        Args:
            connections: Connection data for this direction
            direction: "incoming" or "outgoing"
            project_path: Project path
            
        Returns:
            Number of connections stored
        """
        connection_count = 0
        
        for technology, files in connections.items():
            for file_path, snippets in files.items():
                for snippet in snippets:
                    # Store individual connection in database
                    self._insert_connection(
                        project_path=project_path,
                        technology=technology,
                        file_path=file_path,
                        snippet_lines=snippet["snippet_lines"],
                        description=snippet["description"],
                        direction=direction
                    )
                    connection_count += 1
        
        return connection_count
    
    def _insert_connection(self, project_path: str, technology: str, file_path: str, 
                          snippet_lines: str, description: str, direction: str) -> None:
        """
        Insert a single connection into the database.
        
        Args:
            project_path: Path to the analyzed project
            technology: Technology name (flask, postgresql, etc.)
            file_path: Relative file path
            snippet_lines: Line range (e.g., "15-20")
            description: Connection description
            direction: "incoming" or "outgoing"
        """
        # Parse line range
        start_line, end_line = self._parse_line_range(snippet_lines)
        
        # Insert into database
        query = """
        INSERT INTO cross_index_connections 
        (project_path, technology, file_path, start_line, end_line, description, direction, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute(query, (
            project_path,
            technology,
            file_path,
            start_line,
            end_line,
            description,
            direction,
            datetime.now().isoformat()
        ))
    
    def _parse_line_range(self, snippet_lines: str) -> tuple[int, int]:
        """
        Parse line range string into start and end line numbers.
        
        Args:
            snippet_lines: Line range string (e.g., "15-20" or "25")
            
        Returns:
            Tuple of (start_line, end_line)
        """
        if "-" in snippet_lines:
            start, end = snippet_lines.split("-", 1)
            return int(start.strip()), int(end.strip())
        else:
            # Single line
            line = int(snippet_lines.strip())
            return line, line
    
    def get_project_connections(self, project_path: str) -> Dict[str, Any]:
        """
        Retrieve all connections for a specific project.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Dictionary with project connections organized by direction and technology
        """
        query = """
        SELECT technology, file_path, start_line, end_line, description, direction, created_at
        FROM cross_index_connections 
        WHERE project_path = ?
        ORDER BY direction, technology, file_path, start_line
        """
        
        results = self.db.execute(query, (project_path,)).fetchall()
        
        # Organize results
        connections = {
            "incoming_connections": {},
            "outgoing_connections": {}
        }
        
        for row in results:
            technology, file_path, start_line, end_line, description, direction, created_at = row
            
            direction_key = f"{direction}_connections"
            
            if technology not in connections[direction_key]:
                connections[direction_key][technology] = {}
            
            if file_path not in connections[direction_key][technology]:
                connections[direction_key][technology][file_path] = []
            
            # Format line range
            if start_line == end_line:
                snippet_lines = str(start_line)
            else:
                snippet_lines = f"{start_line}-{end_line}"
            
            connections[direction_key][technology][file_path].append({
                "snippet_lines": snippet_lines,
                "description": description,
                "created_at": created_at
            })
        
        return connections
    
    def create_connections_table(self) -> None:
        """
        Create the cross_index_connections table if it doesn't exist.
        """
        query = """
        CREATE TABLE IF NOT EXISTS cross_index_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT NOT NULL,
            technology TEXT NOT NULL,
            file_path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            description TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
            created_at TEXT NOT NULL,
            UNIQUE(project_path, file_path, start_line, end_line, direction)
        )
        """
        
        self.db.execute(query)
        
        # Create indexes for better query performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_project_path ON cross_index_connections(project_path)",
            "CREATE INDEX IF NOT EXISTS idx_technology ON cross_index_connections(technology)",
            "CREATE INDEX IF NOT EXISTS idx_direction ON cross_index_connections(direction)",
            "CREATE INDEX IF NOT EXISTS idx_file_path ON cross_index_connections(file_path)"
        ]
        
        for index_query in indexes:
            self.db.execute(index_query)
