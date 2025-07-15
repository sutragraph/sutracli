"""
Main converter class that orchestrates the conversion process.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

from .sqlite_client import SQLiteConnection, GraphOperations
from models import ParsedCodebase, CodeNode, CodeEdge, Project
from processors import GraphDataProcessor
from utils import load_json_file


class TreeSitterToSQLiteConverter:
    """Main converter class that handles conversion from tree-sitter JSON to SQLite knowledge graph."""

    def __init__(self, sqlite_connection: Optional[SQLiteConnection] = None):
        """Initialize converter with optional connection."""
        self.connection = sqlite_connection or SQLiteConnection()
        self.graph_ops = GraphOperations(self.connection)
        self.processor = GraphDataProcessor(self.connection)
        logger.debug("🛠️ TreeSitterToSQLiteConverter initialized")

    def convert_json_to_graph(
        self,
        json_file_path: str,
        project_name: Optional[str] = None,
        project_config: Optional[Dict[str, Any]] = None,
        clear_existing: bool = False,
        create_indexes: bool = True,
    ) -> Dict[str, Any]:
        """
        Convert tree-sitter JSON file to SQLite knowledge graph.
        Embeddings are automatically generated for all nodes.

        Args:
            json_file_path: Path to the tree-sitter JSON file
            project_name: Name of the project/codebase (auto-derived if not provided)
            project_config: Project configuration dictionary with metadata
            clear_existing: Whether to clear existing data in the database
            create_indexes: Whether to create indexes for better performance

        Returns:
            Dictionary with conversion statistics
        """
        logger.debug("\n🚀 Starting conversion of:", json_file_path)

        try:
            # Auto-derive project name if not provided
            if project_name is None:
                project_name = Path(json_file_path).stem
                logger.debug(f"📁 Project name: {project_name}")

            # Load and parse JSON data
            logger.debug("📦 Loading JSON data...")
            json_data = load_json_file(json_file_path)
            parsed_data = self._parse_json_data(
                json_data, project_name, json_file_path, project_config
            )

            # Clear database if requested
            if clear_existing:
                logger.debug("🧹 Clearing existing database...")
                self.connection.clear_database(force_clear=True)
                # Recreate tables after clearing
                logger.debug("🗂️ Recreating database tables...")
                self.connection._create_tables()

            # Prepare project data for database
            project_data = {
                "name": project_name,
                "description": (
                    parsed_data.project.description if parsed_data.project else None
                ),
                "language": (
                    parsed_data.project.language if parsed_data.project else None
                ),
                "version": (
                    parsed_data.project.version if parsed_data.project else "1.0.0"
                ),
                "created_at": (
                    parsed_data.project.created_at if parsed_data.project else None
                ),
                "updated_at": (
                    parsed_data.project.updated_at if parsed_data.project else None
                ),
                "source_file": json_file_path,
            }

            # Create project and get its ID FIRST
            project_id = self.connection.insert_project(project_data)

            # Process data into graph format (embeddings are generated automatically)
            logger.debug("🧩 Processing data into graph format with embeddings...")
            graph_data = self.processor.process_codebase(
                parsed_data, project_id, project_name
            )

            # Insert data into SQLite
            logger.debug("🗃️ Inserting data into SQLite...")
            self.graph_ops.insert_graph_data(graph_data, project_data)

            # Create indexes
            if create_indexes:
                logger.debug("🔢 Creating database indexes...")
                self.connection.create_indexes()

            # Get final statistics
            stats = self.graph_ops.get_graph_stats()

            logger.debug("✅ Conversion completed successfully!")
            logger.debug(f"📊 Final statistics: {stats}")

            return {
                "status": "success",
                "input_file": json_file_path,
                "nodes_processed": len(graph_data.nodes),
                "relationships_processed": len(graph_data.relationships),
                "database_stats": stats,
            }

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return {"status": "failed", "error": str(e), "input_file": json_file_path}

    def _parse_json_data(
        self,
        json_data: Dict[str, Any],
        project_name: str,
        source_file: str,
        project_config: Optional[Dict[str, Any]] = None,
    ) -> ParsedCodebase:
        """
        Parse raw JSON data into structured format.

        Args:
            json_data: Raw JSON data from tree-sitter
            project_name: Name of the project
            source_file: Path to the source JSON file
            project_config: Project configuration with metadata

        Returns:
            Parsed codebase structure
        """
        logger.debug("Parsing JSON data structure...")

        # Detect language from JSON data or config
        detected_language = "Unknown"
        if project_config and project_config.get("language"):
            detected_language = project_config["language"]
        else:
            # Try to detect from file extensions in the JSON
            nodes_data = json_data.get("nodes", [])
            for node in nodes_data[:100]:
                if "language" in node:
                    detected_language = node["language"]
                    break

        # Create project info

        project_data = {
            "name": project_name,
            "source_file": source_file,
            "created_at": datetime.now().isoformat(),
            "language": detected_language,
        }

        # Add additional config data if provided
        if project_config:
            for key in ["description", "version"]:
                if key in project_config:
                    project_data[key] = project_config[key]

        project = Project(**project_data)

        # Extract nodes
        nodes_data = json_data.get("nodes", [])
        nodes = []

        for node_data in nodes_data:
            try:
                # Handle different possible field names and structures
                node = CodeNode(**node_data)
                nodes.append(node)
            except Exception as e:
                logger.warning(
                    f"Failed to parse node: {node_data.get('id', 'unknown')} - {e}"
                )

        # Extract edges/relationships
        edges_data = json_data.get("edges", json_data.get("relationships", []))
        edges = []

        for edge_data in edges_data:
            try:
                edge = CodeEdge(**edge_data)
                edges.append(edge)
            except Exception as e:
                logger.warning(f"Failed to parse edge: {edge_data} - {e}")

        logger.debug(
            f"🔍 Parsed {len(nodes)} nodes and {len(edges)} edges for project '{project_name}'"
        )

        return ParsedCodebase(nodes=nodes, edges=edges, project=project)

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
