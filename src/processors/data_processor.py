"""Data processors for converting tree-sitter JSON to SQLite graph."""

import hashlib
from typing import List, Dict
from loguru import logger

from models import (
    CodeNode,
    CodeEdge,
    ParsedCodebase,
    SQLiteNode,
    SQLiteRelationship,
    GraphData,
)
from utils import normalize_node_type, normalize_relationship_type
from .node_embedding_processor import get_node_embedding_processor
from config import config


class NodeProcessor:
    """Processes tree-sitter nodes into SQLite format."""

    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self._file_hash_cache = {}  # Cache to avoid duplicate file hash insertions

    def process_node(self, node: CodeNode, project_id: int) -> SQLiteNode:
        """Convert a tree-sitter node to SQLite format."""
        # Keep original case for file path
        file_path = node.path if node.path else None
        file_hash_id = (
            self._file_hash_cache.get((project_id, file_path)) if file_path else None
        )

        processed_lines = (
            [node.start_line, node.end_line]
            if hasattr(node, "start_line") and hasattr(node, "end_line")
            else node.lines
        )

        cleaned_properties = None
        if node.metadata:
            unwanted_keys = {"file", "line", "visibility"}
            cleaned_properties = {
                k: v for k, v in node.metadata.items() if k not in unwanted_keys
            }

        # Keep original case for name
        name = node.name if node.name else None

        return SQLiteNode(
            node_id=node.id,
            project_id=project_id,
            node_type=normalize_node_type(node.type),
            name=name,
            file_hash_id=file_hash_id,
            lines=processed_lines,
            code_snippet=node.content,
            properties=cleaned_properties,
        )

    def clear_cache(self):
        """Clear the file hash cache."""
        self._file_hash_cache.clear()
        logger.debug("File hash cache cleared")


class RelationshipProcessor:
    """Processes tree-sitter edges into SQLite relationships."""

    def process_edge(self, edge: CodeEdge, project_id: int) -> SQLiteRelationship:
        """Convert a tree-sitter edge to SQLite relationship format."""
        # Filter metadata properties - remove unwanted items like visibility, file, line
        cleaned_properties = None
        if edge.metadata:
            unwanted_keys = {"file", "line", "visibility"}
            cleaned_properties = {
                k: v for k, v in edge.metadata.items() if k not in unwanted_keys
            }

        return SQLiteRelationship(
            from_node_id=edge.from_id,
            to_node_id=edge.to_id,
            project_id=project_id,
            relationship_type=normalize_relationship_type(edge.type),
            properties=cleaned_properties,
        )


class GraphDataProcessor:
    """Main processor that coordinates node and relationship processing with automatic embeddings."""

    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self.node_processor = NodeProcessor(db_connection)
        self.relationship_processor = RelationshipProcessor()
        self.embedding_processor = get_node_embedding_processor(
            max_tokens=config.embedding.max_tokens,
            overlap_tokens=config.embedding.overlap_tokens,
        )

    def _create_file_hashes_batch(
        self, nodes: List[CodeNode], project_id: int
    ) -> Dict[str, int]:
        """Pre-create all file hashes using file nodes directly - since file nodes are unique."""
        file_path_to_hash_id = {}

        # Process only file nodes - they contain all unique file information
        for node in nodes:
            if node.type != "file":
                continue

            # Extract metadata directly - well-structured JSON guaranteed
            file_size = node.metadata.get("size", 0) if node.metadata else 0
            language = node.metadata.get("language", "") if node.metadata else ""
            content_hash = (
                node.content_hash
                or hashlib.sha256(node.content.encode("utf-8")).hexdigest()
                if node.content
                else ""
            )

            # Keep original case for file path and name
            file_path = node.path if node.path else None
            name = node.name if node.name else None

            file_hash_id = self.db_connection.get_or_create_file_hash(
                project_id=project_id,
                file_path=file_path,
                content_hash=content_hash,
                file_size=file_size,
                language=language,
                name=name,
            )
            if file_hash_id:
                file_path_to_hash_id[file_path] = file_hash_id

        print(f"🗂️ Created {len(file_path_to_hash_id)} file hashes from file nodes")
        return file_path_to_hash_id

    def process_codebase(
        self, parsed_data: ParsedCodebase, project_id: int, project_name: str
    ) -> GraphData:
        """Process complete parsed codebase into graph format with embeddings."""
        # Clear cache and log processing start
        self.node_processor.clear_cache()
        print(
            f"🏗️ Processing project '{project_name}' (ID: {project_id}) with {len(parsed_data.nodes)} nodes and {len(parsed_data.edges)} edges"
        )

        # Pre-create file hashes using file nodes directly
        file_path_to_hash_id = self._create_file_hashes_batch(
            parsed_data.nodes, project_id
        )
        self.node_processor._file_hash_cache.update(
            {
                (project_id, path): hash_id
                for path, hash_id in file_path_to_hash_id.items()
            }
        )

        # Generate embeddings and process all data
        embedded_nodes = self.embedding_processor.process_nodes_with_embeddings(
            parsed_data.nodes, project_id, project_name
        )
        sqlite_nodes = [
            self.node_processor.process_node(node, project_id)
            for node in embedded_nodes
        ]
        sqlite_relationships = [
            self.relationship_processor.process_edge(edge, project_id)
            for edge in parsed_data.edges
        ]

        print(
            f"✅ Successfully processed {len(sqlite_nodes)} nodes and {len(sqlite_relationships)} relationships"
        )
        return GraphData(nodes=sqlite_nodes, relationships=sqlite_relationships)
