"""
Main converter class that orchestrates the code extraction to SQLite conversion process.
"""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from graph import GraphOperations, SQLiteConnection
from models.schema import ExtractionData, Project
from utils import load_json_file


class ASTToSqliteConverter:
    """Main converter class that handles conversion from code extraction JSON to SQLite knowledge graph."""

    def __init__(self):
        """Initialize converter with singleton connection."""
        self.connection = SQLiteConnection()
        self.graph_ops = GraphOperations()
        logger.debug("🛠️ ASTToSqliteConverter initialized")

    def convert_json_to_graph(
        self,
        json_file_path: Path,
        project_path: Path,
        project_name: Optional[str] = None,
        clear_existing: bool = False,
    ) -> Dict[str, str | int | float]:
        """
        Convert code extraction JSON file to SQLite knowledge graph.

        Args:
            json_file_path: Path to the extraction JSON file
            project_path: Absolute path to the project directory
            project_name: Name of the project/codebase (auto-derived if not provided)
            clear_existing: Whether to clear existing data in the database

        Returns:
            Dictionary with conversion statistics

        Raises:
            Exception: If conversion fails
        """
        logger.debug(f"🚀 Starting conversion of: {json_file_path}")

        try:
            # Auto-derive project name if not provided
            if project_name is None:
                project_name = Path(json_file_path).stem
                print(f"📁 Project name: {project_name}")

            # Load and parse JSON data
            print("📦 Loading JSON data...")
            json_data = load_json_file(json_file_path)

            # Convert to ExtractionData model
            extraction_data = ExtractionData(**json_data)

            # Clear database if requested
            if clear_existing:
                print("🧹 Clearing existing database...")
                self.connection.clear_database()

            # Create project with all required fields
            from datetime import datetime

            current_time = datetime.now().isoformat()

            project = Project(
                id=1,  # Will be auto-assigned by database
                name=project_name,
                path=str(
                    project_path.absolute()
                ),  # Use the actual project directory path
                description="",
                created_at=current_time,
                updated_at=current_time,
            )

            # Insert project and get its ID
            project_id = self.connection.insert_project(project)
            logger.debug(f"📁 Created project '{project_name}' with ID: {project_id}")

            # Insert extraction data into SQLite
            logger.debug("🗃️ Inserting extraction data into SQLite...")
            self.graph_ops.insert_extraction_data(extraction_data, project_id)

            # Get final statistics
            stats = self.graph_ops.get_extraction_stats()

            print("✅ Conversion completed successfully!")
            print(f"📊 Final statistics: {stats}")

            # Count total items processed
            total_files = len(extraction_data.files)
            total_blocks = sum(
                len(file_data.blocks) for file_data in extraction_data.files.values()
            )
            total_relationships = sum(
                len(file_data.relationships)
                for file_data in extraction_data.files.values()
            )

            # Return simple stats dictionary
            return {
                "status": "success",
                "input_file": str(json_file_path),
                "project_name": project_name,
                "project_id": project_id,
                "files_processed": total_files,
                "blocks_processed": total_blocks,
                "relationships_processed": total_relationships,
                "total_nodes": stats.get("total_nodes", 0),
                "total_relationships": stats.get("total_relationships", 0),
            }

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            # Let the exception propagate instead of wrapping it
            raise

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
