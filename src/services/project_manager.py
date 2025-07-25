"""Project Manager - Centralized project management functionality."""

import time
import tempfile
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from loguru import logger

from graph.sqlite_client import SQLiteConnection
from graph.incremental_indexing import IncrementalIndexing
from embeddings.vector_db import VectorDatabase
from graph import TreeSitterToSQLiteConverter
from config import config


class ProjectManager:
    """Centralized project management for creation, indexing, and directory management."""

    def __init__(self, db_connection: SQLiteConnection, vector_db: VectorDatabase, memory_manager=None):
        """Initialize the project manager.
        
        Args:
            db_connection: Database connection for project operations
            vector_db: Vector database for embeddings
            memory_manager: Optional memory manager for incremental indexing
        """
        self.db_connection = db_connection
        self.vector_db = vector_db
        self.memory_manager = memory_manager

        # Initialize incremental indexing with memory manager if provided
        self.incremental_indexer = IncrementalIndexing(
            self.db_connection, self.memory_manager
        ) if memory_manager else IncrementalIndexing(self.db_connection)

        # Initialize converter for tree-sitter to SQLite conversion
        self.converter = TreeSitterToSQLiteConverter()

        # Cache for project directories to avoid repeated calculations
        self._project_dir_cache: Dict[str, Optional[Path]] = {}

    def determine_project_name(self, project_path: Optional[str] = None) -> str:
        """Determine the correct project name from the database or specified directory.
        
        Args:
            project_path: Optional path to the project directory. If None, uses current directory.
        """
        target_path = Path(project_path).absolute() if project_path else Path.cwd().absolute()

        try:
            projects = self.db_connection.list_all_projects()
            if projects:
                # Check if target directory is a subdirectory of any existing project
                existing_project = self.find_parent_project(projects, target_path)
                if existing_project:
                    logger.debug(f"Found parent project: {existing_project}")
                    return existing_project

            # If no parent project found or no projects exist, use current directory name
            target_name = target_path.name
            logger.debug(f"Using directory name as project name: {target_name}")
            return target_name

        except Exception as e:
            logger.warning(f"Error determining project name: {e}")
            return target_path.name if 'target_path' in locals() else Path.cwd().name

    def find_parent_project(self, projects: List[Dict[str, Any]], target_path: Optional[Path] = None) -> Optional[str]:
        """Find if target directory is a subdirectory of any existing project.
        
        Args:
            projects: List of existing projects from database
            target_path: Path to check. If None, uses current directory.
        """
        check_dir = target_path.absolute() if target_path else Path.cwd().absolute()

        for project in projects:
            project_name = project["name"]
            try:
                # Get the project's root directory by finding the common root of all file paths
                project_dir = self.get_project_directory(project_name)
                if project_dir and check_dir.is_relative_to(project_dir):
                    logger.debug(f"Directory {check_dir} is within project {project_name} at {project_dir}")
                    return project_name
            except Exception as e:
                logger.debug(f"Error checking project {project_name}: {e}")
                continue

        return None

    def get_project_directory(self, project_name: str) -> Optional[Path]:
        """Get the root directory of a project by analyzing its file paths.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Path to the project directory or None if not found
        """
        # Check cache first
        if project_name in self._project_dir_cache:
            return self._project_dir_cache[project_name]

        try:
            # Get all file paths for this project
            file_paths = self.db_connection.execute_query(
                """
                SELECT DISTINCT file_path 
                FROM file_hashes 
                WHERE project_id = (SELECT id FROM projects WHERE name = ?)
                """,
                (project_name,)
            )

            if not file_paths:
                self._project_dir_cache[project_name] = None
                return None

            # Convert to Path objects and find common root
            paths = [Path(row["file_path"]).absolute() for row in file_paths]

            # Find the common root directory
            if len(paths) == 1:
                result = paths[0].parent
            else:
                # Find the longest common path
                common_path = paths[0]
                for path in paths[1:]:
                    # Find common parts between current common_path and this path
                    common_parts = []
                    for part1, part2 in zip(common_path.parts, path.parts):
                        if part1 == part2:
                            common_parts.append(part1)
                        else:
                            break

                    if common_parts:
                        common_path = Path(*common_parts)
                    else:
                        # No common path found
                        result = None
                        break
                else:
                    result = common_path

            # Cache the result
            self._project_dir_cache[project_name] = result
            return result

        except Exception as e:
            logger.debug(f"Error getting project directory for {project_name}: {e}")
            self._project_dir_cache[project_name] = None
            return None

    def ensure_project_indexed(self, project_name: str, project_path: Optional[str] = None) -> None:
        """Ensure the specified project is indexed in the database.
        
        Args:
            project_name: Name of the project
            project_path: Optional path to the project directory
        """
        try:
            print(f"🏷️  Project: {project_name}")

            # Check if project exists in database
            if not self.db_connection.project_exists(project_name):
                self.auto_index_project(project_name, project_path)
        except Exception as e:
            logger.error(f"Error checking project indexing status: {e}")
            print(f"❌ Error checking project status: {e}")
            print("   Continuing with limited functionality...")

    def auto_index_project(self, project_name: str, project_path: Optional[str] = None) -> None:
        """Automatically index the specified project if not found in database.
        
        Args:
            project_name: Name of the project
            project_path: Optional path to the project directory
        """
        try:
            print(f"⚠️  Project '{project_name}' not found in database")
            print("🔄 Starting automatic indexing...")
            print("   This will analyze the codebase and generate embeddings for better responses.")
            print("   Please wait while the project is being indexed...\n")

            # Phase 1: Parse repository
            parser_output_path = self.run_parser(project_name, project_path)

            # Phase 2: Generate embeddings and knowledge graph
            self.run_embedding_generation(project_name, parser_output_path)

            print("\n✅ Project indexing completed successfully!")
            print("   The agent is now ready to provide intelligent assistance.\n")

            # Clear cache for this project since we just indexed it
            self._project_dir_cache.pop(project_name, None)

        except Exception as e:
            logger.error(f"Error during auto-indexing: {e}")
            print(f"❌ Auto-indexing failed: {e}")
            print("   Continuing with limited functionality.")

    def run_parser(self, project_name: str, project_path: Optional[str] = None) -> str:
        """Run the parser phase of indexing.
        
        Args:
            project_name: Name of the project to parse
            project_path: Optional path to the project directory
            
        Returns:
            Path to the generated parser output file
        """
        print("PHASE 1: Parsing Repository")
        print("-" * 40)

        try:
            # Import correct parser components
            from parser.analyzer.analyzer import Analyzer

            # Initialize analyzer
            analyzer = Analyzer(repo_id=project_name)

            # Determine target directory
            target_dir = Path(project_path).absolute() if project_path else Path.cwd().absolute()
            print(f"   Parsing directory: {target_dir}")

            # Run the async analyze_directory method
            results = asyncio.run(analyzer.analyze_directory(str(target_dir)))

            # Save results to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(results, f, indent=2)
                parser_output_path = f.name

            print(f"✅ Repository parsed successfully")
            print(f"   Generated analysis for project: {project_name}")

            return parser_output_path

        except Exception as e:
            logger.error(f"Parser error: {e}")
            print(f"❌ Failed to parse repository: {e}")
            raise

    def run_embedding_generation(self, project_name: str, parser_output_path: Optional[str] = None) -> Dict[str, Any]:
        """Run the embedding generation phase of indexing.
        
        Args:
            project_name: Name of the project
            parser_output_path: Path to parser output file (if None, will run parser first)
            
        Returns:
            Result dictionary from the conversion process
        """
        print("\nPHASE 2: Generating Embeddings & Knowledge Graph")
        print("-" * 40)

        try:
            # If no parser output path provided, run parser first
            if parser_output_path is None:
                parser_output_path = self.run_parser(project_name)

            # Generate embeddings and knowledge graph
            result = self.converter.convert_json_to_graph(
                parser_output_path,
                project_name=project_name,
                clear_existing=False,
                create_indexes=True,
            )

            if result and result.get("status") == "success":
                stats = result.get("database_stats", {})
                print(f"✅ Knowledge graph generated successfully!")
                print(f"   Processed: {stats.get('total_nodes', 0)} nodes, {stats.get('total_relationships', 0)} relationships")
                print(f"   Embeddings: Generated for semantic search")

                # Clean up temporary file
                if os.path.exists(parser_output_path):
                    os.unlink(parser_output_path)

                return result
            else:
                raise Exception("Knowledge graph generation failed")

        except Exception as e:
            logger.error(f"Graph generation error: {e}")
            print(f"❌ Failed to generate knowledge graph: {e}")
            raise

    def perform_incremental_indexing(self, project_name: str) -> Iterator[Dict[str, Any]]:
        """Perform incremental reindexing of the database for the specified project.
        
        Args:
            project_name: Name of the project to reindex
            
        Yields:
            Indexing status and statistics
        """
        logger.debug(f"🔄 Running database reindex for project {project_name}")
        stats = self.incremental_indexer.reindex_database(project_name)
        yield {
            "type": "incremental_indexing",
            "stats": stats,
            "timestamp": time.time(),
        }

    def create_project(self, project_name: str, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project entry in the database.
        
        Args:
            project_name: Name of the project
            project_path: Optional path to the project (defaults to current directory)
            
        Returns:
            Dictionary with project creation result
        """
        try:
            if project_path is None:
                project_path = str(Path.cwd())

            # Check if project already exists
            if self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' already exists"
                }

            # Create project entry (assuming SQLiteConnection has a method for this)
            # Note: This might need to be adjusted based on actual SQLiteConnection API
            project_id = self.db_connection.create_project(project_name, project_path)

            logger.info(f"Created project '{project_name}' with ID {project_id}")

            return {
                "success": True,
                "project_id": project_id,
                "project_name": project_name,
                "project_path": project_path
            }

        except Exception as e:
            logger.error(f"Error creating project {project_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the database.
        
        Returns:
            List of project dictionaries
        """
        try:
            return self.db_connection.list_all_projects()
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return []

    def delete_project(self, project_name: str) -> Dict[str, Any]:
        """Delete a project and all its associated data.
        
        Args:
            project_name: Name of the project to delete
            
        Returns:
            Dictionary with deletion result
        """
        try:
            # Check if project exists
            if not self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found"
                }

            # Delete project (assuming SQLiteConnection has a method for this)
            # Note: This might need to be adjusted based on actual SQLiteConnection API
            self.db_connection.delete_project(project_name)

            # Clear cache for this project
            self._project_dir_cache.pop(project_name, None)

            logger.info(f"Deleted project '{project_name}'")

            return {
                "success": True,
                "project_name": project_name
            }

        except Exception as e:
            logger.error(f"Error deleting project {project_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_project_stats(self, project_name: str) -> Dict[str, Any]:
        """Get statistics for a specific project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Dictionary with project statistics
        """
        try:
            if not self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found"
                }

            # Get project statistics (this might need to be implemented in SQLiteConnection)
            stats = self.db_connection.get_project_statistics(project_name)

            return {
                "success": True,
                "project_name": project_name,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Error getting project stats for {project_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def clear_cache(self) -> None:
        """Clear the project directory cache."""
        self._project_dir_cache.clear()
        logger.debug("Cleared project directory cache")

    def index_project_at_path(self, project_path: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Index a project at the specified path.
        
        Args:
            project_path: Path to the project directory to index
            project_name: Optional custom project name. If None, uses directory name.
            
        Returns:
            Result dictionary with indexing status
        """
        try:
            target_path = Path(project_path).absolute()

            # Validate path exists
            if not target_path.exists():
                return {
                    "success": False,
                    "error": f"Project path does not exist: {project_path}"
                }

            if not target_path.is_dir():
                return {
                    "success": False,
                    "error": f"Project path is not a directory: {project_path}"
                }

            # Determine project name
            if project_name is None:
                project_name = self.determine_project_name(str(target_path))

            logger.info(f"Indexing project '{project_name}' at path: {target_path}")

            # Check if project already exists
            if self.db_connection.project_exists(project_name):
                return {
                    "success": False,
                    "error": f"Project '{project_name}' already exists in database"
                }

            # Perform the indexing
            self.auto_index_project(project_name, str(target_path))

            return {
                "success": True,
                "project_name": project_name,
                "project_path": str(target_path),
                "message": f"Successfully indexed project '{project_name}'"
            }

        except Exception as e:
            logger.error(f"Error indexing project at {project_path}: {e}")
            return {
                "success": False,
                "error": f"Failed to index project: {str(e)}"
            }

    def get_or_create_project_id(
        self, project_name: str, project_path: Optional[str] = None
    ) -> int:
        """Get existing project ID or create a new project and return its ID.

        Args:
            project_name: Name of the project
            project_path: Optional path to the project (defaults to current directory)

        Returns:
            Project ID (integer)

        Raises:
            Exception: If project creation fails
        """
        try:
            # First try to get existing project ID
            result = self.db_connection.execute_query(
                "SELECT id FROM projects WHERE name = ?", (project_name,)
            )

            if result:
                project_id = result[0]["id"]
                logger.debug(
                    f"Found existing project '{project_name}' with ID {project_id}"
                )
                return project_id

            # Project doesn't exist, create it
            if project_path is None:
                project_path = str(Path.cwd())

            # Create project data
            import time

            project_data = {
                "name": project_name,
                "description": f"Auto-created project for {project_name}",
                "language": None,
                "version": None,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_file": project_path,
            }

            project_id = self.db_connection.insert_project(project_data)
            logger.info(f"Created new project '{project_name}' with ID {project_id}")

            return project_id

        except Exception as e:
            logger.error(f"Error getting or creating project {project_name}: {e}")
            raise
