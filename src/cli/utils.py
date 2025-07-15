"""Utility functions for CLI operations."""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from loguru import logger

from graph import TreeSitterToSQLiteConverter
from graph.sqlite_client import SQLiteConnection
from processors.node_embedding_processor import get_node_embedding_processor


def load_project_config(config_file: str) -> Dict[str, Any]:
    """Load project configuration from JSON file."""
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load project config: {e}")
        raise


def process_multiple_projects(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process multiple projects into one graph."""
    projects = config_data.get("projects", [])
    db_settings = config_data.get("database_settings", {})

    if not projects:
        raise ValueError("No projects found in configuration")

    results = []
    total_nodes = 0
    total_relationships = 0

    with TreeSitterToSQLiteConverter() as converter:
        clear_db = db_settings.get("clear_before_import", False)

        for i, project_config in enumerate(projects):
            project_name = project_config["name"]
            json_file = project_config["json_file"]

            logger.debug(f"Processing project {i+1}/{len(projects)}: {project_name}")

            if not Path(json_file).exists():
                logger.warning(f"Skipping {project_name}: file {json_file} not found")
                continue

            try:
                clear_for_this_project = clear_db and i == 0

                result = converter.convert_json_to_graph(
                    json_file,
                    project_name=project_name,
                    project_config=project_config,
                    clear_existing=clear_for_this_project,
                    create_indexes=False,  # Create indexes only at the end
                )

                if result["status"] == "success":
                    total_nodes += result["nodes_processed"]
                    total_relationships += result["relationships_processed"]
                    results.append(result)
                    logger.debug(
                        f"✅ {project_name}: {result['nodes_processed']} nodes, {result['relationships_processed']} relationships"
                    )
                else:
                    logger.error(f"❌ {project_name} failed: {result['error']}")
                    results.append(result)

            except Exception as e:
                logger.error(f"❌ {project_name} failed with exception: {e}")
                results.append(
                    {
                        "status": "failed",
                        "error": str(e),
                        "project_name": project_name,
                        "input_file": json_file,
                    }
                )

        if db_settings.get("create_indexes", True):
            logger.debug("Creating database indexes...")
            converter.connection.create_indexes()

        final_stats = converter.graph_ops.get_graph_stats()

        return {
            "status": "completed",
            "projects_processed": len([r for r in results if r["status"] == "success"]),
            "total_projects": len(projects),
            "total_nodes_processed": total_nodes,
            "total_relationships_processed": total_relationships,
            "final_database_stats": final_stats,
            "project_results": results,
        }


def clear_database_data(
    project_name: str | None = None, force: bool = False
) -> Dict[str, Any]:
    """Clear data from the database."""
    with TreeSitterToSQLiteConverter() as converter:
        if project_name:
            # Clear specific project
            if not force:
                response = input(
                    f"Are you sure you want to delete all data for project '{project_name}'? [y/N]: "
                )
                if response.lower() not in ["y", "yes"]:
                    logger.debug("Operation cancelled")
                    return {"status": "cancelled"}

            # Check if project has any nodes
            node_count = converter.connection.get_project_node_count(project_name)

            if node_count == 0:
                logger.debug(f"No data found for project '{project_name}'")
                return {"status": "no_data", "project_name": project_name}

            # Delete all nodes and relationships for the project
            deleted_count = converter.connection.delete_project_nodes(project_name)

            return {
                "status": "success",
                "project_name": project_name,
                "nodes_deleted": deleted_count,
            }
        else:
            # Clear all data
            # Get current stats before clearing (if tables exist)
            try:
                stats = converter.graph_ops.get_graph_stats()
                nodes_count = stats["total_nodes"]
                relationships_count = stats["total_relationships"]
            except Exception:
                nodes_count = 0
                relationships_count = 0

            # Check if there's data in the database
            if nodes_count > 0 or relationships_count > 0:
                if not force:
                    response = input(
                        f"⚠️  Database contains {nodes_count} nodes and {relationships_count} relationships.\n"
                        "Are you sure you want to completely clear the database (drop all tables)? [y/N]: "
                    )
                    if response.lower() not in ["y", "yes"]:
                        logger.debug("Operation cancelled - database preserved")
                        return {"status": "cancelled"}
            else:
                if not force:
                    response = input(
                        "Database appears to be empty. Drop all tables anyway? [y/N]: "
                    )
                    if response.lower() not in ["y", "yes"]:
                        logger.debug("Operation cancelled")
                        return {"status": "cancelled"}

            # Clear entire database (drop all tables)
            converter.connection.clear_database(force_clear=True)

            return {
                "status": "success",
                "nodes_deleted": nodes_count,
                "relationships_deleted": relationships_count,
            }


def list_projects():
    """List all projects in the database."""
    with TreeSitterToSQLiteConverter() as converter:
        projects = converter.connection.list_all_projects()

        if projects:
            logger.debug(f"Found {len(projects)} projects in the database:")
            for project in projects:
                logger.debug(
                    f"  - {project['name']} ({project.get('language', 'Unknown')}) v{project.get('version', '1.0.0')}"
                )
                if project.get("description"):
                    logger.debug(f"    Description: {project['description']}")
        else:
            logger.debug("No projects found in the database")


def show_database_stats():
    """Display comprehensive database and embedding statistics."""
    try:
        processor = get_node_embedding_processor()
        db_connection = SQLiteConnection()

        print("\n📊 Sutra Knowledge Database Statistics")
        print("=" * 50)

        try:
            cursor = db_connection.connection.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor = db_connection.connection.execute(
                "SELECT COUNT(*) FROM relationships"
            )
            total_relationships = cursor.fetchone()[0]

            cursor = db_connection.connection.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]

            cursor = db_connection.connection.execute("SELECT COUNT(*) FROM file_hashes")
            total_file_hashes = cursor.fetchone()[0]

            print(f"🗃️  Total Projects: {total_projects}")
            print(f"🔢 Total Nodes: {total_nodes:,}")
            print(f"🔗 Total Relationships: {total_relationships:,}")
            print(f"📁 Total File Hashes: {total_file_hashes:,}")

        except Exception as e:
            logger.error(f"Failed to get basic database stats: {e}")
            print("❌ Could not retrieve basic database statistics")

        try:
            embedding_stats = processor.get_embedding_stats()

            print(f"\n🧠 File Embedding Statistics:")
            print(
                f"   📦 Total Embeddings: {embedding_stats.get('total_embeddings', 0):,}"
            )
            print(
                f"   📁 File Nodes with Embeddings: {embedding_stats.get('unique_nodes', 0):,}"
            )
            print(
                f"   📊 Avg Chunks per File: {embedding_stats.get('average_chunks_per_node', 0)}"
            )
            print(
                f"   💾 Storage Method: {embedding_stats.get('storage_method', 'unknown')}"
            )
            print(
                f"   📏 Vector Dimension: {embedding_stats.get('vector_dimension', 0)}"
            )
            print(
                f"   🔧 Max Tokens/Chunk: {embedding_stats.get('max_tokens_per_chunk', 0)}"
            )
            print(f"   🔄 Overlap Tokens: {embedding_stats.get('overlap_tokens', 0)}")
            print(f"   🎯 Strategy: File-only embeddings with chunking")

            if "database_size_mb" in embedding_stats:
                print(f"   💽 Vector DB Size: {embedding_stats['database_size_mb']} MB")

        except Exception as e:
            logger.warning(f"Could not get embedding stats: {e}")

        try:
            cursor = db_connection.connection.execute(
                """
                SELECT node_type, COUNT(*) as count 
                FROM nodes 
                GROUP BY node_type 
                ORDER BY count DESC
            """
            )
            node_types = cursor.fetchall()

            if node_types:
                print(f"\n📈 Top Node Types:")
                for node_type, count in node_types:
                    percentage = (count / total_nodes * 100) if total_nodes > 0 else 0
                    print(f"   {node_type}: {count:,} ({percentage:.1f}%)")

        except Exception as e:
            logger.warning(f"Could not get node type distribution: {e}")

        try:
            cursor = db_connection.connection.execute(
                """
                SELECT relationship_type, COUNT(*) as count
                FROM relationships 
                GROUP BY relationship_type 
                ORDER BY count DESC
            """
            )
            node_types = cursor.fetchall()

            if node_types:
                print(f"\n📊 Top Relationship Types:")
                for relationship_type, count in node_types:
                    percentage = (
                        count / total_relationships * 100
                        if total_relationships > 0
                        else 0
                    )
                    print(f"   {relationship_type}: {count:,} ({percentage:.1f}%)")

        except Exception as e:
            logger.warning(f"Could not get relationship type distribution: {e}")

        try:
            cursor = db_connection.connection.execute(
                """
                SELECT p.name, p.language, COUNT(n.node_id) as node_count
                FROM projects p
                LEFT JOIN nodes n ON p.id = n.project_id
                GROUP BY p.id, p.name, p.language
                ORDER BY node_count DESC
            """
            )
            projects = cursor.fetchall()

            if projects:
                print(f"\n📋 Projects Breakdown:")
                for project_name, language, node_count in projects:
                    print(f"   {project_name} ({language}): {node_count:,} nodes")

        except Exception as e:
            logger.warning(f"Could not get project breakdown: {e}")

        try:
            cursor = db_connection.connection.execute(
                """
                SELECT p.name, COUNT(fh.id) as file_count
                FROM projects p
                LEFT JOIN file_hashes fh ON p.id = fh.project_id
                GROUP BY p.id, p.name
                HAVING COUNT(fh.id) > 0
                ORDER BY file_count DESC
            """
            )
            file_hashes = cursor.fetchall()

            if file_hashes:
                print(f"\n📁 File Hashes by Project:")
                for project_name, file_count in file_hashes:
                    print(f"   {project_name}: {file_count:,} files tracked")

        except Exception as e:
            logger.warning(f"Could not get file hash breakdown: {e}")

        print("\n✨ Analysis ready! Use 'python main.py analyze \"your problem description\"'")
        print("=" * 50)

        db_connection.close()

    except Exception as e:
        logger.error(f"Failed to show database statistics: {e}")
        print(f"❌ Failed to retrieve statistics: {e}")


def setup_logging(log_level: str):
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
